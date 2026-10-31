import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

import openpyxl

from app.dominio.tabela import MATERIAIS, TRECHO_RETO, Conexao, TabelaEquivalentes

PRIMEIRA_COLUNA_DIAMETRO = 3  # coluna D (A=0, B=1, C=2, D=3)


@dataclass
class Importacao:
    tabela: TabelaEquivalentes | None
    fotos: dict[tuple[str, str], tuple[bytes, str]] = field(default_factory=dict)
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    hash: str = ""

    @property
    def valida(self) -> bool:
        return self.tabela is not None and not self.erros


def limpar_texto(valor) -> str:
    """'Joelho 90°\\ncom Redução ' -> 'Joelho 90° com Redução'"""
    return " ".join(str(valor).split())


def gerar_id(nome: str) -> str:
    """'Joelho 90° com Redução' -> 'joelho-90-com-reducao'"""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def ler_numero(valor) -> Decimal:
    """Aceita 1, 0.35 e o texto '1,20' (vírgula decimal, como está na planilha)."""
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    if isinstance(valor, str):
        return Decimal(valor.strip().replace(",", "."))
    raise InvalidOperation


def br(numero: Decimal) -> str:
    return str(numero).replace(".", ",")


def importar_planilha(conteudo: bytes) -> Importacao:
    resultado = Importacao(tabela=None, hash=hashlib.sha256(conteudo).hexdigest())
    try:
        planilha = openpyxl.load_workbook(io.BytesIO(conteudo)).worksheets[0]
    except Exception:
        resultado.erros.append("O arquivo não é uma planilha .xlsx válida.")
        return resultado

    cabecalho = [limpar_texto(c.value) if c.value is not None else "" for c in planilha[1]]
    if len(cabecalho) <= PRIMEIRA_COLUNA_DIAMETRO or cabecalho[2].lower() != "material":
        resultado.erros.append(
            "Cabeçalho inesperado. A linha 1 deve ser: Descrição | Foto | Material | diâmetros..."
        )
        return resultado
    diametros = [d for d in cabecalho[PRIMEIRA_COLUNA_DIAMETRO:] if d]

    conexoes: dict[str, Conexao] = {}
    valores: dict[tuple[str, str, str], Decimal] = {}
    linha_de: dict[int, tuple[str, str]] = {}

    for linha in planilha.iter_rows(min_row=2):
        if linha[0].value is None:
            continue
        nome = limpar_texto(linha[0].value)
        conexao_id = gerar_id(nome)
        material = limpar_texto(linha[2].value or "")
        numero_linha = linha[0].row

        if material not in MATERIAIS:
            resultado.erros.append(f"Linha {numero_linha}: material '{material}' inválido (use PVC ou Metal).")
            continue
        if (conexao_id, material) in linha_de.values():
            resultado.erros.append(f"Linha {numero_linha}: {nome} ({material}) aparece duas vezes.")
            continue

        conexoes.setdefault(conexao_id, Conexao(conexao_id, nome))
        linha_de[numero_linha] = (conexao_id, material)

        anterior = None
        for i, diametro in enumerate(diametros):
            celula = linha[PRIMEIRA_COLUNA_DIAMETRO + i]
            try:
                valor = ler_numero(celula.value)
            except InvalidOperation:
                resultado.erros.append(f"Célula {celula.coordinate}: '{celula.value}' não é um número.")
                continue
            if valor <= 0:
                resultado.erros.append(f"Célula {celula.coordinate}: o valor precisa ser maior que zero.")
                continue
            valores[(conexao_id, material, diametro)] = valor
            if anterior and valor < anterior[1]:
                resultado.avisos.append(
                    f"{nome} ({material}): {diametro} vale {br(valor)} m, menor que "
                    f"{anterior[0]} ({br(anterior[1])} m). Confira a célula {celula.coordinate}."
                )
            anterior = (diametro, valor)

    if TRECHO_RETO not in conexoes:
        resultado.erros.append("A planilha precisa ter a linha 'Trecho Reto' (valor 1 em todos os diâmetros).")

    for imagem in planilha._images:  # fotos da coluna B
        numero_linha = imagem.anchor._from.row + 1
        if numero_linha in linha_de:
            resultado.fotos[linha_de[numero_linha]] = (imagem._data(), imagem.format or "png")

    if not resultado.erros:
        resultado.tabela = TabelaEquivalentes(diametros, list(conexoes.values()), valores)
    return resultado

def comparar(antiga: TabelaEquivalentes, nova: TabelaEquivalentes, limite: int = 30) -> list[str]:
    """Lista legível do que muda entre duas tabelas (usada na pré-visualização)."""
    mudancas = []
    for chave in sorted(set(antiga.valores) | set(nova.valores)):
        velho, novo = antiga.valores.get(chave), nova.valores.get(chave)
        if velho == novo:
            continue
        conexao_id, material, diametro = chave
        descricao = f"{conexao_id} ({material}) {diametro}"
        if velho is None:
            mudancas.append(f"Novo: {descricao} = {br(novo)} m")
        elif novo is None:
            mudancas.append(f"Removido: {descricao}")
        else:
            mudancas.append(f"Alterado: {descricao}: {br(velho)} -> {br(novo)} m")
    if len(mudancas) > limite:
        return mudancas[:limite] + [f"... e mais {len(mudancas) - limite} mudanças."]
    return mudancas