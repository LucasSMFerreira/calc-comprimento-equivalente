from decimal import Decimal

import httpx

from app import config
from app.dominio.tabela import TabelaEquivalentes
from app.entrada.itens import ItemReconhecido, Leitura


class IAIndisponivel(Exception):
    pass


def interpretar_com_ia(texto: str, tabela: TabelaEquivalentes) -> Leitura:
    """Manda o texto para o serviço de IA no homelab. A IA só devolve itens; quem calcula é o Python."""
    if not config.IA_URL:
        raise IAIndisponivel("A IA não está configurada (IA_URL vazio).")
    pedido = {
        "texto": texto,
        "conexoes": [{"id": c.id, "nome": c.nome} for c in tabela.conexoes],
        "diametros": tabela.diametros,
    }
    try:
        resposta = httpx.post(
            f"{config.IA_URL}/interpretar",
            json=pedido,
            headers={"X-Token": config.IA_TOKEN},
            timeout=180,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except (httpx.HTTPError, ValueError) as erro:
        raise IAIndisponivel(f"A IA não respondeu: {erro}") from erro

    # Nunca confie cegamente na IA: confere cada item contra a tabela.
    leitura = Leitura(diametro=dados.get("diametro") if dados.get("diametro") in tabela.diametros else None)
    ids = {c.id for c in tabela.conexoes}
    for item in dados.get("itens", []):
        conexao_id, material = item.get("conexao_id"), item.get("material")
        quantidade = Decimal(str(item.get("quantidade", 0)))
        descricao = f"{quantidade} x {conexao_id} {material}"
        if conexao_id not in ids or quantidade <= 0:
            leitura.pendentes.append(f"{descricao}: resposta inválida da IA")
        elif material not in tabela.materiais_de(conexao_id):
            leitura.pendentes.append(f"{descricao}: material não existe para essa conexão")
        else:
            leitura.itens.append(ItemReconhecido(conexao_id, material, quantidade, f"IA: {descricao}"))
    return leitura