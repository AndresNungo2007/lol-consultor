from __future__ import annotations

import responses

from lol_consultor.connectors.ddragon import DDRAGON
from lol_consultor.service import LoLService

_ITEMS_WITH_VARIANTS = {
    "data": {
        # ítem base (id corto) y su variante de mapa con precio distinto:
        # debe quedarse con la base '3107' (la que Riot reporta en partidas).
        "3107": {
            "name": "Redención",
            "description": "<stats>Vida</stats>",
            "gold": {"total": 2300, "purchasable": True},
            "maps": {"11": True, "30": False},
            "from": ["3105"],
            "tags": ["Health"],
            "image": {"full": "3107.png"},
        },
        "323107": {
            "name": "Redención",
            "description": "<stats>Vida</stats>",
            "gold": {"total": 2800, "purchasable": True},  # variante más cara
            "maps": {"11": True, "30": False},
            "from": ["3105"],
            "tags": ["Health"],
            "image": {"full": "323107.png"},
        },
        # ítem final normal
        "3031": {
            "name": "Filo infinito",
            "description": "<stats>70 AD</stats>",
            "gold": {"total": 3450, "purchasable": True},
            "maps": {"11": True},
            "from": ["1038", "1018"],
            "tags": ["Damage"],
            "image": {"full": "3031.png"},
        },
        # no comprable en Grieta: debe excluirse
        "664403": {
            "name": "Espátula dorada",
            "description": "<stats>Todo</stats>",
            "gold": {"total": 2500, "purchasable": False},
            "maps": {"11": True},
            "from": ["1038"],
            "tags": [],
            "image": {"full": "664403.png"},
        },
        # componente (tiene 'into'): debe excluirse
        "1038": {
            "name": "Espadón",
            "description": "<stats>40 AD</stats>",
            "gold": {"total": 1300, "purchasable": True},
            "maps": {"11": True},
            "into": ["3031"],
            "tags": ["Damage"],
            "image": {"full": "1038.png"},
        },
        # ítem base sin componentes (raw): debe excluirse aunque cueste >=2000
        "1058": {
            "name": "Vara requiescat",
            "description": "<stats>AP</stats>",
            "gold": {"total": 2000, "purchasable": True},
            "maps": {"11": True},
            "tags": ["SpellDamage"],
            "image": {"full": "1058.png"},
        },
        # botas base (300 oro, raw sin componentes): debe excluirse
        "1001": {
            "name": "Botas",
            "description": "<stats>Movimiento</stats>",
            "gold": {"total": 300, "purchasable": True},
            "maps": {"11": True},
            "into": ["3006"],
            "tags": ["Boots"],
            "image": {"full": "1001.png"},
        },
        # botas tier 2 (con componentes y con into: evolucionan): debe incluirse
        "3006": {
            "name": "Grebas de berserker",
            "description": "<stats>Velocidad de ataque</stats>",
            "gold": {"total": 1100, "purchasable": True},
            "maps": {"11": True},
            "from": ["1001", "1042"],
            "into": ["3173"],
            "tags": ["Boots"],
            "image": {"full": "3006.png"},
        },
        # botas tier 3 evolucionadas (finales): debe incluirse
        "3173": {
            "name": "Trituradoras encadenadas",
            "description": "<stats>Velocidad de ataque</stats>",
            "gold": {"total": 1250, "purchasable": True},
            "maps": {"11": True},
            "from": ["3006"],
            "tags": ["Boots"],
            "image": {"full": "3173.png"},
        },
    }
}


@responses.activate
def test_legendary_items_prefers_base_id_and_filters(tmp_path, sample_version):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    responses.add(
        responses.GET,
        f"{DDRAGON}/cdn/{sample_version}/data/es_ES/item.json",
        json=_ITEMS_WITH_VARIANTS,
    )
    service = LoLService(lang="es_ES", cache_dir=tmp_path)

    items = service.legendary_items()

    by_name = {i["name"]: i for i in items}
    # ítems completos + botas tier 2/3; sin raw, sin componentes, sin base 300g
    assert set(by_name) == {
        "Redención",
        "Filo infinito",
        "Grebas de berserker",
        "Trituradoras encadenadas",
    }
    # la variante de mapa se descarta: se conserva el ID base '3107'
    assert by_name["Redención"]["image"]["full"] == "3107.png"
    # las botas tier 2 se muestran pese a tener 'into' (evolucionan)
    assert by_name["Grebas de berserker"]["image"]["full"] == "3006.png"
    # la base de botas de 300 oro (raw, sin 'from') no aparece
    assert "Botas" not in by_name