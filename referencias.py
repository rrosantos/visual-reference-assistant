import banco
import ia
import pinterest


def indexar_pin(pin, board_id=None, forcar=False):
    """Analisa a imagem do pin com o Gemini e guarda a análise e o embedding."""
    pin_id = pin["id"]

    if not forcar:
        existente = banco.buscar(pin_id)
        if existente:
            return existente

    imagem_url = pinterest.url_da_imagem(pin)
    if not imagem_url:
        raise ValueError(f"O pin {pin_id} não tem imagem")

    imagem, mime_type = pinterest.baixar_imagem(imagem_url)
    titulo = pin.get("title") or pin.get("description")

    analise = ia.analisar_imagem(imagem, mime_type, titulo)
    embedding = ia.gerar_embedding(ia.texto_para_busca(analise, titulo))

    banco.salvar(
        pin_id=pin_id,
        board_id=board_id or pin.get("board_id"),
        titulo=titulo,
        link=pin.get("link"),
        imagem_url=imagem_url,
        analise=analise.model_dump(),
        embedding=embedding
    )

    return banco.buscar(pin_id)


def indexar_pin_por_id(pin_id, forcar=False):
    return indexar_pin(pinterest.buscar_pin(pin_id), forcar=forcar)


def indexar_pasta(board_id, limite=25):
    resultado = {"indexados": 0, "ja_existiam": 0, "erros": []}
    pins = pinterest.listar_pins(board_id, page_size=min(limite, 100)).get("items", [])

    for pin in pins[:limite]:
        if banco.buscar(pin["id"]):
            resultado["ja_existiam"] += 1
            continue

        # Um pin com problema (vídeo, imagem fora do ar, limite da API) não derruba a pasta inteira
        try:
            indexar_pin(pin, board_id)
            resultado["indexados"] += 1
        except Exception as erro:
            resultado["erros"].append({"pin_id": pin["id"], "erro": str(erro)})

    return resultado


def buscar_referencias(consulta, limite=6, board_id=None):
    vetor = ia.gerar_embedding(consulta, consulta=True)

    return banco.mais_parecidas(vetor, limite, board_id)
