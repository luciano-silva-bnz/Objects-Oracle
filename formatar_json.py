# -*- coding: iso-8859-1 -*-
import http.client
import pandas as pd
import json
import time

# Lê o arquivo CSV em um DataFrame
cnpjs = pd.read_csv("consinco/cnpjs.csv")

# Cria uma lista vazia para armazenar os resultados
results = []

# Itera sobre as linhas do DataFrame
for index, row in cnpjs.iterrows():
    # Obtém o CNPJ da linha atual
    cnpj = row["cnpj"]

    # Faz a consulta para o CNPJ atual
    conn = http.client.HTTPSConnection("receitaws.com.br")
    headers = { 'Accept': "application/json" }
    conn.request("GET", f"/v1/cnpj/{cnpj}", headers=headers)
    res = conn.getresponse()
    data = res.read()

    # Transforma os dados recebidos em um dicionário
    data_dict = json.loads(data.decode("utf-8"))

    # Adiciona o dicionário à lista de resultados
    results.append(data_dict)

    
    # Pausa a execução do código por 25 segundos e mostra um contador
    for i in range(25):
        print(f"Aguardando {25-i} segundos...")
        time.sleep(1)

# Cria um DataFrame a partir da lista de resultados
df = pd.DataFrame(results)

# Salva o DataFrame em um arquivo do Excel
df.to_excel("consinco/consulta_cnpjs.xlsx", index=False)
