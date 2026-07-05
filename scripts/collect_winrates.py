"""
Recolecta partidas ranked (Riot API) y acumula winrates:
`python scripts/collect_winrates.py [--partidas 100] [--desde 2025-08-01]
 [--hasta 2026-01-01] [--plataformas la1,la2,br1]`

Requiere RIOT_API_KEY en el entorno o .env. Los agregados crecen con cada
ejecución. --desde/--hasta permiten recolectar HISTÓRICO (match-v5 conserva
~2 años); --plataformas recolecta de varios servidores en una pasada.

Nota: mezclar ventanas muy largas mezcla parches y metas distintas; para
comparar ítems del parche actual conviene recolectar ventanas recientes.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lol_consultor import config  # noqa: E402
from lol_consultor.connectors.riot_api import (  # noqa: E402
    PLATFORM_TO_REGION,
    RiotApiConnector,
    RiotApiError,
)
from lol_consultor.winrates import WinrateStore, collect_winrates  # noqa: E402


def _epoch(date_str: str | None) -> int | None:
    if not date_str:
        return None
    return int(datetime.fromisoformat(date_str).replace(tzinfo=UTC).timestamp())


def main() -> int:
    parser = argparse.ArgumentParser(description="Recolecta winrates de items/runas/campeones")
    parser.add_argument("--partidas", type=int, default=100, help="partidas nuevas a procesar")
    parser.add_argument(
        "--store",
        default=None,
        help="ruta del JSON de agregados (default: <cache>/winrates.json)",
    )
    parser.add_argument(
        "--jugadores", type=int, default=30, help="jugadores del ladder a muestrear"
    )
    parser.add_argument(
        "--partidas-por-jugador", type=int, default=25, help="historial a pedir por jugador"
    )
    parser.add_argument("--desde", default=None, help="fecha inicial ISO, ej. 2025-08-01")
    parser.add_argument("--hasta", default=None, help="fecha final ISO, ej. 2026-01-01")
    parser.add_argument(
        "--plataformas",
        default=None,
        help="servidores separados por coma, ej. 'la1,la2,br1,na1' (default: LOL_RIOT_PLATFORM)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    platforms = [
        p.strip() for p in (args.plataformas or config.RIOT_PLATFORM).split(",") if p.strip()
    ]
    store = WinrateStore(args.store or config.CACHE_DIR / "winrates.json")

    total_errors: list[str] = []
    per_platform = max(1, args.partidas // len(platforms))
    for platform in platforms:
        try:
            riot = RiotApiConnector(
                api_key=config.RIOT_API_KEY,
                platform=platform,
                region=PLATFORM_TO_REGION.get(platform, config.RIOT_REGION),
            )
        except RiotApiError as exc:
            print(exc)
            return 1
        print(f"--- Servidor {platform} ({per_platform} partidas) ---")
        report = collect_winrates(
            riot,
            store,
            max_matches=per_platform,
            players=args.jugadores,
            matches_per_player=args.partidas_por_jugador,
            start_time=_epoch(args.desde),
            end_time=_epoch(args.hasta),
        )
        print(report.summary())
        total_errors.extend(report.errors)

    print(f"Total de partidas acumuladas: {store.total_matches}")
    return 1 if total_errors and not store.total_matches else 0


if __name__ == "__main__":
    raise SystemExit(main())
