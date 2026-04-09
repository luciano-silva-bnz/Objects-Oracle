# Dados Tecnicos - Pessoa RJ

## 1. Arquitetura

Aplicacao desktop em Python com interface `tkinter`, organizada em pacote principal `pessoa_rj` e subpacote `pessoa_rj.tools` para as rotinas auxiliares.

Camadas principais:

- interface: `pessoa_rj/ui`
- integracao API: `pessoa_rj/api.py`
- banco Oracle: `pessoa_rj/database.py`
- configuracao e paths: `pessoa_rj/config.py`
- logging: `pessoa_rj/logging_config.py`
- persistencia de token: `pessoa_rj/token_store.py`

## 2. Modulos principais

### Aplicacao principal

- `pessoa_rj/ui/app.py`: constroi login, menu, grade principal, painel de log e abertura das rotinas auxiliares em subprocessos.
- `pessoa_rj/ui/dialogs.py`: dialogos de busca de CPF e importacoes auxiliares.
- `pessoa_rj/__main__.py`: recebe flags e despacha:
  - `--run-convert`
  - `--run-comprov`
  - `--run-fgts`

### Rotinas auxiliares

- `pessoa_rj/tools/convert.py`: processamento de TXT + PDF macro com `pypdf` e `openpyxl`.
- `pessoa_rj/tools/comprov.py`: geracao de PDF com `fpdf`.
- `pessoa_rj/tools/gerar_planilha_fgts.py`: parser de extrato analitico FGTS com exportacao Excel.

## 3. Interface atual

### Janela principal

Componentes:

- barra superior com estatisticas, importacao, filtro e botao `Selecionar/Desmarcar Todos`
- menu nativo com grupos `Arquivo`, `Cadastro` e `Ferramentas`
- `Treeview` para a grade principal
- painel inferior de log
- rodape com imagem redimensionavel

### Motivo da reorganizacao

A interface foi simplificada para evitar excesso de botoes na tela principal. Apenas a selecao em massa permaneceu visivel por ser uma acao diretamente ligada ao grid.

## 4. Fluxo de subprocessos auxiliares

A janela principal nao incorpora as ferramentas auxiliares. Ela relanca o proprio entrypoint com flags especificas.

Fluxo:

1. `ui/app.py` chama `_montar_comando_reexecucao`.
2. O processo filho inicia `cadastro_pessoa_gui.py`.
3. `pessoa_rj.__main__.py` interpreta a flag.
4. O modulo auxiliar correspondente executa sua propria `main()`.

Durante a execucao da rotina auxiliar:

- a janela principal fica desabilitada
- o processo filho e monitorado por polling com `after`
- ao encerrar, a janela principal e reabilitada

## 5. Rotina Extrato planilha FGTS

### Responsabilidades

- selecionar um ou mais arquivos `.txt`
- consolidar os registros validos em um unico `DataFrame`
- exportar um `.xlsx` com aba `Competencias_FGTS`

### Funcoes principais

- `normalizar_caminhos(...)`: remove duplicidade de caminhos selecionados.
- `extrair_competencia(...)`: identifica competencia por extenso ou codificada.
- `ler_registros_fgts(...)`: extrai contexto do trabalhador e lancamentos validos por TXT.
- `gerar_dataframe_fgts(...)`: consolida todos os registros.
- `exportar_planilha_fgts(...)`: escreve o Excel final com autofiltro, freeze pane e ajuste basico de largura.

### Regras de parser

- contexto por trabalhador:
  - nome
  - PIS/PASEP
  - matricula
  - data de admissao
  - data de afastamento
  - empregador
  - inscricao do empregador
- lancamento valido:
  - data
  - descricao
  - valor
  - competencia identificavel
- competencias aceitas:
  - por extenso, exemplo `JANEIRO/2016`
  - codificadas, exemplo `M09/2016`, `R09/2016`, `RE09/2016`, `RESCISOR09/2016`, `BA12/2023`
- exclusoes:
  - saques
  - creditos sem competencia
  - placeholders invalidos como `0/0000`

### Colunas exportadas

- `Arquivo Origem`
- `Nome`
- `PIS/PASEP`
- `Matricula`
- `Data Admissao`
- `Data Afastamento`
- `Empregador`
- `Inscricao Empregador`
- `Data Lancamento`
- `Competencia`
- `Tipo Lancamento`
- `Descricao Original`
- `Valor (texto)`
- `Valor`

## 6. Oracle e API

### Oracle

- bancos configurados: `BNZ`, `MLT`, `ALI`
- SQLs em `pessoa_rj/queries`
- consultas retornam `DataFrame` consolidado para uso na interface

### API Totvs

- autenticacao e refresh token controlados por `requests.Session`
- refresh token persistido em `token_storage.json`
- cadastro de pessoas fisicas enviado para o endpoint configurado em `config.py`

## 7. Logging e runtime

- `pessoa_rj/logging_config.py` centraliza o `FileHandler`
- `pessoa_rj.log` e `token_storage.json` ficam no diretorio de execucao
- quando congelado, o runtime usa a pasta do executavel

## 8. Empacotamento

O arquivo `cadastro_pessoa_gui.spec` precisa manter:

- assets
- SQLs
- `hiddenimports` das rotinas auxiliares

Estado atual dos `hiddenimports` relevantes:

- `pessoa_rj.tools.convert`
- `pessoa_rj.tools.comprov`
- `pessoa_rj.tools.gerar_planilha_fgts`

Sem isso, as rotinas abertas por import dinamico podem funcionar no codigo-fonte e falhar no executavel.

## 9. Seguranca e manutencao

- Credenciais Oracle ainda estao em codigo e devem ser tratadas como sensiveis.
- Logs podem conter CPFs, ids e caminhos de arquivo.
- `token_storage.json` contem refresh token e precisa de protecao no ambiente.
- Alteracoes futuras na UI principal devem considerar que a barra superior agora representa apenas operacoes do grid, enquanto funcoes de apoio ficam no menu.

## 10. Checklist tecnico pos-alteracao

1. Validar `python -m py_compile` nos arquivos alterados.
2. Testar login e importacao de planilha.
3. Testar `Cadastro > Buscar Dados Bancos`.
4. Testar `Ferramentas > Extrair Comprovantes PDF (TXT/PDF)`.
5. Testar `Ferramentas > Gerar Comprovante Trabalhista (RJ)`.
6. Testar `Ferramentas > Extrato planilha FGTS`.
7. Se houver build, validar abertura das rotinas auxiliares no executavel.
