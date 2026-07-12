"""Pestaña Ítems (Streamlit): catálogo filtrable/ordenable con winrate y detalle wiki."""

from __future__ import annotations

import streamlit as st

from lol_consultor.service import LoLService
from lol_consultor.streamlit_ui.shared import winrate_badge
from lol_consultor.textutil import item_description_sections

_TAG_LABELS = {
    "AbilityHaste": "Aceleración de habilidades",
    "Active": "Activa",
    "Armor": "Armadura",
    "ArmorPenetration": "Penetración de armadura",
    "AttackSpeed": "Velocidad de ataque",
    "Boots": "Botas",
    "CooldownReduction": "Reducción de enfriamiento",
    "CriticalStrike": "Golpe crítico",
    "Damage": "Daño de ataque",
    "Health": "Salud",
    "HealthRegen": "Regeneración de vida",
    "LifeSteal": "Robo de vida",
    "MagicPenetration": "Penetración mágica",
    "MagicResist": "Resistencia mágica",
    "Mana": "Maná",
    "ManaRegen": "Regeneración de maná",
    "NonbootsMovement": "Velocidad de movimiento",
    "OnHit": "Al golpear",
    "SpellDamage": "Poder de habilidad",
    "SpellVamp": "Vampirismo de hechizos",
    "Tenacity": "Tenacidad",
}

_SORTS = {
    "Precio: mayor a menor": "gold_desc",
    "Precio: menor a mayor": "gold_asc",
    "Winrate: mayor a menor": "wr_desc",
    "Winrate: menor a mayor": "wr_asc",
}


def render(service: LoLService) -> None:
    items = service.legendary_items()
    if service.winrates.total_matches:
        st.caption(
            f"Winrates sobre {service.winrates.total_matches} partidas ranked. "
            "Comparativos, no causales (el equipo que va ganando completa más ítems)."
        )

    all_tags = sorted({t for i in items for t in i.get("tags", [])})
    col1, col2 = st.columns(2)
    selected = col1.multiselect(
        "Filtrar por tipo", all_tags, format_func=lambda t: _TAG_LABELS.get(t, t)
    )
    sort_label = col2.selectbox("Ordenar por", list(_SORTS))
    sort_by = _SORTS[sort_label]

    if selected:
        items = [i for i in items if set(selected) & set(i.get("tags", []))]

    rows = []
    for item in items:
        item_id = item["image"]["full"].rsplit(".", 1)[0]
        rows.append((item, item_id, service.winrates.winrate_any("items", item_id)))

    if sort_by == "gold_asc":
        rows.sort(key=lambda r: r[0]["gold"]["total"])
    elif sort_by == "wr_desc":
        rows.sort(key=lambda r: r[2][0] if r[2] else -1, reverse=True)
    elif sort_by == "wr_asc":
        rows.sort(key=lambda r: r[2][0] if r[2] is not None else 101)
    else:
        rows.sort(key=lambda r: -r[0]["gold"]["total"])

    st.caption(f"{len(rows)} ítems")
    cols_per_row = 4
    for i in range(0, len(rows), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, (item, item_id, winrate) in zip(cols, rows[i : i + cols_per_row], strict=False):
            with col, st.container(border=True):
                st.image(service.ddragon.item_icon_url(item_id), width=48)
                st.markdown(f"**{item['name']}**")
                st.caption(f"{item['gold']['total']} de oro")
                st.markdown(winrate_badge(winrate))
                _item_body(service, item, item_id)


def _item_body(service: LoLService, item: dict, item_id: str) -> None:
    stats, effects = item_description_sections(item.get("description"))
    if stats:
        st.markdown("\n".join(f"- {s}" for s in stats))
    for effect in effects[:2]:
        st.caption(effect[:200])
    tags = ", ".join(_TAG_LABELS.get(t, t) for t in item.get("tags", []))
    if tags:
        st.caption(tags)
    with st.expander("Detalle wiki"):
        item_en = service.ddragon_en.items().get(item_id)
        if item_en is None:
            st.warning("Sin página de wiki para este ítem.")
            return
        intro = service.wiki.page_intro(item_en["name"])
        notes = service.wiki.page_notes(item_en["name"])
        if intro:
            st.markdown(intro[:2000])
        if notes:
            st.markdown("**Notas e interacciones**")
            st.markdown(notes[:2500])
        if not intro and not notes:
            st.warning("La wiki no tiene contenido para este ítem.")
