# -*- coding: utf-8 -*-
"""
convert.py — Janela única em Tkinter para extrair comprovantes:
[Selecionar Relatório]  [Selecionar Comprovantes]  [Gerar]

Requisitos:
    pip install pypdf    # (ou PyPDF2 como fallback)
"""

# --- silencia o warning de depreciação do cryptography (opcional) ---
import warnings
try:
    from cryptography.utils import CryptographyDeprecationWarning
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
except Exception:
    pass

import os, re, unicodedata, zipfile, sys, traceback, csv
from pathlib import Path

# PDF libs (pypdf preferido; fallback PyPDF2)
try:
    from pypdf import PdfReader, PdfWriter
except Exception:
    from PyPDF2 import PdfReader, PdfWriter

# ------------------ Lógica de processamento ------------------
def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def read_pdf_texts(pdf_path: str):
    reader = PdfReader(pdf_path)
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")
    return texts

def safe_filename(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9\-_. ]+", "", name).strip().replace(" ", "_")
    return base[:120] or "sem_nome"

def group_contiguous(pages):
    if not pages: return []
    pages = sorted(set(pages))
    groups = []; start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1: prev = p
        else:
            groups.append((start, prev)); start = prev = p
    groups.append((start, prev))
    return groups

def extrair_comprovantes(relatorio_pdf: str, macro_pdf: str, pasta_saida: str) -> dict:
    out_dir = Path(pasta_saida); out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Ler nomes do relatório
    rel_all = "\n".join(read_pdf_texts(relatorio_pdf))
    nome_cands = set()

    # padrão comum: "123456 - NOME ..."
    for m in re.finditer(r"\b\d{4,}\s*-\s*([A-ZÁÀÂÃÉÈÊÍÌÓÒÔÕÚÙÇ][A-ZÁÀÂÃÉÈÊÍÌÓÒÔÕÚÙÇ ]{4,})", rel_all):
        name = m.group(1).strip()
        name = re.split(r"\s{2,}|\s+\d{1,3}[.,]\d{2}\b", name)[0].strip()
        nome_cands.add(name)

    # fallback: 2+ palavras maiúsculas
    for m in re.finditer(r"\b([A-ZÁÀÂÃÉÈÊÍÌÓÒÔÕÚÙÇ]{2,}(?:\s+[A-ZÁÀÂÃÉÈÊÍÌÓÒÔÕÚÙÇ]{2,}){1,})\b", rel_all):
        cand = m.group(1).strip()
        if len(cand.split()) >= 2 and len(cand) >= 8:
            nome_cands.add(cand)

    norm_to_original = {}
    for name in nome_cands:
        n = norm_text(name)
        if len(n) < 6 or n.isdigit(): continue
        if any(stop in n for stop in [
            "CONTAS A PAGA","TOTAL","EMPRESA","VALOR","ESPECIE","ESPÉCIE","BANCO","PESSOA",
            "QUITACAO","VENCIMENTO","PAGO","ORIGINAL","LIQUIDO","JUROS","MULTA","DESC"
        ]): continue
        norm_to_original.setdefault(n, name)

    # 2) Indexar o macro
    macro_reader = PdfReader(macro_pdf)
    macro_norm = [norm_text(t) for t in read_pdf_texts(macro_pdf)]

    # 3) Matching tolerante
    name_to_pages = {}
    for nname, orig in norm_to_original.items():
        tokens = [t for t in nname.split() if len(t) >= 3]
        hits = []
        for idx, page_norm in enumerate(macro_norm):
            token_hits = sum(1 for t in tokens if t in page_norm)
            if nname in page_norm or token_hits >= min(2, max(1, len(tokens))):
                hits.append(idx)
        if hits:
            name_to_pages[orig] = hits

    # 4) Gerar PDFs
    resumo_rows = []
    for name, pages in name_to_pages.items():
        for (a, b) in group_contiguous(pages):
            writer = PdfWriter()
            for p in range(a, b+1):
                writer.add_page(macro_reader.pages[p])
            fname = f"{safe_filename(name)}_{a+1:03d}-{b+1:03d}.pdf"
            fpath = Path(pasta_saida) / fname
            with open(fpath, "wb") as f:
                writer.write(f)
            resumo_rows.append((name, f"{a+1}-{b+1}", str(fpath)))

    # 5) CSV + ZIP
    csv_path = Path(pasta_saida) / "resumo_extracao.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        cw = csv.writer(f); cw.writerow(["nome_do_relatorio","paginas_macro","arquivo_gerado"])
        cw.writerows(resumo_rows)

    zip_path = Path(pasta_saida).with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for _,_,path in resumo_rows:
            zf.write(path, arcname=Path(path).name)
        zf.write(csv_path, arcname=csv_path.name)

    return {
        "total_nomes_encontrados_no_relatorio": len(norm_to_original),
        "total_comprovantes_gerados": len(resumo_rows),
        "pasta_saida": str(Path(pasta_saida).resolve()),
        "csv": str(csv_path.resolve()),
        "zip": str(zip_path.resolve()),
    }

