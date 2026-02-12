import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
import re

# =========================
# CONFIGURACOES
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQ_ENTRADA = os.path.join(BASE_DIR, "conf_preço.xlsx")  # base original (nova)
LOGO_ARQ = os.path.join(BASE_DIR, "Bonanza---logo.png")   # logo na mesma pasta

# Paleta Bonanza
BONANZA_RED = "#E30613"
BONANZA_BLUE = "#0054A6"


# =========================
# FUNCOES AUXILIARES
# =========================

def parse_preco(p):
    """Converte a string de preço do formato brasileiro para float (ou mantém se já for número)."""
    if isinstance(p, str):
        p_clean = (
            p.replace("R$", "")
             .replace(" ", "")
             .replace("\xa0", "")
             .replace(".", "")
             .replace(",", ".")
        )
        try:
            return float(p_clean)
        except Exception:
            return np.nan
    return p


def carregar_logo(path_logo):
    """Carrega a imagem da logo, se existir."""
    if os.path.exists(path_logo):
        try:
            return plt.imread(path_logo)
        except Exception:
            return None
    return None


def adicionar_logo(ax, logo_img, zoom=0.14):
    """Plota a logo no canto superior esquerdo da página (fora do gráfico)."""
    if logo_img is None:
        return
    fig = ax.figure
    imagebox = OffsetImage(logo_img, zoom=zoom)
    ab = AnnotationBbox(
        imagebox,
        (0.02, 0.98),              # canto superior esquerdo do PDF
        xycoords=fig.transFigure,
        frameon=False,
        box_alignment=(0, 1),
    )
    fig.add_artist(ab)


def sanitizar_nome_arquivo(texto: str) -> str:
    """Remove caracteres problemáticos para nome de arquivo."""
    texto = re.sub(r"[^\w\-\_]", "_", texto)
    return texto


# =========================
# 1. CARREGAR E PREPARAR DADOS
# =========================

df = pd.read_excel(ARQ_ENTRADA)

# Preço numérico
df["Preco_num"] = df["Preço"].apply(parse_preco)

# Datas
df["Data/Hora"] = pd.to_datetime(df["Data/Hora"])
df["Data"] = df["Data/Hora"].dt.date
periodo_inicio = df["Data"].min()
periodo_fim = df["Data"].max()
periodo_label = f"{periodo_inicio:%d/%m/%Y} a {periodo_fim:%d/%m/%Y}"

# Conformidade / Divergência
acao_upper = df["Ação"].astype(str).str.upper()
df["Conforme"] = np.where(
    (acao_upper.str.contains("OK")) | (acao_upper == "POK"),
    1,
    0
)
df["Divergente"] = 1 - df["Conforme"]

# Logo
logo_img = carregar_logo(LOGO_ARQ)

# Lista de lojas
lojas = sorted(df["Empresa"].dropna().unique())
print("Lojas encontradas:", lojas)

# Ranking geral por filial (rede toda)
ranking_filial = df.groupby("Empresa").agg(
    divergencias=("Divergente", "sum"),
    total=("Divergente", "count")
)
ranking_filial["perc"] = ranking_filial["divergencias"] / ranking_filial["total"] * 100
ranking_filial = ranking_filial.sort_values("perc", ascending=False)


# =========================
# 2. GRÁFICO GERAL DA REDE
# =========================

def grafico_total_e_perc_por_loja(ranking_filial, logo_img, periodo_label=None):
    """Mostra total coletado e % de divergências por loja em um único painel."""
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(ranking_filial))

    ax.bar(x, ranking_filial["total"], color=BONANZA_BLUE, alpha=0.65, label="Total coletado")
    ax_line = ax.twinx()
    ax_line.plot(x, ranking_filial["perc"], color=BONANZA_RED, marker="o", label="% divergência")

    ax.set_xticks(x)
    ax.set_xticklabels(ranking_filial.index)
    for tick in ax.get_xticklabels():
        tick.set_rotation(40)
        tick.set_ha("right")

    ax.set_ylabel("Total coletado")
    ax_line.set_ylabel("% divergência")
    titulo = "Total coletado e % divergência por loja"
    if periodo_label:
        titulo += f"\nPeríodo: {periodo_label}"
    ax.set_title(titulo)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    max_total = ranking_filial["total"].max()
    max_perc = ranking_filial["perc"].max()
    for i, (tot, perc) in enumerate(zip(ranking_filial["total"], ranking_filial["perc"])):
        ax.text(i, tot, int(tot),
                ha="center", va="bottom", fontsize=9, color="black", rotation=0)
        ax_line.text(i, perc, f"{perc:.1f}%",
                     ha="center", va="bottom", fontsize=9, color=BONANZA_RED)

    ax.set_ylim(0, max_total * 1.15 if max_total else 1)
    ax_line.set_ylim(0, max_perc * 1.2 if max_perc else 1)

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax_line.get_legend_handles_labels()
    ax.legend(
        h1 + h2,
        l1 + l2,
        loc="upper right",
        bbox_to_anchor=(1.0, 1.22),
        ncol=2,
        fontsize=8,
        frameon=False,
    )

    adicionar_logo(ax, logo_img)
    fig.tight_layout(rect=(0.04, 0.08, 0.96, 0.86))
    return fig


