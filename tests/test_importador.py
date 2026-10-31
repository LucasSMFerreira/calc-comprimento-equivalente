import io
from decimal import Decimal

import openpyxl

from app.dados.importador import gerar_id, importar_planilha, ler_numero


def test_planilha_do_professor_e_valida(importacao):
    assert importacao.valida
    assert len(importacao.tabela.conexoes) == 35
    assert len(importacao.tabela.diametros) == 17
    assert len(importacao.tabela.valores) == 64 * 17
    assert len(importacao.fotos) == 64


def test_valores_batem_com_a_planilha(tabela):
    assert tabela.valor("joelho-90", "PVC", '3/4"') == Decimal("1.20")
    assert tabela.valor("registro-de-globo", "Metal", '14"') == Decimal("120.90")
    assert tabela.valor("trecho-reto", "Metal", '1/4"') == Decimal("1")


def test_conexao_que_so_existe_em_metal(tabela):
    assert tabela.materiais_de("registro-de-globo") == ["Metal"]
    assert tabela.materiais_de("filtro-y") == ["PVC"]


def test_avisa_valores_suspeitos(importacao):
    assert any("Curva de Transposição (Metal)" in aviso for aviso in importacao.avisos)


def test_ler_numero_aceita_virgula():
    assert ler_numero("1,20") == Decimal("1.20")
    assert ler_numero(1) == Decimal("1")


def test_gerar_id():
    assert gerar_id("Joelho 90°\ncom Redução") == "joelho-90-com-reducao"


def test_arquivo_que_nao_e_excel():
    resultado = importar_planilha(b"isto nao e um excel")
    assert not resultado.valida
    assert "xlsx" in resultado.erros[0]


def planilha(linhas):
    livro = openpyxl.Workbook()
    for linha in linhas:
        livro.active.append(linha)
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def test_erros_apontam_a_celula():
    conteudo = planilha([
        ["Descrição", "Foto", "Material", '1/2"', '3/4"'],
        ["Joelho 90°", None, "PVC", "1,00", "abc"],
        ["Trecho Reto", None, "Plástico", 1, 1],
    ])
    resultado = importar_planilha(conteudo)
    assert not resultado.valida
    assert any("E2" in erro for erro in resultado.erros)
    assert any("Plástico" in erro for erro in resultado.erros)