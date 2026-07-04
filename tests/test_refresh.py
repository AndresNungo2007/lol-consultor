from __future__ import annotations

import threading
import time

from lol_consultor.refresh import refresh_all, start_background_refresher


class _RecordingService:
    """Registra qué rutinas de refresco se invocan."""

    def __init__(self, patch_changed: bool = False, fail_items: bool = False):
        self.calls: list[str] = []
        self._patch_changed = patch_changed
        self._fail_items = fail_items
        self.ddragon = self
        self.opgg = self
        self.wiki = self
        self.version = "14.20.1"

    # --- interfaz usada por refresh_all ---
    def check_for_new_patch(self) -> bool:
        self.calls.append("check_patch")
        return self._patch_changed

    def clear_meta_caches(self) -> int:
        self.calls.append("clear_caches")
        return 3

    def champions(self):
        self.calls.append("champions")
        return {}

    def items(self):
        self.calls.append("items")
        if self._fail_items:
            raise ConnectionError("CDN caído")
        return {}

    def runes(self):
        self.calls.append("runes")
        return []

    def summoner_spells(self):
        self.calls.append("spells")
        return {}

    def refresh_stats(self) -> bool:
        self.calls.append("opgg_refresh")
        return True

    def find_champion(self, _nombre: str):
        return None  # pool no resoluble en este stub

    def champion_list(self):
        return []


def test_refresh_all_runs_every_step_and_reports():
    service = _RecordingService()

    report = refresh_all(service)

    assert report.version == "14.20.1"
    assert not report.patch_changed
    assert "campeones" in report.refreshed
    assert "meta op.gg (forzado)" in report.refreshed
    assert "clear_caches" not in service.calls  # sin parche nuevo no se invalida
    assert report.errors == []


def test_refresh_all_invalidates_caches_on_new_patch():
    service = _RecordingService(patch_changed=True)

    report = refresh_all(service)

    assert report.patch_changed
    assert "clear_caches" in service.calls
    assert any("invalidados" in r for r in report.refreshed)


def test_refresh_all_isolates_step_failures():
    service = _RecordingService(fail_items=True)

    report = refresh_all(service)

    # items falló pero los pasos siguientes corrieron igual
    assert any("items" in e for e in report.errors)
    assert "runas" in report.refreshed
    assert "opgg_refresh" in service.calls


def test_background_refresher_runs_periodically_and_stops():
    service = _RecordingService()
    stop = threading.Event()

    thread = start_background_refresher(
        service, interval_seconds=3600, initial_delay_seconds=0, stop_event=stop
    )
    deadline = time.time() + 5
    while "opgg_refresh" not in service.calls and time.time() < deadline:
        time.sleep(0.05)

    assert "opgg_refresh" in service.calls  # corrió al menos un ciclo
    stop.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
