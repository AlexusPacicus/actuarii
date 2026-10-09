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
  * Paso 4 (`8f49a81`): clave `contract_registry` (`null` o una ruta; aquí `null`), leída por el hook
    en cada llamada; el registro configurado está siempre gobernado. Una sola copia de
    `path_matches`, en `tools/project_config.py`. El registro de Traianus pasa intacto a
    `examples/traianus/contract_registry.json`. 1768 en verde.
  * Paso 5 (`453fd01`): hook `SessionStart` que anuncia qué se gobierna y de dónde sale.
  * Paso 6, con decisiones del autor (2026-10-06):
    * 6a (`1bce3ce`): la revisión ciega se configura con la clave `review`. La configuración completa
      de Traianus está en `examples/traianus/actuarii.json`.
    * 6b (`c199173`): fuera `check_doc_citations.py`; el contrato de delegación pierde `scope` y las
      gates de Traianus (una gate es un nombre libre validado); sin citas de cláusulas de `AGENTS`
      en `tools/` ni en `tests/`; permisos sin directorios inexistentes; OpenCode carga lo mismo que
      `CLAUDE.md`; `.gitignore` propio.
    * 6c (`8fc0a41`, `56edf05`, `e52d951`): `AGENTS.md` genérico (v2.0.0) con sus límites
      declarados; subagentes `implementer` y `blind-reviewer`; skills `blind-review` y `tdd-cycle`
      genéricas, idénticas en `.claude/` y `.opencode/` (con test). Lo de Traianus pasa a
      `examples/traianus/`.
  * **Fase 1 cerrada (2026-10-06, `28848f5`):** 1979 tests en verde. Fuera de `examples/`, `docs/` y
    los datos de los tests no queda ninguna mención a Traianus.
  * **Comprobaciones en una sesión nueva (2026-10-06):**
    * `cd` en Bash ya no rompe los hooks: con el directorio actual en `tools/hooks`, los hooks de
      Bash, Read y Edit se ejecutan y el de Edit deniega nombrando su regla. Regla heredada quitada;
    * el anuncio de gobierno llega al contexto al abrir la sesión: comprobado;
    * que los hooks funcionan aunque el shim no esté en su `PATH`: pendiente. No hay test con un
      `PATH` sin shim (`tests/security/test_hook_project_dir.py` hereda el del entorno).
  * Lección de los pasos 3, 4 y 6c: al cambiar un esquema o mover un documento, el contrato debe
    listar todos los tests que lo usan y no exigir una gate que solo puede pasar después de su
    propio commit.
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

### Fase 2b — auditoría adversarial (acordada 2026-10-06)

Va después del empaquetado, para que cubra el instalador (toca el `settings.json` de otro
repositorio), y antes del README, porque sus resultados son contenido del README. Si sale un fallo de
diseño, todavía hay margen.

* **Quién:** un subagente nuevo, sin el contexto de las sesiones que construyeron el kit. Recibe solo
  la lista de garantías y el código, con el encargo de saltárselas. Se presenta como prueba
  adversarial propia, no como auditoría independiente. La pieza fuerte sigue siendo
  auditar un repositorio ajeno; esta es la plantilla y la prueba de método.
* **Reglas, commiteadas antes de empezar:**
  1. **Alcance:** la lista de garantías que el kit dice cumplir. Lo que ya está en los límites
     declarados queda fuera: se sabe.
  2. **Cada intento es un caso reproducible:** qué intenta el agente, qué esperaba el kit y qué pasó.
     Los que rompen algo pasan a ser tests de regresión.
  3. **Clasificación de cada hallazgo:**
     * rompe una garantía declarada: se corrige antes del lanzamiento, con su test;
     * es un límite no declarado: se declara, y se corrige solo si es barato;
     * es una idea de mejora: va a la v0.2 (p. ej. el recibo atado al contenido o los recibos
       firmados de `docs/prior-art/PRIOR_ART.md`).
  4. **Tiempo cerrado:** dos días. Lo que no entre, no se hace.
  5. **Resultado:** un informe publicado en inglés con los casos. Alimenta la sección del README «qué
     intenta un agente y qué pasa».
