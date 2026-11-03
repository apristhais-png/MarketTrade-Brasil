"""Gera os arquivos leves que o dashboard publica (dashboard/data/*.parquet).

Roda localmente, onde existe o banco completo data/comex.duckdb:

    python -m dashboard.exportar --db data/comex.duckdb

1. Executa as 5 análises SQL existentes (sql/01..05) no banco.
2. Baixa a tabela oficial de NCM (arquivo pequeno) e anexa a descrição oficial (NO_NCM_POR).
3. Grava um Parquet por análise. São só alguns milhares de linhas: dá para versionar no
   GitHub e publicar no Streamlit Cloud sem baixar os CSVs anuais.
"""
import argparse
import sys
from pathlib import Path

import duckdb

from pipeline import analises
from pipeline.download import baixar

NCM_URL = "https://balanca.mdic.gov.br/balanca/bd/tabelas/NCM.csv"
SAIDA = Path(__file__).resolve().parent / "data"


def _ler_ncm(p: str, encoding: str) -> str:
    # A tabela NCM oficial tem aspas internas não escapadas (ex.: 'de 45" ...').
    # strict_mode=false aceita essas linhas; ignore_errors=false garante que nenhuma
    # linha seja descartada silenciosamente (qualquer outro erro continua falhando).
    return (f"read_csv('{p}', delim=';', header=true, quote='\"', encoding='{encoding}', "
            "all_varchar=true, strict_mode=false, ignore_errors=false)")


def carregar_ncm(con, caminho_csv: Path, encoding: str = "latin-1") -> None:
    p = str(caminho_csv).replace("'", "''")
    cols = [d[0] for d in con.execute(
        f"SELECT * FROM {_ler_ncm(p, encoding)} LIMIT 0").description]
    faltando = {"CO_NCM", "NO_NCM_POR"} - set(cols)
    if faltando:
        raise ValueError(f"tabela NCM sem colunas {sorted(faltando)}")
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE ncm_desc AS
        SELECT LPAD(TRIM(CO_NCM), 8, '0') AS ncm, min(TRIM(NO_NCM_POR)) AS descricao_ncm
        FROM {_ler_ncm(p, encoding)}
        GROUP BY 1
    """)  # uma descrição por NCM: o LEFT JOIN não duplica produtos


def exportar(con, saida: Path = SAIDA) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    analises.preparar(con)
    tamanhos = {}
    for nome in analises.ANALISES:
        sql = (analises.SQL_DIR / f"{nome}.sql").read_text(encoding="utf-8").strip().rstrip(";")
        com_desc = "ncm" in [d[0] for d in con.execute(f"SELECT * FROM ({sql}) LIMIT 0").description]
        if com_desc:
            # preserva a ordem original da análise após o JOIN
            sql = (f"SELECT * EXCLUDE (_ordem) FROM (SELECT r.*, d.descricao_ncm FROM "
                   f"(SELECT *, row_number() OVER () AS _ordem FROM ({sql})) r "
                   "LEFT JOIN ncm_desc d USING (ncm)) ORDER BY _ordem")
        destino = (saida / f"{nome}.parquet").as_posix().replace("'", "''")
        con.execute(f"COPY ({sql}) TO '{destino}' (FORMAT parquet)")
        tamanhos[nome] = con.execute(f"SELECT count(*) FROM '{destino}'").fetchone()[0]
    return tamanhos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="data/comex.duckdb")
    ap.add_argument("--ncm-csv", default="data/raw/NCM.csv")
    ap.add_argument("--ncm-url", default=NCM_URL)
    ap.add_argument("--saida", default=str(SAIDA))
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print(f"banco não encontrado: {a.db} (rode antes: python -m pipeline.run)")
        return 1
    baixar(a.ncm_url, Path(a.ncm_csv))
    con = duckdb.connect(a.db, read_only=True)
    carregar_ncm(con, Path(a.ncm_csv))
    for nome, n in exportar(con, Path(a.saida)).items():
        print(f"[exportar] {nome}: {n} linhas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
