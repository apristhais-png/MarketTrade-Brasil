"""Dashboard MarketTrade Brasil — streamlit run dashboard/app.py"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.dados import DadosIndisponiveis, carregar, filtrar  # noqa: E402
from dashboard.formatacao import (  # noqa: E402
    AZUL, COR_UF, COR_UF_DEMAIS, COR_UF_ESPECIAL, CORES_RANKING, MARINHO, MESES, PETROLEO,
    VERDE, ncm_formatado, pct, preparar_participacao, preparar_ranking, resumir, usd,
    usd_compacto)

UF_PADRAO, ANO_PADRAO, MES_PADRAO = "MG", 2019, 1
FONTE = "MDIC/SECEX · Comex Stat — base de dados bruta por NCM. Valores FOB em US$ correntes."
PLOTLY_CFG = {"displayModeBar": False, "responsive": True}

st.set_page_config(page_title="MarketTrade Brasil · Inteligência de Comércio Exterior",
                   page_icon="📦", layout="wide")

st.markdown(f"""<style>
.block-container {{padding: 1.6rem 1.25rem 2.5rem; max-width: 1180px;}}
header[data-testid="stHeader"] {{background: transparent;}}
.mt-header {{display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap;
  gap:.75rem; padding:1.4rem 1.6rem; border-radius:14px; color:#fff;
  background:linear-gradient(120deg, {MARINHO} 0%, {PETROLEO} 70%, {AZUL} 140%);}}
