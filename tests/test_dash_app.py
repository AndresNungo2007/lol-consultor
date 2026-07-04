from __future__ import annotations

from lol_consultor.app.dash_app import create_app
from lol_consultor.app.pages.champions import _ability_card, _meta_section
from lol_consultor.app.pages.items import _item_card
from lol_consultor.app.pages.runes import _tree_card
from lol_consultor.models import ChampionMeta, CounterEntry, PositionMeta
from lol_consultor.service import ChampionDetail


def test_create_app_builds_layout_without_errors(stub_service):
    app = create_app(service=stub_service)

    assert app.layout is not None


def test_meta_section_renders_counters_with_champion_names(sample_champion_list):
    champions_by_key = {int(c["key"]): c for c in sample_champion_list["data"].values()}
    counters = [CounterEntry(champion_id=103, games=100, wins=40)]
    position = PositionMeta(
        position="MID", play_rate=8.8, win_rate=51.0, ban_rate=3.3, counters=counters
    )
    meta = ChampionMeta(champion_id=103, positions=[position])
    detail = ChampionDetail(data={}, meta=meta, patch_history=None)

    section = _meta_section(detail, champions_by_key)

    assert section is not None


def test_meta_section_shows_warning_when_meta_unavailable():
    detail = ChampionDetail(data={}, meta=None, patch_history=None)

    section = _meta_section(detail, champions_by_key={})

    assert section is not None


def test_ability_card_strips_html_tooltip():
    card = _ability_card("Q", "Orbe del engaño", "Inflige <b>daño</b> mágico.", "http://x/icon.png")
    assert card is not None


def test_item_card_renders():
    item = {
        "name": "Filo mortal",
        "description": "<stats>Poder de habilidad</stats>",
        "gold": {"total": 3200},
        "tags": ["SpellDamage"],
    }
    card = _item_card("3089", item, "http://x/item/3089.png")
    assert card is not None


def test_tree_card_renders(sample_runes, stub_service):
    card = _tree_card(sample_runes[0], stub_service)
    assert card is not None
