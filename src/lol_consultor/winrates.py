"""
Winrates de ítems y runas calculados a partir de partidas reales (Riot API).

Metodología: por cada participante de cada partida ranked recolectada se
registra su build final (slots de ítems) y su runa clave (keystone), junto
con si ganó. El winrate de un ítem/runa es victorias/apariciones.

Sesgo conocido (se comunica en la UI): el equipo que va ganando completa más
ítems, así que los winrates por ítem tienden a estar inflados respecto al
50%. Sirven para COMPARAR ítems entre sí, no como probabilidad causal.

Los agregados se persisten en JSON dentro del cache, así crecen con cada
ejecución del recolector (scripts/collect_winrates.py).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from lol_consultor.connectors.riot_api import RiotApiConnector

logger = logging.getLogger(__name__)

_MAX_SEEN_MATCHES = 50_000
MIN_GAMES_FOR_DISPLAY = 30  # bajo esto, el winrate es ruido


@dataclass
class CollectReport:
    matches_processed: int = 0
    matches_skipped: int = 0
    participants: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        text = (
            f"Partidas nuevas: {self.matches_processed} "
            f"(omitidas por repetidas: {self.matches_skipped}), "
            f"participantes agregados: {self.participants}"
        )
        if self.errors:
            text += f", errores: {len(self.errors)}"
        return text


class WinrateStore:
    """Agregados persistentes: item_id/keystone_id -> [apariciones, victorias]."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Archivo de winrates corrupto, se reinicia")
        return {"items": {}, "keystones": {}, "seen_matches": []}

    def save(self) -> None:
        self._data["seen_matches"] = self._data["seen_matches"][-_MAX_SEEN_MATCHES:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data), encoding="utf-8")

    # ---------- registro ----------

    def is_seen(self, match_id: str) -> bool:
        return match_id in self._data["seen_matches"]

    def mark_seen(self, match_id: str) -> None:
        self._data["seen_matches"].append(match_id)

    def record(self, kind: str, entity_id: int, won: bool) -> None:
        bucket = self._data[kind].setdefault(str(entity_id), [0, 0])
        bucket[0] += 1
        bucket[1] += int(won)

    # ---------- consulta ----------

    def winrate(self, kind: str, entity_id: int | str) -> tuple[float, int] | None:
        """(winrate 0-100, partidas) o None si no hay muestra suficiente."""
        bucket = self._data.get(kind, {}).get(str(entity_id))
        if not bucket or bucket[0] < MIN_GAMES_FOR_DISPLAY:
            return None
        games, wins = bucket
        return round(100 * wins / games, 1), games

    def item_winrate(self, item_id: int | str) -> tuple[float, int] | None:
        return self.winrate("items", item_id)

    def keystone_winrate(self, perk_id: int | str) -> tuple[float, int] | None:
        return self.winrate("keystones", perk_id)

    @property
    def total_matches(self) -> int:
        return len(self._data["seen_matches"])

    def sync_from_url(self, url: str, timeout: int = 30) -> bool:
        """
        Descarga el agregado publicado (rama winrates-data del repo) y lo
        adopta si trae MÁS partidas que el local. True si se actualizó.
        """
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        remote = response.json()
        if not isinstance(remote, dict) or "items" not in remote or "seen_matches" not in remote:
            raise ValueError("El agregado remoto no tiene el formato esperado")
        if len(remote["seen_matches"]) <= self.total_matches:
            return False
        self._data = remote
        self.save()
        return True


def _participant_items(participant: dict[str, Any]) -> set[int]:
    """Ítems únicos del build final (slots item0-item5; item6 es el trinket)."""
    return {
        item_id
        for slot in range(6)
        if (item_id := participant.get(f"item{slot}", 0))
    }


def _participant_keystone(participant: dict[str, Any]) -> int | None:
    styles = participant.get("perks", {}).get("styles", [])
    for style in styles:
        if style.get("description") == "primaryStyle":
            selections = style.get("selections", [])
            if selections:
                return selections[0].get("perk")
    return None


def collect_winrates(
    riot: RiotApiConnector,
    store: WinrateStore,
    max_matches: int = 100,
    players: int = 15,
    matches_per_player: int = 10,
) -> CollectReport:
    """
    Recolecta partidas del ladder y agrega ítems/keystones al store.
    Con la key de desarrollo (~45 req/min con throttle), 100 partidas
    tardan unos 3-4 minutos.
    """
    report = CollectReport()
    try:
        puuids = riot.challenger_puuids(max_players=players)
    except Exception as exc:
        report.errors.append(f"ladder: {exc}")
        return report

    pending: list[str] = []
    for puuid in puuids:
        if len(pending) >= max_matches * 2:
            break
        try:
            pending.extend(riot.match_ids(puuid, count=matches_per_player))
        except Exception as exc:
            report.errors.append(f"match_ids: {exc}")

    for match_id in dict.fromkeys(pending):  # dedupe conservando orden
        if report.matches_processed >= max_matches:
            break
        if store.is_seen(match_id):
            report.matches_skipped += 1
            continue
        try:
            match = riot.match(match_id)
        except Exception as exc:
            report.errors.append(f"{match_id}: {exc}")
            continue

        participants = match.get("info", {}).get("participants", [])
        for participant in participants:
            won = bool(participant.get("win"))
            for item_id in _participant_items(participant):
                store.record("items", item_id, won)
            keystone = _participant_keystone(participant)
            if keystone:
                store.record("keystones", keystone, won)
            report.participants += 1

        store.mark_seen(match_id)
        report.matches_processed += 1

    store.save()
    logger.info("Recoleccion terminada: %s", report.summary())
    return report
