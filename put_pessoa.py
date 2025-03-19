# -*- coding: iso-8859-1 -*-
import requests
import json
import pandas as pd
from tkinter import filedialog
from unidecode import unidecode
import string

# Cria uma tabela de tradu��o que remove os caracteres especiais
translator = str.maketrans('', '', string.punctuation)


def incluir_pessoa(data, token):
    # Envia a solicita��o POST para incluir a pessoa
    url = 'https://bonanza150976.consinco.cloudtotvs.com.br:8343/cadastrosestruturaisapi/api/v1/pessoa'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    # Verifique o status da resposta
    if response.status_code in [200, 201]:
        # A inclus�o foi bem-sucedida
        id_pessoa = json.loads(response.text)['idPessoa']
        print(id_pessoa)
        return True, id_pessoa, None
    else:
        # Houve um erro
        error_message = json.loads(response.text)
        print(error_message)
        return False, None, error_message


def ler_planilha(filename):
    # L� os dados da planilha
    df = pd.read_excel(
        filename, dtype={'InscricaoEstadualRG': str, 'CEP': str})
    return df


def replace_nan(x):
    if pd.isna(x):
        return ''
    else:
        return x


def incluir_pessoas_da_planilha(filename, token, log_filename):
    # Abre o arquivo de log para escrita
    with open(log_filename, 'w') as log_file:
        # Escreve o cabe�alho do arquivo de log
        log_file.write('NumeroCPFCNPJ;Status;idPessoa;Mensagem\n')
        # L� os dados da planilha
        df = ler_planilha(filename)

        # Remove os NAN
        df = df.applymap(replace_nan)
        # Itera sobre cada linha da planilha
        for index, row in df.iterrows():
            # Extrai os dados da linha
            data = {

                'NumeroCPFCNPJ': row['NumeroCPFCNPJ'],
                'DigitoCPFCNPJ': row['DigitoCPFCNPJ'],
                'NomeRazaoSocial': unidecode(row['NomeRazaoSocial']).translate(translator).upper(),
                'Fantasia': unidecode(row['Fantasia']).translate(translator).upper()[:30],
                'UFCidade': row['UFCidade'],
                'CEP': row['CEP'],
                # 'NomeCidade': unidecode(row['NomeCidade']).translate(translator).upper(),
                # 'NomeBairro': unidecode(row['NomeBairro']).translate(translator).upper(),
                # 'DescricaoLogradouro': unidecode(row['DescricaoLogradouro']).translate(translator).upper(),
                'NumeroLogradouro': row['NumeroLogradouro'],
                'ComplementoLogradouro': unidecode(row['ComplementoLogradouro']).translate(translator).upper()[:60],
                'InscricaoEstadualRG': row['InscricaoEstadualRG'],
                'TelefoneDDD1': row['TelefoneDDD1'],
                'TelefoneNumero1': row['TelefoneNumero1'],
                'Email': row['Email'],
                'Status': 'A',
                'Tipo': 'J'
            }

            # Inclui a pessoa
            success, id_pessoa, error_message = incluir_pessoa(data, token)
            if success:
                print(
                    f'Pessoa {data["NumeroCPFCNPJ"]} inclu�da com sucesso!')
                # Escreve as informa��es no arquivo de log
                log_file.write(
                    f'{data["NumeroCPFCNPJ"]};Inclu�da;{id_pessoa};\n')
            else:
                print(f'Erro ao incluir pessoa {data["NumeroCPFCNPJ"]}')
                # Escreve as informa��es no arquivo de log
                log_file.write(
                    f'{data["NumeroCPFCNPJ"]};Erro;;{error_message}\n')


# Fazer login na API e obter o token de acesso
login_url = 'https://bonanza150976.consinco.cloudtotvs.com.br:8343/api/v1/auth/login'
login_headers = {'Content-Type': 'application/json'}
login_data = {
    "company": "41",
    "username": "LUCIANOSILVA",
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

# Define o nome do arquivo da planilha
filename = filedialog.askopenfilename(
    filetypes=[("Arquivos do Excel", "*.xlsx")])

# Verifica se um arquivo foi selecionado
if filename:
    # Define o nome do arquivo de log
    log_filename = 'log.txt'
    # Inclui as pessoas da planilha
    incluir_pessoas_da_planilha(filename, token, log_filename)
else:
    # O usu�rio cancelou a sele��o
    print("Nenhum arquivo selecionado")
