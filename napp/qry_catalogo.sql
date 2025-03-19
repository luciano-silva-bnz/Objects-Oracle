SELECT
    p.seqproduto AS "Id do produto",
    p.desccompleta AS "Nome do Produto",
    (nvl((
        SELECT
            MAX(cp.codacesso)
        FROM
            CONSINCO.map_prodcodigo cp
        WHERE
            cp.seqproduto = p.seqproduto
            AND cp.tipcodigo = 'E'
            AND cp.indutilvenda = 'S'
    ),
    (
        SELECT
            MAX(cp.codacesso)
        FROM
            CONSINCO.map_prodcodigo cp
        WHERE
            cp.seqproduto = p.seqproduto
            AND cp.tipcodigo = 'B'
            AND cp.indutilvenda = 'S'
    ))) AS "EAN",
    p.desccompleta AS "Descrição",
    mf.CODNBMSH AS "NCM",
    '' AS "Marca",
    0 AS "Peso Líquido",
    0 AS "Peso Metro Cúbico",
    0 AS "Comprimento",
    0 AS "Largura",
    0 AS "Altura",
    0 AS "Comprimento (Pacote)",
    0 AS "Largura (Pacote)",
    0 AS "Altura (Pacote)",
    '' AS "Categoria",
    '' AS "Cor",
    '' AS "Tamanho",
    '' AS "Coleção",
    '' AS "Origem",
    '' AS "Material",
    '' AS "Modelo",
    '' AS "Gênero",
    p.reffabricante AS "Fabricante",
    '' AS "Composição",
    '' AS "Garantia",
    '' AS "ISBN",
    '' AS "Linha",
    '' AS "Tipo de Cabelo",
    0 AS "Polegadas",
    0 AS "Voltagem",
    0 AS "BTU",
    '' AS "Editora",
    '' AS "Edição",
    '' AS "Idioma",
    '' AS "Autor",
    '' AS "Faixa Etária",
    0 AS "Quantidade de Peças",
    '' AS "Porte da Raça",
    0 AS "Ano de Lançamento",
    '' AS "Id do estoque",
    c.estqloja AS "Quantidade do Estoque",
    mp.MOTIVOPRECOVALIDO AS "Id do preço",
    mp.PRECOVALIDNORMAL AS "Preço Bruto",
    CASE 
        WHEN mp.PRECOVALIDPROMOC > 0 THEN mp.PRECOVALIDPROMOC
        ELSE mp.PRECOVALIDNORMAL
    END AS "Preço Líquido",
    DECODE(mp.STATUSVENDA, 'I', 'Inativo', 'Ativo') AS "Status"
FROM
    CONSINCO.map_produto p
    INNER JOIN consinco.map_familia mf ON mf.seqfamilia = p.seqfamilia
    INNER JOIN CONSINCO.mrl_produtoempresa c ON c.seqproduto = p.seqproduto
    INNER JOIN consinco.MRL_PRODEMPSEG mp ON mp.NROEMPRESA = c.NROEMPRESA AND mp.SEQPRODUTO = p.SEQPRODUTO AND mp.QTDEMBALAGEM = 1
WHERE
    c.nroempresa = 52
