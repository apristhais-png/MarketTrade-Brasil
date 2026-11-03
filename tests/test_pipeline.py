import functools
import http.server
import threading

import pytest

from pipeline import run, sources
from pipeline.load import carregar_arquivo, conectar
from pipeline.quality import validar
from tests.conftest import HEADER_EXP, escrever


def test_links_somente_anuais():
    ls = sources.links()
    assert len(ls) == 6
    assert {l["url"].rsplit("/", 1)[1] for l in ls} == {
        f"{p}_{a}.csv" for p in ("EXP", "IMP") for a in (2017, 2018, 2019)}
    assert not any("COMPLETA" in l["url"] for l in ls)
    with pytest.raises(ValueError):
        sources.url_anual("EXP_COMPLETA", 2017)


def test_carga_e_qualidade(tmp_path, exp_2017, imp_2017):
    con = conectar(tmp_path / "t.duckdb")
    carregar_arquivo(con, exp_2017, 2017, "EXPORTACAO")
    carregar_arquivo(con, imp_2017, 2017, "IMPORTACAO")
    assert con.execute("SELECT count(*) FROM comercio_exterior").fetchone()[0] == 5
    assert con.execute("SELECT valor_fob_usd FROM comercio_exterior WHERE ncm='02013000' "
                       "AND mes=1").fetchone()[0] == 7500
    assert con.execute("SELECT count(*) FROM comercio_exterior WHERE ncm='09011000'").fetchone()[0] == 1
    rel = validar(con, anos=[2017])
    assert rel["ok"], rel
    totais = {t["tipo_operacao"]: t["valor_fob_usd"] for t in rel["totais"]}
    assert totais == {"EXPORTACAO": 8500, "IMPORTACAO": 2000}


def test_reexecucao_nao_duplica(tmp_path, exp_2017):
    con = conectar(tmp_path / "t.duckdb")
    carregar_arquivo(con, exp_2017, 2017, "EXPORTACAO")
    assert carregar_arquivo(con, exp_2017, 2017, "EXPORTACAO")["status"] == "inalterado"
    # arquivo alterado: substitui, não acumula
    escrever(exp_2017, HEADER_EXP, ['2017;05;"02013000";10;160;"SP";01;0817600;1;1;42'])
    carregar_arquivo(con, exp_2017, 2017, "EXPORTACAO")
    assert con.execute("SELECT count(*), sum(valor_fob_usd) FROM comercio_exterior").fetchone() == (1, 42)
    assert validar(con, anos=[2017])["ok"]


@pytest.mark.parametrize("linha, erro", [
    ('2017;01;"02013000";10;160;"SP";01;0817600;1;1;abc', "nulos"),
    ('2017;01;"02013000";10;160;"";01;0817600;1;1;10', "nulos"),
    ('2018;01;"02013000";10;160;"SP";01;0817600;1;1;10', "anos"),
])
def test_rejeita_dados_invalidos_sem_alterar_banco(tmp_path, exp_2017, linha, erro):
    con = conectar(tmp_path / "t.duckdb")
    carregar_arquivo(con, exp_2017, 2017, "EXPORTACAO")
    (tmp_path / "ruim").mkdir()
    ruim = escrever(tmp_path / "ruim" / "EXP_2017.csv",
                    HEADER_EXP, [linha])
    with pytest.raises(ValueError, match=erro):
        carregar_arquivo(con, ruim, 2017, "EXPORTACAO")
    assert con.execute("SELECT sum(valor_fob_usd) FROM comercio_exterior").fetchone()[0] == 8500


def test_rejeita_esquema_sem_coluna(tmp_path):
    con = conectar(tmp_path / "t.duckdb")
    f = escrever(tmp_path / "EXP_2017.csv", "CO_ANO;CO_MES;CO_NCM;VL_FOB", ['2017;1;"1";1'])
    with pytest.raises(ValueError, match="SG_UF_NCM"):
        carregar_arquivo(con, f, 2017, "EXPORTACAO")


def test_validacao_detecta_mes_e_negativo(tmp_path):
    con = conectar(tmp_path / "t.duckdb")
    con.execute("INSERT INTO comercio_exterior VALUES (2017, 13, 'SP', '12345678', 'EXPORTACAO', -1)")
    rel = validar(con, anos=[2017])
    falhas = {c["check"] for c in rel["checks"] if not c["ok"]}
    assert {"datas_mes_1_12", "valores_nao_negativos"} <= falhas


def test_cli_ponta_a_ponta_com_http_local(tmp_path, exp_2017, imp_2017):
    srv_dir = exp_2017.parent
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(srv_dir))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        args = ["--anos", "2017", "--db", str(tmp_path / "out/c.duckdb"),
                "--raw-dir", str(tmp_path / "raw"), "--report-dir", str(tmp_path / "rep"),
                "--base-url", f"http://127.0.0.1:{srv.server_port}"]
        assert run.main(args) == 0
        assert run.main(args) == 0  # reexecução
    finally:
        srv.shutdown()
    con = conectar(tmp_path / "out/c.duckdb")
    assert con.execute("SELECT count(*) FROM comercio_exterior").fetchone()[0] == 5
    assert "Status geral: **OK**" in (tmp_path / "rep/qualidade.md").read_text(encoding="utf-8")
