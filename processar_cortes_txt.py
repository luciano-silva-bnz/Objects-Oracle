#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processar_cortes_txt.py  (tema escuro + Top Compradores em UNID + % por dia da semana)
--------------------------------------------------------------------------------------
- Lê TXT grande (';') em chunks, normaliza EMB->UN, datas no formato YYYY-MM-DD-HH.MM.SS.ffffff
- Cortes EXCLUSIVOS (regra atual):
    corte_total_emb = max(QTDEMBSOLICITADA - QTDEMBSEPARADA, 0)
    estoque_emb = ESTOQUE_FINAL_DIA / QTDEMBALAGEM (se QTDEMBALAGEM>0, senão 0)
    Comercial se (corte_total_emb > estoque_emb); Operacional caso contrário
- Abas: prod_dia, comprador, totais_dia, evolucao, top_compradores, corte_semana (NOVA)
- Gráficos escuros:
    * Evolução diária (EMB), Totais por dia (EMB)
    * Top Compradores (UNID) com CORTE_OPER_UN e CORTE_COM_UN
    * Percentual de corte por dia da semana (UNID) – TX_CORTE_OPER_UN e TX_CORTE_COM_UN
- Se --output ausente: salva ao lado do TXT com _dashboard.xlsx
- Se --input ausente: abre seletor (Tkinter) para o TXT.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np


# ------------------------- Helpers ------------------------- #
def _to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
              .str.replace('.', '', regex=False)   # remove milhar
              .str.replace(',', '.', regex=False)  # vírgula -> ponto
              .str.strip(),
        errors="coerce"
    )


def _read_chunks(txt_path: str, chunksize: int = 200_000, encoding: str = "utf-8"):
    return pd.read_csv(txt_path, sep=';', dtype=str,
                       chunksize=chunksize, encoding=encoding, engine="python")


