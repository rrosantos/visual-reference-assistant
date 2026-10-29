import uuid
from collections import OrderedDict

from google.genai import errors, types

import banco
import ia
import pinterest
import referencias

INSTRUCOES = """Você é a assistente de referências visuais da Raissa.
Ela salva imagens no Pinterest e pede sua ajuda para encontrar inspiração.

- Use buscar_referencias sempre que ela descrever o que procura; nunca invente pins.
- Se a busca vier vazia, explique que a pasta ainda não foi indexada e ofereça indexar.
- Antes de indexar, confirme com ela qual pasta e quantos pins (cada pin gasta uma chamada ao Gemini).
- Ao sugerir referências, diga em uma frase por que cada uma combina com o pedido.
- Responda em português, de forma curta e direta."""

MAXIMO_CONVERSAS = 50


class Conversa:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.referencias = {}
        self.modelos = [ia.MODELO, *ia.MODELOS_RESERVA]
        self.chat = self._criar_chat(self.modelos[0])

    def _criar_chat(self, modelo, historico=None):
        return ia.cliente().chats.create(
            model=modelo,
            history=historico,
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCOES,
                tools=self._ferramentas()
            )
        )

    def enviar(self, mensagem):
        self.referencias = {}

        while True:
            try:
                response = self.chat.send_message(mensagem)
                break
            except errors.APIError as erro:
                # Modelo congestionado ou sem cota: continua a conversa no próximo, com o mesmo histórico
                if erro.code not in (429, 503) or len(self.modelos) == 1:
                    raise
                self.modelos.pop(0)
                self.chat = self._criar_chat(self.modelos[0], self.chat.get_history())

        resposta = response.text or ""

        # Mostra só os pins que o agente citou; se ele não citou nenhum, mostra tudo que a busca trouxe
        citadas = [
            r for r in self.referencias.values()
            if r["pin_id"] in resposta or (r["titulo"] and r["titulo"] in resposta)
        ]

        return {
            "conversa_id": self.id,
            "resposta": resposta,
            "referencias": citadas or list(self.referencias.values())
        }

    def _guardar(self, itens):
        # Guarda os pins que as ferramentas devolveram para a tela mostrar as imagens
        for item in itens:
            self.referencias[item["pin_id"]] = item

    def _ferramentas(self):
        # O SDK do Gemini lê a assinatura e a docstring de cada função para montar a ferramenta
        def listar_pastas() -> list[dict]:
            """Lista as pastas (boards) do Pinterest da usuária, com id, nome e quantidade de pins."""
            try:
                pastas = pinterest.listar_pastas().get("items", [])
            except Exception as erro:
                return [{"erro": str(erro)}]

            return [
                {"id": p["id"], "nome": p.get("name"), "pins": p.get("pin_count")}
                for p in pastas
            ]

        def buscar_referencias(consulta: str, limite: int = 6) -> list[dict]:
            """Busca, entre os pins já indexados, as imagens mais parecidas com a descrição.

            Args:
                consulta: o que a usuária procura, ex.: "luz quente e clima melancólico".
                limite: quantas referências devolver (de 1 a 12).
            """
            try:
                encontradas = referencias.buscar_referencias(consulta, max(1, min(limite, 12)))
            except Exception as erro:
                return [{"erro": str(erro)}]

            self._guardar(encontradas)

            return [_resumo(r) for r in encontradas]

        def indexar_pasta(board_id: str, limite: int = 10) -> dict:
            """Analisa com IA os pins de uma pasta para que eles entrem na busca.

            Args:
                board_id: id da pasta, vindo de listar_pastas.
                limite: quantos pins analisar (de 1 a 50).
            """
            try:
                return referencias.indexar_pasta(board_id, max(1, min(limite, 50)))
            except Exception as erro:
                return {"erro": str(erro)}

        def detalhar_referencia(pin_id: str) -> dict:
            """Mostra a análise completa de um pin; se ele ainda não foi analisado, analisa agora."""
            try:
                referencia = banco.buscar(pin_id) or referencias.indexar_pin_por_id(pin_id)
            except Exception as erro:
                return {"erro": str(erro)}

            self._guardar([referencia])

            return _resumo(referencia)

        return [listar_pastas, buscar_referencias, indexar_pasta, detalhar_referencia]


def _resumo(referencia):
    return {
        "pin_id": referencia["pin_id"],
        "titulo": referencia["titulo"],
        "similaridade": referencia.get("similaridade"),
        **referencia["analise"]
    }


_conversas = OrderedDict()


def conversar(mensagem, conversa_id=None):
    conversa = _conversas.get(conversa_id)

    if conversa is None:
        conversa = Conversa()
        _conversas[conversa.id] = conversa

        # Conversas ficam só em memória; as mais antigas saem para não crescer sem limite
        while len(_conversas) > MAXIMO_CONVERSAS:
            _conversas.popitem(last=False)

    _conversas.move_to_end(conversa.id)

    return conversa.enviar(mensagem)
