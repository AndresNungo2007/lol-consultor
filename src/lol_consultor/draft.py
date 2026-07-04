"""
Motor de análisis de draft: recomienda qué campeón del pool del usuario
elegir según la selección de aliados y enemigos.

Factores considerados (con los datos disponibles públicamente):
  - Fuerza en el meta: winrate del candidato en el rol (op.gg).
  - Countereo directo: matchups desfavorables del candidato contra los
    enemigos ya elegidos, y matchups donde el candidato counterea a un
    enemigo (counters de op.gg por posición).
  - Distribución de daño AP/AD del equipo aliado (perfiles de Data Dragon).
  - Composición: aporte de línea de frente (tanque/peleador) si falta.

Limitación honesta: no existe fuente pública de sinergias directas entre
campeones aliados; la "sinergia" se aproxima vía balance de daño y de
composición, y así se comunica en la UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lol_consultor.service import LoLService

ROLES = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]

# Pesos del modelo de puntaje (magnitudes comparables entre factores).
_W_META = 0.6
_W_COUNTER = 1.0
_BONUS_BALANCE = 2.0
_PENALTY_SKEW = 2.0
_BONUS_FRONTLINE = 2.0
_AD_SKEW_THRESHOLD = 0.65
_FRONTLINE_DEFENSE = 6


@dataclass(frozen=True)
class DraftFactor:
    descripcion: str
    puntos: float


@dataclass(frozen=True)
class DraftRecommendation:
    champion_id: str
    champion_name: str
    score: float
    factores: list[DraftFactor]


def _damage_profile(champ: dict[str, Any]) -> tuple[int, int]:
    """(físico, mágico) según el perfil oficial de Data Dragon (0-10 cada uno)."""
    info = champ.get("info", {})
    return info.get("attack", 0), info.get("magic", 0)


def _is_ap(champ: dict[str, Any]) -> bool:
    ad, ap = _damage_profile(champ)
    return ap > ad


class DraftAnalyzer:
    def __init__(self, service: LoLService) -> None:
        self.service = service

    def analyze(
        self,
        pool: list[str],
        role: str,
        allies: list[str],
        enemies: list[str],
    ) -> list[DraftRecommendation]:
        """Evalúa cada campeón del pool y devuelve recomendaciones ordenadas."""
        ally_champs = self._resolve(allies)
        enemy_champs = self._resolve(enemies)
        enemy_keys = {int(c["key"]) for c in enemy_champs}
        enemy_counter_index = self._enemy_counter_index(enemy_champs)

        results = []
        for name in pool:
            champ = self.service.find_champion(name)
            if champ is None:
                continue
            factores = [
                *self._meta_and_counter_factors(champ, role, enemy_keys, enemy_counter_index),
                *self._damage_balance_factor(champ, ally_champs),
                *self._frontline_factor(champ, ally_champs),
            ]
            score = round(sum(f.puntos for f in factores), 1)
            results.append(
                DraftRecommendation(
                    champion_id=champ["id"],
                    champion_name=champ["name"],
                    score=score,
                    factores=factores,
                )
            )
        return sorted(results, key=lambda r: -r.score)

    # ---------- factores ----------

    def _meta_and_counter_factors(
        self,
        champ: dict[str, Any],
        role: str,
        enemy_keys: set[int],
        enemy_counter_index: dict[int, tuple[str, float]],
    ) -> list[DraftFactor]:
        factores: list[DraftFactor] = []
        by_key = self.service.champions_by_key()
        meta = self.service.opgg.champion_meta(int(champ["key"]))
        position = None
        if meta is not None:
            position = next((p for p in meta.positions if p.position == role), None)
            position = position or meta.best_position()

        if position is None:
            factores.append(
                DraftFactor("Sin datos de meta en op.gg para este parche (0.0)", 0.0)
            )
            return factores

        meta_pts = round((position.win_rate - 50) * _W_META, 1)
        factores.append(
            DraftFactor(
                f"Meta: winrate {position.win_rate}% en {position.position} "
                f"({meta_pts:+.1f})",
                meta_pts,
            )
        )

        # Enemigos que counterean al candidato (el candidato pierde el matchup).
        for counter in position.counters:
            if counter.champion_id in enemy_keys:
                rival = by_key.get(counter.champion_id, {})
                pts = round(-(50 - counter.win_rate) * _W_COUNTER, 1)
                factores.append(
                    DraftFactor(
                        f"Riesgo: {rival.get('name', '?')} te counterea "
                        f"(ganas solo el {counter.win_rate}%) ({pts:+.1f})",
                        pts,
                    )
                )

        # Enemigos a los que el candidato counterea.
        champ_key = int(champ["key"])
        if champ_key in enemy_counter_index:
            enemy_name, enemy_wr = enemy_counter_index[champ_key]
            pts = round((50 - enemy_wr) * _W_COUNTER, 1)
            factores.append(
                DraftFactor(
                    f"Ventaja: countereas a {enemy_name} "
                    f"(le ganas el {round(100 - enemy_wr, 1)}% de las veces) ({pts:+.1f})",
                    pts,
                )
            )
        return factores

    def _damage_balance_factor(
        self, champ: dict[str, Any], allies: list[dict[str, Any]]
    ) -> list[DraftFactor]:
        if not allies:
            return []
        total_ad = sum(_damage_profile(a)[0] for a in allies)
        total_ap = sum(_damage_profile(a)[1] for a in allies)
        if total_ad + total_ap == 0:
            return []
        ad_share = total_ad / (total_ad + total_ap)
        candidate_is_ap = _is_ap(champ)

        if ad_share >= _AD_SKEW_THRESHOLD:
            if candidate_is_ap:
                return [
                    DraftFactor(
                        f"Equilibra el daño: tu equipo es mayormente AD y aportas AP "
                        f"({_BONUS_BALANCE:+.1f})",
                        _BONUS_BALANCE,
                    )
                ]
            return [
                DraftFactor(
                    f"El equipo queda muy cargado a daño físico ({-_PENALTY_SKEW:+.1f})",
                    -_PENALTY_SKEW,
                )
            ]
        if ad_share <= 1 - _AD_SKEW_THRESHOLD:
            if not candidate_is_ap:
                return [
                    DraftFactor(
                        f"Equilibra el daño: tu equipo es mayormente AP y aportas AD "
                        f"({_BONUS_BALANCE:+.1f})",
                        _BONUS_BALANCE,
                    )
                ]
            return [
                DraftFactor(
                    f"El equipo queda muy cargado a daño mágico ({-_PENALTY_SKEW:+.1f})",
                    -_PENALTY_SKEW,
                )
            ]
        return [DraftFactor("El perfil de daño del equipo ya está balanceado (+0.0)", 0.0)]

    def _frontline_factor(
        self, champ: dict[str, Any], allies: list[dict[str, Any]]
    ) -> list[DraftFactor]:
        if not allies:
            return []
        has_frontline = any(
            a.get("info", {}).get("defense", 0) >= _FRONTLINE_DEFENSE for a in allies
        )
        candidate_tanky = champ.get("info", {}).get("defense", 0) >= _FRONTLINE_DEFENSE
        if not has_frontline and candidate_tanky:
            return [
                DraftFactor(
                    f"Aporta la línea de frente que le falta al equipo "
                    f"({_BONUS_FRONTLINE:+.1f})",
                    _BONUS_FRONTLINE,
                )
            ]
        return []

    # ---------- auxiliares ----------

    def _resolve(self, names: list[str]) -> list[dict[str, Any]]:
        resolved = []
        for name in names:
            champ = self.service.find_champion(name)
            if champ is not None:
                resolved.append(champ)
        return resolved

    def _enemy_counter_index(
        self, enemy_champs: list[dict[str, Any]]
    ) -> dict[int, tuple[str, float]]:
        """
        Índice: key de campeón que counterea a algún enemigo ->
        (nombre del enemigo counterado, winrate del enemigo en ese matchup).
        """
        index: dict[int, tuple[str, float]] = {}
        for enemy in enemy_champs:
            meta = self.service.opgg.champion_meta(int(enemy["key"]))
            if meta is None:
                continue
            for position in meta.positions:
                for counter in position.counters:
                    current = index.get(counter.champion_id)
                    if current is None or counter.win_rate < current[1]:
                        index[counter.champion_id] = (enemy["name"], counter.win_rate)
        return index
