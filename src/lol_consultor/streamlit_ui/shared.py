"""Infraestructura compartida de la UI Streamlit: servicio cacheado, sync de
winrates desde la nube y detección de Ollama."""

from __future__ import annotations

import streamlit as st

from lol_consultor import config
from lol_consultor.assistant import LoLAssistant
from lol_consultor.draft import DraftAnalyzer
from lol_consultor.service import LoLService


@st.cache_resource(show_spinner="Cargando datos de League of Legends...")
def get_service() -> LoLService:
    """
    LoLService construido una sola vez por proceso (Data Dragon + caches).
    En Streamlit Cloud el filesystem es efímero: los winrates se traen del
    agregado publicado en la nube (rama winrates-data) porque el recolector
    corre en GitHub Actions, no aquí.
    """
    service = LoLService()
    if config.WINRATES_SYNC_URL:
        try:
            service.winrates.sync_from_url(config.WINRATES_SYNC_URL)
        except Exception:
            pass  # sin winrates la app sigue funcionando (badges "sin datos")
    return service


@st.cache_resource
def get_analyzer(_service: LoLService) -> DraftAnalyzer:
    return DraftAnalyzer(_service)


@st.cache_resource
def get_assistant(_service: LoLService) -> LoLAssistant:
    return LoLAssistant(_service, analyzer=get_analyzer(_service))


def ollama_available(_service: LoLService) -> bool:
    """True si el asistente local (Ollama) está disponible: la pestaña de chat
    solo se muestra en local, no en el despliegue de la nube."""
    try:
        return get_assistant(_service).status_message() is None
    except Exception:
        return False


def winrate_badge(winrate: tuple[float, int] | None) -> str:
    """Texto markdown para un badge de winrate, con marca de muestra baja."""
    if winrate is None:
        return ":gray[sin datos aún]"
    wr, games = winrate
    reliable = games >= config_min_games()
    if not reliable:
        return f":gray[WR {wr}% · {games} part. (muestra baja)]"
    color = "green" if wr >= 50 else "red"
    return f":{color}[**WR {wr}%** · {games} part.]"


def config_min_games() -> int:
    from lol_consultor.winrates import MIN_GAMES_FOR_DISPLAY

    return MIN_GAMES_FOR_DISPLAY
