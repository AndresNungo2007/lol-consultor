"""
Winrates calculados a partir de partidas reales (Riot API).

Dimensiones agregadas (todas persistentes y acumulativas):
  - items / keystones / runes: apariciones y victorias globales
  - champions: winrate por campeón
  - matchups: "A_vs_B" -> partidas de A contra equipos con B (perspectiva de A)
  - duos: "A_con_B" -> partidas con A y B en el mismo equipo
  - item_vs / keystone_vs: "item_vs_enemigo" -> éxito del ítem/runa contra
    un campeón enemigo específico
  - champ_items / champ_keystones / champ_runes: qué compra/usa cada campeón
    (champ_runes incluye TODAS las runas seleccionadas, no solo la keystone)
    y con qué éxito

Sesgo conocido (se comunica en la UI): el equipo que va ganando completa más
ítems; los winrates sirven para COMPARAR opciones, no como causalidad.

Los agregados se persisten en JSON y crecen con cada ejecución del
recolector (scripts/collect_winrates.py o el workflow de GitHub Actions).
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

_MAX_SEEN_MATCHES = 200_000
MIN_GAMES_FOR_DISPLAY = 30  # umbral para considerar la muestra confiable

_EMPTY_SCHEMA: dict[str, Any] = {
    "items": {},
    "keystones": {},
    "runes": {},
    "champions": {},
    "matchups": {},
    "duos": {},
    "item_vs": {},
    "keystone_vs": {},
    "champ_items": {},
    "champ_keystones": {},
    "champ_runes": {},
    "seen_matches": [],
}


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
    """Agregados persistentes: clave -> [apariciones, victorias]."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        data = {k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in _EMPTY_SCHEMA.items()}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                data.update(loaded)  # compatible con archivos de versiones anteriores
            except json.JSONDecodeError:
                logger.warning("Archivo de winrates corrupto, se reinicia")
        return data

    def save(self) -> None:
        self._data["seen_matches"] = self._data["seen_matches"][-_MAX_SEEN_MATCHES:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data), encoding="utf-8")

    # ---------- registro ----------

    def is_seen(self, match_id: str) -> bool:
        return match_id in self._data["seen_matches"]

    def mark_seen(self, match_id: str) -> None:
        self._data["seen_matches"].append(match_id)

    def record(self, kind: str, key: int | str, won: bool) -> None:
        bucket = self._data[kind].setdefault(str(key), [0, 0])
        bucket[0] += 1
        bucket[1] += int(won)

    # ---------- consulta ----------

    def winrate(self, kind: str, key: int | str) -> tuple[float, int] | None:
        """(winrate 0-100, partidas) con muestra >= MIN_GAMES_FOR_DISPLAY, o None."""
        bucket = self._data.get(kind, {}).get(str(key))
        if not bucket or bucket[0] < MIN_GAMES_FOR_DISPLAY:
            return None
        games, wins = bucket
        return round(100 * wins / games, 1), games

    def winrate_any(self, kind: str, key: int | str) -> tuple[float, int] | None:
        """(winrate 0-100, partidas) con cualquier muestra >= 1, o None si nunca visto."""
        bucket = self._data.get(kind, {}).get(str(key))
        if not bucket or bucket[0] == 0:
            return None
        games, wins = bucket
        return round(100 * wins / games, 1), games

    def smoothed(self, kind: str, key: int | str, prior: float = 0.5, k: int = 10) -> float:
        """
        Winrate 0-1 con suavizado bayesiano: con poca muestra tiende al prior.
        (games*wr + k*prior) / (games + k) — evita que 2 partidas den 100%.
        """
        bucket = self._data.get(kind, {}).get(str(key)) or [0, 0]
        games, wins = bucket
        return (wins + k * prior) / (games + k)

    def games(self, kind: str, key: int | str) -> int:
        bucket = self._data.get(kind, {}).get(str(key))
        return bucket[0] if bucket else 0

    def keys_for_prefix(self, kind: str, prefix: str) -> list[str]:
        """Claves de un agregado compuesto que empiezan por prefix (ej. '104_')."""
        return [k for k in self._data.get(kind, {}) if k.startswith(prefix)]

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
        merged = {
            k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in _EMPTY_SCHEMA.items()
        }
        merged.update(remote)
        self._data = merged
        self.save()
        return True


def _participant_items(participant: dict[str, Any]) -> set[int]:
    """Ítems únicos del build final (slots item0-item5; item6 es el trinket)."""
    return {
        item_id
        for slot in range(6)
        if (item_id := participant.get(f"item{slot}", 0))
    }


def _participant_perks(participant: dict[str, Any]) -> tuple[int | None, list[int]]:
    """(keystone, todas las runas seleccionadas) del participante."""
    keystone = None
    all_perks: list[int] = []
    for style in participant.get("perks", {}).get("styles", []):
        selections = style.get("selections", [])
        for i, selection in enumerate(selections):
            perk = selection.get("perk")
            if perk:
                all_perks.append(perk)
                if style.get("description") == "primaryStyle" and i == 0:
                    keystone = perk
    return keystone, all_perks


def _record_participant(
    store: WinrateStore,
    participant: dict[str, Any],
    enemies: list[int],
    allies: list[int],
) -> None:
    won = bool(participant.get("win"))
    champ = participant.get("championId")
    items = _participant_items(participant)
    keystone, all_perks = _participant_perks(participant)

    for item_id in items:
        store.record("items", item_id, won)
        for enemy in enemies:
            store.record("item_vs", f"{item_id}_vs_{enemy}", won)
        if champ:
            store.record("champ_items", f"{champ}_{item_id}", won)

    for perk in all_perks:
        store.record("runes", perk, won)
        if champ:
            store.record("champ_runes", f"{champ}_{perk}", won)
    if keystone:
        store.record("keystones", keystone, won)
        for enemy in enemies:
            store.record("keystone_vs", f"{keystone}_vs_{enemy}", won)
        if champ:
            store.record("champ_keystones", f"{champ}_{keystone}", won)

    if champ:
        store.record("champions", champ, won)
        for enemy in enemies:
            store.record("matchups", f"{champ}_vs_{enemy}", won)
        for ally in allies:
            if ally != champ:
                pair = "_con_".join(map(str, sorted((champ, ally))))
                store.record("duos", pair, won)


def collect_winrates(
    riot: RiotApiConnector,
    store: WinrateStore,
    max_matches: int = 100,
    players: int = 15,
    matches_per_player: int = 10,
    start_time: int | None = None,
    end_time: int | None = None,
) -> CollectReport:
    """
    Recolecta partidas del ladder y agrega todas las dimensiones al store.
    start_time/end_time (epoch segundos) permiten recolectar HISTÓRICO
    (match-v5 conserva ~2 años de partidas).
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
            pending.extend(
                riot.match_ids(
                    puuid,
                    count=matches_per_player,
                    start_time=start_time,
                    end_time=end_time,
                )
            )
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
        champs_by_team: dict[int, list[int]] = {}
        for participant in participants:
            champs_by_team.setdefault(participant.get("teamId", 0), []).append(
                participant.get("championId", 0)
            )

        for participant in participants:
            team = participant.get("teamId", 0)
            allies = champs_by_team.get(team, [])
            enemies = [
                c for t, champs in champs_by_team.items() if t != team for c in champs
            ]
            _record_participant(store, participant, enemies, allies)
            report.participants += 1

        store.mark_seen(match_id)
        report.matches_processed += 1

    store.save()
    logger.info("Recoleccion terminada: %s", report.summary())
    return report
