# Actuarii — plan y traspaso

Escrito el 2026-10-05 en la sesión de Traianus que decidió la extracción. Es el punto de partida de la
primera sesión abierta en este repositorio. Las decisiones marcadas «autor» son del autor; el resto son
propuestas.

## Qué es

Un kit para gobernar agentes de código con reglas que se cumplen en código, no por instrucción:

* **Puerta de propuestas:** un servidor MCP valida cada mutación (esquema de 5 Radicales) y deja un
  rastro de auditoría en SQLite.
* **Escritura con recibo:** un hook bloquea `Edit`/`Write` en rutas gobernadas si no hay un
  `EXECUTE_SAFE` reciente para ese fichero.
* **Revisión ciega:** con un paquete de revisión bloqueado, el hook de lectura deniega todo lo que
  queda fuera del paquete.
* **Contexto obligatorio:** las rutas registradas no se editan sin un recibo de que se sirvieron las
  secciones del contrato que les tocan.
* **Python cerrado:** un shim deja ejecutar solo scripts commiteados.
* **Delegación por contrato:** JSON estricto (Pydantic) para encargar trabajo a un subagente y para
  recibir su informe.

Nació gobernando Traianus. Ese repositorio es su caso de uso real.

## Decisiones tomadas (autor, 2026-10-05)

* **Nombre:** Actuarii.
* **Licencia:** Apache-2.0.
* **Historia:** conservada con `git filter-repo`, como en Polar Projector.
* **Relación con Traianus:**
  * Este repositorio es el canónico.
  * Traianus guarda una copia vendorizada, porque su `pyproject.toml` está congelado (AGENTS 1.5 de
    Traianus).
  * Los cambios entran aquí primero y se portan a mano.
  * Cuando Traianus levante la congelación, pasa a depender del paquete.
* **Orden:** primero el kit, que se usa sin Traianus. Traianus como memoria de agentes viene
  después, y solo si el kit da señal (ver «Fase 4»).

## Estado inicial

* **Origen:**
  * Clon de Traianus en `HEAD` `49d2434`, filtrado a las rutas del kit.
  * Se incluyeron también las rutas antiguas (`traianus/security/`, `tools/governance/`,
    `tools/schemas/`, `tools/tridenguard_validator.py`) para no perder historia.
* **Repositorio:**
  * 123 commits y 65 ficheros, todos idénticos byte a byte a los de Traianus.
  * Sin remoto y sin ningún commit propio.
* **Dependencias:**
  * Código: solo `pydantic`. El servidor MCP está escrito a mano sobre stdio.
  * Tests: el código no importa `traianus`; algunos tests todavía sí.

**Acoplamientos que quedan:**

