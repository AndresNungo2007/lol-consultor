"""
Refresco manual/programado de datos: `python scripts/refresh_data.py [--completo]`.

Pensado para ejecutarse con la app cerrada (deja el cache caliente para el
próximo arranque). Programable en el Task Scheduler de Windows o cron:

  schtasks /Create /SC HOURLY /TN "LoLConsultor Refresh" ^
    /TR "\"<ruta>\\.venv\\Scripts\\python.exe\" \"<ruta>\\scripts\\refresh_data.py\""

--completo: además pre-descarga el detalle de TODOS los campeones (~170
peticiones al CDN de Riot; útil tras un parche nuevo).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lol_consultor.refresh import refresh_all  # noqa: E402
from lol_consultor.service import LoLService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Actualiza los datos cacheados de LoL Consultor")
    parser.add_argument(
        "--completo",
        action="store_true",
        help="pre-descarga tambien el detalle de todos los campeones",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    service = LoLService()
    report = refresh_all(service, prefetch_champion_details=args.completo)
    print(report.summary())
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
