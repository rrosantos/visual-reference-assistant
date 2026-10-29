import os
import secrets
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Carrega o .env antes dos módulos que leem configuração ao serem importados
load_dotenv()

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from google.genai import errors as erros_gemini
from pydantic import BaseModel, Field

import agente
import banco
import pinterest
import referencias

app = FastAPI(
    title="Visual Reference Assistant",
    version="2.0.0"
)


def verificar_api_key(x_api_key: str = Header(...)):
    esperada = os.getenv("APP_API_KEY")

    # compare_digest evita descobrir a chave pelo tempo de resposta
    if not esperada or not secrets.compare_digest(x_api_key, esperada):
        raise HTTPException(
            status_code=401,
            detail="API key inválida"
        )


api = APIRouter(dependencies=[Depends(verificar_api_key)])


class Mensagem(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    conversa_id: Optional[str] = None


def chamar_ia(funcao, *args):
    try:
        return funcao(*args)
    except erros_gemini.APIError as erro:
        raise HTTPException(status_code=502, detail=f"Erro no Gemini: {erro.message}")


@api.get("/boards")
def listar_pastas():
    return pinterest.listar_pastas()


@api.get("/boards/{board_id}/pins")
def listar_pins(board_id: str, bookmark: Optional[str] = None, page_size: int = 25):
    return pinterest.listar_pins(board_id, bookmark, page_size)


@api.get("/pins/{pin_id}")
def buscar_pin(pin_id: str):
    return pinterest.buscar_pin(pin_id)


@api.post("/pins/{pin_id}/analise")
def analisar_pin(pin_id: str, forcar: bool = False):
    return chamar_ia(referencias.indexar_pin_por_id, pin_id, forcar)


@api.post("/boards/{board_id}/indexar")
def indexar_pasta(board_id: str, limite: int = 25):
    return chamar_ia(referencias.indexar_pasta, board_id, max(1, min(limite, 100)))


@api.get("/referencias/busca")
def buscar_referencias(q: str, limite: int = 6, board_id: Optional[str] = None):
    return chamar_ia(referencias.buscar_referencias, q, max(1, min(limite, 30)), board_id)


@api.get("/referencias/total")
def total_referencias():
    return {"total": banco.total(), "por_pasta": banco.total_por_pasta()}


@api.post("/chat")
def conversar(corpo: Mensagem):
    return chamar_ia(agente.conversar, corpo.mensagem, corpo.conversa_id)


app.include_router(api)


@app.get("/app", include_in_schema=False)
def tela():
    return FileResponse(Path(__file__).parent / "static" / "app.html")
