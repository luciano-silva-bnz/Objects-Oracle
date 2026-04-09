from __future__ import annotations

import re
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from openpyxl.utils import get_column_letter

from ..logging_config import get_logger
from ..version import APP_VERSION, get_tool_window_title

logger = get_logger(__name__)

SHEET_NAME = "Competencias_FGTS"
DEFAULT_OUTPUT_NAME = "FGTS_competencias.xlsx"

LANCAMENTO_PATTERN = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d\.]+,\d{2})\s*$")
MES_EXTENSO_PATTERN = re.compile(
    r"(JANEIRO|FEVEREIRO|MARCO|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)/\d{4}"
)
MES_CODIFICADO_PATTERN = re.compile(r"\b([A-Z]{1,10})\s*(\d{1,2})\s*/\s*(\d{4})\b")

OUTPUT_COLUMNS = [
    "Arquivo Origem",
    "Nome",
    "PIS/PASEP",
    "Matrícula",
    "Data Admissão",
    "Data Afastamento",
    "Empregador",
    "Inscrição Empregador",
    "Data Lançamento",
    "Competência",
    "Tipo Lançamento",
    "Descrição Original",
    "Valor (texto)",
    "Valor",
]


def limpar(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "")).strip()


def normalizar_caminhos(paths: list[str | Path]) -> list[Path]:
    vistos: set[str] = set()
    arquivos: list[Path] = []
    for raw_path in paths:
        texto = str(raw_path).strip()
        if not texto:
            continue
        path = Path(texto).expanduser().resolve()
        chave = str(path).lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        arquivos.append(path)
    return arquivos


def _novo_contexto() -> dict[str, str]:
    return {
        "Nome": "",
        "PIS/PASEP": "",
        "Matrícula": "",
        "Data Admissão": "",
        "Data Afastamento": "",
        "Empregador": "",
        "Inscrição Empregador": "",
    }


def extrair_competencia(descricao: str) -> tuple[str | None, str]:
    descricao_limpa = limpar(descricao).upper()

    match_extenso = MES_EXTENSO_PATTERN.search(descricao_limpa)
    if match_extenso:
        tipo = limpar(descricao_limpa[:match_extenso.start()] + " " + descricao_limpa[match_extenso.end():])
        return match_extenso.group(0), tipo

    match_codigo = MES_CODIFICADO_PATTERN.search(descricao_limpa)
    if not match_codigo:
        return None, descricao_limpa

    prefixo, mes_texto, ano_texto = match_codigo.groups()
    try:
        mes = int(mes_texto)
        ano = int(ano_texto)
    except ValueError:
        return None, descricao_limpa

    if not 1 <= mes <= 12 or not 1900 <= ano <= 2100:
        return None, descricao_limpa

    competencia = f"{prefixo}{mes:02d}/{ano:04d}"
    tipo = limpar(descricao_limpa[:match_codigo.start()] + " " + descricao_limpa[match_codigo.end():])
    return competencia, tipo