# ------------------ GUI Tkinter (janela única) ------------------
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Extrair Comprovantes")
        self.geometry("720x260")
        self.minsize(640, 240)

        self.relatorio_path = tk.StringVar()
        self.macro_path = tk.StringVar()
        self.saida_dir = tk.StringVar(value=str(Path.cwd() / "comprovantes_out"))
        self.status = tk.StringVar(value="Selecione os arquivos e clique em GERAR.")

        pad = {"padx": 12, "pady": 8}

        # Linha 1: Relatório
        ttk.Button(self, text="Relatório (PDF)...", command=self.pick_relatorio).grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.relatorio_path).grid(row=0, column=1, columnspan=3, sticky="we", **pad)

        # Linha 2: Comprovantes (macro)
        ttk.Button(self, text="Comprovantes (PDF macro)...", command=self.pick_macro).grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.macro_path).grid(row=1, column=1, columnspan=3, sticky="we", **pad)

        # Linha 3: Pasta saída
        ttk.Button(self, text="Pasta de saída...", command=self.pick_saida).grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.saida_dir).grid(row=2, column=1, columnspan=3, sticky="we", **pad)

        # Status
        ttk.Label(self, textvariable=self.status, foreground="#444").grid(row=3, column=0, columnspan=4, sticky="w", **pad)

        # Ação
        ttk.Button(self, text="GERAR", command=self.on_gerar).grid(row=4, column=2, sticky="e", **pad)
        ttk.Button(self, text="FECHAR", command=self.destroy).grid(row=4, column=3, sticky="w", **pad)

        for c in range(1, 4):
            self.columnconfigure(c, weight=1)

    def pick_relatorio(self):
        p = filedialog.askopenfilename(title="Selecione o RELATÓRIO (PDF)", filetypes=[("PDF", "*.pdf")])
        if p: self.relatorio_path.set(p)

    def pick_macro(self):
        p = filedialog.askopenfilename(title="Selecione o PDF MACRO de COMPROVANTES", filetypes=[("PDF", "*.pdf")])
        if p: self.macro_path.set(p)

    def pick_saida(self):
        d = filedialog.askdirectory(title="Selecione a pasta de saída")
        if d: self.saida_dir.set(d)

    def on_gerar(self):
        rel = self.relatorio_path.get().strip()
        mac = self.macro_path.get().strip()
        out = self.saida_dir.get().strip() or str(Path.cwd() / "comprovantes_out")

        if not rel or not mac:
            messagebox.showwarning("Faltando arquivo", "Selecione o RELATÓRIO e o PDF de COMPROVANTES.")
            return
        if not os.path.isfile(rel) or not rel.lower().endswith(".pdf"):
            messagebox.showerror("Arquivo inválido", "O RELATÓRIO deve ser um PDF válido.")
            return
        if not os.path.isfile(mac) or not mac.lower().endswith(".pdf"):
            messagebox.showerror("Arquivo inválido", "O arquivo de COMPROVANTES deve ser um PDF válido.")
            return

        try:
            self.status.set("Processando... aguarde.")
            self.update_idletasks()
            result = extrair_comprovantes(rel, mac, out)
            self.status.set("Concluído.")
            msg = (
                "Concluído!\n\n"
                f"Nomes no relatório: {result['total_nomes_encontrados_no_relatorio']}\n"
                f"Comprovantes gerados: {result['total_comprovantes_gerados']}\n\n"
                f"Pasta: {result['pasta_saida']}\nCSV: {result['csv']}\nZIP: {result['zip']}"
            )
            if messagebox.askyesno("Sucesso", msg + "\n\nAbrir a pasta de saída?"):
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(result["pasta_saida"])
                    elif sys.platform == "darwin":
                        os.system(f'open "{result["pasta_saida"]}"')
                    else:
                        os.system(f'xdg-open "{result["pasta_saida"]}"')
                except Exception:
                    pass
        except Exception as e:
            self.status.set("Erro.")
            traceback.print_exc()
            messagebox.showerror("Erro ao gerar", f"{type(e).__name__}: {e}")

if __name__ == "__main__":
    # iniciar a janela imediatamente
    app = App()
    app.mainloop()
