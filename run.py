"""Ponto de entrada: `python run.py` (é o que o Discloud executa)."""
import uvicorn

from app import config

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORTA)