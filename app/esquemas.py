from decimal import Decimal

from pydantic import BaseModel, Field


class ItemEntrada(BaseModel):
    conexao_id: str
    material: str
    quantidade: Decimal = Field(gt=0)
    trechos: list[Decimal] = []


class PedidoCalculo(BaseModel):
    diametro: str
    itens: list[ItemEntrada] = []


class PedidoTexto(BaseModel):
    texto: str = Field(min_length=3, max_length=2000)
    usar_ia: bool = False