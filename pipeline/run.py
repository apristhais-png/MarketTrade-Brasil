"""CLI: python -m pipeline.run [--anos 2017 2018 2019] [--db data/comex.duckdb]"""
import argparse
import sys
from pathlib import Path

from . import sources
from .download import baixar
from .load import carregar_arquivo, conectar
from .quality import salvar_relatorio, validar


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Pipeline Comex Stat (MDIC) -> DuckDB")
    ap.add_argument("--anos", type=int, nargs="+", default=list(sources.ANOS))
    ap.add_argument("--db", default="data/comex.duckdb")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--report-dir", default="reports")
    ap.add_argument("--base-url", default=sources.BASE_URL)
    ap.add_argument("--forcar-download", action="store_true")
    ap.add_argument("--encoding", default="latin-1")
    a = ap.parse_args(argv)

    Path(a.db).parent.mkdir(parents=True, exist_ok=True)
    con = conectar(a.db)
    for item in sources.links(a.anos, a.base_url):
        destino = Path(a.raw_dir) / Path(item["url"]).name
        print(f"[download] {item['url']}")
        baixar(item["url"], destino, forcar=a.forcar_download)
        print(f"[carga] {carregar_arquivo(con, destino, item['ano'], item['tipo_operacao'], a.encoding)}")

    rel = validar(con, anos=a.anos)
    js, md = salvar_relatorio(rel, a.report_dir)
    print(f"[qualidade] {'OK' if rel['ok'] else 'FALHA'} -> {md}")
    return 0 if rel["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
