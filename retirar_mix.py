import pandas as pd
import tkinter as tk
from tkinter import filedialog

# Crie uma janela de diálogo para o usuário selecionar o arquivo
root = tk.Tk()
root.withdraw()
caminho_arquivo = filedialog.askopenfilename()

# Solicite ao usuário que insira o número da empresa
nroempresa = input("Por favor, insira o número da empresa: ")

# Valide se o número da empresa é numérico
if not nroempresa.isdigit():
    print("Erro: O número da empresa deve ser numérico.")
    exit()

# Carregue seus dados do arquivo CSV para um DataFrame do pandas
try:
    df = pd.read_excel(caminho_arquivo)

except Exception as e:
    print(f"Erro ao abrir o arquivo: {e}")
    exit()

# Crie uma lista para armazenar suas consultas SQL
sql_queries = []

for index, row in df.iterrows():
    codigo_produto = row['Código Produto']
    query = f"""
    UPDATE MRL_PRODUTOEMPRESA A
    SET A.STATUSCOMPRA = 'I'
    WHERE A.NROEMPRESA = '{nroempresa}'
    AND A.SEQPRODUTO = '{codigo_produto}';
    """
    sql_queries.append(query)

# Escreva as consultas SQL em um arquivo de script
with open('script.sql', 'w') as f:
    for query in sql_queries:
        f.write(query + "\n")
