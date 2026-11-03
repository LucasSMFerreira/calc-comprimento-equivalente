import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # lê o arquivo .env, se existir

RAIZ = Path(__file__).resolve().parent.parent
BANCO = os.getenv("BANCO", str(RAIZ / "data" / "calculadora.db"))
TABELA_PADRAO = RAIZ / "data" / "tabela_padrao.xlsx"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
PORTA = int(os.getenv("PORTA", "8080"))
IA_URL = os.getenv("IA_URL", "")
IA_TOKEN = os.getenv("IA_TOKEN", "")