SELECT
    V.NRODOCTO AS "Id do registro do item",
    V.NRODOCTO AS "Id da Venda",
    TO_CHAR(V.DTAHORLANCTO, 'YYYY-MM-DD HH24:MI:SS') AS "Data e horário da Venda",
    V.SEQPRODUTO AS "Id do Produto",
    (nvl((
        SELECT
            MAX(cp.codacesso)
        FROM
            CONSINCO.map_prodcodigo cp
        WHERE
            cp.seqproduto = V.seqproduto
            AND cp.tipcodigo = 'E'
            AND cp.indutilvenda = 'S'
    ),
    (
        SELECT
            MAX(cp.codacesso)
        FROM
            CONSINCO.map_prodcodigo cp
        WHERE
            cp.seqproduto = V.seqproduto
            AND cp.tipcodigo = 'B'
            AND cp.indutilvenda = 'S'
    ))) AS "EAN",
    P.DESCCOMPLETA AS "Nome",
    '' AS "CFOP",
    V.QTDITEM AS "Quantidade",
    0 AS "Peso",
    V.VLRITEMSEMDESC AS "Preço bruto unitário",
    V.VLRITEM AS "Preço líquido unitário",
    V.VLRDESCITEM AS "Desconto unitário do item",
    'Faturado' AS "Status"
FROM
    consinco.maxv_abcdistribbase V
INNER JOIN consinco.map_produto P ON
    P.SEQPRODUTO = V.SEQPRODUTO
WHERE
    V.dtavda >= (SYSDATE - 2)
    AND V.dtavda < (SYSDATE - 1)
    AND V.nroempresa = 52
    AND V.VLRITEM <> 0
