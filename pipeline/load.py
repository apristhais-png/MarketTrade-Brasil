"""Leitura eficiente (DuckDB read_csv, só as colunas necessárias) e carga idempotente."""
import hashlib
from pathlib import Path

import duckdb

COLUNAS_OBRIGATORIAS = ["CO_ANO", "CO_MES", "CO_NCM", "SG_UF_NCM", "VL_FOB"]

DDL = """
CREATE TABLE IF NOT EXISTS comercio_exterior (
    ano            SMALLINT     NOT NULL,
    mes            TINYINT      NOT NULL,
    uf             VARCHAR      NOT NULL,
    ncm            VARCHAR(8)   NOT NULL,
    tipo_operacao  VARCHAR      NOT NULL,
    valor_fob_usd  HUGEINT      NOT NULL,
    PRIMARY KEY (ano, mes, uf, ncm, tipo_operacao)
);
CREATE TABLE IF NOT EXISTS controle_cargas (
    arquivo        VARCHAR PRIMARY KEY,
    ano            SMALLINT NOT NULL,
    tipo_operacao  VARCHAR  NOT NULL,
    sha256         VARCHAR  NOT NULL,
    linhas_origem  BIGINT   NOT NULL,
    total_fob_origem HUGEINT NOT NULL,
    carregado_em   TIMESTAMP DEFAULT current_timestamp
);
"""


def conectar(caminho_db) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(caminho_db))
    con.execute(DDL)
    return con


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _rel(caminho: Path, encoding: str) -> str:
    p = str(caminho).replace("'", "''")
    return (
        f"read_csv('{p}', delim=';', header=true, quote='\"', encoding='{encoding}', "
        "all_varchar=true)"
    )


def colunas_arquivo(con, caminho: Path, encoding: str = "latin-1") -> list[str]:
    return [d[0] for d in con.execute(f"SELECT * FROM {_rel(caminho, encoding)} LIMIT 0").description]


def carregar_arquivo(con, caminho: Path, ano: int, tipo_operacao: str,
                     encoding: str = "latin-1") -> dict:
    """Substitui atomicamente os dados de (ano, tipo_operacao). Reexecutar não duplica."""
    caminho = Path(caminho)
    faltando = set(COLUNAS_OBRIGATORIAS) - set(colunas_arquivo(con, caminho, encoding))
    if faltando:
        raise ValueError(f"{caminho.name}: colunas ausentes {sorted(faltando)}")

    digest = sha256(caminho)
    ja = con.execute("SELECT sha256 FROM controle_cargas WHERE arquivo = ?",
                     [caminho.name]).fetchone()
    if ja and ja[0] == digest:
        return {"arquivo": caminho.name, "status": "inalterado"}

    rel = _rel(caminho, encoding)
    staging = f"""
        SELECT TRY_CAST(CO_ANO AS SMALLINT) AS ano,
               TRY_CAST(CO_MES AS TINYINT)  AS mes,
               UPPER(TRIM(SG_UF_NCM))       AS uf,
               LPAD(TRIM(CO_NCM), 8, '0')   AS ncm,
               TRY_CAST(VL_FOB AS HUGEINT)  AS valor_fob_usd
        FROM {rel}
    """
    con.execute("BEGIN")
    try:
        con.execute(f"CREATE OR REPLACE TEMP TABLE stg AS {staging}")
        linhas, total = con.execute(
            "SELECT count(*), coalesce(sum(valor_fob_usd), 0) FROM stg").fetchone()
        invalidas = con.execute(
            "SELECT count(*) FROM stg WHERE ano IS NULL OR mes IS NULL OR uf IS NULL "
            "OR uf = '' OR ncm IS NULL OR valor_fob_usd IS NULL").fetchone()[0]
        if invalidas:
            raise ValueError(f"{caminho.name}: {invalidas} linhas com nulos/valores não numéricos")
        anos = [r[0] for r in con.execute("SELECT DISTINCT ano FROM stg").fetchall()]
        if anos != [ano]:
            raise ValueError(f"{caminho.name}: anos encontrados {anos}, esperado {ano}")

        con.execute("DELETE FROM comercio_exterior WHERE ano = ? AND tipo_operacao = ?",
                    [ano, tipo_operacao])
        con.execute("""
            INSERT INTO comercio_exterior
            SELECT ano, mes, uf, ncm, ?, sum(valor_fob_usd)
            FROM stg GROUP BY ano, mes, uf, ncm
        """, [tipo_operacao])
        con.execute("DELETE FROM controle_cargas WHERE arquivo = ?", [caminho.name])
        con.execute(
            "INSERT INTO controle_cargas (arquivo, ano, tipo_operacao, sha256, linhas_origem, "
            "total_fob_origem) VALUES (?, ?, ?, ?, ?, ?)",
            [caminho.name, ano, tipo_operacao, digest, linhas, total])
        con.execute("DROP TABLE stg")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return {"arquivo": caminho.name, "status": "carregado", "linhas": linhas}
