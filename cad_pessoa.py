import requests
import json
import pandas as pd

# Fazer login na API e obter o token de acesso
login_url = 'https://bonanza150977.consinco.cloudtotvs.com.br:8343/api/v1/auth/login'
login_headers = {'Content-Type': 'application/json'}
login_data = {
    "company": "41",
    "username": "LUCIANO",
    "password": "09031110"
}

login_response = requests.post(
    login_url, headers=login_headers, data=json.dumps(login_data))

# Verifique o status da resposta
if login_response.status_code == 200:
    # A resposta foi bem-sucedida
    # Fa�a algo com os dados retornados
    login_data = login_response.json()
    token = login_data['access_token']
else:
    # Houve um erro
    print(f'Erro: {login_response.status_code}')

# Consultar informa��es sobre uma pessoa usando o token de acesso
pessoa_url = 'https://bonanza150977.consinco.cloudtotvs.com.br:8343/cadastrosestruturaisapi/api/v1/pessoa/Id'

pessoa_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
}
pessoa_params = {
    # Adicione aqui os par�metros necess�rios para a consulta
    # Por exemplo:
    'Id': 1,
}

pessoa_response = requests.get(
    pessoa_url, headers=pessoa_headers, params=pessoa_params)

# Verifique o status da resposta
if pessoa_response.status_code == 200:
    # A resposta foi bem-sucedida
    # Fa�a algo com os dados retornados
    pessoa_data = pessoa_response.json()
    print(f'OK: {pessoa_data}')
else:
    # Houve um erro
    print(f'Erro: {pessoa_response.status_code}')

# L� os dados da planilha
df = pd.read_excel('planilha.xlsx')

# Itera sobre cada linha da planilha
for index, row in df.iterrows():
    # Extrai os dados da linha
    data = {
        'NomeRazaoSocial': row['NomeRazaoSocial'],
        'Fantasia': row['Fantasia'],
        'CEP': row['CEP'],
        'NomeCidade': row['Cidade'],
        'NomeBairro': row['Bairro'],
        'DescricaoLogradouro': row['Logradouro'],
        'NumeroLogradouro': row['N�mero'],
        'ComplementoLogradouro': row['Complemento'],
        'TelefoneDDD1': row['DDD'],
        'TelefoneNumero1': row['N�mero'],
        'Email': row['email']
    }

    # Envia a solicita��o POST para incluir a pessoa
    url = 'https://bonanza150976.consinco.cloudtotvs.com.br:8343/cadastrosestruturaisapi/api/v1/Pessoa'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    # Verifique o status da resposta
    if response.status_code == 200:
        # A inclus�o foi bem-sucedida
        print(f'Pessoa {index + 1} incluída com sucesso!')
    else:
        # Houve um erro
        print(f'Erro ao incluir pessoa {index + 1}: {response.status_code}')
