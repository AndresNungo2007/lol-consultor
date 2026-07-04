"""Página 'Análisis de draft': recomienda qué campeón del pool elegir en champ select."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html

from lol_consultor import config
from lol_consultor.draft import ROLES, DraftAnalyzer, DraftRecommendation
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
    rank: int, rec: DraftRecommendation, service: LoLService
) -> dbc.Card:
    icon_url = service.ddragon.champion_square_url(f"{rec.champion_id}.png")
    color = "success" if rank == 1 else None
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
        recs = analyzer.analyze(pool, role or config.DEFAULT_ROLE, allies or [], enemies or [])
        if not recs:
            return dbc.Alert("No pude resolver los campeones del pool.", color="warning")
        return [
            _recommendation_card(i + 1, rec, service) for i, rec in enumerate(recs)
        ]
