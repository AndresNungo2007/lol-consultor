"""Entrypoint local: `python scripts/run_dash.py`."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lol_consultor import config  # noqa: E402
from lol_consultor.app.dash_app import create_app  # noqa: E402
from lol_consultor.refresh import start_background_refresher  # noqa: E402
from lol_consultor.service import LoLService  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")

    service = LoLService()
    if config.REFRESH_INTERVAL_S > 0:
        start_background_refresher(service, config.REFRESH_INTERVAL_S)

    app = create_app(service=service)
    debug = os.getenv("LOL_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=8050, debug=debug)
