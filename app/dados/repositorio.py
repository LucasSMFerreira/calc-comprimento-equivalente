import io
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
from openpyxl.drawing.image import Image as ImagemExcel

from app.dados.importador import Importacao
from app.dominio.erros import ErroDominio
from app.dominio.tabela import Conexao, TabelaEquivalentes

ESQUEMA = """
CREATE TABLE IF NOT EXISTS versoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    origem TEXT NOT NULL,
    criada_em TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    ativa INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS diametros (
    versao_id INTEGER NOT NULL REFERENCES versoes(id),
    ordem INTEGER NOT NULL,
    polegada TEXT NOT NULL,
    PRIMARY KEY (versao_id, polegada)
);
CREATE TABLE IF NOT EXISTS conexoes (
    versao_id INTEGER NOT NULL REFERENCES versoes(id),
    id TEXT NOT NULL,
    nome TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    PRIMARY KEY (versao_id, id)
);
CREATE TABLE IF NOT EXISTS valores (
    versao_id INTEGER NOT NULL REFERENCES versoes(id),
    conexao_id TEXT NOT NULL,
    material TEXT NOT NULL,
    diametro TEXT NOT NULL,
    leq TEXT NOT NULL,
    PRIMARY KEY (versao_id, conexao_id, material, diametro)
);
CREATE TABLE IF NOT EXISTS fotos (
    versao_id INTEGER NOT NULL REFERENCES versoes(id),
    conexao_id TEXT NOT NULL,
    material TEXT NOT NULL,
    formato TEXT NOT NULL,
    dados BLOB NOT NULL,
    PRIMARY KEY (versao_id, conexao_id, material)
);
"""


class Repositorio:
    """Guarda as versões da tabela base num arquivo SQLite."""

    def __init__(self, caminho: str | Path):
        self.caminho = str(caminho)
        with self._conexao() as con:
            con.executescript(ESQUEMA)

    @contextmanager
    def _conexao(self):
        con = sqlite3.connect(self.caminho)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            with con:  # commit no final, rollback se der erro
                yield con
        finally:
            con.close()

    def salvar_versao(self, nome: str, origem: str, importacao: Importacao) -> int:
        if not importacao.valida:
            raise ErroDominio("A planilha tem erros e não pode ser salva.")
        tabela = importacao.tabela
        with self._conexao() as con:
            repetida = con.execute("SELECT id FROM versoes WHERE hash = ?", (importacao.hash,)).fetchone()
            if repetida:
                raise ErroDominio(f"Essa planilha já foi importada (versão {repetida['id']}).")
            cursor = con.execute(
                "INSERT INTO versoes (nome, origem, criada_em, hash) VALUES (?, ?, ?, ?)",
                (nome, origem, datetime.now().isoformat(timespec="seconds"), importacao.hash),
            )
            versao_id = cursor.lastrowid
            con.executemany(
                "INSERT INTO diametros VALUES (?, ?, ?)",
                [(versao_id, i, d) for i, d in enumerate(tabela.diametros)],
            )
            con.executemany(
                "INSERT INTO conexoes VALUES (?, ?, ?, ?)",
                [(versao_id, c.id, c.nome, i) for i, c in enumerate(tabela.conexoes)],
            )
            con.executemany(
                "INSERT INTO valores VALUES (?, ?, ?, ?, ?)",
                [(versao_id, c, m, d, str(v)) for (c, m, d), v in tabela.valores.items()],
            )
            con.executemany(
                "INSERT INTO fotos VALUES (?, ?, ?, ?, ?)",
                [(versao_id, c, m, fmt, dados) for (c, m), (dados, fmt) in importacao.fotos.items()],
            )
        return versao_id

    def listar_versoes(self) -> list[dict]:
        with self._conexao() as con:
            linhas = con.execute(
                "SELECT id, nome, origem, criada_em, ativa FROM versoes ORDER BY id DESC"
            ).fetchall()
        return [dict(linha) | {"ativa": bool(linha["ativa"])} for linha in linhas]

    def ativar(self, versao_id: int) -> None:
        with self._conexao() as con:
            if not con.execute("SELECT 1 FROM versoes WHERE id = ?", (versao_id,)).fetchone():
                raise ErroDominio(f"Versão {versao_id} não existe.")
            con.execute("UPDATE versoes SET ativa = (id = ?)", (versao_id,))

    def versao_ativa(self) -> dict | None:
        with self._conexao() as con:
            linha = con.execute("SELECT id, nome, criada_em FROM versoes WHERE ativa = 1").fetchone()
        return dict(linha) if linha else None

    def carregar_tabela(self, versao_id: int) -> TabelaEquivalentes:
        with self._conexao() as con:
            diametros = [r["polegada"] for r in con.execute(
                "SELECT polegada FROM diametros WHERE versao_id = ? ORDER BY ordem", (versao_id,))]
            conexoes = [Conexao(r["id"], r["nome"]) for r in con.execute(
                "SELECT id, nome FROM conexoes WHERE versao_id = ? ORDER BY ordem", (versao_id,))]
            valores = {
                (r["conexao_id"], r["material"], r["diametro"]): Decimal(r["leq"])
                for r in con.execute("SELECT * FROM valores WHERE versao_id = ?", (versao_id,))
            }
        if not conexoes:
            raise ErroDominio(f"Versão {versao_id} não existe.")
        return TabelaEquivalentes(diametros, conexoes, valores)

    def foto(self, versao_id: int, conexao_id: str, material: str) -> tuple[bytes, str] | None:
        with self._conexao() as con:
            linha = con.execute(
                "SELECT dados, formato FROM fotos WHERE versao_id = ? AND conexao_id = ? AND material = ?",
                (versao_id, conexao_id, material),
            ).fetchone()
        return (linha["dados"], linha["formato"]) if linha else None

    def exportar_xlsx(self, versao_id: int) -> bytes:
        """Gera uma planilha no mesmo formato da original (pode ser reimportada)."""
        tabela = self.carregar_tabela(versao_id)
        livro = openpyxl.Workbook()
        folha = livro.active
        folha.title = "Plan1"
        folha.append(["Descrição", "Foto", "Material", *tabela.diametros])
        for conexao in tabela.conexoes:
            for material in tabela.materiais_de(conexao.id):
                folha.append([conexao.nome, None, material, *[
                    float(tabela.valores[(conexao.id, material, d)]) for d in tabela.diametros
                ]])
                foto = self.foto(versao_id, conexao.id, material)
                if foto:
                    imagem = ImagemExcel(io.BytesIO(foto[0]))
                    imagem.width, imagem.height = 40, 40
                    folha.add_image(imagem, f"B{folha.max_row}")
                    folha.row_dimensions[folha.max_row].height = 32
        saida = io.BytesIO()
        livro.save(saida)
        return saida.getvalue()