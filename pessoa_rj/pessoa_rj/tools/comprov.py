import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from fpdf import FPDF
import os
from datetime import date
from ..logging_config import get_logger
from ..config import ASSETS_DIR
from ..version import APP_VERSION, get_tool_window_title

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

# ---------------- PDF com cabeçalho institucionais ---------------- #
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
        self.root.title(get_tool_window_title("Extrair Dados - Base RJ + Mov. de Titulos C5"))
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
        self.row_records = []
        self.item_to_record = {}
        self.selected_keys = set()

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

        cols = ("select", "credor", "cpf", "fgts", "verba_rescisoria", "qtd_parcelas", "valor_parcela", "programação")
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
            "programação": "PROGRAMAÇÃO DE PAGAMENTO"
        }
        widths = {
            "select": 95, "credor": 240, "cpf": 130, "fgts": 140,
            "verba_rescisoria": 140, "qtd_parcelas": 110, "valor_parcela": 120, "programação": 360
        }
        anchors = {
            "select": "center", "credor": "w", "cpf": "center", "fgts": "e",
            "verba_rescisoria": "e", "qtd_parcelas": "center", "valor_parcela": "e", "programação": "w"
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor=anchors[c])

        self.tree.tag_configure('alert', background='#FFF3B0')
        self.tree.tag_configure('selected_row', background='#CCE5FF')
        self.tree.tag_configure('alert_selected', background='#FFD59E')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.scroll_y.config(command=self.tree.yview)
        self.tree.bind("<Button-1>", self.toggle_checkbox)
        self.tree.bind("<Double-1>", self._handle_tree_double_click)

        # Exportar
        self.btn_export = tk.Button(root, text="Gerar PDF", command=self.export_pdf, state="disabled")
        self.btn_export.pack(pady=8)

    # ---------- Helpers ---------- #
    def format_currency(self, val):
        if val is None:
            return ""
        if isinstance(val, str):
            cleaned = val.strip()
            if not cleaned or cleaned.lower() == "nan":
                return ""
            candidate = cleaned
        else:
            candidate = val
        try:
            number = float(candidate)
        except Exception:
            try:
                number = float(str(candidate).replace('.', '').replace(',', '.'))
            except Exception:
                return ""
        if pd.isna(number) or number != number:
            return ""
        return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
    def _to_decimal(self, series):
        if pd.api.types.is_numeric_dtype(series):
            return pd.to_numeric(series, errors="coerce")
        return pd.to_numeric(
            series.astype(str)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False),
            errors="coerce",
        )

    def load_trabalhista(self):
        filepath = filedialog.askopenfilename(
            title="Selecione Planilha Base RJ",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not filepath:
            logger.info('Seleção da Planilha Base RJ cancelada pelo usuário')
            return
        try:
            df = pd.read_excel(
                filepath,
                sheet_name="Trabalhista",
                usecols="B,C,AP,AQ,AR,AS",
                skiprows=3,
            )
            df.columns = [
                "CREDOR",
                "CPF",
                "FGTS",
                "VERBA RESCISÓRIA",
                "QTD PARCELAS",
                "VALOR PARCELA",
            ]

            df = df[df["CPF"].notna()]
            df = df[~df["CPF"].astype(str).str.strip().str.upper().eq("CPF")]
            df = df[~df["CREDOR"].astype(str).str.strip().str.upper().eq("CREDOR")]

            df["FGTS"] = self._to_decimal(df["FGTS"])
            df["VERBA RESCISÓRIA"] = self._to_decimal(df["VERBA RESCISÓRIA"])
            df["VALOR PARCELA"] = self._to_decimal(df["VALOR PARCELA"])
            df["QTD PARCELAS"] = pd.to_numeric(df["QTD PARCELAS"], errors="coerce")

            df["CPF_ORIGINAL"] = df["CPF"].astype(str)
            df["CPF_NORM"] = df["CPF_ORIGINAL"].str.replace(r"\D", "", regex=True).str.zfill(11)

            self.trabalhista = df.dropna(how="all").reset_index(drop=True)
            logger.info('Planilha Base RJ carregada (%d linhas) a partir de %s', len(self.trabalhista), filepath)
            messagebox.showinfo("OK", "Planilha Base RJ carregada.")
            self.btn_select_prog.config(state="normal")
        except Exception as e:
            logger.exception('Erro ao carregar planilha Base RJ: %s', filepath)
            messagebox.showerror("Erro", f"Não foi possível carregar a Planilha Base RJ\n{e}")

    def load_programacao(self):
        filepath = filedialog.askopenfilename(
            title="Seleciona Planilha Mov. de Títulos C5",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not filepath:
            logger.info('Seleção da Planilha C5 cancelada pelo usuário')
            return
        try:
            required_cols = [
                "BANCO",
                "AGENCIA",
                "DIGAGENCIA",
                "NROCONTA",
                "DIGCONTA",
                "TIPO_CONTA",
                "CNPJ/CPF",
                "DTAVENCIMENTO",
                "VLRNOMINAL",
            ]
            df = pd.read_excel(filepath, sheet_name="MOV_TITULOS")
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise ValueError(f"Colunas ausentes na planilha: {', '.join(missing)}")

            df = df[required_cols].copy()
            df.rename(
                columns={
                    "CNPJ/CPF": "CPF",
                    "DTAVENCIMENTO": "DATA_VENCIMENTO",
                    "VLRNOMINAL": "VALOR_NOMINAL",
                },
                inplace=True,
            )

            for col in ["BANCO", "AGENCIA", "DIGAGENCIA", "NROCONTA", "DIGCONTA", "TIPO_CONTA", "CPF"]:
                df[col] = df[col].astype(str).fillna("").str.strip()

            df["CPF_ORIGINAL"] = df["CPF"]
            df["CPF_NORM"] = df["CPF_ORIGINAL"].str.replace(r"\D", "", regex=True).str.zfill(11)
            df["PROGRAMACAO_DATA"] = pd.to_datetime(df["DATA_VENCIMENTO"], errors="coerce")

            if pd.api.types.is_numeric_dtype(df["VALOR_NOMINAL"]):
                df["VALOR_PROG"] = pd.to_numeric(df["VALOR_NOMINAL"], errors="coerce")
            else:
                valor_normalizado = (
                    df["VALOR_NOMINAL"]
                    .astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                )
                df["VALOR_PROG"] = pd.to_numeric(valor_normalizado, errors="coerce")

            self.programacao = df[df["CPF_NORM"].astype(str).str.strip() != ""].reset_index(drop=True)
            logger.info('Planilha C5 carregada (%d linhas) a partir de %s', len(self.programacao), filepath)
            messagebox.showinfo("OK", "Planilha Mov. de Títulos C5 carregada.")
            self.merge_data()
        except Exception as e:
            logger.exception('Erro ao carregar planilha C5: %s', filepath)
            messagebox.showerror("Erro", f"Não foi possível carregar a Planilha Mov. de Títulos C5\n{e}")

    def merge_data(self):
        trab = self.trabalhista.copy()
        prog = self.programacao.copy()

        def clean_str(value):
            if pd.isna(value):
                return ""
            return str(value).strip()

        def digits_only(value):
            return re.sub(r"\D", "", clean_str(value))

        def first_valid(series):
            for value in series:
                val = clean_str(value)
                if val and val.lower() != "nan":
                    return val
            return ""

        prog = prog[prog["CPF_NORM"].astype(str).str.strip() != ""].copy()

        prog_valid = prog.dropna(subset=["PROGRAMACAO_DATA"]).copy()
        prog_valid["DATA_STR"] = prog_valid["PROGRAMACAO_DATA"].dt.strftime("%d/%m/%Y")

        def _fmt_val(value):
            try:
                return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                return ""

        prog_valid["VALOR_STR"] = prog_valid["VALOR_PROG"].apply(_fmt_val)
        prog_valid["ITEM"] = prog_valid.apply(
            lambda row: f"{row['DATA_STR']} - {row['VALOR_STR']}" if row["VALOR_STR"] else row["DATA_STR"],
            axis=1,
        )

        prog_grouped = prog_valid.groupby("CPF_NORM")["ITEM"].apply(lambda values: ", ".join(values)).reset_index()
        prog_metrics = prog_valid.groupby("CPF_NORM").agg(
            PROG_TOTAL=("VALOR_PROG", "sum"),
            PROG_QTD=("ITEM", "count"),
        ).reset_index()

        prog_bank = prog.copy()
        prog_bank["BANCO_FMT"] = prog_bank["BANCO"].apply(lambda v: digits_only(v).zfill(3)[:3] if digits_only(v) else "")
        prog_bank["AGENCIA_FMT"] = prog_bank["AGENCIA"].apply(lambda v: digits_only(v).zfill(4)[:4] if digits_only(v) else "")
        prog_bank["DIGAGENCIA_FMT"] = prog_bank["DIGAGENCIA"].apply(lambda v: digits_only(v)[:1])

        def format_conta(value):
            digits = digits_only(value)
            if not digits:
                return ""
            stripped = digits.lstrip('0')
            cleaned = stripped or digits
            return cleaned[:15]

        prog_bank["NROCONTA_FMT"] = prog_bank["NROCONTA"].apply(format_conta)
        prog_bank["DIGCONTA_FMT"] = prog_bank["DIGCONTA"].apply(lambda v: digits_only(v)[:1])
        prog_bank["TIPO_CONTA_FMT"] = prog_bank["TIPO_CONTA"].apply(clean_str)

        bank_grouped = prog_bank.groupby("CPF_NORM").agg({
            "BANCO_FMT": first_valid,
            "AGENCIA_FMT": first_valid,
            "DIGAGENCIA_FMT": first_valid,
            "NROCONTA_FMT": first_valid,
            "DIGCONTA_FMT": first_valid,
            "TIPO_CONTA_FMT": first_valid,
        }).reset_index()

        merged = trab.merge(prog_grouped, on="CPF_NORM", how="left")
        merged = merged.merge(prog_metrics, on="CPF_NORM", how="left")
        merged = merged.merge(bank_grouped, on="CPF_NORM", how="left")
        merged = merged.rename(columns={"ITEM": "PROGRAMACAO"})

        def build_bank_info(row):
            return {
                "banco": clean_str(row.get("BANCO_FMT")),
                "agencia": clean_str(row.get("AGENCIA_FMT")),
                "dig_agencia": clean_str(row.get("DIGAGENCIA_FMT")),
                "conta": clean_str(row.get("NROCONTA_FMT")),
                "dig_conta": clean_str(row.get("DIGCONTA_FMT")),
                "tipo": clean_str(row.get("TIPO_CONTA_FMT")),
            }

        merged["BANK_INFO"] = merged.apply(build_bank_info, axis=1)

        self.merged_data_base = merged
        self.merged_data = self.merged_data_base.copy()
        self.selected_keys.clear()
        logger.info(
            'Dados combinados: base=%d, programações=%d, dados bancários=%d',
            len(trab),
            len(prog_grouped),
            len(bank_grouped),
        )
        self.populate_table()
        self.btn_export.config(state="normal")

    def populate_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.check_vars.clear()
        self.row_records = []
        self.item_to_record = {}

        for _, row in self.merged_data.iterrows():
            credor = "" if pd.isna(row["CREDOR"]) else str(row["CREDOR"])
            cpf_original = row.get("CPF_ORIGINAL", "")
            cpf_norm = row.get("CPF_NORM", "")
            fgts = self.format_currency(row.get("FGTS"))
            verba = self.format_currency(row.get("VERBA RESCISÓRIA"))
            qtd_raw = row.get("QTD PARCELAS")
            qtd = "" if pd.isna(qtd_raw) else str(int(qtd_raw))
            valor_raw = row.get("VALOR PARCELA")
            valor = self.format_currency(valor_raw)
            programacao = row.get("PROGRAMACAO", "")
            if pd.isna(programacao):
                programacao = ""
            programacao_str = str(programacao)
            bank_info = row.get("BANK_INFO") or {}

            expected_total = None
            if not pd.isna(qtd_raw) and not pd.isna(valor_raw):
                try:
                    expected_total = float(qtd_raw) * float(valor_raw)
                except Exception:
                    expected_total = None
            actual_total = row.get("PROG_TOTAL")
            actual_qtd = row.get("PROG_QTD")
            mismatch_total = (
                expected_total is not None
                and actual_total is not None
                and not pd.isna(actual_total)
                and abs(expected_total - float(actual_total)) > 0.5
            )
            mismatch_qtd = (
                not pd.isna(qtd_raw)
                and actual_qtd is not None
                and not pd.isna(actual_qtd)
                and int(qtd_raw) != int(actual_qtd)
            )

            key = (cpf_norm, credor)
            selected = key in self.selected_keys
            var = tk.BooleanVar(value=selected)
            if selected:
                self.selected_keys.add(key)

            base_tags = []
            if mismatch_total or mismatch_qtd:
                base_tags.append('alert')

            tags = list(base_tags)
            if selected:
                if 'alert' in base_tags:
                    tags = ['alert_selected']
                else:
                    tags.append('selected_row')

            checkbox_value = '[x]' if selected else '[ ]'
            item_id = self.tree.insert(
                "",
                "end",
                values=(checkbox_value, credor, cpf_original, fgts, verba, qtd, valor, programacao_str),
                tags=tags,
            )

            record = {
                'var': var,
                'key': key,
                'credor': credor,
                'cpf_original': cpf_original,
                'cpf_norm': cpf_norm,
                'fgts': fgts,
                'verba': verba,
                'qtd': qtd,
                'valor': valor,
                'programacao': programacao_str,
                'bank_info': bank_info,
                'base_tags': base_tags,
                'item_id': item_id,
            }
            self.row_records.append(record)
            self.item_to_record[item_id] = record

        self.check_vars = [
            (
                rec['var'],
                rec['credor'],
                rec['cpf_original'],
                rec['cpf_norm'],
                rec['fgts'],
                rec['verba'],
                rec['qtd'],
                rec['valor'],
                rec['programacao'],
                rec['bank_info'],
            )
            for rec in self.row_records
        ]

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
                record = self.item_to_record.get(item)
                if record:
                    new_state = not record['var'].get()
                    record['var'].set(new_state)
                    if new_state:
                        self.selected_keys.add(record['key'])
                    else:
                        self.selected_keys.discard(record['key'])
                    self.tree.set(item, "select", "[x]" if new_state else "[ ]")
                    self._apply_row_tags(item, record)

    def _apply_row_tags(self, item_id, record):
        base_tags = record['base_tags']
        if record['var'].get():
            if 'alert' in base_tags:
                tags = ['alert_selected']
            else:
                tags = base_tags + ['selected_row']
        else:
            tags = base_tags if base_tags else []
        if tags:
            self.tree.item(item_id, tags=tags)
        else:
            self.tree.item(item_id, tags=())

    def _handle_tree_double_click(self, event):
        region = self.tree.identify('region', event.x, event.y)
        column = self.tree.identify_column(event.x)
        if region == 'heading' and column == '#1':
            records = [rec for rec in self.row_records if self.tree.exists(rec['item_id'])]
            if not records:
                return 'break'
            all_selected = all(rec['var'].get() for rec in records)
            new_state = not all_selected
            for rec in records:
                rec['var'].set(new_state)
                if new_state:
                    self.selected_keys.add(rec['key'])
                else:
                    self.selected_keys.discard(rec['key'])
                self.tree.set(rec['item_id'], 'select', '[x]' if new_state else '[ ]')
                self._apply_row_tags(rec['item_id'], rec)
            return 'break'
        return None

    # ---------- Exportar PDF ---------- #
    def _render_one_pdf(self, filepath, credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao, bank_info):
        pdf = ReportPDF(company_name=COMPANY_NAME_DEFAULT, logo_path=self.logo_path, watermark_path=self.watermark_path)
        logger.info('Gerando PDF para %s em %s', credor, filepath)
        pdf.alias_nb_pages()
        pdf.set_margins(left=12, top=35, right=12)
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 9, "Dados do Credor", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"CREDOR: {credor}", ln=True)
        pdf.cell(0, 7, f"CPF: {self.mask_cpf(cpf_original, cpf_norm)}", ln=True)

        info = bank_info or {}
        bank_values = [str(info.get(key) or "").strip() for key in ("banco", "agencia", "dig_agencia", "conta", "dig_conta", "tipo")]
        if any(bank_values):
            pdf.ln(1)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, "Dados Bancários", ln=True)
            pdf.set_font("Arial", "", 11)
            banco = bank_values[0] or "-"
            pdf.cell(0, 7, f"Banco: {banco.zfill(3) if banco.isdigit() else banco}", ln=True)
            agencia = bank_values[1] or "-"
            dig_agencia = bank_values[2] or ""
            linha_agencia = f"Agência: {agencia.zfill(4) if agencia.isdigit() else agencia}"
            if dig_agencia:
                linha_agencia += f"    Dígito: {dig_agencia[:1]}"
            pdf.cell(0, 7, linha_agencia, ln=True)
            conta = bank_values[3] or "-"
            dig_conta = bank_values[4] or ""
            linha_conta = f"Conta: {conta}"
            if dig_conta:
                linha_conta += f"    Dígito: {dig_conta[:1]}"
            pdf.cell(0, 7, linha_conta, ln=True)
            tipo = bank_values[5] or "-"
            pdf.cell(0, 7, f"Tipo de Conta: {tipo}", ln=True)
            pdf.ln(3)

        th = 8
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(58, th, "FGTS + MULTA FGTS (40%)", border=1, align="C", fill=True)
        pdf.cell(50, th, "VERBA RESCISÓRIA",        border=1, align="C", fill=True)
        pdf.cell(35, th, "QTD PARCELAS",            border=1, align="C", fill=True)
        pdf.cell(40, th, "VALOR PARCELA",           border=1, align="C", fill=True)
        pdf.ln(th)

        pdf.set_font("Arial", "", 11)
        fgts_exib = f"{fgts.strip()}*" if fgts else "-"
        pdf.cell(58, th, fgts_exib, border=1, align="C")
        pdf.cell(50, th, verba or "-", border=1, align="C")
        pdf.cell(35, th, qtd or "-",   border=1, align="C")
        pdf.cell(40, th, valor or "-", border=1, align="C")
        pdf.ln(th + 2)

        pdf.set_font("Arial", "I", 10)
        pdf.multi_cell(0, 6, "*O FGTS será quitado integralmente, em uma única parcela, até o término da programação abaixo, com a devida correção monetária. O valor será creditado em sua conta vinculada ao FGTS.")
        pdf.ln(1)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 9, "Programação de Pagamento", ln=True)
        pdf.set_font("Arial", "", 11)
        if programacao:
            for item in str(programacao).split(", "):
                pdf.cell(0, 7, item, ln=True)
        else:
            pdf.cell(0, 7, "Sem programação encontrada.", ln=True)

        pdf.ln(6)
        pdf.set_font("Arial", "I", 11)
        pdf.cell(0, 8, data_por_extenso(), ln=True, align="R")

        pdf.output(filepath)
        logger.info('PDF salvo em %s', filepath)
    def export_pdf(self):
        selected_rows = [rest for var, *rest in self.check_vars if var.get()]
        if not selected_rows:
            logger.warning('Exportação ignorada: nenhum item selecionado')
            messagebox.showwarning("Aviso", "Selecione ao menos um item para exportar.")
            return

        if len(selected_rows) == 1:
            credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao, bank_info = selected_rows[0]
            suggested = self.sanitize_filename(credor) + ".pdf"
            output_file = filedialog.asksaveasfilename(
                title="Salvar PDF",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=suggested,
            )
            if output_file:
                logger.info('Exportação única selecionada: %s -> %s', credor, output_file)
                try:
                    self._render_one_pdf(output_file, credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao, bank_info)
                    logger.info('PDF gerado com sucesso: %s', output_file)
                    messagebox.showinfo("Sucesso", f"PDF salvo em\n{output_file}")
                except Exception as exc:
                    logger.exception('Falha ao gerar PDF para %s', credor)
                    messagebox.showerror("Erro", f"Não foi possível salvar o PDF\n{exc}")
            return

        out_dir = filedialog.askdirectory(title="Selecione a pasta para salvar os PDFs")
        if not out_dir:
            logger.info('Exportação múltipla cancelada: nenhuma pasta selecionada')
            return

        ok, fail = 0, 0
        for credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao, bank_info in selected_rows:
            fname = self.sanitize_filename(credor) + ".pdf"
            fpath = os.path.join(out_dir, fname)
            try:
                logger.info('Gerando PDF em lote: %s', fpath)
                self._render_one_pdf(fpath, credor, cpf_original, cpf_norm, fgts, verba, qtd, valor, programacao, bank_info)
                ok += 1
            except Exception:
                logger.exception('Falha ao gerar PDF em lote para %s', credor)
                fail += 1

        logger.info('Exportação múltipla concluída: sucesso=%s, falhas=%s, destino=%s', ok, fail, out_dir)
        message = f"{ok} arquivo(s) salvo(s) em\n{out_dir}"
        if fail:
            message += f"\n{fail} arquivo(s) falharam ao salvar."
        messagebox.showinfo("Exportação concluída", message)

def main():
    root = tk.Tk()
    app = App(root)
    logger.info('Aplicacao de comprovantes iniciada - versao %s', APP_VERSION)
    root.mainloop()
    logger.info('Aplicacao de comprovantes encerrada - versao %s', APP_VERSION)


if __name__ == "__main__":
    main()