* **Estado (2026-10-08):** la auditoría de la semana 1 ya cubrió el kit (A01–A18 en
  `docs/adversarial-audit/CASES.md`). Queda una 2b reducida, con sus pautas commiteadas antes, sobre
  lo que entró después.
* **Casos de partida de la 2b reducida:**
  * **El instalador:** escribe en el `settings.json`, el `.mcp.json`, el `.gitignore` y los hooks de git
    de otro repositorio.
  * **El navegador integrado (autor y Claude, 2026-10-08):** en la app de escritorio, el navegador es
    una vía a la web fuera del sandbox, de entrada y de salida: navegar a una URL ya es emitir datos,
    y no pasa por el proxy. `AGENTS.md` 7.1 deniega `WebFetch` y `WebSearch`, pero §9 no menciona el
    navegador. Ahí no decide ninguna regla: decide el modelo, con la aprobación de cada sitio por la
    persona, y el modelo elige la URL después de aprobado el dominio. Es un límite no declarado; se
    declara en §9 y se corrige solo si es barato.

### Fase 3 — lanzamiento

* **Búsqueda previa:** buscar herramientas parecidas (colecciones de hooks para Claude Code,
  guardrails de agentes, gobierno con recibos). Decir en qué se parece y en qué no. Se adelanta a la
  semana 1 (ver «Calendario»): si ya existe algo igual, hay que saberlo antes de empaquetar, no
  después.
* **README en inglés:**
  * El problema.
    * **Marco (autor, 2026-10-08; viene de Triarii, de una hackathon anterior):** un LLM comete la
      falacia de von Neumann a nivel semántico. Recibe instrucciones y datos por el mismo canal, el
      contexto, y no los distingue de forma fiable. La inyección de prompt no se evita: se le quita al
      LLM la autoridad. Las neuronas proponen y las reglas disponen; una regla determinista fuera del
      modelo decide, lo haya convencido lo que lo haya convencido.
    * Es el párrafo de entrada: explica por qué existe el kit sin presentarlo como «guardrails»,
      hueco saturado según `docs/prior-art/PRIOR_ART.md`.
    * De ahí sale la tabla de qué canal decide quién (sandbox, hook con recibo, regla de permisos o
      el propio modelo). Los canales donde decide el modelo son los límites declarados.
  * Qué impide el kit y qué no: la lista de límites declarados es lo que lo hace creíble.
  * Instalación.
  * Un caso real: la línea base de Qwen3 o la puerta del motor sobre P1 en Traianus (2026-10-05),
    del protocolo congelado al resultado, con los commits.
* **Un texto técnico corto para HN y Reddit:** revisar antes las reglas de autopromoción de cada
  sitio. El inglés, pulido.

### Fase 4 — Traianus como memoria de agentes (solo si el kit da señal)

* **Cuándo:** después de las fases 0–3 y con el perfil de freelance en marcha. No retrasa los ingresos.
* **Regla del autor (2026-10-06):** la investigación de Traianus (WP1, la puerta, la línea física de
  la viscosidad) solo se retoma con una aplicación que demuestre utilidad. Esta es esa aplicación.
* **Detalle:** en «Como memoria de agentes», más abajo.

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
  * La puerta del kit deniega que un cambio introduzca primitivas de red (`urllib`, `http`…) en un
    `.py` gobernado, y el sandbox no deja a `Bash` conectarse a `127.0.0.1` sin permitirlo en
    `allowedDomains`.
  * Un cliente HTTP a `127.0.0.1` necesita las dos cosas.
  * Hará falta una excepción declarada (un módulo designado, solo loopback, con su test), no un
    rodeo.
* **Primer piloto posible:** las notas de memoria del propio proyecto como corpus, con la regla
  escrita antes.

