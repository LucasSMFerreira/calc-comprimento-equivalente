import httpx

from app import config

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


def test_memorial_em_pdf(cliente):
    resposta = cliente.post("/api/memorial", json=EXERCICIO_5)
    assert resposta.headers["content-type"] == "application/pdf"
    assert resposta.content.startswith(b"%PDF")


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


def test_saude_mostra_versao_ativa(cliente):
    assert cliente.get("/api/saude").json() == {
        "status": "ok", "versao_ativa": 1, "ia_configurada": False, "admin_protegido": True}


def test_valores_de_uma_conexao(cliente):
    dados = cliente.get("/api/tabela/joelho-90").json()
    assert dados["nome"] == "Joelho 90°"
    assert dados["valores"]["PVC"]['3/4"'] == 1.2
    assert list(dados["valores"]) == ["PVC", "Metal"]


def test_conexao_inexistente_da_404(cliente):
    assert cliente.get("/api/tabela/abacaxi").status_code == 404


def test_modelo_e_planilha_de_itens(cliente):
    modelo = cliente.get("/api/itens/modelo").content
    resposta = cliente.post("/api/itens/planilha", files={"arquivo": ("itens.xlsx", modelo)}).json()
    assert [i["conexao_id"] for i in resposta["itens"]] == ["joelho-90", "trecho-reto"]


def test_texto_do_exercicio_5_pela_api(cliente):
    texto = "1 entrada normal, 5 cotovelos 90, 2 registros de gaveta de metal e 10,7 m de tubo"
    resposta = cliente.post("/api/itens/texto", json={"texto": texto}).json()
    assert len(resposta["itens"]) == 4
    assert resposta["pendentes"] == []


def test_texto_sem_ia_usa_so_as_regras(cliente):
    resposta = cliente.post("/api/itens/texto", json={"texto": "5 joelhos 90 e 3 mangueiras"}).json()
    assert resposta["usou_ia"] is False
    assert len(resposta["itens"]) == 1
    assert "IA não está configurada" in resposta["avisos"][0]


def test_texto_com_ia_simulada(cliente, monkeypatch):
    monkeypatch.setattr(config, "IA_URL", "http://ia-falsa")

    def post_falso(url, **kwargs):
        dados = {"diametro": '1"', "itens": [
            {"conexao_id": "joelho-90", "material": "Metal", "quantidade": 2},
            {"conexao_id": "inventado", "material": "PVC", "quantidade": 1}]}
        return httpx.Response(200, json=dados, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post_falso)
    resposta = cliente.post("/api/itens/texto", json={"texto": "duas mangueiras de ferro"}).json()
    assert resposta["usou_ia"] is True
    assert resposta["diametro"] == '1"'
    assert resposta["itens"][0]["conexao_id"] == "joelho-90"
    assert "resposta inválida" in resposta["pendentes"][0]  # a IA inventou; o sistema barrou


def test_usar_ia_forca_a_ia_mesmo_quando_as_regras_entendem(cliente, monkeypatch):
    monkeypatch.setattr(config, "IA_URL", "http://ia-falsa")
    chamadas = []

    def post_falso(url, **kwargs):
        chamadas.append(url)
        return httpx.Response(200, json={"diametro": "", "itens": []}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post_falso)
    cliente.post("/api/itens/texto", json={"texto": "5 joelhos 90", "usar_ia": True})
    assert chamadas == ["http://ia-falsa/interpretar"]


def test_saude_informa_se_admin_tem_senha(cliente):
    assert cliente.get("/api/saude").json()["admin_protegido"] is True


def test_sem_admin_token_gerenciar_tabela_e_livre(cliente, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    planilha = cliente.get("/api/tabelas/1/exportar").content
    resposta = cliente.post("/api/tabelas/previa", files={"arquivo": ("nova.xlsx", planilha)})
    assert resposta.status_code == 200
    assert cliente.get("/api/saude").json()["admin_protegido"] is False