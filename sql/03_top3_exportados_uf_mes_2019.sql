-- Top 3 NCMs exportados por UF e mês em 2019, critério: soma do valor FOB em US$.
-- Empate: menor código NCM primeiro. UFs especiais excluídas (ver README).
WITH agg AS (
  SELECT mes, uf, ncm, sum(valor_fob_usd) AS valor_fob_usd
  FROM fato
  WHERE tipo_operacao = 'EXPORTACAO' AND ano = 2019 AND uf_oficial
  GROUP BY mes, uf, ncm
)
SELECT 2019 AS ano, mes, uf, ranking, ncm, valor_fob_usd FROM (
  SELECT *, row_number() OVER (PARTITION BY mes, uf ORDER BY valor_fob_usd DESC, ncm) AS ranking
  FROM agg
) WHERE ranking <= 3
ORDER BY mes, uf, ranking;
