"""Pestaña Dinámicas del juego (Streamlit): mecánicas con detalle wiki lazy."""

from __future__ import annotations

import streamlit as st

from lol_consultor.gamewiki import MECANICAS, categorias
from lol_consultor.service import LoLService


def render(service: LoLService) -> None:
    st.caption("Mecánicas centrales del juego: " + ", ".join(categorias()))
    filtro = st.text_input("Filtrar", placeholder="ej. armadura, tenacidad, oro").strip().lower()

    for mecanica in MECANICAS:
        haystack = (mecanica.titulo + " " + mecanica.texto).lower()
        if filtro and filtro not in haystack:
            continue
        with st.expander(f"{mecanica.titulo}  ·  {mecanica.categoria}"):
            st.write(mecanica.texto)
            if mecanica.wiki_page:
                with st.popover("Ver detalle de la wikilol (EN)"):
                    intro = service.wiki.page_intro(mecanica.wiki_page)
                    if intro:
                        st.markdown(intro[:3000])
                    else:
                        st.warning("La wiki no respondió.")