def ler_registros_fgts(txt_path: str | Path) -> list[dict[str, str]]:
    path = Path(txt_path).resolve()
    linhas = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    registros: list[dict[str, str]] = []
    contexto = _novo_contexto()

    for indice, linha_original in enumerate(linhas):
        linha = linha_original.rstrip()

        if "NOME DO TRABALHADOR" in linha and indice + 1 < len(linhas):
            proxima = linhas[indice + 1]
            match = re.match(r"^(.*?)\s{2,}\d+\s+\d{2}", proxima)
            if match:
                contexto["Nome"] = limpar(match.group(1))

        if "PIS/PASEP" in linha and indice + 1 < len(linhas):
            proxima = linhas[indice + 1]
            match = re.match(r"^\s*(\d+)\s+.*?\s+(\d{2}/\d{2}/\d{4})\s+", proxima)
            if match:
                contexto["PIS/PASEP"] = match.group(1).strip()
                contexto["Data Admissão"] = match.group(2).strip()

        if "DATA DE OPCAO" in linha and indice + 1 < len(linhas):
            proxima = linhas[indice + 1]
            match_afastamento = re.search(r"(\d{2}/\d{2}/\d{4})\s*-\s*\S+", proxima)
            if match_afastamento:
                contexto["Data Afastamento"] = match_afastamento.group(1).strip()

            match_matricula = re.search(r"(\d+)\s*$", proxima)
            if match_matricula:
                contexto["Matrícula"] = match_matricula.group(1).strip()

        if "NOME DO EMPREGADOR" in linha and indice + 1 < len(linhas):
            proxima = linhas[indice + 1]
            match = re.match(r"^(.*?)\s{2,}(\d+)\s*$", proxima)
            if match:
                contexto["Empregador"] = limpar(match.group(1))
                contexto["Inscrição Empregador"] = match.group(2).strip()

        match_lancamento = LANCAMENTO_PATTERN.match(linha)
        if not match_lancamento:
            continue

        data_lancamento = match_lancamento.group(1)
        descricao_original = limpar(match_lancamento.group(2))
        valor_texto = match_lancamento.group(3)
        competencia, tipo_lancamento = extrair_competencia(descricao_original)
        if not competencia:
            continue

        registros.append(
            {
                "Arquivo Origem": path.name,
                **contexto,
                "Data Lançamento": data_lancamento,
                "Competência": competencia,
                "Tipo Lançamento": tipo_lancamento,
                "Descrição Original": descricao_original,
                "Valor (texto)": valor_texto,
            }
        )

    logger.info("TXT FGTS lido: %s (%d registros válidos)", path, len(registros))
    return registros


