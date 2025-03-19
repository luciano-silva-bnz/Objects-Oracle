import os
import xml.etree.ElementTree as ET
import pandas as pd
from tkinter import Tk, filedialog
from datetime import datetime

def selecionar_pasta():
    """Abre uma janela para selecionar a pasta que contém os arquivos XML."""
    Tk().withdraw()  # Oculta a janela principal do Tkinter
    return filedialog.askdirectory(title="Selecione a pasta com arquivos XML")

def formatar_valor(valor):
    """Formata valores numéricos, substituindo '.' por ','."""
    if valor is None:
        return None
    try:
        # Substituir ponto por vazio e vírgula por ponto para decimal
        return float(valor.replace(',', '.'))
    except Exception as e:
        print(f"Erro ao formatar valor '{valor}': {e}")
        return None

def formatar_data(data):
    """Converte a data do formato XML para o formato padrão do Excel."""
    if data is None:
        return None
    try:
        return datetime.strptime(data, "%d-%b-%y").strftime("%d/%m/%Y")
    except Exception as e:
        print(f"Erro ao formatar data '{data}': {e}")
        return None

def extrair_dados_xml(caminho):
    """Extrai dados de um arquivo XML específico."""
    try:
        tree = ET.parse(caminho)
        root = tree.getroot()

        # Namespaces do XML
        namespaces = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

        # Extração dos dados
        data_emissao = root.find('.//ns:ide/ns:dEmi', namespaces)
        valor_nota = root.find('.//ns:total/ns:ICMSTot/ns:vNF', namespaces)
        emitente = root.find('.//ns:emit/ns:xNome', namespaces)
        destinatario = root.find('.//ns:dest/ns:xNome', namespaces)

        # Formatar os dados extraídos
        data_emissao = formatar_data(data_emissao.text if data_emissao is not None else None)
        valor_nota = formatar_valor(valor_nota.text if valor_nota is not None else None)
        emitente = emitente.text if emitente is not None else "Desconhecido"
        destinatario = destinatario.text if destinatario is not None else "Desconhecido"

        return {
            "Nome do Arquivo": os.path.basename(caminho),
            "Data Emissão": data_emissao,
            "Valor Nota": valor_nota,
            "Emitente": emitente,
            "Destinatário": destinatario
        }
    except ET.ParseError as e:
        print(f"Erro ao processar o arquivo {caminho}: {e}")
        return None

def processar_pasta(pasta):
    """Processa todos os arquivos XML em uma pasta."""
    dados = []
    for arquivo in os.listdir(pasta):
        if arquivo.lower().endswith('.xml'):  # Ignora maiúsculas e minúsculas
            caminho_arquivo = os.path.join(pasta, arquivo)
            info = extrair_dados_xml(caminho_arquivo)
            if info:
                dados.append(info)
    return dados

def salvar_planilha(dados, caminho_saida):
    """Salva os dados extraídos em uma planilha Excel."""
    df = pd.DataFrame(dados)
    df.to_excel(caminho_saida, index=False)
    print(f"Planilha salva em: {caminho_saida}")

if __name__ == "__main__":
    pasta = selecionar_pasta()
    if pasta:
        print("Processando arquivos...")
        dados_extraidos = processar_pasta(pasta)
        if dados_extraidos:
            salvar_planilha(dados_extraidos, os.path.join(pasta, "Dados_Extraidos.xlsx"))
        else:
            print("Nenhum dado foi extraído.")
    else:
        print("Nenhuma pasta foi selecionada.")
