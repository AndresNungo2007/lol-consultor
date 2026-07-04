"""Configuración del proyecto vía variables de entorno."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


LANG: str = os.getenv("LOL_LANG", "es_ES")
CACHE_DIR: Path = Path(os.getenv("LOL_CACHE_DIR", ".lol_cache"))
HTTP_TIMEOUT: int = _int_env("LOL_HTTP_TIMEOUT", 20)

# TTLs de cache (segundos). Data Dragon se versiona por parche (no usa TTL).
WIKI_CACHE_TTL: int = _int_env("LOL_WIKI_CACHE_TTL", 24 * 3600)
OPGG_CACHE_TTL: int = _int_env("LOL_OPGG_CACHE_TTL", 6 * 3600)

# Cada cuánto revisa la app si hay parche nuevo de Data Dragon (milisegundos).
PATCH_CHECK_INTERVAL_MS: int = _int_env("LOL_PATCH_CHECK_INTERVAL_MS", 30 * 60 * 1000)
