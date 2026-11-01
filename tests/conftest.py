from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.dados.importador import importar_planilha

PLANILHA = Path(__file__).resolve().parent.parent / "data" / "tabela_padrao.xlsx"


@pytest.fixture(scope="session")
def importacao():
    return importar_planilha(PLANILHA.read_bytes())


@pytest.fixture(scope="session")
def tabela(importacao):
    return importacao.tabela


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    """App de verdade, mas com banco temporário (cada teste começa do zero)."""
    monkeypatch.setattr(config, "BANCO", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "ADMIN_TOKEN", "senha-teste")
    from app.main import app

    with TestClient(app) as cliente:
        yield cliente