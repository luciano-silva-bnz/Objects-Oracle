import pandas as pd
import tkinter as tk
from tkinter import filedialog

# Função para selecionar arquivos
def selecionar_arquivos():
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal do Tkinter
    file_paths = filedialog.askopenfilenames(title='Selecione as três planilhas do Excel')
    return list(file_paths)

# Função para selecionar o local e o nome do arquivo para salvar a nova planilha
def salvar_como():
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal do Tkinter
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel files", "*.xlsx")],
                                             title="Salvar a nova planilha como",
                                             initialfile="analise de movimentação.xlsx")
    return file_path

# Seleciona os arquivos usando a interface gráfica
file_paths = selecionar_arquivos()

# Lista para armazenar os dataframes filtrados
dfs = []

# Lê cada arquivo do Excel e adiciona o dataframe filtrado à lista
for file in file_paths:
    # Lê o arquivo do Excel
    df = pd.read_excel(file, sheet_name='Exportar Planilha', dtype=str)
    # Verifica se as colunas 'B9_FILIAL' e 'B9_LOCAL' existem antes de filtrar
    if 'B9_FILIAL' in df.columns and 'B9_LOCAL' in df.columns:
        # Filtra o dataframe pelas condições especificadas
        df_filtered = df[(df['B9_FILIAL'] == '41') & (df['B9_LOCAL'] == '01')]
        # Adiciona o dataframe filtrado à lista se não estiver vazio
        if not df_filtered.empty:
            dfs.append(df_filtered)
    else:
        # Se as colunas 'B9_FILIAL' e 'B9_LOCAL' não existirem, adiciona o dataframe inteiro à lista
        dfs.append(df)

if dfs:
    final_df = pd.concat(dfs, ignore_index=True)
else:
    print("Nenhum dataframe para concatenar. Verifique os arquivos e condições de filtragem.")
    # Pode adicionar mais lógica aqui, como uma saída antecipada do script ou outra ação

# Cria um novo dataframe para armazenar os valores de código e descrição do produto
new_df = pd.DataFrame(columns=['Codigo', 'Descrição'])

# Procura os campos especificados em cada planilha e adiciona os valores ao novo dataframe
for codigo_col in ['COD PRODUTO', 'B9_COD']:
    if codigo_col in final_df.columns:
        for descricao_col in ['DESCRICAO', 'B1_DESC']:
            if descricao_col in final_df.columns:
                # Extrai os dados das colunas código e descrição
                temp_df = final_df[[codigo_col, descricao_col]].drop_duplicates()
                temp_df.columns = ['Codigo', 'Descrição']  # Renomeia as colunas
                # Verifica se o código e a descrição estão presentes antes de adicionar ao novo dataframe
                for index, row in temp_df.iterrows():
                    if pd.notnull(row['Codigo']) and pd.notnull(row['Descrição']):
                        if row['Codigo'] not in new_df['Codigo'].values:
                            new_df = pd.concat([new_df, pd.DataFrame([row])], ignore_index=True)


# Seleciona o local e o nome do arquivo para salvar a nova planilha
save_path = salvar_como()

# Salva o novo dataframe como uma nova planilha do Excel no local selecionado pelo usuário
if save_path:  # Verifica se um caminho foi fornecido
    new_df.to_excel(save_path, index=False)
    print(f"Uma nova planilha foi criada em: {save_path}")
else:
    print("A operação de salvar foi cancelada.")
