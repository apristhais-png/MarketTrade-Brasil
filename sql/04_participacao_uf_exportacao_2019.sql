-- Participação % de cada UF no total nacional (EXPORTACAO, 2019), pelo valor FOB em US$.
-- Denominador = total nacional COMPLETO (inclui códigos especiais); os códigos especiais
-- aparecem agregados na linha 'UF_ESPECIAL', de modo que a soma das linhas é 100%.
WITH por_uf AS (
  SELECT CASE WHEN uf_oficial THEN uf ELSE 'UF_ESPECIAL' END AS uf,
         sum(valor_fob_usd) AS valor_fob_usd
  FROM fato
  WHERE tipo_operacao = 'EXPORTACAO' AND ano = 2019
  GROUP BY 1
)
SELECT uf, valor_fob_usd,
       sum(valor_fob_usd) OVER () AS total_nacional_fob_usd,
       round(100.0 * valor_fob_usd / sum(valor_fob_usd) OVER (), 4) AS participacao_pct
FROM por_uf
ORDER BY (uf = 'UF_ESPECIAL'), valor_fob_usd DESC, uf;
