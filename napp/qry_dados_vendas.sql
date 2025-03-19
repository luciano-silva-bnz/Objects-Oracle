SELECT
    V.NRODOCTO AS "Id da venda",
    V.NRODOCTO AS "Número da Nota",
    TO_CHAR(V.DTAHORLANCTO, 'YYYY-MM-DD HH24:MI:SS') AS "Data e horário da Venda",
    SUM(V.VLRITEM) - SUM(V.VLRDESCITEM) + SUM(V.VLRACRESCIMO) AS "Valor Líquido da Venda",
    SUM(V.VLRITEM) AS "Subtotal da Venda",
    SUM(V.VLRACRESCIMO) AS "Valor de Frete / Acréscimo",
    SUM(V.VLRDESCITEM) AS "Valor do Desconto",
    'Faturado' AS "Status",
    V.SEQOPERADOR AS "Cód. do Vendedor",
    '' AS "Tipo de Envio",
    V.NROFORMAPAGTO AS "Id do Tipo de Pagamento",
    P.FORMAPAGTO AS "Tipo de Pagamento",
    '' AS "Id da Transação",
    1 AS "Número de Parcelas"
FROM
    consinco.maxv_abcdistribbase V
INNER JOIN consinco.MRL_FORMAPAGTO P ON
    P.NROFORMAPAGTO = V.NROFORMAPAGTO
WHERE
    V.dtavda >= (SYSDATE - 2)
    AND V.dtavda < (SYSDATE - 1)
    AND V.nroempresa = 52
    AND V.VLRITEM <> 0
GROUP BY
    V.NRODOCTO,
    V.DTAHORLANCTO,
    V.SEQOPERADOR,
    V.NROFORMAPAGTO,
    P.FORMAPAGTO
