# Manual de Utilizacao - Pessoa RJ

## 1. Visao geral

Aplicacao desktop para cadastro de pessoas fisicas no Consinco, consulta em bancos Oracle e execucao de rotinas auxiliares de apoio ao time.

As funcoes da tela principal foram reorganizadas em menu superior para reduzir excesso de botoes. Permanecem visiveis na barra principal apenas as acoes de uso direto da grade:

- `Importar Planilha`
- filtro de pesquisa
- `Selecionar/Desmarcar Todos`

As demais acoes ficam nos menus `Arquivo`, `Cadastro` e `Ferramentas`.

## 2. Pre-requisitos

- Python 3.11+ com dependencias instaladas.
- Bibliotecas usadas no projeto: `pandas`, `requests`, `oracledb`, `tkinter`, `pillow`, `fpdf`, `openpyxl`, `pypdf` ou `PyPDF2`.
- Oracle Instant Client configurado quando `oracledb` operar em modo thick.
- Acesso valido aos bancos Oracle configurados e a API Totvs Consinco.

## 3. Estrutura principal da aplicacao

- `cadastro_pessoa_gui.py`: ponto de entrada simples para execucao local.
- `pessoa_rj/__main__.py`: dispatcher da aplicacao principal e das rotinas auxiliares.
- `pessoa_rj/ui/app.py`: janela principal, menu, grade, log e abertura das rotinas auxiliares.
- `pessoa_rj/ui/dialogs.py`: dialogos auxiliares, incluindo busca de CPFs.
- `pessoa_rj/tools/convert.py`: extracao de comprovantes PDF a partir de TXT + PDF macro.
- `pessoa_rj/tools/comprov.py`: geracao de comprovante trabalhista RJ.
- `pessoa_rj/tools/gerar_planilha_fgts.py`: extracao de competencias de FGTS a partir de TXT analitico.

## 4. Executando a aplicacao

### Desenvolvimento

```powershell
python -m pessoa_rj
```

### Executavel

Utilize o executavel gerado pelo PyInstaller no diretorio de distribuicao.

## 5. Como identificar a versao em uso

Voce pode verificar a versao atual de tres formas:

- na barra de titulo da janela principal
- em `Ajuda > Sobre`
- nas propriedades do arquivo `cadastro_pessoa_gui.exe`, aba `Detalhes`

## 6. Como atualizar a versao instalada

Fluxo recomendado para o usuario final:

1. Fechar completamente o sistema.
2. Substituir o `cadastro_pessoa_gui.exe` antigo pelo novo.
3. Manter o mesmo atalho ou a mesma pasta de instalacao para evitar reconfiguracao manual.

Se a versao antiga estiver em uso no momento da copia, o Windows pode bloquear a substituicao do arquivo.

## 7. Fluxo principal de cadastro

1. Fazer login com usuario e senha Totvs.
2. Importar uma planilha `.xlsx` ou usar `Cadastro > Buscar Dados Bancos`.
3. Filtrar os registros pela barra principal.
4. Marcar os itens desejados na grade.
5. Usar `Selecionar/Desmarcar Todos` quando precisar atuar no conjunto exibido.
6. Acionar `Cadastro > Cadastrar Selecionados`.
7. Conferir o painel de log e o arquivo `resultado_<nome>.xlsx` gerado ao lado da planilha importada.

## 8. Menus da tela principal

### Arquivo

- `Importar Planilha`: carrega o Excel base para a grade principal.
- `Sair`: encerra a aplicacao.

### Cadastro

- `Buscar Dados Bancos`: abre a rotina de consulta de CPFs nos bancos Oracle.
- `Cadastrar Selecionados`: envia para a API Totvs os registros marcados.

### Ferramentas

- `Extrair Comprovantes PDF (TXT/PDF)`: abre a rotina de segmentacao de comprovantes.
- `Gerar Comprovante Trabalhista (RJ)`: abre a rotina de emissao de PDFs trabalhistas.
- `Extrato planilha FGTS`: abre a rotina de leitura do extrato analitico FGTS e exportacao para Excel.

## 9. Rotina Extrato planilha FGTS

### Objetivo

Gerar uma planilha unica com competencias de FGTS a partir de um ou mais arquivos `.txt` de extrato analitico.

### Como usar

1. Abrir `Ferramentas > Extrato planilha FGTS`.
2. Selecionar um ou mais arquivos `.txt`.
3. Escolher o destino no `Salvar como`.
4. Clicar em `GERAR`.

### Regras principais

- A rotina consolida varios TXTs em um unico `.xlsx`.
- O Excel e gerado na aba `Competencias_FGTS`.
- Sao exportadas competencias por extenso como `JANEIRO/2016`.
- Tambem sao exportadas competencias codificadas como `M09/2016`, `R09/2016`, `RE09/2016`, `RESCISOR09/2016` e equivalentes validos.
- Lancamentos sem competencia identificavel nao entram na saida.
- Placeholders invalidos como `0/0000` sao ignorados.

### Colunas da planilha

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

## 10. Rotina Extrair Comprovantes PDF (TXT/PDF)

Usa um relatorio TXT e um ou mais PDFs macro para localizar comprovantes e gerar:

- PDFs individuais
- `resumo_extracao.xlsx`
- `comprovantes.zip`

Os arquivos sao salvos na pasta escolhida pelo usuario.

## 11. Rotina Gerar Comprovante Trabalhista (RJ)

Usa as planilhas Base RJ e Movimentacao C5 para montar PDFs por credor, com suporte a exportacao unica ou em lote.

## 12. Logs e arquivos de saida

- Log principal: `pessoa_rj.log`
- Tokens: `token_storage.json`
- Resultado de cadastro: `resultado_<nome_da_planilha>.xlsx`
- Rotinas auxiliares: salvam na pasta escolhida pelo usuario

## 13. Resolucao rapida de problemas

- Falha de login: validar usuario, senha e conectividade com a API Totvs.
- Falha Oracle: validar rede, VPN, credenciais e ambiente do Instant Client.
- Janela auxiliar nao abre no executavel: revisar `hiddenimports` e `datas` do `cadastro_pessoa_gui.spec`.
- Arquivo FGTS sem saida: validar se o TXT possui lancamentos com competencia identificavel.
