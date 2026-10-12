# DEVLOG de Actuarii

Una entrada por día, la más reciente arriba: qué se hizo (con sus commits), qué se decidió y por qué, qué
salió mal y qué se aprendió. Lo que ya cuentan los documentos de diseño se enlaza, no se repite. Se
escribe al cerrar cada sesión (decisión del autor, 2026-10-07). Las entradas del 5 y el 6 de octubre se
reconstruyeron el 7 a partir de `git log` y de `docs/PLAN.md`.

## 2026-10-10

Una sesión, sin cambios en el repositorio. Entrada reconstruida el 12 a partir de la transcripción y del
resumen que dejó la sesión fuera del repositorio
(`~/.claude/plans/haz-una-auditor-a-del-serialized-stream.md`).

**Hecho**
* Auditoría informal de solo lectura sobre `main` en `e0291db`, pedida por el autor para gastar los
  créditos de la semana. No es la 2b reducida, que necesita sus pautas commiteadas antes de empezar, y
  ningún punto tiene todavía un caso reproducible. Se interrumpió al ir a comprobar si hay un `.venv`
  dentro del repositorio.
* Comprobado leyendo el código:
  1. Con un `core.hooksPath` global absoluto, el instalador escribe el `pre-commit` en esa carpeta
     compartida, fuera del destino (`tools/install.py:330-336`). En cualquier otro repositorio del
     usuario, el hook no encuentra `tools/git/commit_integrity.py` y rechaza todos los commits. El test
     solo cubre una ruta relativa.
  2. El anuncio de la sesión puede mentir (G13): afirma que `Bash` no escribe las rutas gobernadas
     mirando solo `sandbox.enabled`, sin comprobar que `denyWrite` cubra cada ruta de `governed_paths`,
     ni `.claude/settings.local.json`, ni `excludedCommands`.
  3. Un repositorio instalado queda más débil que este: sin `"disableAllHooks": false` (una de las
     medidas de A09), y se acepta un `sandbox` previo con `excludedCommands`, `allowWrite` o `network`,
     que `tests/security/test_sandbox_settings.py` prohíbe aquí.
  4. `.data/` no está gobernado: un `Write` vacía la base de auditoría sin recibo. `denyWrite` no cubre
     sus ficheros `-wal` ni `-shm`.
  5. A18 sigue abierto: unos `params` o `arguments` que no son un objeto tiran el servidor MCP
     (`validator.py:340-345`), y no hay test.
  6. AGENTS 6.2 está marcado **[enforced]**, pero nada obliga a ejecutar `delegation_contract.py` ni
     `verify_red_green.py`, y el verificador no compara el diff con los ficheros que el contrato permite
     tocar.
  7. Una ruta gobernada que es un enlace simbólico no gobierna nada: la puerta, el sandbox y el
     `pre-commit` deciden por el destino del enlace.
  8. Menores: identificadores de Traianus en los tests; `check_impact.py` sin uso; `subprocess`
     importado fuera de `run_process.py`; `except sqlite3.Error: pass` en el validador; patrones del
     registro de contratos sin validar; dos falsos positivos del hook de `Bash` reproducidos (A06 y
     `ls .venv/bin/python3`); y la redacción de §9 sobre la lista de primitivas, que sugiere que solo
     pasan rodeos indirectos.
* Hipótesis sin probar:
  * **H1, la más grave:** con el intérprete en un `.venv` dentro del repositorio, un `.pth` o un
    `sitecustomize.py` escrito en su `site-packages` se ejecuta en cada hook y en el servidor MCP, que
    corren fuera del sandbox, y anula todas las puertas. `-I` no lo impide y `-S` sí.
  * H2: renombrar desde `Bash` el directorio que contiene una ruta en `denyWrite`.
  * H3: un enlace duro desde una ruta no gobernada a un fichero gobernado.
  * H4: un `Glob` con llaves que sale del paquete de la revisión ciega.
  * H5: más canales fuera del sandbox además del navegador (conectores, Chrome, artifacts y las
    herramientas del escritorio que hacen `merge` en el host).

