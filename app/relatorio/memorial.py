import io
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from fpdf import FPDF

from app.dominio.calculo import Resultado
from app.dominio.tabela import TRECHO_RETO


def br(numero: Decimal, casas: int = 2) -> str:
    return f"{numero:.{casas}f}".replace(".", ",")


def gerar_memorial(resultado: Resultado, versao: str,
                   foto_de: Callable[[str, str], bytes | None]) -> bytes:
    """Memorial de cálculo em PDF: tabela de itens, somatório e lista de compras."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Memorial de Cálculo - Comprimento Equivalente", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Data: {datetime.now():%d/%m/%Y %H:%M}   Diâmetro: {resultado.diametro}   "
                   f"Tabela: {versao}", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, "Fórmula: L total = soma de (quantidade x L equivalente unitário). "
                         "Valores em metros de tubulação reta de mesmo diâmetro.")
    pdf.ln(3)

    larguras = (16, 70, 22, 22, 28, 32)
    titulos = ("Foto", "Conexão", "Material", "Qtd", "L eq. (m)", "Subtotal (m)")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    for largura, titulo in zip(larguras, titulos):
        pdf.cell(largura, 8, titulo, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for linha in resultado.linhas:
        x, y = pdf.get_x(), pdf.get_y()
        pdf.cell(larguras[0], 14, "", border=1)
        foto = foto_de(linha.conexao_id, linha.material)
        if foto:
            pdf.image(io.BytesIO(foto), x=x + 2, y=y + 1, w=12, h=12, keep_aspect_ratio=True)
        quantidade = br(linha.quantidade, 2 if linha.conexao_id == TRECHO_RETO else 0)
        for largura, texto in zip(larguras[1:], (linha.nome, linha.material, quantidade,
                                                 br(linha.leq_unitario), br(linha.subtotal))):
            pdf.cell(largura, 14, texto, border=1, align="L" if largura == 70 else "C")
        pdf.ln()

    pdf.set_font("Helvetica", "B", 11)
    for rotulo, valor in (("Conexões", resultado.total_conexoes),
                          ("Trechos retos", resultado.total_trechos_retos),
                          ("COMPRIMENTO EQUIVALENTE TOTAL", resultado.total)):
        pdf.cell(sum(larguras[:5]), 8, rotulo, border=1, align="R")
        pdf.cell(larguras[5], 8, f"{br(valor)} m", border=1, align="C")
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Lista de compras", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for linha in resultado.linhas:
        if linha.conexao_id == TRECHO_RETO:
            texto = f"- Tubo {linha.material} {resultado.diametro}: {br(linha.quantidade)} m"
        if len(linha.trechos) > 1:
                texto += " (" + " + ".join(br(t) for t in linha.trechos) + ")"    
        else:
            texto = f"- {br(linha.quantidade, 0)} x {linha.nome} ({linha.material}) {resultado.diametro}"
        pdf.cell(0, 7, texto, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())