"""Dashboard MarketTrade Brasil — streamlit run dashboard/app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.dados import DadosIndisponiveis, carregar, filtrar  # noqa: E402

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

st.set_page_config(page_title="MarketTrade Brasil", layout="wide")
st.title("MarketTrade Brasil — Comércio exterior por UF")
st.caption("Fonte: MDIC/SECEX (Comex Stat), valores FOB em US$. Produtos identificados por NCM.")


@st.cache_data
def _dados():
    return carregar()


try:
    dados = _dados()
except DadosIndisponiveis as e:
    st.error(f"Dados do dashboard indisponíveis. {e}")
    st.stop()

ufs_todas = sorted(set(dados["01_top3_exportados_uf_ano"]["uf"])
                   | set(dados["02_top3_importados_uf_ano"]["uf"]))
anos_todos = sorted(set(dados["01_top3_exportados_uf_ano"]["ano"])
                    | set(dados["02_top3_importados_uf_ano"]["ano"]))

with st.sidebar:
    st.header("Filtros")
    ufs = st.multiselect("UF", ufs_todas, default=ufs_todas[:5])
    anos = st.multiselect("Ano (análises 1 e 2)", anos_todos, default=anos_todos)
    meses = st.multiselect("Mês de 2019 (análise 3)", list(range(1, 13)),
                           default=list(range(1, 13)), format_func=lambda m: MESES[m - 1])


def fmt(df):
    return df.drop(columns=["produto"], errors="ignore").rename(columns={
        "valor_fob_usd": "FOB (US$)", "descricao_ncm": "Descrição NCM",
        "participacao_pct": "Participação (%)", "total_nacional_fob_usd": "Total nacional (US$)"})


def top3(df, titulo_facet):
    if df.empty:
        st.info("Nenhum dado para os filtros selecionados.")
        return
    fig = px.bar(df, x="valor_fob_usd", y="uf", color="produto", orientation="h",
                 facet_col=titulo_facet, facet_col_wrap=3, barmode="group",
                 hover_data={"ncm": True, "ranking": True, "produto": False},
                 labels={"valor_fob_usd": "FOB (US$)", "uf": "UF", "produto": "Produto (NCM)"},
                 height=max(400, 60 * df["uf"].nunique() * (1 + df[titulo_facet].nunique() // 3)))
    fig.update_layout(legend=dict(orientation="h", y=-0.15), margin=dict(l=0, r=0))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(fmt(df), width="stretch", hide_index=True)


def participacao(df, rotulo):
    total = df["total_nacional_fob_usd"].iloc[0] if not df.empty else 0
    st.metric(f"Total nacional {rotulo} 2019 (US$)", f"{total:,.0f}".replace(",", "."))
    sel = filtrar(df, ufs=ufs + ["UF_ESPECIAL"] if ufs else None)
    if sel.empty:
        st.info("Nenhum dado para os filtros selecionados.")
        return
    fig = px.bar(sel.sort_values("participacao_pct"), x="participacao_pct", y="uf",
                 orientation="h", text="participacao_pct",
                 labels={"participacao_pct": "Participação (%)", "uf": "UF"})
    fig.update_traces(texttemplate="%{text:.2f}%")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(fmt(sel), width="stretch", hide_index=True)
    st.caption("UF_ESPECIAL agrega códigos da SECEX que não são UFs (ex.: ND); entram no total.")


abas = st.tabs(["1. Top 3 exportados", "2. Top 3 importados", "3. Exportados por mês (2019)",
                "4. Participação exportação", "5. Participação importação"])
with abas[0]:
    top3(filtrar(dados["01_top3_exportados_uf_ano"], ufs, anos), "ano")
with abas[1]:
    top3(filtrar(dados["02_top3_importados_uf_ano"], ufs, anos), "ano")
with abas[2]:
    top3(filtrar(dados["03_top3_exportados_uf_mes_2019"], ufs, meses=meses), "mes")
with abas[3]:
    participacao(dados["04_participacao_uf_exportacao_2019"], "exportado")
with abas[4]:
    participacao(dados["05_participacao_uf_importacao_2019"], "importado")