**Salió mal y se aprendió**
* Lo encontrado quedó solo en la conversación y en un fichero fuera del repositorio. Esta entrada lo
  trae al repositorio hasta que pase a casos de `docs/adversarial-audit/CASES.md`.

**Siguiente**
* Commitear las pautas de la 2b reducida con estos puntos y los del PLAN como casos de partida; después,
  cada uno como caso reproducible en un clon desechable, clasificado y, si rompe una garantía, corregido
  por contrato. H1 va primero.

## 2026-10-09

Una sesión, de tarde. Se corrigió lo que dejó el ensayo del 8 y se preparó la medida en macOS. Suite: de
3069 a 3080 en verde en macOS. Entrada reconstruida el 12 a partir de `git log` y de la transcripción
de la sesión.

**Hecho**
* Fallo del kit y roce 4 del ensayo, por contrato al implementador (`sonnet`) en la rama
  `fase2/shim-ficheros` (`d2912f4`):
  * Los enlaces del shim se quedan como enlaces en Actuarii, ya commiteados. El instalador escribe en
    el destino un fichero normal con los bytes y el bit de ejecución de aquello a lo que apunta el
    enlace. Rechaza con código 2, sin escribir nada, un enlace que no resuelve a un fichero normal de
    los árboles del kit.
  * Un test instala el kit y lo commitea con su propio `pre-commit`; entra también en la secuencia de
    la CI.
  * `--dry-run` acaba en «dry run: nothing was written», sin pasos siguientes.
  * `verify_red_green.py` repetido por el chat principal salió 0: los seis grupos de tests fallan en la
    base y pasan en el commit final.
* `main` avanzó por fast-forward dentro del sandbox (`git branch -f main <rama>` y `git switch main`),
  sin ninguna orden del autor, porque `main` no se había movido desde la rama. Ramas `fase2/*`
  borradas.
* `INSTALL.md` (`6908014`): dónde clonar, rutas explícitas, el primer commit del kit instalado en la
  terminal antes de abrir Claude Code (dentro de la sesión, el shim rechaza `commit_integrity.py`
  hasta que está en `HEAD`), un entorno sin `.venv` y cómo leer `pip check`.
* Hito 1 de la prueba en limpio reformulado antes de medir (`e0291db`; `PRUEBA_EN_LIMPIO.md` §4c):
  se comprueba por el registro del kit (la transcripción, la tabla `receipts` por hash y el
  `git diff` del destino), no por la conducta del agente. En §5, qué roces del ensayo quedan corregidos
  y dónde.
* Idea para la v0.2 en `docs/PLAN.md` (`e0291db`): las operaciones sobre rutas gobernadas sin canal
  gobernado.
* Medida en macOS preparada: copia del ensayo borrada, clon de Actuarii en `~/Documents/actuarii-medida`
  (`e0291db`) y clon de `noticias` en `~/Documents/noticias-medida` (`v3-exp`, `1676538`). El clon de
  `noticias` es el paso 1 de la secuencia cronometrada. La medida no siguió: en el destino no hay nada
  instalado ni ninguna sesión de Claude Code. Sin cifra.

**Decidido (autor)**
* Las operaciones sobre una ruta gobernada que no son escribir contenido (borrar, renombrar o cambiar
  el modo o el tipo de un fichero, y los `merge`, `switch` y `restore` que reescriben el árbol) no
  tienen canal gobernado y caen siempre en la persona. Es fricción para cualquier usuario del kit: va a
  la v0.2, dentro del intermediario de escritura por MCP, y el README de la v0.1 la declara.
* El hito 1, tal como quedó en §4c.

