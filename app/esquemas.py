from decimal import Decimal

from pydantic import BaseModel, Field


class ItemEntrada(BaseModel):
    conexao_id: str
    material: str
    quantidade: Decimal = Field(gt=0)


class PedidoCalculo(BaseModel):
    diametro: str
    itens: list[ItemEntrada] = []