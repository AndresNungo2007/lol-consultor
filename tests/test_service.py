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
        # botas completas: debe excluirse por el tag Boots
        "3117": {
            "name": "Botas de movilidad",
            "description": "<stats>Movimiento</stats>",
            "gold": {"total": 2000, "purchasable": True},
            "maps": {"11": True},
            "from": ["1001"],
            "tags": ["Boots"],
            "image": {"full": "3117.png"},
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
    # solo ítems compuestos, finales, no botas, no raw, sin duplicados
    assert set(by_name) == {"Redención", "Filo infinito"}
    # la variante de mapa se descarta: se conserva el ID base '3107'
    assert by_name["Redención"]["image"]["full"] == "3107.png"