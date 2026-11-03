"""Dashboard MarketTrade Brasil — streamlit run dashboard/app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.dados import DadosIndisponiveis, carregar, filtrar  # noqa: E402
from dashboard.formatacao import (  # noqa: E402
    COR_UF, COR_UF_ESPECIAL, CORES_RANKING, MESES, pct, preparar_participacao,
    preparar_ranking, usd, usd_compacto)

UF_PADRAO, ANO_PADRAO, MES_PADRAO = "MG", 2019, 1
FONTE = ("Fonte: MDIC/SECEX — Comex Stat (base de dados bruta por NCM). "
         "Valores FOB em US$ correntes.")

st.set_page_config(page_title="MarketTrade Brasil", page_icon="📦", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
h1 {font-size: 1.9rem !important;} h3 {margin-top: .4rem;}
[data-testid="stMetricValue"] {font-size: 1.4rem;}
</style>""", unsafe_allow_html=True)

st.title("MarketTrade Brasil")
st.markdown("##### Comércio exterior brasileiro por Unidade da Federação · 2017–2019")
st.caption(FONTE)


@st.cache_data
def _dados():
    return carregar()


try:
    dados = _dados()
except DadosIndisponiveis as e:
    st.error(f"Dados do dashboard indisponíveis. {e}")
    st.stop()


def _indice(opcoes, padrao):
    return opcoes.index(padrao) if padrao in opcoes else 0


def grafico_ranking(d):
    fig = go.Figure(go.Bar(
        x=d["valor_fob_usd"], y=d["rotulo"], orientation="h",
        marker_color=[CORES_RANKING[int(r)] for r in d["ranking"]],
        text=[usd_compacto(v) for v in d["valor_fob_usd"]], textposition="outside",
        cliponaxis=False,
        customdata=list(zip(d["posicao"], d["ncm_fmt"], d["descricao_ncm"], d["fob_fmt"])),
        hovertemplate="<b>%{customdata[0]} · NCM %{customdata[1]}</b><br>%{customdata[2]}"
                      "<br>FOB: %{customdata[3]}<extra></extra>"))
    fig.update_layout(
        height=300, margin=dict(l=0, r=80, t=10, b=10), showlegend=False,
        yaxis=dict(autorange="reversed", title=None, automargin=True),
        xaxis=dict(title="Valor FOB (US$)", showticklabels=False, showgrid=False, zeroline=True),
        plot_bgcolor="white", font=dict(size=13))
    return fig


def tabela_ranking(d):
    st.dataframe(
        d[["posicao", "ncm", "descricao_ncm", "fob_fmt"]], hide_index=True, width="stretch",
        column_config={
            "posicao": st.column_config.TextColumn("Posição", width="small"),
            "ncm": st.column_config.TextColumn("NCM", width="small"),
            "descricao_ncm": st.column_config.TextColumn("Descrição oficial NCM", width="large"),
            "valor_fob_usd": st.column_config.NumberColumn("Valor FOB (US$)", format="localized"),
        })


def ranking(df, chave, titulo, por_mes=False):
    st.subheader(titulo)
    ufs = sorted(df["uf"].unique())
    c1, c2 = st.columns(2)
    uf = c1.selectbox("UF", ufs, index=_indice(ufs, UF_PADRAO), key=f"{chave}_uf")
    if por_mes:
        meses = sorted(int(m) for m in df["mes"].unique())
        mes = c2.selectbox("Mês (2019)", meses, index=_indice(meses, MES_PADRAO),
                           format_func=lambda m: MESES[m - 1], key=f"{chave}_mes")
        sel, periodo = filtrar(df, ufs=[uf], meses=[mes]), f"{MESES[mes - 1].lower()} de 2019"
    else:
        anos = sorted(int(a) for a in df["ano"].unique())
        ano = c2.selectbox("Ano", anos, index=_indice(anos, ANO_PADRAO), key=f"{chave}_ano")
        sel, periodo = filtrar(df, ufs=[uf], anos=[ano]), str(ano)
    if sel.empty:
        st.info(f"Sem registros para {uf} em {periodo}.")
        return
    d = preparar_ranking(sel)
    st.caption(f"{uf} · {periodo} · 3 produtos (NCM) de maior valor FOB")
    st.plotly_chart(grafico_ranking(d), width="stretch", config={"displayModeBar": False},
                    key=f"{chave}_graf")
    tabela_ranking(d)


def participacao(df, titulo, rotulo):
    st.subheader(titulo)
    d = preparar_participacao(df)
    estados = d[~d["especial"]]
    esp = d[d["especial"]]
    total = float(d["total_nacional_fob_usd"].iloc[0])
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Total nacional {rotulo} (2019)", usd_compacto(total), help=usd(total))
    if not estados.empty:
        lider = estados.iloc[0]
        c2.metric("Maior participação", f"{lider['uf']} · {pct(lider['participacao_pct'])}")
    c3.metric("UF especial*", pct(esp["participacao_pct"].sum()) if not esp.empty else "—")

    fig = go.Figure(go.Bar(
        x=d["participacao_pct"], y=d["rotulo"], orientation="h",
        marker_color=[COR_UF_ESPECIAL if e else COR_UF for e in d["especial"]],
        text=d["pct_fmt"], textposition="outside", cliponaxis=False,
        customdata=list(zip(d["rotulo"], d["pct_fmt"], d["fob_fmt"])),
        hovertemplate="<b>%{customdata[0]}</b><br>Participação: %{customdata[1]}"
                      "<br>FOB: %{customdata[2]}<extra></extra>"))
    fig.update_layout(
        height=max(420, 24 * len(d)), margin=dict(l=0, r=60, t=10, b=10), showlegend=False,
        yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=12)),
        xaxis=dict(title="Participação no total nacional (%)", showticklabels=False,
                   showgrid=False),
        plot_bgcolor="white", font=dict(size=13))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"{rotulo}_part")
    with st.expander("Tabela completa"):
        st.dataframe(
            d[["rotulo", "fob_fmt", "pct_fmt"]], hide_index=True, width="stretch",
            column_config={
                "rotulo": "UF",
                "fob_fmt": st.column_config.TextColumn("Valor FOB (US$)"),
                "pct_fmt": st.column_config.TextColumn("Participação"),
            })
    st.caption("*UF especial agrega códigos da SECEX que não correspondem a um estado "
               "(ex.: ND – não declarada). Entra no total nacional, mas é exibida à parte.")


abas = st.tabs(["1 · Top 3 exportados", "2 · Top 3 importados", "3 · Exportados por mês (2019)",
                "4 · Participação nas exportações", "5 · Participação nas importações"])
with abas[0]:
    ranking(dados["01_top3_exportados_uf_ano"], "exp",
            "Top 3 produtos exportados por UF (2017–2019)")
with abas[1]:
    ranking(dados["02_top3_importados_uf_ano"], "imp",
            "Top 3 produtos importados por UF (2017–2019)")
with abas[2]:
    ranking(dados["03_top3_exportados_uf_mes_2019"], "mes",
            "Top 3 produtos exportados por UF e mês (2019)", por_mes=True)
with abas[3]:
    participacao(dados["04_participacao_uf_exportacao_2019"],
                 "Participação de cada UF no total exportado (2019)", "exportado")
with abas[4]:
    participacao(dados["05_participacao_uf_importacao_2019"],
                 "Participação de cada UF no total importado (2019)", "importado")

st.divider()
st.caption(FONTE + " Produtos identificados pelo código NCM e descrição oficial (tabela NCM/MDIC).")
