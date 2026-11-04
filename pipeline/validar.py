"""Revalida um banco DuckDB já carregado, sem downloads nem recarga.

    python -m pipeline.validar --db data/comex.duckdb [--anos 2017 2018 2019]

Abre o banco em modo somente leitura, executa as mesmas regras de pipeline/quality.py
usadas por `python -m pipeline.run` e grava reports/qualidade.{md,json}.
"""
import argparse
import sys
from pathlib import Path

import duckdb

from .quality import salvar_relatorio, validar


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="data/comex.duckdb")
    ap.add_argument("--anos", type=int, nargs="+", default=[2017, 2018, 2019])
    ap.add_argument("--report-dir", default="reports")
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print(f"banco não encontrado: {a.db} (rode antes: python -m pipeline.run)")
        return 2
    con = duckdb.connect(a.db, read_only=True)
    rel = validar(con, anos=a.anos)
    _, md = salvar_relatorio(rel, a.report_dir)
    for c in rel["checks"]:
        print(f"[{'OK' if c['ok'] else 'FALHA'}] {c['check']}: {c['detalhe']}")
    print(f"[qualidade] {'OK' if rel['ok'] else 'FALHA'} -> {md}")
    return 0 if rel["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
