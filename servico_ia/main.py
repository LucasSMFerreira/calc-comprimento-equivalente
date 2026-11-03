"""Serviço de IA que roda no homelab, ao lado do Ollama.

Recebe um texto livre e devolve itens estruturados. Não faz conta nenhuma.
"""
import hmac
import json
import os

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODELO = os.getenv("MODELO", "qwen2.5:1.5b")
IA_TOKEN = os.getenv("IA_TOKEN", "")

PROMPT = """Você transforma a descrição de uma instalação hidráulica em uma lista de itens.

Conexões disponíveis (id: nome):
{catalogo}

Regras:
- Use somente os ids da lista acima.
- "cotovelo" é o mesmo que "joelho". "Entrada normal" é "saida-entrada-de-canalizacao".
- Tubo, cano ou trecho reto usa o id "trecho-reto" e a quantidade é em metros.
- material é "PVC" ou "Metal" (aço, ferro, cobre, bronze e galvanizado são "Metal").
  Se o texto não disser o material, use "PVC".
- diametro: um destes valores {diametros}, ou "" se o texto não disser.

Texto: {texto}"""


class Conexao(BaseModel):
    id: str
    nome: str


class Pedido(BaseModel):
    texto: str = Field(min_length=3, max_length=2000)
    conexoes: list[Conexao]
    diametros: list[str]


def montar_esquema(ids: list[str], diametros: list[str]) -> dict:
    """JSON Schema: o Ollama obriga o modelo a responder exatamente neste formato."""
    return {
        "type": "object",
        "properties": {
            "diametro": {"type": "string", "enum": [*diametros, ""]},
            "itens": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "conexao_id": {"type": "string", "enum": ids},
                        "material": {"type": "string", "enum": ["PVC", "Metal"]},
                        "quantidade": {"type": "number"},
                    },
                    "required": ["conexao_id", "material", "quantidade"],
                },
            },
        },
        "required": ["diametro", "itens"],
    }


app = FastAPI(title="Serviço de IA da calculadora")


@app.get("/saude")
def saude():
    return {"status": "ok", "modelo": MODELO}


@app.post("/interpretar")
def interpretar(pedido: Pedido, x_token: str = Header(default="")):
    if not IA_TOKEN or not hmac.compare_digest(x_token, IA_TOKEN):
        raise HTTPException(401, "Token inválido.")
    catalogo = "\n".join(f"- {c.id}: {c.nome}" for c in pedido.conexoes)
    prompt = PROMPT.format(catalogo=catalogo, diametros=pedido.diametros, texto=pedido.texto)
    try:
        resposta = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": MODELO,
                "messages": [{"role": "user", "content": prompt}],
                "format": montar_esquema([c.id for c in pedido.conexoes], pedido.diametros),
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=170,
        )
        resposta.raise_for_status()
        return json.loads(resposta.json()["message"]["content"])
    except (httpx.HTTPError, KeyError, json.JSONDecodeError) as erro:
        raise HTTPException(502, f"O Ollama não respondeu direito: {erro}") from erro