| Dónde | Qué |
|---|---|
| `tests/conftest.py` | Importa el motor entero (FastAPI, storage, bootstrap, encoder falso). Del kit solo hace falta `sys.path` y `isolate_audit_db`. Hay que mirar qué usan de `isolate_db` `test_hook_gate`, `test_hook_case_identity` y `test_audit_database`. |
| `tests/security/test_ingesta_idempotency.py`, `test_internal_error_masking.py` | Tests del motor; fuera. |
| `tests/security/test_security.py` | Todos son del motor salvo `test_boundary_validator_gate`, que se queda. |
| `tests/security/test_audit_database.py` | Importa `traianus.storage` para comprobar que el validador no usa la base del motor. Hay que reformularlo sin el motor. |
| `tools/boundary_validator/hook_gate.py:28-30` | Rutas gobernadas fijas (`traianus`, `tests`, `AGENTS.md`, `docs/specifications`, `tools/boundary_validator`). |
| `tools/bin/python3` (y `python`, `python3.11`), `tools/hooks/deny_python_escapes.py` | Directorios permitidos fijos (`tools/`, `traianus/`). |
| `tools/hooks/contract_registry.json` | Reglas de Traianus (K6, R4, ruta de vectores); pasa a ser un ejemplo. |
| `.claude/settings.json`, `.mcp.json` | Hooks con ruta relativa: un `cd` los rompe todos (issue #89 de Traianus). `.mcp.json` declara `spectral-math-engine`, que no viene. |
| `AGENTS.md`, `.claude/agents/*`, skills, mensajes de los hooks | Hablan de Traianus y citan cláusulas suyas. |
| `.gitignore` | El de Traianus. |

**Comportamiento esperado:** mientras `hook_gate.py` gobierne `tests/**`, el propio kit bloquea las
ediciones en `tests/` de este repositorio hasta que el validador dé `EXECUTE_SAFE`. Es correcto: el
kit se gobierna a sí mismo desde el primer commit.

## Fases

### Fase 0 — línea base en verde

* **Objetivo:** que la suite del kit pase sin Traianus instalado.
* **Pasos:**
  * Quitar los tests del motor.
  * Un `conftest.py` mínimo.
  * Un `pyproject.toml` provisional (`pydantic` y `pytest`).
  * `CLAUDE.md` con `@AGENTS.md` y `@docs/PLAN.md`.
* **Hecho cuando:** `pytest tests/` está en verde en un entorno virtual sin `traianus`. Se anota el
  número de tests.
* **Resultado (2026-10-05, `c23f421`):** 1497 pasan y 3 se saltan en un `.venv` con solo
  `pydantic==2.13.3` y `pytest`. Se quitaron los tests del motor y los que leían documentos de
  Traianus; los de grounding apuntan a `tools/boundary_validator/validator.py`. Un test nuevo
  (`tests/unit/test_kit_independence.py`) impide que `tests/` o `tools/` vuelvan a importar
  `traianus`, `fastapi`, `numpy` o `helpers`.

### Fase 1 — generalización

Por contrato JSON al implementador, test-first.

* **Configuración del proyecto:** un fichero (propuesta: `actuarii.toml` o `.actuarii.json`, lo
  decide el contrato) con:
  * las rutas gobernadas;
  * los directorios donde el shim deja ejecutar Python;
  * la ruta del registro de contratos y la ventana del recibo (hoy 900 s).
  * Sin configuración, el kit gobierna lo mínimo y lo dice; no falla en silencio.
* **Hooks:** se llaman con `$CLAUDE_PROJECT_DIR` y no dependen del directorio actual. Hace falta un
  test que haga `cd` y compruebe que siguen funcionando.
* **Avance (2026-10-05):**
  * Paso 1 (`cc81355`): las órdenes de hook usan `$CLAUDE_PROJECT_DIR`; fuera `spectral-math-engine`.
  * Paso 2 (`4ec1912`, `151bacc`): `.actuarii.json` (JSON, no TOML: los hooks deben importar con un
    Python 3.9 de sistema) con `governed_paths` y `receipt_window_seconds`, leído por
    `tools/project_config.py`. Sin fichero se gobierna un mínimo incorporado (`.actuarii.json`,
    `AGENTS.md`, `CLAUDE.md`); con uno inválido se deniega todo dentro de la raíz. El propio fichero
    está siempre gobernado y cada denegación nombra su regla. Los 3 saltados de la fase 0 ya no
    existen: 1614 en verde, 0 saltados.
  * Paso 3 (`af75004`), con dos decisiones del autor: el kit gobierna también `tools/hooks/**` y
    `tools/bin/**`; el shim lee `python_script_dirs` pidiéndoselo a `tools/project_config.py` con el
    intérprete real aislado (`-I`), una sola fuente de verdad. El directorio del kit está siempre
    permitido (si no, los hooks saldrían 126 y la puerta se abriría); con la configuración inválida
    solo ese. Sin fichero, todo el repositorio (solo scripts commiteados). 1683 en verde.
  * Pendientes: ruta del registro de contratos y registro como ejemplo, con una sola copia de `path_matches` (paso 4); anuncio al abrir sesión de
    lo que se gobierna y de dónde sale (paso 5); textos, `AGENTS.md`, subagentes, skills y limpieza
    del perímetro de permisos (paso 6).
* **Mensajes y textos:** sin Traianus ni cláusulas suyas. Cada denegación dice qué regla del
  fichero de configuración la causa.
* **AGENTS.md:** una plantilla genérica de constitución, con las reglas que el kit hace cumplir y sus
  límites declarados. La de Traianus se queda en Traianus.
* **Subagentes:** el auditor ciego y los implementadores, como plantillas sin rutas de Traianus.
* **Se queda en Traianus (ya está fuera):** `audit_harness.py`, `traianus_invariant_verifier.py` y
  las skills `lab-analyst`, `spectral-mathematician` y `spec-first`.

### Fase 2 — empaquetado y prueba en limpio

* **Empaquetado:** `pyproject.toml` definitivo con Apache-2.0, `LICENSE` y `NOTICE`.
* **Instalación:** una orden instala el kit en un repositorio existente (copia los hooks, el
  `settings.json` y la configuración de ejemplo), sin pisar lo que ya hay.
* **Prueba:** sobre un repositorio vacío, de cero a una edición bloqueada y luego permitida en
  menos de 5 minutos, con cronómetro. Se repite en Linux (CI).
* **CI propio:** GitHub Actions con la suite completa.

### Fase 3 — lanzamiento

* **Búsqueda previa:** antes de escribir el README, buscar herramientas parecidas (colecciones de
  hooks para Claude Code, guardrails de agentes, gobierno con recibos). Decir en qué se parece y en
  qué no. Si ya existe algo igual, se replantea aquí, no después.
* **README en inglés:**
  * El problema.
  * Qué impide el kit y qué no: la lista de límites declarados es lo que lo hace creíble.
  * Instalación.
  * Un caso real: la línea base de Qwen3 o la puerta del motor sobre P1 en Traianus (2026-10-05),
    del protocolo congelado al resultado, con los commits.
* **Un texto técnico corto para HN y Reddit:** revisar antes las reglas de autopromoción de cada
  sitio. El inglés, pulido.

### Fase 4 — Traianus como memoria de agentes (solo si el kit da señal)

Ver la sección siguiente.

## Cómo entra Traianus

Entra de dos formas: como **caso de uso** (desde ya) y como **memoria** (más adelante).

### Como caso de uso

* La historia de los dos repositorios es la prueba: semanas de trabajo con agentes gobernados.
* Ejemplos completos del flujo con fechas y commits:
  * protocolo congelado;
  * contrato validado;
  * implementador test-first;
  * revisión ciega;
  * ejecución byte a byte;
  * lectura.
* Los ejemplos van en el README y en un documento de caso, en inglés.

### Como memoria de agentes

Los *actuarii* levantan las actas; Traianus es el archivo donde quedan.

* **El problema, visto en este proyecto:**
  * La memoria de un agente de código suele ser un fichero de notas que el propio agente escribe sin
    que nadie lo apruebe.
  * La de Traianus tiene unas 50 entradas, y algunas ya estaban obsoletas cuando se leyeron.
  * Nada impide que el agente recuerde algo falso o que lo reescriba en silencio.
* **El flujo:**
  * El agente propone un recuerdo: `POST /ingesta`, texto plano con `X-Idempotency-Key`. Entra en
    `pending_approval` o `incubating`.
  * Una persona lo aprueba: `POST /nodos/{id}/consolidar` con la clave ética en verdadero.
    Consolidado ⟺ (σ² ≥ θ_dyn) ∧ aprobación. La puerta no se toca y la clave ética pasa a ser un
    HITL real por recuerdo.
  * La historia es append-only: se sabe qué sabía el agente en cada momento.
  * RefApp-01 es el visor humano. Los ejes de color elegidos por el usuario (p. ej.
    Arquitectura-Azul) son una lente de observación, no estado: no cambian B_0 ni la época.
* **Frontera:**
  * Actuarii nunca importa Traianus (torch y unos 2 GB no caben en un kit de gobierno). Le habla por
    HTTP en `127.0.0.1`, como un cliente más, junto a RefApp-01.
  * Los conceptos de dominio (agente, recuerdo, decisión) viven en Actuarii, nunca en `traianus/`
    (AGENTS 3.2 de Traianus).
  * Va como un extra opcional o como un paquete aparte.
* **Lo que falta en el motor:**
  1. **Consulta sin escritura:** texto → vector y vecinas por ε, sin escribir nada. Es el endpoint de
     observación ya diseñado en `docs/roadmap/NEXT_RESEARCH.md` de Traianus. Hoy no existe: `/ingesta`
     escribe, y `/relations` solo lee lo ya guardado. Refutador: la base queda idéntica byte a byte
     (R2).
  2. **θ_dyn:** sobre Beezer, la puerta consolidó solo el 7,6 % (LEDGER 102–103 de Traianus). Si con
     recuerdos de agentes pasa lo mismo, quedaría en `incubating` casi todo lo que la persona aprueba.
     Hay que medirlo con la regla comprometida antes, sin ajustar la base ni el umbral mirando el
     resultado (limitación L4).
  3. **Issue #92 de Traianus:** normalización en float32 en `/consolidar` y `/ingesta`, y en float64 en
     `/ingesta/vector`.
* **Ordenar los recuerdos:** solo por cercanía (ε o vecinas más próximas). σ² no mide relevancia
  (lectura de LEDGER 103).
* **Una tensión de diseño que hay que resolver antes:**
  * La matriz zero-trust del propio kit pone en cuarentena las primitivas de red (`urllib`, `httpx`…)
    en los bloques de implementación que pasan por la puerta.
  * Un cliente HTTP a `127.0.0.1` las necesita.
  * Hará falta una excepción declarada (un módulo designado, solo loopback, con su test), no un
    rodeo.
* **Primer piloto posible:** las notas de memoria del propio proyecto como corpus, con la regla
  escrita antes.

## Decisiones pendientes (autor)

1. **Señal de éxito y fecha, escritas antes del lanzamiento.**
   * Propuesta: cuatro semanas desde la publicación.
   * Éxito si al menos 5 personas ajenas lo instalan o abren una issue, o si nace una conversación de
     trabajo.
   * Si no llega, se revisa con datos, sin reencuadrar.
2. **La búsqueda previa:** quién la hace y con qué herramienta (en Traianus WebFetch y WebSearch están
   denegados).
3. **Repositorio en GitHub:** privado hasta la fase 3 (propuesta) o público desde ya.
4. **Bitácora:** si Actuarii lleva su propio DEVLOG y LEDGER o los cambios se anotan en los de
   Traianus.

## Reglas de trabajo heredadas

Vienen de la memoria de la sesión de Traianus y una sesión nueva aquí no las ve:

* **Sin `cd` en Bash:** rompía todos los hooks con ruta relativa. Desde `b29c653` las órdenes usan
  `$CLAUDE_PROJECT_DIR`; la regla sigue hasta que una sesión abierta después de ese commit lo
  compruebe. Mientras, rutas absolutas y `git -C`.
* **Sin atribución a Claude** en commits ni PR: ni `Co-Authored-By` ni «Generated with Claude Code».
* **El chat principal no escribe código:**
  * El código y los tests van al implementador, con un contrato JSON validado en código.
  * El chat principal escribe contratos y revisa diffs.
* **Subagentes con `model: "sonnet"`**, salvo que el autor diga otro.
* **Comprometer antes del resultado:** cada versión que se va a ejecutar y su regla de comparación se
  commitean antes de que exista ningún resultado.
* **Antes de una suite completa:** comprobar el espacio en disco.
* **Python:** solo scripts commiteados, a través del shim; `pytest` por su propio punto de entrada,
  nunca `python3 -m`.
* **Las ideas que se salen del camino** se apuntan y esperan a que acabe el objetivo actual.

## Cómo empezar la sesión nueva

1. Abrir Claude Code con `/Users/test/Documents/Actuarii` como carpeta.
2. Primer mensaje: «Lee `docs/PLAN.md` y empieza por la fase 0.»
3. Aún no hay `CLAUDE.md`: crearlo es el primer paso de la fase 0. Hasta entonces, `AGENTS.md` y este
   plan no se cargan solos.
