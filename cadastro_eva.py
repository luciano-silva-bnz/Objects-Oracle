import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os

# Abra uma janela de diálogo para o usuário selecionar o arquivo
root = tk.Tk()
root.withdraw()  # Ocultar a janela Tkinter extra
caminho_arquivo = filedialog.askopenfilename()

# Carregue seu arquivo Excel em um DataFrame
df = pd.read_excel(caminho_arquivo, dtype=str)

# Remova a primeira coluna
df = df.iloc[:, 1:]

# Defina o número máximo de linhas por arquivo
max_linhas = 499

# Calcule o número de arquivos que serão criados
num_arquivos = len(df) // max_linhas + (len(df) % max_linhas != 0)

# Crie cada arquivo
for i in range(num_arquivos):
    df_i = df[i*max_linhas:(i+1)*max_linhas]
    # Salve o arquivo no mesmo local que o arquivo original
    caminho_saida = os.path.join(os.path.dirname(caminho_arquivo), f'cadastro_eva_{i+1}.csv')
    df_i.to_csv(caminho_saida, sep=';', index=False, encoding='utf-8')
