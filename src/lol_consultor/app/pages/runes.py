"""Página 'Runas': árboles de runas (Precisión, Dominación, etc.) y sus perks."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import ALL, Dash, Input, Output, ctx, dcc, html, no_update

from lol_consultor.service import LoLService
from lol_consultor.textutil import strip_tags
from lol_consultor.winrates import MIN_GAMES_FOR_DISPLAY


def _perk_block(perk: dict, service: LoLService, is_keystone: bool = False) -> html.Div:
    icon_url = service.ddragon.rune_icon_url(perk["icon"])
    description = strip_tags(perk.get("shortDesc"))[:200]
    children = [
        html.Img(src=icon_url, height="32px", className="me-2"),
        html.Span(perk["name"], className="fw-bold"),
    ]
    winrate = service.winrates.winrate_any("runes", perk["id"])
    if winrate is not None:
        wr, games = winrate
        reliable = games >= MIN_GAMES_FOR_DISPLAY
        children.append(
            dbc.Badge(
                f"WR {wr}% · {games}" + ("" if reliable else " (muestra baja)"),
                color=("success" if wr >= 50 else "danger") if reliable else "secondary",
                class_name="ms-2",
            )
        )
    else:
        children.append(dbc.Badge("sin datos aún", color="dark", class_name="ms-2 text-muted"))
    children.append(
        dbc.Button(
            "wiki",
            id={"type": "rune-wiki-btn", "index": str(perk["id"])},
            size="sm",
            outline=True,
            color="info",
            class_name="ms-2 py-0",
        )
    )
    children.append(html.P(description, className="small text-muted mb-2"))
    return html.Div(children, className="mb-2")


def _tree_card(tree: dict, service: LoLService) -> dbc.Card:
    slot_blocks = [
        html.Div(
            [
                _perk_block(perk, service, is_keystone=(slot_index == 0))
                for perk in slot["runes"]
            ],
            className="d-flex flex-wrap gap-3",
        )
        for slot_index, slot in enumerate(tree["slots"])
    ]
    tree_icon_url = service.ddragon.rune_icon_url(tree["icon"])

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.Img(src=tree_icon_url, height="28px", className="me-2"),
                    html.Strong(tree["name"]),
                ]
            ),
            dbc.CardBody(slot_blocks),
        ],
        class_name="mb-3",
    )


def layout(service: LoLService) -> html.Div:
    trees = service.rune_trees()
    return html.Div(
        [
            *[_tree_card(tree, service) for tree in trees],
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id="rune-wiki-title")),
                    dbc.ModalBody(dcc.Loading(html.Div(id="rune-wiki-body"))),
                ],
                id="rune-wiki-modal",
                size="lg",
                is_open=False,
                scrollable=True,
            ),
        ]
    )


def _english_perk_names(service: LoLService) -> dict[str, str]:
    names: dict[str, str] = {}
    for tree in service.ddragon_en.runes():
        for slot in tree["slots"]:
            for perk in slot["runes"]:
                names[str(perk["id"])] = perk["name"]
    return names


def register_callbacks(app: Dash, service: LoLService) -> None:
    @app.callback(
        Output("rune-wiki-modal", "is_open"),
        Output("rune-wiki-title", "children"),
        Output("rune-wiki-body", "children"),
        Input({"type": "rune-wiki-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def _open_wiki(clicks):
        if not any(c for c in clicks if c):
            return no_update, no_update, no_update
        perk_id = ctx.triggered_id["index"]
        title = _english_perk_names(service).get(perk_id)
        if not title:
            return True, "Runa", dbc.Alert("Sin página de wiki para esta runa.", color="warning")
        intro = service.wiki.page_intro(title)
        body: list = []
        if intro:
            body.append(html.Div(intro[:3000], style={"whiteSpace": "pre-wrap"}, className="small"))
        else:
            body.append(dbc.Alert("La wiki no tiene contenido para esta runa.", color="warning"))
        body.append(
            html.P("Fuente: wikilol (EN)", className="small text-muted fst-italic mt-3 mb-0")
        )
        return True, title, html.Div(body)
