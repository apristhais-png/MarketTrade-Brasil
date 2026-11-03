"""Leitura e filtragem dos resultados publicados (sem dependência do Streamlit)."""
from pathlib import Path

import pandas as pd

from pipeline.analises import ANALISES

PASTA = Path(__file__).resolve().parent / "data"

COLUNAS = {
    "01_top3_exportados_uf_ano": {"ano", "uf", "ranking", "ncm", "valor_fob_usd", "descricao_ncm"},
    "02_top3_importados_uf_ano": {"ano", "uf", "ranking", "ncm", "valor_fob_usd", "descricao_ncm"},
    "03_top3_exportados_uf_mes_2019": {"ano", "mes", "uf", "ranking", "ncm", "valor_fob_usd",
                                       "descricao_ncm"},
    "04_participacao_uf_exportacao_2019": {"uf", "valor_fob_usd", "total_nacional_fob_usd",
                                           "participacao_pct"},
    "05_participacao_uf_importacao_2019": {"uf", "valor_fob_usd", "total_nacional_fob_usd",
                                           "participacao_pct"},
}


class DadosIndisponiveis(Exception):
    pass


def carregar(pasta: Path = PASTA) -> dict[str, pd.DataFrame]:
    pasta = Path(pasta)
    faltando = [n for n in ANALISES if not (pasta / f"{n}.parquet").exists()]
    if faltando:
        raise DadosIndisponiveis(
            f"Arquivos ausentes em {pasta}: {', '.join(f + '.parquet' for f in faltando)}. "
            "Gere-os com: python -m dashboard.exportar --db data/comex.duckdb")
    dfs = {}
    for nome in ANALISES:
        try:
            df = pd.read_parquet(pasta / f"{nome}.parquet")
        except Exception as e:  # arquivo corrompido etc.
            raise DadosIndisponiveis(f"Falha ao ler {nome}.parquet: {e}") from e
        ausentes = COLUNAS[nome] - set(df.columns)
        if ausentes:
            raise DadosIndisponiveis(f"{nome}.parquet sem colunas {sorted(ausentes)}")
        if "ncm" in df.columns:
            df["ncm"] = df["ncm"].astype(str).str.zfill(8)
            df["descricao_ncm"] = df["descricao_ncm"].fillna("(descrição não encontrada na tabela NCM)")
            df["produto"] = df["ncm"] + " – " + df["descricao_ncm"]
        dfs[nome] = df
    return dfs


def filtrar(df: pd.DataFrame, ufs=None, anos=None, meses=None) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    if ufs:
        m &= df["uf"].isin(ufs)
    if anos and "ano" in df.columns:
        m &= df["ano"].isin(anos)
    if meses and "mes" in df.columns:
        m &= df["mes"].isin(meses)
    return df[m]
