from pipeline import validar
from pipeline.load import carregar_arquivo, conectar


def test_validar_banco_existente_sem_download(tmp_path, exp_2017):
    db = tmp_path / "c.duckdb"
    con = conectar(db)
    carregar_arquivo(con, exp_2017, 2017, "EXPORTACAO")
    con.close()
    assert validar.main(["--db", str(db), "--anos", "2017", "--report-dir", str(tmp_path / "r")]) == 0
    assert "Status geral: **OK**" in (tmp_path / "r/qualidade.md").read_text(encoding="utf-8")


def test_validar_banco_ausente(tmp_path):
    assert validar.main(["--db", str(tmp_path / "x.duckdb")]) == 2
