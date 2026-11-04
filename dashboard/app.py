"""Dashboard MarketTrade Brasil — streamlit run dashboard/app.py"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.dados import DadosIndisponiveis, carregar, filtrar  # noqa: E402
from dashboard.formatacao import (  # noqa: E402
    COR_UF, COR_UF_DEMAIS, COR_UF_ESPECIAL, CORES_RANKING, FUNDO, MARINHO, MESES, PETROLEO,
    TEXTO_SUAVE, VERDE, ncm_formatado, pct, preparar_participacao, preparar_ranking, resumir, usd,
    usd_compacto)

UF_PADRAO, ANO_PADRAO, MES_PADRAO = "MG", 2019, 1
FONTE = "MDIC/SECEX · Comex Stat — base de dados bruta por NCM. Valores FOB em US$ correntes."
PLOTLY_CFG = {"displayModeBar": False, "responsive": True}

st.set_page_config(page_title="MarketTrade Brasil · Inteligência de Comércio Exterior",
                   page_icon="📦", layout="wide")

FONTE_UI = "Inter, 'Source Sans Pro', system-ui, sans-serif"

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Inter:wght@400;500;600;700&display=swap');
:root {{--mar:{MARINHO}; --pet:{PETROLEO}; --verde:{VERDE}; --fundo:{FUNDO}; --suave:{TEXTO_SUAVE};
  --linha:#E3E8F0;}}
html, body, [data-testid="stAppViewContainer"], .stMarkdown, button, input {{font-family:{FONTE_UI};}}
.block-container {{padding:1.4rem 1.25rem 2.5rem; max-width:1200px;}}
header[data-testid="stHeader"] {{background:transparent;}}

/* Cabeçalho */
.mt-hero {{position:relative; overflow:hidden; border-radius:20px; color:#fff; background:var(--mar);
  padding:1.9rem 2rem 1.7rem; min-height:150px;}}
.mt-hero svg {{position:absolute; right:-40px; top:-30px; height:250px; width:auto; opacity:.9;
  pointer-events:none;}}
.mt-marca {{display:flex; align-items:center; gap:.9rem; position:relative;}}
.mt-logo {{flex:0 0 auto; width:52px; height:52px; border-radius:14px; background:var(--verde);
  color:var(--mar); display:grid; place-items:center; font:700 1.25rem/1 Fraunces, Georgia, serif;
  letter-spacing:-.02em;}}
.mt-kicker {{font-size:.72rem; font-weight:600; letter-spacing:.16em; text-transform:uppercase;
  color:var(--verde);}}
.mt-hero h1 {{font:600 2.05rem/1.1 Fraunces, Georgia, serif; margin:.15rem 0 0; padding:0; color:#fff;
  letter-spacing:-.015em;}}
.mt-hero-rodape {{position:relative; display:flex; flex-wrap:wrap; gap:.5rem 1.2rem; align-items:center;
  margin-top:1.25rem; font-size:.85rem; color:#C3D0DE;}}
.mt-chip {{border:1px solid rgba(133,219,196,.45); color:#fff; border-radius:999px; padding:.28rem .8rem;
  font-weight:600; font-size:.8rem; letter-spacing:.03em; white-space:nowrap;}}
.mt-chip b {{color:var(--verde); font-weight:700;}}

/* Abas (seletores para tablist ARIA; cobre versões novas e antigas do Streamlit) */
.stTabs [role="tablist"] {{gap:.35rem; overflow-x:auto; scrollbar-width:none; background:#fff;
  border:1px solid var(--linha); border-radius:14px; padding:.35rem; margin-top:1.2rem;}}
.stTabs [role="tablist"]::-webkit-scrollbar {{display:none;}}
.stTabs .react-aria-SelectionIndicator, div[data-baseweb="tab-highlight"],
div[data-baseweb="tab-border"] {{display:none !important;}}
.stTabs [role="tab"] {{border-radius:10px; padding:.55rem .95rem; height:auto; white-space:nowrap;
  flex:0 0 auto; transition:background .15s ease;}}
.stTabs [role="tab"] p {{font-weight:600; font-size:.88rem; color:var(--suave); margin:0;}}
.stTabs [role="tab"]:hover {{background:#EEF3F7;}}
.stTabs [role="tab"][aria-selected="true"] {{background:var(--mar);}}
.stTabs [role="tab"][aria-selected="true"] p {{color:#fff;}}
.stTabs [role="tab"]:focus-visible {{outline:2px solid var(--pet); outline-offset:2px;}}

/* Seções */
.mt-secao {{margin:1.3rem 0 .6rem;}}
.mt-secao .n {{font-size:.72rem; font-weight:700; letter-spacing:.14em; color:var(--pet);
  text-transform:uppercase;}}
.mt-secao h3 {{font:600 1.5rem/1.2 Fraunces, Georgia, serif; color:var(--mar); margin:.2rem 0 .25rem;
  padding:0; letter-spacing:-.01em;}}
.mt-secao p {{color:var(--suave); font-size:.93rem; margin:0; max-width:62ch;}}
[data-testid="stWidgetLabel"] p {{font-size:.78rem; font-weight:600; letter-spacing:.05em;
  text-transform:uppercase; color:var(--suave);}}

/* Cards */
.mt-cards {{display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:.8rem;
  margin:.6rem 0 1.1rem;}}
.mt-card {{background:#fff; border:1px solid var(--linha); border-radius:16px; padding:1rem 1.1rem;
  min-width:0; animation:mtIn .35s ease both;}}
.mt-card .k {{font-size:.7rem; text-transform:uppercase; letter-spacing:.1em; color:var(--suave);
  font-weight:600;}}
.mt-card .v {{font-size:1.45rem; font-weight:700; color:var(--mar); margin-top:.35rem; line-height:1.2;
  overflow-wrap:anywhere; letter-spacing:-.01em; font-variant-numeric:tabular-nums;}}
.mt-card .s {{font-size:.82rem; color:var(--suave); margin-top:.3rem; line-height:1.4; overflow-wrap:anywhere;}}
.mt-card.destaque {{background:var(--mar); border-color:var(--mar); position:relative; overflow:hidden;}}
.mt-card.destaque::after {{content:""; position:absolute; right:-28px; top:-28px; width:90px; height:90px;
  border-radius:50%; border:14px solid rgba(133,219,196,.18);}}
.mt-card.destaque .k {{color:var(--verde);}}
.mt-card.destaque .v {{color:#fff;}}
.mt-card.destaque .s {{color:#C9D5E2;}}
@keyframes mtIn {{from {{opacity:0; transform:translateY(4px);}} to {{opacity:1; transform:none;}}}}
@media (prefers-reduced-motion: reduce) {{.mt-card, .stTabs [role="tab"] {{animation:none; transition:none;}}}}

/* Gráficos e tabelas */
[data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {{background:#fff; border:1px solid var(--linha);
  border-radius:16px; padding:.6rem .5rem;}}
.mt-rotulo {{font-size:.72rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
  color:var(--suave); margin:1rem 0 .4rem;}}
[data-testid="stExpander"] details {{border:1px solid var(--linha); border-radius:14px; background:#fff;}}
.mt-nota {{font-size:.82rem; color:var(--suave); border-left:3px solid var(--verde); padding:.2rem 0 .2rem .7rem;
  margin:.8rem 0 0;}}
.mt-rodape {{display:flex; flex-wrap:wrap; justify-content:space-between; gap:.4rem 1rem;
  border-top:1px solid var(--linha); margin-top:2.4rem; padding-top:1rem; color:var(--suave); font-size:.78rem;}}
.mt-rodape b {{color:var(--mar); font-family:Fraunces, Georgia, serif;}}

@media (max-width: 640px) {{
  .block-container {{padding:.9rem .75rem 2rem;}}
  .mt-hero {{padding:1.3rem 1.2rem 1.2rem; border-radius:16px;}}
  .mt-hero svg {{height:170px; right:-70px; top:-20px; opacity:.55;}}
  .mt-hero h1 {{font-size:1.55rem;}} .mt-logo {{width:44px; height:44px; font-size:1.05rem;}}
  .mt-secao h3 {{font-size:1.25rem;}}
  .mt-cards {{grid-template-columns:1fr 1fr; gap:.6rem;}}
  .mt-card {{padding:.8rem .85rem;}} .mt-card .v {{font-size:1.1rem;}}
  .mt-card.destaque {{grid-column:1 / -1; order:-1;}}
  .mt-cards .mt-card:last-child {{grid-column:1 / -1;}}
}}
</style>""", unsafe_allow_html=True)

