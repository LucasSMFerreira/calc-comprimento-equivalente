import pytest

from app.dados.importador import importar_planilha
from app.dados.repositorio import Repositorio
from app.dominio.erros import ErroDominio


@pytest.fixture
def repo(tmp_path):
    return Repositorio(tmp_path / "teste.db")


def test_salva_e_carrega_a_mesma_tabela(repo, importacao):
    versao = repo.salvar_versao("Professor", "planilha.xlsx", importacao)
    assert repo.carregar_tabela(versao).valores == importacao.tabela.valores


def test_so_uma_versao_fica_ativa(repo, importacao):
    v1 = repo.salvar_versao("v1", "a.xlsx", importacao)
    v2 = repo.salvar_versao("v2", "b.xlsx", importar_planilha(repo.exportar_xlsx(v1)))
    repo.ativar(v1)
    repo.ativar(v2)
    assert repo.versao_ativa()["id"] == v2
    assert [v["ativa"] for v in repo.listar_versoes()] == [True, False]


def test_nao_importa_a_mesma_planilha_duas_vezes(repo, importacao):
    repo.salvar_versao("v1", "a.xlsx", importacao)
    with pytest.raises(ErroDominio, match="já foi importada"):
        repo.salvar_versao("v1 de novo", "a.xlsx", importacao)


def test_exportar_e_reimportar_mantem_valores_e_fotos(repo, importacao):
    versao = repo.salvar_versao("v1", "a.xlsx", importacao)
    reimportada = importar_planilha(repo.exportar_xlsx(versao))
    assert reimportada.valida
    assert reimportada.tabela.valores == importacao.tabela.valores
    assert len(reimportada.fotos) == 64


def test_dados_continuam_depois_de_reabrir(tmp_path, importacao):
    caminho = tmp_path / "persistente.db"
    versao = Repositorio(caminho).salvar_versao("v1", "a.xlsx", importacao)
    assert Repositorio(caminho).carregar_tabela(versao).valores == importacao.tabela.valores