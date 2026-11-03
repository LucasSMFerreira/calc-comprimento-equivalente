from dataclasses import dataclass, field
from decimal import Decimal

from app.dominio.tabela import TRECHO_RETO, TabelaEquivalentes
from app.entrada.reconhecedor import reconhecer_conexao, reconhecer_material


@dataclass
class ItemReconhecido:
    conexao_id: str
    material: str
    quantidade: Decimal
    original: str


@dataclass
class Leitura:
    """O que foi entendido de uma entrada (planilha ou texto) antes do usuário confirmar."""

    itens: list[ItemReconhecido] = field(default_factory=list)
    pendentes: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    diametro: str | None = None


def montar_item(descricao: str, material_texto: str, quantidade: Decimal,
                tabela: TabelaEquivalentes, leitura: Leitura) -> None:
    """Reconhece uma linha e coloca em itens (deu certo) ou pendentes (não deu)."""
    original = f"{quantidade} x {descricao} {material_texto}".strip()
    conexao_id = reconhecer_conexao(descricao, tabela)
    if conexao_id is None:
        leitura.pendentes.append(f"{original}: conexão não reconhecida")
        return
    if quantidade <= 0:
        leitura.pendentes.append(f"{original}: quantidade inválida")
        return

    disponiveis = tabela.materiais_de(conexao_id)
    material = reconhecer_material(f"{material_texto} {descricao}") or disponiveis[0]
    if material not in disponiveis:
        leitura.avisos.append(f"{tabela.nome_de(conexao_id)} só existe em {disponiveis[0]}; usei {disponiveis[0]}.")
        material = disponiveis[0]
    if conexao_id != TRECHO_RETO and quantidade != quantidade.to_integral_value():
        leitura.pendentes.append(f"{original}: conexão precisa de quantidade inteira")
        return
    leitura.itens.append(ItemReconhecido(conexao_id, material, quantidade, original))