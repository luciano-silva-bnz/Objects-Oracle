import requests
import cx_Oracle
import pandas as pd

# Configurações do banco de dados e API
DATABASE_DSN = cx_Oracle.makedsn('189.126.156.13', '1521', service_name='CM6QEI_150976_C')
DATABASE_USER = 'CLT150976POWERBI'
DATABASE_PASSWORD = 'hdeak29453HJBED!?'

API_BASE_URL = 'https://pubdata.nappsolutions.io/api/'

USERNAME = 'esphera.caruarushopping_bonanza'
PASSWORD = '85fvANa13'

# Função para obter o token de autenticação
def get_auth_token():
    auth_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    response = requests.post(API_BASE_URL+'auth', json=auth_data)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        response.raise_for_status()

# Conectando ao banco de dados Oracle
def get_connection_db():
    return cx_Oracle.connect(DATABASE_USER, DATABASE_PASSWORD, DATABASE_DSN)

def get_data_from_db(query):
    connection = get_connection_db()
    cursor = connection.cursor()
    cursor.execute(query)
    columns = [col[0] for col in cursor.description]
    result = cursor.fetchall()
    cursor.close()
    connection.close()
    return pd.DataFrame(result, columns=columns)

# Função para renomear os arquivos locais com base no nome retornado pela API
def rename_local_files(signed_urls, file_paths):
    renamed_files = []
    
    for url, file_path in zip(signed_urls, file_paths):
        # Extrair o novo nome do arquivo da URL assinada
        new_filename = url.split('/')[-1]
        new_file_path = os.path.join(os.path.dirname(file_path), new_filename)
        
        # Renomear o arquivo local
        os.rename(file_path, new_file_path)
        
        renamed_files.append(new_file_path)
    
    return renamed_files

# Função para enviar os nomes dos arquivos e obter as URLs assinadas
def post_upload(token, files_info):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(API_BASE_URL+'upload', json=files_info, headers=headers)
        response.raise_for_status()  # Levanta um erro para códigos de status 4xx/5xx
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Exibe o erro HTTP
        print(f'Response content: {response.content}')  # Exibe o conteúdo da resposta
    except Exception as err:
        print(f'Other error occurred: {err}')  # Exibe outros tipos de erro

# Função para fazer o upload dos arquivos renomeados para o Google Storage
def upload_to_storage(signed_urls, renamed_files):
    headers = {'Content-Type': 'plain/text'}
    
    for url, file_path in zip(signed_urls, renamed_files):
        with open(file_path, 'rb') as file_data:
            response = requests.put(url, headers=headers, data=file_data)
            if response.status_code == 200:
                print(f"Upload do arquivo {file_path} concluído com sucesso.")
            else:
                print(f"Erro ao fazer upload do arquivo {file_path}: {response.status_code}")

def carregar_sql(arquivo_sql):
    with open(arquivo_sql, 'r', encoding='utf-8') as file:
        return file.read()

def process_data_and_call_api():
    # Obter o token de autenticação
    token = get_auth_token()
    
    # Carregar as queries
    query_catalogo = carregar_sql('consinco\\napp\\qry_catalogo.sql')
    query_itens_venda = carregar_sql('consinco\\napp\\qry_itens_vendas.sql')
    query_dados_venda = carregar_sql('consinco\\napp\\qry_dados_vendas.sql')

    # Obter dados da Venda, Itens e Catálogo
    dados_venda_df = get_data_from_db(query_dados_venda)
    itens_venda_df = get_data_from_db(query_itens_venda)
    catalogo_df = get_data_from_db(query_catalogo)

    # Ajustar campos numéricos com zeros à esquerda
    catalogo_df['CODNBMSH'] = catalogo_df['CODNBMSH'].astype(str).str.zfill(8)
    
    # Salvar os DataFrames em CSV
    dados_venda_csv = 'bnz_dados_venda.csv'
    itens_venda_csv = 'bnz_itens_venda.csv'
    catalogo_csv = 'bnz_catalogo.csv'

    # Salvar os DataFrames sem cabeçalho
    dados_venda_df.to_csv(dados_venda_csv, index=False, sep=';', header=False)
    itens_venda_df.to_csv(itens_venda_csv, index=False, sep=';', header=False)
    catalogo_df.to_csv(catalogo_csv, index=False, sep=';', header=False)

    # Preparar os dados para a API de upload
    files_info = {
        "files": [
            {"type": "vendas", "name": "bnz_dados_venda.csv"},
            {"type": "vendas", "name": "bnz_itens_venda.csv"},
            {"type": "catalogo", "name": "bnz_catalogo.csv"}
        ]
    }

    # Enviar os arquivos para a API e obter as URLs assinadas
    response = post_upload(token, files_info)
    upload_urls = response.get("uploadFiles", [])

    # Mapeamento de arquivos locais para os renomeados pela API
    file_name_mapping = {
        "bnz_dados_venda.csv": dados_venda_csv,
        "bnz_itens_venda.csv": itens_venda_csv,
        "bnz_catalogo.csv": catalogo_csv
    }

    # Fazer upload dos arquivos para as URLs assinadas
    for file_info in upload_urls:
        renamed_file = file_info['name']  # Nome do arquivo renomeado pela API
        original_file = file_name_mapping.get(renamed_file.split('_')[-1], '')  # Localiza o arquivo original
        upload_url = file_info['url']

        if original_file:
            upload_to_storage(original_file, upload_url)
        else:
            print(f"Arquivo original não encontrado para {renamed_file}")

if __name__ == "__main__":
    process_data_and_call_api()