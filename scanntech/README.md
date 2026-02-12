# Schanntech Club Promo

Projeto PHP para consultar campanhas Scanntech por filial, com filtros em tempo real e administracao de filiais.

## Estrutura

- `public/index.php`: pagina principal de consulta.
- `public/api/promocoes.php`: endpoint backend para consolidar API externa.
- `public/admin/filiais.php`: cadastro e manutencao de filiais.
- `storage/filiais.json`: lista de filiais utilizadas na consulta.
- `config/.env.example`: exemplo de credenciais e configuracoes.

## Configuracao

1. Copie `config/.env.example` para `config/.env`.
2. Preencha:
   - `SCANNTECH_USER`
   - `SCANNTECH_PASS`
3. Ajuste timeout e cache se necessario.

## Execucao local

Suba um servidor PHP apontando para `public/`.

Exemplo:

```bash
php -S localhost:8080 -t public
```
