"""Verificações que dependem do banco completo data/comex.duckdb (não versionado).

São puladas automaticamente no CI e em qualquer máquina sem o banco.
"""
from decimal import Decimal
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
        a, b = list(sql[c]), list(pub[c])
        if c in ("uf", "ncm"):
            assert [str(x) for x in a] == [str(x) for x in b], c
        elif c == "participacao_pct":
            # única coluna com tolerância: arredondada a 4 casas no SQL (DECIMAL)
            dif = max(abs(Decimal(str(x)) - Decimal(str(y))) for x, y in zip(a, b))
            assert dif <= Decimal("0.00005"), (c, dif)
        else:
            # ano, mes, ranking, valor_fob_usd, total_nacional_fob_usd: igualdade exata em inteiros.
            # O Parquet pode guardar FOB como float64; só é aceito se for inteiro exato.
            assert [_inteiro(x) for x in a] == [_inteiro(y) for y in b], c


def _inteiro(v):
    """Converte para int sem perda; falha se o valor tiver parte fracionária."""
    d = Decimal(str(v))
    assert d == d.to_integral_value(), f"valor não inteiro: {v!r}"
    return int(d)
