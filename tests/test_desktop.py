import desktop


def test_pasta_de_dados_fica_no_localappdata(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    pasta = desktop.pasta_de_dados()
    assert pasta == tmp_path / "CalculadoraComprimentoEquivalente"
    assert pasta.is_dir()


def test_porta_livre_e_um_numero_valido():
    assert 0 < desktop.porta_livre() < 65536