#### Criterio de utilidad (autor y Claude, 2026-10-06)

Lección del producto de matemáticas: allí lo que importaba era la calidad del ranking, que da
cualquier embedding, y el motor no intervino. La aplicación que justifique retomar Traianus tiene que
cumplir las cuatro condiciones:

1. **Su utilidad viene de las propiedades del motor** (append-only, aprobación humana,
   determinismo), no de buscar bien.
2. **Tiene un usuario real desde el primer día:** el autor, con sus propios agentes.
3. **Su utilidad se mide**, con la regla comprometida antes de cualquier dato.
4. **No retrasa los ingresos.**

La memoria de los agentes del autor cumple las cuatro.

**Datos que genera para la investigación:**
* Cada aprobación, corrección o rechazo del autor es una **etiqueta**.
* Así la puerta tiene por fin un trabajo contra el que medirse: ¿σ² ≥ θ_dyn, o una base derivada del
  corpus (WP1), predice lo que el autor rechaza?
* Es la pregunta de WP1, con datos reales que se acumulan con el uso, y no con 18 ítems escritos a
  mano.

**Condiciones de método:**
* Mientras aprueba, el autor no ve σ² ni el estado de la puerta. Si los viera, sus etiquetas dejarían
  de ser independientes de lo que se mide.
* Hipótesis, regla de decisión y tamaño mínimo de muestra, comprometidos antes de empezar a etiquetar.
* La viscosidad como umbral (línea aparcada en `docs/roadmap/NEXT_RESEARCH.md` de Traianus) entra
  solo después de WP1, porque depende de la base.

**Valor comercial:** «memoria auditable para los agentes de tu equipo» encaja con la oferta de
freelance de configurar agentes de forma segura.

## Calendario (acordado 2026-10-06)

Tres semanas hasta el lanzamiento y cuatro de ventana para la señal. Se fija a partir del ritmo de la
fase 1 (cuatro pasos en un día) y de los créditos semanales. Si hay menos horas, se recorta alcance,
no se mueve la fecha de lanzamiento.

| Semana | Fechas | Qué |
|---|---|---|
| 1 | 6–11 oct | Búsqueda previa, lo primero (un día como mucho). Cerrar la fase 1 (paso 5 hecho en `453fd01`; queda el paso 6). Cerrar las decisiones pendientes. |
| 2 | 12–18 oct | Fase 2: `pyproject.toml`, `LICENSE`, `NOTICE`, orden de instalación, prueba en un repo vacío con cronómetro (< 5 min), CI. |
| 3 | 19–25 oct | Fase 3: README en inglés, documento del caso Traianus, texto corto para HN y Reddit. **Se publica el 25 de octubre, esté como esté**; lo que no esté listo pasa a la v0.2. |
| 4–7 | 26 oct – 22 nov | Ventana de señal. Auditoría de ejemplo publicada (con el propio kit, sobre un repositorio ajeno; fallos de seguridad, primero en privado a sus mantenedores). Solo se arregla lo que pidan usuarios reales. |
| — | 22 nov | Revisión con datos frente a la señal comprometida. |

**Antes del lanzamiento no se hace:**
* Nada de Traianus: ni la fase 4, ni el endpoint de consulta, ni WP1.
* Ninguna mejora de gobernanza que no responda a un fallo real.
* Ninguna función nueva fuera de este plan.

## Decisiones de la semana 1 (autor, 2026-10-07)

Las cuatro están cerradas. Las tres primeras son las propuestas de Claude del 2026-10-06, aceptadas tal
cual.

1. **Señal de éxito, escrita antes del lanzamiento:** cuatro semanas desde la publicación. Éxito si al
   menos 5 personas ajenas lo instalan o abren una issue, o si nace una conversación de trabajo. Si no
   llega, se revisa con datos, sin reencuadrar.
