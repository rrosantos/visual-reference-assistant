# Visual Reference Assistant

Assistente de IA para referências visuais salvas no Pinterest. Cada imagem é analisada pelo
**Gemini** (estilo, paleta, iluminação, composição e clima) e vira um vetor de busca. Assim dá para
encontrar inspiração por descrição ("luz quente, clima nostálgico") e conversar com um agente que
decide sozinho quando listar pastas, indexar pins ou buscar referências.

<!-- TODO: GIF da tela /app funcionando -->

## Como funciona

```
Pinterest API ──► pinterest.py ──► imagem do pin
                                        │
                                        ▼
                          ia.py: Gemini multimodal
                     (saída estruturada com Pydantic)
                                        │
                     análise ──► embedding (gemini-embedding-2)
                                        │
                                        ▼
                         banco.py: SQLite + similaridade de cosseno
                                        ▲
         agente.py: Gemini com tool calling ┘  ◄── POST /chat ◄── static/app.html
```

- **Análise multimodal:** o modelo recebe a imagem e devolve um JSON validado pelo schema
  `AnaliseVisual`, em vez de texto livre.
- **Busca semântica:** o texto da análise vira embedding (`RETRIEVAL_DOCUMENT`) e a pergunta vira
  outro (`RETRIEVAL_QUERY`); a busca ordena por similaridade de cosseno.
- **Agente:** quatro funções Python (`listar_pastas`, `buscar_referencias`, `indexar_pasta`,
  `detalhar_referencia`) viram ferramentas pelo *automatic function calling* do SDK `google-genai`.
  As instruções do agente proíbem inventar pins e exigem confirmação antes de gastar chamadas
  indexando uma pasta.
- **Indexação idempotente:** pins já analisados não são reprocessados, e um pin com erro não
  interrompe a pasta inteira.

## Rodando localmente

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env   # preencha as chaves
venv/bin/uvicorn main:app --reload
```

Abra `http://localhost:8000/app`, informe a `APP_API_KEY`, carregue as pastas e indexe uma.
A documentação da API fica em `http://localhost:8000/docs`.

Com Docker:

```bash
docker build -t visual-reference-assistant .
docker run --env-file .env -p 8000:8000 -v "$PWD/dados:/app/dados" visual-reference-assistant
```

## Endpoints

Todos exigem o header `x-api-key`.

| Método | Rota | O que faz |
|---|---|---|
| GET | `/boards` | Lista as pastas do Pinterest |
| GET | `/boards/{board_id}/pins` | Lista os pins de uma pasta |
| GET | `/pins/{pin_id}` | Detalhes de um pin |
| POST | `/pins/{pin_id}/analise` | Analisa um pin com o Gemini (`?forcar=true` refaz) |
| POST | `/boards/{board_id}/indexar` | Analisa os pins de uma pasta (`?limite=25`) |
| GET | `/referencias/busca?q=...` | Busca semântica nos pins indexados |
| POST | `/chat` | Conversa com o agente (`{"mensagem": "...", "conversa_id": null}`) |

## Limitações e próximos passos

- A busca é força bruta em Python: ótima para centenas ou alguns milhares de pins; acima disso,
  trocar por `sqlite-vec` ou `pgvector`.
- As conversas do agente ficam em memória e somem ao reiniciar o servidor.
- O plano gratuito do Gemini limita as requisições por minuto; indexar pastas grandes pode
  precisar de pausas entre os pins.
- Os modelos do Gemini são aposentados com frequência e às vezes respondem 503 em picos de
  demanda; troque o modelo pela variável `GEMINI_MODEL` sem mexer no código.
- Ideias: busca por imagem (enviar uma foto e achar parecidas), geração de moodboard e
  avaliação da qualidade da busca com um conjunto de perguntas rotuladas.

## Stack

Python 3.12 · FastAPI · Gemini (`google-genai`) · Pydantic · SQLite · Docker
