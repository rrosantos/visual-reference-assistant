import os

import requests
from fastapi import HTTPException

PINTEREST_API = "https://api.pinterest.com/v5"

# Ordem de preferência dos tamanhos de imagem que a API do Pinterest devolve
TAMANHOS_IMAGEM = ["1200x", "600x", "originals", "400x300", "150x150"]


def pinterest_get(endpoint, params=None):
    headers = {
        "Authorization": f"Bearer {os.getenv('PINTEREST_ACCESS_TOKEN')}",
        "Accept": "application/json"
    }

    response = requests.get(
        f"{PINTEREST_API}{endpoint}",
        headers=headers,
        params=params,
        timeout=30
    )

    if not response.ok:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json()
        )

    return response.json()


def listar_pastas():
    return pinterest_get("/boards")


def listar_pins(board_id, bookmark=None, page_size=25):
    params = {"page_size": page_size}

    if bookmark:
        params["bookmark"] = bookmark

    return pinterest_get(f"/boards/{board_id}/pins", params=params)


def buscar_pin(pin_id):
    return pinterest_get(f"/pins/{pin_id}")


def url_da_imagem(pin):
    imagens = (pin.get("media") or {}).get("images") or {}

    for tamanho in TAMANHOS_IMAGEM:
        if tamanho in imagens:
            return imagens[tamanho]["url"]

    return None


def baixar_imagem(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    mime_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]

    return response.content, mime_type
