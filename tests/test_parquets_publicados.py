"""Integridade dos Parquets REAIS versionados em dashboard/data/ (rodam no CI).

Não acessam o MDIC nem dependem de data/comex.duckdb: verificam apenas a coerência interna
dos resultados publicados com as regras das consultas em sql/.
"""
import pandas as pd
import pytest

from dashboard.dados import COLUNAS, PASTA
from pipeline.analises import ANALISES

UFS_OFICIAIS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
                "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}
LINHAS_ESPERADAS = dict(zip(ANALISES, [243, 243, 972, 28, 28]))
RANKINGS = {"01_top3_exportados_uf_ano": ["ano", "uf"],
            "02_top3_importados_uf_ano": ["ano", "uf"],
            "03_top3_exportados_uf_mes_2019": ["ano", "mes", "uf"]}
PARTICIPACOES = ["04_participacao_uf_exportacao_2019", "05_participacao_uf_importacao_2019"]


@pytest.fixture(scope="module")
def pq():
    return {n: pd.read_parquet(PASTA / f"{n}.parquet") for n in ANALISES}


def test_arquivos_e_quantidade_de_linhas(pq):
    assert {n: len(df) for n, df in pq.items()} == LINHAS_ESPERADAS


@pytest.mark.parametrize("nome", ANALISES)
def test_colunas_e_sem_nulos(pq, nome):
    df = pq[nome]
    assert set(df.columns) == COLUNAS[nome] - ({"descricao_ncm"} if nome in PARTICIPACOES else set())
    assert not df.isna().any().any()
    assert (df["valor_fob_usd"] > 0).all()


@pytest.mark.parametrize("nome", RANKINGS)
def test_rankings(pq, nome):
    df, chave = pq[nome], RANKINGS[nome]
    assert df["ncm"].str.fullmatch(r"\d{8}").all()
    assert (df["descricao_ncm"].str.strip() != "").all()
    assert set(df["uf"]) == UFS_OFICIAIS  # UFs especiais excluídas dos rankings
    assert not df.duplicated(chave + ["ranking"]).any()
    assert not df.duplicated(chave + ["ncm"]).any()
    for _, g in df.groupby(chave):
        g = g.sort_values("ranking")
        assert list(g["ranking"]) == [1, 2, 3]
        assert g["valor_fob_usd"].is_monotonic_decreasing
        # empate de valor: menor NCM primeiro (regra do SQL)
        for (_, a), (_, b) in zip(g.iloc[:-1].iterrows(), g.iloc[1:].iterrows()):
            if a.valor_fob_usd == b.valor_fob_usd:
                assert a.ncm < b.ncm


def test_periodos(pq):
    for n in ("01_top3_exportados_uf_ano", "02_top3_importados_uf_ano"):
        assert set(pq[n]["ano"]) == {2017, 2018, 2019}
    mes = pq["03_top3_exportados_uf_mes_2019"]
    assert set(mes["ano"]) == {2019}
    assert set(mes["mes"]) == set(range(1, 13))


@pytest.mark.parametrize("nome", PARTICIPACOES)
def test_participacoes_2019(pq, nome):
    df = pq[nome]
    assert set(df["uf"]) == UFS_OFICIAIS | {"UF_ESPECIAL"}
    assert not df["uf"].duplicated().any()
    assert df["total_nacional_fob_usd"].nunique() == 1
    total = df["total_nacional_fob_usd"].iloc[0]
    assert df["valor_fob_usd"].sum() == pytest.approx(total, rel=1e-12)
    # participacao_pct é arredondada a 4 casas no SQL
    calc = 100 * df["valor_fob_usd"] / total
    assert ((df["participacao_pct"] - calc).abs() <= 0.00005 + 1e-9).all()
    # 28 arredondamentos de até 0,00005 cada
    assert df["participacao_pct"].sum() == pytest.approx(100, abs=28 * 0.00005)
