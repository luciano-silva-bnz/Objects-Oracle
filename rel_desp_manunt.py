import os
import re
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox

# ---------------------------
# Helpers de normalização
# ---------------------------

def norm_text(s: object) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s

def norm_date(s: object) -> str:
    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")

def format_date_br(s: object) -> str:
    if pd.isna(s):
        return ""
    dt = pd.to_datetime(str(s), errors="coerce", dayfirst=True)
    if pd.isna(dt):
        return str(s)
    return dt.strftime("%d/%m/%Y")

def format_currency_br(s: object) -> str:
    if pd.isna(s):
        return ""
    text = str(s).strip()
    if not text:
        return ""
    # Remove prefixos/sufixos n?o num?ricos (R$, espa?os etc.)
    clean = re.sub(r"[^\d,.-]", "", text)

    # Heur?stica sem usar decimal/thousands (compat?vel com pandas antigos)
    if "," in clean and "." in clean:
        parse_str = clean.replace(".", "").replace(",", ".")
    elif "," in clean:
        parse_str = clean.replace(".", "").replace(",", ".")
    else:
        parse_str = clean

    numeric = pd.to_numeric(parse_str, errors="coerce")
    if pd.isna(numeric):
        return text
    return f"{numeric:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def norm_supplier(s: object) -> str:
    s = norm_text(s)
    # remove sufixo " - 2418" (código ao final)
    s = re.sub(r"\s*-\s*\d+\s*$", "", s)
    return s

def extract_nf_num_from_historico(hist: object) -> str:
    """
    Extrai o número da NF do texto do Histórico:
    Ex: " ... na NF nº 2529 de ..." -> "2529"
    """
    if pd.isna(hist):
        return ""
    m = re.search(r"NF\s*n[ºo]\s*([0-9]+)", str(hist), flags=re.IGNORECASE)
    return m.group(1) if m else ""

def extract_num_from_titulo(titulo: object) -> str:
    """
    Extrai a parte numérica inicial do TÍTULO:
    Ex: "2529/001-1" -> "2529"
    """
    if pd.isna(titulo):
        return ""
    m = re.match(r"\s*([0-9]+)", str(titulo))
    return m.group(1) if m else ""

def agg_obstitulo(series: pd.Series):
    vals = [v for v in series.dropna().astype(str).tolist() if v.strip() and v.strip().lower() != "nan"]
    if not vals:
        return np.nan
    seen = []
    for v in vals:
        if v not in seen:
            seen.append(v)
    return " | ".join(seen)

# ---------------------------
# Validação de estrutura
# ---------------------------

REQ_DATA = {"Loja", "Data", "Fornecedor", "Histórico"}
REQ_DESP = {"NROEMPRESA", "DTACONTABILIZA", "PESSOA", "TÍTULO", "OBSTÍTULO"}

def validate_columns(df: pd.DataFrame, required: set, nome: str) -> None:
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise ValueError(
            f"Estrutura inválida em {nome}. Faltando coluna(s): {', '.join(missing)}"
        )

# ---------------------------
# Processamento principal
# ---------------------------

def process_files(path_data_xlsx: str, path_despesas_csv: str, output_path: str) -> dict:
    # Lê arquivos
    df_data = pd.read_excel(path_data_xlsx, dtype=str)

    # Tenta detectar separador do CSV (padrão ; no seu caso)
    with open(path_despesas_csv, "rb") as f:
        raw = f.read(4096)
    raw_text = raw.decode("latin1", errors="ignore")
    sep_guess = ";" if raw_text.count(";") >= raw_text.count(",") else ","

    df_desp = pd.read_csv(path_despesas_csv, sep=sep_guess, dtype=str, encoding="latin1")

    # Valida estrutura
    validate_columns(df_data, REQ_DATA, "data.xlsx")
    validate_columns(df_desp, REQ_DESP, "despesas.csv")

    # Monta chave temporária para data.xlsx
    tmp_data = pd.DataFrame(index=df_data.index)
    tmp_data["filial"] = df_data["Loja"].map(norm_text)
    tmp_data["dt_cont"] = df_data["Data"].map(norm_date)
    tmp_data["nota"] = df_data["Histórico"].map(extract_nf_num_from_historico)
    tmp_data["fornecedor_key"] = df_data["Fornecedor"].map(norm_supplier)
    tmp_data["chave"] = (
        tmp_data["filial"] + "|" +
        tmp_data["dt_cont"] + "|" +
        tmp_data["nota"] + "|" +
        tmp_data["fornecedor_key"]
    )

    # Monta chave temporária para despesas.csv
    tmp_desp = pd.DataFrame(index=df_desp.index)
    tmp_desp["filial"] = df_desp["NROEMPRESA"].map(norm_text)
    tmp_desp["dt_cont"] = df_desp["DTACONTABILIZA"].map(norm_date)
    tmp_desp["nota"] = df_desp["TÍTULO"].map(extract_num_from_titulo)
    tmp_desp["fornecedor_key"] = df_desp["PESSOA"].map(norm_supplier)
    tmp_desp["chave"] = (
        tmp_desp["filial"] + "|" +
        tmp_desp["dt_cont"] + "|" +
        tmp_desp["nota"] + "|" +
        tmp_desp["fornecedor_key"]
    )
    tmp_desp["OBSTÍTULO"] = df_desp["OBSTÍTULO"]

    # Agrega para evitar duplicar linhas em caso de chave repetida no CSV
    df_desp_agg = tmp_desp.groupby("chave", as_index=False).agg({"OBSTÍTULO": agg_obstitulo})

    # Faz merge sem manter colunas auxiliares
    df_out = df_data.copy()
    df_out["_chave_tmp"] = tmp_data["chave"].values

    df_out = df_out.merge(df_desp_agg, left_on="_chave_tmp", right_on="chave", how="left")
    df_out.drop(columns=["_chave_tmp", "chave"], inplace=True)

    # Garante que só adicionamos OBSTÍTULO (se já existir, substitui)
    # (Se você preferir não substituir, dá pra mudar esta lógica.)
    # Aqui já está ok pois o merge cria/atualiza OBSTÍTULO.

    # Formata coluna de data no padrao brasileiro dd/mm/aaaa
    if "Data" in df_out.columns:
        df_out["Data"] = df_out["Data"].apply(format_date_br)

    # Formata coluna de valor no padrao brasileiro
    for col_val in ("Valor", "VALOR"):
        if col_val in df_out.columns:
            df_out[col_val] = df_out[col_val].apply(format_currency_br)

    # Salva
    df_out.to_excel(output_path, index=False)

    # Estatísticas
    filled = int(df_out["OBSTÍTULO"].notna().sum()) if "OBSTÍTULO" in df_out.columns else 0
    total = int(len(df_out))

    return {
        "sep_detected": sep_guess,
        "total_rows": total,
        "filled_obstitulo": filled,
        "output_path": output_path,
    }