**Salió mal y se aprendió**
* El primer contrato convertía los enlaces del shim en ficheros dentro de Actuarii. Eso obligaba a
  borrar en `tools/**`, que desde el sandbox solo puede hacer el autor, con una pausa del implementador
  a mitad de camino. El autor señaló que había demasiadas peticiones para él. Se enmendó el contrato:
  convierte el instalador, que ya ejecuta la persona fuera de la sesión. El implementador ya había
  empezado a tocar `test_python_gate.py` y la enmienda le pidió dejarlo como en la base. Lección: al
  diseñar un contrato, contar qué pasos caen en la persona y buscar el diseño que no los necesite.
* De ahí salió la fricción general del kit (decisión de arriba), y también la vía que la evita en parte:
  avanzar `main` por fast-forward dentro del sandbox cuando no se ha movido.
* La formulación del hito 1 propuesta el 8 («ninguna escritura gobernada sin recibo») no se podía
  comprobar con el rastro: el hook no registra sus decisiones, solo quedan los recibos. Se fijó el
  método concreto antes de medir.
* El commit `e0291db`, que solo toca documentos, se hizo con `test_ci_workflow.py` en verde (el único
  test que los lee) y no con la suite entera. La suite había pasado en `6908014`.
* Los tres commits del día no se subieron: `main` quedó 3 por delante de `origin`, y la CI no ha
  ejecutado todavía el test del commit con el hook.

**Siguiente**
* `git push`, para que la CI compruebe `d2912f4`.
* La medida cronometrada en macOS desde un clon nuevo de `noticias`, siguiendo solo `INSTALL.md`; después,
  la comprobación del hito 1 según §4c.
* El caso real sin cronómetro (§4b) y la 2b reducida, con sus pautas commiteadas antes.
* Liberar disco: quedaban unos 6 GiB libres (97 %), y `verify_red_green.py` crea worktrees temporales.
* Decidir si las ramas heredadas de Traianus siguen en el repositorio antes de hacerlo público.

## 2026-10-08

Dos sesiones. La primera siguió a la del 7, sin cambios de código; la segunda adelantó la fase 2.
Suite: de 2976 a 3063 en verde.

**Hecho**
* DEVLOG creado, con las entradas del 5 al 7 y la regla de escribirlo al cerrar cada sesión
  (`d1d67c4`, del 7).
* Idea para la v0.2 apuntada en `docs/PLAN.md` (`c74dc54`): un núcleo independiente del proveedor,
  para que cualquier entorno de agentes se enganche y las reglas se ejecuten en un paquete. Tres
  piezas: adaptadores finos por entorno sobre una decisión central; el sandbox del sistema por fuera
  del agente entero (`@anthropic-ai/sandbox-runtime` o un contenedor), con la configuración sacada de
  `.actuarii.json`; y un intermediario de escritura por MCP, que escribe las rutas gobernadas tras
  comprobar la propuesta, de modo que la frontera no dependa de los hooks de cada entorno.
* Fase 2, adelantada desde el 12 de octubre:
  * Decisiones de la fase y protocolo de la prueba en limpio, commiteados antes de medir (`f65f53a`;
    `docs/design/PRUEBA_EN_LIMPIO.md`).
  * Instalador, `tools/install.py` (`4d615e2`): copia el kit, fusiona `settings.json` con su
    `sandbox` y `.mcp.json`, instala el `pre-commit` y añade `.data/` al `.gitignore`. Comprueba
    todo antes de escribir; con un choque no escribe nada; una segunda ejecución no cambia nada.
    Biblioteca estándar, Python 3.9. 57 tests, uno de punta a punta: en un repositorio recién
    instalado, el hook copiado deniega sin recibo y permite con el recibo del validador copiado.
  * Corrección del hito 1 (`70304b3`): sin base de auditoría, el hook de escritura deniega con su
    regla y la llamada a `validate_proposal`, en vez de «unable to open database file». Las
    consultas de `hook_gate` siguen fallando sin base, como fijaban sus tests.
  * `LICENSE` (texto oficial de Apache-2.0, de dos copias locales independientes e idénticas,
    SHA-256 `cfc7749b…3d30`) y `NOTICE` (`b38dcbd`); `pyproject.toml` de la v0.1.0 (`7e99ee7`).
  * Cada cambio de código, por contrato validado al implementador (`sonnet`), con
    `verify_red_green.py` repetido por el chat principal antes de fusionar: salió 0 las tres veces.
