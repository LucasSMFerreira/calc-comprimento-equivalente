from decimal import Decimal

import pytest

from app.dominio.calculo import Item, agrupar, calcular
from app.dominio.diametros import mm_para_polegada
from app.dominio.erros import ErroDominio

EXERCICIO_5 = [
    Item("saida-entrada-de-canalizacao", "PVC", Decimal("1")),
    Item("joelho-90", "PVC", Decimal("5")),
    Item("registro-de-gaveta-aberto", "Metal", Decimal("2")),
    Item("trecho-reto", "PVC", Decimal("10.7")),
]


def test_exercicio_5_dos_slides_da_17_80(tabela):
    resultado = calcular(EXERCICIO_5, '3/4"', tabela)
    assert resultado.total_conexoes == Decimal("7.10")
    assert resultado.total_trechos_retos == Decimal("10.70")
    assert resultado.total == Decimal("17.80")


def test_cada_linha_multiplica_quantidade_pelo_valor_da_tabela(tabela):
    resultado = calcular(EXERCICIO_5, '3/4"', tabela)
    joelho = resultado.linhas[1]
    assert joelho.leq_unitario == Decimal("1.20")
    assert joelho.subtotal == Decimal("6.00")


def test_valor_muda_com_o_diametro(tabela):
    item = [Item("joelho-90", "Metal", Decimal("1"))]
    assert calcular(item, '1"', tabela).total == Decimal("0.94")
    assert calcular(item, '3"', tabela).total == Decimal("2.82")


def test_itens_repetidos_sao_somados():
    itens = [Item("joelho-90", "PVC", Decimal("2")), Item("joelho-90", "PVC", Decimal("3"))]
    assert agrupar(itens) == [Item("joelho-90", "PVC", Decimal("5"))]


def test_lista_vazia_da_zero(tabela):
    assert calcular([], '3/4"', tabela).total == 0


@pytest.mark.parametrize("item, mensagem", [
    (Item("joelho-90", "PVC", Decimal("0")), "maior que zero"),
    (Item("joelho-90", "PVC", Decimal("1.5")), "número inteiro"),
    (Item("registro-de-globo", "PVC", Decimal("1")), "não tem valor"),
    (Item("abacaxi", "PVC", Decimal("1")), "não existe"),
])
def test_itens_invalidos_dao_erro_claro(tabela, item, mensagem):
    with pytest.raises(ErroDominio, match=mensagem):
        calcular([item], '3/4"', tabela)


def test_diametro_inexistente(tabela):
    with pytest.raises(ErroDominio, match="Diâmetro"):
        calcular(EXERCICIO_5, '7"', tabela)


@pytest.mark.parametrize("mm, padrao, esperado", [(25, "pvc", '3/4"'), (25, "dn", '1"'), (110, "pvc", '4"')])
def test_conversao_de_milimetros(mm, padrao, esperado):
    assert mm_para_polegada(mm, padrao) == esperado


def test_milimetro_fora_da_lista():
    with pytest.raises(ErroDominio):
        mm_para_polegada(26, "pvc")