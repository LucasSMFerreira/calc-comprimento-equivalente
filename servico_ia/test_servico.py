import json

import httpx
import main
import pytest
from fastapi.testclient import TestClient

PEDIDO = {
    "texto": "5 cotovelos de 3/4",
    "conexoes": [{"id": "joelho-90", "nome": "Joelho 90°"}],
    "diametros": ['3/4"', '1"'],
}


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(main, "IA_TOKEN", "segredo")
    return TestClient(main.app)


def test_sem_token_e_recusado(cliente):
    assert cliente.post("/interpretar", json=PEDIDO).status_code == 401


def test_envia_esquema_e_devolve_json_do_modelo(cliente, monkeypatch):
    enviado = {}

    def post_falso(url, json, timeout):
        enviado.update(json)
        conteudo = '{"diametro": "3/4\\"", "itens": [{"conexao_id": "joelho-90", "material": "PVC", "quantidade": 5}]}'
        return httpx.Response(200, json={"message": {"content": conteudo}}, request=httpx.Request("POST", url))

    monkeypatch.setattr(main.httpx, "post", post_falso)
    resposta = cliente.post("/interpretar", json=PEDIDO, headers={"X-Token": "segredo"})
    assert resposta.json()["itens"][0]["quantidade"] == 5
    esquema = enviado["format"]["properties"]["itens"]["items"]["properties"]
    assert esquema["conexao_id"]["enum"] == ["joelho-90"]  # o modelo só pode escolher ids da tabela
    assert enviado["options"]["temperature"] == 0
    assert "joelho-90: Joelho 90°" in enviado["messages"][0]["content"]
    json.dumps(enviado)  # tudo serializável