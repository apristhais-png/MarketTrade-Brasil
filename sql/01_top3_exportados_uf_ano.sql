-- Top 3 NCMs (EXPORTACAO) por UF e ano (2017–2019), critério: soma do valor FOB em US$.
-- Empate: menor código NCM primeiro. UFs especiais excluídas (ver README).
WITH agg AS (
  SELECT ano, uf, ncm, sum(valor_fob_usd) AS valor_fob_usd
  FROM fato
  WHERE tipo_operacao = 'EXPORTACAO' AND ano BETWEEN 2017 AND 2019 AND uf_oficial
  GROUP BY ano, uf, ncm
)
SELECT ano, uf, ranking, ncm, valor_fob_usd FROM (
  SELECT *, row_number() OVER (PARTITION BY ano, uf ORDER BY valor_fob_usd DESC, ncm) AS ranking
  FROM agg
) WHERE ranking <= 3
ORDER BY ano, uf, ranking;
