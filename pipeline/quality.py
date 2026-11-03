"""Validações de qualidade sobre a tabela carregada e geração de relatório."""
import json
from pathlib import Path

UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
       "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
       # códigos especiais usados pela SECEX
       "ND", "EX", "ZN", "RE", "MN", "CB", "ZZ"}

ESQUEMA = {"ano": "SMALLINT", "mes": "TINYINT", "uf": "VARCHAR", "ncm": "VARCHAR",
           "tipo_operacao": "VARCHAR", "valor_fob_usd": "HUGEINT"}


def _um(con, sql, params=None):
    return con.execute(sql, params or []).fetchone()[0]


def validar(con, anos=None) -> dict:
    checks = []

    def add(nome, ok, detalhe):
        checks.append({"check": nome, "ok": bool(ok), "detalhe": detalhe})

    tipos = {r[0]: r[1].split("(")[0] for r in con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'comercio_exterior'").fetchall()}
    add("esquema", tipos == ESQUEMA, tipos)

    nulos = _um(con, "SELECT count(*) FROM comercio_exterior WHERE " +
                " OR ".join(f"{c} IS NULL" for c in ESQUEMA))
    add("nulos", nulos == 0, f"{nulos} linhas com nulos")

    meses = _um(con, "SELECT count(*) FROM comercio_exterior WHERE mes NOT BETWEEN 1 AND 12")
    add("datas_mes_1_12", meses == 0, f"{meses} linhas com mês inválido")

    if anos:
        fora = _um(con, f"SELECT count(*) FROM comercio_exterior WHERE ano NOT IN "
                        f"({','.join(map(str, anos))})")
        add("datas_ano_esperado", fora == 0, f"{fora} linhas fora de {list(anos)}")

    neg = _um(con, "SELECT count(*) FROM comercio_exterior WHERE valor_fob_usd < 0")
    add("valores_nao_negativos", neg == 0, f"{neg} linhas com FOB negativo")

    ncm = _um(con, "SELECT count(*) FROM comercio_exterior WHERE NOT regexp_full_match(ncm, '[0-9]{8}')")
    add("ncm_8_digitos", ncm == 0, f"{ncm} NCMs fora do padrão")

    ufs = [r[0] for r in con.execute("SELECT DISTINCT uf FROM comercio_exterior").fetchall()]
    invalidas = sorted(set(ufs) - UFS)
    add("uf_valida", not invalidas, f"UFs desconhecidas: {invalidas}")

    op = [r[0] for r in con.execute("SELECT DISTINCT tipo_operacao FROM comercio_exterior").fetchall()]
    add("tipo_operacao", set(op) <= {"EXPORTACAO", "IMPORTACAO"}, sorted(op))

    dup = _um(con, "SELECT count(*) FROM (SELECT 1 FROM comercio_exterior GROUP BY "
                   "ano, mes, uf, ncm, tipo_operacao HAVING count(*) > 1)")
    add("sem_duplicidade", dup == 0, f"{dup} chaves duplicadas")

    divergencias = con.execute("""
        SELECT c.arquivo, c.total_fob_origem, coalesce(t.total, 0) AS total
        FROM controle_cargas c
        LEFT JOIN (SELECT ano, tipo_operacao, sum(valor_fob_usd) AS total
                   FROM comercio_exterior GROUP BY ALL) t USING (ano, tipo_operacao)
        WHERE c.total_fob_origem <> coalesce(t.total, 0)
    """).fetchall()
    add("totais_origem_vs_destino", not divergencias,
        [{"arquivo": a, "origem": int(o), "destino": int(d)} for a, o, d in divergencias])

    totais = [
        {"ano": a, "tipo_operacao": t, "linhas": int(n), "valor_fob_usd": int(v)}
        for a, t, n, v in con.execute(
            "SELECT ano, tipo_operacao, count(*), sum(valor_fob_usd) FROM comercio_exterior "
            "GROUP BY ALL ORDER BY 1, 2").fetchall()
    ]
    return {"ok": all(c["ok"] for c in checks), "checks": checks, "totais": totais}


def salvar_relatorio(rel: dict, pasta: Path) -> tuple[Path, Path]:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    js = pasta / "qualidade.json"
    js.write_text(json.dumps(rel, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md = pasta / "qualidade.md"
    linhas = ["# Relatório de qualidade", "", f"Status geral: **{'OK' if rel['ok'] else 'FALHA'}**",
              "", "| Check | OK | Detalhe |", "|---|---|---|"]
    linhas += [f"| {c['check']} | {'✅' if c['ok'] else '❌'} | {c['detalhe']} |" for c in rel["checks"]]
    linhas += ["", "## Totais", "", "| Ano | Operação | Linhas | FOB (US$) |", "|---|---|---|---|"]
    linhas += [f"| {t['ano']} | {t['tipo_operacao']} | {t['linhas']:,} | {t['valor_fob_usd']:,} |"
               for t in rel["totais"]]
    md.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return js, md
