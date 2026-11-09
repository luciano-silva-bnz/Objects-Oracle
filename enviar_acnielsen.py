import os
import posixpath
import shutil
import paramiko
from contextlib import contextmanager


@contextmanager
def sftp_connection(host, username, password, port=22, compress=False):
    """Manage both SSH and SFTP lifetimes; retain the existing host-key policy."""
    with paramiko.SSHClient() as client:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username=username,
                       password=password, compress=compress,
                       allow_agent=False, look_for_keys=False)
        with client.open_sftp() as sftp:
            yield sftp


def download_preserving_mtime(sftp, remote_path, local_path):
    """Paramiko equivalent of pysftp.get(..., preserve_mtime=True)."""
    attributes = sftp.stat(remote_path)
    sftp.get(remote_path, local_path)
    os.utime(local_path, (attributes.st_atime, attributes.st_mtime))

def enviar_arquivo(caminho_arquivo):
    try:
        # Configuração das credenciais SFTP

        # Conecta-se ao servidor SFTP
        with sftp_connection(
            host="namft.nielseniq.com",
            username="mft@bonanza.br",
            password="GI&7%md6Bq%1",
            compress=False
        ) as sftp:
            # Define o diretório remoto
            diretorio_remoto = "/DELIVERY"
            
            # Define o caminho de destino no servidor SFTP
            caminho_destino_sftp = posixpath.join(diretorio_remoto, os.path.basename(caminho_arquivo))
            
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
