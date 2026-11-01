import hmac
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import config
from app.dados.importador import comparar, importar_planilha
from app.dados.repositorio import Repositorio
from app.dominio.calculo import Item, Resultado, calcular
from app.dominio.diametros import PADROES_MM
from app.dominio.erros import ErroDominio
from app.esquemas import PedidoCalculo

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def preparar_banco(repo: Repositorio) -> None:
    """Na primeira vez, importa a planilha do professor e deixa ela ativa."""
    if repo.versao_ativa() is None:
        importacao = importar_planilha(config.TABELA_PADRAO.read_bytes())
        versao_id = repo.salvar_versao("Tabela do professor", config.TABELA_PADRAO.name, importacao)
        repo.ativar(versao_id)


def exigir_admin(x_admin_token: str = Header(default="")) -> None:
    if not config.ADMIN_TOKEN:
        raise HTTPException(503, "Defina ADMIN_TOKEN no servidor para gerenciar tabelas.")
    if not hmac.compare_digest(x_admin_token, config.ADMIN_TOKEN):
        raise HTTPException(401, "Senha de administrador incorreta.")


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


@app.get("/api/tabelas")
def listar_tabelas(r: Repositorio = Depends(repo)):
    return r.listar_versoes()


@app.post("/api/tabelas/previa", dependencies=[Depends(exigir_admin)])
async def previa_tabela(arquivo: UploadFile = File(...), r: Repositorio = Depends(repo)):
    importacao = importar_planilha(await arquivo.read())
    _, atual = tabela_ativa(r)
    return {
        "valida": importacao.valida,
        "erros": importacao.erros,
        "avisos": importacao.avisos,
        "conexoes": len(importacao.tabela.conexoes) if importacao.valida else 0,
        "diametros": importacao.tabela.diametros if importacao.valida else [],
        "fotos": len(importacao.fotos),
        "mudancas": comparar(___, importacao.tabela) if importacao.valida else [],
    }


@app.post("/api/tabelas", dependencies=[Depends(exigir_admin)])
async def salvar_tabela(nome: str = Form(...), arquivo: UploadFile = File(...),
                        r: Repositorio = Depends(repo)):
    importacao = importar_planilha(await arquivo.read())
    if not importacao.valida:
        raise ErroDominio("A planilha tem erros: " + " ".join(importacao.erros[:3]))
    versao_id = r.salvar_versao(nome, arquivo.filename or "upload.xlsx", importacao)
    r.ativar(versao_id)
    return {"id": versao_id}


@app.post("/api/tabelas/{versao_id}/ativar", dependencies=[Depends(exigir_admin)])
def ativar_tabela(versao_id: int, r: Repositorio = Depends(repo)):
    r.ativar(versao_id)
    return {"ativa": versao_id}


@app.get("/api/tabelas/{versao_id}/exportar")
def exportar_tabela(versao_id: int, r: Repositorio = Depends(repo)):
    return Response(r.exportar_xlsx(versao_id), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="tabela-v{versao_id}.xlsx"'})


app.mount("/", StaticFiles(directory=config.RAIZ / "app" / "static", html=True), name="static")