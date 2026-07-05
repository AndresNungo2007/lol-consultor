from __future__ import annotations

from lol_consultor.probability import suggest_items, win_probability
from lol_consultor.winrates import WinrateStore


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
