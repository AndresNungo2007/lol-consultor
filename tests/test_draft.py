from __future__ import annotations

from lol_consultor.draft import DraftAnalyzer
from lol_consultor.models import ChampionMeta, CounterEntry, PositionMeta

# Roster sintético: dos junglas del pool, un enemigo y aliados con perfiles marcados.
_CHAMPS = {
    "Viego": {"id": "Viego", "key": "234", "name": "Viego",
              "info": {"attack": 8, "magic": 2, "defense": 4, "difficulty": 6}},
    "Karthus": {"id": "Karthus", "key": "30", "name": "Karthus",
                "info": {"attack": 2, "magic": 10, "defense": 2, "difficulty": 7}},
    "LeeSin": {"id": "LeeSin", "key": "64", "name": "Lee Sin",
               "info": {"attack": 8, "magic": 3, "defense": 5, "difficulty": 6}},
    "Yasuo": {"id": "Yasuo", "key": "157", "name": "Yasuo",
              "info": {"attack": 8, "magic": 4, "defense": 4, "difficulty": 10}},
    "Malphite": {"id": "Malphite", "key": "54", "name": "Malphite",
                 "info": {"attack": 5, "magic": 7, "defense": 9, "difficulty": 2}},
    "Caitlyn": {"id": "Caitlyn", "key": "51", "name": "Caitlyn",
                "info": {"attack": 8, "magic": 2, "defense": 2, "difficulty": 6}},
    "Talon": {"id": "Talon", "key": "91", "name": "Talon",
              "info": {"attack": 9, "magic": 1, "defense": 3, "difficulty": 7}},
}

# Meta sintética por key: Viego fuerte pero countereado por Lee Sin;
# Lee Sin (enemigo) pierde contra Karthus.
_META = {
    234: ChampionMeta(champion_id=234, positions=[
        PositionMeta(position="JUNGLE", play_rate=10.0, win_rate=52.0, ban_rate=5.0,
                     counters=[CounterEntry(champion_id=64, games=1000, wins=460)]),  # 46% vs Lee
    ]),
    30: ChampionMeta(champion_id=30, positions=[
        PositionMeta(position="JUNGLE", play_rate=3.0, win_rate=50.0, ban_rate=1.0, counters=[]),
    ]),
    # Lee Sin gana solo el 46% contra Karthus (key 30)
    64: ChampionMeta(champion_id=64, positions=[
        PositionMeta(position="JUNGLE", play_rate=12.0, win_rate=49.0, ban_rate=8.0,
                     counters=[CounterEntry(champion_id=30, games=800, wins=368)]),
    ]),
}


class _FakeOpgg:
    def champion_meta(self, champion_key: int, **_kwargs):
        return _META.get(champion_key)


class _FakeService:
    def __init__(self):
        self.opgg = _FakeOpgg()

    def champion_list(self):
        return list(_CHAMPS.values())

    def champions_by_key(self):
        return {int(c["key"]): c for c in _CHAMPS.values()}

    def find_champion(self, nombre: str):
        needle = nombre.strip().lower()
        for c in _CHAMPS.values():
            if c["id"].lower() == needle or c["name"].lower() == needle:
                return c
        for c in _CHAMPS.values():
            if needle in c["name"].lower():
                return c
        return None


def test_counter_relationships_affect_ranking():
    analyzer = DraftAnalyzer(_FakeService())

    recs = analyzer.analyze(
        pool=["Viego", "Karthus"], role="JUNGLE", allies=[], enemies=["Lee Sin"]
    )

    by_name = {r.champion_name: r for r in recs}
    # Viego pierde vs Lee Sin -> factor de riesgo negativo presente
    assert any("Riesgo" in f.descripcion for f in by_name["Viego"].factores)
    # Karthus counterea a Lee Sin -> factor de ventaja positivo presente
    assert any("Ventaja" in f.descripcion for f in by_name["Karthus"].factores)
    # y el countereo debe poner a Karthus por encima de Viego
    assert recs[0].champion_name == "Karthus"


def test_damage_balance_rewards_ap_when_team_is_ad():
    analyzer = DraftAnalyzer(_FakeService())

    recs = analyzer.analyze(
        pool=["Viego", "Karthus"], role="JUNGLE",
        allies=["Caitlyn", "Talon", "Yasuo"],  # equipo muy AD
        enemies=[],
    )

    by_name = {r.champion_name: r for r in recs}
    karthus_balance = [f for f in by_name["Karthus"].factores if "Equilibra" in f.descripcion]
    viego_skew = [f for f in by_name["Viego"].factores if "cargado" in f.descripcion]
    assert karthus_balance and karthus_balance[0].puntos > 0
    assert viego_skew and viego_skew[0].puntos < 0


def test_frontline_bonus_when_team_lacks_tank():
    analyzer = DraftAnalyzer(_FakeService())

    # equipo sin frontline: Caitlyn y Talon (defense 2 y 3)
    recs = analyzer.analyze(
        pool=["Malphite"], role="JUNGLE", allies=["Caitlyn", "Talon"], enemies=[]
    )

    assert any("línea de frente" in f.descripcion for f in recs[0].factores)


def test_unknown_pool_champions_are_skipped():
    analyzer = DraftAnalyzer(_FakeService())

    recs = analyzer.analyze(pool=["NoExiste", "Viego"], role="JUNGLE", allies=[], enemies=[])

    assert [r.champion_name for r in recs] == ["Viego"]


def test_handles_missing_meta_gracefully():
    analyzer = DraftAnalyzer(_FakeService())

    # Malphite no tiene meta en _META -> factor informativo, sin excepción
    recs = analyzer.analyze(pool=["Malphite"], role="JUNGLE", allies=[], enemies=[])

    assert recs[0].score == 0.0
    assert any("Sin datos de meta" in f.descripcion for f in recs[0].factores)
