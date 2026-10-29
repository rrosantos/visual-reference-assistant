import json
import math
import os
import sqlite3
from pathlib import Path

CAMINHO = Path(os.getenv("DB_PATH", "dados/referencias.db"))


def conectar():
    CAMINHO.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(CAMINHO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS referencias (
            pin_id TEXT PRIMARY KEY,
            board_id TEXT,
            titulo TEXT,
            link TEXT,
            imagem_url TEXT,
            analise TEXT NOT NULL,
            embedding TEXT NOT NULL,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    return conexao


def salvar(pin_id, board_id, titulo, link, imagem_url, analise, embedding):
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT OR REPLACE INTO referencias
                (pin_id, board_id, titulo, link, imagem_url, analise, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (pin_id, board_id, titulo, link, imagem_url, json.dumps(analise), json.dumps(embedding))
        )


def buscar(pin_id):
    with conectar() as conexao:
        linha = conexao.execute("SELECT * FROM referencias WHERE pin_id = ?", (pin_id,)).fetchone()

    return _formatar(linha) if linha else None


def similaridade(a, b):
    produto = sum(x * y for x, y in zip(a, b))
    normas = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))

    return produto / normas if normas else 0.0


def mais_parecidas(vetor, limite=6, board_id=None):
    # Busca por força bruta: suficiente para alguns milhares de pins
    sql = "SELECT * FROM referencias"
    params = ()

    if board_id:
        sql += " WHERE board_id = ?"
        params = (board_id,)

    with conectar() as conexao:
        linhas = conexao.execute(sql, params).fetchall()

    pontuadas = [
        (similaridade(vetor, json.loads(linha["embedding"])), linha)
        for linha in linhas
    ]
    pontuadas.sort(key=lambda item: item[0], reverse=True)

    return [
        {**_formatar(linha), "similaridade": round(nota, 3)}
        for nota, linha in pontuadas[:limite]
    ]


def total():
    with conectar() as conexao:
        return conexao.execute("SELECT COUNT(*) FROM referencias").fetchone()[0]


def total_por_pasta():
    with conectar() as conexao:
        linhas = conexao.execute(
            "SELECT board_id, COUNT(*) AS total FROM referencias GROUP BY board_id"
        ).fetchall()

    return {linha["board_id"]: linha["total"] for linha in linhas}


def _formatar(linha):
    return {
        "pin_id": linha["pin_id"],
        "board_id": linha["board_id"],
        "titulo": linha["titulo"],
        "link": linha["link"],
        "imagem_url": linha["imagem_url"],
        "analise": json.loads(linha["analise"])
    }