# Composição abstrata (apenas formas, sem dados): rotas e órbitas sugerindo fluxo comercial.
HERO_SVG = f"""<svg viewBox="0 0 420 260" aria-hidden="true" focusable="false">
<g fill="none" stroke-linecap="round">
<circle cx="300" cy="130" r="118" stroke="{PETROLEO}" stroke-opacity=".55" stroke-width="1"/>
<circle cx="300" cy="130" r="82" stroke="{PETROLEO}" stroke-opacity=".7" stroke-width="1"/>
<circle cx="300" cy="130" r="46" stroke="{VERDE}" stroke-opacity=".5" stroke-width="1"/>
<path d="M40 210 C150 200 190 70 300 60" stroke="{VERDE}" stroke-width="2" stroke-opacity=".85"/>
<path d="M70 240 C180 230 230 120 380 110" stroke="{PETROLEO}" stroke-width="2"/>
<path d="M120 250 C210 235 250 180 360 190" stroke="{VERDE}" stroke-width="1.2" stroke-opacity=".45"
  stroke-dasharray="3 6"/>
</g>
<circle cx="300" cy="60" r="5" fill="{VERDE}"/><circle cx="380" cy="110" r="4" fill="{PETROLEO}"/>
<circle cx="360" cy="190" r="3" fill="{VERDE}" fill-opacity=".7"/>
</svg>"""

