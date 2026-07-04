from __future__ import annotations

from lol_consultor.textutil import item_description_sections, strip_tags


def test_strip_tags_removes_html_and_placeholders():
    raw = (
        "Aatrox golpea e inflige {{ qdamage }} de <b>daño físico</b>."
        "{{ spellmodifierdescriptionappend }}"
    )

    text = strip_tags(raw)

    assert "{{" not in text
    assert "<b>" not in text
    assert "daño físico" in text


def test_strip_tags_handles_none_and_empty():
    assert strip_tags(None) == ""
    assert strip_tags("") == ""


def test_item_description_sections_splits_stats_and_effects():
    raw = (
        "<mainText><stats><attention>150</attention> de daño de ataque<br>"
        "<attention>20%</attention> de probabilidad de impacto crítico</stats>"
        "<br><passive>Muerte e impuestos:</passive> Si dejas a un campeón con poca vida, "
        "lo ejecutas.</mainText>"
    )

    stats, effects = item_description_sections(raw)

    assert stats == ["150 de daño de ataque", "20% de probabilidad de impacto crítico"]
    assert len(effects) == 1
    assert effects[0].startswith("Muerte e impuestos:")


def test_item_description_sections_without_stats_block():
    raw = "<mainText>Activa - Consumir: Abre una selección de objetos.</mainText>"

    stats, effects = item_description_sections(raw)

    assert stats == []
    assert effects == ["Activa - Consumir: Abre una selección de objetos."]


def test_item_description_sections_handles_none():
    assert item_description_sections(None) == ([], [])
