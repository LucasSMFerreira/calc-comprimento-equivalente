import re
import unicodedata

from rapidfuzz import fuzz

from app.dominio.tabela import TabelaEquivalentes

# Nomes que as pessoas usam -> nome que está na tabela
SINONIMOS = {
    "cotovelo": "joelho",
    "entrada normal": "saida entrada de canalizacao",
    "saida de canalizacao": "saida entrada de canalizacao",
    "tubo": "trecho reto",
    "cano": "trecho reto",
    "tubulacao": "trecho reto",
    "saida lateral": "passagem lateral",
    "saida bilateral": "passagem bilateral",
}
# Palavras que não ajudam a achar a conexão
IGNORAR = {"de", "da", "do", "das", "dos", "a", "o", "e", "pvc", "metal", "aco", "ferro",
           "galvanizado", "cobre", "bronze", "latao", "raio", "medio", "longo", "curto"}
PALAVRAS_METAL = ("metal", "aco", "ferro", "galvanizado", "cobre", "bronze", "latao")
NOTA_MINIMA = 85


def normalizar(texto: str) -> str:
    """'Registro de Gaveta (ABERTO)' -> 'registro de gaveta aberto'"""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    palavras = re.sub(r"[^a-z0-9]+", " ", sem_acento).split()
    # tira o plural simples: joelhos -> joelho, registros -> registro
    limpo = " ".join(p[:-1] if len(p) > 3 and p.endswith("s") else p for p in palavras)
    for apelido, oficial in SINONIMOS.items():
        limpo = re.sub(rf"\b{apelido}\b", oficial, limpo)
    return limpo


def palavras_chave(texto: str) -> str:
    return " ".join(p for p in normalizar(texto).split() if p not in IGNORAR)


def reconhecer_conexao(texto: str, tabela: TabelaEquivalentes) -> str | None:
    """Devolve o id da conexão mais parecida com o texto, ou None se nenhuma for parecida."""
    procurado = palavras_chave(texto)
    if not procurado:
        return None
    melhor_id, melhor_nota = None, (0.0, 0.0)
    for conexao in tabela.conexoes:
        nome = palavras_chave(conexao.nome)
        # 1º critério: palavras em comum; 2º (desempate): nome inteiro parecido
        nota = (fuzz.token_set_ratio(procurado, nome), fuzz.token_sort_ratio(procurado, nome))
        if nota > melhor_nota:
            melhor_id, melhor_nota = conexao.id, nota
    return melhor_id if melhor_nota[0] >= NOTA_MINIMA else None


def reconhecer_material(texto: str) -> str | None:
    normal = normalizar(texto)
    if "pvc" in normal:
        return "PVC"
    if any(palavra in normal for palavra in PALAVRAS_METAL):
        return "Metal"
    return None