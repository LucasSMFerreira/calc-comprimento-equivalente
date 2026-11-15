"""Versão para desktop: abre a calculadora no navegador, sem instalar nada.

É o ponto de entrada do executável do Windows (gerado pelo PyInstaller no GitHub Actions).
Roda tudo no próprio computador: sem internet, sem senha de admin e sem IA
(o texto livre continua funcionando pelas regras).
"""
import os
import socket
import threading
import webbrowser
from pathlib import Path


def pasta_de_dados() -> Path:
    """Pasta onde o banco fica salvo entre uma execução e outra."""
    base = os.getenv("LOCALAPPDATA") or str(Path.home())
    pasta = Path(base) / "CalculadoraComprimentoEquivalente"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def porta_livre() -> int:
    """Pede ao sistema uma porta que ninguém está usando."""
    with socket.socket() as conexao:
        conexao.bind(("127.0.0.1", 0))
        return conexao.getsockname()[1]


def main() -> None:
    # As variáveis precisam existir ANTES de importar o app, porque o config.py lê na importação.
    os.environ.setdefault("BANCO", str(pasta_de_dados() / "calculadora.db"))
    os.environ.setdefault("ADMIN_TOKEN", "")

    import uvicorn

    from app.main import app

    porta = int(os.getenv("CALC_PORTA") or porta_livre())
    endereco = f"http://127.0.0.1:{porta}"
    print("Calculadora de Comprimento Equivalente")
    print(f"Abrindo {endereco} no navegador...")
    print("Para fechar a calculadora, feche esta janela.")
    if not os.getenv("CALC_SEM_NAVEGADOR"):
        threading.Timer(1.5, webbrowser.open, args=[endereco]).start()
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")


if __name__ == "__main__":
    main()