st.markdown(f"""<div class="mt-hero">{HERO_SVG}
<div class="mt-marca"><div class="mt-logo" aria-hidden="true">MT.</div>
<div><div class="mt-kicker">Inteligência de Comércio Exterior</div><h1>MarketTrade Brasil</h1></div></div>
<div class="mt-hero-rodape"><span class="mt-chip">Período <b>2017–2019</b></span>
<span>Exportações e importações por UF e produto (NCM)</span>
<span>Fonte: MDIC/SECEX · Comex Stat</span></div></div>""", unsafe_allow_html=True)


def rodape():
    st.markdown(f'<div class="mt-rodape"><span><b>MT.</b> MarketTrade Brasil</span>'
                f"<span>Fonte: {FONTE} Descrições: tabela oficial NCM/MDIC.</span></div>",
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


def secao(numero, titulo, descricao):
    st.markdown(f'<div class="mt-secao"><div class="n">Análise {numero} de 5</div>'
                f"<h3>{html.escape(titulo)}</h3><p>{html.escape(descricao)}</p></div>",
                unsafe_allow_html=True)


def rotulo(texto):
    st.markdown(f'<div class="mt-rotulo">{html.escape(texto)}</div>', unsafe_allow_html=True)


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
        font=dict(family=FONTE_UI, size=13, color=MARINHO),
        hoverlabel=dict(bgcolor=MARINHO, bordercolor=MARINHO, font=dict(color="white", size=13,
                        family=FONTE_UI), align="left"),
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
                  f"<span style='color:#4E5D70'>{html.escape(resumir(r['descricao_ncm'], 34))}</span>"))
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


def ranking(df, numero, chave, titulo, descricao, operacao, por_mes=False):
    secao(numero, titulo, descricao)
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
    rotulo("Ranking por valor FOB")
    st.plotly_chart(grafico_ranking(d), width="stretch", config=PLOTLY_CFG, key=f"{chave}_graf")
    rotulo("Descrição oficial dos produtos")
    tabela_ranking(d)
    if len(d) < 3:
        st.caption(f"Somente {len(d)} produto(s) com registro para {uf} em {periodo}.")


def participacao(df, numero, chave, titulo, descricao, operacao):
    secao(numero, titulo, descricao)
    if df.empty:
        st.warning("O arquivo desta análise não contém registros.")
        return
    d = preparar_participacao(df)
    estados, esp = d[~d["especial"]], d[d["especial"]]
    total = float(d["total_nacional_fob_usd"].iloc[0])
    lider = estados.iloc[0] if not estados.empty else None
    cards([
        (f"Total nacional {operacao} · 2019", usd_compacto(total), usd(total), False),
        ("UF com maior participação", f"{lider['uf']} · {pct(lider['participacao_pct'])}" if lider is not None else "—",
         usd(lider["valor_fob_usd"]) if lider is not None else None, True),
        ("Top 10 UFs somadas", pct(estados.head(10)["participacao_pct"].sum()), "do total nacional", False),
        ("UF especial*", pct(esp["participacao_pct"].sum()) if not esp.empty else "—",
         usd(esp["valor_fob_usd"].sum()) if not esp.empty else None, False),
    ])
    modo = st.radio("Exibição do gráfico", ["Top 10 estados", f"Todas as UFs ({len(d)})"],
                    horizontal=True, key=f"{chave}_modo")
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
    st.markdown('<p class="mt-nota"><b>*UF especial</b> agrega códigos da SECEX que não correspondem '
                "a um estado (ex.: ND – não declarada). Entra no total nacional, mas é exibida à parte.</p>",
                unsafe_allow_html=True)


abas = st.tabs(["Top 3 exportados", "Top 3 importados", "Exportação mensal",
                "Participação · exportação", "Participação · importação"])
with abas[0]:
    ranking(dados["01_top3_exportados_uf_ano"], 1, "exp", "Top 3 produtos exportados por UF",
            "Os três NCMs com maior valor FOB exportado pela UF no ano (2017–2019).", "exportados")
with abas[1]:
    ranking(dados["02_top3_importados_uf_ano"], 2, "imp", "Top 3 produtos importados por UF",
            "Os três NCMs com maior valor FOB importado pela UF no ano (2017–2019).", "importados")
with abas[2]:
    ranking(dados["03_top3_exportados_uf_mes_2019"], 3, "mes", "Top 3 exportados por UF e mês",
            "Os três NCMs com maior valor FOB exportado pela UF em cada mês de 2019.", "exportados",
            por_mes=True)
with abas[3]:
    participacao(dados["04_participacao_uf_exportacao_2019"], 4, "pexp",
                 "Participação das UFs nas exportações",
                 "Fatia de cada UF no valor FOB total exportado pelo Brasil em 2019.", "exportado")
with abas[4]:
    participacao(dados["05_participacao_uf_importacao_2019"], 5, "pimp",
                 "Participação das UFs nas importações",
                 "Fatia de cada UF no valor FOB total importado pelo Brasil em 2019.", "importado")

rodape()
