import os
import shutil
import pysftp

def enviar_arquivo(caminho_arquivo):
    try:
        # Configuração das credenciais SFTP
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # Ignora a verificação da chave de host

        # Conecta-se ao servidor SFTP
        with pysftp.Connection(
            host="namft.nielseniq.com",
            username="mft@bonanza.br",
            password="GI&7%md6Bq%1",
            cnopts=cnopts
        ) as sftp:
            # Define o diretório remoto
            diretorio_remoto = "/DELIVERY"
            
            # Define o caminho de destino no servidor SFTP
            caminho_destino_sftp = os.path.join(diretorio_remoto, os.path.basename(caminho_arquivo))
            
            # Envia o arquivo
            sftp.put(caminho_arquivo, caminho_destino_sftp)

        print(f"Arquivo {caminho_arquivo} enviado com sucesso!")

        return True

    except Exception as e:
        print(f"Falha ao enviar arquivo {caminho_arquivo}: {str(e)}")
        return False

def mover_arquivos(origem, destino):
    try:
        # Obtém a lista de arquivos no diretório de origem com extensão .txt
        arquivos = [arquivo for arquivo in os.listdir(origem) if arquivo.lower().endswith(".txt") and os.path.isfile(os.path.join(origem, arquivo))]

        # Move cada arquivo para o diretório de destino
        for arquivo in arquivos:
            caminho_origem = os.path.join(origem, arquivo)

            # Envia o arquivo antes de movê-lo
            if enviar_arquivo(caminho_origem):
                caminho_destino = os.path.join(destino, arquivo)
                shutil.move(caminho_origem, caminho_destino)

    except Exception as e:
        print(f"Erro ao mover/arquivar os arquivos: {str(e)}")

# Restante do código...


# Diretórios de origem e destino
diretorio_origem = r'N:\\'
diretorio_destino = r'C:\\ETL\\Acnielsen'

# Chama a função para mover e enviar arquivos
mover_arquivos(diretorio_origem, diretorio_destino)
