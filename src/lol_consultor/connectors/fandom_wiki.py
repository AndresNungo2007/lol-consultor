"""
Conector de leagueoflegends.fandom.com vía su MediaWiki API pública
(api.php), diseñada para consumo programático -> no es scraping de HTML.

Data Dragon ya cubre lore/blurb/allytips/enemytips de forma oficial (ver
connectors/ddragon.py), así que este conector se enfoca en lo que Riot NO
publica: el historial de cambios de balance por campeón ("Patch history"),
útil para entender cómo evolucionó su estilo de juego reciente.

Nota técnica: esta wiki no tiene instalada la extensión TextExtracts
(`prop=extracts` falla), y el wikitext crudo de sus secciones son en su
mayoría transclusiones de plantillas/Lua vacías de contenido legible. Por
eso se usa `action=parse&prop=text` (HTML ya renderizado) y se limpia con un
stripper propio, en vez de intentar parsear wikitext.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable
from typing import Any

import requests

from lol_consultor.cache import TTLCache

WIKI_API = "https://leagueoflegends.fandom.com/api.php"

_PATCH_HISTORY_HEADINGS = {"patch history"}


def _strip_html(raw_html: str) -> str:
    """HTML renderizado por MediaWiki -> texto plano legible."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL)
    text = re.sub(r'<span class="mw-editsection">.*?</span></span>', "", text, flags=re.DOTALL)
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"<(h[1-6]|dt)[^>]*>", "\n\n", text)
    text = re.sub(r"<(dd|/p|br)[^>]*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class FandomWikiConnector:
    def __init__(self, cache: TTLCache, ttl_seconds: int, timeout: int = 20) -> None:
        self.cache = cache
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "format": "json"}
        r = self.session.get(WIKI_API, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def champion_page_title(self, champion_display_name: str) -> str:
        """La wiki aloja varios juegos de Riot; las páginas de campeón usan '/LoL'."""
        return f"{champion_display_name}/LoL"

    def page_section_text(self, title: str, heading_candidates: Iterable[str]) -> str | None:
        """
        Busca la primera sección cuyo título (case-insensitive) esté en
        `heading_candidates` y devuelve su texto renderizado y limpio.
        None si la página o ninguna de esas secciones existen.
        """
        candidates = {h.strip().lower() for h in heading_candidates}

        def fetch() -> str | None:
            sections = self._get({"action": "parse", "page": title, "prop": "sections"})
            if "error" in sections:
                return None
            section_index = None
            for section in sections.get("parse", {}).get("sections", []):
                if section.get("line", "").strip().lower() in candidates:
                    section_index = section["index"]
                    break
            if section_index is None:
                return None

            content = self._get(
                {
                    "action": "parse",
                    "page": title,
                    "section": section_index,
                    "prop": "text",
                }
            )
            raw_html = content.get("parse", {}).get("text", {}).get("*")
            return _strip_html(raw_html) if raw_html else None

        cache_key = f"wiki_section_{title}_{'_'.join(sorted(candidates))}"
        return self.cache.get_or_set(cache_key, self.ttl_seconds, fetch)

    def champion_patch_history(self, champion_display_name: str) -> str | None:
        """Historial reciente de cambios de balance del campeón, en texto plano."""
        title = self.champion_page_title(champion_display_name)
        return self.page_section_text(title, _PATCH_HISTORY_HEADINGS)
