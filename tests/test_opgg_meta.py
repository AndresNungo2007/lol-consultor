from __future__ import annotations

from opgg.params import Queue, Tier

from lol_consultor.cache import TTLCache
from lol_consultor.connectors.opgg_meta import OpggMetaConnector

FIXTURE_STATS = [
    {
        "id": 103,
        "positions": [
            {
                "name": "MID",
                "stats": {"pick_rate": 0.088, "win_rate": 0.51, "ban_rate": 0.033},
                "counters": [
                    {"champion_id": 166, "play": 2312, "win": 1110},  # ~48.0%
                    {"champion_id": 91, "play": 1000, "win": 550},  # 55.0%
                ],
            }
        ],
    }
]


class _FakeOpggClient:
    def __init__(self, stats=None, error: Exception | None = None):
        self._stats = stats
        self._error = error

    def get_champion_stats(self, tier, region, queue_type):
        if self._error:
            raise self._error
        return self._stats


def _connector(tmp_path) -> OpggMetaConnector:
    return OpggMetaConnector(TTLCache(tmp_path), ttl_seconds=3600)


def test_champion_meta_parses_and_sorts_counters_by_win_rate(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "lol_consultor.connectors.opgg_meta.OPGG",
        lambda: _FakeOpggClient(stats=FIXTURE_STATS),
    )

    meta = _connector(tmp_path).champion_meta(103, tier=Tier.EMERALD_PLUS, queue=Queue.SOLO)

    assert meta is not None
    assert meta.champion_id == 103
    position = meta.positions[0]
    assert position.position == "MID"
    assert position.win_rate == 51.0
    # ordenado por winrate ascendente: el counter más fuerte (menor winrate) primero
    assert [c.champion_id for c in position.counters] == [166, 91]
    assert position.counters[0].win_rate == 48.0


def test_champion_meta_returns_none_for_unknown_champion(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "lol_consultor.connectors.opgg_meta.OPGG",
        lambda: _FakeOpggClient(stats=FIXTURE_STATS),
    )

    meta = _connector(tmp_path).champion_meta(999999)

    assert meta is None


def test_champion_meta_degrades_gracefully_when_opgg_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "lol_consultor.connectors.opgg_meta.OPGG",
        lambda: _FakeOpggClient(error=RuntimeError("op.gg no disponible")),
    )

    meta = _connector(tmp_path).champion_meta(103)

    assert meta is None  # no debe propagar la excepción
