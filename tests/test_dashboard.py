"""Testes do dashboard com dados sintéticos (valores e descrições fictícios)."""
import pandas as pd
import pytest

from dashboard import dados, exportar
from pipeline.analises import ANALISES
from pipeline.load import conectar

LINHAS = [
    (2019, 1, "SP", "01010101", "EXPORTACAO", 300),
    (2019, 1, "SP", "00000123", "EXPORTACAO", 100),
    (2019, 1, "ND", "02020202", "EXPORTACAO", 100),
    (2018, 2, "RJ", "01010101", "EXPORTACAO", 50),
    (2019, 3, "AM", "03030303", "IMPORTACAO", 80),
]


@pytest.fixture
def publicado(tmp_path):
    con = conectar(tmp_path / "c.duckdb")
    con.executemany("INSERT INTO comercio_exterior VALUES (?, ?, ?, ?, ?, ?)", LINHAS)
    ncm = tmp_path / "NCM.csv"
    ncm.write_text("CO_NCM;CO_UNID;NO_NCM_POR\n"
                   '"01010101";10;"Produto fictício A"\n"00000123";10;"Produto fictício B"\n',
                   encoding="latin-1")
    exportar.carregar_ncm(con, ncm)
    saida = tmp_path / "pub"
    exportar.exportar(con, saida)
    return saida


def test_exportar_gera_5_parquets_com_descricao(publicado):
    assert sorted(p.stem for p in publicado.glob("*.parquet")) == sorted(ANALISES)
    df = pd.read_parquet(publicado / "01_top3_exportados_uf_ano.parquet")
    sp = df[(df.uf == "SP") & (df.ano == 2019)]
    assert list(sp.ncm) == ["01010101", "00000123"]
    assert list(sp.descricao_ncm) == ["Produto fictício A", "Produto fictício B"]


def test_carregar_preserva_ncm_e_marca_sem_descricao(publicado):
    d = dados.carregar(publicado)
    imp = d["02_top3_importados_uf_ano"]
    assert imp.iloc[0].ncm == "03030303"
    assert "não encontrada" in imp.iloc[0].descricao_ncm
    assert d["01_top3_exportados_uf_ano"].produto.str.startswith("0").all()


def test_participacao_vem_do_banco(publicado):
    p = dados.carregar(publicado)["04_participacao_uf_exportacao_2019"].set_index("uf")
    assert p.loc["SP", "participacao_pct"] == pytest.approx(80.0)
    assert p.loc["UF_ESPECIAL", "participacao_pct"] == pytest.approx(20.0)


def test_filtrar(publicado):
    df = dados.carregar(publicado)["01_top3_exportados_uf_ano"]
    assert set(dados.filtrar(df, ufs=["RJ"]).ano) == {2018}
    assert dados.filtrar(df, anos=[2017]).empty
    assert len(dados.filtrar(df)) == len(df)


def test_erros_de_dados(tmp_path, publicado):
    with pytest.raises(dados.DadosIndisponiveis, match="dashboard.exportar"):
        dados.carregar(tmp_path / "vazio")
    (publicado / "04_participacao_uf_exportacao_2019.parquet").write_bytes(b"lixo")
    with pytest.raises(dados.DadosIndisponiveis, match="Falha ao ler"):
        dados.carregar(publicado)


def test_ncm_sem_coluna_descricao(tmp_path):
    con = conectar(tmp_path / "c.duckdb")
    f = tmp_path / "NCM.csv"
    f.write_text("CO_NCM;X\n1;2\n")
    with pytest.raises(ValueError, match="NO_NCM_POR"):
        exportar.carregar_ncm(con, f)


def _app(monkeypatch, pasta):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    st.cache_data.clear()
    monkeypatch.setattr(dados, "PASTA", pasta)
    monkeypatch.setattr(dados.carregar, "__defaults__", (pasta,))
    return AppTest.from_file("../dashboard/app.py", default_timeout=60).run()


def test_app_renderiza_5_abas(monkeypatch, publicado):
    at = _app(monkeypatch, publicado)
    assert not at.exception
    assert len(at.tabs) == 5
    # rankings: seletores simples de UF e ano/mês (3 abas x 2 selectbox)
    assert len(at.selectbox) == 6


def test_app_sem_dados_mostra_erro(monkeypatch, tmp_path):
    at = _app(monkeypatch, tmp_path / "vazio")
    assert not at.exception
    assert "Não foi possível carregar os dados" in at.error[0].value
    assert "dashboard.exportar" in at.error[0].value


def test_ncm_com_aspas_internas_nao_escapadas(tmp_path):
    con = conectar(tmp_path / "c.duckdb")
    con.executemany("INSERT INTO comercio_exterior VALUES (?, ?, ?, ?, ?, ?)", [
        (2019, 1, "SP", "84713012", "EXPORTACAO", 500),
        (2019, 1, "SP", "01010101", "EXPORTACAO", 300),
        (2019, 1, "SP", "00000123", "EXPORTACAO", 100),
    ])
    linhas = ["CO_NCM;CO_UNID;NO_NCM_POR"]
    linhas += [f'"{i:08d}";10;"Produto fictício {i}"' for i in range(1000, 6100)]  # > linha 5043
    linhas += ['"84713012";11;"Monitor fictício de 45" polegadas, tela plana"',
               '"01010101";10;"Produto fictício A"',
               '"00000123";10;"Produto fictício B"',
               '"00000123";10;"Produto fictício B"']  # linha repetida na tabela
    f = tmp_path / "NCM.csv"
    f.write_text("\n".join(linhas) + "\n", encoding="latin-1")

    exportar.carregar_ncm(con, f)
    # nenhuma linha descartada: 5100 + 3 NCMs distintos
    assert con.execute("SELECT count(*) FROM ncm_desc").fetchone()[0] == 5103
    assert con.execute("SELECT descricao_ncm FROM ncm_desc WHERE ncm = '84713012'").fetchone()[0] \
        == 'Monitor fictício de 45" polegadas, tela plana'

    exportar.exportar(con, tmp_path / "pub")
    df = pd.read_parquet(tmp_path / "pub" / "01_top3_exportados_uf_ano.parquet")
    assert list(df.ncm) == ["84713012", "01010101", "00000123"]  # sem duplicar, ordem mantida
    assert list(df.descricao_ncm) == ['Monitor fictício de 45" polegadas, tela plana',
                                      "Produto fictício A", "Produto fictício B"]
