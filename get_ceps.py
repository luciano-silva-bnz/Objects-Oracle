from tkinter import filedialog
import pandas as pd
import requests

# Define o nome do arquivo da planilha
filename = filedialog.askopenfilename(
    filetypes=[("Arquivos do Excel", "*.xlsx")])

# Verifica se um arquivo foi selecionado
if filename:
    # Lê a planilha com a lista de CEPs
    df = pd.read_excel(filename, usecols=['postcode_range'])

    # Cria uma lista vazia para armazenar os resultados
    resultados = []

    # Itera sobre cada faixa de CEPs na lista
    for index, row in df.iterrows():
        # Obtém o início e o fim da faixa de CEPs
        inicio, fim = row['postcode_range'].split(' a ')

        # Remove os caracteres não numéricos
        inicio = int(''.join(filter(str.isdigit, inicio)))
        fim = int(''.join(filter(str.isdigit, fim)))

        # Itera sobre cada CEP na faixa
        for cep in range(inicio, fim + 1):
            # Faz a requisição para o site ViaCEP
            response = requests.get(f'http://viacep.com.br/ws/{cep}/json/')
            data = response.json()

            # Verifica se o CEP existe
            if 'erro' not in data:
                # Adiciona o resultado à lista
                resultados.append(data)

    # Cria um novo DataFrame com os resultados
    df_resultados = pd.DataFrame(resultados)

    # Salva o DataFrame em uma nova planilha
    df_resultados.to_excel('resultados.xlsx', index=False)

else:
    # O usuário cancelou a seleção
    print("Nenhum arquivo selecionado")
