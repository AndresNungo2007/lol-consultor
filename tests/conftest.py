from __future__ import annotations

import pytest

SAMPLE_VERSION = "14.20.1"

SAMPLE_CHAMPION_LIST = {
    "data": {
        "Ahri": {
            "id": "Ahri",
            "key": "103",
            "name": "Ahri",
            "title": "the Nine-Tailed Fox",
            "tags": ["Mage", "Assassin"],
            "info": {"attack": 3, "defense": 4, "magic": 8, "difficulty": 5},
            "image": {"full": "Ahri.png"},
        }
    }
}

SAMPLE_CHAMPION_DETAIL = {
    "data": {
        "Ahri": {
            **SAMPLE_CHAMPION_LIST["data"]["Ahri"],
            "blurb": "Ahri es una vastaya mágica.",
            "lore": "Historia larga de Ahri.",
            "allytips": ["Usa Hechizar para preparar combos."],
            "enemytips": ["Espera a que gaste su definitiva."],
            "passive": {
                "name": "Robo de esencia",
                "description": "Descripción de la pasiva.",
                "image": {"full": "Ahri_Passive.png"},
            },
            "spells": [
                {
                    "name": "Orbe del engaño",
                    "tooltip": "Inflige daño.",
                    "cooldownBurn": "7",
                    "image": {"full": "AhriOrbofDeception.png"},
                }
            ],
            "stats": {"hp": 590},
        }
    }
}

SAMPLE_ITEMS = {
    "data": {
        "3089": {
            "name": "Filo mortal",
            "description": "<stats>Aumenta el poder de habilidad.</stats>",
            "gold": {"total": 3200},
            "tags": ["SpellDamage"],
            "image": {"full": "3089.png"},
        }
    }
}

SAMPLE_RUNES = [
    {
        "id": 8100,
        "name": "Dominación",
        "icon": "perk-images/Styles/7200_Domination.png",
        "slots": [
            {
                "runes": [
                    {
                        "id": 8112,
                        "name": "Electrocutar",
                        "shortDesc": "Golpea tres veces para infligir daño extra.",
                        "icon": "perk-images/Styles/Domination/Electrocute/Electrocute.png",
                    }
                ]
            }
        ],
    }
]


@pytest.fixture
def sample_version() -> str:
    return SAMPLE_VERSION


@pytest.fixture
def sample_champion_list() -> dict:
    return SAMPLE_CHAMPION_LIST


@pytest.fixture
def sample_champion_detail() -> dict:
    return SAMPLE_CHAMPION_DETAIL


@pytest.fixture
def sample_items() -> dict:
    return SAMPLE_ITEMS


@pytest.fixture
def sample_runes() -> list:
    return SAMPLE_RUNES


class StubDDragon:
    """Sustituye a DDragonConnector en tests: mismas URLs, sin red."""

    def __init__(self, version: str) -> None:
        self.version = version

    def champion(self, champion_id: str) -> dict:
        return SAMPLE_CHAMPION_DETAIL["data"][champion_id]

    def champion_square_url(self, full: str) -> str:
        return f"http://x/{full}"

    def splash_url(self, champion_id: str, skin_num: int = 0) -> str:
        return f"http://x/{champion_id}_{skin_num}.jpg"

    def passive_icon_url(self, full: str) -> str:
        return f"http://x/passive/{full}"

    def spell_icon_url(self, full: str) -> str:
        return f"http://x/spell/{full}"

    def item_icon_url(self, item_id: str) -> str:
        return f"http://x/item/{item_id}.png"

    def rune_icon_url(self, icon_path: str) -> str:
        return f"http://x/{icon_path}"


class _StubOpgg:
    def champion_meta(self, champion_key: int, **_kwargs):
        from lol_consultor.models import ChampionMeta, CounterEntry, PositionMeta

        counters = [CounterEntry(champion_id=166, games=2312, wins=1110)]
        position = PositionMeta(
            position="MID", play_rate=8.8, win_rate=51.0, ban_rate=3.3, counters=counters
        )
        return ChampionMeta(champion_id=champion_key, positions=[position])


class _StubWiki:
    def champion_patch_history(self, _name: str) -> str:
        return "V14.20: cambio de balance"

    def champion_abilities(self, _name: str) -> str:
        return "Scoring a takedown resets the cooldown."


class _StubWinrates:
    total_matches = 0

    def item_winrate(self, _item_id):
        return None

    def keystone_winrate(self, _perk_id):
        return None

    def winrate_any(self, _kind, _key):
        return None

    def games(self, _kind, _key):
        return 0

    def smoothed(self, _kind, _key, prior=0.5, k=10):
        return prior

    def keys_for_prefix(self, _kind, _prefix):
        return []


class StubService:
    """Sustituye a LoLService en tests: misma interfaz, sin red."""

    def __init__(
        self, champion_list: dict, champion_detail: dict, items: dict, runes: list, version: str
    ) -> None:
        self._champion_list = champion_list
        self._champion_detail = champion_detail
        self._items = items
        self._runes = runes
        self.ddragon = StubDDragon(version)
        self.ddragon_en = StubDDragon(version)
        self.opgg = _StubOpgg()
        self.wiki = _StubWiki()
        self.winrates = _StubWinrates()

    def champion_list(self):
        return list(self._champion_list["data"].values())

    def champions_by_key(self):
        return {int(c["key"]): c for c in self._champion_list["data"].values()}

    def find_champion(self, nombre: str):
        needle = nombre.strip().lower()
        for c in self.champion_list():
            if c["id"].lower() == needle or c["name"].lower() == needle:
                return c
        for c in self.champion_list():
            if needle in c["name"].lower() or needle in c["id"].lower():
                return c
        return None

    def english_name(self, champion_id: str) -> str:
        return champion_id

    def champion_detail(self, champion_id, **_kwargs):
        from lol_consultor.models import ChampionMeta, CounterEntry, PositionMeta
        from lol_consultor.service import ChampionDetail

        data = self._champion_detail["data"][champion_id]
        counters = [CounterEntry(champion_id=166, games=2312, wins=1110)]
        position = PositionMeta(
            position="MID", play_rate=8.8, win_rate=51.0, ban_rate=3.3, counters=counters
        )
        meta = ChampionMeta(champion_id=103, positions=[position])
        return ChampionDetail(
            data=data,
            meta=meta,
            patch_history="V14.20: cambio de balance",
            wiki_abilities="Scoring a takedown resets the cooldown.",
        )

    def legendary_items(self):
        return list(self._items["data"].values())

    def rune_trees(self):
        return self._runes

    def check_for_new_patch(self):
        return False


@pytest.fixture
def stub_service(
    sample_champion_list, sample_champion_detail, sample_items, sample_runes, sample_version
):
    return StubService(
        sample_champion_list, sample_champion_detail, sample_items, sample_runes, sample_version
    )


@pytest.fixture
def stub_assistant(stub_service):
    """LoLAssistant con cliente Ollama falso (sin red), listo para usar en la UI."""
    from types import SimpleNamespace

    from lol_consultor.assistant import LoLAssistant

    class _FakeClient:
        def list(self):
            return SimpleNamespace(models=[SimpleNamespace(model="qwen3:8b")])

        def chat(self, model, messages, tools, think):
            return SimpleNamespace(
                message=SimpleNamespace(content="respuesta de prueba", tool_calls=None)
            )

    return LoLAssistant(stub_service, model="qwen3:8b", client=_FakeClient())
