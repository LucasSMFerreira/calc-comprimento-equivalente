from dataclasses import dataclass
from decimal import Decimal

from app.dominio.erros import ErroDominio

MATERIAIS = ("PVC", "Metal")
TRECHO_RETO = "trecho-reto"  # tubo reto: L_eq = 1, a quantidade é em metros


@dataclass(frozen=True)
class Conexao:
    id: str
    nome: str


@dataclass
class TabelaEquivalentes:
    """Tabela de comprimentos equivalentes, em metros.

    valores[(conexao_id, material, diametro)] = L_eq unitário
    """

    diametros: list[str]
    conexoes: list[Conexao]
    valores: dict[tuple[str, str, str], Decimal]

    def nome_de(self, conexao_id: str) -> str:
        for conexao in self.conexoes:
            if conexao.id == conexao_id:
                return conexao.nome
        raise ErroDominio(f"Conexão '{conexao_id}' não existe na tabela.")

    def materiais_de(self, conexao_id: str) -> list[str]:
        return [
            material
            for material in MATERIAIS
            if any((conexao_id, material, d) in self.valores for d in self.diametros)
        ]

    def valor(self, conexao_id: str, material: str, diametro: str) -> Decimal:
        chave = (conexao_id, material, diametro)
        if chave not in self.valores:
            nome = self.nome_de(conexao_id)
            raise ErroDominio(f"A tabela não tem valor para {nome} em {material} de {diametro}.")
        return self.valores[chave]