* Marco del README en `docs/PLAN.md` (`6b6e275`) y casos de partida de la 2b reducida, el instalador
  y el navegador integrado (`b936cb6`).
* Repositorio privado en GitHub, `AlexusPacicus/actuarii`, creado por el autor con `gh`.
* CI en Linux (`e8f0d5d`): acciones fijadas por SHA, Python 3.11, la secuencia de la prueba en limpio
  como paso propio y la suite. Primera ejecución en verde: 3 tests de la secuencia en 2 s y la suite
  en 50 s, 3055 pasan y 14 se saltan (los casos que piden un sistema de ficheros que no distinga
  mayúsculas, por la cuenta de sus condiciones). Resultados en `docs/design/PRUEBA_EN_LIMPIO.md` §5.
* Enmienda de la prueba en limpio antes de medir (`27b0ef5`): destino un clon de `noticias` en
  `v3-exp`, y el agente recibe solo la tarea. Comparación de configuraciones (sin gobierno, gobierno
  por instrucción, Actuarii) apuntada en `docs/design/COSTE.md` §6, sin medir.
* Guía de instalación, `INSTALL.md` (`f79ac08`).
* Ensayo de la prueba en limpio en macOS sobre `noticias`, sin cifra: el agente pidió el recibo por
  su cuenta y escribió; salieron siete roces de la guía y del instalador y un fallo del kit (§5).

**Decidido (autor)**
* El núcleo independiente del proveedor va a la v0.2 o a la v1; antes del lanzamiento no se hace. El
  README de la v0.1 dice la dirección en una frase.
* La fase 2 es solo lo que dice el plan. El kit en cualquier directorio, quitar `pydantic` y el plugin
  van a «Ideas para la v0.2»; lo de `pydantic`, con la cifra de la prueba cronometrada.
* Distribución de la v0.1: un instalador en Python que copia el kit en `tools/` y se para si algo
  choca. Autoría solo con el nombre, sin correo.
* Marco del README, que viene de Triarii: un LLM comete la falacia de von Neumann a nivel semántico;
  no se evita la inyección, se le quita al LLM la autoridad. Las neuronas proponen y las reglas
  disponen.
* En las pruebas, el agente recibe solo la tarea: ni procedimiento ni autoridad ni gobernanza en el
  texto. Si no, no se distingue la regla de la obediencia.
* El hito 1 del ensayo (ninguna denegación) es un error de formulación del protocolo: el agente no
  gobierna, así que lo que se observa es el registro del kit, no la conducta del agente.

**Salió mal y se aprendió**
* El instalador sacó un fallo real: en un repositorio recién instalado, la primera denegación no decía
  qué hacer. Se corrigió antes de medir, como manda el protocolo.
* El primer arreglo propuesto cambiaba `hook_gate`, contra una decisión fijada en tres tests (un
  rastro que falta no se puede verificar). Leer antes los tests movió el arreglo al hook.
* El primer plan de la fase mezclaba cosas fuera del plan; el autor lo vio y se recortó.
* Errores del chat principal: dijo «no tengo red» cuando solo `Bash` no la tiene (el navegador
  integrado sí sale; con él se podía comprobar `LICENSE` contra apache.org); y un
  `ls .venv/bin/python3` que el hook denegó con razón, por nombrar un intérprete por su ruta.
* El navegador integrado es una vía a la web fuera del sandbox donde decide el modelo, no una regla, y
  `AGENTS.md` §9 no lo declara: caso para la 2b.
