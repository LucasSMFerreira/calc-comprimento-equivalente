from app.dominio.erros import ErroDominio

# A planilha usa polegadas. Para quem pensa em milímetros existem duas referências:
# - PVC soldável (água fria) é vendido pelo diâmetro EXTERNO: 25 mm equivale a 3/4".
# - Tubos metálicos usam o diâmetro NOMINAL (DN): DN 25 equivale a 1".
PADROES_MM = {
    "pvc": {
        "nome": "PVC soldável (diâmetro externo)",
        "mapa": {20: '1/2"', 25: '3/4"', 32: '1"', 40: '1 1/4"', 50: '1 1/2"',
                 60: '2"', 75: '2 1/2"', 85: '3"', 110: '4"'},
    },
    "dn": {
        "nome": "Diâmetro nominal (DN)",
        "mapa": {8: '1/4"', 10: '3/8"', 15: '1/2"', 20: '3/4"', 25: '1"', 32: '1 1/4"',
                 40: '1 1/2"', 50: '2"', 65: '2 1/2"', 80: '3"', 100: '4"', 125: '5"',
                 150: '6"', 200: '8"', 250: '10"', 300: '12"', 350: '14"'},
    },
}


def mm_para_polegada(mm: int, padrao: str) -> str:
    if padrao not in PADROES_MM:
        raise ErroDominio(f"Padrão '{padrao}' desconhecido. Use 'pvc' ou 'dn'.")
    mapa = PADROES_MM[padrao]["mapa"]
    if mm not in mapa:
        raise ErroDominio(f"{mm} mm não existe no padrão {PADROES_MM[padrao]['nome']}.")
    return mapa[mm]