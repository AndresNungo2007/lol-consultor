"""
Conector de meta/counters de League of Legends via op.gg, usando la librería
de terceros `OPGG.py` (https://github.com/ShoobyDoo/OPGG.py), que envuelve la
API interna de op.gg en vez de que este proyecto escriba scraping de HTML.

`get_champion_stats()` trae, por campeón y posición: winrate/pickrate/
banrate globales y una lista `counters` (campeones rivales con su winrate en
ese matchup) -> eso es lo que se expone aquí.

No cubre build de ítems ni página de runas recomendada: esos datos en op.gg
se cargan client-side vía su API privada tras hidratar React, no están
disponibles en ninguna librería mantenida ni endpoint documentado. Se dejan
fuera de alcance (ver connectors/ddragon.py para tips oficiales de Riot sobre
cómo jugar el campeón / contra él).

Es una dependencia de un tercero no oficial: cualquier fallo (cambio de
esquema, timeout, servicio caído) se degrada a `None` en vez de propagar la
excepción, para que el resto de la app siga funcionando.
"""

from __future__ import annotations

import logging
from typing import Any

from opgg.opgg import OPGG
from opgg.params import Queue, StatsRegion, Tier

from lol_consultor.cache import TTLCache
from lol_consultor.models import ChampionMeta, CounterEntry, PositionMeta

logger = logging.getLogger(__name__)


class OpggMetaConnector:
    def __init__(self, cache: TTLCache, ttl_seconds: int) -> None:
        self.cache = cache
        self.ttl_seconds = ttl_seconds

    def _fetch_all_stats(
        self, tier: Tier, queue: Queue, force: bool = False
    ) -> list[dict[str, Any]] | None:
        def fetch() -> list[dict[str, Any]]:
            client = OPGG()
            return client.get_champion_stats(
                tier=tier, region=StatsRegion.GLOBAL, queue_type=queue
            )

        cache_key = f"opgg_stats_{tier.value}_{queue.value}"
        try:
            return self.cache.get_or_set(cache_key, self.ttl_seconds, fetch, force=force)
        except Exception:
            logger.warning("op.gg no disponible, se omiten counters/meta", exc_info=True)
            return None

    def refresh_stats(
        self, tier: Tier = Tier.EMERALD_PLUS, queue: Queue = Queue.SOLO
    ) -> bool:
        """Fuerza la re-descarga de estadísticas. True si op.gg respondió."""
        return self._fetch_all_stats(tier, queue, force=True) is not None

    def champion_meta(
        self,
        champion_key: int,
        tier: Tier = Tier.EMERALD_PLUS,
        queue: Queue = Queue.SOLO,
    ) -> ChampionMeta | None:
        """
        champion_key: id numérico del campeón (el mismo 'key' de Data Dragon).
        None si op.gg no responde o el campeón no tiene datos para ese filtro.
        """
        all_stats = self._fetch_all_stats(tier, queue)
        if not all_stats:
            return None

        raw = next((c for c in all_stats if c.get("id") == champion_key), None)
        if raw is None:
            return None

        positions = [
            PositionMeta(
                position=pos["name"],
                play_rate=round(100 * pos["stats"].get("pick_rate", 0), 1),
                win_rate=round(100 * pos["stats"].get("win_rate", 0), 1),
                ban_rate=round(100 * pos["stats"].get("ban_rate", 0), 1),
                counters=sorted(
                    (
                        CounterEntry(
                            champion_id=c["champion_id"], games=c["play"], wins=c["win"]
                        )
                        for c in pos.get("counters", [])
                    ),
                    key=lambda c: c.win_rate,
                ),
            )
            for pos in raw.get("positions", [])
        ]
        return ChampionMeta(champion_id=champion_key, positions=positions)
