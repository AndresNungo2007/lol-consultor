"""Página 'Análisis de draft': recomienda qué campeón del pool elegir en champ select."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html

from lol_consultor import config
from lol_consultor.draft import ROLES, DraftAnalyzer, DraftRecommendation
from lol_consultor.probability import (
    WinProbability,
    entity_names_from_service,
    suggest_items,
    suggest_keystones,
    win_probability,
)
from lol_consultor.service import LoLService


def _champion_options(service: LoLService) -> list[dict[str, str]]:
    return [{"label": c["name"], "value": c["id"]} for c in service.champion_list()]


def layout(service: LoLService) -> html.Div:
    options = _champion_options(service)
    valid_ids = {o["value"] for o in options}
    default_pool = [c for c in config.DEFAULT_POOL if c in valid_ids]
    return html.Div(
        [
            dbc.Alert(
                "Elige tu pool y rol, agrega los picks de aliados y enemigos a medida "
                "que avanza la selección, y presiona Analizar. El puntaje combina meta "
                "(winrate op.gg), counters contra los enemigos, balance de daño AP/AD y "
                "composición del equipo.",
                color="info",
                class_name="small",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Tu pool de campeones", className="small"),
                            dcc.Dropdown(
                                id="draft-pool",
                                options=options,
                                value=default_pool,
                                multi=True,
                            ),
                        ],
                        md=8,
                    ),
                    dbc.Col(
                        [
                            html.Label("Tu rol", className="small"),
                            dcc.Dropdown(
                                id="draft-role",
                                options=[{"label": r, "value": r} for r in ROLES],
                                value=config.DEFAULT_ROLE,
                                clearable=False,
                            ),
                        ],
                        md=4,
                    ),
                ],
                class_name="mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Aliados ya elegidos", className="small"),
                            dcc.Dropdown(id="draft-allies", options=options, multi=True),
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            html.Label("Enemigos ya elegidos", className="small"),
                            dcc.Dropdown(id="draft-enemies", options=options, multi=True),
                        ],
                        md=6,
                    ),
                ],
                class_name="mb-3",
            ),
            dbc.Button("Analizar draft", id="draft-run", color="primary", class_name="mb-3"),
            dcc.Loading(html.Div(id="draft-results")),
        ]
    )


def _recommendation_card(
    rank: int,
    rec: DraftRecommendation,
    service: LoLService,
    prob: WinProbability | None = None,
) -> dbc.Card:
    icon_url = service.ddragon.champion_square_url(f"{rec.champion_id}.png")
    color = "success" if rank == 1 else None
    prob_badge = None
    if prob is not None:
        prob_badge = dbc.Badge(
            f"Prob. victoria: {prob.probability}%",
            color="info",
            class_name="ms-2",
            title=f"Evidencia: {prob.evidence_games} partidas propias",
        )
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Img(src=icon_url, height="48px", className="me-2 rounded"),
                        html.Strong(f"{rank}. {rec.champion_name}"),
                        dbc.Badge(
                            f"{rec.score:+.1f}",
                            color="success" if rec.score >= 0 else "danger",
                            class_name="ms-2",
                        ),
                        prob_badge or "",
                    ],
                    className="d-flex align-items-center mb-2",
                ),
                html.Ul(
                    [html.Li(f.descripcion, className="small") for f in rec.factores],
                    className="mb-0",
                ),
            ]
        ),
        color=color,
        outline=True,
        class_name="mb-2",
    )


def _final_suggestion_card(
    service: LoLService,
    rec: DraftRecommendation,
    prob: WinProbability | None,
    enemy_keys: list[int],
) -> dbc.Card:
    """Pick sugerido + build (ítems/runas) rankeado contra los enemigos elegidos."""
    champ = service.find_champion(rec.champion_id)
    champ_key = int(champ["key"]) if champ else 0
    item_names, keystone_names = entity_names_from_service(service)
    items = suggest_items(service.winrates, champ_key, enemy_keys, item_names)
    keystones = suggest_keystones(service.winrates, champ_key, enemy_keys, keystone_names)

    children: list = [
        html.H5(
            [
                "Sugerencia: ",
                html.Img(
                    src=service.ddragon.champion_square_url(f"{rec.champion_id}.png"),
                    height="36px",
                    className="mx-2 rounded",
                ),
                html.Strong(rec.champion_name),
                dbc.Badge(
                    f"Prob. victoria estimada: {prob.probability}%" if prob else "sin datos",
                    color="info",
                    class_name="ms-2",
                ),
            ],
            className="d-flex align-items-center",
        ),
    ]
    if prob:
        children.append(
            html.P(
                " · ".join(prob.notes),
                className="small text-muted",
            )
        )
    if items:
        children.append(html.H6("Ítems con mejor éxito en este matchup (tus datos):"))
        children.append(
            html.Ul(
                [
                    html.Li(
                        f"{s.name} — {s.score}% ajustado ({s.games} partidas con este campeón)",
                        className="small",
                    )
                    for s in items
                ]
            )
        )
    if keystones:
        children.append(html.H6("Runas clave con mejor éxito:"))
        children.append(
            html.Ul(
                [
                    html.Li(
                        f"{s.name} — {s.score}% ajustado ({s.games} partidas)",
                        className="small",
                    )
                    for s in keystones
                ]
            )
        )
    if not items and not keystones:
        children.append(
            html.P(
                "Aún no hay muestra de builds para este campeón: corre el recolector "
                "(o espera a la rutina de GitHub Actions) para habilitar la sugerencia.",
                className="small text-muted",
            )
        )
    children.append(
        html.P(
            "Estimaciones observacionales con suavizado bayesiano: comparan opciones, "
            "no garantizan el resultado de una partida.",
            className="small fst-italic text-muted mb-0",
        )
    )
    return dbc.Card(dbc.CardBody(children), color="success", outline=True, class_name="mb-3")


def register_callbacks(app: Dash, service: LoLService, analyzer: DraftAnalyzer) -> None:
    @app.callback(
        Output("draft-results", "children"),
        Input("draft-run", "n_clicks"),
        State("draft-pool", "value"),
        State("draft-role", "value"),
        State("draft-allies", "value"),
        State("draft-enemies", "value"),
        prevent_initial_call=True,
    )
    def _run(_clicks, pool, role, allies, enemies):
        if not pool:
            return dbc.Alert("Selecciona al menos un campeón en tu pool.", color="warning")
        role = role or config.DEFAULT_ROLE
        recs = analyzer.analyze(pool, role, allies or [], enemies or [])
        if not recs:
            return dbc.Alert("No pude resolver los campeones del pool.", color="warning")

        def _keys(names: list[str]) -> list[int]:
            resolved = (service.find_champion(n) for n in names or [])
            return [int(c["key"]) for c in resolved if c]

        ally_keys, enemy_keys = _keys(allies), _keys(enemies)
        probs: dict[str, WinProbability] = {}
        for rec in recs:
            champ = service.find_champion(rec.champion_id)
            if champ is None:
                continue
            meta = service.opgg.champion_meta(int(champ["key"]))
            opgg_wr = None
            if meta is not None:
                position = next((p for p in meta.positions if p.position == role), None)
                position = position or meta.best_position()
                opgg_wr = position.win_rate if position else None
            probs[rec.champion_id] = win_probability(
                service.winrates, int(champ["key"]), ally_keys, enemy_keys, opgg_wr
            )

        cards: list = [
            _final_suggestion_card(service, recs[0], probs.get(recs[0].champion_id), enemy_keys)
        ]
        cards.extend(
            _recommendation_card(i + 1, rec, service, probs.get(rec.champion_id))
            for i, rec in enumerate(recs)
        )
        return cards