2. **Repositorio en GitHub:** privado hasta el 25 de octubre; público al publicar.
3. **Bitácora:** un solo DEVLOG en Actuarii, sin LEDGER, y nada en los de Traianus.
4. **La búsqueda previa (2026-10-06):** la hizo Claude con el navegador integrado. Resultado en
   `docs/prior-art/PRIOR_ART.md`: no hay nada igual; se ajusta la presentación, no el kit. Deja abierta
   una decisión para la fase 2: distribuir como plugin, como `install.sh` o de las dos formas.

## Decisiones de la fase 2 (autor, 2026-10-08)

1. **Alcance:** la fase 2 es lo que dice su sección y lo que añade el traspaso del 2026-10-07, nada más.
   Lo que la revisión del código sugirió fuera de eso va a «Ideas para la v0.2».
2. **Distribución en la v0.1:** un instalador que copia el kit dentro del repositorio de destino; el
   plugin, en la v0.2. Motivo: el shim solo deja ejecutar scripts commiteados en `HEAD` del propio
   repositorio, el kit se gobierna a sí mismo porque está en `governed_paths`, y la clave `sandbox` y
   el `pre-commit` se escriben en el proyecto de todos modos. Un plugin vive fuera del repositorio.
3. **Forma del instalador:** un script de Python de la biblioteca estándar, que importa con un Python
   3.9 de sistema como los hooks, y no un `install.sh`: tiene que fusionar `settings.json` y
   `.mcp.json` sin pisar nada, y eso en `sh` no se hace bien.
4. **Dónde copia el kit:** en `tools/`, como en este repositorio. Si el destino ya tiene `tools/`, o
   cualquier otra cosa que el instalador escribiría, se para, dice qué choca y no escribe nada.
5. **Dependencia:** el validador y el contrato de delegación siguen necesitando `pydantic`; el
   instalador y la guía piden un entorno que lo tenga, y la prueba cronometrada incluye prepararlo.
6. **La prueba en limpio** sigue el protocolo de `docs/design/PRUEBA_EN_LIMPIO.md`, commiteado antes
   de la primera medida.

## Traspaso (2026-10-07, cierre de la semana 1 de trabajo)

* **Estado:** `main` limpio, suite en 2976 verdes. Todas las correcciones de la auditoría están
  cerradas; la tabla con sus commits está en `docs/process/PROCESO.md` §9. El kit tal como es lo
  describe `AGENTS.md` v2.1.0.
* **Hecho desde el traspaso anterior (2026-10-06):**
  * F4b, primitivas por `ast` decididas en la puerta (`74177b4`); la lista queda cerrada.
  * Sandbox de Claude Code como frontera de `Bash`: red, escrituras, movimientos y borrados en las
    rutas gobernadas (`750ac0c`; prueba S1–S9 en `docs/design/SANDBOX.md`).
  * Integridad del commit con el hook `pre-commit` (`15c8ad0`), instalado en este repositorio.
  * `AGENTS.md` v2.1.0, la skill `boundary-validator` y la plantilla `implementer` al día (`f4189ea`,
    `429d5ff`).
  * F6, los hooks con y sin el shim y con el Python 3.9.6 del sistema (`a21fbfc`).
  * A15, la fase roja y la verde comprobadas en código con `tools/audit/verify_red_green.py` y el
    informe `delegation-report/2` (`17a05e1`).
  * Coste de una escritura gobernada medido (`docs/design/COSTE.md`): 1875 ms de mediana, por encima
    del umbral de 1 s; según la regla, no se optimiza antes del lanzamiento, el README declara las
    cifras y el diseño para la v0.2 está en su §5.
