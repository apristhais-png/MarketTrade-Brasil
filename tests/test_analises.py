"""Testes das 5 análises com dados sintéticos (valores fictícios, não são números reais)."""
import pytest

from pipeline import analises
from pipeline.load import conectar

LINHAS = [
    # ano, mes, uf, ncm, tipo, fob  (valores fictícios)
    (2019, 1, "SP", "01010101", "EXPORTACAO", 100),
    (2019, 1, "SP", "02020202", "EXPORTACAO", 300),
    (2019, 1, "SP", "03030303", "EXPORTACAO", 200),
    (2019, 1, "SP", "04040404", "EXPORTACAO", 50),   # 4º lugar -> fora do top 3
    (2019, 2, "SP", "04040404", "EXPORTACAO", 500),  # mesmo NCM em outro mês
    (2019, 1, "MG", "00000123", "EXPORTACAO", 70),   # zeros à esquerda preservados
    (2019, 1, "MG", "00000999", "EXPORTACAO", 70),   # empate -> menor NCM primeiro
    (2019, 1, "ND", "09090909", "EXPORTACAO", 230),  # UF especial
    (2017, 5, "RS", "05050505", "EXPORTACAO", 10),
    (2016, 5, "RS", "06060606", "EXPORTACAO", 999),  # fora do período
    (2019, 3, "AM", "07070707", "IMPORTACAO", 600),
    (2019, 3, "SC", "08080808", "IMPORTACAO", 400),
    (2018, 3, "SC", "08080808", "IMPORTACAO", 40),
    (2018, 4, "SC", "08080808", "IMPORTACAO", 60),   # soma entre meses no ano
]


@pytest.fixture
def con(tmp_path):
    c = conectar(tmp_path / "a.duckdb")
    c.executemany("INSERT INTO comercio_exterior VALUES (?, ?, ?, ?, ?, ?)", LINHAS)
    return c


def rows(con, nome):
    cols, linhas = analises.executar(con, nome)
    return [dict(zip(cols, l)) for l in linhas]


def test_top3_exportados_uf_ano(con):
    r = rows(con, "01_top3_exportados_uf_ano")
    sp19 = [(x["ranking"], x["ncm"], x["valor_fob_usd"]) for x in r if x["uf"] == "SP" and x["ano"] == 2019]
    assert sp19 == [(1, "04040404", 550), (2, "02020202", 300), (3, "03030303", 200)]
    mg = [x["ncm"] for x in r if x["uf"] == "MG"]
    assert mg == ["00000123", "00000999"]
    assert {x["ano"] for x in r} == {2017, 2019}
    assert not any(x["uf"] == "ND" for x in r)


def test_top3_importados_uf_ano(con):
    r = rows(con, "02_top3_importados_uf_ano")
    assert [(x["ano"], x["uf"], x["ncm"], x["valor_fob_usd"]) for x in r] == [
        (2018, "SC", "08080808", 100), (2019, "AM", "07070707", 600), (2019, "SC", "08080808", 400)]


def test_top3_exportados_uf_mes_2019(con):
    r = rows(con, "03_top3_exportados_uf_mes_2019")
    jan_sp = [x["ncm"] for x in r if x["uf"] == "SP" and x["mes"] == 1]
    assert jan_sp == ["02020202", "03030303", "01010101"]
    assert [x["ncm"] for x in r if x["uf"] == "SP" and x["mes"] == 2] == ["04040404"]
    assert {x["ano"] for x in r} == {2019}


def test_participacao_exportacao_2019(con):
    r = {x["uf"]: x for x in rows(con, "04_participacao_uf_exportacao_2019")}
    total = 100 + 300 + 200 + 50 + 500 + 70 + 70 + 230
    assert all(x["total_nacional_fob_usd"] == total for x in r.values())
    assert r["SP"]["participacao_pct"] == pytest.approx(100 * 1150 / total, abs=1e-4)
    assert r["UF_ESPECIAL"]["valor_fob_usd"] == 230
    assert sum(x["participacao_pct"] for x in r.values()) == pytest.approx(100, abs=1e-3)


def test_participacao_importacao_2019(con):
    r = {x["uf"]: x["participacao_pct"] for x in rows(con, "05_participacao_uf_importacao_2019")}
    assert r == {"AM": pytest.approx(60.0), "SC": pytest.approx(40.0)}


def test_cli_exporta_5_csvs(con, tmp_path):
    db = tmp_path / "a.duckdb"
    con.close()
    assert analises.main(["--db", str(db), "--saida", str(tmp_path / "out")]) == 0
    arquivos = sorted(p.name for p in (tmp_path / "out").glob("*.csv"))
    assert arquivos == [f"{n}.csv" for n in analises.ANALISES]
    assert "04040404" in (tmp_path / "out/01_top3_exportados_uf_ano.csv").read_text()


def test_cli_sem_banco(tmp_path):
    assert analises.main(["--db", str(tmp_path / "nao.duckdb")]) == 1