def gerar_dataframe_fgts(txt_paths: list[str | Path]) -> pd.DataFrame:
    arquivos = normalizar_caminhos(txt_paths)
    registros: list[dict[str, str]] = []

    for txt_path in arquivos:
        registros.extend(ler_registros_fgts(txt_path))

    if not registros:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = pd.DataFrame(registros)
    df["Valor"] = (
        df["Valor (texto)"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    return df.reindex(columns=OUTPUT_COLUMNS)


def exportar_planilha_fgts(df: pd.DataFrame, output_path: str | Path) -> Path:
    destino = Path(output_path).expanduser().resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        worksheet = writer.sheets[SHEET_NAME]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for indice_coluna, coluna in enumerate(df.columns, start=1):
            serie = df[coluna].fillna("").astype(str)
            largura = max(len(coluna), *(len(valor) for valor in serie))
            worksheet.column_dimensions[get_column_letter(indice_coluna)].width = min(max(largura + 2, 12), 45)

    logger.info("Planilha FGTS exportada: %s (%d linhas)", destino, len(df))
    return destino


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(get_tool_window_title("Extrato planilha FGTS"))
        self.geometry("860x250")
        self.minsize(720, 220)

        self.txt_paths = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status = tk.StringVar(value="Selecione os arquivos TXT e o destino da planilha.")
        self._txt_list: list[str] = []

        pad = {"padx": 12, "pady": 8}

        ttk.Button(self, text="TXT(s)...", command=self.pick_txts).grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.txt_paths).grid(row=0, column=1, columnspan=3, sticky="we", **pad)

        ttk.Button(self, text="Salvar como...", command=self.pick_output).grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.output_path).grid(row=1, column=1, columnspan=3, sticky="we", **pad)

        ttk.Label(self, textvariable=self.status, foreground="#444").grid(row=2, column=0, columnspan=4, sticky="w", **pad)
        ttk.Button(self, text="GERAR", command=self.on_generate).grid(row=3, column=2, sticky="e", **pad)
        ttk.Button(self, text="FECHAR", command=self.destroy).grid(row=3, column=3, sticky="w", **pad)

        for coluna in range(1, 4):
            self.columnconfigure(coluna, weight=1)

        self.after(100, self.centralizar)

    def centralizar(self) -> None:
        self.update_idletasks()
        largura = self.winfo_width()
        altura = self.winfo_height()
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = (largura_tela - largura) // 2
        pos_y = (altura_tela - altura) // 2
        self.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")

    def pick_txts(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecione um ou mais extratos FGTS (TXT)",
            filetypes=[("TXT", "*.txt")],
        )
        if not paths:
            logger.info("Selecao de TXT FGTS cancelada")
            return

        arquivos = normalizar_caminhos(list(paths))
        self._txt_list = [str(path) for path in arquivos]
        self.txt_paths.set("; ".join(self._txt_list))
        logger.info("TXT(s) FGTS selecionados: %d arquivo(s)", len(self._txt_list))

    def pick_output(self) -> None:
        initial_dir = Path.cwd()
        if self._txt_list:
            initial_dir = Path(self._txt_list[0]).parent
        elif self.output_path.get().strip():
            initial_dir = Path(self.output_path.get().strip()).expanduser().resolve().parent

        output = filedialog.asksaveasfilename(
            title="Salvar Extrato planilha FGTS como",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialdir=str(initial_dir),
            initialfile=DEFAULT_OUTPUT_NAME,
        )
        if not output:
            logger.info("Selecao de destino FGTS cancelada")
            return

        self.output_path.set(output)
        logger.info("Destino do Extrato planilha FGTS selecionado: %s", output)

    def on_generate(self) -> None:
        txt_list = self._txt_list or [parte.strip() for parte in self.txt_paths.get().split(";") if parte.strip()]
        txt_paths = normalizar_caminhos(txt_list)
        output = self.output_path.get().strip()

        if not txt_paths:
            logger.warning("Geracao FGTS cancelada: nenhum TXT informado")
            messagebox.showwarning("Faltando arquivo", "Selecione ao menos um arquivo TXT.")
            return

        invalidos = [str(path) for path in txt_paths if not path.is_file() or path.suffix.lower() != ".txt"]
        if invalidos:
            logger.warning("TXT(s) invalidos para FGTS: %s", invalidos)
            messagebox.showerror("Arquivo invalido", "Estes caminhos nao sao arquivos TXT validos:\n\n" + "\n".join(invalidos))
            return

        if not output:
            logger.warning("Geracao FGTS cancelada: destino nao informado")
            messagebox.showwarning("Destino obrigatorio", "Escolha onde salvar a planilha.")
            return

        if not output.lower().endswith(".xlsx"):
            output += ".xlsx"
            self.output_path.set(output)

        try:
            self.status.set(f"Processando {len(txt_paths)} arquivo(s)...")
            self.update_idletasks()
            df = gerar_dataframe_fgts([str(path) for path in txt_paths])
            if df.empty:
                self.status.set("Nenhum lancamento valido encontrado.")
                logger.info("Nenhum registro FGTS valido encontrado para %s", txt_paths)
                messagebox.showwarning("Sem dados", "Nenhum lancamento com competencia valida foi encontrado nos arquivos selecionados.")
                return

            destino = exportar_planilha_fgts(df, output)
            self.status.set("Concluido.")
            messagebox.showinfo(
                "Sucesso",
                f"Planilha gerada com sucesso.\n\nArquivos processados: {len(txt_paths)}\nLinhas exportadas: {len(df)}\nDestino: {destino}",
            )
        except Exception as exc:  # noqa: BLE001
            self.status.set("Erro.")
            logger.exception("Erro ao gerar Extrato planilha FGTS")
            messagebox.showerror("Erro ao gerar", f"{type(exc).__name__}: {exc}")


def main() -> int:
    logger.info("Iniciando Extrato planilha FGTS - versao %s", APP_VERSION)
    app = App()
    try:
        style = ttk.Style()
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        style.configure("TButton", padding=(6, 2))
    except Exception:  # noqa: BLE001
        pass
    app.mainloop()
    logger.info("Extrato planilha FGTS encerrado - versao %s", APP_VERSION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
