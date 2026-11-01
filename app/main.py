from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import config
from app.dados.importador import importar_planilha
from app.dados.repositorio import Repositorio
from app.dominio.calculo import Item, Resultado, calcular
from app.dominio.diametros import PADROES_MM
from app.dominio.erros import ErroDominio
from app.esquemas import PedidoCalculo


def preparar_banco(repo: Repositorio) -> None:
    """Na primeira vez, importa a planilha do professor e deixa ela ativa."""
    if repo.versao_ativa() is None:
        importacao = importar_planilha(config.TABELA_PADRAO.read_bytes())
        versao_id = repo.salvar_versao("Tabela do professor", config.TABELA_PADRAO.name, importacao)
        repo.ativar(versao_id)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    app.state.repo = Repositorio(config.BANCO)
    preparar_banco(app.state.repo)
    yield


app = FastAPI(title="Calculadora de Comprimento Equivalente", lifespan=ciclo_de_vida)


@app.exception_handler(ErroDominio)
async def erro_de_dominio(request: Request, erro: ErroDominio):
    return JSONResponse(status_code=422, content={"detail": str(erro)})


def repo(request: Request) -> Repositorio:
    return request.app.state.repo


def tabela_ativa(r: Repositorio):
    versao = r.versao_ativa()
    return versao, r.carregar_tabela(versao["id"])


def resultado_json(resultado: Resultado) -> dict:
    return {
        "diametro": resultado.diametro,
        "linhas": [
            {"conexao_id": ln.conexao_id, "nome": ln.nome, "material": ln.material,
             "quantidade": float(ln.quantidade), "leq_unitario": float(ln.leq_unitario),
             "subtotal": float(ln.subtotal)}
            for ln in resultado.linhas
        ],
        "total_conexoes": float(resultado.total_conexoes),
        "total_trechos_retos": float(resultado.total_trechos_retos),
        "total": float(resultado.total),
    }


# ---------- calculadora ----------

@app.get("/api/saude")
def saude():
    return {"status": "ok"}


@app.get("/api/tabela")
def obter_tabela(r: Repositorio = Depends(repo)):
    versao, tabela = tabela_ativa(r)
    return {
        "versao": versao,
        "diametros": tabela.diametros,
        "padroes_mm": PADROES_MM,
        "conexoes": [
            {"id": c.id, "nome": c.nome, "materiais": tabela.materiais_de(c.id),
             "valores": {m: {d: float(tabela.valores[(c.id, m, d)]) for d in tabela.diametros}
                         for m in tabela.materiais_de(c.id)}}
            for c in tabela.conexoes
        ],
    }


@app.get("/api/fotos/{versao_id}/{conexao_id}/{material}")
def obter_foto(versao_id: int, conexao_id: str, material: str, r: Repositorio = Depends(repo)):
    foto = r.foto(versao_id, conexao_id, material)
    if foto is None:
        raise HTTPException(404, "Foto não encontrada.")
    dados, formato = foto
    return Response(dados, media_type=f"image/{formato}",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/calcular")
def api_calcular(pedido: PedidoCalculo, r: Repositorio = Depends(repo)):
    _, tabela = tabela_ativa(r)
    itens = [Item(i.conexao_id, i.material, i.quantidade) for i in pedido.itens]
    return resultado_json(calcular(itens, pedido.diametro, tabela))


app.mount("/", StaticFiles(directory=config.RAIZ / "app" / "static", html=True), name="static")