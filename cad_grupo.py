#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
import pandas as pd
import pyautogui
import time
from tkinter import filedialog

'''
# Codigo para pegar a posição do mouse
for i in range(6):
    x, y = pyautogui.position()
    print("Posição do mouse: x={}, y={}".format(x, y))
    time.sleep(5)
'''

# ler a planilha com pandas
file = filedialog.askopenfile()
df = pd.read_excel(file.name)

# iterar sobre cada linha da planilha
for index, row in df.iterrows():
    # obter os valores das células "Nome" e "Sobrenome"
    nome = row['Nome']
    sobrenome = row['Sobrenome']

# inserir o valor da célula "Nome" no campo correspondente
    pyautogui.click(x=154, y=134)  # coordenadas do campo "input_nome"
    pyautogui.write(nome)

    # inserir o valor da célula "Sobrenome" no campo correspondente
    pyautogui.click(x=163, y=162)  # coordenadas do campo "input_sobrenome"
    pyautogui.write(sobrenome)

    # clicar no botão "Salvar"
    pyautogui.click(x=81, y=90)  # coordenadas do botão "botao_salvar"

    # aguardar a ação ser concluída
    time.sleep(3)

# mensagem de finalização
print('Processo concluído com sucesso!')
