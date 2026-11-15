# Receita do PyInstaller para gerar o executável: pyinstaller --noconfirm calculadora.spec
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ["desktop.py"],
    datas=[
        ("app/static", "app/static"),  # interface (HTML, CSS, JS)
        ("data/tabela_padrao.xlsx", "data"),  # tabela do professor, importada na primeira execução
        *collect_data_files("fpdf"),
    ],
    # o uvicorn e o FastAPI carregam alguns módulos pelo nome, em tempo de execução
    hiddenimports=[*collect_submodules("uvicorn"), "python_multipart"],
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="CalculadoraHidraulica",
    console=True,  # a janela preta mostra o endereço e fecha a calculadora quando fechada
    upx=False,
)
