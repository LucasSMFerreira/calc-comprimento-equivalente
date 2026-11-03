import re

from app.dados.importador import ler_numero
from app.dominio.tabela import TabelaEquivalentes
from app.entrada.itens import Leitura, montar_item

# "5 joelhos 90 de pvc" -> quantidade=5, resto="joelhos 90 de pvc"
# "10,7 m de tubo"      -> quantidade=10,7, resto="tubo"
PADRAO_ITEM = re.compile(
    r"^(\d+(?:[.,]\d+)?)\s*(?:(?:x|m|metros?|un|unid\w*|p[cç]s?)\b)?\s*(?:de\s+)?(.+)$", re.I
)
# separa por ; : quebra de linha, " e ", ou vírgula que NÃO seja decimal (10,7 continua junto)
SEPARADORES = re.compile(r"[;:\n]|,(?!\d)|\s+e\s+")
PADRAO_DIAMETRO = re.compile(r"(\d+\s+\d/\d|\d+/\d+|\d+)\s*(\"|''|pol\w*)", re.I)


def ler_texto(texto: str, tabela: TabelaEquivalentes) -> Leitura:
    """Leitura por regras (sem IA). O que não entender vai para 'pendentes'."""
    leitura = Leitura()
    achado = PADRAO_DIAMETRO.search(texto)
    if achado:
        candidato = f'{" ".join(achado.group(1).split())}"'
        if candidato in tabela.diametros:
            leitura.diametro = candidato
        texto = texto.replace(achado.group(0), " ")

    for parte in SEPARADORES.split(texto):
        parte = parte.strip(" .")
        if not re.search(r"\d", parte):  # sem número não é item (ex.: "Tubulação de")
            continue
        casou = PADRAO_ITEM.match(parte)
        if not casou:
            leitura.pendentes.append(f"{parte}: não achei a quantidade")
            continue
        montar_item(casou.group(2), "", ler_numero(casou.group(1)), tabela, leitura)
    return leitura