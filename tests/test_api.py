EXERCICIO_5 = {
    "diametro": '3/4"',
    "itens": [
        {"conexao_id": "saida-entrada-de-canalizacao", "material": "PVC", "quantidade": 1},
        {"conexao_id": "joelho-90", "material": "PVC", "quantidade": 5},
        {"conexao_id": "registro-de-gaveta-aberto", "material": "Metal", "quantidade": 2},
        {"conexao_id": "trecho-reto", "material": "PVC", "quantidade": 10.7},
    ],
}
ADMIN = {"X-Admin-Token": "senha-teste"}


def test_primeira_execucao_carrega_a_tabela_do_professor(cliente):
    tabela = cliente.get("/api/tabela").json()
    assert tabela["versao"]["nome"] == "Tabela do professor"
    assert len(tabela["conexoes"]) == 35


def test_calcular_exercicio_5(cliente):
    resposta = cliente.post("/api/calcular", json=EXERCICIO_5)
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 17.8


def test_erro_de_regra_vira_422_com_mensagem(cliente):
    pedido = {"diametro": '3/4"', "itens": [{"conexao_id": "registro-de-globo", "material": "PVC",
                                              "quantidade": 1}]}
    resposta = cliente.post("/api/calcular", json=pedido)
    assert resposta.status_code == 422
    assert "Registro de Globo" in resposta.json()["detail"]


def test_foto_da_conexao(cliente):
    assert cliente.get("/api/fotos/1/joelho-90/PVC").status_code == 200
    assert cliente.get("/api/fotos/1/abacaxi/PVC").status_code == 404


def test_trocar_tabela_exige_senha(cliente):
    planilha = cliente.get("/api/tabelas/1/exportar").content
    arquivos = {"arquivo": ("nova.xlsx", planilha)}
    assert cliente.post("/api/tabelas/previa", files=arquivos).status_code == 401
    assert cliente.post("/api/tabelas/previa", files=arquivos, headers=ADMIN).json()["valida"]


def test_salvar_nova_tabela_e_voltar_para_antiga(cliente):
    planilha = cliente.get("/api/tabelas/1/exportar").content
    nova = cliente.post("/api/tabelas", data={"nome": "Cópia"},
                        files={"arquivo": ("nova.xlsx", planilha)}, headers=ADMIN).json()
    assert cliente.get("/api/tabela").json()["versao"]["id"] == nova["id"]
    cliente.post("/api/tabelas/1/ativar", headers=ADMIN)
    assert cliente.get("/api/tabela").json()["versao"]["id"] == 1