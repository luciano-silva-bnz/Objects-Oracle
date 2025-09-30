from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from ..api import TotvsAPI
from ..config import ASSETS_DIR
from ..logging_config import get_logger
from .dialogs import BuscaCPFWindow

logger = get_logger(__name__)

MARK_SELECTED = "[x]"
MARK_UNSELECTED = "[ ]"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.api = TotvsAPI()
        self.df = pd.DataFrame()
        self.filter_key = ""
        self.import_path: Path | None = None
        self.convert_process: subprocess.Popen[str] | None = None
        self.comprov_process: subprocess.Popen[str] | None = None
        self._build_login()

    def _build_login(self) -> None:
        self.root.withdraw()

        win = tk.Toplevel(self.root)
        win.title("Login TOTVS-CONSINCO")
        win.protocol("WM_DELETE_WINDOW", self.root.destroy)
        win.geometry("300x180")
        self._center(win, 300, 180)

        tk.Label(win, text="Usuario:").pack(pady=5)
        self.ent_user = tk.Entry(win)
        self.ent_user.pack()
        tk.Label(win, text="Senha:").pack(pady=5)
        self.ent_pass = tk.Entry(win, show="*")
        self.ent_pass.pack()
        btn_entrar = tk.Button(win, text="Entrar", command=lambda: self._do_login(win))
        btn_entrar.pack(pady=10)
        win.grab_set()
        win.focus_force()
        self.ent_pass.bind("<Return>", lambda event: self._do_login(win))
        self.ent_user.bind("<Return>", lambda event: self.ent_pass.focus_set())

    def _do_login(self, win: tk.Toplevel) -> None:
        username = self.ent_user.get()
        ok, msg = self.api.authenticate(username, self.ent_pass.get())
        if not ok:
            logger.warning("Falha de login para %s: %s", username, msg)
            messagebox.showerror("Erro de Login", msg)
            return

        logger.info("Login bem-sucedido para %s", username)
        win.destroy()
        self.root.deiconify()
        self._build_ui()

    def _center(self, win: tk.Toplevel, width: int, height: int) -> None:
        screen_w, screen_h = win.winfo_screenwidth(), win.winfo_screenheight()
        pos_x, pos_y = (screen_w - width) // 2, (screen_h - height) // 2
        win.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        bar1 = ttk.Frame(self.root, padding=(6, 4, 6, 0))
        bar1.grid(row=0, column=0, sticky="ew")

        self.lbl_stats = ttk.Label(bar1, text="Total: 0 | Selecionados: 0 | Cadastrados: 0")
        self.lbl_stats.pack(side="left", padx=(0, 10))

        ttk.Button(bar1, text="Importar Planilha", command=self.importar).pack(side="left", padx=3)
        self.ent_filter = ttk.Entry(bar1, width=30)
        self.ent_filter.pack(side="left", padx=3)
        ttk.Button(bar1, text="Filtrar", command=self.aplicar_filtro).pack(side="left", padx=3)

        bar2 = ttk.Frame(self.root, padding=(6, 2, 6, 4))
        bar2.grid(row=1, column=0, sticky="ew")

        ttk.Button(bar2, text="Selecionar/Desmarcar Todos", command=self.selecionar_todos).pack(side="left", padx=3)
        ttk.Button(bar2, text="Buscar Dados Bancos", command=self.abrir_janela_busca_cpfs).pack(side="left", padx=3)
        ttk.Button(bar2, text="Cadastrar Selecionados", command=self.cadastrar).pack(side="left", padx=3)
        ttk.Button(bar2, text="Extrair Comprovantes PDF (TXT/PDF)", command=self.abrir_convert_extrator).pack(side="left", padx=3)
        ttk.Button(bar2, text="Gerar Comprovante Trabalhista (RJ)", command=self.abrir_comprov_app).pack(side="left", padx=3)

        paned = ttk.Panedwindow(self.root, orient="vertical")
        paned.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))

        tree_frame = ttk.Frame(paned)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        sb = ttk.Scrollbar(tree_frame, orient="vertical")
        self.tree = ttk.Treeview(tree_frame, show="headings", selectmode="none", yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        sb.config(command=self.tree.yview)
        self.tree.bind("<Double-1>", self._toggle)

        paned.add(tree_frame, weight=4)

        log_frame = ttk.Frame(paned)
        log_frame.grid_columnconfigure(0, weight=1)

        self.txt = tk.Text(log_frame, height=8)
        self.txt.grid(row=0, column=0, sticky="ew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.txt.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.txt.config(yscrollcommand=log_scroll.set)

        paned.add(log_frame, weight=1)

        self._carregar_rodape()

    def importar(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not file_path:
            return
        self.import_path = Path(file_path)
        try:
            self.df = pd.read_excel(file_path, dtype=str).fillna("")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha ao importar planilha %s", file_path)
            messagebox.showerror("Erro ao importar", str(exc))
            return
        for col in ["Selecionado", "Status", "idPessoa", "ErroDetalhes"]:
            self.df[col] = ""
        self.filter_key = ""
        self._refresh(self.df)
        logger.info("Planilha importada: %s (%d linhas)", file_path, len(self.df))

    def aplicar_filtro(self) -> None:
        if self.df.empty:
            messagebox.showwarning("Aviso", "Importe antes de filtrar")
            return
        key = self.ent_filter.get().strip().lower()
        self.filter_key = key
        if not key:
            df_show = self.df
        else:
            mask = self.df['RA_CIC'].str.contains(key) | self.df['RA_NOME'].str.lower().str.contains(key)
            df_show = self.df[mask]
        self._refresh(df_show)
        logger.info("Filtro aplicado: %s (exibindo %d registros)", key or '<vazio>', len(df_show))

    def selecionar_todos(self) -> None:
        if self.df.empty:
            return
        if not self.filter_key:
            df_subset = self.df
        else:
            mask = self.df['RA_CIC'].str.contains(self.filter_key) | self.df['RA_NOME'].str.lower().str.contains(self.filter_key)
            df_subset = self.df[mask]
        all_selected = all(df_subset['Selecionado'] == '1')
        self.df.loc[df_subset.index, 'Selecionado'] = '' if all_selected else '1'
        self._refresh(df_subset)

    def _toggle(self, event: tk.Event[tk.Misc]) -> None:
        if self.tree.identify_column(event.x) != '#1':
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        idx = int(row_id)
        value = self.df.at[idx, 'Selecionado']
        self.df.at[idx, 'Selecionado'] = '' if value == '1' else '1'
        if not self.filter_key:
            df_show = self.df
        else:
            mask = self.df['RA_CIC'].str.contains(self.filter_key) | self.df['RA_NOME'].str.lower().str.contains(self.filter_key)
            df_show = self.df[mask]
        self._refresh(df_show)

    def _refresh(self, df_view: pd.DataFrame) -> None:
        self.tree.delete(*self.tree.get_children())
        columns = ['Selecionado'] + [c for c in df_view.columns if c not in ['Selecionado', 'Status', 'idPessoa', 'ErroDetalhes']]
        self.tree['columns'] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        for idx, row in df_view.iterrows():
            mark = MARK_SELECTED if row['Selecionado'] == '1' else MARK_UNSELECTED
            values = [mark] + [row[c] for c in columns[1:]]
            self.tree.insert('', 'end', iid=idx, values=values)
        self._stats()

    def _stats(self) -> None:
        total = len(self.df)
        selected = int((self.df['Selecionado'] == '1').sum())
        completed = int((self.df['Status'] == 'Sucesso').sum()) + int((self.df['Status'] == 'Existente').sum())
        self.lbl_stats.config(text=f'Total: {total} | Selecionados: {selected} | Cadastrados: {completed}')

    def montar_payload(self, row: pd.Series) -> dict[str, str | None]:
        nome = row['RA_NOME']
        fantasia = nome.split(' ')[0]
        sexo = row.get('RA_SEXO', '')
        ddd = row.get('RA_DDDCELU', '')
        telefone = row.get('TELEFONE_FORMATADO', '')
        cep = row.get('RA_CEP', '').replace('.0', '') or None
        uf_cidade = str(row.get('RA_ESTADO', '')).strip() or None
        cpf = row['RA_CIC'].zfill(11)
        numero, digito = cpf[:-2], cpf[-2:]
        return {
            'nomeRazaoSocial': nome,
            'fantasia': fantasia,
            'tipo': 'F',
            'status': 'A',
            'sexo': sexo or None,
            'InscricaoEstadualRG': row.get('RA_RG', '') or None,
            'cep': cep,
            'telefoneDDD1': ddd or None,
            'telefoneNumero1': telefone or None,
            'numeroCPFCNPJ': numero,
            'digitoCPFCNPJ': digito,
            'ufCidade': uf_cidade,
            'numeroLogradouro': row.get('RA_NUMENDE', '').replace('.0', '') or None,
        }

    def cadastrar(self) -> None:
        self.txt.delete('1.0', tk.END)
        df_selected = self.df[self.df['Selecionado'] == '1']
        count_selected = len(df_selected)
        processed = 0
        for idx, row in df_selected.iterrows():
            cpf = row['RA_CIC'].zfill(11)
            numero, digito = cpf[:-2], cpf[-2:]
            pessoa_id, status_api = self.api.consultar_pessoa(numero, digito)
            if pessoa_id is not None:
                self.df.at[idx, 'idPessoa'] = pessoa_id
                self.df.at[idx, 'Status'] = status_api or 'Existente'
                processed += 1
                logger.info('Pessoa ja existente: %s (id %s)', row['RA_NOME'], pessoa_id)
                self.txt.insert(tk.END, f"[EXISTENTE] {row['RA_NOME']} -> id {pessoa_id}, status {status_api}\n")
                continue
            payload = self.montar_payload(row)
            try:
                response = self.api.incluir_pessoa(payload)
            except Exception as exc:  # noqa: BLE001
                logger.exception('Erro ao incluir pessoa %s', row['RA_NOME'])
                self.df.at[idx, 'ErroDetalhes'] = str(exc)
                self.df.at[idx, 'Status'] = 'Erro'
                self.txt.insert(tk.END, f"[ERRO] {row['RA_NOME']} -> {exc}\n")
                continue
            if response.status_code == 201:
                new_id = response.json().get('idPessoa')
                self.df.at[idx, 'idPessoa'] = new_id
                self.df.at[idx, 'Status'] = 'Sucesso'
                processed += 1
                logger.info('Pessoa cadastrada com sucesso: %s (id %s)', row['RA_NOME'], new_id)
                self.txt.insert(tk.END, f"[OK] {row['RA_NOME']} -> id {new_id}\n")
            else:
                self.df.at[idx, 'ErroDetalhes'] = response.text
                self.df.at[idx, 'Status'] = f"Erro {response.status_code}"
                logger.warning('Falha ao cadastrar %s: %s %s', row['RA_NOME'], response.status_code, response.text)
                self.txt.insert(tk.END, f"[ERRO] {row['RA_NOME']} -> {response.status_code} {response.text}\n")
        messagebox.showinfo('Integracao', f"Total selecionados: {count_selected}\nProcessados: {processed}")
        if self.import_path:
            out_file = self.import_path.parent / f"resultado_{self.import_path.stem}.xlsx"
            df_export = self.df.loc[df_selected.index, ['RA_CIC', 'RA_NOME', 'idPessoa', 'Status', 'ErroDetalhes']]
            df_export.to_excel(out_file, index=False)
            self.txt.insert(tk.END, f"[INFO] Resultado exportado em {out_file}\n")
        if not self.filter_key:
            df_view = self.df
        else:
            mask = self.df['RA_CIC'].str.contains(self.filter_key) | self.df['RA_NOME'].str.lower().str.contains(self.filter_key)
            df_view = self.df[mask]
        self._refresh(df_view)

    def abrir_janela_busca_cpfs(self) -> None:
        def integrar(df_encontrado: pd.DataFrame) -> None:
            self.df = df_encontrado.copy().fillna('').astype(str)
            for col in ['Selecionado', 'Status', 'idPessoa', 'ErroDetalhes']:
                if col not in self.df.columns:
                    self.df[col] = ''
            self.filter_key = ''
            self._refresh(self.df)
            messagebox.showinfo('Importacao', f"{len(self.df)} registros trazidos dos bancos e prontos para cadastro!")

        BuscaCPFWindow(self.root, on_confirm=integrar)

    def abrir_convert_extrator(self) -> None:
        if self._processo_em_execucao(self.convert_process):
            logger.info('Solicitacao ignorada: extrator ja em execucao')
            messagebox.showinfo('Extrator ja aberto', 'A janela de extracao ja esta aberta.')
            return

        self.root.attributes('-disabled', True)

        try:
            cmd = self._montar_comando_reexecucao('--run-convert')
            logger.info('Abrindo extrator de comprovantes com comando: %s', cmd)
            self.convert_process = subprocess.Popen(cmd)
            self.root.after(1000, self._verifica_convert_fechado)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Falha ao iniciar extrator de comprovantes')
            self.convert_process = None
            self._reativar_janela_se_possivel()
            messagebox.showerror('Erro', f'Falha ao abrir rotina de extracao:\n{exc}')

    def abrir_comprov_app(self) -> None:
        if self._processo_em_execucao(self.comprov_process):
            logger.info('Solicitacao ignorada: comprovante ja em execucao')
            messagebox.showinfo('Comprovante ja aberto', 'A janela de comprovante ja esta aberta.')
            return

        self.root.attributes('-disabled', True)

        try:
            cmd = self._montar_comando_reexecucao('--run-comprov')
            logger.info('Abrindo gerador de comprovante com comando: %s', cmd)
            self.comprov_process = subprocess.Popen(cmd)
            self.root.after(1000, self._verifica_comprov_fechado)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Falha ao iniciar gerador de comprovante')
            self.comprov_process = None
            self._reativar_janela_se_possivel()
            messagebox.showerror('Erro', f'Falha ao abrir rotina de comprovante:\n{exc}')

    def _verifica_convert_fechado(self) -> None:
        if self._processo_em_execucao(self.convert_process):
            self.root.after(1000, self._verifica_convert_fechado)
            return
        proc = self.convert_process
        return_code = proc.returncode if proc is not None else None
        logger.info('Extrator encerrado (retorno %s)', return_code)
        self.convert_process = None
        self._reativar_janela_se_possivel()

    def _verifica_comprov_fechado(self) -> None:
        if self._processo_em_execucao(self.comprov_process):
            self.root.after(1000, self._verifica_comprov_fechado)
            return
        proc = self.comprov_process
        return_code = proc.returncode if proc is not None else None
        logger.info('Gerador de comprovante encerrado (retorno %s)', return_code)
        self.comprov_process = None
        self._reativar_janela_se_possivel()

    def _processo_em_execucao(self, proc: subprocess.Popen[str] | None) -> bool:
        return proc is not None and proc.poll() is None

    def _reativar_janela_se_possivel(self) -> None:
        if not self._processo_em_execucao(self.convert_process) and not self._processo_em_execucao(self.comprov_process):
            logger.debug('Janela principal reativada')
            self.root.attributes('-disabled', False)

    def _montar_comando_reexecucao(self, flag: str) -> list[str]:
        if getattr(sys, 'frozen', False):
            return [sys.executable, flag]
        entry = Path(sys.argv[0]).resolve()
        return [sys.executable, str(entry), flag]

    def _carregar_rodape(self) -> None:
        try:
            rodape_path = ASSETS_DIR / 'rodape.png'
            if rodape_path.exists():
                img = Image.open(rodape_path)
                largura = 1000
                proporcao = img.height / img.width if img.width else 1
                nova_altura = int(largura * proporcao)
                img_redimensionada = img.resize((largura, nova_altura), Image.Resampling.LANCZOS)
                self.rodape_img = ImageTk.PhotoImage(img_redimensionada)
                self.rodape_frame = tk.Frame(self.root)
                self.rodape_frame.grid(row=3, column=0, sticky='ew')
                self.rodape_frame.grid_columnconfigure(0, weight=1)
                self.rodape_label = tk.Label(self.rodape_frame, image=self.rodape_img, bd=0)
                self.rodape_label.grid(row=0, column=0, sticky='ew')
                self.root.bind('<Configure>', self._redimensionar_rodape)
                return
        except Exception as exc:  # noqa: BLE001
            logger.warning('Falha ao carregar rodape: %s', exc)
        self._criar_rodape_simples()

    def _criar_rodape_simples(self) -> None:
        footer_frame = ttk.Frame(self.root, padding=(10, 8, 10, 8))
        footer_frame.grid(row=3, column=0, sticky='ew')
        footer_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(footer_frame, text='BONANZA SUPERMERCADOS', font=('Segoe UI', 10, 'bold'), foreground='#2E86AB').grid(row=0, column=0, sticky='w')
        info_text = 'Setor de Desenvolvimento - 2025 Sistema de Cadastro'
        ttk.Label(footer_frame, text=info_text, font=('Segoe UI', 8), foreground='gray').grid(row=0, column=2, sticky='e')

    def _redimensionar_rodape(self, event: tk.Event[tk.Misc] | None = None) -> None:
        if event and event.widget is not self.root:
            return
        if not hasattr(self, 'rodape_img') or not hasattr(self, 'rodape_label'):
            return
        rodape_path = ASSETS_DIR / 'rodape.png'
        if not rodape_path.exists():
            return
        try:
            largura = self.root.winfo_width()
            ultima = getattr(self, '_ultima_largura', None)
            if ultima is not None and abs(largura - ultima) < 10:
                return
            setattr(self, '_ultima_largura', largura)
            img = Image.open(rodape_path)
            proporcao = img.height / img.width if img.width else 1
            nova_altura = int(largura * proporcao)
            img_redimensionada = img.resize((largura, nova_altura), Image.Resampling.LANCZOS)
            self.rodape_img = ImageTk.PhotoImage(img_redimensionada)
            self.rodape_label.configure(image=self.rodape_img)
        except Exception as exc:  # noqa: BLE001
            logger.debug('Erro ao redimensionar rodape: %s', exc)


def run_app() -> None:
    root = tk.Tk()
    root.title('Cadastro de Pessoas(F) Consinco V.2.0 - Bonanza Supermercados')
    root.geometry('1000x700')
    try:
        style = ttk.Style()
        theme = 'vista' if 'vista' in style.theme_names() else 'clam'
        style.theme_use(theme)
        style.configure('TButton', padding=(6, 2))
    except Exception:  # noqa: BLE001
        pass

    logger.info('Aplicacao principal iniciada')
    App(root)
    root.update_idletasks()
    width = root.winfo_width() or 1000
    height = root.winfo_height() or 700
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    pos_x = (screen_w - width) // 2
    pos_y = (screen_h - height) // 2
    root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    root.mainloop()
