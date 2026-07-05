"""Fachada que combina los tres conectores para que la UI no dependa de sus detalles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opgg.params import Queue, Tier

from lol_consultor import config
from lol_consultor.cache import TTLCache
from lol_consultor.connectors.ddragon import DDragonConnector
from lol_consultor.connectors.lol_wiki import LoLWikiConnector
from lol_consultor.connectors.opgg_meta import OpggMetaConnector
from lol_consultor.models import ChampionMeta
from lol_consultor.winrates import WinrateStore


@dataclass(frozen=True)
class ChampionDetail:
    data: dict[str, Any]  # JSON completo de Data Dragon (spells, passive, stats, tips...)
    meta: ChampionMeta | None  # tier/counters de op.gg, None si no disponible
    patch_history: str | None  # texto plano, None si no disponible
    wiki_abilities: str | None = None  # detalle fino de habilidades (wikilol)


class LoLService:
    def __init__(
        self,
        lang: str = config.LANG,
        cache_dir: str | Path = config.CACHE_DIR,
        timeout: int = config.HTTP_TIMEOUT,
    ) -> None:
        self.ddragon = DDragonConnector(lang=lang, cache_dir=cache_dir, timeout=timeout)
        # Nombres en inglés (títulos de página de la wikilol); cache_dir propio
        # para no colisionar con los JSON del idioma principal, misma versión.
        self.ddragon_en = DDragonConnector(
            lang="en_US",
            cache_dir=Path(cache_dir) / "_en",
            timeout=timeout,
            version=self.ddragon.version,
        )
        self.ttl_cache = TTLCache(Path(cache_dir) / "_ttl")
        self.wiki = LoLWikiConnector(self.ttl_cache, config.WIKI_CACHE_TTL, timeout=timeout)
        self.opgg = OpggMetaConnector(self.ttl_cache, config.OPGG_CACHE_TTL)
        # Winrates propios calculados con la Riot API (scripts/collect_winrates.py).
        self.winrates = WinrateStore(Path(cache_dir) / "winrates.json")

    def check_for_new_patch(self) -> bool:
        """True si Data Dragon publicó un parche nuevo desde la última consulta."""
        changed = self.ddragon.check_for_new_patch()
        if changed:
            self.ddragon_en.version = self.ddragon.version
            self.ddragon_en._cache.clear()
        return changed

    def english_name(self, champion_id: str) -> str | None:
        """Nombre en inglés del campeón (título de página en la wikilol)."""
        champ = self.ddragon_en.champions().get(champion_id)
        return champ["name"] if champ else None

    def clear_meta_caches(self) -> int:
        """Invalida los caches TTL (wiki y op.gg). Devuelve cuántas entradas borró."""
        return self.ttl_cache.clear()

    def champion_list(self) -> list[dict[str, Any]]:
        """Campeones ordenados alfabéticamente, con sus datos básicos."""
        champs = self.ddragon.champions()
        return sorted(champs.values(), key=lambda c: c["name"])

    def champions_by_key(self) -> dict[int, dict[str, Any]]:
        """Índice numérico ('key' de Data Dragon) -> datos básicos del campeón."""
        return {int(c["key"]): c for c in self.ddragon.champions().values()}

    def find_champion(self, nombre: str) -> dict[str, Any] | None:
        """Busca un campeón por id o nombre, tolerante a mayúsculas y coincidencia parcial."""
        needle = nombre.strip().lower()
        if not needle:
            return None
        champs = self.champion_list()
        for c in champs:
            if c["id"].lower() == needle or c["name"].lower() == needle:
                return c
        for c in champs:
            if needle in c["name"].lower() or needle in c["id"].lower():
                return c
        return None

    def champion_detail(
        self,
        champion_id: str,
        tier: Tier = Tier.EMERALD_PLUS,
        queue: Queue = Queue.SOLO,
    ) -> ChampionDetail:
        data = self.ddragon.champion(champion_id)
        meta = self.opgg.champion_meta(int(data["key"]), tier=tier, queue=queue)
        wiki_title = self.english_name(champion_id) or data["name"]
        patch_history = self.wiki.champion_patch_history(wiki_title)
        wiki_abilities = self.wiki.champion_abilities(wiki_title)
        return ChampionDetail(
            data=data, meta=meta, patch_history=patch_history, wiki_abilities=wiki_abilities
        )

    def items(self) -> dict[str, Any]:
        return self.ddragon.items()

    def legendary_items(self) -> list[dict[str, Any]]:
        """
        Ítems completos (>=2500 oro, sin upgrade posterior) de la Grieta del
        Invocador. Data Dragon trae variantes del mismo ítem por mapa/modo
        (ARAM, Arena...) con IDs distintos: se filtra por mapa 11 y se
        deduplica por nombre para no mostrar repetidos.
        """
        candidates = sorted(
            (
                item
                for item in self.ddragon.items().values()
                if item.get("gold", {}).get("total", 0) >= 2500
                and not item.get("into")
                and item.get("maps", {}).get("11", False)
                and item.get("gold", {}).get("purchasable", True)
            ),
            key=lambda i: -i["gold"]["total"],
        )
        seen: set[str] = set()
        unique = []
        for item in candidates:
            if item["name"] not in seen:
                seen.add(item["name"])
                unique.append(item)
        return unique

    def rune_trees(self) -> list[dict[str, Any]]:
        return self.ddragon.runes()
