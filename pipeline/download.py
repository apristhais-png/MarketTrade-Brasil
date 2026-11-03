"""Download com streaming, arquivo temporário e reaproveitamento de cache local."""
from pathlib import Path

import requests


def baixar(url: str, destino: Path, forcar: bool = False, timeout: int = 120) -> Path:
    destino = Path(destino)
    if destino.exists() and destino.stat().st_size > 0 and not forcar:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.replace(destino)
    return destino
