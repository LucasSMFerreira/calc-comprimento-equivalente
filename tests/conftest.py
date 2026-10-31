from pathlib import Path

import pytest

from app.dados.importador import importar_planilha

PLANILHA = Path(__file__).resolve().parent.parent / "data" / "tabela_padrao.xlsx"


@pytest.fixture(scope="session")
def importacao():
    return importar_planilha(PLANILHA.read_bytes())


@pytest.fixture(scope="session")
def tabela(importacao):
    return importacao.tabela