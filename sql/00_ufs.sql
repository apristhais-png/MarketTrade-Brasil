-- Classificação das UFs. Os códigos especiais da SECEX (UF não declarada, exterior, zona
-- não declarada, reexportação, consumo de bordo etc.) não são unidades da federação.
CREATE OR REPLACE TEMP VIEW uf_ref AS
SELECT * FROM (VALUES
  ('AC'),('AL'),('AP'),('AM'),('BA'),('CE'),('DF'),('ES'),('GO'),('MA'),('MT'),('MS'),('MG'),
  ('PA'),('PB'),('PR'),('PE'),('PI'),('RJ'),('RN'),('RS'),('RO'),('RR'),('SC'),('SP'),('SE'),('TO')
) t(uf);

CREATE OR REPLACE TEMP VIEW fato AS
SELECT c.*, (c.uf IN (SELECT uf FROM uf_ref)) AS uf_oficial
FROM comercio_exterior c;
