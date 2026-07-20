"""
Búsqueda de texto en las habilidades de TODOS los campeones.

Existe porque el asistente de chat no tenía ninguna herramienta para
responder preguntas del tipo "¿qué campeones tienen habilidades que hacen
X?" — y ante la falta de una tool, el LLM respondía inventando una lista
completa (nombres de habilidades incorrectos, campeones con kits que no
existen). Este módulo permite responder esas preguntas con datos reales.

Solo busca en campeones YA cacheados en disco (DDragonConnector.champion_if_
cached): recorrer los ~170 campeones con descarga en vivo tardaría minutos,
inviable dentro de un turno de chat. La cobertura se reporta siempre para
que el llamador pueda comunicarla con honestidad en vez de aparentar
integridad que no tiene.
"""

from __future__ import annotations

from dataclasses import dataclass

from lol_consultor.service import LoLService
from lol_consultor.textutil import strip_tags

_SLOTS = "QWER"


@dataclass(frozen=True)
class AbilityMatch:
    champion_name: str
    slot: str  # "Pasiva", "Q", "W", "E" o "R"
    ability_name: str
    snippet: str


@dataclass(frozen=True)
class AbilitySearchResult:
    matches: list[AbilityMatch]
    champions_checked: int
    champions_total: int

    @property
    def full_coverage(self) -> bool:
        return self.champions_checked >= self.champions_total


def search_champion_abilities(service: LoLService, pattern: str) -> AbilitySearchResult:
    """Busca `pattern` (subcadena, sin distinguir mayúsculas) en pasiva y QWER
    de cada campeón cacheado en disco."""
    needle = pattern.strip().lower()
    all_champs = service.champion_list()
    matches: list[AbilityMatch] = []
    checked = 0

    for champ in all_champs:
        data = service.ddragon.champion_if_cached(champ["id"])
        if data is None:
            continue
        checked += 1

        entries = [("Pasiva", data["passive"]["name"], data["passive"].get("description"))]
        for slot, spell in zip(_SLOTS, data.get("spells", []), strict=False):
            entries.append((slot, spell["name"], spell.get("description") or spell.get("tooltip")))

        for slot, name, raw_desc in entries:
            text = strip_tags(raw_desc)
            if needle and needle in text.lower():
                matches.append(
                    AbilityMatch(
                        champion_name=champ["name"],
                        slot=slot,
                        ability_name=name,
                        snippet=text[:220],
                    )
                )

    return AbilitySearchResult(
        matches=matches, champions_checked=checked, champions_total=len(all_champs)
    )
