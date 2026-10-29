import os
import re

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, field_validator

MODELO = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
MODELO_EMBEDDING = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")

# Tentados em ordem quando o modelo principal está congestionado (503) ou sem cota (429)
MODELOS_RESERVA = [
    m.strip() for m in os.getenv("GEMINI_MODELOS_RESERVA", "gemini-3.1-flash-lite").split(",") if m.strip()
]

PROMPT_ANALISE = """Você é uma diretora de arte analisando uma imagem de referência visual.
Descreva a imagem de forma objetiva, pensando em quem vai usá-la como inspiração
(ilustração, design, fotografia ou moda). Responda em português."""

_cliente = None


class AnaliseVisual(BaseModel):
    descricao: str = Field(description="O que aparece na imagem, em 1 ou 2 frases")
    estilo: list[str] = Field(description="Estilos visuais, ex.: minimalista, aquarela, cyberpunk")
    paleta: list[str] = Field(description="De 3 a 6 cores predominantes em hexadecimal, ex.: #E8A87C")
    iluminacao: str = Field(description="Tipo de luz, ex.: luz quente de fim de tarde")
    composicao: str = Field(description="Enquadramento e organização dos elementos")
    clima: str = Field(description="Sensação que a imagem passa, ex.: melancólico, acolhedor")
    tags: list[str] = Field(description="De 5 a 10 palavras-chave para busca")

    @field_validator("paleta")
    @classmethod
    def limpar_paleta(cls, paleta):
        return normalizar_paleta(paleta)


def normalizar_paleta(paleta):
    # O modelo às vezes devolve "#2A241F me", "1C3B2B" sem # ou duas cores grudadas
    cores = re.findall(r"(?<![0-9A-Fa-f])#?([0-9A-Fa-f]{6})(?![0-9A-Fa-f])", " ".join(paleta))

    return list(dict.fromkeys(f"#{cor.upper()}" for cor in cores))[:6]


def cliente():
    global _cliente

    if _cliente is None:
        _cliente = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    return _cliente


def analisar_imagem(imagem, mime_type, titulo=None):
    contexto = PROMPT_ANALISE

    if titulo:
        contexto += f"\nTítulo dado pela pessoa ao salvar: {titulo}"

    modelos = [MODELO, *MODELOS_RESERVA]

    for modelo in modelos:
        try:
            response = cliente().models.generate_content(
                model=modelo,
                contents=[types.Part.from_bytes(data=imagem, mime_type=mime_type), contexto],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AnaliseVisual
                )
            )
            return response.parsed
        except errors.APIError as erro:
            if erro.code not in (429, 503) or modelo == modelos[-1]:
                raise


def texto_para_busca(analise, titulo=None):
    partes = [
        titulo or "",
        analise.descricao,
        "Estilo: " + ", ".join(analise.estilo),
        "Iluminação: " + analise.iluminacao,
        "Composição: " + analise.composicao,
        "Clima: " + analise.clima,
        "Tags: " + ", ".join(analise.tags)
    ]

    return "\n".join(p for p in partes if p)


def gerar_embedding(texto, consulta=False):
    # O Gemini gera vetores diferentes para o documento indexado e para a pergunta de busca
    tipo = "RETRIEVAL_QUERY" if consulta else "RETRIEVAL_DOCUMENT"

    response = cliente().models.embed_content(
        model=MODELO_EMBEDDING,
        contents=texto,
        config=types.EmbedContentConfig(task_type=tipo)
    )

    return response.embeddings[0].values
