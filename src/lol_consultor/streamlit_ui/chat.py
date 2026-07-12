"""Pestaña Asistente IA (Streamlit): chat con Ollama local. Solo se muestra
cuando Ollama está disponible (no en el despliegue de la nube)."""

from __future__ import annotations

import streamlit as st

from lol_consultor.service import LoLService
from lol_consultor.streamlit_ui.shared import get_assistant


def render(service: LoLService) -> None:
    assistant = get_assistant(service)
    st.caption(f"Asistente local (modelo {assistant.model} vía Ollama, sin costo).")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for turn in st.session_state.chat_history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])

    prompt = st.chat_input("Pregúntame sobre campeones, ítems, counters, draft...")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"), st.spinner("Pensando..."):
            answer, st.session_state.chat_history = assistant.ask(
                st.session_state.chat_history, prompt
            )
            st.markdown(answer)
