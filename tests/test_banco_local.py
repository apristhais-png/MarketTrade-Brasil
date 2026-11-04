"""Verificações que dependem do banco completo data/comex.duckdb (não versionado).

São puladas automaticamente no CI e em qualquer máquina sem o banco.
"""
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from dashboard.dados import PASTA
from pipeline import analises
from pipeline.quality import validar

DB = Path(__file__).resolve().parent.parent / "data" / "comex.duckdb"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="data/comex.duckdb ausente (verificação local)")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


def test_qualidade_banco_completo(con):
    rel = validar(con, anos=[2017, 2018, 2019])
    assert rel["ok"], [c for c in rel["checks"] if not c["ok"]]


@pytest.mark.parametrize("nome", analises.ANALISES)
def test_parquet_publicado_igual_ao_sql(con, nome):
    cols, linhas = analises.executar(con, nome)
    sql = pd.DataFrame(linhas, columns=cols)
    pub = pd.read_parquet(PASTA / f"{nome}.parquet")[cols]
    assert len(sql) == len(pub)
    for c in cols:
        a, b = sql[c].reset_index(drop=True), pub[c].reset_index(drop=True)
        if c in ("uf", "ncm"):
            assert (a.astype(str) == b.astype(str)).all(), c
        else:  # HUGEINT/DECIMAL no DuckDB x float/int no Parquet
            assert (a.astype(float) - b.astype(float)).abs().max() <= 1e-6, c
