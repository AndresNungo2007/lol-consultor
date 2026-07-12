"""Pestaña Runas (Streamlit): árboles con winrate por runa y detalle wiki."""

from __future__ import annotations

import streamlit as st

from lol_consultor.service import LoLService
from lol_consultor.streamlit_ui.shared import winrate_badge
from lol_consultor.textutil import strip_tags


def render(service: LoLService) -> None:
    trees = service.rune_trees()
    en_names = _english_perk_names(service)
    for tree in trees:
        st.subheader(tree["name"])
        for slot in tree["slots"]:
            cols = st.columns(len(slot["runes"]))
            for col, perk in zip(cols, slot["runes"], strict=True):
                with col, st.container(border=True):
                    st.image(service.ddragon.rune_icon_url(perk["icon"]), width=36)
                    st.markdown(f"**{perk['name']}**")
                    st.markdown(winrate_badge(service.winrates.winrate_any("runes", perk["id"])))
                    st.caption(strip_tags(perk.get("shortDesc"))[:180])
                    with st.expander("wiki"):
                        title = en_names.get(str(perk["id"]))
                        intro = service.wiki.page_intro(title) if title else None
                        if intro:
                            st.markdown(intro[:2500])
                        else:
                            st.warning("Sin contenido de wiki.")
        st.divider()


def _english_perk_names(service: LoLService) -> dict[str, str]:
    names: dict[str, str] = {}
    for tree in service.ddragon_en.runes():
        for slot in tree["slots"]:
            for perk in slot["runes"]:
                names[str(perk["id"])] = perk["name"]
    return names