* **Cómo se trabaja ahora** (una sesión nueva tiene que saberlo):
  * **El sandbox está activo.** `Bash` no escribe las rutas gobernadas ni sale a la red. Las órdenes de
    git que reescriben rutas gobernadas (`switch`, `merge`, `restore`, `checkout` de una ruta) las
    ejecuta el autor con `!`; el chat le pasa las órdenes, una por bloque.
  * **El hook de integridad está instalado** en `.git/hooks/pre-commit`; el anuncio de la sesión dice
    si lo está y si el sandbox está activo.
  * **Cada informe de delegación** es `delegation-report/2` y se verifica con `verify_red_green.py`
    (en segundo plano mientras se revisa el diff) antes de fusionar. El contrato que se pasa al
    verificador tiene que decir `report_schema: delegation-report/2`.
  * **Se commitea solo si `pytest` sale con 0**, comprobando su código de salida, no el de la orden
    que le sigue (lección del commit rehecho `429d5ff`).
  * **El servidor MCP ejecuta el código con el que arrancó:** un cambio en el validador necesita que
    el autor lo reconecte. Los hooks, en cambio, se releen en cada llamada (AGENTS 6.5).
  * `.opencode/` no está gobernado, por decisión del autor (AGENTS §9).
* **Decisiones del autor del 2026-10-07:** la lista de primitivas cerrada; el sandbox como frontera de
  lo que se ejecuta; las órdenes de git que escriben rutas gobernadas, a mano; la integridad del commit
  en la v0.1 y el formato del mensaje en la v0.2; A15 verificado en el flujo de delegación; el coste
  según la regla de `COSTE.md` §3.
* **Siguiente: fase 2 (semana 2, 12–18 de octubre).** Además de lo que dice la fase:
  * decidir la distribución: plugin, `install.sh` o las dos (`docs/prior-art/PRIOR_ART.md`);
  * el instalador escribe la clave `sandbox` con un `denyWrite` sacado de `governed_paths`, copia el
    hook `pre-commit` (corre fuera de la sesión, lo lanza la persona) y avisa si falta
    `allowUnsandboxedCommands: false` en los ajustes del usuario;
  * la CI en Linux necesita `bubblewrap` y `socat` para el sandbox; los tests que piden un sistema de
    ficheros que no distingue mayúsculas se saltan allí, con su motivo.
* Las decisiones de la semana 1 están
  cerradas (sección anterior).

## Ideas para la v0.2

* **Núcleo independiente del proveedor (autor, 2026-10-07):** que cualquier entorno de agentes se
  enganche y las reglas se ejecuten en un paquete. Tres piezas:
  * **Adaptadores:** la decisión «¿se permite esta escritura?» queda en una función central y cada
    entorno (Claude Code, un plugin de OpenCode…) tiene un adaptador fino que traduce su evento. Un
    entorno sin hooks previos a cada herramienta no se puede vigilar así.
  * **El sandbox por fuera:** el kit lanza el agente entero dentro de `@anthropic-ai/sandbox-runtime`
    (sobre el que está construido el de Claude Code) o de un contenedor con las rutas gobernadas en solo
    lectura, con la configuración sacada de `.actuarii.json`. Dependencia nueva de npm: necesita la
    aprobación del autor y comprobar si es estable.
  * **Intermediario de escritura por MCP:** con el proceso entero dentro, tampoco las herramientas de
    ficheros del agente escriben las rutas gobernadas; el agente propone por MCP y un proceso fuera
    del sandbox comprueba recibo, cita y primitivas y escribe él. La frontera deja de depender de los
    hooks de cada entorno. Encaja con el proceso residente de `docs/design/COSTE.md` §5.

  Tamaño de v0.2 o v1. El README de la v0.1 dice la dirección en una frase: hoy funciona con Claude
  Code, y las reglas ya están separadas del entorno.
* **Plantilla de script para los tests (autor, 2026-10-07):** llevar la verificación de A15 (la fase
  roja en el commit base y la verde en el final, ejecutadas por código y no declaradas) a una
  plantilla de script reutilizable que compruebe de forma determinista la reproducibilidad (la misma
  suite da el mismo resultado en un árbol limpio) y la cobertura (qué código cubren los tests que el
  contrato nombra), para cualquier proyecto que adopte el kit.
