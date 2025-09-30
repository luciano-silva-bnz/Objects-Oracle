SELECT
    r.ra_filial,
    r.ra_mat,
    r.ra_nome,
    r.ra_nasc,
    r.ra_cic,
    r.ra_codfunc,
    r.ra_proces,
    r.ra_msblql,
    r.ra_estado,
    r.ra_municip,
    r.ra_bairro,
    r.ra_enderec,
    r.ra_numende,
    r.ra_sexo,
    r.ra_cep,
    r.ra_dddcelu,
    r.ra_numcelu,
    r.ra_telefon,
    r.ra_rg,
    CASE
        WHEN TRIM(r.ra_numcelu) IS NULL OR TRIM(r.ra_numcelu) = '' THEN NULL
        WHEN length(trim(regexp_replace(r.ra_numcelu, '[^0-9]', ''))) < 8 THEN NULL
        ELSE
            CASE 
                WHEN length(regexp_replace(r.ra_numcelu, '[^0-9]', '')) = 8 THEN
                    substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 1, 4) || '-' ||
                    substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 5, 4)
                WHEN length(regexp_replace(r.ra_numcelu, '[^0-9]', '')) = 9 THEN
                    substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 1, 5) || '-' ||
                    substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 6, 4)
                ELSE regexp_replace(r.ra_numcelu, '[^0-9]', '')
            END
    END AS telefone_formatado
FROM u_c1pcxh_pr.sra020 r
WHERE r.ra_demissa <> ' '
  AND r.d_e_l_e_t_ = ' '
  --AND r.ra_demissa >= '20150101'
  AND r.ra_rescrai NOT IN ('30', '31')
  AND {in_clause}
ORDER BY r.ra_filial
