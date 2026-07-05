"""Página 'Runas': árboles de runas (Precisión, Dominación, etc.) y sus perks."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from lol_consultor.service import LoLService
from lol_consultor.textutil import strip_tags


def _perk_block(perk: dict, service: LoLService, is_keystone: bool = False) -> html.Div:
    icon_url = service.ddragon.rune_icon_url(perk["icon"])
    description = strip_tags(perk.get("shortDesc"))[:200]
    children = [
        html.Img(src=icon_url, height="32px", className="me-2"),
        html.Span(perk["name"], className="fw-bold"),
    ]
    if is_keystone:
        winrate = service.winrates.keystone_winrate(perk["id"])
        if winrate is not None:
            wr, games = winrate
            children.append(
                dbc.Badge(
                    f"WR {wr}% · {games}",
                    color="success" if wr >= 50 else "secondary",
                    class_name="ms-2",
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
    return html.Div([_tree_card(tree, service) for tree in trees])
