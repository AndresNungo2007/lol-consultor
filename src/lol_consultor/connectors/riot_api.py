"""
Conector de la API oficial de Riot Games (requiere API key gratuita).

Se usa para recolectar partidas ranked reales y calcular winrates de ítems y
runas — datos que ninguna fuente pública expone directamente. Endpoints:
  - league-v4: jugadores del ladder (semilla de la recolección)
  - summoner-v4: summonerId -> puuid
  - match-v5: ids de partidas por jugador y detalle de cada partida

La key de desarrollo (developer.riotgames.com) expira cada 24 h y tiene
límites de 20 req/s y 100 req/2 min: el conector aplica un throttle fijo y
respeta el Retry-After de los 429.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

RANKED_SOLO_QUEUE_ID = 420

# Enrutamiento regional de match-v5 por servidor (platform).
PLATFORM_TO_REGION = {
    "la1": "americas", "la2": "americas", "na1": "americas", "br1": "americas",
    "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe", "me1": "europe",
    "kr": "asia", "jp1": "asia",
    "oc1": "sea", "sg2": "sea", "tw2": "sea", "vn2": "sea",
}


class RiotApiError(RuntimeError):
    pass


class RiotApiConnector:
    def __init__(
        self,
        api_key: str,
        platform: str = "la1",
        region: str = "americas",
        timeout: int = 20,
        throttle_seconds: float = 1.3,
    ) -> None:
        """
        platform: servidor del ladder (la1=LAN, la2=LAS, na1, euw1...).
        region: enrutamiento de match-v5 (americas, europe, asia).
        throttle_seconds: pausa entre peticiones para no exceder 100 req/2min.
        """
        if not api_key:
            raise RiotApiError(
                "Falta RIOT_API_KEY. Crea una key gratuita en "
                "https://developer.riotgames.com y agrégala a tu .env."
            )
        self.platform_url = f"https://{platform}.api.riotgames.com"
        self.region_url = f"https://{region}.api.riotgames.com"
        self.timeout = timeout
        self.throttle_seconds = throttle_seconds
        self.session = requests.Session()
        self.session.headers.update({"X-Riot-Token": api_key})
        self._last_request = 0.0

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        wait = self.throttle_seconds - (time.time() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        response = self.session.get(url, params=params, timeout=self.timeout)
        self._last_request = time.time()

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "10"))
            logger.info("Rate limit de Riot: esperando %ss", retry_after)
            time.sleep(retry_after)
            response = self.session.get(url, params=params, timeout=self.timeout)
            self._last_request = time.time()
        if response.status_code == 403:
            raise RiotApiError("Riot API devolvió 403: la key expiró o es inválida.")
        response.raise_for_status()
        return response.json()

    # ---------- semilla: jugadores del ladder ----------

    def challenger_puuids(self, max_players: int = 30) -> list[str]:
        """PUUIDs de los mejores jugadores de soloQ del servidor configurado."""
        league = self._get(
            f"{self.platform_url}/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
        )
        entries = sorted(
            league.get("entries", []), key=lambda e: -e.get("leaguePoints", 0)
        )[:max_players]
        puuids = []
        for entry in entries:
            puuid = entry.get("puuid")
            if not puuid and entry.get("summonerId"):
                summoner = self._get(
                    f"{self.platform_url}/lol/summoner/v4/summoners/{entry['summonerId']}"
                )
                puuid = summoner.get("puuid")
            if puuid:
                puuids.append(puuid)
        return puuids

    # ---------- partidas ----------

    def match_ids(
        self,
        puuid: str,
        count: int = 20,
        start_time: int | None = None,
        end_time: int | None = None,
        start: int = 0,
    ) -> list[str]:
        """
        IDs de partidas ranked soloQ de un jugador. start_time/end_time
        (epoch segundos) permiten ventanas históricas — match-v5 conserva
        alrededor de 2 años de partidas; 'start' pagina hacia atrás.
        """
        params: dict[str, Any] = {
            "queue": RANKED_SOLO_QUEUE_ID,
            "count": min(count, 100),
            "start": start,
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        return self._get(
            f"{self.region_url}/lol/match/v5/matches/by-puuid/{puuid}/ids",
            params=params,
        )

    def match(self, match_id: str) -> dict[str, Any]:
        """Detalle completo de una partida (participantes, builds, runas, resultado)."""
        return self._get(f"{self.region_url}/lol/match/v5/matches/{match_id}")
