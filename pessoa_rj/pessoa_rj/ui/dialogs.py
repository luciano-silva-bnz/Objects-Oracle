from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

import pandas as pd

from ..config import DATABASES
from ..database import execute_query
from ..logging_config import get_logger
from ..utils import prepare_cpf_list

logger = get_logger(__name__)


class BuscaCPFWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_confirm: Callable[[pd.DataFrame], None]):
        super().__init__(master)
        self.title("Consulta Multibanco por Lista de CPF")
        self.geometry("680x480")
        self.resizable(False, False)
        self.on_confirm = on_confirm

        self._build_widgets()
        self.grab_set()
        self.focus_force()

    def _build_widgets(self) -> None:
        frame_top = ttk.Frame(self, padding=8)
        frame_top.pack(fill="x")

        ttk.Label(frame_top, text="Informe CPFs ou importe planilha").pack(anchor="w")
        self.txt_cpfs = tk.Text(frame_top, height=6, width=80)
        self.txt_cpfs.pack(fill="both", expand=True, pady=(4, 8))

        toolbar = ttk.Frame(frame_top)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Importar XLSX", command=self.importar_excel).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Buscar", command=self.buscar_bancos).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Fechar", command=self.destroy).pack(side="right", padx=3)

        self.lbl_status = ttk.Label(self, text="")
        self.lbl_status.pack(fill="x", padx=8)

        tree_frame = ttk.Frame(self, padding=8)
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_frame, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)

        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scroll_y.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.df_resultado = pd.DataFrame()

        ttk.Button(self, text="Usar estes dados na tela principal", command=self.usar_dados).pack(pady=6)

    def importar_excel(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.read_excel(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro ao importar", str(exc))
            return
        col_cpf = next((c for c in df.columns if "cpf" in c.lower() or "cic" in c.lower()), df.columns[0])
        cpfs = df[col_cpf].astype(str).tolist()
        self.txt_cpfs.delete("1.0", tk.END)
        self.txt_cpfs.insert(tk.END, "\n".join(cpfs))

    def buscar_bancos(self) -> None:
        texto = self.txt_cpfs.get("1.0", tk.END)
        cpfs = prepare_cpf_list(texto)
        logger.debug("CPFs extraidos: %s", cpfs)
        if not cpfs:
            messagebox.showwarning("Atencao", "Nenhum CPF válido informado.")
            return

        self.lbl_status.config(text=f"{len(cpfs)} CPFs preparados para busca... Aguarde.")
        self.update_idletasks()

        resultados: list[pd.DataFrame] = []
        for config in DATABASES:
            try:
                df = execute_query(config, cpfs)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Erro ao consultar banco %s", config.name)
                messagebox.showerror("Erro Banco", f"Erro ao consultar Banco {config.name}: {exc}")
                continue
            resultados.append(df)

        if resultados:
            df_final = pd.concat(resultados, ignore_index=True)
            self.df_resultado = df_final.copy()
            self.show_dataframe(df_final)
            self.lbl_status.config(text=f"Busca finalizada. Registros encontrados: {len(df_final)}")
        else:
            self.lbl_status.config(text="Nenhum dado retornado dos bancos.")

    def show_dataframe(self, df: pd.DataFrame) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        for column in df.columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=120)
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=list(row))

    def usar_dados(self) -> None:
        if self.df_resultado.empty:
            messagebox.showwarning("Atencao", "Nenhum dado para usar.")
            return
        self.on_confirm(self.df_resultado)
        self.destroy()
