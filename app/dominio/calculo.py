from dataclasses import dataclass
from decimal import Decimal

from app.dominio.erros import ErroDominio
from app.dominio.tabela import TRECHO_RETO, TabelaEquivalentes


@dataclass(frozen=True)
class Item:
    conexao_id: str
    material: str
    quantidade: Decimal


@dataclass(frozen=True)
class Linha:
    conexao_id: str
    nome: str
    material: str
    quantidade: Decimal
    leq_unitario: Decimal
    subtotal: Decimal


@dataclass(frozen=True)
class Resultado:
    diametro: str
    linhas: list[Linha]
    total_conexoes: Decimal
    total_trechos_retos: Decimal
    total: Decimal


def agrupar(itens: list[Item]) -> list[Item]:
    """Soma as quantidades de itens repetidos (mesma conexão e mesmo material)."""
    somas: dict[tuple[str, str], Decimal] = {}
    for item in itens:
        chave = (item.conexao_id, item.material)
        somas[chave] = somas.get(chave, Decimal(0)) + item.quantidade
    return [Item(c, m, q) for (c, m), q in somas.items()]


def validar_item(item: Item) -> None:
    if item.quantidade <= 0:
        raise ErroDominio("A quantidade precisa ser maior que zero.")
    eh_inteiro = item.quantidade == item.quantidade.to_integral_value()
    if item.conexao_id != TRECHO_RETO and not eh_inteiro:
        raise ErroDominio("Conexões são contadas em peças: use um número inteiro.")


def calcular(itens: list[Item], diametro: str, tabela: TabelaEquivalentes) -> Resultado:
    """L_total = soma de (quantidade x L_eq unitário) de cada item."""
    if diametro not in tabela.diametros:
        raise ErroDominio(f"Diâmetro {diametro} não existe na tabela.")

    linhas = []
    for item in agrupar(itens):
        validar_item(item)
        leq = tabela.valor(item.conexao_id, item.material, diametro)
        linhas.append(
            Linha(
                conexao_id=item.conexao_id,
                nome=tabela.nome_de(item.conexao_id),
                material=item.material,
                quantidade=item.quantidade,
                leq_unitario=leq,
                subtotal=item.quantidade * leq,
            )
        )

    total_conexoes = sum((ln.subtotal for ln in linhas if ln.conexao_id != TRECHO_RETO), Decimal(0))
    total_retos = sum((ln.subtotal for ln in linhas if ln.conexao_id == TRECHO_RETO), Decimal(0))
    return Resultado(diametro, linhas, total_conexoes, total_retos, total_conexoes + total_retos)