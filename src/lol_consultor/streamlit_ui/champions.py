"""Pestaña Campeones (Streamlit): buscador + detalle completo."""

from __future__ import annotations

import streamlit as st

from lol_consultor.probability import best_matchups
from lol_consultor.service import LoLService
from lol_consultor.textutil import strip_tags

_SLOT_EMOJIS = {"Pasiva": "🔮", "Q": "⚔️", "W": "🛡️", "E": "💨", "R": "🌟"}


def render(service: LoLService) -> None:
    champs = service.champion_list()
    names = {c["name"]: c["id"] for c in champs}
    choice = st.selectbox("Campeón", list(names), key="champ_select")
    if not choice:
        return
    champion_id = names[choice]

    detail = service.champion_detail(champion_id)
    data = detail.data
    ddragon = service.ddragon

    col_img, col_info = st.columns([1, 2])
    with col_img:
        st.image(ddragon.splash_url(data["id"]), width="stretch")
    with col_info:
        st.subheader(f"{data['name']} — {data['title']}")
        st.caption(" · ".join(data.get("tags", [])))
        info = data["info"]
        st.write(
            f"**Dificultad** {info['difficulty']}/10 · **Ataque** {info['attack']}/10 · "
            f"**Magia** {info['magic']}/10 · **Defensa** {info['defense']}/10"
        )
        st.write(strip_tags(data.get("blurb")))

    tabs = st.tabs(
        [
            "Habilidades",
            "Habilidades a fondo (wiki)",
            "Estilo de juego",
            "Meta y counters",
            "Historial de parches",
        ]
    )
    with tabs[0]:
        _abilities(service, data)
    with tabs[1]:
        _wiki_abilities(service, detail, champion_id)
    with tabs[2]:
        _tips(data)
    with tabs[3]:
        _meta(service, detail, int(data["key"]))
    with tabs[4]:
        if detail.patch_history:
            st.text(detail.patch_history)
        else:
            st.info("Sin historial de parches disponible.")


def _abilities(service: LoLService, data: dict) -> None:
    passive = data["passive"]
    with st.container(border=True):
        c1, c2 = st.columns([1, 8])
        c1.image(service.ddragon.passive_icon_url(passive["image"]["full"]), width=48)
        c2.markdown(f"**🔮 Pasiva: {passive['name']}**")
        c2.caption(strip_tags(passive["description"]))
    for slot, spell in zip("QWER", data["spells"], strict=True):
        with st.container(border=True):
            c1, c2 = st.columns([1, 8])
            c1.image(service.ddragon.spell_icon_url(spell["image"]["full"]), width=48)
            c2.markdown(f"**{_SLOT_EMOJIS[slot]} {slot}: {spell['name']}**")
            c2.caption(
                f"Enfriamiento {spell.get('cooldownBurn', '?')}s — "
                + strip_tags(spell.get("description") or "")
            )


def _wiki_abilities(service: LoLService, detail, champion_id: str) -> None:
    if not detail.wiki_abilities:
        st.warning("Detalle de la wiki no disponible para este campeón.")
        return
    st.info("Fuente: wikilol (en inglés) — cifras por nivel, resets e interacciones.")
    text = detail.wiki_abilities
    try:
        data_en = service.ddragon_en.champion(champion_id)
        ordered = [("Pasiva", data_en["passive"]["name"])]
        for slot, spell in zip("QWER", data_en.get("spells", []), strict=False):
            ordered.append((slot, spell["name"]))
    except Exception:
        st.text(text)
        return

    boundaries = sorted(
        (idx, slot, name)
        for slot, name in ordered
        if (idx := text.find(name)) >= 0
    )
    if not boundaries:
        st.text(text)
        return
    for i, (idx, slot, name) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        chunk = text[idx + len(name): end].strip()
        with st.expander(f"{_SLOT_EMOJIS.get(slot, '')} {slot}: {name}", expanded=(slot == "R")):
            st.markdown(chunk)


def _tips(data: dict) -> None:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Cómo jugarlo (Riot)**")
        for tip in data.get("allytips", []):
            st.markdown(f"- {strip_tags(tip)}")
    with c2:
        st.markdown("**Cómo contrarrestarlo (Riot)**")
        for tip in data.get("enemytips", []):
            st.markdown(f"- {strip_tags(tip)}")


def _meta(service: LoLService, detail, champion_key: int) -> None:
    by_key = service.champions_by_key()
    if detail.meta is None or not detail.meta.positions:
        st.warning("Meta/counters de op.gg no disponible en este momento.")
    else:
        st.caption("Fuente: op.gg (comunidad). Ordenado por menor winrate (counters más fuertes).")
        for pos in detail.meta.positions:
            st.markdown(
                f"**{pos.position}** — winrate {pos.win_rate}% · pickrate "
                f"{pos.play_rate}% · banrate {pos.ban_rate}%"
            )
            if pos.counters:
                st.dataframe(
                    {
                        "Counter": [
                            (by_key.get(c.champion_id) or {}).get("name", f"#{c.champion_id}")
                            for c in pos.counters
                        ],
                        "Partidas": [c.games for c in pos.counters],
                        "Winrate del matchup": [f"{c.win_rate}%" for c in pos.counters],
                    },
                    hide_index=True,
                    width="stretch",
                )

    best = best_matchups(service.winrates, champion_key)
    if best:
        st.markdown("**Tus mejores matchups** (datos propios recolectados)")
        st.dataframe(
            {
                "Rival": [
                    (by_key.get(m.champion_id) or {}).get("name", f"#{m.champion_id}")
                    for m in best
                ],
                "Partidas": [m.games for m in best],
                "Winrate del matchup": [f"{m.win_rate}%" for m in best],
            },
            hide_index=True,
            width="stretch",
        )
