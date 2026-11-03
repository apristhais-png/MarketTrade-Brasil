"""Executa as 5 análises SQL (pasta sql/) no banco DuckDB e exporta CSVs.

python -m pipeline.analises [--db data/comex.duckdb] [--saida reports/analises]
"""
import argparse
import sys
from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
ANALISES = [
    "01_top3_exportados_uf_ano",
    "02_top3_importados_uf_ano",
    "03_top3_exportados_uf_mes_2019",
    "04_participacao_uf_exportacao_2019",
    "05_participacao_uf_importacao_2019",
]


def preparar(con) -> None:
    con.execute((SQL_DIR / "00_ufs.sql").read_text(encoding="utf-8"))


def executar(con, nome: str):
    """Retorna (colunas, linhas) da análise."""
    preparar(con)
    rel = con.execute((SQL_DIR / f"{nome}.sql").read_text(encoding="utf-8"))
    return [d[0] for d in rel.description], rel.fetchall()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="data/comex.duckdb")
    ap.add_argument("--saida", default="reports/analises")
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print(f"banco não encontrado: {a.db} (rode antes: python -m pipeline.run)")
        return 1
    con = duckdb.connect(a.db, read_only=True)
    preparar(con)
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    for nome in ANALISES:
        destino = (saida / f"{nome}.csv").as_posix().replace("'", "''")
        sql = (SQL_DIR / f"{nome}.sql").read_text(encoding="utf-8").strip().rstrip(";")
        con.execute(f"COPY ({sql}) TO '{destino}' (HEADER, DELIMITER ';')")
        print(f"[analise] {nome} -> {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
