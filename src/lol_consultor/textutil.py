"""Limpieza de HTML embebido en textos de Data Dragon (tooltips, descripciones)."""

from __future__ import annotations

import html
import re


def strip_tags(raw: str | None) -> str:
    if not raw:
        return ""
    text = re.sub(r"\{\{.*?\}\}", "", raw)  # placeholders sin resolver de Data Dragon
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return html.unescape(text).strip()


def item_description_sections(raw: str | None) -> tuple[list[str], list[str]]:
    """
    Separa el HTML de descripción de un ítem de Data Dragon en:
      - stats: una línea por atributo (contenido de <stats>, separado por <br>)
      - resto: párrafos con pasivas/activas y otros efectos
    """
    if not raw:
        return [], []

    stats: list[str] = []
    match = re.search(r"<stats>(.*?)</stats>", raw, flags=re.DOTALL)
    if match:
        stats = [strip_tags(part) for part in re.split(r"<br\s*/?>", match.group(1))]
        stats = [s for s in stats if s]
        raw = raw.replace(match.group(0), "")

    rest = [strip_tags(part) for part in re.split(r"<br\s*/?>", raw)]
    rest = [line for line in rest if line]
    return stats, rest