.mt-header h1 {{font-size:1.7rem; font-weight:700; margin:0; padding:0; color:#fff; letter-spacing:-.01em;}}
.mt-header p {{margin:.15rem 0 0; color:#C9D8E8; font-size:.95rem;}}
.mt-badge {{font-size:.78rem; font-weight:600; letter-spacing:.04em; padding:.3rem .7rem;
  border-radius:999px; background:rgba(255,255,255,.12); color:#fff; white-space:nowrap;}}
.mt-badge b {{color:#7FD6A8;}}
.mt-fonte {{color:#5B6B80; font-size:.8rem; margin:.55rem 0 1.1rem;}}
.mt-secao h3 {{font-size:1.2rem; font-weight:700; color:{MARINHO}; margin:.6rem 0 .1rem; padding:0;}}
.mt-secao p {{color:#5B6B80; font-size:.9rem; margin:0 0 .8rem;}}
.mt-cards {{display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:.75rem;
  margin:.4rem 0 1rem;}}
.mt-card {{background:#fff; border:1px solid #E4EAF2; border-radius:12px; padding:.85rem 1rem; min-width:0;}}
.mt-card .k {{font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:#6B7A8F; font-weight:600;}}
.mt-card .v {{font-size:1.25rem; font-weight:700; color:{MARINHO}; margin-top:.2rem; line-height:1.25;
  overflow-wrap:anywhere;}}
.mt-card .s {{font-size:.8rem; color:#5B6B80; margin-top:.15rem; overflow-wrap:anywhere;}}
.mt-card.destaque {{border-left:3px solid {VERDE};}}
.mt-rodape {{border-top:1px solid #E4EAF2; margin-top:2rem; padding-top:.8rem; color:#7A8799; font-size:.78rem;}}
div[data-baseweb="tab-list"] {{gap:.25rem; overflow-x:auto;}}
button[data-baseweb="tab"] p {{font-weight:600;}}
[data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {{background:#fff; border:1px solid #E4EAF2;
  border-radius:12px; padding:.4rem;}}
@media (max-width: 640px) {{
  .block-container {{padding: 1rem .75rem 2rem;}}
  .mt-header {{padding:1.1rem 1.1rem;}} .mt-header h1 {{font-size:1.35rem;}}
  .mt-cards {{grid-template-columns:1fr 1fr;}} .mt-card .v {{font-size:1.05rem;}}
}}
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="mt-header"><div><h1>MarketTrade Brasil</h1>
<p>Inteligência de Comércio Exterior</p></div>
<span class="mt-badge">PERÍODO <b>2017–2019</b></span></div>""", unsafe_allow_html=True)
st.markdown(f'<div class="mt-fonte">Fonte: {FONTE}</div>', unsafe_allow_html=True)


def rodape():
    st.markdown(f'<div class="mt-rodape">MarketTrade Brasil · Fonte: {FONTE} '
                "Produtos identificados pelo código NCM e descrição oficial (tabela NCM/MDIC).</div>",
                unsafe_allow_html=True)


@st.cache_data
def _dados():
    return carregar()


try:
    dados = _dados()
except DadosIndisponiveis as e:
    st.error(f"**Não foi possível carregar os dados do dashboard.**\n\n{e}")
    rodape()
    st.stop()


def secao(titulo, descricao):
    st.markdown(f'<div class="mt-secao"><h3>{html.escape(titulo)}</h3>'
                f"<p>{html.escape(descricao)}</p></div>", unsafe_allow_html=True)


def cards(itens):
    """itens: (rótulo, valor, subtítulo, destaque). Todos os textos são escapados."""
    blocos = "".join(
        f'<div class="mt-card{" destaque" if d else ""}"><div class="k">{html.escape(k)}</div>'
        f'<div class="v">{html.escape(v)}</div>'
        + (f'<div class="s">{html.escape(s)}</div>' if s else "") + "</div>"
        for k, v, s, d in itens)
    st.markdown(f'<div class="mt-cards">{blocos}</div>', unsafe_allow_html=True)


def _indice(opcoes, padrao):
    return opcoes.index(padrao) if padrao in opcoes else 0


def _layout(fig, altura, margem_dir):
    fig.update_layout(
        height=altura, margin=dict(l=0, r=margem_dir, t=8, b=8), showlegend=False,
        plot_bgcolor="white", paper_bgcolor="white", bargap=0.38,
        font=dict(family="Source Sans Pro, sans-serif", size=13, color=MARINHO),
        hoverlabel=dict(bgcolor="white", bordercolor="#E4EAF2", font_size=13, align="left"),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(autorange="reversed", title=None, automargin=True, fixedrange=True,
                   ticklabelstandoff=8))
    return fig


def grafico_ranking(d):
    """Rótulo (posição, NCM e nome) acima de cada barra: a barra usa a largura toda,
    inclusive no celular, sem espremer nem cortar texto."""
    ys = list(range(len(d)))
    fig = go.Figure(go.Bar(
        x=d["valor_fob_usd"], y=ys, orientation="h", width=0.42,
        marker=dict(color=[CORES_RANKING[int(r)] for r in d["ranking"]], cornerradius=6),
        text=[f"<b>{usd_compacto(v)}</b>" for v in d["valor_fob_usd"]], textposition="outside",
        textfont=dict(size=14, color=MARINHO), cliponaxis=False,
        customdata=list(zip(d["posicao"], d["ncm_fmt"], d["descricao_ncm"], d["fob_fmt"])),
        hovertemplate="<b>%{customdata[0]} · NCM %{customdata[1]}</b><br>%{customdata[2]}"
                      "<br>Valor FOB: <b>%{customdata[3]}</b><extra></extra>"))
    for y, (_, r) in zip(ys, d.iterrows()):
        fig.add_annotation(
            x=0, y=y, xref="x", yref="y", yshift=22, xanchor="left", yanchor="bottom",
            showarrow=False, align="left", font=dict(size=13, color=MARINHO),
            text=(f"<b>{r['posicao']} · NCM {r['ncm_fmt']}</b><br>"
                  f"<span style='color:#5B6B80'>{html.escape(resumir(r['descricao_ncm'], 34))}</span>"))
    _layout(fig, 400, 90)
    fig.update_layout(margin=dict(l=4, r=90, t=50, b=4))
    fig.update_yaxes(showticklabels=False, range=[len(d) - 0.5, -0.9])
    return fig


def tabela_ranking(d):
    st.dataframe(
        d[["posicao", "ncm_fmt", "descricao_ncm", "fob_fmt"]], hide_index=True, width="stretch",
        column_config={
            "posicao": st.column_config.TextColumn("Posição", width="small"),
            "ncm_fmt": st.column_config.TextColumn("NCM", width="small"),
            "descricao_ncm": st.column_config.TextColumn("Descrição oficial do produto (NCM)",
                                                         width="large"),
            "fob_fmt": st.column_config.TextColumn("Valor FOB (US$)", width="medium"),
        })


def ranking(df, chave, titulo, descricao, operacao, por_mes=False):
    secao(titulo, descricao)
    if df.empty:
        st.warning("O arquivo desta análise não contém registros.")
        return
    ufs = sorted(df["uf"].unique())
    c1, c2 = st.columns(2)
    uf = c1.selectbox("Unidade da Federação", ufs, index=_indice(ufs, UF_PADRAO), key=f"{chave}_uf")
    if por_mes:
        meses = sorted(int(m) for m in df["mes"].unique())
        mes = c2.selectbox("Mês de 2019", meses, index=_indice(meses, MES_PADRAO),
                           format_func=lambda m: MESES[m - 1], key=f"{chave}_mes")
        sel, periodo = filtrar(df, ufs=[uf], meses=[mes]), f"{MESES[mes - 1]}/2019"
    else:
        anos = sorted(int(a) for a in df["ano"].unique())
        ano = c2.selectbox("Ano", anos, index=_indice(anos, ANO_PADRAO), key=f"{chave}_ano")
        sel, periodo = filtrar(df, ufs=[uf], anos=[ano]), str(ano)
    if sel.empty:
        st.info(f"Não há produtos {operacao} registrados para {uf} em {periodo} nos dados do MDIC.")
        return
    d = preparar_ranking(sel)
    lider = d.iloc[0]
    cards([
        ("UF selecionada", uf, None, False),
        ("Período", periodo, None, False),
        ("Produto líder", f"NCM {ncm_formatado(lider['ncm'])}", resumir(lider["descricao_ncm"], 60), True),
        ("Valor FOB do líder", usd_compacto(lider["valor_fob_usd"]), usd(lider["valor_fob_usd"]), False),
    ])
    st.plotly_chart(grafico_ranking(d), width="stretch", config=PLOTLY_CFG, key=f"{chave}_graf")
    tabela_ranking(d)
    if len(d) < 3:
        st.caption(f"Somente {len(d)} produto(s) com registro para {uf} em {periodo}.")


def participacao(df, chave, titulo, descricao, rotulo):
    secao(titulo, descricao)
    if df.empty:
        st.warning("O arquivo desta análise não contém registros.")
        return
    d = preparar_participacao(df)
    estados, esp = d[~d["especial"]], d[d["especial"]]
    total = float(d["total_nacional_fob_usd"].iloc[0])
    lider = estados.iloc[0] if not estados.empty else None
    cards([
        (f"Total nacional {rotulo} · 2019", usd_compacto(total), usd(total), False),
        ("UF com maior participação", f"{lider['uf']} · {pct(lider['participacao_pct'])}" if lider is not None else "—",
         usd(lider["valor_fob_usd"]) if lider is not None else None, True),
        ("Top 10 UFs somadas", pct(estados.head(10)["participacao_pct"].sum()), "do total nacional", False),
        ("UF especial*", pct(esp["participacao_pct"].sum()) if not esp.empty else "—",
         usd(esp["valor_fob_usd"].sum()) if not esp.empty else None, False),
    ])
    modo = st.radio("Exibição", ["Top 10 estados", f"Todas as UFs ({len(d)})"], horizontal=True,
                    key=f"{chave}_modo", label_visibility="collapsed")
    g = estados.head(10) if modo.startswith("Top") else d
    cores = [COR_UF_ESPECIAL if e else (COR_UF if i < 10 else COR_UF_DEMAIS)
             for i, e in enumerate(g["especial"])]
    fig = go.Figure(go.Bar(
        x=g["participacao_pct"], y=g["rotulo"], orientation="h",
        marker=dict(color=cores, cornerradius=4),
        text=[f"<b>{p}</b>" for p in g["pct_fmt"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=MARINHO),
        customdata=list(zip(g["rotulo"], g["pct_fmt"], g["fob_fmt"])),
        hovertemplate="<b>%{customdata[0]}</b><br>Participação: %{customdata[1]}"
                      "<br>Valor FOB: %{customdata[2]}<extra></extra>"))
    _layout(fig, max(320, 30 * len(g) + 30), 70)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CFG, key=f"{chave}_graf")
    with st.expander(f"Tabela completa · {len(estados)} estados + UF especial", expanded=False):
        t = d.assign(posicao=[f"{i + 1}º" if not e else "—" for i, e in enumerate(d["especial"])])
        st.dataframe(
            t[["posicao", "rotulo", "fob_fmt", "pct_fmt"]], hide_index=True, width="stretch",
            height=min(38 + 35 * len(t), 1050),
            column_config={
                "posicao": st.column_config.TextColumn("Posição", width="small"),
                "rotulo": st.column_config.TextColumn("UF", width="small"),
                "fob_fmt": st.column_config.TextColumn("Valor FOB (US$)"),
                "pct_fmt": st.column_config.TextColumn("Participação no total nacional"),
            })
    st.caption("*UF especial agrega códigos da SECEX que não correspondem a um estado "
               "(ex.: ND – não declarada). Entra no total nacional, mas é exibida à parte.")


abas = st.tabs(["Exportações · Top 3", "Importações · Top 3", "Exportações mensais",
                "Participação · Exportação", "Participação · Importação"])
with abas[0]:
    ranking(dados["01_top3_exportados_uf_ano"], "exp", "Top 3 produtos exportados por UF",
            "Os três NCMs com maior valor FOB exportado pela UF no ano (2017–2019).", "exportados")
with abas[1]:
    ranking(dados["02_top3_importados_uf_ano"], "imp", "Top 3 produtos importados por UF",
            "Os três NCMs com maior valor FOB importado pela UF no ano (2017–2019).", "importados")
with abas[2]:
    ranking(dados["03_top3_exportados_uf_mes_2019"], "mes", "Top 3 exportados por UF e mês",
            "Os três NCMs com maior valor FOB exportado pela UF em cada mês de 2019.", "exportados",
            por_mes=True)
with abas[3]:
    participacao(dados["04_participacao_uf_exportacao_2019"], "pexp",
                 "Participação das UFs nas exportações",
                 "Fatia de cada UF no valor FOB total exportado pelo Brasil em 2019.", "exportado")
with abas[4]:
    participacao(dados["05_participacao_uf_importacao_2019"], "pimp",
                 "Participação das UFs nas importações",
                 "Fatia de cada UF no valor FOB total importado pelo Brasil em 2019.", "importado")

rodape()