# =========================
# 3. FUNÇÃO PARA GERAR GRÁFICOS DE UMA LOJA
# =========================


def gerar_figuras_loja(df_loja, nome_loja, ranking_filial, logo_img):
    figs = []

    # 1) Divergências por dia para cada mês encontrado
    for periodo, df_mes in df_loja.groupby(df_loja["Data/Hora"].dt.to_period("M")):
        if df_mes.empty:
            continue

        dv = df_mes.groupby("Data").agg(
            divergencias=("Divergente", "sum"),
            total=("Divergente", "count")
        )
        dv["perc"] = dv["divergencias"] / dv["total"] * 100
        datas_labels = [d.strftime("%d/%m") for d in dv.index]
        x = np.arange(len(datas_labels))

        fig2, ax2 = plt.subplots(figsize=(12, 6))
        ax2.bar(x, dv["total"], color=BONANZA_BLUE, alpha=0.6, label="Total coletado")
        ax2_line = ax2.twinx()
        ax2_line.plot(x, dv["divergencias"], color=BONANZA_RED, marker="o", label="Divergências")

        ax2.set_xticks(x)
        ax2.set_xticklabels(datas_labels)
        for tick in ax2.get_xticklabels():
            tick.set_rotation(40)
            tick.set_ha("right")

        mes_label = periodo.strftime("%m/%Y")
        ax2.set_xlabel(f"Data ({mes_label})")
        ax2.set_ylabel("Total coletado")
        ax2_line.set_ylabel("Qtde divergências")
        ax2.set_title(f"Divergências por Dia - {mes_label} - {nome_loja}")
        ax2.grid(axis="y", linestyle="--", alpha=0.3)

        max_total = dv["total"].max()
        max_div = dv["divergencias"].max()
        for i, (tot, div, perc) in enumerate(zip(dv["total"], dv["divergencias"], dv["perc"])):
            ax2.text(i, tot, str(int(tot)),
                     ha="center", va="bottom", fontsize=9, color="black")
            ax2_line.text(i, div, f"{perc:.1f}%",
                          ha="center", va="bottom", fontsize=9, color=BONANZA_RED)

        ax2.set_ylim(0, max_total * 1.15 if max_total else 1)
        ax2_line.set_ylim(0, max_div * 1.2 if max_div else 1)

        h1, l1 = ax2.get_legend_handles_labels()
        h2, l2 = ax2_line.get_legend_handles_labels()
        ax2.legend(
            h1 + h2,
            l1 + l2,
            loc="upper right",
            bbox_to_anchor=(1.0, 1.22),
            ncol=2,
            fontsize=8,
            frameon=False,
        )

        adicionar_logo(ax2, logo_img)
        fig2.tight_layout(rect=(0.04, 0.08, 0.96, 0.86))
        figs.append(fig2)

    # 2) Visão geral da rede (mesmo painel para todas as lojas)
    figs.append(grafico_total_e_perc_por_loja(ranking_filial, logo_img, periodo_label))

    return figs



# =========================
# 4. GERAR PDF POR LOJA (inclui visão da rede)
# =========================

for loja in lojas:
    df_loja = df[df["Empresa"] == loja].copy()
    if df_loja.empty:
        continue

    figs_loja = gerar_figuras_loja(df_loja, loja, ranking_filial, logo_img)

    nome_pdf = os.path.join(BASE_DIR, f"analise_preco_{sanitizar_nome_arquivo(loja)}.pdf")
    with PdfPages(nome_pdf) as pdf:
        for fig in figs_loja:
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
    print(f"PDF gerado para a loja {loja}: {nome_pdf}")

print("Processo concluído.")
