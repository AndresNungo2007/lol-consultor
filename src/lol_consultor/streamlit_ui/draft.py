"""Pestaña Análisis de draft (Streamlit): pick sugerido, probabilidad y build."""

from __future__ import annotations

import streamlit as st

from lol_consultor import config
from lol_consultor.draft import ROLES, DraftAnalyzer
from lol_consultor.probability import (
    BuildSuggestion,
    entity_icons_from_service,
    entity_names_from_service,
    suggest_items,
    suggest_keystones,
    suggest_secondary_runes,
    win_probability,
)
from lol_consultor.service import LoLService
from lol_consultor.winrates import MIN_GAMES_FOR_DISPLAY


def render(service: LoLService, analyzer: DraftAnalyzer) -> None:
    st.caption(
        "El orden usa un puntaje heurístico (meta op.gg, counters, balance de daño). "
        "La probabilidad de victoria es un cálculo aparte sobre tus partidas recolectadas: "
        "con poca muestra (n bajo) puede diferir del puntaje — es la incertidumbre real."
    )
    champs = service.champion_list()
    names = {c["name"]: c["id"] for c in champs}
    default_pool = [c["name"] for c in champs if c["id"] in config.DEFAULT_POOL]

    col1, col2 = st.columns([3, 1])
    pool = col1.multiselect("Tu pool de campeones", list(names), default=default_pool)
    role = col2.selectbox("Tu rol", ROLES, index=ROLES.index(config.DEFAULT_ROLE))
    col3, col4 = st.columns(2)
    allies = col3.multiselect("Aliados ya elegidos", list(names))
    enemies = col4.multiselect("Enemigos ya elegidos", list(names))

    if not st.button("Analizar draft", type="primary"):
        return
    if not pool:
        st.warning("Selecciona al menos un campeón en tu pool.")
        return

    pool_ids = [names[n] for n in pool]
    ally_ids = [names[n] for n in allies]
    enemy_ids = [names[n] for n in enemies]
    recs = analyzer.analyze(pool_ids, role, ally_ids, enemy_ids)
    if not recs:
        st.warning("No pude resolver los campeones del pool.")
        return

    ally_keys = _keys(service, ally_ids)
    enemy_keys = _keys(service, enemy_ids)
    probs = {}
    for rec in recs:
        champ = service.find_champion(rec.champion_id)
        if champ is None:
            continue
        opgg_wr = _opgg_winrate(service, champ, role)
        probs[rec.champion_id] = win_probability(
            service.winrates, int(champ["key"]), ally_keys, enemy_keys, opgg_wr
        )

    _suggestion_card(service, recs[0], probs.get(recs[0].champion_id), enemy_keys)
    st.divider()
    st.markdown("### Ranking del pool")
    for i, rec in enumerate(recs, start=1):
        _rec_row(service, i, rec, probs.get(rec.champion_id))


def _keys(service: LoLService, ids: list[str]) -> list[int]:
    out = []
    for cid in ids:
        c = service.find_champion(cid)
        if c:
            out.append(int(c["key"]))
    return out


def _opgg_winrate(service: LoLService, champ: dict, role: str) -> float | None:
    meta = service.opgg.champion_meta(int(champ["key"]))
    if meta is None:
        return None
    position = next((p for p in meta.positions if p.position == role), None) or meta.best_position()
    return position.win_rate if position else None


def _prob_label(prob) -> str:
    if prob is None:
        return ":gray[sin datos]"
    reliable = prob.champion_games >= MIN_GAMES_FOR_DISPLAY
    base = f"Prob. victoria {prob.probability}% (n={prob.champion_games})"
    return f":blue[{base}]" if reliable else f":gray[{base} · muestra baja]"


def _suggestion_card(service, rec, prob, enemy_keys) -> None:
    champ = service.find_champion(rec.champion_id)
    champ_key = int(champ["key"]) if champ else 0
    item_names, rune_names = entity_names_from_service(service)
    item_icons, rune_icons = entity_icons_from_service(service)
    items = suggest_items(service.winrates, champ_key, enemy_keys, item_names, top=3)
    keystones = suggest_keystones(service.winrates, champ_key, enemy_keys, rune_names, top=1)
    secondary = (
        suggest_secondary_runes(
            service.winrates, champ_key, keystones[0].entity_id, service.rune_trees(), rune_names
        )
        if keystones
        else []
    )

    with st.container(border=True):
        c1, c2 = st.columns([1, 6])
        c1.image(service.ddragon.champion_square_url(f"{rec.champion_id}.png"), width=56)
        c2.markdown(f"### Sugerencia: {rec.champion_name}")
        c2.markdown(_prob_label(prob))
        if prob:
            st.caption(" · ".join(prob.notes))
        if items:
            st.markdown("**Top 3 ítems con mejor éxito en este matchup:**")
            _bullets(items, item_icons, "partidas con este campeón")
        if keystones:
            st.markdown("**Runa clave + sub-runas de su rama:**")
            _bullets(keystones + secondary, rune_icons, "partidas")
        if not items and not keystones:
            st.info(
                "Aún no hay muestra de builds para este campeón. La rutina de recolección "
                "la irá llenando."
            )
        st.caption(
            "Estimaciones observacionales con suavizado bayesiano: comparan opciones, "
            "no garantizan el resultado de una partida."
        )


def _bullets(suggestions: list[BuildSuggestion], icons: dict[str, str], suffix: str) -> None:
    for s in suggestions:
        c1, c2 = st.columns([1, 12])
        icon = icons.get(s.entity_id)
        if icon:
            c1.image(icon, width=24)
        c2.markdown(f"{s.name} — **{s.score}%** ajustado ({s.games} {suffix})")


def _rec_row(service, rank, rec, prob) -> None:
    with st.container(border=True):
        c1, c2 = st.columns([1, 10])
        c1.image(service.ddragon.champion_square_url(f"{rec.champion_id}.png"), width=40)
        c2.markdown(
            f"**{rank}. {rec.champion_name}** · puntaje {rec.score:+.1f} · {_prob_label(prob)}"
        )
        for f in rec.factores:
            c2.caption(f"• {f.descripcion}")
