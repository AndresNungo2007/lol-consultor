from __future__ import annotations

from lol_consultor.ability_search import search_champion_abilities


def test_finds_match_in_spell_description(stub_service):
    result = search_champion_abilities(stub_service, "inflige daño")

    assert result.champions_checked == 1
    assert result.champions_total == 1
    assert result.full_coverage
    assert len(result.matches) == 1
    assert result.matches[0].champion_name == "Ahri"
    assert result.matches[0].slot == "Q"
    assert result.matches[0].ability_name == "Orbe del engaño"


def test_no_match_returns_empty_but_reports_coverage(stub_service):
    result = search_champion_abilities(stub_service, "algo que no existe en ningún kit")

    assert result.matches == []
    assert result.champions_checked == 1
    assert result.full_coverage


def test_search_is_case_insensitive(stub_service):
    result = search_champion_abilities(stub_service, "INFLIGE DAÑO")

    assert len(result.matches) == 1


def test_partial_coverage_when_champion_not_cached(stub_service):
    original = stub_service.ddragon.champion_if_cached
    stub_service.ddragon.champion_if_cached = lambda _cid: None
    try:
        result = search_champion_abilities(stub_service, "daño")
    finally:
        stub_service.ddragon.champion_if_cached = original

    assert result.matches == []
    assert result.champions_checked == 0
    assert result.champions_total == 1
    assert not result.full_coverage
