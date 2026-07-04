from __future__ import annotations

from lol_consultor.gamewiki import MECANICAS, buscar_mecanica, categorias


def test_mecanicas_have_unique_ids_and_content():
    ids = [m.id for m in MECANICAS]
    assert len(ids) == len(set(ids))
    assert all(len(m.texto) > 100 for m in MECANICAS)


def test_buscar_por_titulo_exacto_y_parcial():
    assert buscar_mecanica("Armadura").id == "armadura"
    assert buscar_mecanica("armadura").id == "armadura"
    assert buscar_mecanica("tenacidad").id == "tenacidad"
    assert buscar_mecanica("omnivamp").id == "omnivampirismo"


def test_buscar_por_contenido():
    # 'heridas graves' aparece en el texto de robo de vida y tiene su propia entrada
    assert buscar_mecanica("antisanación") is not None


def test_buscar_no_encontrada():
    assert buscar_mecanica("mecanica inventada xyz") is None
    assert buscar_mecanica("") is None


def test_categorias_sin_duplicados():
    cats = categorias()
    assert len(cats) == len(set(cats))
    assert "Defensa" in cats
