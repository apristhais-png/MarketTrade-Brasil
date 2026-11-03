import pandas as pd
import pytest

from dashboard import dados, formatacao as f

REAIS = dados.PASTA


def test_formatos():
    assert f.ncm_formatado("08012100") == "0801.21.00"
    assert f.ncm_formatado("123") == "0000.01.23"
    assert f.usd(1234567.4) == "US$ 1.234.567"
    assert f.usd_compacto(2.5e9) == "US$ 2,50 bi"
    assert f.usd_compacto(851810) == "US$ 851,81 mil"
    assert f.pct(21.999) == "22,00%"


def test_resumir():
    longo = "Outras miudezas comestíveis de bovino, congeladas, exceto línguas e fígados"
    r = f.resumir(longo, 40)
    assert len(r) <= 40 and r.endswith("…") and longo.startswith(r[:-1])
    assert f.resumir("Curto") == "Curto"


def _rank(n=4):
    return pd.DataFrame({"ranking": [3, 1, 2, 4][:n], "ncm": ["00000003", "00000001", "00000002", "4"][:n],
                         "descricao_ncm": ["C fictício", "A " + "x" * 80, "B fictício", "D"][:n],
                         "valor_fob_usd": [10.0, 30.0, 20.0, 5.0][:n]})


def test_preparar_ranking_tres_barras_ordenadas_sem_alterar_dados():
    d = f.preparar_ranking(_rank())
    assert list(d.ranking) == [1, 2, 3]
    assert list(d.valor_fob_usd) == [30.0, 20.0, 10.0]
    assert d.iloc[0].rotulo.startswith("<b>1º · 0000.00.01</b><br>A") and d.iloc[0].rotulo.endswith("…")
    assert d.iloc[0].descricao_ncm == "A " + "x" * 80  # descrição completa preservada
    assert list(d.ncm) == ["00000001", "00000002", "00000003"]


def test_preparar_participacao_uf_especial_ao_final():
    df = pd.DataFrame({"uf": ["UF_ESPECIAL", "MG", "SP"], "valor_fob_usd": [5.0, 25.0, 70.0],
                       "total_nacional_fob_usd": [100.0] * 3, "participacao_pct": [5.0, 25.0, 70.0]})
    d = f.preparar_participacao(df)
    assert list(d.uf) == ["SP", "MG", "UF_ESPECIAL"]
    assert list(d.especial) == [False, False, True]


@pytest.mark.skipif(not (REAIS / "04_participacao_uf_exportacao_2019.parquet").exists(),
                    reason="Parquets reais ausentes")
def test_app_com_dados_reais_padroes(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(dados.carregar, "__defaults__", (REAIS,))
    st.cache_data.clear()
    at = AppTest.from_file("../dashboard/app.py", default_timeout=60).run()
    assert not at.exception
    valores = [s.value for s in at.selectbox]
    assert valores == ["MG", 2019, "MG", 2019, "MG", 1]
    # participação: todos os estados + UF especial, independentemente dos rankings
    part = f.preparar_participacao(dados.carregar(REAIS)["04_participacao_uf_exportacao_2019"])
    assert len(part) == 28 and part.iloc[-1].uf == "UF_ESPECIAL"
    assert part.participacao_pct.sum() == pytest.approx(100, abs=0.01)
