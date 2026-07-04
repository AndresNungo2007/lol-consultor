"""Página 'Ítems': catálogo de ítems legendarios filtrable por etiqueta."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html

from lol_consultor.service import LoLService
from lol_consultor.textutil import item_description_sections

_TAG_LABELS = {
    "AbilityHaste": "Aceleración de habilidades",
    "Active": "Activa",
    "Armor": "Armadura",
    "ArmorPenetration": "Penetración de armadura",
    "AttackSpeed": "Velocidad de ataque",
    "Aura": "Aura",
    "Boots": "Botas",
    "Consumable": "Consumible",
    "CooldownReduction": "Reducción de enfriamiento",
    "CriticalStrike": "Golpe crítico",
    "Damage": "Daño de ataque",
    "GoldPer": "Generación de oro",
    "Health": "Salud",
    "HealthRegen": "Regeneración de vida",
    "Jungle": "Jungla",
    "Lane": "Línea",
    "LifeSteal": "Robo de vida",
    "MagicPenetration": "Penetración mágica",
    "MagicResist": "Resistencia mágica",
    "Mana": "Maná",
    "ManaRegen": "Regeneración de maná",
    "NonbootsMovement": "Velocidad de movimiento",
    "OnHit": "Al golpear",
    "Slow": "Ralentización",
    "SpellBlock": "Resistencia mágica",
    "SpellDamage": "Poder de habilidad",
    "SpellVamp": "Vampirismo de hechizos",
    "Stealth": "Sigilo",
    "Tenacity": "Tenacidad",
    "Trinket": "Baratija",
    "Vision": "Visión",
}


def _item_card(
    item_id: str, item: dict, icon_url: str, winrate: tuple[float, int] | None = None
) -> dbc.Card:
    stats, effects = item_description_sections(item.get("description"))
    tags = ", ".join(_TAG_LABELS.get(t, t) for t in item.get("tags", []))

    body: list = [
        html.H6(item["name"]),
        html.P(f"{item['gold']['total']} de oro", className="small text-warning mb-1"),
    ]
    if winrate is not None:
        wr, games = winrate
        body.append(
            dbc.Badge(
                f"WR {wr}% · {games} apariciones",
                color="success" if wr >= 50 else "secondary",
                class_name="mb-2",
            )
        )
    if stats:
        body.append(
            html.Ul(
                [html.Li(stat) for stat in stats],
                className="small ps-3 mb-2",
            )
        )
    for effect in effects[:3]:
        body.append(html.P(effect[:220], className="small mb-1"))
    body.append(html.P(tags, className="small text-muted mt-2 mb-0"))

    return dbc.Card(
        [
            dbc.CardImg(src=icon_url, top=True, style={"width": "64px", "margin": "8px auto"}),
            dbc.CardBody(body),
        ],
        style={"width": "240px"},
        class_name="m-2",
    )


def layout(service: LoLService) -> html.Div:
    all_tags = sorted({t for i in service.legendary_items() for t in i.get("tags", [])})
    tag_options = [{"label": _TAG_LABELS.get(t, t), "value": t} for t in all_tags]
    winrate_note = (
        dbc.Alert(
            f"Winrates calculados con la Riot API sobre {service.winrates.total_matches} "
            "partidas ranked recolectadas. Ojo: comparativos, no causales (el equipo que "
            "va ganando completa más ítems).",
            color="info",
            class_name="small",
        )
        if service.winrates.total_matches
        else None
    )
    return html.Div(
        [
            winrate_note or html.Div(),
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
            winrate = service.winrates.item_winrate(item_id)
            cards.append(_item_card(item_id, item, icon_url, winrate=winrate))
        return cards
