# Primeiro, vamos ler o arquivo
with open('arquivo.txt', 'r') as f:
    linhas = f.readlines()

registros = []
for linha in linhas:
    campos = linha.strip().split('|')
    if campos[1] == 'H001' or campos[1] == 'H990':
        registros.append({"tipo": campos[1], "valor": campos[2]})
    elif campos[1] == 'H005':
        registros.append({"tipo": campos[1], "data": campos[2], "valor": float(campos[3].replace(',', '.')), "ind": campos[4]})
    elif campos[1] == 'H010':
        registros.append({"tipo": campos[1], "cod_item": campos[2], "unid": campos[3], "qtd": float(campos[4].replace(',', '.')) if ',' in campos[4] else int(campos[4]), "vl_unit": float(campos[5].replace(',', '.')), "vl_item": float(campos[6].replace(',', '.')), "ind_prop": campos[7], "cod_part": campos[8], "txt_compl": campos[9], "cod_cta": campos[10], "vl_item_ir": float(campos[11].replace(',', '.'))})

# Vamos supor que o novo valor para o H005 é 781442.18
novo_valor_H005 = 1167034.23

# Calculamos o fator de proporção
fator = novo_valor_H005 / registros[1]["valor"]

# Atualizamos o valor do H005
registros[1]["valor"] = novo_valor_H005

# Agora atualizamos os valores dos H010
for registro in registros[2:-1]:
    if registro["tipo"] == "H010":
        registro["vl_unit"] = round(registro["vl_unit"] * fator, 6)
        registro["vl_item"] = round(registro["qtd"] * registro["vl_unit"], 2)
        registro["vl_item_ir"] = registro["vl_item"]

# Agora os registros estão atualizados
with open('arquivo_atualizado.txt', 'w') as f:
    for registro in registros:
        if registro["tipo"] == "H001" or registro["tipo"] == "H990":
            f.write(f"|{registro['tipo']}|{registro['valor']}|\n")
        elif registro["tipo"] == "H005":
            f.write(f"|{registro['tipo']}|{registro['data']}|{registro['valor']:.2f}|{registro['ind']}|\n".replace('.', ','))
        elif registro["tipo"] == "H010":
            qtd_formatada = f'{registro["qtd"]:.2f}' if isinstance(registro["qtd"], float) else f'{registro["qtd"]}'
            f.write(f"|{registro['tipo']}|{registro['cod_item']}|{registro['unid']}|{qtd_formatada}|{registro['vl_unit']:.6f}|{registro['vl_item']:.2f}|{registro['ind_prop']}|{registro['cod_part']}|{registro['txt_compl']}|{registro['cod_cta']}|{registro['vl_item_ir']:.2f}|\n".replace('.', ','))
