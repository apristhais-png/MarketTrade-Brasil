# Validação e qualidade dos dados

Há três níveis de verificação, com escopos diferentes:

| Nível | Onde roda | Depende de | Arquivos |
|---|---|---|---|
| **1. Testes sintéticos** | CI e local | nada (CSVs/bancos minúsculos criados no teste) | `tests/test_pipeline.py`, `test_analises.py`, `test_dashboard.py`, `test_formatacao.py`, `test_validar_cli.py` |
| **2. Dados publicados** | CI e local | `dashboard/data/*.parquet` versionados | `tests/test_parquets_publicados.py` |
| **3. Banco completo** | só local | `data/comex.duckdb` (não versionado) | `tests/test_banco_local.py` (pulado se o banco não existir) e `python -m pipeline.validar` |

Os testes sintéticos usam valores fictícios. Eles verificam a lógica do código, não os números oficiais.

## Regras aplicadas na carga (`pipeline/load.py`)
Se qualquer regra falhar, a carga do arquivo é interrompida com `ROLLBACK`:
- presença das colunas `CO_ANO`, `CO_MES`, `CO_NCM`, `SG_UF_NCM` e `VL_FOB`;
- nenhum nulo, UF vazia ou valor não numérico em ano, mês, UF, NCM e FOB (`TRY_CAST` + contagem);
- todas as linhas do arquivo pertencem ao ano esperado (por exemplo, `EXP_2018.csv` só pode ter 2018);
- o NCM é normalizado para 8 dígitos com zeros à esquerda.

## Regras do relatório de qualidade (`pipeline/quality.py`)
Geradas por `python -m pipeline.run` ou `python -m pipeline.validar` em `reports/qualidade.md` e `.json`:

| Check | Regra |
|---|---|
| `esquema` | colunas e tipos da tabela `comercio_exterior` |
| `nulos` | nenhuma coluna nula |
| `datas_mes_1_12` | mês entre 1 e 12 |
| `datas_ano_esperado` | todo `(ano, operação)` no banco tem arquivo de origem registrado em `controle_cargas` |
| `anos_solicitados_carregados` | os anos pedidos em `--anos` foram carregados |
| `valores_nao_negativos` | FOB ≥ 0 |
| `ncm_8_digitos` | NCM com exatamente 8 dígitos |
| `uf_valida` | UF entre as 27 oficiais ou os códigos especiais conhecidos |
| `tipo_operacao` | apenas `EXPORTACAO` / `IMPORTACAO` |
| `sem_duplicidade` | nenhuma chave `(ano, mes, uf, ncm, tipo_operacao)` repetida |
| `totais_origem_vs_destino` | reconciliação, descrita abaixo |

## Reconciliação origem × DuckDB
Durante a carga, a soma de `VL_FOB` de **todas as linhas do CSV** é gravada em
`controle_cargas.total_fob_origem`, junto com o número de linhas lidas. Depois, o check
`totais_origem_vs_destino` compara esse valor com `sum(valor_fob_usd)` da tabela `comercio_exterior` para
o mesmo `(ano, tipo_operacao)`. Como a agregação apenas soma, os dois totais precisam ser idênticos: qualquer
linha perdida ou duplicada aparece como divergência.

## Dados processados e publicados
- O processamento completo dos 6 arquivos (2017–2019) foi executado **localmente** pela autora, e o
  relatório terminou com **`[qualidade] OK`**. O banco e o relatório não são versionados. Para repetir
  a verificação sem novo download:
  ```bash
  python -m pipeline.validar --db data/comex.duckdb
  ```
  Com o banco presente, `pytest -q` também executa `tests/test_banco_local.py`. Esse teste refaz o
  relatório e confere se cada Parquet publicado é igual ao resultado da consulta SQL correspondente.
- Os Parquets reais publicados em `dashboard/data/` têm:

  | Arquivo | Linhas |
  |---|---|
  | `01_top3_exportados_uf_ano.parquet` | 243 (27 UFs × 3 anos × 3 posições) |
  | `02_top3_importados_uf_ano.parquet` | 243 (27 UFs × 3 anos × 3 posições) |
  | `03_top3_exportados_uf_mes_2019.parquet` | 972 (27 UFs × 12 meses × 3 posições) |
  | `04_participacao_uf_exportacao_2019.parquet` | 28 (27 UFs + `UF_ESPECIAL`) |
  | `05_participacao_uf_importacao_2019.parquet` | 28 (27 UFs + `UF_ESPECIAL`) |

## Verificações dos Parquets publicados (CI)
`tests/test_parquets_publicados.py` roda a cada push ou PR para `main` e confere:
- a quantidade de linhas acima, as colunas esperadas, a ausência de nulos e FOB > 0;
- NCM com 8 dígitos e descrição preenchida;
- nos rankings: somente as 27 UFs oficiais, posições exatamente 1, 2 e 3 por grupo, valores decrescentes,
  desempate pelo menor NCM e nenhum NCM ou posição repetidos no grupo;
- anos 2017–2019 nas análises 1 e 2, e 2019 com os meses 1–12 na análise 3;
- nas participações: 27 UFs + `UF_ESPECIAL` sem repetição, total nacional único e igual à soma das linhas,
  cada percentual igual a `100 × valor / total` dentro do arredondamento de 4 casas e soma próxima de
  100%, com tolerância de 28 × 0,00005.

Esses testes provam a **coerência interna** dos resultados publicados. Eles não provam que os números são
iguais aos do MDIC. Essa garantia vem da reconciliação origem × DuckDB, que roda localmente (nível 3).

## Tratamento de UFs especiais
`SG_UF_NCM` traz, além das 27 UFs, códigos da SECEX que não são estados (por exemplo `ND`, não
declarada; a lista aceita está em `pipeline/quality.py`). Esses registros são **mantidos** no banco.
- **Rankings (análises 1–3):** ficam de fora, porque não representam uma UF.
- **Participações (análises 4–5):** entram no total nacional, para que o denominador seja o total
  oficial, e aparecem somados em uma única linha `UF_ESPECIAL`. Assim as linhas somam 100%.

## Limitações
- O CI não acessa o MDIC e não tem o banco completo. A reconciliação com a origem depende de execução
  local (nível 3).
- O relatório local `[qualidade] OK` não fica versionado. A evidência no repositório são os Parquets e
  os testes de integridade sobre eles.
- A lista de códigos especiais aceitos foi definida no projeto. Um código novo da SECEX faria o check
  `uf_valida` falhar e exigiria revisão manual.
- `participacao_pct` é arredondada a 4 casas no SQL, por isso a soma pode diferir de 100% por poucos
  décimos de milésimo.
- A descrição NCM usa a tabela vigente na data da exportação. Um NCM ausente dessa tabela aparece como
  "descrição não encontrada".
