from __future__ import annotations

import json

import responses

from lol_consultor.cache import TTLCache
from lol_consultor.connectors.lol_wiki import WIKI_API, LoLWikiConnector, _strip_html


def _connector(tmp_path) -> LoLWikiConnector:
    return LoLWikiConnector(TTLCache(tmp_path), ttl_seconds=3600)


def _callback_factory(sections: list[dict], text_by_index: dict[str, str]):
    def _callback(request):
        url = request.url
        if "prop=sections" in url:
            body = {"parse": {"sections": sections}}
        elif "prop=text" in url:
            section = None
            for part in url.split("&"):
                if part.startswith("section="):
                    section = part.split("=", 1)[1]
            body = {"parse": {"text": {"*": text_by_index.get(section, "")}}}
        else:
            body = {"error": "unexpected request"}
        return (200, {}, json.dumps(body))

    return _callback


@responses.activate
def test_champion_patch_history_happy_path(tmp_path):
    sections = [{"line": "Abilities", "index": "1"}, {"line": "Patch history", "index": "3"}]
    text_by_index = {"3": "<h2>Patch history</h2><ul><li>V14.20: nerf de daño</li></ul>"}
    responses.add_callback(
        responses.GET, WIKI_API, callback=_callback_factory(sections, text_by_index)
    )

    connector = _connector(tmp_path)
    result = connector.champion_patch_history("Ahri")

    assert result is not None
    assert "nerf de daño" in result


@responses.activate
def test_page_section_text_returns_none_when_heading_missing(tmp_path):
    sections = [{"line": "Abilities", "index": "1"}, {"line": "Trivia", "index": "4"}]
    responses.add_callback(responses.GET, WIKI_API, callback=_callback_factory(sections, {}))

    connector = _connector(tmp_path)
    result = connector.champion_patch_history("Ahri")

    assert result is None


@responses.activate
def test_page_section_text_returns_none_on_wiki_error(tmp_path):
    def _callback(request):
        return (200, {}, json.dumps({"error": {"code": "missingtitle"}}))

    responses.add_callback(responses.GET, WIKI_API, callback=_callback)

    connector = _connector(tmp_path)
    result = connector.page_section_text("PaginaQueNoExiste", ["Patch history"])

    assert result is None


@responses.activate
def test_champion_abilities_returns_detailed_section(tmp_path):
    sections = [{"line": "Abilities", "index": "1"}, {"line": "Patch history", "index": "3"}]
    text_by_index = {
        "1": "<p>Scoring a takedown against an enemy champion resets the cooldown.</p>"
    }
    responses.add_callback(
        responses.GET, WIKI_API, callback=_callback_factory(sections, text_by_index)
    )

    connector = _connector(tmp_path)
    result = connector.champion_abilities("Locke")

    assert result is not None
    assert "resets the cooldown" in result


def test_strip_html_removes_tags_and_editsection_links():
    raw = (
        '<h2><span class="mw-headline">Patch history</span>'
        '<span class="mw-editsection">'
        '<span class="mw-editsection-bracket">[</span>'
        '<a href="#">edit</a>'
        '<span class="mw-editsection-bracket">]</span></span></h2>'
        "<ul><li>V14.20: cambio de balance</li></ul>"
    )

    text = _strip_html(raw)

    assert "Patch history" in text
    assert "edit" not in text
    assert "- V14.20: cambio de balance" in text