* **Verificación de A15 más barata y más estricta (autor, 2026-10-07):** empezar la parte del commit
  base en cuanto termina la fase roja, a la par del implementador, con los ficheros de test atados
  por su hash y la exigencia de que los commiteados sean los mismos; un modo que verifique solo los
  tests del contrato y deje la suite entera a la CI, para proyectos con suites largas; exigir que
  falle cada identificador de un test rojo, no solo el conjunto; y que `run_process.py` ofrezca su
  error de tiempo agotado, para que el verificador no lo tome de `run_process.subprocess`.
* **Operaciones sin canal gobernado (autor, 2026-10-09):** el único canal gobernado es escribir contenido
  (`Edit` y `Write` con recibo). Todo lo demás sobre una ruta gobernada cae en la persona: el sandbox lo
  bloquea y no hay recibo que lo autorice. Eso incluye:
  * borrar, renombrar o cambiar el modo o el tipo de un fichero;
  * las órdenes de git que reescriben el árbol (`merge`, `switch`, `restore`).

  Es fricción para cualquier usuario del kit, no solo aquí. Encaja en el intermediario de escritura por
  MCP: recibos también para esas operaciones. El README de la v0.1 lo declara como fricción conocida. Ya
  se evita una parte: si `main` no se ha movido desde la rama, el chat la avanza por fast-forward
  (`git branch -f main <rama>` y `git switch main`), sin reescribir el árbol y dentro del sandbox.
* **Formato del mensaje del commit** (prefijo de una lista cerrada, tipo frente a rutas, plantilla,
  sin atribución), en el `pre-commit` (`docs/design/SANDBOX.md` §9).
* **Coste por escritura gobernada:** el diseño de `docs/design/COSTE.md` §5 (validador en
  `permissions.allow`, un solo proceso para los hooks de escritura, arranque de Python más ligero).
* **Revisor ciego con `Bash`**, como otro proceso con `denyRead` fuera del paquete
  (`docs/design/SANDBOX.md` §4).
* **Distribución como plugin** (decisión 2 de la fase 2), junto con el núcleo independiente del
  proveedor.
* **Kit en cualquier directorio (revisión de la fase 2, 2026-10-08):** `project_config.KIT_DIR` ya
  sale de la ubicación del módulo, pero `tools/` sigue escrito tal cual en `.claude/settings.json`,
  `.mcp.json`, `tools/git/pre-commit`, `HOOK_SOURCE` de `announce_governance.py` y
  `deny_python_escapes.py`. Con eso resuelto, el instalador podría copiar el kit en `.actuarii/` y no
  chocar con un `tools/` ajeno. Necesita un test que instale con otro nombre y ejecute los hooks.
* **Kit solo con la biblioteca estándar (revisión de la fase 2, 2026-10-08):** quitar `pydantic` de
  `tools/boundary_validator/` y de `tools/audit/delegation_contract.py`. Instalar sería copiar, y
  `requires-python` podría bajar a 3.9. Se decide con la cifra de la prueba en limpio: si preparar el
  entorno pesa en los 5 minutos, hay motivo.

## Reglas de trabajo heredadas

Vienen de la memoria de la sesión de Traianus y una sesión nueva aquí no las ve:

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
* **DEVLOG:** al cerrar cada sesión, una entrada del día en `docs/DEVLOG.md` (qué se hizo con sus commits, qué
  se decidió, qué salió mal y qué se aprendió).
* **Commitear solo con la suite en verde,** comprobando el código de salida de `pytest`, no el de la
  orden que le sigue.

## Cómo empezar la sesión nueva

1. Abrir Claude Code con `/Users/test/Documents/Actuarii` como carpeta. `CLAUDE.md` carga
   `AGENTS.md` y este plan.
2. Leer el anuncio de la sesión: el sandbox tiene que estar activo y el hook de integridad instalado.
3. Primer mensaje: «Lee el traspaso de `docs/PLAN.md` y empieza la fase 2.»
