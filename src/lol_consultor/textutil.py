"""Limpieza mínima de HTML embebido en textos de Data Dragon (tooltips, descripciones)."""

from __future__ import annotations

import html
import re


def strip_tags(raw: str | None) -> str:
    if not raw:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", raw)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()
