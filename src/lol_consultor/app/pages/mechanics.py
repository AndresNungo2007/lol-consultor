"""Página 'Dinámicas del juego': wiki de mecánicas centrales (armadura, CC, sustain...)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html

from lol_consultor.gamewiki import MECANICAS, categorias


def _accordion_items(filtro: str = "") -> list[dbc.AccordionItem]:
    needle = filtro.strip().lower()
    items = []
    for mecanica in MECANICAS:
        haystack = (mecanica.titulo + " " + mecanica.texto).lower()
        if needle and needle not in haystack:
            continue
        items.append(
            dbc.AccordionItem(
                html.Div(mecanica.texto, style={"whiteSpace": "pre-wrap"}, className="small"),
                title=f"{mecanica.titulo}  ·  {mecanica.categoria}",
                item_id=mecanica.id,
            )
        )
    return items


def layout() -> html.Div:
    return html.Div(
        [
            dbc.Alert(
                "Cómo funcionan las mecánicas centrales del juego: "
                + ", ".join(categorias())
                + ". Estas reglas son estables entre parches.",
                color="info",
                class_name="small",
            ),
            dbc.Row(
                dbc.Col(
                    dcc.Input(
                        id="mechanics-filter",
                        placeholder="Filtrar... (ej. armadura, tenacidad, oro)",
                        type="text",
                        className="form-control",
                        debounce=True,
                    ),
                    md=5,
                ),
                class_name="mb-3",
            ),
            html.Div(
                dbc.Accordion(_accordion_items(), start_collapsed=True, always_open=True),
                id="mechanics-list",
            ),
        ]
    )


def register_callbacks(app: Dash) -> None:
    @app.callback(
        Output("mechanics-list", "children"),
        Input("mechanics-filter", "value"),
        prevent_initial_call=True,
    )
    def _filter(value: str | None):
        items = _accordion_items(value or "")
        if not items:
            return dbc.Alert("Ninguna mecánica coincide con ese filtro.", color="warning")
        return dbc.Accordion(items, start_collapsed=True, always_open=True)
