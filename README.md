# MarketTrade Brasil

[![tests](https://github.com/apristhais-png/MarketTrade-Brasil/actions/workflows/tests.yml/badge.svg)](https://github.com/apristhais-png/MarketTrade-Brasil/actions/workflows/tests.yml)

Projeto de Engenharia de Dados sobre as exportações e importações brasileiras de **2017 a 2019**,
por UF e produto (NCM). A fonte são os dados oficiais do
[MDIC/SECEX – Base de dados bruta](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta).

**Dashboard público:** https://markettrade-brasil-syxggiuacldn9jbkp8zdxk.streamlit.app/

**Tecnologias:** Python · DuckDB · SQL · Parquet · Streamlit · Plotly · pytest · GitHub Actions

## Arquitetura resumida

```
MDIC/SECEX (6 CSVs anuais) → download + validação → DuckDB (comercio_exterior, controle_cargas)
  → 5 consultas SQL → Parquets agregados + descrições NCM → dashboard Streamlit
```

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md): fluxo (Mermaid), granularidade, armazenamento, idempotência e decisões.
- [docs/VALIDACAO.md](docs/VALIDACAO.md): regras de qualidade, reconciliação origem × DuckDB, UFs especiais e limitações.

## Início rápido

```bash
pip install -r requirements.txt
```
```bash
pytest -q
```
```bash
streamlit run dashboard/app.py
```
O dashboard funciona direto com os Parquets versionados em `dashboard/data/`. Para refazer tudo a
partir do MDIC, veja as seções abaixo: `pipeline.run`, depois `dashboard.exportar`.

Para revalidar um banco local já carregado, sem baixar nada de novo:
```bash
python -m pipeline.validar --db data/comex.duckdb
```

**CI:** a cada push ou PR para `main`, o GitHub Actions roda `pytest -q` (Python 3.12). Entram os testes
sintéticos e a verificação dos Parquets publicados. O CI não acessa o MDIC e não precisa do banco
completo; os testes que dependem de `data/comex.duckdb` são pulados.

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
Usam CSVs minúsculos e um servidor HTTP local (sem acesso à internet). Os três níveis de teste
(sintéticos, dados publicados e banco local) estão descritos em [docs/VALIDACAO.md](docs/VALIDACAO.md).

## Análises SQL (Tarefa 2)

Consultas em `sql/`, executadas sobre a tabela `comercio_exterior` do banco gerado pelo pipeline:

| Arquivo | Análise |
|---|---|
| `01_top3_exportados_uf_ano.sql` | Top 3 NCMs exportados por UF em 2017, 2018 e 2019 |
| `02_top3_importados_uf_ano.sql` | Top 3 NCMs importados por UF em 2017, 2018 e 2019 |
| `03_top3_exportados_uf_mes_2019.sql` | Top 3 NCMs exportados por UF e mês em 2019 |
| `04_participacao_uf_exportacao_2019.sql` | % de cada UF no total nacional exportado em 2019 |
| `05_participacao_uf_importacao_2019.sql` | % de cada UF no total nacional importado em 2019 |

```bash
python -m pipeline.analises --db data/comex.duckdb --saida reports/analises
```
Gera um CSV (`;`) por análise em `reports/analises/` (não versionado).

**Critérios**
- Produto = código NCM, mantido como texto de 8 dígitos (zeros à esquerda preservados).
- Ordenação pela soma de `valor_fob_usd` (FOB em US$); em caso de empate, vence o menor NCM.
  Assim o resultado tem exatamente até 3 linhas por grupo e é determinístico.

**UFs especiais.** Os arquivos da SECEX trazem, em `SG_UF_NCM`, códigos que não são unidades
da federação (por exemplo `ND`, UF não declarada, e outros como `EX`, `ZN`, `RE`, `MN`, `CB`,
`ZZ`). A lista das 27 UFs oficiais fica em `sql/00_ufs.sql`. Tratamento:
- **Rankings (análises 1–3):** os códigos especiais ficam de fora, porque não representam um estado.
- **Participação (análises 4–5):** o denominador é o total nacional **completo**, com os códigos
  especiais incluídos, para bater com o total oficial. Eles aparecem somados em uma única linha
  `UF_ESPECIAL`, e a soma das participações dá 100%.

## Dashboard (Tarefa 3)

Dashboard Streamlit + Plotly com as 5 análises SQL, uma por aba, e filtros de UF, ano e mês na
barra lateral. Cada produto aparece com o código NCM (8 dígitos) e a descrição oficial
(`NO_NCM_POR`) da tabela NCM do MDIC (`https://balanca.mdic.gov.br/balanca/bd/tabelas/NCM.csv`).
Um NCM ausente da tabela aparece como "(descrição não encontrada na tabela NCM)", nunca com texto inventado.

### Como os dados chegam ao dashboard
O banco `data/comex.duckdb` e os CSVs anuais não vão para o GitHub. O dashboard lê só os
**resultados agregados** das 5 análises, em `dashboard/data/*.parquet`: alguns milhares de linhas,
poucos KB. Esses arquivos são gerados localmente a partir do banco real e versionados:

```bash
python -m pipeline.run
```
```bash
python -m dashboard.exportar --db data/comex.duckdb
```
```bash
git add dashboard/data/*.parquet && git commit -m "Atualiza dados do dashboard"
```
Se os arquivos não existirem ou estiverem corrompidos, o app mostra uma mensagem de erro com
o comando acima, em vez de exibir dados.

### Rodar localmente
```bash
streamlit run dashboard/app.py
```

### Publicar no Streamlit Community Cloud
1. Gere e faça commit de `dashboard/data/*.parquet` (passos acima) e envie para o GitHub.
2. Em https://share.streamlit.io, clique em **Create app** e escolha este repositório e o branch `main`.
3. Em **Main file path**, informe `dashboard/app.py`. As dependências vêm de `requirements.txt`.
4. Faça o deploy. O Cloud não baixa nenhum CSV do MDIC; ele só lê os Parquets do repositório.
