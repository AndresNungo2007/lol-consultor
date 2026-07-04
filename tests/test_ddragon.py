from __future__ import annotations

import responses

from lol_consultor.connectors.ddragon import CDRAGON, DDRAGON, DDragonConnector


@responses.activate
def test_champions_downloads_and_caches(tmp_path, sample_version, sample_champion_list):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    connector = DDragonConnector(lang="es_ES", cache_dir=tmp_path)

    responses.add(
        responses.GET,
        f"{DDRAGON}/cdn/{sample_version}/data/es_ES/champion.json",
        json=sample_champion_list,
    )

    champs = connector.champions()
    assert "Ahri" in champs
    assert champs["Ahri"]["key"] == "103"

    # segunda llamada debe venir del cache en disco, no de un segundo request HTTP
    responses.reset()
    champs_again = connector.champions()
    assert champs_again["Ahri"]["name"] == "Ahri"


@responses.activate
def test_champion_detail(tmp_path, sample_version, sample_champion_detail):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    connector = DDragonConnector(lang="es_ES", cache_dir=tmp_path)

    responses.add(
        responses.GET,
        f"{DDRAGON}/cdn/{sample_version}/data/es_ES/champion/Ahri.json",
        json=sample_champion_detail,
    )

    ahri = connector.champion("Ahri")
    assert ahri["passive"]["name"] == "Robo de esencia"
    assert ahri["spells"][0]["name"] == "Orbe del engaño"


@responses.activate
def test_items(tmp_path, sample_version, sample_items):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    connector = DDragonConnector(lang="es_ES", cache_dir=tmp_path)

    responses.add(
        responses.GET, f"{DDRAGON}/cdn/{sample_version}/data/es_ES/item.json", json=sample_items
    )
    items = connector.items()
    assert items["3089"]["gold"]["total"] == 3200


@responses.activate
def test_runes(tmp_path, sample_version, sample_runes):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    connector = DDragonConnector(lang="es_ES", cache_dir=tmp_path)

    responses.add(
        responses.GET,
        f"{DDRAGON}/cdn/{sample_version}/data/es_ES/runesReforged.json",
        json=sample_runes,
    )
    runes = connector.runes()
    assert runes[0]["name"] == "Dominación"


@responses.activate
def test_check_for_new_patch_detects_change(tmp_path, sample_version):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    connector = DDragonConnector(lang="es_ES", cache_dir=tmp_path)
    assert connector.version == sample_version

    responses.replace(responses.GET, f"{DDRAGON}/api/versions.json", json=["14.21.1"])
    changed = connector.check_for_new_patch()

    assert changed is True
    assert connector.version == "14.21.1"


@responses.activate
def test_image_url_helpers(tmp_path, sample_version):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    connector = DDragonConnector(lang="es_ES", cache_dir=tmp_path)

    cdn = f"{DDRAGON}/cdn/{sample_version}"
    assert connector.champion_square_url("Ahri.png") == f"{cdn}/img/champion/Ahri.png"
    assert connector.item_icon_url("3089") == f"{cdn}/img/item/3089.png"
    assert connector.passive_icon_url("Ahri_Passive.png") == f"{cdn}/img/passive/Ahri_Passive.png"
    assert connector.spell_icon_url("Spell.png") == f"{cdn}/img/spell/Spell.png"
    assert connector.splash_url("Ahri", 1) == f"{DDRAGON}/cdn/img/champion/splash/Ahri_1.jpg"


@responses.activate
def test_champion_abilities_cdragon(tmp_path, sample_version):
    responses.add(responses.GET, f"{DDRAGON}/api/versions.json", json=[sample_version])
    connector = DDragonConnector(lang="es_ES", cache_dir=tmp_path)

    url = f"{CDRAGON}/latest/plugins/rcp-be-lol-game-data/global/default/v1/champions/103.json"
    responses.add(responses.GET, url, json={"id": 103, "name": "Ahri"})

    data = connector.champion_abilities_cdragon(103)
    assert data["id"] == 103
