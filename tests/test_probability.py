from __future__ import annotations

from lol_consultor.probability import (
    best_matchups,
    suggest_items,
    suggest_secondary_runes,
    win_probability,
)
from lol_consultor.winrates import WinrateStore

_RUNE_TREES = [
    {
        "id": 8000,
        "name": "Precision",
        "slots": [
            {"runes": [{"id": 8005, "name": "Precision Keystone"}]},
            {"runes": [{"id": 9101, "name": "Presencia de la mente"}]},
            {"runes": [{"id": 9102, "name": "Leyenda: Alacridad"}]},
            {"runes": [{"id": 9103, "name": "Golpe de gracia"}]},
        ],
    },
    {
        "id": 8100,
        "name": "Dominación",
        "slots": [
            {"runes": [{"id": 8112, "name": "Electrocutar"}]},
            {"runes": [{"id": 9201, "name": "Triunfo cazador"}]},
        ],
    },
]


def _store_with(tmp_path, records: dict[str, dict[str, list[int]]]) -> WinrateStore:
    store = WinrateStore(tmp_path / "wr.json")
    for kind, entries in records.items():
        for key, (games, wins) in entries.items():
            for i in range(games):
                store.record(kind, key, won=i < wins)
    return store


def test_win_probability_uses_champion_base(tmp_path):
    store = _store_with(tmp_path, {"champions": {"234": [100, 60]}})

    result = win_probability(store, 234, ally_keys=[], enemy_keys=[])

    assert 55 < result.probability < 60  # cerca del 60% observado, suavizado
    assert result.champion_games == 100


def test_win_probability_without_data_tends_to_prior(tmp_path):
    store = WinrateStore(tmp_path / "wr.json")

    neutral = win_probability(store, 234, [], [])
    with_opgg = win_probability(store, 234, [], [], opgg_winrate=54.0)

    assert abs(neutral.probability - 50.0) < 1
    assert 52 < with_opgg.probability < 55  # el prior de op.gg manda sin datos propios


def test_bad_matchup_lowers_probability(tmp_path):
    store = _store_with(
        tmp_path,
        {
            "champions": {"234": [200, 100]},  # base 50%
            "matchups": {"234_vs_64": [60, 15]},  # 25% vs Lee Sin
        },
    )

    without_enemy = win_probability(store, 234, [], [])
    against_counter = win_probability(store, 234, [], [64])

    assert against_counter.probability < without_enemy.probability - 5
    assert any("Matchup" in n for n in against_counter.notes)


def test_good_duo_raises_probability(tmp_path):
    store = _store_with(
        tmp_path,
        {
            "champions": {"234": [200, 100]},
            "duos": {"103_con_234": [50, 38]},  # 76% con Ahri
        },
    )

    solo = win_probability(store, 234, [], [])
    with_ally = win_probability(store, 234, [103], [])

    assert with_ally.probability > solo.probability + 3


def test_suggest_items_ranks_by_matchup_success(tmp_path):
    store = _store_with(
        tmp_path,
        {
            "items": {"3031": [200, 100], "3153": [200, 100]},  # global 50% ambos
            "champ_items": {"234_3031": [40, 20], "234_3153": [40, 20]},  # 50% ambos
            "item_vs": {"3031_vs_157": [30, 24], "3153_vs_157": [30, 9]},  # 80% vs 30%
        },
    )
    names = {"3031": "Filo infinito", "3153": "Hoja del rey arruinado"}

    ranked = suggest_items(store, 234, enemy_keys=[157], item_names=names)

    assert [s.name for s in ranked] == ["Filo infinito", "Hoja del rey arruinado"]
    assert ranked[0].score > ranked[1].score


def test_suggest_items_requires_champion_usage(tmp_path):
    store = _store_with(tmp_path, {"items": {"3031": [100, 60]}})  # global, pero sin champ_items

    ranked = suggest_items(store, 234, enemy_keys=[], item_names={"3031": "Filo infinito"})

    assert ranked == []


def test_suggest_secondary_runes_stays_within_keystone_tree(tmp_path):
    store = _store_with(
        tmp_path,
        {
            "champ_runes": {
                "234_9101": [40, 28],  # 70%, misma rama (Precision)
                "234_9201": [40, 30],  # 75%, pero es de OTRA rama (Dominación)
            },
        },
    )
    rune_names = {
        str(r["id"]): r["name"]
        for tree in _RUNE_TREES
        for slot in tree["slots"]
        for r in slot["runes"]
    }

    ranked = suggest_secondary_runes(
        store, 234, keystone_id="8005", rune_trees=_RUNE_TREES, rune_names=rune_names
    )

    ids = [s.entity_id for s in ranked]
    assert "9201" not in ids  # de otra rama: no debe aparecer aunque tenga mejor winrate
    assert "9101" in ids


def test_suggest_secondary_runes_falls_back_to_global_without_champion_sample(tmp_path):
    store = _store_with(tmp_path, {"runes": {"9102": [50, 30]}})  # 60% global, sin champ_runes
    rune_names = {
        str(r["id"]): r["name"]
        for tree in _RUNE_TREES
        for slot in tree["slots"]
        for r in slot["runes"]
    }

    ranked = suggest_secondary_runes(
        store, 234, keystone_id="8005", rune_trees=_RUNE_TREES, rune_names=rune_names
    )

    match = next(s for s in ranked if s.entity_id == "9102")
    assert match.games == 50
    assert 55 < match.score < 65


def test_suggest_secondary_runes_unknown_keystone_returns_empty(tmp_path):
    store = WinrateStore(tmp_path / "wr.json")

    ranked = suggest_secondary_runes(
        store, 234, keystone_id="99999", rune_trees=_RUNE_TREES, rune_names={}
    )

    assert ranked == []


def test_best_matchups_sorts_descending_and_respects_min_games(tmp_path):
    store = WinrateStore(tmp_path / "wr.json")
    for i in range(10):
        store.record("matchups", "234_vs_157", won=i < 8)  # 80%, n=10
    for _ in range(2):
        store.record("matchups", "234_vs_64", won=True)  # 100%, n=2 (bajo el minimo)
    for i in range(5):
        store.record("matchups", "234_vs_99", won=i < 3)  # 60%, n=5

    ranked = best_matchups(store, 234, min_games=3)

    assert [r.champion_id for r in ranked] == [157, 99]  # 64 excluido por muestra chica
    assert ranked[0].win_rate == 80.0
    assert ranked[0].games == 10


def test_best_matchups_respects_top_limit(tmp_path):
    store = WinrateStore(tmp_path / "wr.json")
    for enemy in [1, 2, 3, 4]:
        for _ in range(5):
            store.record("matchups", f"234_vs_{enemy}", won=True)

    ranked = best_matchups(store, 234, min_games=3, top=2)

    assert len(ranked) == 2


def test_best_matchups_empty_without_data(tmp_path):
    store = WinrateStore(tmp_path / "wr.json")

    assert best_matchups(store, 234) == []
