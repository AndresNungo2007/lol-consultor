# LoL Consultor

Interfaz de consulta (Dash) de League of Legends: campeones, ítems, runas,
estilo de juego, meta/counters, análisis de draft, dinámicas del juego y un
asistente de chat con IA local. Se mantiene actualizada sola: cachea por
parche y revisa periódicamente si Riot publicó uno nuevo.

## Fuentes de datos

| Dato | Fuente | Oficial |
|---|---|---|
| Campeones, ítems, runas, hechizos, iconos, tips (allytips/enemytips) | [Data Dragon](https://developer.riotgames.com/docs/lol) | Sí (Riot) |
| Detalle fino de habilidades (resets, cifras por nivel) e historial de parches | [wikilol](https://wiki.leagueoflegends.com) (MediaWiki API) | No (comunidad) |
| Tier list, winrate/pickrate/banrate, counters por matchup | [op.gg](https://op.gg) vía [`OPGG.py`](https://github.com/ShoobyDoo/OPGG.py) | No |
| Winrates de ítems y runas (calculados de partidas reales) | [Riot API](https://developer.riotgames.com) Match-V5 | Sí (Riot, requiere key) |

> Nota: la antigua wiki de Fandom quedó congelada en el parche 14.18 tras la
> migración de la comunidad a wiki.leagueoflegends.com; este proyecto usa la nueva.

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

## Rutinas de actualización

Tres capas mantienen los datos al día:

1. **Cache por parche y TTL (siempre activo):** Data Dragon se cachea por
   versión de parche; wiki (24 h) y op.gg (6 h) por TTL. Al vencer, se
   refrescan en la siguiente consulta.
2. **Refresher en segundo plano (mientras la app corre):** cada
   `LOL_REFRESH_INTERVAL_S` segundos (default 1 h) la app detecta parches
   nuevos (e invalida todos los caches si lo hay), pre-descarga campeones,
   ítems, runas y hechizos, fuerza la actualización del meta de op.gg y
   pre-calienta el pool del usuario.
3. **Script programable (con la app cerrada):**

   ```bash
   python scripts/refresh_data.py            # ciclo estándar
   python scripts/refresh_data.py --completo # + detalle de los ~170 campeones
   ```

   Para programarlo cada hora en Windows (ajusta las rutas):

   ```bat
   schtasks /Create /SC HOURLY /TN "LoLConsultor Refresh" ^
     /TR "\"C:\ruta\.venv\Scripts\python.exe\" \"C:\ruta\scripts\refresh_data.py\""
   ```

## Winrates de ítems y runas

No existe fuente pública que exponga winrates por ítem/runa, así que el
proyecto los **calcula** con la API oficial de Riot. De cada partida ranked
del ladder se agregan varias dimensiones: ítems y runas (globales, por
campeón y contra cada campeón enemigo), winrate por campeón, matchups
(campeón vs campeón) y dúos (aliados juntos). Con eso el análisis de draft
estima la **probabilidad de victoria** (combinación de log-odds con
suavizado bayesiano: con poca muestra tiende al prior en vez de inventar
extremos) y sugiere **ítems y runas según su éxito contra los enemigos
elegidos**.

Opciones del recolector: `--desde/--hasta` (ventanas históricas, match-v5
conserva ~2 años; ojo que ventanas largas mezclan parches) y
`--plataformas la1,la2,br1,na1` (multi-servidor).

```bash
# 1. Key gratuita en https://developer.riotgames.com -> RIOT_API_KEY en .env
#    (la key de desarrollo expira cada 24 h)
# 2. Recolectar (acumula entre ejecuciones; ~3-4 min por cada 100 partidas)
python scripts/collect_winrates.py --partidas 200
```

Los badges aparecen en las pestañas de Ítems y Runas cuando un ítem/runa
tiene al menos 30 apariciones. **Sesgo conocido:** el equipo que va ganando
completa más ítems, así que estos winrates sirven para comparar ítems entre
sí, no como probabilidad causal de victoria.

### Recolección automática en la nube

El workflow [collect-winrates.yml](.github/workflows/collect-winrates.yml)
corre cada 6 horas en GitHub Actions con el secreto `RIOT_API_KEY` del repo,
acumula la muestra y publica el agregado en la rama `winrates-data`. La app
local lo sincroniza en su ciclo de refresco (`LOL_WINRATES_SYNC_URL`), así la
muestra crece aunque tu PC esté apagado.

Cuando la key expira, el job falla y GitHub te avisa por correo: renueva la
key y actualiza el secreto (Settings → Secrets and variables → Actions).
Para no renovar a diario, solicita una **Personal API Key** en
developer.riotgames.com (Register Product → Personal): no expira cada 24 h.

## Análisis de draft

La pestaña "Análisis de draft" recomienda qué campeón elegir de tu pool según
los picks de aliados y enemigos. El puntaje combina: winrate en el meta
(op.gg), counters contra los enemigos elegidos, balance de daño AP/AD del
equipo y aporte de línea de frente. El pool y rol por defecto se configuran
con `LOL_POOL` (nombres separados por coma) y `LOL_ROLE`
(TOP/JUNGLE/MID/ADC/SUPPORT).

Nota: no existe fuente pública de sinergias directas entre aliados; la
"sinergia" se aproxima vía balance de daño y composición.

## Dinámicas del juego

La pestaña "Dinámicas del juego" explica las mecánicas centrales (armadura,
resistencia mágica, penetración, omnivampirismo, tenacidad, tipos de CC,
visión, oro, experiencia...) con contenido curado en español. Son reglas
estables entre parches, por eso viven en el repo y no en una fuente externa.

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
