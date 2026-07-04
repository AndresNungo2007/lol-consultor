"""Página 'Ítems': catálogo de ítems legendarios filtrable por etiqueta."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html

from lol_consultor.service import LoLService
from lol_consultor.textutil import strip_tags

_TAG_LABELS = {
    "Damage": "Daño de ataque",
    "SpellDamage": "Poder de habilidad",
    "Health": "Salud",
    "Armor": "Armadura",
    "SpellBlock": "Resistencia mágica",
    "AttackSpeed": "Velocidad de ataque",
    "CriticalStrike": "Golpe crítico",
    "Mana": "Maná",
    "Boots": "Botas",
    "LifeSteal": "Robo de vida",
    "SpellVamp": "Vampirismo de habilidad",
    "OnHit": "Al golpear",
    "Slow": "Ralentización",
    "Tenacity": "Tenacidad",
}


def _item_card(item_id: str, item: dict, icon_url: str) -> dbc.Card:
    tags = ", ".join(_TAG_LABELS.get(t, t) for t in item.get("tags", []))
    return dbc.Card(
        [
            dbc.CardImg(src=icon_url, top=True, style={"width": "64px", "margin": "8px auto"}),
            dbc.CardBody(
                [
                    html.H6(item["name"]),
                    html.P(f"{item['gold']['total']} de oro", className="small text-warning mb-1"),
                    html.P(strip_tags(item.get("description"))[:280], className="small"),
                    html.P(tags, className="small text-muted"),
                ]
            ),
        ],
        style={"width": "220px"},
        class_name="m-2",
    )


def layout(service: LoLService) -> html.Div:
    all_tags = sorted({t for i in service.legendary_items() for t in i.get("tags", [])})
    tag_options = [{"label": _TAG_LABELS.get(t, t), "value": t} for t in all_tags]
    return html.Div(
        [
            dbc.Row(
                dbc.Col(
                    dcc.Dropdown(
                        id="item-tag-filter",
                        options=tag_options,
                        multi=True,
                        placeholder="Filtrar por tipo de ítem...",
                    ),
                    md=6,
                ),
                class_name="mb-3",
            ),
            html.Div(id="item-grid", className="d-flex flex-wrap"),
        ]
    )


def register_callbacks(app: Dash, service: LoLService) -> None:
    @app.callback(Output("item-grid", "children"), Input("item-tag-filter", "value"))
    def _update(selected_tags: list[str] | None):
        items = service.legendary_items()
        if selected_tags:
            items = [i for i in items if set(selected_tags) & set(i.get("tags", []))]

        cards = []
        for item in items:
            item_id = item["image"]["full"].rsplit(".", 1)[0]
            icon_url = service.ddragon.item_icon_url(item_id)
            cards.append(_item_card(item_id, item, icon_url))
        return cards
