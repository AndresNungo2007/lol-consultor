"""
Rutinas de actualización proactiva de datos.

Tres capas de frescura:
  1. Cache perezoso (ya existente): ddragon por parche, wiki/op.gg por TTL.
  2. `refresh_all`: un ciclo que detecta parche nuevo (invalida todo si lo hay),
     pre-descarga los datasets base y fuerza la actualización de op.gg.
  3. `start_background_refresher`: hilo daemon que ejecuta el ciclo cada
     N segundos mientras la app corre. Para refrescar con la app cerrada,
     ver scripts/refresh_data.py (programable en el Task Scheduler / cron).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from lol_consultor import config
from lol_consultor.service import LoLService

logger = logging.getLogger(__name__)


@dataclass
class RefreshReport:
    version: str = "?"
    patch_changed: bool = False
    refreshed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        estado = "PARCHE NUEVO" if self.patch_changed else "sin cambios de parche"
        lines = [f"Parche {self.version} ({estado})"]
        if self.refreshed:
            lines.append("Actualizado: " + ", ".join(self.refreshed))
        if self.errors:
            lines.append("Errores: " + " | ".join(self.errors))
        return "\n".join(lines)


def refresh_all(service: LoLService, prefetch_champion_details: bool = False) -> RefreshReport:
    """
    Ejecuta un ciclo completo de actualización. Cada paso es independiente:
    un fallo se registra en el reporte sin frenar los demás.
    """
    report = RefreshReport()

    try:
        report.patch_changed = service.check_for_new_patch()
        report.version = service.ddragon.version
        if report.patch_changed:
            removed = service.clear_meta_caches()
            report.refreshed.append(f"caches TTL invalidados ({removed} entradas)")
    except Exception as exc:
        report.errors.append(f"chequeo de parche: {exc}")

    steps: list[tuple[str, Callable[[], object]]] = [
        ("campeones", service.ddragon.champions),
        ("items", service.ddragon.items),
        ("runas", service.ddragon.runes),
        ("hechizos", service.ddragon.summoner_spells),
    ]
    for name, step in steps:
        try:
            step()
            report.refreshed.append(name)
        except Exception as exc:
            report.errors.append(f"{name}: {exc}")

    try:
        if service.opgg.refresh_stats():
            report.refreshed.append("meta op.gg (forzado)")
        else:
            report.errors.append("meta op.gg: sin respuesta")
    except Exception as exc:
        report.errors.append(f"meta op.gg: {exc}")

    # Pre-calentar lo que usa el análisis de draft: detalles y parches del pool.
    for name in config.DEFAULT_POOL:
        try:
            champ = service.find_champion(name)
            if champ is None:
                continue
            service.ddragon.champion(champ["id"])
            service.wiki.champion_patch_history(champ["name"])
        except Exception as exc:
            report.errors.append(f"pool {name}: {exc}")
    report.refreshed.append(f"pool ({len(config.DEFAULT_POOL)} campeones)")

    if prefetch_champion_details:
        count = 0
        for champ in service.champion_list():
            try:
                service.ddragon.champion(champ["id"])
                count += 1
            except Exception as exc:
                report.errors.append(f"detalle {champ['id']}: {exc}")
        report.refreshed.append(f"detalles completos ({count} campeones)")

    logger.info("Refresco terminado: %s", report.summary().replace("\n", " / "))
    return report


def start_background_refresher(
    service: LoLService,
    interval_seconds: int = config.REFRESH_INTERVAL_S,
    initial_delay_seconds: int = 10,
    stop_event: threading.Event | None = None,
) -> threading.Thread:
    """
    Lanza un hilo daemon que corre refresh_all periódicamente mientras
    la app esté viva. Devuelve el hilo (útil para tests con stop_event).
    """
    stop = stop_event or threading.Event()

    def _loop() -> None:
        if stop.wait(initial_delay_seconds):
            return
        while True:
            try:
                refresh_all(service)
            except Exception:
                logger.warning("Ciclo de refresco falló", exc_info=True)
            if stop.wait(interval_seconds):
                return

    thread = threading.Thread(target=_loop, daemon=True, name="lol-refresher")
    thread.start()
    return thread
