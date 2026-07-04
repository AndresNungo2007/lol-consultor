"""Cache genérico en disco con expiración por TTL.

Distinto del cache por versión de parche de Data Dragon (ese vive en
connectors/ddragon.py porque su invalidación natural es "cambió el parche",
no un TTL de tiempo). Este lo usan las fuentes que cambian de forma
independiente del parche (wiki, estadísticas de op.gg).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


class TTLCache:
    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{safe_key}.json"

    def get_or_set(self, key: str, ttl_seconds: int, fetch_fn: Callable[[], Any]) -> Any:
        """Devuelve el valor cacheado si no expiró; si no, llama a fetch_fn y cachea."""
        path = self._path(key)
        if path.exists():
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
                if time.time() - envelope["fetched_at"] < ttl_seconds:
                    return envelope["data"]
            except (json.JSONDecodeError, KeyError):
                pass  # cache corrupto: se vuelve a descargar

        data = fetch_fn()
        envelope = {"fetched_at": time.time(), "data": data}
        path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
        return data
