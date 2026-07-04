# LoL Consultor

Interfaz de consulta (Dash) de League of Legends: campeones, ítems, runas,
estilo de juego, meta/counters y un asistente de chat con IA local. Se
mantiene actualizada sola: cachea por parche y revisa periódicamente si Riot
publicó uno nuevo.

## Fuentes de datos

| Dato | Fuente | Oficial |
|---|---|---|
| Campeones, ítems, runas, hechizos, iconos, tips (allytips/enemytips) | [Data Dragon](https://developer.riotgames.com/docs/lol) | Sí (Riot) |
| Habilidades detalladas | [Community Dragon](https://www.communitydragon.org/) | Sí (Riot) |
| Historial de cambios de balance por campeón | [Fandom Wiki](https://leagueoflegends.fandom.com) (MediaWiki API) | No |
| Tier list, winrate/pickrate/banrate, counters por matchup | [op.gg](https://op.gg) vía [`OPGG.py`](https://github.com/ShoobyDoo/OPGG.py) | No |

**Fuera de alcance:** build de ítems y página de runas recomendada de op.gg
(se cargan client-side vía su API privada, no hay endpoint público ni
librería mantenida que los exponga) y u.gg (su `robots.txt` bloquea
explícitamente a `ClaudeBot`, así que no se automatizan peticiones ahí).

Las fuentes no oficiales (wiki, op.gg) están aisladas en su propio conector
con caching y **degradación elegante**: si fallan, la app sigue funcionando
y esa sección muestra un aviso en vez de romperse.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
```

## Uso

```bash
python scripts/run_dash.py
```

Abre `http://localhost:8050`.

Variables de entorno disponibles en [.env.example](.env.example) (cópialo a
`.env` para sobreescribir defaults).

## Asistente IA (chat)

La pestaña "Asistente IA" permite preguntar en lenguaje natural ("¿quién
counterea a Yasuo?", "¿qué ítems dan robo de vida?"). Usa un LLM **local y
gratuito** vía [Ollama](https://ollama.com) con tool use: el modelo decide qué
consultar y la app ejecuta esas consultas contra las fuentes de datos.

Requisitos (una sola vez):

```bash
# 1. Instalar Ollama (Windows: winget install Ollama.Ollama)
# 2. Descargar el modelo (~5 GB; corre bien con GPU de 8+ GB VRAM)
ollama pull qwen3:8b
```

Si Ollama no está corriendo, la pestaña muestra instrucciones en vez de
romperse. El modelo y host se configuran con `LOL_OLLAMA_MODEL` y
`LOL_OLLAMA_HOST`.

## Tests y calidad

```bash
pytest
ruff check .
mypy src
```

## Docker

```bash
docker build -t lol-consultor .
docker run -p 8050:8050 -v lol_cache:/data lol-consultor
```

## Arquitectura

```
src/lol_consultor/
├── connectors/       # un conector por fuente externa (ddragon, fandom_wiki, opgg_meta)
├── cache.py          # cache genérico en disco con TTL (wiki, op.gg)
├── models.py         # dataclasses tipadas para los datos de op.gg
├── service.py        # fachada que combina los conectores para la UI
├── assistant.py      # chat IA local (Ollama + tool use sobre LoLService)
└── app/              # app Dash (factory + páginas por pestaña)
```

## Aviso legal

LoL Consultor no está afiliado a Riot Games y no refleja sus puntos de vista
ni los de nadie oficialmente involucrado en producir o gestionar League of
Legends. League of Legends y Riot Games son marcas registradas o marcas
comerciales de Riot Games, Inc. Los datos de op.gg y de la wiki de Fandom
pertenecen a sus respectivas comunidades/plataformas y no son oficiales de
Riot.
