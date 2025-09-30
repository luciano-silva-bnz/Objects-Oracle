import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from fpdf import FPDF
import os
from datetime import date
from pessoa_rj.logging_config import get_logger
from pessoa_rj.config import ASSETS_DIR

logger = get_logger(__name__)

COMPANY_NAME_DEFAULT = "Bonanza Supermercados LTDA"

# ---------------- Utilitário: Data por extenso ---------------- #
def data_por_extenso(dt=None):
    if dt is None:
        dt = date.today()
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    return f"Caruaru, {dt.day} de {meses[dt.month - 1]} de {dt.year}"

# ---------------- PDF com cabeçalho/rodapé institucionais ---------------- #
class ReportPDF(FPDF):
    def __init__(self, company_name=COMPANY_NAME_DEFAULT, logo_path=None, watermark_path=None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.company_name = company_name
        self.logo_path = logo_path
        self.watermark_path = watermark_path

    def header(self):
        # Logo (se houver)
        if self.logo_path and Path(self.logo_path).exists():
            try:
                self.image(self.logo_path, x=12, y=10, w=28)
            except Exception:
                pass

        x_offset = 12 + (28 + 6 if self.logo_path and Path(self.logo_path).exists() else 0)
        self.set_xy(x_offset, 12)
        self.set_font("Arial", "B", 14)
        title = self.company_name.strip() or COMPANY_NAME_DEFAULT
        self.cell(0, 8, title, ln=1)

        self.set_x(x_offset)
        self.set_font("Arial", "", 11)
        # >>> Subtítulo ajustado conforme pedido:
        self.cell(0, 7, "Recuperação Judicial - Classe Trabalhista", ln=1)

        self.set_y(28)
        self.set_draw_color(200, 200, 200)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(4)

    def footer(self):
        if self.watermark_path and Path(self.watermark_path).exists():
            try:
                page_width = self.w
                watermark_height = page_width * 78 / 1000  # maintain 1000x78 asset ratio
                y_position = self.h - watermark_height
                self.image(self.watermark_path, x=0, y=y_position, w=page_width)
            except Exception:
                pass
        self.set_y(-15)
        self.set_draw_color(220, 220, 220)
        self.line(12, self.get_y(), 198, self.get_y())
        self.set_y(-12)
        self.set_font("Arial", "I", 9)
        self.cell(0, 8, f"Página {self.page_no()}/{{nb}}", align="C")

# ---------------- App Tkinter ---------------- #
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Extrair Dados - Base RJ + Mov. de Títulos C5")
        self.root.geometry("1250x650")
        logger.info('Inicializando gerador de comprovantes RJ')

        # Logo no mesmo diretório
        script_dir = Path(__file__).resolve().parent
        candidate_dirs = [ASSETS_DIR, script_dir]
        self.logo_path = None
        for base_dir in candidate_dirs:
            for name in ["Bonanza---logo_Prancheta 1.png", "bonanza_logo.png", "logo.png"]:
                p = base_dir / name
                if p.exists():
                    self.logo_path = str(p)
                    break
            if self.logo_path:
                break

        watermark_file = None
        for base_dir in candidate_dirs:
            candidate = base_dir / "rodape.png"
            if candidate.exists():
                watermark_file = candidate
                break
        self.watermark_path = str(watermark_file) if watermark_file else None

        self.trabalhista = None
        self.programacao = None
        self.merged_data_base = None  # base sem filtro
        self.merged_data = None       # visão filtrada
        self.check_vars = []

        # Barra superior
        top = tk.Frame(root)
        top.pack(pady=6)

        self.btn_select_trab = tk.Button(top, text="Selecione Planilha Base RJ", command=self.load_trabalhista)
        self.btn_select_trab.grid(row=0, column=0, padx=6)

        self.btn_select_prog = tk.Button(top, text="Seleciona Planilha Mov. de Títulos C5", command=self.load_programacao, state="disabled")
        self.btn_select_prog.grid(row=0, column=1, padx=6)

        # Busca (live)
        search_frame = tk.Frame(root)
        search_frame.pack(pady=5)
        tk.Label(search_frame, text="Pesquisar:").pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=6)
        self.search_entry.bind("<KeyRelease>", self.on_search_key)  # filtra enquanto digita
        tk.Button(search_frame, text="Buscar", command=self.search_now).pack(side=tk.LEFT)

        # Tabela
        self.table_frame = tk.Frame(root)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.scroll_y = tk.Scrollbar(self.table_frame, orient=tk.VERTICAL)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ("select", "credor", "cpf", "fgts", "verba_rescisoria", "qtd_parcelas", "valor_parcela", "programacao")
        self.tree = ttk.Treeview(
            self.table_frame,
            columns=cols,
            show="headings",
            yscrollcommand=self.scroll_y.set,
            height=18
        )
        headers = {
            "select": "Selecionar",
            "credor": "CREDOR",
            "cpf": "CPF",
            "fgts": "FGTS",
            "verba_rescisoria": "VERBA RESCISÓRIA",
            "qtd_parcelas": "QTD PARCELAS",
            "valor_parcela": "VALOR PARCELA",
            "programacao": "PROGRAMAÇÃO DE PAGAMENTO"
        }
        widths = {
            "select": 95, "credor": 240, "cpf": 130, "fgts": 140,
            "verba_rescisoria": 140, "qtd_parcelas": 110, "valor_parcela": 120, "programacao": 360
        }
        anchors = {
            "select": "center", "credor": "w", "cpf": "center", "fgts": "e",
            "verba_rescisoria": "e", "qtd_parcelas": "center", "valor_parcela": "e", "programacao": "w"
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor=anchors[c])

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.scroll_y.config(command=self.tree.yview)

        # Exportar
        self.btn_export = tk.Button(root, text="Gerar PDF", command=self.export_pdf, state="disabled")
        self.btn_export.pack(pady=8)

    # ---------- Helpers ---------- #
    def format_currency(self, val):
        try:
            return f"R$ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "" if pd.isna(val) else str(val)

    def mask_cpf(self, cpf_original, cpf_norm):
        # Sempre prioriza o CPF normalizado (11 dígitos) para mascarar corretamente
        d = re.sub(r"\D", "", str(cpf_norm or ""))
        d = d.zfill(11)
        if len(d) == 11:
            return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
        # fallback no original (quase nunca)
        d2 = re.sub(r"\D", "", str(cpf_original or ""))
        d2 = d2.zfill(11)
        if len(d2) == 11:
            return f"{d2[0:3]}.{d2[3:6]}.{d2[6:9]}-{d2[9:11]}"
        return str(cpf_original or cpf_norm)

    def sanitize_filename(self, name):
        """Remove caracteres inválidos para nome de arquivo e limita tamanho."""
        if not name:
            return "documento"
        cleaned = re.sub(r'[<>:"/\\|?*\n\r\t]+', "_", str(name))
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:150] or "documento"

    # ---------- Seleções ---------- #
    def load_trabalhista(self):
        filepath = filedialog.askopenfilename(
            title="Selecione Planilha Base RJ",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not filepath:
            logger.info('Seleção da Planilha Base RJ cancelada pelo usuário')
            return
        try:
            df = pd.read_excel(filepath, sheet_name="Trabalhista", usecols="B,C,AP,AQ,AR,AS", skiprows=3)
            # Renomear colunas conforme solicitado
            df.columns = ["CREDOR", "CPF", "FGTS", "VERBA RESCISÓRIA", "QTD PARCELAS", "VALOR PARCELA"]

            df["CPF_ORIGINAL"] = df["CPF"].astype(str)
            df["CPF_NORM"] = df["CPF_ORIGINAL"].str.replace(r"\D", "", regex=True).str.zfill(11)

            self.trabalhista = df.dropna(how="all").reset_index(drop=True)
            logger.info('Planilha Base RJ carregada (%d linhas) a partir de %s', len(self.trabalhista), filepath)
            messagebox.showinfo("OK", "Planilha Base RJ carregada.")
            self.btn_select_prog.config(state="normal")
        except Exception as e:
            logger.exception('Erro ao carregar planilha Base RJ: %s', filepath)
            messagebox.showerror("Erro", f"Não foi possível carregar a Planilha Base RJ:\n{e}")

    def load_programacao(self):
        filepath = filedialog.askopenfilename(
            title="Seleciona Planilha Mov. de Títulos C5",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not filepath:
            logger.info('Seleção da Planilha C5 cancelada pelo usuário')
            return
        try:
            df = pd.read_excel(filepath, sheet_name="Plan1", usecols="B,F,H", skiprows=1)
            df.columns = ["CPF", "PROGRAMAÇÃO", "VALOR_PROG"]

            df["CPF_ORIGINAL"] = df["CPF"].astype(str)
            df["CPF_NORM"] = df["CPF_ORIGINAL"].str.replace(r"\D", "", regex=True).str.zfill(11)

            self.programacao = df.dropna(subset=["CPF_NORM", "PROGRAMAÇÃO"]).reset_index(drop=True)
            logger.info('Planilha C5 carregada (%d linhas) a partir de %s', len(self.programacao), filepath)
            messagebox.showinfo("OK", "Planilha Mov. de Títulos C5 carregada.")
            self.merge_data()
        except Exception as e:
            logger.exception('Erro ao carregar planilha C5: %s', filepath)
            messagebox.showerror("Erro", f"Não foi possível carregar a Planilha Mov. de Títulos C5:\n{e}")

    def merge_data(self):
        trab = self.trabalhista.copy()
        prog = self.programacao.copy()

        # Converte datas e descarta inválidas
        prog["PROGRAMAÇÃO"] = pd.to_datetime(prog["PROGRAMAÇÃO"], errors="coerce")
        prog = prog.dropna(subset=["PROGRAMAÇÃO"])

        # Formata data (dd/mm/aaaa)
        prog["DATA_STR"] = prog["PROGRAMAÇÃO"].dt.strftime("%d/%m/%Y")

        # Formata valor da parcela (coluna H) em R$
        def _fmt_val(v):
            try:
                return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                return ""

        prog["VALOR_STR"] = prog["VALOR_PROG"].apply(_fmt_val)

        # Monta "DATA - R$ VALOR" (se não houver valor, fica só a data)
        prog["ITEM"] = prog.apply(
            lambda r: f"{r['DATA_STR']} - {r['VALOR_STR']}" if r["VALOR_STR"] else r["DATA_STR"],
            axis=1
        )

        # Agrupa todos os itens por CPF_NORM em uma única string
        prog_grouped = prog.groupby("CPF_NORM")["ITEM"].apply(lambda x: ", ".join(x)).reset_index()

        merged = trab.merge(prog_grouped, on="CPF_NORM", how="left")
        self.merged_data_base = merged.rename(columns={"ITEM": "PROGRAMACAO"})
        self.merged_data = self.merged_data_base.copy()
        logger.info('Dados combinados: base=%d, programações=%d', len(trab), len(prog_grouped))
        self.populate_table()
        self.btn_export.config(state="normal")

    def populate_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.check_vars.clear()

        for _, row in self.merged_data.iterrows():
            credor = "" if pd.isna(row["CREDOR"]) else str(row["CREDOR"])
            cpf = row["CPF_ORIGINAL"]  # (se quiser, troque por self.mask_cpf(row["CPF_ORIGINAL"], row.get("CPF_NORM","")))
            fgts = self.format_currency(row["FGTS"])
            verba = self.format_currency(row["VERBA RESCISÓRIA"])
            qtd = "" if pd.isna(row["QTD PARCELAS"]) else str(int(row["QTD PARCELAS"]))
            valor = self.format_currency(row["VALOR PARCELA"])
            programacao = "" if pd.isna(row["PROGRAMACAO"]) else row["PROGRAMACAO"]

            var = tk.BooleanVar(value=False)
            self.check_vars.append((var, credor, cpf, row.get("CPF_NORM", ""), fgts, verba, qtd, valor, programacao))

            self.tree.insert("", "end", values=("☐", credor, cpf, fgts, verba, qtd, valor, programacao))

        self.tree.bind("<Button-1>", self.toggle_checkbox)

    # Busca live
    def on_search_key(self, event):
        self.apply_filter(self.search_entry.get())

    def search_now(self):
        self.apply_filter(self.search_entry.get())

    def apply_filter(self, text):
        q = (text or "").lower().strip()
        if not isinstance(self.merged_data_base, pd.DataFrame):
            return
        if not q:
            self.merged_data = self.merged_data_base.copy()
        else:
            self.merged_data = self.merged_data_base[
                self.merged_data_base.apply(lambda r: q in str(r.values).lower(), axis=1)
            ].reset_index(drop=True)
        self.populate_table()

    def toggle_checkbox(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            if col == "#1":
                item = self.tree.identify_row(event.y)
                if item:
                    index = self.tree.index(item)
                    var, *rest = self.check_vars[index]
                    var.set(not var.get())
                    self.tree.set(item, "select", "☑" if var.get() else "☐")

    # ---------- Exportar PDF ---------- #
    def _render_one_pdf(self, filepath, credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao):
        pdf = ReportPDF(company_name=COMPANY_NAME_DEFAULT, logo_path=self.logo_path, watermark_path=self.watermark_path)
        logger.info('Gerando PDF para %s em %s', credor, filepath)
        pdf.alias_nb_pages()
        pdf.set_margins(left=12, top=35, right=12)
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()

        # Dados do credor
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 9, "Dados do Credor", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"CREDOR: {credor}", ln=True)
        pdf.cell(0, 7, f"CPF: {self.mask_cpf(cpf_original, cpf_norm)}", ln=True)
        pdf.ln(2)

        # --- Tabela de valores ---
        th = 8
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(58, th, "FGTS + MULTA FGTS (40%)", border=1, align="C", fill=True)
        pdf.cell(50, th, "VERBA RESCISÓRIA",        border=1, align="C", fill=True)
        pdf.cell(35, th, "QTD PARCELAS",            border=1, align="C", fill=True)
        pdf.cell(40, th, "VALOR PARCELA",           border=1, align="C", fill=True)
        pdf.ln(th)

        pdf.set_font("Arial", "", 11)
        fgts_exib = (fgts.strip() + "*") if fgts else "-"  # asterisco após o valor
        pdf.cell(58, th, fgts_exib, border=1, align="C")
        pdf.cell(50, th, verba or "-", border=1, align="C")
        pdf.cell(35, th, qtd or "-",   border=1, align="C")
        pdf.cell(40, th, valor or "-", border=1, align="C")
        pdf.ln(th + 2)

        # Nota solicitada + Programação
        pdf.set_font("Arial", "I", 10)
        pdf.multi_cell(0, 6, "*O FGTS será quitado integralmente, em uma única parcela, até o término da programação abaixo, com a devida correção monetária. O valor será creditado em sua conta vinculada ao FGTS.")
        pdf.ln(1)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 9, "Programação de Pagamento", ln=True)
        pdf.set_font("Arial", "", 11)
        if programacao:
            for item in str(programacao).split(", "):
                pdf.cell(0, 7, item, ln=True)   # "DD/MM/AAAA - R$ X.XXX,XX"
        else:
            pdf.cell(0, 7, "Sem programação encontrada.", ln=True)

        # --- Data por extenso (final, lado direito) ---
        pdf.ln(6)
        pdf.set_font("Arial", "I", 11)
        pdf.cell(0, 8, data_por_extenso(), ln=True, align="R")
        # (se quiser descer mais, troque o ln(6) por set_y(-30) ou similar)

        pdf.output(filepath)
        logger.info('PDF salvo em %s', filepath)

    def export_pdf(self):
        selected_rows = [rest for var, *rest in self.check_vars if var.get()]
        if not selected_rows:
            logger.warning('Exportação ignorada: nenhum item selecionado')
            messagebox.showwarning("Aviso", "Selecione ao menos um item para exportar.")
            return

        # 1 selecionado -> sugere nome do credor
        if len(selected_rows) == 1:
            credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao = selected_rows[0]
            suggested = self.sanitize_filename(credor) + ".pdf"
            output_file = filedialog.asksaveasfilename(
                title="Salvar PDF",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=suggested
            )
            if output_file:
                logger.info('Exportação única selecionada: %s -> %s', credor, output_file)
                try:
                    self._render_one_pdf(output_file, credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao)
                    logger.info('PDF gerado com sucesso: %s', output_file)
                    messagebox.showinfo("Sucesso", f"PDF salvo em:\n{output_file}")
                except Exception as e:
                    logger.exception('Falha ao gerar PDF para %s', credor)
                    messagebox.showerror("Erro", f"Não foi possível salvar o PDF:\n{e}")
            return

        # Vários -> pede pasta e salva 1 arquivo por credor
        out_dir = filedialog.askdirectory(title="Selecione a pasta para salvar os PDFs")
        if not out_dir:
            logger.info('Exportação múltipla cancelada: nenhuma pasta selecionada')
            return

        ok, fail = 0, 0
        for credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao in selected_rows:
            fname = self.sanitize_filename(credor) + ".pdf"
            fpath = os.path.join(out_dir, fname)
            try:
                logger.info('Gerando PDF em lote: %s', fpath)
                self._render_one_pdf(fpath, credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao)
                ok += 1
            except Exception:
                logger.exception('Falha ao gerar PDF em lote para %s', credor)
                fail += 1

        logger.info('Exportação múltipla concluída: sucesso=%s, falhas=%s, destino=%s', ok, fail, out_dir)
        message = f"{ok} arquivo(s) salvo(s) em:\n{out_dir}"
        if fail:
            message += f"\n{fail} arquivo(s) falharam ao salvar."
        messagebox.showinfo("Exportação concluída", message)

# ---------------- Run ---------------- #
def main():
    root = tk.Tk()
    app = App(root)
    logger.info('Aplicação de comprovantes iniciada')
    root.mainloop()
    logger.info('Aplicação de comprovantes encerrada')


if __name__ == "__main__":
    main()





