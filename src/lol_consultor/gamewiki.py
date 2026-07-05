"""
Dinámicas del juego: explicaciones curadas (en español) de las mecánicas
centrales de League of Legends. Contenido estático porque estas reglas son
estables entre parches; los valores numéricos de campeones/ítems concretos
se consultan en las otras secciones (que sí se actualizan por parche).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mecanica:
    id: str
    titulo: str
    categoria: str
    texto: str
    wiki_page: str | None = None  # título de página en wiki.leagueoflegends.com


MECANICAS: list[Mecanica] = [
    Mecanica(
        id="armadura",
        wiki_page="Armor",
        titulo="Armadura",
        categoria="Defensa",
        texto=(
            "Reduce el daño físico recibido. La reducción porcentual es "
            "armadura / (100 + armadura): con 100 de armadura recibes 50% menos daño físico; "
            "con 200, 66% menos. Tiene rendimientos decrecientes: cada punto adicional 'vale' "
            "un poco menos en porcentaje, pero cada punto aumenta tu vida efectiva contra "
            "daño físico de forma lineal (1% de tu vida por cada punto). "
            "Se compra en ítems como Malla de espinas o Corazón de acero, y algunos campeones "
            "la ganan con habilidades."
        ),
    ),
    Mecanica(
        id="resistencia-magica",
        wiki_page="Magic resistance",
        titulo="Resistencia mágica",
        categoria="Defensa",
        texto=(
            "Igual que la armadura pero contra daño mágico: reducción = RM / (100 + RM). "
            "Los campeones cuerpo a cuerpo suelen ganar algo de RM por nivel; los a distancia no, "
            "por eso los magos 'queman' más fácil a los tiradores. Ítems típicos: "
            "Buscador de la fuerza vital, Égida de fuego solar (híbrido), "
            "Bendición de Mikael (aliados)."
        ),
    ),
    Mecanica(
        id="penetracion",
        wiki_page="Armor penetration",
        titulo="Penetración y letalidad",
        categoria="Daño",
        texto=(
            "La penetración ignora parte de las resistencias del objetivo. Hay cuatro variantes:\n"
            "- Letalidad: penetración de armadura plana (escala con tu nivel).\n"
            "- Penetración de armadura porcentual (ej. Recordatorio mortal): "
            "ignora un % de la armadura.\n"
            "- Penetración mágica plana (ej. Zapatos del hechicero).\n"
            "- Penetración mágica porcentual (ej. Vara del vacío).\n"
            "Se aplica primero la porcentual y luego la plana. La penetración nunca convierte la "
            "resistencia en negativa; solo las reducciones de resistencias pueden."
        ),
    ),
    Mecanica(
        id="golpe-critico",
        wiki_page="Critical strike",
        titulo="Golpe crítico",
        categoria="Daño",
        texto=(
            "Probabilidad de que un ataque básico inflija 175% del daño normal (la mayoría de "
            "tiradores construyen 100% de crítico para que todos sus ataques sean críticos). "
            "Filo infinito aumenta el daño crítico. Algunas habilidades que 'aplican efectos de "
            "ataque' también pueden criticar. El crítico no afecta el daño de habilidades normales."
        ),
    ),
    Mecanica(
        id="velocidad-ataque",
        wiki_page="Attack speed",
        titulo="Velocidad de ataque",
        categoria="Daño",
        texto=(
            "Cuántos ataques básicos haces por segundo. Cada campeón tiene una velocidad base y "
            "un 'ratio': los aumentos porcentuales de ítems/runas "
            "multiplican el ratio, no la base, "
            "por eso el mismo ítem rinde distinto en distintos campeones. El límite estándar es "
            "2.5 ataques/segundo (algunos efectos lo superan). Ítems clave: Filo de Guinsoo, "
            "Huracán de Runaan, Berserkers."
        ),
    ),
    Mecanica(
        id="aceleracion-habilidades",
        wiki_page="Haste",
        titulo="Aceleración de habilidades",
        categoria="Utilidad",
        texto=(
            "Reduce los enfriamientos de habilidades. La reducción porcentual equivalente es "
            "aceleración / (100 + aceleración): 100 de aceleración = enfriamientos 50% más cortos "
            "(lanzas el doble de habilidades). A diferencia de la antigua "
            "'reducción de enfriamiento', "
            "no tiene tope y escala linealmente: cada 10 puntos siempre añaden un 10% más de "
            "lanzamientos por minuto."
        ),
    ),
    Mecanica(
        id="robo-vida",
        wiki_page="Life steal",
        titulo="Robo de vida",
        categoria="Sustain",
        texto=(
            "Te cura un porcentaje del daño que infligen tus ataques básicos (y efectos que "
            "cuentan como ataque). No aplica a habilidades. Ítems típicos: Sanguinaria, "
            "Hidra voraz. Se reduce con Heridas graves."
        ),
    ),
    Mecanica(
        id="omnivampirismo",
        wiki_page="Omnivamp",
        titulo="Omnivampirismo",
        categoria="Sustain",
        texto=(
            "Como el robo de vida, pero cura por TODO el daño que infliges: ataques, habilidades, "
            "ítems e incluso daño en área (aunque históricamente el daño en área ha curado a un "
            "ratio reducido según la versión del juego). Es más raro y más caro de obtener que el "
            "robo de vida. Aparece en runas y en ítems selectos según el parche."
        ),
    ),
    Mecanica(
        id="curaciones-escudos",
        wiki_page="Shield",
        titulo="Curaciones y escudos",
        categoria="Sustain",
        texto=(
            "Las curaciones restauran vida; los escudos añaden vida temporal que se consume antes "
            "que la vida real y expira a los pocos segundos. El 'poder de curación y escudos' "
            "(ej. Redención, Ardent Censer) amplifica ambos. Los escudos no se ven afectados por "
            "Heridas graves, pero sí existen efectos anti-escudo (ej. Segadora de escudos)."
        ),
    ),
    Mecanica(
        id="heridas-graves",
        wiki_page="Grievous Wounds",
        titulo="Heridas graves (antisanación)",
        categoria="Sustain",
        texto=(
            "Reduce toda la curación que recibe el objetivo (robo de vida, omnivampirismo, "
            "habilidades de curación y pociones) durante unos segundos. Se aplica con ítems "
            "(Llamado del verdugo / Recordatorio mortal para AD; Orbe del olvido / Morellonomicón "
            "para AP), con el hechizo Prender y con algunas habilidades de campeón. Es la "
            "respuesta estándar a composiciones con mucho sustain."
        ),
    ),
    Mecanica(
        id="tenacidad",
        wiki_page="Tenacity",
        titulo="Tenacidad (reducción de CC)",
        categoria="Control",
        texto=(
            "Reduce la DURACIÓN del control de masas que recibes: aturdimientos, ralentizaciones, "
            "enraizamientos, silencios, etc. NO reduce el daño, y NO afecta: "
            "knockups/desplazamientos (la R de Malphite dura lo mismo con o sin tenacidad) ni "
            "supresiones (R de Malzahar/Warwick). "
            "Fuentes: Mercuriales (botas), runa Leyenda: Tenacidad, Elixir de hierro. "
            "Varias fuentes se combinan MULTIPLICATIVAMENTE, no se suman: la duración restante "
            "se multiplica. Ejemplo: con 30%, 20% y 20% de tenacidad, la duración del CC es "
            "0.70 x 0.80 x 0.80 = 0.448, es decir 44.8% de la duración original, equivalente a "
            "55.2% de tenacidad total (no 70%)."
        ),
    ),
    Mecanica(
        id="tipos-cc",
        wiki_page="Crowd control",
        titulo="Tipos de control de masas (CC)",
        categoria="Control",
        texto=(
            "- Aturdimiento (stun): no puedes moverte ni actuar.\n"
            "- Enraizamiento (root): no puedes moverte, pero sí atacar/lanzar "
            "habilidades sin desplazamiento.\n"
            "- Ralentización (slow): velocidad de movimiento reducida.\n"
            "- Silencio: no puedes lanzar habilidades.\n"
            "- Desarme: no puedes hacer ataques básicos.\n"
            "- Encanto/Miedo/Provocación: pierdes el control del movimiento de tu campeón.\n"
            "- Knockup/Desplazamiento: inmune a tenacidad; solo se limpia con "
            "inmunidades (QSS no lo quita).\n"
            "- Supresión: como aturdimiento, pero no se reduce con tenacidad "
            "(sí se limpia con QSS).\n"
            "- Sueño: incapacitado hasta recibir daño."
        ),
    ),
    Mecanica(
        id="velocidad-movimiento",
        wiki_page="Movement speed",
        titulo="Velocidad de movimiento",
        categoria="Utilidad",
        texto=(
            "Unidades de distancia por segundo (la base típica es 325-355). Los aumentos "
            "porcentuales y planos se combinan, pero por encima de ~415 y ~490 se aplican "
            "penalizaciones progresivas (soft caps) para que nadie sea infinitamente rápido. "
            "Las ralentizaciones más fuertes tienen prioridad y las múltiples ralentizaciones "
            "se aplican con rendimientos decrecientes."
        ),
    ),
    Mecanica(
        id="experiencia-niveles",
        wiki_page="Experience (champion)",
        titulo="Experiencia y niveles",
        categoria="Economía",
        texto=(
            "Se gana por súbditos/monstruos cercanos (no hace falta rematarlos) y por "
            "asesinatos/asistencias. Compartir carril divide la experiencia: por eso el soporte "
            "va detrás en niveles. La jungla tiene su propia curva vía monstruos. Los niveles "
            "suben stats base y permiten subir habilidades (nivel 6/11/16 para la definitiva). "
            "Estar muerto o lejos del mapa te atrasa: la ventaja de niveles suele pesar más que "
            "la de oro en el juego temprano."
        ),
    ),
    Mecanica(
        id="oro-ingresos",
        wiki_page="Gold",
        titulo="Oro e ingresos",
        categoria="Economía",
        texto=(
            "Fuentes: oro pasivo por segundo, último golpe a súbditos (CS), monstruos, torres "
            "(placas antes del minuto 14), asesinatos/asistencias y objetivos. Un asesinato "
            "estándar da 300 de oro; las rachas aumentan la recompensa del que las corta "
            "(shutdown). El CS es la fuente más estable: ~14 súbditos ≈ 300 de oro. Los soportes "
            "compensan con su ítem de soporte que genera oro por ejecutar o dañar."
        ),
    ),
    Mecanica(
        id="vision",
        wiki_page="Sight",
        titulo="Visión y wards",
        categoria="Utilidad",
        texto=(
            "El mapa está cubierto por niebla de guerra. Fuentes de visión: wards furtivos "
            "(baratija amarilla, límite 3 por jugador), wards de control (rosados, revelan "
            "wards enemigos e invisibilidad, límite 1), baratija azul (lente lejano) y el "
            "barrido (lente rojo) para negar visión enemiga. La puntuación de visión mide "
            "wards puestos/destruidos. El control de visión alrededor de objetivos (dragón, "
            "barón) suele decidir las peleas importantes."
        ),
    ),
    Mecanica(
        id="escalado-stats",
        wiki_page="Ability power",
        titulo="Escalado y ratios (AP/AD)",
        categoria="Daño",
        texto=(
            "Las habilidades tienen daño base + ratios: '+80% AP' significa que ganas 0.8 de "
            "daño por cada punto de poder de habilidad. 'AD adicional' cuenta solo el AD de "
            "ítems/runas; 'AD total' incluye el base. Por eso algunos campeones escalan mejor "
            "con ítems que otros: compara los ratios, no solo el daño base. Los perfiles de "
            "daño del equipo (mucho AD vs mucho AP) importan porque el rival puede apilar una "
            "sola resistencia si tu daño es monocromático."
        ),
    ),
]


def buscar_mecanica(termino: str) -> Mecanica | None:
    """Búsqueda tolerante por id o título (coincidencia parcial, sin mayúsculas)."""
    needle = termino.strip().lower()
    if not needle:
        return None
    for m in MECANICAS:
        if m.id == needle or m.titulo.lower() == needle:
            return m
    for m in MECANICAS:
        if needle in m.titulo.lower() or needle in m.id:
            return m
    for m in MECANICAS:
        if needle in m.texto.lower():
            return m
    return None


def categorias() -> list[str]:
    vistas: list[str] = []
    for m in MECANICAS:
        if m.categoria not in vistas:
            vistas.append(m.categoria)
    return vistas
