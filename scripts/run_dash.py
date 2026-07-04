"""Entrypoint local: `python scripts/run_dash.py`."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lol_consultor.app.dash_app import create_app  # noqa: E402

if __name__ == "__main__":
    app = create_app()
    debug = os.getenv("LOL_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=8050, debug=debug)
