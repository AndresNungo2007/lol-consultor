from __future__ import annotations

from lol_consultor.winrates import (
    MIN_GAMES_FOR_DISPLAY,
    WinrateStore,
    collect_winrates,
)


def _participant(
    win: bool,
    items: list[int],
    keystone: int = 8112,
    champion: int = 234,
    team: int = 100,
):
    p = {
        "win": win,
        "championId": champion,
        "teamId": team,
        "perks": {"styles": [
            {"description": "primaryStyle", "selections": [
                {"perk": keystone}, {"perk": 8126},
            ]},
            {"description": "subStyle", "selections": [{"perk": 8347}]},
        ]},
    }
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

    def match_ids(self, puuid: str, count: int, start_time=None, end_time=None):
        return list(self._matches.keys())

    def match(self, match_id: str):
        return self._matches[match_id]


def test_collect_aggregates_all_dimensions(tmp_path):
    matches = [
        _match("LA1_1", [
            _participant(True, items=[3031, 3006], champion=234, team=100),
            _participant(False, items=[3157], champion=157, team=200, keystone=8005),
        ]),
    ]
    store = WinrateStore(tmp_path / "wr.json")

    report = collect_winrates(_FakeRiot(matches), store, max_matches=10)

    assert report.matches_processed == 1
    assert store._data["items"]["3031"] == [1, 1]
    assert "3364" not in store._data["items"]  # trinket excluido
    # dimensiones nuevas
    assert store._data["champions"]["234"] == [1, 1]
    assert store._data["champions"]["157"] == [1, 0]
    assert store._data["matchups"]["234_vs_157"] == [1, 1]
    assert store._data["matchups"]["157_vs_234"] == [1, 0]
    assert store._data["item_vs"]["3031_vs_157"] == [1, 1]
    assert store._data["champ_items"]["234_3031"] == [1, 1]
    assert store._data["champ_keystones"]["234_8112"] == [1, 1]
    assert store._data["keystone_vs"]["8112_vs_157"] == [1, 1]
    # todas las runas seleccionadas cuentan en 'runes'
    assert store._data["runes"]["8347"] == [2, 1]


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


def test_store_loads_legacy_schema_without_new_keys(tmp_path):
    path = tmp_path / "wr.json"
    path.write_text('{"items": {"3031": [40, 22]}, "keystones": {}, "seen_matches": ["LA1_1"]}')

    store = WinrateStore(path)

    assert store.item_winrate(3031) == (55.0, 40)
    assert store._data["matchups"] == {}  # clave nueva presente aunque el archivo sea viejo


def test_winrate_any_vs_thresholded(tmp_path):
    store = WinrateStore(tmp_path / "wr.json")
    for _ in range(5):
        store.record("items", 3031, won=True)

    assert store.item_winrate(3031) is None  # bajo el umbral
    assert store.winrate_any("items", 3031) == (100.0, 5)
    assert store.winrate_any("items", 9999) is None


def test_smoothed_pulls_small_samples_to_prior(tmp_path):
    store = WinrateStore(tmp_path / "wr.json")
    store.record("items", 3031, won=True)  # 1 partida, 100%

    smoothed = store.smoothed("items", 3031, prior=0.5, k=10)

    assert 0.5 < smoothed < 0.6  # lejos del 100% crudo


def test_sync_from_url_adopts_bigger_remote(tmp_path):
    import responses as responses_lib

    store = WinrateStore(tmp_path / "wr.json")
    store.record("items", 3031, won=True)
    store.mark_seen("LA1_1")
    remote = {
        "items": {"3031": [50, 30]},
        "keystones": {},
        "seen_matches": [f"LA1_{i}" for i in range(40)],
    }
    with responses_lib.RequestsMock() as rsps:
        rsps.add(responses_lib.GET, "https://example.com/winrates.json", json=remote)

        updated = store.sync_from_url("https://example.com/winrates.json")

    assert updated
    assert store.total_matches == 40
    assert store.item_winrate(3031) == (60.0, 50)
    assert store._data["matchups"] == {}  # esquema completo aunque el remoto sea viejo


def test_sync_from_url_ignores_smaller_remote(tmp_path):
    import responses as responses_lib

    store = WinrateStore(tmp_path / "wr.json")
    for i in range(10):
        store.mark_seen(f"LA1_{i}")
    remote = {"items": {}, "keystones": {}, "seen_matches": ["LA1_0"]}
    with responses_lib.RequestsMock() as rsps:
        rsps.add(responses_lib.GET, "https://example.com/winrates.json", json=remote)

        updated = store.sync_from_url("https://example.com/winrates.json")

    assert not updated
    assert store.total_matches == 10


def test_collect_handles_ladder_failure(tmp_path):
    class _BrokenRiot:
        def challenger_puuids(self, max_players: int):
            raise ConnectionError("403 key expirada")

    store = WinrateStore(tmp_path / "wr.json")
    report = collect_winrates(_BrokenRiot(), store, max_matches=10)

    assert report.matches_processed == 0
    assert report.errors
