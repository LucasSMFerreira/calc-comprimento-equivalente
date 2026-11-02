import io
from decimal import Decimal, InvalidOperation

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

from app.dados.importador import ler_numero
from app.dominio.tabela import TabelaEquivalentes
from app.entrada.itens import Leitura, montar_item
from app.entrada.reconhecedor import normalizar


def gerar_modelo(tabela: TabelaEquivalentes) -> bytes:
    """Planilha modelo com listas suspensas, para o usuário preencher sem errar nomes."""
    livro = openpyxl.Workbook()
    folha = livro.active
    folha.title = "Itens"
    folha.append(["Conexão", "Material", "Quantidade"])
    folha.append(["Joelho 90°", "PVC", 5])
    folha.append(["Trecho Reto", "PVC", 10.7])
    for coluna, largura in zip("ABC", (38, 12, 14)):
        folha.column_dimensions[coluna].width = largura

    lista = livro.create_sheet("Conexões")
    for conexao in tabela.conexoes:
        lista.append([conexao.nome])
    nomes = DataValidation(type="list", formula1=f"='Conexões'!$A$1:$A${len(tabela.conexoes)}")
    materiais = DataValidation(type="list", formula1='"PVC,Metal"')
    folha.add_data_validation(nomes)
    folha.add_data_validation(materiais)
    nomes.add("A2:A200")
    materiais.add("B2:B200")

    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def achar_colunas(cabecalho: list[str]) -> dict[str, int]:
    """Descobre em qual coluna está cada informação, pelo nome do cabeçalho."""
    colunas = {}
    for i, titulo in enumerate(cabecalho):
        if any(p in titulo for p in ("conex", "descri", "item", "peca", "acessorio")):
            colunas.setdefault("descricao", i)
        elif "material" in titulo:
            colunas.setdefault("material", i)
        elif any(p in titulo for p in ("quant", "qtd", "qtde")):
            colunas.setdefault("quantidade", i)
    return colunas


def ler_planilha_itens(conteudo: bytes, tabela: TabelaEquivalentes) -> Leitura:
    leitura = Leitura()
    try:
        folha = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True).worksheets[0]
    except Exception:
        leitura.pendentes.append("O arquivo não é uma planilha .xlsx válida.")
        return leitura

    linhas = list(folha.iter_rows(values_only=True))
    for numero, linha in enumerate(linhas[:10]):  # procura o cabeçalho nas 10 primeiras linhas
        colunas = achar_colunas([normalizar(str(v)) if v is not None else "" for v in linha])
        if "descricao" in colunas and "quantidade" in colunas:
            break
    else:
        leitura.pendentes.append("Não achei as colunas 'Conexão' e 'Quantidade' no início da planilha.")
        return leitura

    for linha in linhas[numero + 1:]:
        descricao = linha[colunas["descricao"]]
        if descricao is None:
            continue
        material = linha[colunas["material"]] if "material" in colunas else ""
        try:
            quantidade = ler_numero(linha[colunas["quantidade"]])
        except InvalidOperation:
            quantidade = Decimal(0)
        montar_item(str(descricao), str(material or ""), quantidade, tabela, leitura)
    return leitura