def _parse_dates(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%Y-%m-%d-%H.%M.%S.%f", errors="coerce")


# ------------------------- Núcleo ------------------------- #
def process_txt(txt_path: str,
                xlsx_out: str,
                chunksize: int = 200_000,
                encoding: str = "utf-8"):
    try:
        import xlsxwriter  # noqa: F401
        from xlsxwriter.utility import xl_col_to_name
    except Exception as e:
        raise SystemExit(
            "Dependência ausente: XlsxWriter. Instale com:\n"
            "  python -m pip install XlsxWriter\n"
            f"Detalhes: {e}"
        )

    agg_produto_dia = []
    agg_comprador = []
    prep_parts = []

    required = [
        "DTAHORGERACAO", "SEQPRODUTO", "DESCCOMPLETA", "COMPRADOR",
        "QTDEMBALAGEM", "QTDEMBSOLICITADA", "QTDEMBSEPARADA",
        "ESTOQUE_FINAL_DIA", "EMBALAGEM"
    ]

    for chunk in _read_chunks(txt_path, chunksize=chunksize, encoding=encoding):
        chunk.columns = [c.strip() for c in chunk.columns]

        missing = [k for k in required if k not in chunk.columns]
        if missing:
            raise ValueError(f"Colunas ausentes no TXT: {missing}")

        qtd_emb       = _to_num(chunk["QTDEMBALAGEM"]).fillna(0)
        qtd_solic_emb = _to_num(chunk["QTDEMBSOLICITADA"]).fillna(0)
        qtd_sep_emb   = _to_num(chunk["QTDEMBSEPARADA"]).fillna(0)
        estoque_un    = _to_num(chunk["ESTOQUE_FINAL_DIA"]).fillna(0)

        dt    = _parse_dates(chunk["DTAHORGERACAO"])
        data  = dt.dt.date

        produto   = (chunk["SEQPRODUTO"].fillna("").astype(str).str.strip()
                     + " - " + chunk["DESCCOMPLETA"].fillna("").astype(str).str.strip())
        comprador = chunk["COMPRADOR"].fillna("").astype(str).str.strip()
        embalagem = chunk["EMBALAGEM"].fillna("").astype(str).str.strip()

        # Normalizações em UN
        solic_un = qtd_solic_emb * qtd_emb
        sep_un   = qtd_sep_emb   * qtd_emb

        # Cortes EXCLUSIVOS (regra atual)
        corte_total_emb = (qtd_solic_emb - qtd_sep_emb).clip(lower=0)
        estoque_emb     = np.where(qtd_emb > 0, estoque_un / qtd_emb, 0)
        corte_com_emb   = np.where(corte_total_emb > estoque_emb, corte_total_emb, 0.0)
        corte_oper_emb  = corte_total_emb - corte_com_emb

        corte_com_un  = corte_com_emb  * qtd_emb
        corte_oper_un = corte_oper_emb * qtd_emb

        prep = pd.DataFrame({
            "DATA": data,
            "PRODUTO": produto,
            "COMPRADOR": comprador,
            "EMBALAGEM": embalagem,
            "QTDEMBALAGEM": qtd_emb,
            "SOLIC_EMB": qtd_solic_emb,
            "SEPAR_EMB": qtd_sep_emb,
            "SOLIC_UN": solic_un,
            "SEPAR_UN": sep_un,
            "ESTOQUE_UN": estoque_un,
            "ESTOQUE_EMB_EQUIV": estoque_emb,
            "CORTE_OPER_EMB": corte_oper_emb,
            "CORTE_COM_EMB":  corte_com_emb,
            "CORTE_OPER_UN":  corte_oper_un,
            "CORTE_COM_UN":   corte_com_un,
        })

        prep_parts.append(prep)

        # Agregado por chunk (estoque do dia como MAX)
        keys = ["DATA", "PRODUTO", "COMPRADOR", "QTDEMBALAGEM"]
        agg_dict = {
            "SOLIC_EMB": "sum", "SEPAR_EMB": "sum",
            "CORTE_OPER_EMB": "sum", "CORTE_COM_EMB": "sum",
            "SOLIC_UN": "sum", "SEPAR_UN": "sum",
            "CORTE_OPER_UN": "sum", "CORTE_COM_UN": "sum",
            "ESTOQUE_UN": "max", "ESTOQUE_EMB_EQUIV": "max"
        }
        g = prep.groupby(keys, dropna=False).agg(agg_dict).reset_index()
        g = g.rename(columns={
            "ESTOQUE_UN": "ESTOQUE_UN_DIA",
            "ESTOQUE_EMB_EQUIV": "ESTOQUE_EMB_EQUIV_DIA"
        })
        agg_produto_dia.append(g)

        # Comprador (período)
        agg_comprador.append(
            prep.groupby(["COMPRADOR"], dropna=False).agg(
                SOLIC_EMB=("SOLIC_EMB", "sum"),
                SEPAR_EMB=("SEPAR_EMB", "sum"),
                CORTE_OPER_EMB=("CORTE_OPER_EMB", "sum"),
                CORTE_COM_EMB=("CORTE_COM_EMB", "sum"),
                SOLIC_UN=("SOLIC_UN", "sum"),
                SEPAR_UN=("SEPAR_UN", "sum"),
                CORTE_OPER_UN=("CORTE_OPER_UN", "sum"),
                CORTE_COM_UN=("CORTE_COM_UN", "sum"),
            ).reset_index()
        )

    # Consolidação entre chunks
    keys = ["DATA", "PRODUTO", "COMPRADOR", "QTDEMBALAGEM"]
    df_prod_dia = pd.concat(agg_produto_dia, ignore_index=True).groupby(
        keys, dropna=False
    ).agg({
        "SOLIC_EMB": "sum", "SEPAR_EMB": "sum",
        "CORTE_OPER_EMB": "sum", "CORTE_COM_EMB": "sum",
        "SOLIC_UN": "sum", "SEPAR_UN": "sum",
        "CORTE_OPER_UN": "sum", "CORTE_COM_UN": "sum",
        "ESTOQUE_UN_DIA": "max", "ESTOQUE_EMB_EQUIV_DIA": "max"
    }).reset_index()

    df_comprador = pd.concat(agg_comprador, ignore_index=True).groupby(
        ["COMPRADOR"], dropna=False
    ).sum().reset_index()

    full_prep = pd.concat(prep_parts, ignore_index=True)

    # Visões
    totais_dia = full_prep.groupby('DATA')[
        ['SOLIC_EMB', 'SEPAR_EMB', 'CORTE_OPER_EMB', 'CORTE_COM_EMB',
         'SOLIC_UN', 'SEPAR_UN', 'CORTE_OPER_UN', 'CORTE_COM_UN']
    ].sum().reset_index()

    # Top compradores agora em UNID
    df_comprador['TOTAL_CORTES_UN'] = df_comprador['CORTE_OPER_UN'] + df_comprador['CORTE_COM_UN']
    top_compradores = df_comprador.sort_values('TOTAL_CORTES_UN', ascending=False).head(15).reset_index(drop=True)

    # NOVO: Percentual por dia da semana (Seg..Dom)
    tmp = full_prep.copy()
    tmp['DATA_DT'] = pd.to_datetime(tmp['DATA'])
    dow_num = tmp['DATA_DT'].dt.weekday  # 0=Seg ... 6=Dom
    dow_map = {0: 'SEG', 1: 'TER', 2: 'QUA', 3: 'QUI', 4: 'SEX', 5: 'SAB', 6: 'DOM'}
    tmp['DOW'] = dow_num.map(dow_map)

    tmp['CORTE_TOTAL_EMB'] = tmp['CORTE_OPER_EMB'] + tmp['CORTE_COM_EMB']
    tmp['CORTE_TOTAL_UN']  = tmp['CORTE_OPER_UN']  + tmp['CORTE_COM_UN']

    corte_semana = tmp.groupby('DOW', dropna=False)[
        ['SOLIC_EMB','SEPAR_EMB','CORTE_OPER_EMB','CORTE_COM_EMB','CORTE_TOTAL_EMB',
         'SOLIC_UN','SEPAR_UN','CORTE_OPER_UN','CORTE_COM_UN','CORTE_TOTAL_UN']
    ].sum().reset_index()

    # Ordena SEG..DOM
    dow_order = ['SEG','TER','QUA','QUI','SEX','SAB','DOM']
    corte_semana['DOW'] = pd.Categorical(corte_semana['DOW'], categories=dow_order, ordered=True)
    corte_semana = corte_semana.sort_values('DOW')

    # Taxas (fração 0..1 para formatar como % no Excel)
    def _rate(num, den):
        return np.where(den > 0, num / den, np.nan)

    corte_semana['TX_CORTE_TOTAL_UN'] = _rate(corte_semana['CORTE_TOTAL_UN'], corte_semana['SOLIC_UN'])
    corte_semana['TX_CORTE_OPER_UN']  = _rate(corte_semana['CORTE_OPER_UN'],  corte_semana['SOLIC_UN'])
    corte_semana['TX_CORTE_COM_UN']   = _rate(corte_semana['CORTE_COM_UN'],   corte_semana['SOLIC_UN'])

    corte_semana['TX_CORTE_TOTAL_EMB'] = _rate(corte_semana['CORTE_TOTAL_EMB'], corte_semana['SOLIC_EMB'])
    corte_semana['TX_CORTE_OPER_EMB']  = _rate(corte_semana['CORTE_OPER_EMB'],  corte_semana['SOLIC_EMB'])
    corte_semana['TX_CORTE_COM_EMB']   = _rate(corte_semana['CORTE_COM_EMB'],   corte_semana['SOLIC_EMB'])

    # Ordenação de colunas em prod_dia
    cols_order = [
        "DATA", "PRODUTO", "COMPRADOR", "QTDEMBALAGEM",
        "SOLIC_EMB", "SEPAR_EMB", "CORTE_OPER_EMB", "CORTE_COM_EMB",
        "SOLIC_UN", "SEPAR_UN", "CORTE_OPER_UN", "CORTE_COM_UN",
        "ESTOQUE_UN_DIA", "ESTOQUE_EMB_EQUIV_DIA"
    ]
    df_prod_dia = df_prod_dia.reindex(columns=cols_order)

    # -------------------- Excel + Gráficos (tema escuro) -------------------- #
    with pd.ExcelWriter(xlsx_out, engine="xlsxwriter") as writer:
        df_prod_dia.to_excel(writer, sheet_name="prod_dia", index=False)
        df_comprador.to_excel(writer, sheet_name="comprador", index=False)
        totais_dia.to_excel(writer, sheet_name="totais_dia", index=False)
        top_compradores.to_excel(writer, sheet_name="top_compradores", index=False)
        corte_semana.to_excel(writer, sheet_name="corte_semana", index=False)

        wb = writer.book
        from xlsxwriter.utility import xl_col_to_name
        date_fmt = wb.add_format({"num_format": "dd/mm/yy"})
        pct_fmt  = wb.add_format({"num_format": "0.0%"})

        def _table(ws_name: str, df: pd.DataFrame, date_cols=None, pct_cols=None):
            ws = writer.sheets[ws_name]
            if date_cols:
                for col_letter in date_cols:
                    ws.set_column(f"{col_letter}:{col_letter}", 12, date_fmt)
            if pct_cols:
                for col in pct_cols:
                    idx = df.columns.get_loc(col)
                    col_letter = xl_col_to_name(idx)
                    ws.set_column(f"{col_letter}:{col_letter}", None, pct_fmt)
            nrows, ncols = df.shape
            ws.add_table(0, 0, nrows, ncols - 1, {
                "style": "Table Style Light 9",
                "columns": [{"header": c} for c in df.columns]
            })
            return ws

        def _darkify(chart, title: str, percent_axis: bool = False):
            chart.set_title({"name": title, "name_font": {"color": "white"}})
            chart.set_chartarea({"fill": {"color": "#1E1E1E"}})
            chart.set_plotarea({"fill": {"color": "#2B2B2B"}})
            chart.set_legend({"font": {"color": "white"}})
            x_axis = {
                "name_font": {"color": "white"},
                "num_font": {"color": "white"},
                "line": {"color": "white"},
                "major_gridlines": {"visible": True, "line": {"color": "#555555"}},
            }
            y_axis = {
                "name_font": {"color": "white"},
                "num_font": {"color": "white"},
                "line": {"color": "white"},
            }
            if percent_axis:
                y_axis["num_format"] = "0.0%"
            chart.set_x_axis(x_axis)
            chart.set_y_axis(y_axis)
            return chart

        _table("prod_dia", df_prod_dia, date_cols=["A"])
        _table("comprador", df_comprador)
        _table("totais_dia", totais_dia, date_cols=["A"])
        _table("top_compradores", top_compradores)
        _table("corte_semana", corte_semana, pct_cols=[
            "TX_CORTE_TOTAL_UN","TX_CORTE_OPER_UN","TX_CORTE_COM_UN",
            "TX_CORTE_TOTAL_EMB","TX_CORTE_OPER_EMB","TX_CORTE_COM_EMB"
        ])

        # Evolução diária (EMB)
        evol = df_prod_dia.groupby("DATA")[["CORTE_OPER_EMB", "CORTE_COM_EMB"]].sum().reset_index()
        evol.to_excel(writer, sheet_name="evolucao", index=False)
        ws_e = _table("evolucao", evol, date_cols=["A"])
        chart_line = wb.add_chart({"type": "line"})
        for col in ["CORTE_OPER_EMB", "CORTE_COM_EMB"]:
            idx = evol.columns.get_loc(col)
            chart_line.add_series({
                "name":       col,
                "categories": ["evolucao", 1, 0, len(evol), 0],
                "values":     ["evolucao", 1, idx, len(evol), idx],
                "marker":     {"type": "circle"}
            })
        _darkify(chart_line, "Evolução Diária - Cortes (EMB)")
        ws_e.insert_chart("E2", chart_line, {"x_scale": 1.3, "y_scale": 1.2})

        # Totais do dia (EMB)
        ws_td = writer.sheets["totais_dia"]
        chart_td = wb.add_chart({"type": "line"})
        for col in ["SOLIC_EMB", "SEPAR_EMB", "CORTE_OPER_EMB", "CORTE_COM_EMB"]:
            idx = totais_dia.columns.get_loc(col)
            chart_td.add_series({
                "name":       col,
                "categories": ["totais_dia", 1, 0, len(totais_dia), 0],
                "values":     ["totais_dia", 1, idx, len(totais_dia), idx],
                "marker":     {"type": "circle"}
            })
        _darkify(chart_td, "Totais por Dia (EMB)")
        ws_td.insert_chart("K2", chart_td, {"x_scale": 1.3, "y_scale": 1.2})

        # Top Compradores (UNID)
        ws_top = writer.sheets["top_compradores"]
        chart_bar = wb.add_chart({"type": "bar"})
        col_comp = top_compradores.columns.get_loc("COMPRADOR")
        col_opun = top_compradores.columns.get_loc("CORTE_OPER_UN")
        col_cmun = top_compradores.columns.get_loc("CORTE_COM_UN")
        n = len(top_compradores)
        chart_bar.add_series({
            "name": "CORTE_OPER_UN",
            "categories": ["top_compradores", 1, col_comp, n, col_comp],
            "values":     ["top_compradores", 1, col_opun, n, col_opun],
            "data_labels": {"value": True, "font": {"color": "white"}},
            "fill":   {"color": "#2F75B5"}, "border": {"color": "#2F75B5"},
        })
        chart_bar.add_series({
            "name": "CORTE_COM_UN",
            "categories": ["top_compradores", 1, col_comp, n, col_comp],
            "values":     ["top_compradores", 1, col_cmun, n, col_cmun],
            "data_labels": {"value": True, "font": {"color": "white"}},
            "fill":   {"color": "#C0504D"}, "border": {"color": "#C0504D"},
        })
        chart_bar.set_y_axis({"reverse": True})
        _darkify(chart_bar, "Top Compradores - Cortes (UNID)")
        ws_top.insert_chart("G2", chart_bar, {"x_scale": 1.25, "y_scale": 1.15})

        # NOVO: Gráfico % por dia da semana (UNID)
        ws_cw = writer.sheets["corte_semana"]
        chart_dow = wb.add_chart({"type": "column"})
        col_dow   = corte_semana.columns.get_loc("DOW")
        col_tx_op = corte_semana.columns.get_loc("TX_CORTE_OPER_UN")
        col_tx_cm = corte_semana.columns.get_loc("TX_CORTE_COM_UN")
        m = len(corte_semana)
        chart_dow.add_series({
            "name": "TX_CORTE_OPER_UN",
            "categories": ["corte_semana", 1, col_dow, m, col_dow],
            "values":     ["corte_semana", 1, col_tx_op, m, col_tx_op],
            "data_labels": {"value": True, "font": {"color": "white"}},
        })
        chart_dow.add_series({
            "name": "TX_CORTE_COM_UN",
            "categories": ["corte_semana", 1, col_dow, m, col_dow],
            "values":     ["corte_semana", 1, col_tx_cm, m, col_tx_cm],
            "data_labels": {"value": True, "font": {"color": "white"}},
        })
        _darkify(chart_dow, "Percentual de Corte por Dia da Semana (UN)", percent_axis=True)
        ws_cw.insert_chart("N2", chart_dow, {"x_scale": 1.25, "y_scale": 1.1})

    return {
        "prod_dia": df_prod_dia,
        "comprador": df_comprador,
        "totais_dia": totais_dia,
        "top_compradores": top_compradores,
        "corte_semana": corte_semana,
    }


# ------------------------- CLI ------------------------- #
if __name__ == "__main__":
    import argparse
    import tkinter as tk
    from tkinter import filedialog

    parser = argparse.ArgumentParser(
        description="Processa TXT de cortes com normalização e dashboard Excel (tema escuro)."
    )
    parser.add_argument("--input", help="Caminho do arquivo TXT (';').")
    parser.add_argument("--output", help="Caminho do Excel (.xlsx). Se ausente, salva ao lado do TXT com _dashboard.xlsx")
    parser.add_argument("--chunksize", type=int, default=200_000, help="Linhas por chunk.")
    parser.add_argument("--encoding", default="utf-8", help="Ex.: 'utf-8' ou 'latin-1'.")
    args = parser.parse_args()

    txt_path = args.input
    xlsx_out = args.output

    if not txt_path:
        root = tk.Tk(); root.withdraw()
        txt_path = filedialog.askopenfilename(
            title="Selecione o arquivo TXT de cortes",
            filetypes=[("Arquivos TXT", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        if not txt_path:
            raise SystemExit("Nenhum arquivo TXT selecionado.")

    if not xlsx_out:
        base = os.path.splitext(txt_path)[0]
        xlsx_out = base + "_dashboard.xlsx"

    process_txt(txt_path, xlsx_out, chunksize=args.chunksize, encoding=args.encoding)
