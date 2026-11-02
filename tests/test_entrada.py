from decimal import Decimal

import pytest

from app.entrada.planilha_itens import gerar_modelo, ler_planilha_itens
from app.entrada.reconhecedor import reconhecer_conexao, reconhecer_material
from app.entrada.texto import ler_texto


@pytest.mark.parametrize("texto, esperado", [
    ("Joelho 90", "joelho-90"),
    ("cotovelo 90° raio médio", "joelho-90"),
    ("Joelho 90° com redução", "joelho-90-com-reducao"),
    ("registros de gaveta", "registro-de-gaveta-aberto"),
    ("entrada normal", "saida-entrada-de-canalizacao"),
    ("tubo", "trecho-reto"),
    ("tê de saída lateral", "te-passagem-lateral"),
    ("abacaxi", None),
])
def test_reconhece_nomes_do_dia_a_dia(tabela, texto, esperado):
    assert reconhecer_conexao(texto, tabela) == esperado


def test_reconhece_material():
    assert reconhecer_material("registro de aço") == "Metal"
    assert reconhecer_material("joelho PVC") == "PVC"
    assert reconhecer_material("joelho") is None


def test_texto_do_exercicio_5(tabela):
    leitura = ler_texto(
        '3/4": 1 entrada normal, 5 cotovelos 90 de PVC, 2 registros de gaveta de metal e 10,7 m de tubo',
        tabela,
    )
    assert leitura.diametro == '3/4"'
    assert [(i.conexao_id, i.material, i.quantidade) for i in leitura.itens] == [
        ("saida-entrada-de-canalizacao", "PVC", Decimal("1")),
        ("joelho-90", "PVC", Decimal("5")),
        ("registro-de-gaveta-aberto", "Metal", Decimal("2")),
        ("trecho-reto", "PVC", Decimal("10.7")),
    ]
    assert leitura.pendentes == []


def test_texto_com_coisa_desconhecida_vai_para_pendentes(tabela):
    leitura = ler_texto("3 mangueiras", tabela)
    assert leitura.itens == []
    assert "mangueiras" in leitura.pendentes[0]


def test_modelo_baixado_pode_ser_lido_de_volta(tabela):
    leitura = ler_planilha_itens(gerar_modelo(tabela), tabela)
    assert [(i.conexao_id, i.quantidade) for i in leitura.itens] == [
        ("joelho-90", Decimal("5")), ("trecho-reto", Decimal("10.7"))]


def test_material_que_nao_existe_vira_aviso(tabela):
    leitura = ler_texto("1 registro de globo de pvc", tabela)
    assert leitura.itens[0].material == "Metal"
    assert "só existe em Metal" in leitura.avisos[0]