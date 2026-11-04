"""Formatação de textos e valores para o dashboard (sem dependência do Streamlit)."""
import pandas as pd

MARINHO, PETROLEO, VERDE, FUNDO = "#10253F", "#167E91", "#85DBC4", "#F5F7FB"
TEXTO_SUAVE = "#4E5D70"  # contraste AA sobre branco e sobre o fundo
CORES_RANKING = {1: MARINHO, 2: PETROLEO, 3: VERDE}
COR_UF = PETROLEO
COR_UF_DEMAIS = "#B9D6DC"
COR_UF_ESPECIAL = "#B8C0CC"
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
         "Setembro", "Outubro", "Novembro", "Dezembro"]


def ncm_formatado(ncm: str) -> str:
    """'08012100' -> '0801.21.00' (apenas exibição; o código original é preservado)."""
    n = str(ncm).zfill(8)
    return f"{n[:4]}.{n[4:6]}.{n[6:]}"


def resumir(texto: str, limite: int = 45) -> str:
    texto = " ".join(str(texto).split())
    if len(texto) <= limite:
        return texto
    corte = texto[: limite - 1].rsplit(" ", 1)[0].rstrip(",;:- ")
    return (corte or texto[: limite - 1]) + "…"


def usd(valor: float) -> str:
    """Formato brasileiro: US$ 1.234.567."""
    return "US$ " + f"{float(valor):,.0f}".replace(",", ".")


def usd_compacto(valor: float) -> str:
    v = float(valor)
    for div, suf in ((1e9, " bi"), (1e6, " mi"), (1e3, " mil")):
        if abs(v) >= div:
            return "US$ " + f"{v / div:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + suf
    return usd(v)


def pct(valor: float) -> str:
    return f"{float(valor):.2f}".replace(".", ",") + "%"


def preparar_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Top 3 já filtrado (1 UF/período): ordena e cria rótulos curtos e completos."""
    d = df.sort_values("ranking").head(3).copy()
    d["posicao"] = d["ranking"].map(lambda r: f"{int(r)}º")
    d["ncm_fmt"] = d["ncm"].map(ncm_formatado)
    # rótulo em duas linhas (estreito, cabe no celular); descrição completa fica no hover/tabela
    d["rotulo"] = ("<b>" + d["posicao"] + " · " + d["ncm_fmt"] + "</b><br>"
                   + d["descricao_ncm"].map(lambda t: resumir(t, 32)))
    d["fob_fmt"] = d["valor_fob_usd"].map(usd)
    return d


def preparar_participacao(df: pd.DataFrame) -> pd.DataFrame:
    """Todos os estados ordenados por percentual; UF_ESPECIAL sempre ao final, separada."""
    d = df.copy()
    d["especial"] = d["uf"].eq("UF_ESPECIAL")
    d["rotulo"] = d["uf"].where(~d["especial"], "UF especial*")
    d = d.sort_values(["especial", "participacao_pct"], ascending=[True, False])
    d["pct_fmt"] = d["participacao_pct"].map(pct)
    d["fob_fmt"] = d["valor_fob_usd"].map(usd)
    return d.reset_index(drop=True)
