"""Fachada que combina los tres conectores para que la UI no dependa de sus detalles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opgg.params import Queue, Tier

from lol_consultor import config
from lol_consultor.cache import TTLCache
from lol_consultor.connectors.ddragon import DDragonConnector
from lol_consultor.connectors.fandom_wiki import FandomWikiConnector
from lol_consultor.connectors.opgg_meta import OpggMetaConnector
from lol_consultor.models import ChampionMeta


@dataclass(frozen=True)
class ChampionDetail:
    data: dict[str, Any]  # JSON completo de Data Dragon (spells, passive, stats, tips...)
    meta: ChampionMeta | None  # tier/counters de op.gg, None si no disponible
    patch_history: str | None  # texto plano, None si no disponible


class LoLService:
    def __init__(
        self,
        lang: str = config.LANG,
        cache_dir: str | Path = config.CACHE_DIR,
        timeout: int = config.HTTP_TIMEOUT,
    ) -> None:
        self.ddragon = DDragonConnector(lang=lang, cache_dir=cache_dir, timeout=timeout)
        ttl_cache = TTLCache(Path(cache_dir) / "_ttl")
        self.wiki = FandomWikiConnector(ttl_cache, config.WIKI_CACHE_TTL, timeout=timeout)
        self.opgg = OpggMetaConnector(ttl_cache, config.OPGG_CACHE_TTL)

    def check_for_new_patch(self) -> bool:
        """True si Data Dragon publicó un parche nuevo desde la última consulta."""
        return self.ddragon.check_for_new_patch()

    def champion_list(self) -> list[dict[str, Any]]:
        """Campeones ordenados alfabéticamente, con sus datos básicos."""
        champs = self.ddragon.champions()
        return sorted(champs.values(), key=lambda c: c["name"])

    def champions_by_key(self) -> dict[int, dict[str, Any]]:
        """Índice numérico ('key' de Data Dragon) -> datos básicos del campeón."""
        return {int(c["key"]): c for c in self.ddragon.champions().values()}

    def champion_detail(
        self,
        champion_id: str,
        tier: Tier = Tier.EMERALD_PLUS,
        queue: Queue = Queue.SOLO,
    ) -> ChampionDetail:
        data = self.ddragon.champion(champion_id)
        meta = self.opgg.champion_meta(int(data["key"]), tier=tier, queue=queue)
        patch_history = self.wiki.champion_patch_history(data["name"])
        return ChampionDetail(data=data, meta=meta, patch_history=patch_history)

    def items(self) -> dict[str, Any]:
        return self.ddragon.items()

    def legendary_items(self) -> list[dict[str, Any]]:
        """Ítems completos (>=2500 oro, sin upgrade posterior)."""
        return sorted(
            (
                item
                for item in self.ddragon.items().values()
                if item.get("gold", {}).get("total", 0) >= 2500 and not item.get("into")
            ),
            key=lambda i: -i["gold"]["total"],
        )

    def rune_trees(self) -> list[dict[str, Any]]:
        return self.ddragon.runes()
