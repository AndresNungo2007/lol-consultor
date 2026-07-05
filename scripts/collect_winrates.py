"""
Recolecta partidas ranked (Riot API) y acumula winrates de ítems y runas:
`python scripts/collect_winrates.py [--partidas 100]`

Requiere RIOT_API_KEY en el entorno o .env (gratuita en
https://developer.riotgames.com; la key de desarrollo expira cada 24 h).
Los agregados crecen con cada ejecución; programable igual que
refresh_data.py (Task Scheduler / cron).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lol_consultor import config  # noqa: E402
from lol_consultor.connectors.riot_api import RiotApiConnector, RiotApiError  # noqa: E402
from lol_consultor.winrates import WinrateStore, collect_winrates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Recolecta winrates de items/runas")
    parser.add_argument("--partidas", type=int, default=100, help="partidas nuevas a procesar")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    try:
        riot = RiotApiConnector(
            api_key=config.RIOT_API_KEY,
            platform=config.RIOT_PLATFORM,
            region=config.RIOT_REGION,
        )
    except RiotApiError as exc:
        print(exc)
        return 1

    store = WinrateStore(config.CACHE_DIR / "winrates.json")
    report = collect_winrates(riot, store, max_matches=args.partidas)
    print(report.summary())
    print(f"Total de partidas acumuladas: {store.total_matches}")
    return 1 if report.errors and not report.matches_processed else 0


if __name__ == "__main__":
    raise SystemExit(main())
