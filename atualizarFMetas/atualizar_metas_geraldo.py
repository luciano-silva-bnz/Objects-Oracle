import os
import sys
import traceback
import calendar
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox


def selecionar_arquivo(titulo):
    """Abre um diálogo para o usuário selecionar um arquivo Excel."""
    caminho = filedialog.askopenfilename(
        title=titulo,
        filetypes=[("Arquivos Excel", "*.xlsx *.xls")]
    )
    return caminho


def base_dir():
    """Retorna a pasta do executável (PyInstaller) ou do .py."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def build_metas_from_sazonalidade(saz_path, ano_alvo=2026):
    """
    Lê a planilha de sazonalidade e monta um DataFrame no padrão da fMetas:
    Colunas: DATA, NROEMPRESA, META, MÊS/ANO

    Regras:
    - Percorre todas as abas cujo nome é numérico (01, 02, 04, 05, 09, ...).
    - Usa a coluna de índice 7 (8ª coluna) como DATA -> datas do ano alvo.
    - Usa a coluna de índice 9 (10ª coluna) como META diária.
    - Mantém apenas linhas com DATA não nula e ano = ano_alvo.
    """

    xls_saz = pd.ExcelFile(saz_path)
    frames = []

    for sh in xls_saz.sheet_names:
        loja = sh.strip()
        # Considera apenas abas cujo nome é número (lojas)
        if not loja.isdigit():
            continue

        try:
            df = pd.read_excel(saz_path, sheet_name=sh)

            # Garante que existam colunas suficientes
            if df.shape[1] < 10:
                print(f"Aba '{sh}' tem menos de 10 colunas, ignorando.")
                continue

            # Índice 7 = 8ª coluna -> DATA (ano alvo)
            col_date = df.columns[7]
            # Índice 9 = 10ª coluna -> META diária
            col_value = df.columns[9]

            tmp = df[[col_date, col_value]].copy()
            tmp = tmp.rename(columns={col_date: "DATA", col_value: "META"})

            # Apenas linhas com alguma DATA
            tmp = tmp[~tmp["DATA"].isna()].copy()

            # Converte para datetime
            tmp["DATA"] = pd.to_datetime(tmp["DATA"], errors="coerce")
            tmp = tmp[~tmp["DATA"].isna()].copy()

            # Filtra pelo ano alvo
            tmp = tmp[tmp["DATA"].dt.year == ano_alvo].copy()
            if tmp.empty:
                print(f"Aba '{sh}' não possui datas para o ano {ano_alvo}, ignorando.")
                continue

            # Considera apenas o mês presente na planilha (cada arquivo é mensal)
            mes_alvo = int(tmp["DATA"].dt.month.mode().iloc[0])
            start_month = pd.Timestamp(year=ano_alvo, month=mes_alvo, day=1)
            end_month_day = calendar.monthrange(ano_alvo, mes_alvo)[1]
            end_month = pd.Timestamp(year=ano_alvo, month=mes_alvo, day=end_month_day)

            # Algumas lojas fecham aos domingos e a planilha não traz meta nessas datas.
            # Inserimos domingos ausentes com META = 0 para manter o calendário completo.
            full_dates = pd.DataFrame(
                {"DATA": pd.date_range(start_month, end_month, freq="D")}
            )

            tmp = full_dates.merge(tmp[["DATA", "META"]], on="DATA", how="left")
            tmp.loc[(tmp["META"].isna()) & (tmp["DATA"].dt.weekday == 6), "META"] = 0

            # Mantém apenas dias que receberam meta (originais ou domingos zerados)
            tmp = tmp.dropna(subset=["META"]).copy()
            tmp["META"] = tmp["META"].astype(float).round(2)

            # Define NROEMPRESA como texto, mas sem zero à esquerda (ex.: 01 -> "1")
            tmp["NROEMPRESA"] = str(int(loja))

            # Monta MÊS/ANO no formato 1/2026, 2/2026, etc
            tmp["MÊS/ANO"] = tmp["DATA"].dt.month.astype(str) + "/" + tmp["DATA"].dt.year.astype(str)

            frames.append(tmp[["DATA", "NROEMPRESA", "META", "MÊS/ANO"]])

        except Exception as e:
            print(f"Erro ao processar aba '{sh}': {e}")
            traceback.print_exc()
            continue

    if frames:
        metas = pd.concat(frames, ignore_index=True)
        # Ordena por loja e data
        metas = metas.sort_values(["NROEMPRESA", "DATA"]).reset_index(drop=True)
        return metas
    else:
        return pd.DataFrame(columns=["DATA", "NROEMPRESA", "META", "MÊS/ANO"])


def main():
    # Configura Tkinter (sem mostrar a janela principal)
    root = tk.Tk()
    root.withdraw()

    try:
        # Usa planilha modelo fixa ao lado do executável / .py
        fmetas_path = os.path.join(base_dir(), "fMetas_Bonanza.xlsx")
        if not os.path.isfile(fmetas_path):
            messagebox.showerror(
                "Erro",
                f"Arquivo fMetas_Bonanza.xlsx não encontrado em:\n\n{fmetas_path}\n\n"
                "Coloque o arquivo na mesma pasta do executável (ou do .py) e tente novamente."
            )
            return

        messagebox.showinfo("Informação", "Agora selecione o arquivo de Sazonalidade (ex: Sazonalidade 01.2026 ok.xlsx).")
        saz_path = selecionar_arquivo("Selecione o arquivo de Sazonalidade")

        if not saz_path:
            messagebox.showwarning("Atenção", "Nenhum arquivo de Sazonalidade selecionado. Operação cancelada.")
            return

        # Ano alvo (pode alterar aqui se quiser outro ano)
        ANO_ALVO = 2026

        # Monta DataFrame de metas a partir da sazonalidade
        metas_ano = build_metas_from_sazonalidade(saz_path, ano_alvo=ANO_ALVO)

        if metas_ano.empty:
            messagebox.showwarning("Atenção", f"Não foram encontradas metas com datas no ano {ANO_ALVO}.")
            return

        # Garante tipo texto para NROEMPRESA (ex.: 1, 2, 10)
        metas_ano["NROEMPRESA"] = metas_ano["NROEMPRESA"].astype(str)
        # Formata data no padrão dd/mm/aaaa sem horário
        metas_ano["DATA"] = metas_ano["DATA"].dt.strftime("%d/%m/%Y")

        # Gera nome do arquivo de saída (mesmo diretório da sazonalidade escolhida)
        pasta_base = os.path.dirname(saz_path)
        nome_base = os.path.splitext(os.path.basename(saz_path))[0]
        out_append_path = os.path.join(
            pasta_base,
            f"{nome_base}_APENAS_{ANO_ALVO}_PARA_INSERIR.xlsx"
        )

        # Salva apenas as linhas novas em uma aba separada
        with pd.ExcelWriter(out_append_path, engine="openpyxl") as writer:
            metas_ano.to_excel(writer, sheet_name=f"fMetas_{ANO_ALVO}", index=False)

        messagebox.showinfo(
            "Concluído",
            f"Arquivo gerado com sucesso:\n\n{out_append_path}\n\n"
            f"Aba: fMetas_{ANO_ALVO}\n\n"
            "Agora é só abrir esse arquivo, copiar todas as linhas e colar "
            "na aba fMetas do Google Sheets logo abaixo dos dados atuais."
        )

    except Exception as e:
        traceback.print_exc()
        messagebox.showerror("Erro", f"Ocorreu um erro:\n\n{e}")
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
