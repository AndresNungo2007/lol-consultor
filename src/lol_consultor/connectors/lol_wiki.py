"""
Conector de wiki.leagueoflegends.com (la "wikilol" oficial de la comunidad)
vía su MediaWiki API pública (api.php) -> no es scraping de HTML.

Es la fuente más precisa para el DETALLE de habilidades (resets, cifras
exactas, interacciones) y para el historial de parches al día. Nota: la
antigua wiki de Fandom quedó congelada en el parche 14.18 tras la migración
a este dominio; este conector la reemplaza.

Los títulos de página usan el nombre EN INGLÉS del campeón (ej. 'Locke',
'Nunu & Willump'); la capa de servicio resuelve el nombre inglés desde
Data Dragon en_US.

Nota técnica: el wikitext crudo son transclusiones de plantillas/Lua sin
contenido legible, por eso se usa `action=parse&prop=text` (HTML renderizado)
y se limpia con un stripper propio.
"""

from __future__ import annotations

import html
import re
import time
from collections.abc import Iterable
from typing import Any

import requests

from lol_consultor.cache import TTLCache

WIKI_API = "https://wiki.leagueoflegends.com/en-us/api.php"

_PATCH_HISTORY_HEADINGS = {"patch history"}
_ABILITIES_HEADINGS = {"abilities"}


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


class LoLWikiConnector:
    def __init__(self, cache: TTLCache, ttl_seconds: int, timeout: int = 20) -> None:
        self.cache = cache
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        # redirects=1: muchas páginas son redirecciones (ej. 'Omnivamp' ->
        # 'Vamp'); sin esto se parsea el stub "Redirect to: ..." en vez del
        # contenido real.
        params = {**params, "format": "json", "redirects": "1"}
        try:
            r = self.session.get(WIKI_API, params=params, timeout=self.timeout)
            r.raise_for_status()
        except requests.exceptions.RequestException:
            # Un solo reintento: la API de MediaWiki devuelve 200 + un campo
            # "error" para páginas inexistentes (no una excepción de red), así
            # que llegar aquí siempre es un hipo transitorio (timeout, conexión),
            # nunca "la página no existe". Sin esto, champion_detail() —que
            # consulta esta fuente en paralelo con op.gg y el historial de
            # parches— convertía cualquier lentitud momentánea en un falso
            # "detalle de la wiki no disponible" para campeones que sí lo tienen.
            time.sleep(0.5)
            r = self.session.get(WIKI_API, params=params, timeout=self.timeout)
            r.raise_for_status()
        return r.json()

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

    def page_intro(self, title: str) -> str | None:
        """Sección introductoria (lead) de una página, en texto plano."""

        def fetch() -> str | None:
            content = self._get(
                {"action": "parse", "page": title, "section": "0", "prop": "text"}
            )
            if "error" in content:
                return None
            raw_html = content.get("parse", {}).get("text", {}).get("*")
            return _strip_html(raw_html) if raw_html else None

        return self.cache.get_or_set(f"wiki_intro_{title}", self.ttl_seconds, fetch)

    def page_notes(self, title: str) -> str | None:
        """Sección 'Notes' de una página (ej. ítems: interacciones y detalles)."""
        return self.page_section_text(title, {"notes"})

    def champion_patch_history(self, champion_english_name: str) -> str | None:
        """Historial de cambios de balance del campeón, al día, en texto plano."""
        return self.page_section_text(champion_english_name, _PATCH_HISTORY_HEADINGS)

    def champion_abilities(self, champion_english_name: str) -> str | None:
        """
        Detalle completo de habilidades desde la wiki: cooldowns, costos,
        daños por nivel, resets e interacciones que Data Dragon omite.
        """
        return self.page_section_text(champion_english_name, _ABILITIES_HEADINGS)
