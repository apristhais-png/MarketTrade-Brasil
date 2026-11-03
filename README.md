# MarketTrade Brasil

Projeto de Engenharia de Dados para análise das importações
e exportações brasileiras de 2017 a 2019.

Tecnologias: Python, DuckDB, SQL e Streamlit.

Fonte: dados oficiais do comércio exterior brasileiro
([MDIC – Base de dados bruta](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta)).

## Pipeline (Python + DuckDB)

### Fontes usadas
Apenas os arquivos **anuais** detalhados por NCM (a base histórica `*_COMPLETA` nunca é baixada):

| Ano | Exportação | Importação |
|---|---|---|
| 2017 | `.../ncm/EXP_2017.csv` | `.../ncm/IMP_2017.csv` |
| 2018 | `.../ncm/EXP_2018.csv` | `.../ncm/IMP_2018.csv` |
| 2019 | `.../ncm/EXP_2019.csv` | `.../ncm/IMP_2019.csv` |

Base: `https://balanca.mdic.gov.br/balanca/bd/comexstat-bd/ncm` (configurável com `--base-url`,
definida em `pipeline/sources.py`). Formato: CSV separado por `;`, cabeçalho, encoding latin-1
(configurável com `--encoding`).

### Tabela gerada: `comercio_exterior`
| Coluna | Origem | Tipo |
|---|---|---|
| ano | CO_ANO | SMALLINT |
| mes | CO_MES | TINYINT |
| uf | SG_UF_NCM | VARCHAR |
| ncm | CO_NCM (8 dígitos, zeros à esquerda) | VARCHAR |
| tipo_operacao | EXPORTACAO / IMPORTACAO | VARCHAR |
| valor_fob_usd | soma de VL_FOB | HUGEINT |

Chave primária: `(ano, mes, uf, ncm, tipo_operacao)` — os valores são agregados nessa granularidade
(país, via, URF etc. não fazem parte do escopo). A tabela `controle_cargas` registra o hash SHA-256,
nº de linhas e total FOB de cada arquivo de origem.

### Executar
```bash
pip install -r requirements.txt
```
```bash
python -m pipeline.run                      # 2017–2019
```
```bash
python -m pipeline.run --anos 2019 --db data/comex.duckdb
```
Saídas (não versionadas, ver `.gitignore`): CSVs em `data/raw/`, banco em `data/comex.duckdb`,
relatório em `reports/qualidade.md` e `reports/qualidade.json`. O código de saída é `1` se algum
check de qualidade falhar.

### Reexecução sem duplicidade
- Download reaproveita arquivo já existente (use `--forcar-download` para baixar de novo).
- Arquivo com o mesmo SHA-256 já carregado é ignorado.
- Arquivo alterado substitui os dados do seu `(ano, tipo_operacao)` dentro de uma transação
  (DELETE + INSERT); em caso de erro há ROLLBACK e o banco fica intacto.

### Validações (relatório de qualidade)
Na carga: colunas obrigatórias presentes, nenhum nulo/valor não numérico, ano do arquivo = ano esperado.
Após a carga: esquema da tabela, nulos, mês 1–12, anos (todo período no banco precisa ter arquivo de origem registrado em `controle_cargas` e os anos pedidos em `--anos` precisam estar carregados — outros períodos já presentes no banco não geram falha), FOB não negativo, NCM com 8 dígitos,
UF válida, tipo de operação, ausência de chaves duplicadas e **total FOB de origem = total no DuckDB**
por arquivo, além dos totais por ano/operação.

### Testes
```bash
python -m pytest -q
```
Usam CSVs minúsculos e um servidor HTTP local (sem acesso à internet).
