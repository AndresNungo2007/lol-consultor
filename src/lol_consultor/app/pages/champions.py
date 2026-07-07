"""Página 'Campeones': buscador + detalle (habilidades, meta de op.gg, patch history)."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html, no_update

from lol_consultor.probability import best_matchups
from lol_consultor.service import LoLService
from lol_consultor.textutil import strip_tags
from lol_consultor.winrates import MIN_GAMES_FOR_DISPLAY


def layout(service: LoLService) -> html.Div:
    champs = service.champion_list()
    options = [{"label": c["name"], "value": c["id"]} for c in champs]
    return html.Div(
        [
            dbc.Row(
                dbc.Col(
                    dcc.Dropdown(
                        id="champion-dropdown",
                        options=options,
                        value=options[0]["value"] if options else None,
                        clearable=False,
                        placeholder="Busca un campeón...",
                    ),
                    md=5,
                ),
                class_name="mb-3",
            ),
            dcc.Loading(html.Div(id="champion-detail")),
        ]
    )


def _ability_card(
    title: str, name: str, tooltip: str | None, icon_url: str, extra: str = ""
) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Img(src=icon_url, height="40px", className="me-2"),
                        html.Strong(f"{title}: {name}"),
                    ],
                    className="d-flex align-items-center mb-2",
                ),
                html.P(strip_tags(tooltip), style={"whiteSpace": "pre-wrap"}, className="small"),
                html.Small(extra, className="text-muted"),
            ]
        ),
        class_name="mb-2",
    )


def _best_matchups_section(
    service: LoLService, champion_key: int, champions_by_key: dict[int, dict[str, Any]]
) -> html.Div | None:
    """
    Top matchups donde el campeón gana más, con datos propios recolectados
    (Riot API). op.gg solo expone los peores matchups (counters); esto
    cubre lo que a op.gg le falta. No está separado por rol porque la
    recolección no registra en qué línea se jugó cada partida.
    """
    matchups = best_matchups(service.winrates, champion_key)
    if not matchups:
        return None

    rows = []
    for m in matchups:
        rival = champions_by_key.get(m.champion_id)
        rival_name = rival["name"] if rival else f"#{m.champion_id}"
        reliable = m.games >= MIN_GAMES_FOR_DISPLAY
        rows.append(
            html.Tr(
                [
                    html.Td(rival_name),
                    html.Td(f"{m.games} partidas" + ("" if reliable else " (muestra baja)")),
                    html.Td(f"{m.win_rate}%"),
                ]
            )
        )
    return html.Div(
        [
            html.H6("Tus mejores matchups (datos propios, todas las partidas recolectadas)"),
            dbc.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Rival"),
                                html.Th("Partidas"),
                                html.Th("Winrate del matchup"),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                bordered=False,
                size="sm",
                striped=True,
            ),
        ],
        className="mb-3",
    )


def _meta_section(
    detail, service: LoLService, champion_key: int, champions_by_key: dict[int, dict[str, Any]]
) -> html.Div:
    best_section = _best_matchups_section(service, champion_key, champions_by_key)
    if detail.meta is None or not detail.meta.positions:
        return html.Div(
            [
                dbc.Alert(
                    "Meta/counters de op.gg no disponible en este momento.",
                    color="warning",
                    class_name="mb-2",
                ),
                best_section or html.Div(),
            ]
        )

    blocks = []
    for pos in detail.meta.positions:
        rows = []
        for entry in pos.counters:
            rival = champions_by_key.get(entry.champion_id)
            rival_name = rival["name"] if rival else f"#{entry.champion_id}"
            rows.append(
                html.Tr(
                    [
                        html.Td(rival_name),
                        html.Td(f"{entry.games} partidas"),
                        html.Td(f"{entry.win_rate}%"),
                    ]
                )
            )
        blocks.append(
            html.Div(
                [
                    html.H6(
                        f"{pos.position} — winrate {pos.win_rate}% · pickrate "
                        f"{pos.play_rate}% · banrate {pos.ban_rate}%"
                    ),
                    dbc.Table(
                        [
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Counter"),
                                        html.Th("Partidas"),
                                        html.Th("Winrate del matchup"),
                                    ]
                                )
                            ),
                            html.Tbody(rows),
                        ],
                        bordered=False,
                        size="sm",
                        striped=True,
                    )
                    if rows
                    else html.P("Sin datos de counters suficientes.", className="small text-muted"),
                ],
                className="mb-3",
            )
        )
    return html.Div(
        [
            dbc.Alert(
                "Fuente: op.gg (comunidad), no oficial de Riot. Ordenado por menor winrate primero "
                "(los counters más fuertes).",
                color="info",
                class_name="small mb-2",
            ),
            *blocks,
            best_section or html.Div(),
        ]
    )


_SLOT_EMOJIS = {"Pasiva": "🔮", "Q": "⚔️", "W": "🛡️", "E": "💨", "R": "🌟"}
_BOLD_PREFIXES = ("Active:", "Passive:", "Innate:", "Recast:", "Toggle:")


def _ability_text_components(chunk: str) -> list:
    """Texto plano de la wiki -> párrafos, bullets y sub-encabezados en negrita."""
    components: list = []
    bullets: list = []

    def _flush_bullets() -> None:
        if bullets:
            components.append(html.Ul(list(bullets), className="small mb-2"))
            bullets.clear()

    for line in chunk.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            bullets.append(html.Li(line[2:]))
            continue
        _flush_bullets()
        if line.endswith(":") and len(line) < 60:
            components.append(html.P(html.Strong(line), className="small mb-1 mt-2"))
        elif line.startswith(_BOLD_PREFIXES):
            prefix, _, rest = line.partition(":")
            components.append(
                html.P([html.Strong(f"{prefix}:"), rest], className="small mb-1")
            )
        else:
            components.append(html.P(line, className="small mb-1"))
    _flush_bullets()
    return components


def _wiki_abilities_section(detail, service: LoLService, champion_id: str):
    """Detalle de la wiki partido en una card por habilidad (con iconos y bullets)."""
    if not detail.wiki_abilities:
        return dbc.Alert(
            "Detalle de la wiki no disponible para este campeón.",
            color="warning",
            class_name="small",
        )

    text = detail.wiki_abilities
    try:
        data_en = service.ddragon_en.champion(champion_id)
        ordered = [("Pasiva", data_en["passive"]["name"], None)]
        for slot, spell in zip("QWER", data_en.get("spells", []), strict=False):
            ordered.append((slot, spell["name"], spell["image"]["full"]))
    except Exception:
        ordered = []

    # localizar el inicio de cada habilidad dentro del texto de la wiki
    boundaries = []
    for slot, name, icon in ordered:
        idx = text.find(name)
        if idx >= 0:
            boundaries.append((idx, slot, name, icon))
    boundaries.sort()

    if not boundaries:
        return dbc.Card(
            dbc.CardBody(_ability_text_components(text)), class_name="small"
        )

    cards = []
    for i, (idx, slot, name, icon) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        chunk = text[idx + len(name): end]
        header = html.Div(
            [
                html.Img(
                    src=service.ddragon.spell_icon_url(icon), height="32px", className="me-2"
                )
                if icon
                else html.Span(_SLOT_EMOJIS.get(slot, ""), className="me-2 fs-5"),
                html.Strong(f"{_SLOT_EMOJIS.get(slot, '')} {slot}: {name}"),
            ],
            className="d-flex align-items-center mb-2",
        )
        cards.append(
            dbc.Card(
                dbc.CardBody([header, *_ability_text_components(chunk)]),
                class_name="mb-2",
            )
        )
    return html.Div(
        [
            dbc.Alert(
                "Fuente: wikilol (en inglés) — incluye cifras por nivel, resets e "
                "interacciones que Riot no publica en Data Dragon.",
                color="info",
                class_name="small",
            ),
            *cards,
        ]
    )


def register_callbacks(app: Dash, service: LoLService) -> None:
    @app.callback(Output("champion-detail", "children"), Input("champion-dropdown", "value"))
    def _update(champion_id: str | None):
        if not champion_id:
            return no_update

        detail = service.champion_detail(champion_id)
        data = detail.data
        ddragon = service.ddragon

        header = dbc.Row(
            [
                dbc.Col(
                    html.Img(
                        src=ddragon.splash_url(data["id"]),
                        style={"width": "100%", "borderRadius": "8px"},
                    ),
                    md=4,
                ),
                dbc.Col(
                    [
                        html.H3(f"{data['name']} — {data['title']}"),
                        html.P(strip_tags(data.get("blurb"))),
                        html.Div(
                            [dbc.Badge(tag, className="me-1") for tag in data.get("tags", [])]
                        ),
                        html.P(
                            f"Dificultad: {data['info']['difficulty']}/10 · "
                            f"Ataque: {data['info']['attack']}/10 · "
                            f"Magia: {data['info']['magic']}/10 · "
                            f"Defensa: {data['info']['defense']}/10",
                            className="small text-muted",
                        ),
                    ],
                    md=8,
                ),
            ],
            class_name="mb-3",
        )

        passive = data["passive"]
        ability_cards = [
            _ability_card(
                "Pasiva",
                passive["name"],
                passive["description"],
                ddragon.passive_icon_url(passive["image"]["full"]),
            )
        ]
        for slot, spell in zip(["Q", "W", "E", "R"], data["spells"], strict=True):
            ability_cards.append(
                _ability_card(
                    slot,
                    spell["name"],
                    # 'description' es prosa limpia; 'tooltip' trae placeholders
                    # sin resolver tipo {{ qdamage }} (limitación de Data Dragon).
                    spell.get("description") or spell.get("tooltip"),
                    ddragon.spell_icon_url(spell["image"]["full"]),
                    extra=f"Enfriamiento: {spell.get('cooldownBurn', '-')}s",
                )
            )

        ally_tips = [html.Li(strip_tags(t)) for t in data.get("allytips", [])]
        enemy_tips = [html.Li(strip_tags(t)) for t in data.get("enemytips", [])]
        tips = dbc.Row(
            [
                dbc.Col(
                    [html.H6("Cómo jugarlo (Riot)"), html.Ul(ally_tips) or html.P("—")],
                    md=6,
                ),
                dbc.Col(
                    [html.H6("Cómo contrarrestarlo (Riot)"), html.Ul(enemy_tips) or html.P("—")],
                    md=6,
                ),
            ],
            class_name="mb-3",
        )

        meta_section = _meta_section(
            detail, service, int(data["key"]), service.champions_by_key()
        )

        wiki_abilities_section = _wiki_abilities_section(detail, service, champion_id)

        patch_history_style = {"whiteSpace": "pre-wrap", "maxHeight": "300px", "overflowY": "auto"}
        patch_section = (
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Historial de cambios recientes (wikilol)"),
                        html.Pre(
                            detail.patch_history, style=patch_history_style, className="small"
                        ),
                    ]
                )
            )
            if detail.patch_history
            else dbc.Alert(
                "Historial de parches no disponible.", color="warning", class_name="small"
            )
        )

        return html.Div(
            [
                header,
                dbc.Tabs(
                    [
                        dbc.Tab(html.Div(ability_cards, className="mt-3"), label="Habilidades"),
                        dbc.Tab(
                            html.Div(wiki_abilities_section, className="mt-3"),
                            label="Habilidades a fondo (wiki)",
                        ),
                        dbc.Tab(tips, label="Estilo de juego"),
                        dbc.Tab(
                            html.Div(meta_section, className="mt-3"),
                            label="Meta y counters (op.gg)",
                        ),
                        dbc.Tab(
                            html.Div(patch_section, className="mt-3"),
                            label="Historial de parches",
                        ),
                    ]
                ),
            ]
        )
