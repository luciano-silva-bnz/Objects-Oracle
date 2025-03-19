import pandas as pd
import os

# Caminho da pasta com os arquivos Excel
pasta = 'C:\\CONSINCO\\simplus\\jailson'
# Nome do arquivo Excel final
arquivo_final = 'C:\\CONSINCO\simplus\\jailson\\Arquivo_Unificado.xlsx'

# Lista de dataframes para juntar todas as abas
df_list = []

for arquivo in os.listdir(pasta):
    if arquivo.endswith('.xlsx'):
        file_path = os.path.join(pasta, arquivo)
        xls = pd.ExcelFile(file_path)
        for aba in xls.sheet_names:
            df = pd.read_excel(file_path, sheet_name=aba)
            df['Arquivo'] = arquivo
            df['Aba'] = aba
            # Filtrando URLs longas
            for col in df.columns:
                df[col] = df[col].apply(lambda x: x if isinstance(x, str) and len(x) <= 2079 else '' if isinstance(x, str) else x)
            df_list.append(df)

# Concatenar todas as abas
df_final = pd.concat(df_list, ignore_index=True)

# Escrever no arquivo final
df_final.to_excel(arquivo_final, index=False)