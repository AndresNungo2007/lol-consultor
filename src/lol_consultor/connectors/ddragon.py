"""
Conector de datos de League of Legends basado en fuentes OFICIALES de Riot.

Cubre (sin API key, gratis):
  - Campeones (lista + detalle con habilidades, spells y pasiva)
  - Ítems (stats, precio, receta/'into'/'from', tags)
  - Runas (árboles y perks de runesReforged)
  - Hechizos de invocador
  - URLs de imágenes (iconos, splash, loading, ability icons)

Estrategia: descarga Data Dragon y lo cachea en disco por versión de parche.
Solo vuelve a descargar cuando Riot publica un parche nuevo -> siempre
actualizado sin tráfico innecesario.

NO cubre (no existe API oficial): counters, tier lists, build recomendada,
winrates por matchup, estilos de juego detallados. Ver connectors/fandom_wiki.py
y connectors/opgg_meta.py para esos datos.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

DDRAGON = "https://ddragon.leagueoflegends.com"
# Community Dragon: datos de habilidades más precisos que ddragon.
CDRAGON = "https://raw.communitydragon.org"


class DDragonConnector:
    def __init__(
        self,
        lang: str = "es_ES",
        cache_dir: str | Path = ".lol_cache",
        version: str | None = None,
        timeout: int = 20,
        auto_update: bool = True,
    ) -> None:
        """
        lang: idioma de ddragon, p.ej. 'es_ES', 'es_MX', 'en_US'.
        cache_dir: carpeta local donde se guardan los JSON por versión.
        version: fija un parche concreto; None = último disponible.
        auto_update: si True, comprueba el último parche al instanciar.
        """
        self.lang = lang
        self.timeout = timeout
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"Accept-Charset": "UTF-8"})
        self._cache: dict[str, Any] = {}
        self.version = version or (self.latest_version() if auto_update else self._pinned_version())

    # ---------- infraestructura ----------

    def _get_json(self, url: str) -> Any:
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _pinned_version(self) -> str:
        f = self.cache_dir / "_version.txt"
        return f.read_text().strip() if f.exists() else self.latest_version()

    def latest_version(self) -> str:
        """Último parche publicado en Data Dragon (el primero del array)."""
        versions = self._get_json(f"{DDRAGON}/api/versions.json")
        return versions[0]

    def _cache_path(self, name: str) -> Path:
        d = self.cache_dir / self.version
        d.mkdir(parents=True, exist_ok=True)
        return d / name

    def _load_cached(self, name: str, url: str) -> Any:
        """Devuelve JSON desde disco; si no está para este parche, lo baja."""
        if name in self._cache:
            return self._cache[name]
        path = self._cache_path(name)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = self._get_json(url)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            (self.cache_dir / "_version.txt").write_text(self.version)
        self._cache[name] = data
        return data

    def check_for_new_patch(self) -> bool:
        """
        Comprueba si hay parche nuevo. Si lo hay, apunta a él (los datos se
        bajarán de forma perezosa la próxima vez que los pidas).
        Devuelve True si cambió la versión.
        """
        latest = self.latest_version()
        if latest != self.version:
            self.version = latest
            self._cache.clear()
            return True
        return False

    # ---------- datos ----------

    def champions(self) -> dict[str, Any]:
        """Lista resumida de todos los campeones (key -> datos básicos)."""
        url = f"{DDRAGON}/cdn/{self.version}/data/{self.lang}/champion.json"
        return self._load_cached("champion.json", url)["data"]

    def champion(self, name: str) -> dict[str, Any]:
        """
        Detalle COMPLETO de un campeón: habilidades (spells), pasiva, stats,
        tips, skins, etc. 'name' es el id, p.ej. 'Ahri', 'MonkeyKing' (Wukong).
        """
        url = f"{DDRAGON}/cdn/{self.version}/data/{self.lang}/champion/{name}.json"
        return self._load_cached(f"champion_{name}.json", url)["data"][name]

    def items(self) -> dict[str, Any]:
        url = f"{DDRAGON}/cdn/{self.version}/data/{self.lang}/item.json"
        return self._load_cached("item.json", url)["data"]

    def runes(self) -> list[dict[str, Any]]:
        """Árboles de runas (Precisión, Dominación, etc.) con sus perks."""
        url = f"{DDRAGON}/cdn/{self.version}/data/{self.lang}/runesReforged.json"
        return self._load_cached("runesReforged.json", url)

    def summoner_spells(self) -> dict[str, Any]:
        url = f"{DDRAGON}/cdn/{self.version}/data/{self.lang}/summoner.json"
        return self._load_cached("summoner.json", url)["data"]

    # ---------- habilidades precisas (Community Dragon) ----------

    def champion_abilities_cdragon(self, champion_key: int | str) -> dict[str, Any]:
        """
        Datos de habilidades desde Community Dragon (más precisos que ddragon).
        'champion_key' es el numérico ('key' en champions()), p.ej. Ahri = 103.
        """
        url = (
            f"{CDRAGON}/latest/plugins/rcp-be-lol-game-data/global/default/"
            f"v1/champions/{champion_key}.json"
        )
        return self._load_cached(f"cdragon_{champion_key}.json", url)

    # ---------- imágenes ----------

    def champion_square_url(self, image_full: str) -> str:
        """image_full = champion()['image']['full'], p.ej. 'Ahri.png'."""
        return f"{DDRAGON}/cdn/{self.version}/img/champion/{image_full}"

    def item_icon_url(self, item_id: str) -> str:
        return f"{DDRAGON}/cdn/{self.version}/img/item/{item_id}.png"

    def passive_icon_url(self, image_full: str) -> str:
        """image_full = champion()['passive']['image']['full']."""
        return f"{DDRAGON}/cdn/{self.version}/img/passive/{image_full}"

    def spell_icon_url(self, image_full: str) -> str:
        """image_full = champion()['spells'][i]['image']['full']."""
        return f"{DDRAGON}/cdn/{self.version}/img/spell/{image_full}"

    def splash_url(self, champion_id: str, skin_num: int = 0) -> str:
        return f"{DDRAGON}/cdn/img/champion/splash/{champion_id}_{skin_num}.jpg"

    def rune_icon_url(self, icon_path: str) -> str:
        """icon_path = campo 'icon' de un perk/style, p.ej. 'perk-images/Styles/...'."""
        return f"{DDRAGON}/cdn/img/{icon_path}"
