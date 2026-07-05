from __future__ import annotations

from lol_consultor.winrates import (
    MIN_GAMES_FOR_DISPLAY,
    WinrateStore,
    collect_winrates,
)


def _participant(win: bool, items: list[int], keystone: int = 8112):
    p = {"win": win, "perks": {"styles": [
        {"description": "primaryStyle", "selections": [{"perk": keystone}]},
        {"description": "subStyle", "selections": [{"perk": 8347}]},
    ]}}
    for slot in range(6):
        p[f"item{slot}"] = items[slot] if slot < len(items) else 0
    p["item6"] = 3364  # trinket: no debe contarse
    return p


def _match(match_id: str, participants: list[dict]):
    return {"metadata": {"matchId": match_id}, "info": {"participants": participants}}


class _FakeRiot:
    def __init__(self, matches: list[dict]):
        self._matches = {m["metadata"]["matchId"]: m for m in matches}

    def challenger_puuids(self, max_players: int):
        return ["puuid-1"]

    def match_ids(self, puuid: str, count: int):
        return list(self._matches.keys())

    def match(self, match_id: str):
        return self._matches[match_id]


def test_collect_aggregates_items_and_keystones(tmp_path):
    matches = [
        _match("LA1_1", [
            _participant(True, items=[3031, 3006]),
            _participant(False, items=[3157]),
        ]),
    ]
    store = WinrateStore(tmp_path / "wr.json")

    report = collect_winrates(_FakeRiot(matches), store, max_matches=10)

    assert report.matches_processed == 1
    assert report.participants == 2
    assert store._data["items"]["3031"] == [1, 1]  # aparicion ganadora
    assert store._data["items"]["3157"] == [1, 0]  # aparicion perdedora
    assert "3364" not in store._data["items"]  # trinket excluido
    assert store._data["keystones"]["8112"] == [2, 1]


def test_collect_skips_already_seen_matches(tmp_path):
    matches = [_match("LA1_1", [_participant(True, items=[3031])])]
    store = WinrateStore(tmp_path / "wr.json")

    collect_winrates(_FakeRiot(matches), store, max_matches=10)
    report2 = collect_winrates(_FakeRiot(matches), store, max_matches=10)

    assert report2.matches_processed == 0
    assert report2.matches_skipped == 1
    assert store._data["items"]["3031"] == [1, 1]  # no se duplico


def test_store_persists_and_reloads(tmp_path):
    path = tmp_path / "wr.json"
    store = WinrateStore(path)
    for _ in range(MIN_GAMES_FOR_DISPLAY):
        store.record("items", 3031, won=True)
    store.save()

    reloaded = WinrateStore(path)

    assert reloaded.item_winrate(3031) == (100.0, MIN_GAMES_FOR_DISPLAY)


def test_winrate_hidden_below_min_sample(tmp_path):
    store = WinrateStore(tmp_path / "wr.json")
    for _ in range(MIN_GAMES_FOR_DISPLAY - 1):
        store.record("items", 3031, won=True)

    assert store.item_winrate(3031) is None  # muestra insuficiente


def test_collect_handles_ladder_failure(tmp_path):
    class _BrokenRiot:
        def challenger_puuids(self, max_players: int):
            raise ConnectionError("403 key expirada")

    store = WinrateStore(tmp_path / "wr.json")
    report = collect_winrates(_BrokenRiot(), store, max_matches=10)

    assert report.matches_processed == 0
    assert report.errors
