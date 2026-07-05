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

# Refresco proactivo en segundo plano (segundos). 0 = desactivado.
REFRESH_INTERVAL_S: int = _int_env("LOL_REFRESH_INTERVAL_S", 3600)

# Asistente de chat (LLM local vía Ollama).
OLLAMA_HOST: str = os.getenv("LOL_OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL: str = os.getenv("LOL_OLLAMA_MODEL", "qwen3:8b")

# Riot API (winrates de items/runas a partir de partidas reales).
# Key gratuita en https://developer.riotgames.com (la de desarrollo expira cada 24 h).
RIOT_API_KEY: str = os.getenv("RIOT_API_KEY", "")
RIOT_PLATFORM: str = os.getenv("LOL_RIOT_PLATFORM", "la1")  # LAN (Latinoamérica Norte)
RIOT_REGION: str = os.getenv("LOL_RIOT_REGION", "americas")

# URL del agregado de winrates publicado por GitHub Actions (rama winrates-data).
# El refresher lo descarga si trae más partidas que el local. Vacío = desactivado.
WINRATES_SYNC_URL: str = os.getenv(
    "LOL_WINRATES_SYNC_URL",
    "https://raw.githubusercontent.com/AndresNungo2007/lol-consultor/winrates-data/winrates.json",
)

# Análisis de draft: pool de campeones del usuario y su rol habitual.
DEFAULT_POOL: list[str] = [
    c.strip()
    for c in os.getenv(
        "LOL_POOL", "Briar,Udyr,Viego,Karthus,Belveth,Olaf,Ekko"
    ).split(",")
    if c.strip()
]
DEFAULT_ROLE: str = os.getenv("LOL_ROLE", "JUNGLE")
