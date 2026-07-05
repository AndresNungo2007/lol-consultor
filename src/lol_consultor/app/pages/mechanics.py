"""Página 'Dinámicas del juego': wiki de mecánicas centrales (armadura, CC, sustain...)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import MATCH, Dash, Input, Output, State, dcc, html

from lol_consultor.gamewiki import MECANICAS, buscar_mecanica, categorias
from lol_consultor.service import LoLService


def _accordion_items(filtro: str = "") -> list[dbc.AccordionItem]:
    needle = filtro.strip().lower()
    items = []
    for mecanica in MECANICAS:
        haystack = (mecanica.titulo + " " + mecanica.texto).lower()
        if needle and needle not in haystack:
            continue
        body: list = [
            html.Div(mecanica.texto, style={"whiteSpace": "pre-wrap"}, className="small"),
        ]
        if mecanica.wiki_page:
            body.extend(
                [
                    dbc.Button(
                        "Ver detalle de la wikilol (EN)",
                        id={"type": "mech-wiki-btn", "index": mecanica.id},
                        size="sm",
                        outline=True,
                        color="info",
                        class_name="mt-2",
                    ),
                    dcc.Loading(
                        html.Div(id={"type": "mech-wiki-out", "index": mecanica.id})
                    ),
                ]
            )
        items.append(
            dbc.AccordionItem(
                body,
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
                + ". Resumen curado en español; el botón de cada mecánica trae el "
                "detalle actualizado de la wikilol.",
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


def register_callbacks(app: Dash, service: LoLService) -> None:
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

    @app.callback(
        Output({"type": "mech-wiki-out", "index": MATCH}, "children"),
        Input({"type": "mech-wiki-btn", "index": MATCH}, "n_clicks"),
        State({"type": "mech-wiki-btn", "index": MATCH}, "id"),
        prevent_initial_call=True,
    )
    def _load_wiki(_clicks, button_id):
        mecanica = buscar_mecanica(button_id["index"])
        if mecanica is None or not mecanica.wiki_page:
            return dbc.Alert("Sin página de wiki asociada.", color="warning")
        intro = service.wiki.page_intro(mecanica.wiki_page)
        if not intro:
            return dbc.Alert("La wiki no respondió; intenta de nuevo.", color="warning")
        return dbc.Card(
            dbc.CardBody(
                html.Div(
                    intro[:3000],
                    style={"whiteSpace": "pre-wrap", "maxHeight": "300px", "overflowY": "auto"},
                    className="small",
                )
            ),
            class_name="mt-2",
        )