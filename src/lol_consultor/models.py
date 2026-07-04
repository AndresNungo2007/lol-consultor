"""
Modelos tipados para los datos de meta/counters de op.gg.

Los datos de Data Dragon y de la wiki ya vienen razonablemente estructurados
(dicts / texto) y se consumen tal cual desde la capa de servicio y la app;
no se duplican aquí en dataclasses paralelas. Los de op.gg sí se normalizan
porque el JSON crudo es profundamente anidado y poco práctico de consumir
directamente en los callbacks de Dash.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CounterEntry:
    champion_id: int
    games: int
    wins: int

    @property
    def win_rate(self) -> float:
        """Winrate del campeón consultado contra este rival (0-100)."""
        return round(100 * self.wins / self.games, 1) if self.games else 0.0


@dataclass(frozen=True)
class PositionMeta:
    position: str
    play_rate: float
    win_rate: float
    ban_rate: float
    counters: list[CounterEntry]


@dataclass(frozen=True)
class ChampionMeta:
    champion_id: int
    positions: list[PositionMeta]

    def best_position(self) -> PositionMeta | None:
        return max(self.positions, key=lambda p: p.play_rate, default=None)