* El ensayo encontró lo que los tests no veían: el `pre-commit` del kit rechaza sus propios enlaces
  del shim, así que un kit instalado no se podía commitear. Los tests del instalador no commitean en
  el destino; la secuencia de la CI tampoco.
* Los primeros textos del protocolo daban al agente instrucciones de procedimiento («sigue el
  procedimiento que te indica la denegación»); lo vio el autor y se enmendaron antes de medir.
* Errores del chat principal en el cierre: afirmó que los 14 saltados de Linux eran todos por
  mayúsculas antes de comprobarlo (se corrigió contando las condiciones antes de subirlo); la guía
  salió con tres huecos que el ensayo encontró en minutos; y anotó como decisión del autor una
  clasificación del hito 1 que el autor no había tomado («ajeno a ello» se refería a la nota oculta
  de Claude Code). Se corrigió antes de subirlo: ante una respuesta ambigua, se pregunta.

**Siguiente**
* Corregir antes de repetir la medida, por contrato: los nombres `python` y `python3.11` del shim como
  ficheros normales y no enlaces, con un test de que son idénticos; un commit en el destino con el
  hook instalado en los tests del instalador y en la secuencia de la CI; la salida de `--dry-run`
  sin pasos siguientes.
* Corregir `INSTALL.md`: dónde clonar, rutas explícitas, entorno en un clon sin `.venv` y cómo leer
  `pip check`.
* Commitear la nueva formulación del hito 1 (propuesta en §5: un `EXECUTE_SAFE` en el rastro antes de
  cada escritura gobernada) antes de repetir la medida.
* Repetir la medida en macOS desde un clon nuevo de `noticias`, cronometrada y sin ayuda del chat.
* El caso real sin cronómetro (§4b) y la comparación de configuraciones (`COSTE.md` §6).
* La 2b reducida, con sus pautas commiteadas antes.
* Opcional: comprobar `LICENSE` contra apache.org con el navegador.
* Borrar las ramas fusionadas `fase2/*` y la copia de ensayo `/Users/test/Documents/noticias-prueba`.

## 2026-10-07

Escrita al cerrar la sesión. Suite: de 2350 a 2976 en verde.

**Hecho**
* F3 comprobada en la llamada real: Claude Code convierte el texto JSON en objeto, y el rechazo de un
  texto que no es JSON sí se aplica (`2268ef5`).
* F4b, primitivas por `ast` sobre el fichero resultante, decididas en la puerta (`74177b4`), en dos
  pasos porque el servidor MCP en marcha conservaba la matriz léxica hasta reconectarlo (`28f2c80`,
  `b6888ca`). Diseño en `docs/design/RECIBO_CONTENIDO.md` §4.1.
* Sandbox de Claude Code investigado, probado (casos S1–S9) y adoptado como frontera de `Bash`
  (`750ac0c`). Detalle en `docs/design/SANDBOX.md`.
* Integridad del commit con un hook `pre-commit` (`15c8ad0`), instalado y probado en este repositorio.
* `AGENTS.md` v2.1.0, la skill `boundary-validator` y la plantilla `implementer` al día (`f4189ea`,
  `429d5ff`, `1bdcd90`); `PROCESO.md` con el estado de las correcciones (`6c5ee4b`).
* F6, los hooks deciden igual con y sin el shim y con el Python 3.9.6 del sistema (`a21fbfc`).
* A15, la fase roja y la verde de los tests se comprueban en código (`17a05e1`).
* Coste de una escritura gobernada medido con la regla commiteada antes (`86a4550`, `6c2aa74`) y
  diseño de optimización para la v0.2 (`bc89176`, `fee798c`). Detalle en `docs/design/COSTE.md`.
* Traspaso y decisiones de la semana 1 en `docs/PLAN.md` (`7a7e362`, `fee798c`).

