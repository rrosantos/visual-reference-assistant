import os

import requests
from dotenv import load_dotenv
from fastapi import Header, FastAPI, HTTPException
from typing import Optional

load_dotenv()

app = FastAPI(
    title="Visual Reference Assistant",
    version="1.0.0"
)

PINTEREST_API = "https://api.pinterest.com/v5"
TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
APP_API_KEY = os.getenv("APP_API_KEY")

def pinterest_get(endpoint, params=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
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

def verificar_api_key(x_api_key: str = Header(...)):
    if x_api_key != APP_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="API key inválida"
        )

@app.get("/boards")
def listar_pastas(x_api_key: str = Header(...)):
    verificar_api_key(x_api_key)
    return pinterest_get("/boards")


@app.get("/boards/{board_id}/pins")
def listar_pins(
    board_id: str,
    bookmark: Optional[str] = None,
    page_size: int = 25,
    x_api_key: str = Header(...)
):
    verificar_api_key(x_api_key)
    params = {
        "page_size": page_size
    }

    if bookmark:
        params["bookmark"] = bookmark

    return pinterest_get(
        f"/boards/{board_id}/pins",
        params=params
    )


@app.get("/pins/{pin_id}")
def buscar_pin(pin_id: str, x_api_key: str = Header(...)):
    verificar_api_key(x_api_key)
    return pinterest_get(f"/pins/{pin_id}")