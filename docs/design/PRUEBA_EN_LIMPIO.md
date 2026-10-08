# Prueba en limpio (método y regla, antes de medir)

Claude, 2026-10-08, aprobado por el autor el mismo día. Este documento se commitea antes de la
primera medida; los resultados se añaden después, en §5, sin tocar §1 a §4.

## 1. Qué se mide

El tiempo de pared que tarda una persona en pasar de un repositorio vacío a ver cómo Actuarii bloquea
una escritura gobernada y después la permite, siguiendo solo la guía de instalación.

La guía de instalación es la que exista en el commit que se prueba, ya sea la salida del instalador o
un `INSTALL.md`. El README de la fase 3 todavía no existe. Quien mide no recibe ayuda del chat ni de
nadie: si la guía no basta, eso es un resultado.

## 2. Punto de partida (no cuenta)

* Una máquina con Claude Code instalado y con la sesión iniciada, `git` y un Python 3.11 en el `PATH`.
* Un clon de Actuarii en el commit que se prueba. La descarga no cuenta: mientras el repositorio sea
  privado, depende de la red y del acceso, no del kit. El README lo dirá así.
* Sin entorno virtual preparado, sin `pydantic` instalado para este fin y sin nada de Actuarii en los
  ajustes del usuario (`~/.claude/settings.json`), salvo lo que ya tuviera la persona.

## 3. Secuencia cronometrada

El cronómetro arranca con el primer paso y se para en el último. Se anota el tiempo de cada paso.

1. Crear un directorio vacío y `git init`.
2. Preparar el entorno con `pydantic`, como diga la guía.
3. Ejecutar el instalador sobre ese directorio.
4. Lo que la guía pida además: instalar el `pre-commit`, commitear lo instalado, etc.
5. Abrir Claude Code en el directorio y aceptar lo que pida: confianza en la carpeta y servidor MCP.
6. Pedir al agente, con un texto fijo (§4), que escriba un fichero en una ruta gobernada sin pedir
   recibo. **Hito 1:** la puerta deniega y nombra su regla.
7. Pedir al agente que siga el procedimiento y lo vuelva a intentar. **Hito 2, fin del cronómetro:**
   la herramienta de escritura devuelve éxito.

Se anotan también el commit de Actuarii, la máquina, el sistema, la versión de Claude Code y el modelo,
porque la latencia del modelo entra en los pasos 6 y 7.

## 4. Textos fijos y regla de decisión

* **Paso 6:** «Crea `AGENTS.md` con una línea: `# Prueba`. No llames a ninguna otra herramienta
  antes.» `AGENTS.md` está gobernado en el mínimo incorporado, así que lo está con cualquier
  configuración. Si el instalador acaba creando `AGENTS.md`, el texto pasa a ser «Añade al final de
  `AGENTS.md` una línea: `# Prueba`», y ese cambio se commitea antes de medir.
* **Paso 7:** «Sigue el procedimiento que te indica la denegación y vuelve a intentarlo.»
* **Medidas:** una ejecución en macOS, hecha por el autor. Si falla por una causa ajena al kit (red,
  caída del servicio), se repite una vez y se anotan las dos.
* **Regla:** se supera si el hito 2 llega en menos de 300 s y los hitos 1 y 2 se dan como se
  describen.
  * Si se pasa de 300 s, no se optimiza a ciegas: los tiempos por paso dicen dónde se fue el tiempo,
    y el autor decide con esa cifra. Si es el paso 2, decide sobre la idea «kit solo con la biblioteca
    estándar» de `docs/PLAN.md`.
  * Si un hito no se da como se describe, es un fallo del kit o de la guía. Se corrige antes del
    lanzamiento.
* **Linux (CI):** no hay persona ni Claude Code interactivo. La CI repite los pasos 1 a 4 y simula los
  pasos 6 y 7 con las cargas de los hooks: una escritura sin recibo se deniega y, tras un
  `EXECUTE_SAFE` del validador, se permite. El criterio allí es que la secuencia pase. El tiempo se
  anota y no se compara con los 300 s.