**Decidido (autor)**
* La lista de primitivas queda cerrada: cada forma nueva sería otro parche. La frontera de lo que se
  ejecuta es el sandbox, no la lista.
* Las órdenes de git que reescriben rutas gobernadas las ejecuta la persona con `!`.
* La integridad del commit entra en la v0.1; el formato del mensaje, en la v0.2.
* `.opencode/` no se gobierna: OpenCode se usa aquí solo para opinar, y se declara.
* El coste por escritura (1875 ms de mediana, umbral de 1 s) no se optimiza antes del lanzamiento.
* Decisiones de la semana 1: la señal de éxito, GitHub privado hasta el 25 de octubre y este DEVLOG.

**Salió mal y se aprendió**
* El implementador de F4b-2 cableó el hook antes de su `import`; el hook, que se relee en cada
  llamada, dio `NameError` y denegó todas las escrituras en `.py` gobernados, también la que lo
  arreglaba. Se devolvió a `HEAD` con permiso del autor. Ahora es AGENTS 6.5.
* La revisión de la integridad del commit encontró que `TESTS/x.py` pasaba junto a `tests/x.py` en un
  sistema de ficheros que no distingue mayúsculas; se corrigió antes de fusionar (`ceef6a7`).
* Un `git checkout <commit> -- <ruta>` que falla en el sandbox ya ha escrito el índice (S8): de ahí la
  integridad del commit.
* Errores del chat principal: un `python3 -` suelto en una orden (no ejecutó nada, pero AGENTS 4.2 lo
  prohíbe); un commit hecho con un test en rojo porque el `&&` seguía al `tail` y no a `pytest` (se
  rehízo; desde entonces se mira el código de salida de `pytest`); una lectura equivocada de la
  transcripción en S5 que el autor corrigió; y dos contratos con un detalle falso (`.actuarii.json`
  fuera de `governed_paths`, y que `deny_python_escapes.py` deniega `python3 -c`), que el implementador
  detectó y resolvió bien.

## 2026-10-06

Reconstruida. Suite: de 1768 a 2350 en verde.

**Hecho**
* Fase 1, pasos 5 y 6: el anuncio al abrir sesión (`453fd01`), la revisión ciega configurable
  (`1bce3ce`), fuera lo que solo servía a Traianus (`c199173`) y `AGENTS.md` genérico con sus
  subagentes y skills (`28848f5`). Fase 1 cerrada con 1979 tests (`4c68bdf`).
* Búsqueda previa: no hay nada igual; se ajusta la presentación, no el kit (`b13f88d`).
* Auditoría adversarial con pautas aprobadas antes de empezar (`d00af1e`): casos A01–A18 y plan de
  correcciones F1–F7 (`cac165d`).
* F1, el cableado del kit gobernado (`afe12bb`); F2, la puerta deniega por defecto (`65f6d30`); F3,
  entrada estricta del validador (`47f29be`); F4a, el recibo ata el contenido exacto (`d87032d`).

**Decidido (autor)**
* Calendario de tres semanas hasta el 25 de octubre y criterio de utilidad para retomar Traianus
  (`7910a63`).
* La auditoría adversarial se adelanta al empaquetado. F2 deniega por defecto y la matriz léxica se
  elimina en F4 (`c1669dc`).

## 2026-10-05

Reconstruida. Suite: 1497 en verde al cerrar la fase 0, 1768 al final del día.

**Hecho**
* Extracción del kit desde Traianus con la historia conservada; plan y `CLAUDE.md` (`5497eb4`).
* Fase 0: la suite pasa sin Traianus instalado (`49a6464`).
* Fase 1, pasos 1 a 4: los hooks no dependen del directorio actual (`cc81355`), la configuración del
  proyecto en `.actuarii.json` (`6cf5eb9`), los directorios del shim (`f7f1182`) y el registro de
  contratos (`7d5498a`) salen de ella.
