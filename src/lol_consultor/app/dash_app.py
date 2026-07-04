"""Factory de la app Dash: layout con tabs (Campeones/Ítems/Runas) + auto-refresco de parche."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html

from lol_consultor import config
from lol_consultor.app.pages import champions, chat, draft_page, items, mechanics, runes
from lol_consultor.assistant import LoLAssistant
from lol_consultor.draft import DraftAnalyzer
from lol_consultor.service import LoLService


def create_app(service: LoLService | None = None, assistant: LoLAssistant | None = None) -> Dash:
    service = service or LoLService()
    analyzer = DraftAnalyzer(service)
    assistant = assistant or LoLAssistant(service, analyzer=analyzer)

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.DARKLY],
        title="LoL Consultor",
        suppress_callback_exceptions=True,
    )

    app.layout = dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    [
                        html.H2("LoL Consultor"),
                        html.Div(id="patch-banner", className="small text-muted mb-2"),
                    ]
                )
            ),
            dcc.Interval(id="patch-check-interval", interval=config.PATCH_CHECK_INTERVAL_MS),
            dbc.Tabs(
                [
                    dbc.Tab(champions.layout(service), label="Campeones"),
                    dbc.Tab(items.layout(service), label="Ítems"),
                    dbc.Tab(runes.layout(service), label="Runas"),
                    dbc.Tab(draft_page.layout(service), label="Análisis de draft"),
                    dbc.Tab(mechanics.layout(), label="Dinámicas del juego"),
                    dbc.Tab(chat.layout(assistant), label="Asistente IA"),
                ]
            ),
        ],
        fluid=True,
        class_name="py-3",
    )

    champions.register_callbacks(app, service)
    items.register_callbacks(app, service)
    draft_page.register_callbacks(app, service, analyzer)
    mechanics.register_callbacks(app)
    chat.register_callbacks(app, assistant)

    @app.callback(Output("patch-banner", "children"), Input("patch-check-interval", "n_intervals"))
    def _check_patch(_n_intervals: int) -> str:
        changed = service.check_for_new_patch()
        note = " (se detectó parche nuevo, refresca la página)" if changed else ""
        return f"Parche actual: {service.ddragon.version}{note}"

    return app
