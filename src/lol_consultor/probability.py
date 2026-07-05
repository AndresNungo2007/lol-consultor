"""
Probabilidad de victoria y sugerencia de build a partir de los datos
recolectados con la Riot API (winrates.py).

Modelo: combinación de log-odds con suavizado bayesiano.
  P = sigmoide( logit(base del campeón) + Σ ajustes por matchup vs cada
      enemigo + Σ ajustes por dúo con cada aliado )
Cada término se suaviza hacia su prior según su muestra: con pocos datos el
ajuste tiende a 0 y la probabilidad tiende a la base del campeón. Es un
estimador honesto de datos observacionales: sirve para comparar opciones,
no garantiza el resultado de una partida concreta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from lol_consultor.winrates import WinrateStore

# Suavizado: partidas "ficticias" hacia el prior. Más alto = más conservador.
_K_CHAMPION = 40
_K_MATCHUP = 15
_K_DUO = 15
_K_ITEM = 20
_K_ITEM_VS = 12


def _logit(p: float) -> float:
    p = min(max(p, 0.01), 0.99)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


@dataclass
class WinProbability:
    probability: float  # 0-100
    champion_games: int
    evidence_games: int  # partidas totales que aportaron a los ajustes
    notes: list[str] = field(default_factory=list)


def win_probability(
    store: WinrateStore,
    champion_key: int,
    ally_keys: list[int],
    enemy_keys: list[int],
    opgg_winrate: float | None = None,
) -> WinProbability:
    """
    Probabilidad estimada de ganar con `champion_key` dado el draft.
    opgg_winrate (0-100) se usa como prior de la base del campeón: aporta
    la muestra masiva de op.gg donde la nuestra todavía es chica.
    """
    prior = (opgg_winrate / 100) if opgg_winrate else 0.5
    base = store.smoothed("champions", champion_key, prior=prior, k=_K_CHAMPION)
    champion_games = store.games("champions", champion_key)
    logit = _logit(base)
    notes = [
        f"Base {round(base * 100, 1)}% "
        f"(muestra propia: {champion_games} partidas"
        + (f", prior op.gg {opgg_winrate}%" if opgg_winrate else "")
        + ")"
    ]
    evidence = champion_games

    for enemy in enemy_keys:
        key = f"{champion_key}_vs_{enemy}"
        games = store.games("matchups", key)
        if games == 0:
            continue
        adjusted = store.smoothed("matchups", key, prior=base, k=_K_MATCHUP)
        delta = _logit(adjusted) - _logit(base)
        logit += delta
        evidence += games
        notes.append(
            f"Matchup vs #{enemy}: {round(adjusted * 100, 1)}% en {games} partidas "
            f"({'+' if delta >= 0 else ''}{round(delta, 2)} logit)"
        )

    for ally in ally_keys:
        if ally == champion_key:
            continue
        key = "_con_".join(map(str, sorted((champion_key, ally))))
        games = store.games("duos", key)
        if games == 0:
            continue
        adjusted = store.smoothed("duos", key, prior=base, k=_K_DUO)
        delta = _logit(adjusted) - _logit(base)
        logit += delta
        evidence += games

    return WinProbability(
        probability=round(_sigmoid(logit) * 100, 1),
        champion_games=champion_games,
        evidence_games=evidence,
        notes=notes,
    )


@dataclass
class BuildSuggestion:
    entity_id: str
    name: str
    score: float  # winrate suavizado 0-100 condicionado al draft
    games: int  # muestra del campeón con ese ítem/runa


def _rank_for_champion(
    store: WinrateStore,
    champion_key: int,
    enemy_keys: list[int],
    champ_kind: str,
    vs_kind: str,
    global_kind: str,
    names: dict[str, str],
    k_champ: int,
    k_vs: int,
    top: int = 6,
    min_games: int = 3,
) -> list[BuildSuggestion]:
    """
    Rankea ítems/runas que el campeón realmente usa (champ_kind), ajustando
    por su éxito contra los enemigos elegidos (vs_kind).
    """
    prefix = f"{champion_key}_"
    suggestions = []
    for key in store.keys_for_prefix(champ_kind, prefix):
        entity_id = key[len(prefix):]
        if entity_id not in names:
            continue  # ítem de otro parche / runa desconocida
        games = store.games(champ_kind, key)
        if games < min_games:
            continue
        global_prior = store.smoothed(global_kind, entity_id, prior=0.5, k=k_champ)
        base = store.smoothed(champ_kind, key, prior=global_prior, k=k_champ)
        logit = _logit(base)
        for enemy in enemy_keys:
            vs_key = f"{entity_id}_vs_{enemy}"
            if store.games(vs_kind, vs_key) == 0:
                continue
            adjusted = store.smoothed(vs_kind, vs_key, prior=base, k=k_vs)
            logit += _logit(adjusted) - _logit(base)
        suggestions.append(
            BuildSuggestion(
                entity_id=entity_id,
                name=names[entity_id],
                score=round(_sigmoid(logit) * 100, 1),
                games=games,
            )
        )
    suggestions.sort(key=lambda s: -s.score)
    return suggestions[:top]


def suggest_items(
    store: WinrateStore,
    champion_key: int,
    enemy_keys: list[int],
    item_names: dict[str, str],
    top: int = 6,
) -> list[BuildSuggestion]:
    """Ítems que el campeón usa, rankeados por éxito contra estos enemigos."""
    return _rank_for_champion(
        store, champion_key, enemy_keys,
        champ_kind="champ_items", vs_kind="item_vs", global_kind="items",
        names=item_names, k_champ=_K_ITEM, k_vs=_K_ITEM_VS, top=top,
    )


def suggest_keystones(
    store: WinrateStore,
    champion_key: int,
    enemy_keys: list[int],
    keystone_names: dict[str, str],
    top: int = 3,
) -> list[BuildSuggestion]:
    """Runas clave que el campeón usa, rankeadas por éxito contra estos enemigos."""
    return _rank_for_champion(
        store, champion_key, enemy_keys,
        champ_kind="champ_keystones", vs_kind="keystone_vs", global_kind="keystones",
        names=keystone_names, k_champ=_K_ITEM, k_vs=_K_ITEM_VS, top=top,
    )


def entity_names_from_service(service: Any) -> tuple[dict[str, str], dict[str, str]]:
    """(nombres de ítems por id, nombres de runas por id) desde Data Dragon."""
    item_names = {iid: item["name"] for iid, item in service.ddragon.items().items()}
    keystone_names: dict[str, str] = {}
    for tree in service.rune_trees():
        for slot in tree["slots"]:
            for perk in slot["runes"]:
                keystone_names[str(perk["id"])] = perk["name"]
    return item_names, keystone_names
