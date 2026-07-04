from __future__ import annotations

import responses

from lol_consultor.connectors.ddragon import DDRAGON
from lol_consultor.service import LoLService

_ITEMS_WITH_VARIANTS = {
    "data": {
        # mismo ítem en Grieta (11) y Arena (30): solo debe quedar uno
        "3031": {
            "name": "Filo infinito",
            "description": "<stats>70 AD</stats>",
            "gold": {"total": 3450, "purchasable": True},
            "maps": {"11": True, "30": False},
            "tags": ["Damage"],
            "image": {"full": "3031.png"},
        },
        "223031": {
            "name": "Filo infinito",
            "description": "<stats>70 AD</stats>",
            "gold": {"total": 3450, "purchasable": True},
            "maps": {"11": False, "30": True},
            "tags": ["Damage"],
            "image": {"full": "223031.png"},
        },
        # no comprable en Grieta: debe excluirse
        "664403": {
            "name": "Espátula dorada",
            "description": "<stats>Todo</stats>",
            "gold": {"total": 2500, "purchasable": False},
            "maps": {"11": True},
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
    }
}


@responses.activate
def test_legendary_items_dedupes_map_variants(tmp_path, sample_version):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    responses.add(
        responses.GET,
        f"{DDRAGON}/cdn/{sample_version}/data/es_ES/item.json",
        json=_ITEMS_WITH_VARIANTS,
    )
    service = LoLService(lang="es_ES", cache_dir=tmp_path)

    items = service.legendary_items()

    names = [i["name"] for i in items]
    assert names == ["Filo infinito"]  # sin duplicados, sin Arena, sin componentes
