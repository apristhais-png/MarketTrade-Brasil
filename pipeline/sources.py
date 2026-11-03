"""Links anuais oficiais (MDIC / Comex Stat - base de dados bruta, detalhada por NCM).

Página de origem:
https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta

Somente os arquivos anuais EXP_<ano>.csv / IMP_<ano>.csv são usados; a base
histórica completa (EXP_COMPLETA / IMP_COMPLETA) nunca é baixada.
"""

BASE_URL = "https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ncm"
ANOS = (2017, 2018, 2019)
TIPOS = {"EXP": "EXPORTACAO", "IMP": "IMPORTACAO"}


def url_anual(prefixo: str, ano: int, base_url: str = BASE_URL) -> str:
    if prefixo not in TIPOS:
        raise ValueError(f"prefixo inválido: {prefixo}")
    if "COMPLETA" in prefixo.upper():
        raise ValueError("a base histórica completa não deve ser usada")
    return f"{base_url}/{prefixo}_{ano}.csv"


def links(anos=ANOS, base_url: str = BASE_URL) -> list[dict]:
    return [
        {"ano": a, "prefixo": p, "tipo_operacao": t, "url": url_anual(p, a, base_url)}
        for a in anos
        for p, t in TIPOS.items()
    ]
