import os
import shutil
from datetime import datetime, timedelta

def mover_xml_modificados(entrada, destino, cnpj):
    # Obtém a data de ontem
    data_ontem = datetime.now() - timedelta(days=1)
    
    # Formata a data no formato esperado para comparação
    data_formatada = data_ontem.strftime("%Y-%m-%d")

    # Constrói o caminho do diretório de origem (B:\)
    caminho_origem = os.path.join(entrada)

    # Constrói o caminho do diretório de destino (C:\AreaNfe\xml\{cnpj}\processar)
    caminho_destino = os.path.join(destino, cnpj, "processar")

    # Garante que o diretório de destino existe, se não, cria
    os.makedirs(caminho_destino, exist_ok=True)

    # Itera sobre os arquivos no diretório de origem
    for arquivo in os.listdir(caminho_origem):
        caminho_arquivo = os.path.join(caminho_origem, arquivo)
        
        # Verifica se é um arquivo XML e se a data de modificação é a de ontem
        if arquivo.lower().endswith('.xml') and data_formatada in str(datetime.fromtimestamp(os.path.getmtime(caminho_arquivo)).date()):
            # Move o arquivo para o diretório de destino
            shutil.move(caminho_arquivo, caminho_destino)
            print(f"Arquivo {arquivo} movido para {caminho_destino}")

# Exemplo de uso
if __name__ == "__main__":
    diretorio_entrada = "B:\\"
    diretorio_destino = "C:\\AreaNfe\\xml\\"
    cnpj_empresa = "12023966000123"

    mover_xml_modificados(diretorio_entrada, diretorio_destino, cnpj_empresa)
