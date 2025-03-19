# Dicionário para armazenar os valores acumulados por número do documento fiscal e chave C190
valores_acumulados = {}

# Lista para armazenar as linhas corrigidas do arquivo
linhas_corrigidas = []

# Variável para controlar o número do documento fiscal atual
documento_atual = None

# Variável para armazenar a linha C190 atual
linha_atual = None

# Percorre cada linha do arquivo
with open('loja 09_EMP9 2_EMP9_CST.TXT', 'r') as arquivo:
    for linha in arquivo:
        campos = linha.split('|')
        # Verifica se é um registro C100
        if campos[1] == 'C100':
            # Atualiza o número do documento fiscal atual
            documento_atual = campos[9]
            # Zera a chave de busca
            valores_acumulados = {}
            linhas_corrigidas.append(linha)
        # Verifica se é um registro C190
        elif campos[1] == 'C190':
            # Chave para agrupar por documento fiscal e C190
            chave = (documento_atual, campos[1], campos[2], campos[3], campos[4])
            # Verifica se a chave já existe no dicionário
            if chave in valores_acumulados:
                # Se já existe, acumula os valores
                for i in range(5, 14):
                    valores_acumulados[chave][i-5] += float(campos[i].replace(',', '.')) if campos[i].strip() else 0
            else:
                # Se não existe, adiciona ao dicionário
                valores_acumulados[chave] = [float(campos[i].replace(',', '.')) if campos[i].strip() else 0 for i in range(5, 14)]
                # Adiciona a linha corrigida à lista
                if linha_atual:
                    linhas_corrigidas.append(linha_atual)
                linha_atual = linha
        else:
            # Adiciona a linha original à lista
            linhas_corrigidas.append(linha)

# Adiciona a última linha C190 à lista
if linha_atual:
    linhas_corrigidas.append(linha_atual)

# Atualiza as linhas com os valores acumulados
for i in range(len(linhas_corrigidas)):
    campos = linhas_corrigidas[i].split('|')
    if campos[1] == 'C190':
        chave = (documento_atual, campos[1], campos[2], campos[3], campos[4])
        if chave in valores_acumulados:
            linhas_corrigidas[i] = '|'.join(list(chave) + [str(valor).replace('.', ',') for valor in valores_acumulados[chave]]) + '||\n'

# Sobrescreve o arquivo com as linhas corrigidas
with open('loja 09_EMP9 2_EMP9_CST.TXT_corrigido.txt', 'w') as arquivo_corrigido:
    for linha in linhas_corrigidas:
        arquivo_corrigido.write(linha)

print("Arquivo corrigido com sucesso!")
