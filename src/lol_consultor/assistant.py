"""
Asistente de chat en lenguaje natural sobre League of Legends.

Usa un LLM local vía Ollama (gratis, sin API key) con tool use: el modelo
decide qué consultar (campeones, habilidades, counters, ítems, runas,
historial de parches) y este módulo ejecuta esas consultas contra LoLService.

Si Ollama no está corriendo o el modelo no está descargado, el asistente se
degrada con un mensaje de ayuda en vez de romper la app.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ollama import Client

from lol_consultor import config
from lol_consultor.draft import DraftAnalyzer
from lol_consultor.gamewiki import MECANICAS, buscar_mecanica
from lol_consultor.service import LoLService
from lol_consultor.textutil import item_description_sections, strip_tags

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 6

_SYSTEM_PROMPT = (
    "Eres un asistente experto en League of Legends. Respondes SIEMPRE en español, "
    "de forma concreta y breve — incluso cuando las herramientas devuelvan texto en "
    "inglés, tu respuesta final debe estar en español (traduce lo relevante y conserva "
    "los nombres propios de habilidades/ítems).\n"
    "REGLA OBLIGATORIA: nunca respondas de memoria. Antes de responder llama a la "
    "herramienta correspondiente y basa tu respuesta EXCLUSIVAMENTE en lo que devuelva:\n"
    "- Mecánicas del juego (tenacidad, armadura, penetración, omnivamp, CC, oro, visión...) "
    "-> explicar_dinamica\n"
    "- Qué campeón elegir/pickear en un draft -> analizar_draft\n"
    "- Resumen de un campeón -> detalle_campeon | counters y winrates -> meta_campeon\n"
    "- Detalles FINOS de habilidades (resets, cifras por nivel, interacciones) "
    "-> habilidades_detalladas (fuente: wikilol, la más precisa)\n"
    "- Ítems -> buscar_items | runas -> arboles_runas | cambios de balance -> historial_parches\n"
    "Si la herramienta contradice lo que creías, la herramienta tiene razón. "
    "Si una herramienta no devuelve datos, dilo claramente; no inventes cifras. "
    "Si ni siquiera habilidades_detalladas menciona el detalle preguntado, responde que las "
    "fuentes no lo especifican en vez de afirmarlo o negarlo categóricamente. "
    "Los counters provienen de op.gg (comunidad), el detalle de habilidades de la wiki de la "
    "comunidad y el resto de datos oficiales de Riot."
)

_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "listar_campeones",
            "description": "Lista los nombres de todos los campeones disponibles.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detalle_campeon",
            "description": (
                "Detalle de un campeón: rol, dificultad, pasiva y habilidades Q/W/E/R "
                "con su descripción, y consejos oficiales para jugarlo y contrarrestarlo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del campeón, ej. 'Ahri'"}
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "meta_campeon",
            "description": (
                "Estadísticas de meta actuales de un campeón (op.gg): winrate, pickrate, "
                "banrate por posición y sus counters (campeones contra los que pierde más)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del campeón"}
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_items",
            "description": (
                "Busca ítems legendarios por texto en su nombre o descripción "
                "(ej. 'robo de vida', 'crítico', 'armadura')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string", "description": "Texto a buscar"}
                },
                "required": ["texto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "arboles_runas",
            "description": "Lista los árboles de runas con sus runas clave (keystones).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "historial_parches",
            "description": "Cambios de balance recientes de un campeón (wiki de la comunidad).",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del campeón"}
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "habilidades_detalladas",
            "description": (
                "Detalle COMPLETO de las habilidades de un campeón desde la wiki de la "
                "comunidad: cooldowns, costos, daños por nivel, resets e interacciones. "
                "Úsala para preguntas finas sobre cómo funciona una habilidad."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del campeón"}
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_draft",
            "description": (
                "Recomienda qué campeón elegir del pool del usuario según los picks de "
                "aliados y enemigos (meta, counters, balance AP/AD, composición). "
                "Úsala cuando pregunten qué campeón conviene elegir/pickear."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "enemigos": {
                        "type": "string",
                        "description": "Enemigos separados por coma, ej. 'Yasuo, Lee Sin'",
                    },
                    "aliados": {
                        "type": "string",
                        "description": "Campeones aliados separados por coma (opcional)",
                    },
                },
                "required": ["enemigos"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explicar_dinamica",
            "description": (
                "Explica una mecánica del juego: armadura, resistencia mágica, penetración, "
                "omnivampirismo, tenacidad, tipos de CC, visión, oro, experiencia, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "termino": {"type": "string", "description": "Mecánica a explicar"}
                },
                "required": ["termino"],
            },
        },
    },
]


class LoLAssistant:
    def __init__(
        self,
        service: LoLService,
        model: str = config.OLLAMA_MODEL,
        host: str = config.OLLAMA_HOST,
        client: Any | None = None,
        analyzer: DraftAnalyzer | None = None,
    ) -> None:
        self.service = service
        self.model = model
        self.client = client or Client(host=host)
        self.analyzer = analyzer or DraftAnalyzer(service)

    # ---------- disponibilidad ----------

    def status_message(self) -> str | None:
        """None si el asistente está listo; si no, texto explicando qué falta."""
        try:
            models = [m.model for m in self.client.list().models]
        except Exception:
            return (
                "Ollama no está corriendo. Instálalo desde ollama.com y "
                "arranca la app de Ollama (o ejecuta 'ollama serve')."
            )
        if not any(m and m.startswith(self.model.split(":")[0]) for m in models):
            return (
                f"El modelo '{self.model}' no está descargado. "
                f"Ejecuta: ollama pull {self.model}"
            )
        return None

    # ---------- conversación ----------

    def ask(self, history: list[dict[str, str]], question: str) -> tuple[str, list[dict[str, str]]]:
        """
        history: turnos previos [{'role': 'user'|'assistant', 'content': ...}, ...]
        Devuelve (respuesta, historial_actualizado). Los intercambios internos de
        tools no se persisten en el historial (solo user/assistant).
        """
        messages: list[Any] = [{"role": "system", "content": _SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        try:
            answer = self._run_tool_loop(messages)
        except Exception:
            logger.warning("Fallo consultando a Ollama", exc_info=True)
            answer = (
                "No pude consultar el modelo local. Verifica que Ollama esté "
                "corriendo y que el modelo esté descargado."
            )

        new_history = [
            *history,
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        return answer, new_history

    def _run_tool_loop(self, messages: list[Any]) -> str:
        for _ in range(_MAX_TOOL_ROUNDS):
            # think=True mejora la selección de tools y la aritmética del modelo
            # (el razonamiento viaja aparte, no contamina la respuesta).
            response = self.client.chat(
                model=self.model, messages=messages, tools=_TOOL_SCHEMAS, think=True
            )
            message = response.message
            if not message.tool_calls:
                return (message.content or "").strip() or "No obtuve respuesta del modelo."

            messages.append(message)
            for call in message.tool_calls:
                result = self._dispatch(call.function.name, dict(call.function.arguments))
                messages.append(
                    {"role": "tool", "tool_name": call.function.name, "content": result}
                )
        return "La consulta requirió demasiados pasos; intenta una pregunta más específica."

    # ---------- tools ----------

    def _dispatch(self, name: str, args: dict[str, Any]) -> str:
        handlers: dict[str, Callable[..., str]] = {
            "listar_campeones": self._listar_campeones,
            "detalle_campeon": self._detalle_campeon,
            "meta_campeon": self._meta_campeon,
            "buscar_items": self._buscar_items,
            "arboles_runas": self._arboles_runas,
            "historial_parches": self._historial_parches,
            "habilidades_detalladas": self._habilidades_detalladas,
            "analizar_draft": self._analizar_draft,
            "explicar_dinamica": self._explicar_dinamica,
        }
        handler = handlers.get(name)
        if handler is None:
            return f"Herramienta desconocida: {name}"
        try:
            return handler(**args)
        except TypeError:
            return f"Argumentos inválidos para {name}: {args}"
        except Exception:
            logger.warning("Fallo ejecutando la tool %s", name, exc_info=True)
            return f"Error consultando datos con {name}."

    def _find_champion(self, nombre: str) -> dict[str, Any] | None:
        return self.service.find_champion(nombre)

    def _listar_campeones(self) -> str:
        names = [c["name"] for c in self.service.champion_list()]
        return ", ".join(names)

    def _detalle_campeon(self, nombre: str) -> str:
        champ = self._find_champion(nombre)
        if champ is None:
            return f"No encontré ningún campeón llamado '{nombre}'."
        data = self.service.ddragon.champion(champ["id"])
        roles = ", ".join(data.get("tags", []))
        lines = [
            f"{data['name']} — {data['title']}",
            f"Roles: {roles} | Dificultad: {data['info']['difficulty']}/10",
            f"Pasiva: {data['passive']['name']}: {strip_tags(data['passive']['description'])}",
        ]
        for slot, spell in zip("QWER", data["spells"], strict=False):
            desc = strip_tags(spell.get("description") or "")
            lines.append(
                f"{slot}: {spell['name']} (enfriamiento {spell.get('cooldownBurn', '?')}s): {desc}"
            )
        if data.get("allytips"):
            lines.append("Consejos para jugarlo: " + " | ".join(map(strip_tags, data["allytips"])))
        if data.get("enemytips"):
            lines.append(
                "Consejos para enfrentarlo: " + " | ".join(map(strip_tags, data["enemytips"]))
            )
        return "\n".join(lines)

    def _meta_campeon(self, nombre: str) -> str:
        champ = self._find_champion(nombre)
        if champ is None:
            return f"No encontré ningún campeón llamado '{nombre}'."
        meta = self.service.opgg.champion_meta(int(champ["key"]))
        if meta is None or not meta.positions:
            return f"op.gg no tiene datos de meta disponibles para {champ['name']} ahora mismo."
        by_key = self.service.champions_by_key()
        lines = [f"Meta actual de {champ['name']} (op.gg, Esmeralda+):"]
        for pos in meta.positions:
            lines.append(
                f"- {pos.position}: winrate {pos.win_rate}%, pickrate {pos.play_rate}%, "
                f"banrate {pos.ban_rate}%"
            )
            for counter in pos.counters:
                rival = by_key.get(counter.champion_id)
                rival_name = rival["name"] if rival else f"#{counter.champion_id}"
                lines.append(
                    f"  * Counter: {rival_name} ({champ['name']} gana solo el "
                    f"{counter.win_rate}% de {counter.games} partidas)"
                )
        return "\n".join(lines)

    def _buscar_items(self, texto: str) -> str:
        needle = texto.strip().lower()
        matches = []
        for item in self.service.legendary_items():
            haystack = (item["name"] + " " + item.get("description", "")).lower()
            if needle in haystack:
                stats, effects = item_description_sections(item.get("description"))
                parts = [f"{item['name']} ({item['gold']['total']} oro)"]
                if stats:
                    parts.append("stats: " + "; ".join(stats))
                if effects:
                    parts.append("efecto: " + effects[0][:200])
                matches.append(" — ".join(parts))
            if len(matches) >= 8:
                break
        return "\n".join(matches) if matches else f"No encontré ítems que mencionen '{texto}'."

    def _arboles_runas(self) -> str:
        lines = []
        for tree in self.service.rune_trees():
            keystones = [perk["name"] for perk in tree["slots"][0]["runes"]]
            lines.append(f"{tree['name']}: keystones {', '.join(keystones)}")
        return "\n".join(lines)

    def _historial_parches(self, nombre: str) -> str:
        champ = self._find_champion(nombre)
        if champ is None:
            return f"No encontré ningún campeón llamado '{nombre}'."
        wiki_title = self.service.english_name(champ["id"]) or champ["name"]
        history = self.service.wiki.champion_patch_history(wiki_title)
        if not history:
            return f"No hay historial de parches disponible para {champ['name']}."
        return history[:2000]

    def _habilidades_detalladas(self, nombre: str) -> str:
        champ = self._find_champion(nombre)
        if champ is None:
            return f"No encontré ningún campeón llamado '{nombre}'."
        wiki_title = self.service.english_name(champ["id"]) or champ["name"]
        abilities = self.service.wiki.champion_abilities(wiki_title)
        if not abilities:
            return f"La wiki no tiene detalle de habilidades para {champ['name']}."
        # La wiki no etiqueta los slots (Q/W/E/R van en iconos que se pierden al
        # limpiar el HTML): anteponer el mapa slot -> nombre en inglés para que
        # el modelo asocie bien cada párrafo.
        slot_map = self._english_slot_map(champ["id"])
        return f"{slot_map}\n\n{abilities[:8000]}" if slot_map else abilities[:8000]

    def _english_slot_map(self, champion_id: str) -> str:
        try:
            data = self.service.ddragon_en.champion(champion_id)
        except Exception:
            return ""
        parts = [f"Pasiva: {data['passive']['name']}"]
        for slot, spell in zip("QWER", data.get("spells", []), strict=False):
            parts.append(f"{slot}: {spell['name']}")
        return "Mapa de habilidades de " + data["name"] + " -> " + " | ".join(parts)

    def _analizar_draft(self, enemigos: str, aliados: str = "") -> str:
        enemy_list = [e.strip() for e in enemigos.split(",") if e.strip()]
        ally_list = [a.strip() for a in aliados.split(",") if a.strip()]
        recs = self.analyzer.analyze(
            pool=config.DEFAULT_POOL,
            role=config.DEFAULT_ROLE,
            allies=ally_list,
            enemies=enemy_list,
        )
        if not recs:
            return "No pude analizar el draft (pool vacío o campeones no reconocidos)."
        lines = [
            f"Recomendación de pick ({config.DEFAULT_ROLE}, pool: "
            f"{', '.join(config.DEFAULT_POOL)}):"
        ]
        for i, rec in enumerate(recs, start=1):
            lines.append(f"{i}. {rec.champion_name} (puntaje {rec.score:+.1f})")
            for factor in rec.factores:
                lines.append(f"   - {factor.descripcion}")
        return "\n".join(lines)

    def _explicar_dinamica(self, termino: str) -> str:
        mecanica = buscar_mecanica(termino)
        if mecanica is None:
            disponibles = ", ".join(m.titulo for m in MECANICAS)
            return f"No tengo esa mecánica documentada. Disponibles: {disponibles}."
        return f"{mecanica.titulo} ({mecanica.categoria}):\n{mecanica.texto}"