# ---------------------------
# UI Tkinter
# ---------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Adicionar OBSTÍTULO (despesas.csv -> BI.xlsx)")
        self.geometry("720x320")

        self.path_data = tk.StringVar()
        self.path_desp = tk.StringVar()
        self.path_out = tk.StringVar()

        # Data.xlsx
        tk.Label(self, text="Selecione o BI.xlsx:").pack(anchor="w", padx=12, pady=(12, 2))
        frm1 = tk.Frame(self)
        frm1.pack(fill="x", padx=12)
        tk.Entry(frm1, textvariable=self.path_data).pack(side="left", fill="x", expand=True)
        tk.Button(frm1, text="Procurar...", command=self.pick_data).pack(side="left", padx=6)

        # Despesas.csv
        tk.Label(self, text="Selecione o despesas.csv:").pack(anchor="w", padx=12, pady=(12, 2))
        frm2 = tk.Frame(self)
        frm2.pack(fill="x", padx=12)
        tk.Entry(frm2, textvariable=self.path_desp).pack(side="left", fill="x", expand=True)
        tk.Button(frm2, text="Procurar...", command=self.pick_desp).pack(side="left", padx=6)

        # Output
        tk.Label(self, text="Salvar como (xlsx):").pack(anchor="w", padx=12, pady=(12, 2))
        frm3 = tk.Frame(self)
        frm3.pack(fill="x", padx=12)
        tk.Entry(frm3, textvariable=self.path_out).pack(side="left", fill="x", expand=True)
        tk.Button(frm3, text="Escolher...", command=self.pick_out).pack(side="left", padx=6)

        # Run
        tk.Button(self, text="Processar", height=2, command=self.run).pack(pady=14)

        tk.Label(
            self,
            text="Obs.: Se não encontrar OBSTÍTULO, a célula ficará vazia (NaN).",
            fg="#444"
        ).pack()

    def pick_data(self):
        p = filedialog.askopenfilename(
            title="Selecione o BI.xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if p:
            self.path_data.set(p)
            if not self.path_out.get():
                base = os.path.splitext(os.path.basename(p))[0]
                out_default = os.path.join(os.path.dirname(p), f"{base}_com_obstitulo.xlsx")
                self.path_out.set(out_default)

    def pick_desp(self):
        p = filedialog.askopenfilename(
            title="Selecione o despesas.csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if p:
            self.path_desp.set(p)

    def pick_out(self):
        p = filedialog.asksaveasfilename(
            title="Salvar arquivo final",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if p:
            self.path_out.set(p)

    def run(self):
        try:
            data_p = self.path_data.get().strip()
            desp_p = self.path_desp.get().strip()
            out_p = self.path_out.get().strip()

            if not data_p or not os.path.exists(data_p):
                raise FileNotFoundError("Selecione um arquivo data.xlsx válido.")
            if not desp_p or not os.path.exists(desp_p):
                raise FileNotFoundError("Selecione um arquivo despesas.csv válido.")
            if not out_p:
                raise ValueError("Escolha o caminho de saída (Salvar como).")

            stats = process_files(data_p, desp_p, out_p)

            messagebox.showinfo(
                "Concluído",
                "Processamento finalizado!\n\n"
                f"Separador CSV detectado: {stats['sep_detected']}\n"
                f"Linhas no data.xlsx: {stats['total_rows']}\n"
                f"OBSTÍTULO preenchido: {stats['filled_obstitulo']}\n\n"
                f"Arquivo gerado:\n{stats['output_path']}"
            )

        except Exception as e:
            messagebox.showerror("Erro", str(e))

if __name__ == "__main__":
    app = App()
    app.mainloop()