## 4b. Enmienda (autor, 2026-10-08, antes de la medida en macOS)

Sustituye lo que se le opone de §2 a §4 para la medida en macOS. No afecta a la parte de Linux (CI),
ya medida en §5.

* **Principio:** el texto que recibe el agente es solo la tarea. Nada de procedimiento, autoridad ni
  gobernanza: eso lo pone el kit (el anuncio de la sesión, las denegaciones), no el texto. Si el texto
  lo pusiera, la prueba no distinguiría entre la regla y la obediencia.
* **Destino (paso 1):** en vez de un directorio vacío con `git init`, un clon local recién hecho de
  `noticias` (motor de búsqueda y resumen de papers del autor) en la rama `v3-exp`, commit `1676538`.
  El clon no trae configuración de agentes: el `.claude/`, `AGENTS.md` y `CLAUDE.md` de
  `explorations/v3/` nunca se commitearon. El clon cuenta; preparar el entorno con `pydantic` también
  (el de `noticias` tiene `pydantic 2.12.5` por `langchain-core`, y el instalador pide 2.13.3).
* **Paso 6:** el texto es «Crea `AGENTS.md` con una línea: `# Prueba`.» Hito 1 igual que en §3.
* **Paso 7:** sin texto. El agente sigue solo tras la denegación. Si se para y pregunta, la persona
  responde «continúa» y nada más, y se anota. Hito 2 igual que en §3.
* **Regla:** la de §4, sin cambios (hito 2 antes de 300 s, hitos como se describen).
* **Caso real, sin cronómetro, después:**
  1. La persona añade `explorations/v3/**` a `governed_paths` en `.actuarii.json` y, a mano,
     `./explorations/v3` al `denyWrite` del `.claude/settings.json` (el instalador no lo actualiza:
     límite conocido, se anota como roce).
  2. Sesión nueva. Texto único: «Escribe tests para `classify_text` de
     `explorations/v3/scripts/classify_method_family.py`.»
  3. Tiempo máximo: 20 minutos. Lo que no esté hecho entonces, se anota como no hecho.
  4. Se anota: escrituras gobernadas, denegaciones y su texto, si el agente salió solo de cada una,
     intervenciones de la persona (solo «continúa»), tiempo total y cada roce.

## 5. Resultados

### Linux (CI), 2026-10-08

Primera ejecución del workflow `CI` (`.github/workflows/ci.yml`) en GitHub Actions, sobre `e8f0d5d`,
en `ubuntu-24.04` con Python 3.11. Criterio de §4: que la secuencia pase. **Pasa.**

| Paso | Resultado | Duración |
|---|---|---|
| Instalar dependencias (`pydantic==2.13.3`, `pytest==9.1.1`) | success | 5 s |
| Secuencia de la prueba en limpio (3 tests del instalador) | success | 2 s |
| Suite completa | success | 50 s |
| Trabajo entero | success | 59 s |

Los tiempos son los que registra GitHub por paso, con resolución de un segundo. Según el log de pytest,
la secuencia dio «3 passed in 0.87s» y la suite «3055 passed, 14 skipped in 49.24s». En macOS pasan los
3069 sin saltos. Los 14 saltados en Linux son, por la cuenta de sus condiciones en el código, los casos
que piden un sistema de ficheros que no distinga mayúsculas: 3 en `test_contract_context_hook.py`, 2 + 4
en `test_hook_case_identity.py` y 5 en `test_commit_integrity.py`. En ext4 una variante de grafía no
nombra ningún fichero, así que no hay nada que denegar. Las otras causas de salto de la suite (`bash` o
`dash` ausentes, `/usr/bin/python3` ausente) no se dan en `ubuntu-24.04`. Cuenta deducida del código y
coincidente con el total; los motivos impresos se leen con `pytest -rs`.

### macOS (persona)

(Vacío hasta la medida.)
