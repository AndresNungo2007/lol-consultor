"""
Entrypoint de la app Streamlit (para despliegue en Streamlit Community Cloud).

La lógica de negocio se reutiliza tal cual de LoLService/DraftAnalyzer/
probability/gamewiki; aquí solo se orquesta la UI. La pestaña de chat (Ollama
local) solo aparece cuando Ollama está disponible: en la nube no se muestra.

Local:  streamlit run streamlit_app.py
Nube:   Streamlit Community Cloud detecta este archivo automáticamente.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permitir importar el paquete tanto instalado como desde ./src (Streamlit Cloud).
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from lol_consultor.streamlit_ui import (  # noqa: E402
    champions,
    chat,
    draft,
    items,
    mechanics,
    runes,
)
from lol_consultor.streamlit_ui.shared import (  # noqa: E402
    get_analyzer,
    get_service,
    ollama_available,
)

st.set_page_config(page_title="LoL Consultor", page_icon="⚔️", layout="wide")


def main() -> None:
    st.title("⚔️ LoL Consultor")
    service = get_service()
    analyzer = get_analyzer(service)
    st.caption(f"Parche actual: {service.ddragon.version}")

    labels = ["Campeones", "Ítems", "Runas", "Análisis de draft", "Dinámicas del juego"]
    show_chat = ollama_available(service)
    if show_chat:
        labels.append("Asistente IA")

    tabs = st.tabs(labels)
    with tabs[0]:
        champions.render(service)
    with tabs[1]:
        items.render(service)
    with tabs[2]:
        runes.render(service)
    with tabs[3]:
        draft.render(service, analyzer)
    with tabs[4]:
        mechanics.render(service)
    if show_chat:
        with tabs[5]:
            chat.render(service)


if __name__ == "__main__":
    main()
