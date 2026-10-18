# DEVLOG de Actuarii

Una entrada por día, la más reciente arriba: qué se hizo (con sus commits), qué se decidió y por qué, qué
salió mal y qué se aprendió. Lo que ya cuentan los documentos de diseño se enlaza, no se repite. Se
escribe al cerrar cada sesión (decisión del autor, 2026-10-07). Las entradas del 5 y el 6 de octubre se
reconstruyeron el 7 a partir de `git log` y de `docs/PLAN.md`.

## 2026-10-18 (evening)

The first entry in English. The published tree goes into English (ADR-032); the status, the memory and the roadmap
are translated.

**Done**
* **The inventory of what gets published:**
  * the kit, its tests and the reference documents (README, INSTALL, AGENTS, agents and skills) were already in
    English;
  * `docs/` (about 6,400 lines) and the memory were in Spanish, and so are the messages of the 329 commits.
* **Found while making the inventory, and left to the author** (status, pending item 2):
  * three lines of `PLAN.md` about the author's professional plans;
  * `examples/traianus/`, which nothing uses and which still says "Blind by construction".

  The tree and the history are both published: taking something out of the tree does not take it out of the
  history.
* **ADR-032.**
* **Translated, edited for a reader from outside:**
  * `ESTADO.md`, brought up to date at the same time;
  * the four memory files, each with its receipt; `pocas-peticiones-al-autor.md` now says that ADR-022 removed the
    bare `"Bash"` it describes;
  * `ROADMAP.md`, with V7 rewritten and a new V10 for the translation. Dated notes mark what changed since: option
    (c) in `MEMORY.md`, fixed in `0116031`; the Traianus case, replaced by ADR-030.
* **The README** no longer marks the ROADMAP as Spanish.

**Decided (author)**
* **ADR-032:** the published tree in English, by priority, with what is not translated by the 25th leaving the tree;
  the history stays as it is; the repository's documents are written in English from now on.

**Next**
* **The author:** review the translated `ROADMAP.md` as the sample of tone and edits, and the three decisions above.
  On closing, the author said that "we will be able to shorten"; what and how is to be agreed before translating
  more, and is not recorded as a decision.
* **Translation, priority 1:** `CASES.md`, `PRUEBA_EN_LIMPIO.md`, `COSTE.md`, `ENTORNO_PROPIO.md`, `SANDBOX.md`.
  Then `DECISIONES.md`, then the rest. When it is done, the README's line about Spanish says that the history keeps
  the original commit messages.

## 2026-10-18 (última hora de la tarde)

La denegación de `pytest` a través del intérprete orienta (ADR-031), y el caso real queda cerrado en GitHub.

**Hecho**
* **El caso, cerrado por el autor:** la rama `v3-exp-clasificador`, en GitHub (AI-Papers-Engine); el rastro, copiado
  a la evidencia e idéntico, comprobado con `cmp`.
* **El orden, comprobado antes de decidir:** la documentación de Claude Code (`code.claude.com/docs/en/hooks`, leída
  con el navegador integrado) dice que las reglas de permisos se evalúan sobre lo que devuelve el hook
  `PreToolUse`, y que el motivo de su denegación se le muestra al agente.
* **ADR-031 y su contrato** (`docs/design/PYTEST_NOMBRADO.contrato.json`), en `9b83e01`.
* **El implementador** (Sonnet, unos 16 min), en `v01/pytest-nombrado` (`f42cd45`):
  * R7 en `deny_python_escapes.py`, con una función que lee las opciones del intérprete;
  * la línea del anuncio, como constante compartida por el caso válido y el inválido;
  * 20 tests que fallan en la base y pasan al final; la suite, con 3705.
* **Comprobado por el chat:**
  * el informe es válido;
  * `verify_red_green.py` sale con 0;
  * el diff solo toca los cuatro ficheros del contrato, y su acta dice `matches` en los cuatro;
  * **en vivo:** `python3 -m pytest --version` en esta sesión recibe la denegación del hook, con R7, y no la genérica.
* **`main` avanzado** hasta `f42cd45`. El README cierra el caso con el arreglo, y §5 lo anota.

**Salió mal y se aprendió**
* **R7 alcanzó a su propio commit:** el mensaje del contrato mencionaba `python3 -m pytest`, y `git commit -m` se
  denegó. Es el límite declarado de una mención entre comillas, el mismo que tiene R2. El implementador commiteó con
  `git commit -F -` y un heredoc. Lección: los mensajes de commit no nombran esa orden; si hace falta nombrarla, se
  usa `-F` con un heredoc de delimitador entre comillas.
* **Una propuesta enviada por error queda en el rastro** (`32a57642…`), sin usar en ninguna escritura. El acta del
  commit no la lista, porque solo lista los recibos de escrituras que llegaron al commit.

**Siguiente**
* **Una lectura entera del README,** antes del jueves 22.
* **V7, V9 y la comprobación de V8.**

## 2026-10-18 (tarde, el caso real hecho)

El caso real del README está hecho, con el plan de §4f: dos commits en `noticias` con su acta, el registro
comprobado y un hueco del kit encontrado.

**Hecho**
* **El caso,** en `~/Documents/noticias-caso`, rama `v3-exp-clasificador`, en 8 min 32 s de sesión. El detalle, en
  `docs/design/PRUEBA_EN_LIMPIO.md` §5:
  * el test (`0ef8fb5`) y el arreglo (`69d1c36`) llevan `Actuarii-Record: matches`, con los motivos del agente en
    español;
  * la puerta rechazó un `importlib` y un `Edit` sin su recibo, y el agente salió solo de las dos.
* **Comprobado por el chat:**
  * el registro, por §4c: tres escrituras, cada una con su recibo, con las citas y los bloques recalculados desde la
    transcripción con `jq` y `shasum`, y la cadena de `writes` hasta el fichero commiteado;
  * el rojo y el verde, cada commit reconstruido en el scratchpad y ejecutado con el `pytest` del entorno: 2 fallan
    y 1 pasa en `0ef8fb5`, y pasan los 3 en `69d1c36`.
* **La sección del README,** escrita, con los enlaces a los dos commits en GitHub.
* **No hubo ningún «sí, hazlo».** Por la pantalla parecía que el agente había encontrado `pytest` solo. La
  transcripción dice que la persona escribió «usa pytest directamente».

**Salió mal y se aprendió**
* **La denegación de `python3 -m pytest` no orienta.** El agente lo intentó tres veces y no probó `pytest` hasta que
  la persona se lo dijo. Es un hueco del kit, no del agente.
* **El chat sacó conclusiones de lo que el autor pegaba de la pantalla:** el «sí, hazlo» no llegó a enviarse.
  Lección: lo que pasó en una sesión se lee en su transcripción, no en la pantalla.

**Siguiente**
* **El autor:** subir la rama del caso y copiar su rastro a la evidencia.
* **El autor decide** si la denegación nombra `pytest` (ESTADO, pendiente 2).

## 2026-10-18 (tarde, el caso real)

El caso real del README será en `noticias` v3, no en Traianus (ADR-030), con su plan escrito antes de hacerlo.

**Hecho**
* **El repaso de `noticias` v3 con el autor:**
  * commiteados, una hipótesis (H1), un protocolo congelado con criterios de éxito y de fracaso, y un experimento 0
    de 9 papers;

  `origin` es `github.com/AlexusPacicus/AI-Papers-Engine`, público según el autor.
* **Los dos defectos del clasificador, confirmados al leer `origin/v3-exp`:** la búsqueda por subcadena (`gan`
  dentro de `organization`) y el empate de `diffusion transformer` con `diffusion`, que da `other`.
* **ADR-030 y el plan del caso** (`docs/design/PRUEBA_EN_LIMPIO.md` §4f). El plan fija:
  * la preparación, con los restos de la medida borrados antes, porque `~/Documents/actuarii` haría parar el
    bloque;
  * el texto único de la tarea, que dice dónde van los tests para que queden dentro de lo gobernado;
  * lo que se comprueba después y lo que se cuenta, salga como salga.
* **Al día:** V6 del ROADMAP, la sección del caso en el README, y el ESTADO con el calendario hasta el 22.

**Decidido (autor)**
* **ADR-030.**

**Siguiente**
* **El autor:** el caso, con el plan de §4f, como tarde el miércoles 21.
* **Para decidir:** el instalador copia el kit (Apache-2.0) sin el texto de la licencia. Quien lo instale en un
  repositorio público lo redistribuye sin esa copia, que la licencia pide.

## 2026-10-18 (tarde)

El README está en `main`, con los límites en ocho problemas y la instalación medida. Le falta el caso de Traianus.

**Hecho**
* **`v01/readme` encima de `main`,** sin merge ni reescribir el árbol: la rama se movió a `main` y el borrador se
  volvió a aplicar con `cherry-pick` (`867a6a9` sustituye a `59487c1`, que nada citaba).
* **La sección de límites del README** (`2092f2f`), la otra mitad de V5 (ADR-026):
  * cuatro problemas de gobernanza y cuatro de seguridad, cada uno con su motivo, un ejemplo y lo que cambia en la
    v0.2, sin los ids de los casos;
  * lo de la v0.2, tomado de `ENTORNO_PROPIO.md` (§3, §4.3, §5 y §6), sin prometer más: una persona que apruebe
    cada recibo no está prevista, y la inyección de prompt no se resuelve;
  * el ejemplo del problema 2 sale de la medida: Claude Code pidió aprobar la escritura y mostró su contenido, pero
    el motivo solo llegó al validador.
* **`main` avanzado** hasta `2092f2f`.
* **La instalación del README:** el bloque de `INSTALL.md` (ADR-028), la primera pregunta con el destino
  (ADR-029) y la cifra de V4. Son 223 s, medidos una vez por el autor, que conoce el kit, frente a los 612,8 s del
  procedimiento anterior.

**Siguiente**
* **El autor:** el caso de Traianus (cuál, si sus commits son públicos y si se puede leer su repositorio).
* **V7 y V9.** La comprobación de V8, adelantada si el autor da su lista de términos.
* Ramas que ya están en `main` y se pueden borrar: `v01/readme`, `v01/limites` y `v01/destino-nombrado`.

## 2026-10-18 (mediodía)

El instalador nombra el destino en su primera pregunta, antes de escribir (ADR-029), por contrato al implementador.

**Hecho**
* **ADR-029 y su contrato** (`docs/design/DESTINO_NOMBRADO.contrato.json`, validado), en `15fe01a`. Antes de
  delegar, se sirvió el contexto con `context_pack.py` para comprobar que encuentra cada sección.
* **El implementador** (Sonnet, unos 49 min) hizo su commit en `v01/destino-nombrado` (`119d569`). La pregunta de
  qué más gobernar empieza con `installing into <destino>; nothing is written until you answer, and Ctrl-C stops
  here`, y como el resto de la pregunta solo sale en un terminal. Dos tests nuevos, en proceso, con una entrada que
  se hace pasar por terminal; seis tests de guarda sin cambios.
* **Comprobado por el chat:**
  * el informe es válido;
  * `verify_red_green.py` sale con 0: T1 y T2 fallan en la base y pasan al final, T3 pasa en los dos y la suite
    completa pasa al final;
  * el diff solo toca `tools/install.py` y `tests/unit/test_installer.py`;
  * el acta del commit dice `matches` en los dos, con sus motivos.
* **`main` avanzado** hasta `119d569` sin reescribir el árbol. **`INSTALL.md`,** al día: la primera pregunta nombra
  el repositorio, y Ctrl-C para antes de escribir nada.

**Decidido (autor)**
* **ADR-029.**

**Siguiente**
* **La sección de límites del README** y, después, el README.

## 2026-10-18 (antes del mediodía)

La medida en macOS (V4) está superada: 223 s desde el clon de `noticias` hasta el hito 2 (intento 5). El kit acabó
instalado en el repositorio de trabajo del autor y se deshizo sin pérdida.

**Hecho**
* **El intento 5,** en `docs/design/PRUEBA_EN_LIMPIO.md` §5, con la guía de un bloque (`93cc0c9`). El bloque funcionó
  a la primera: instalación, `pydantic` desde cero y commit, a los 139 s. La puerta denegó en vivo la primera
  escritura, cuyo recibo era de `Prueba` sin el salto de línea final, nombrando la regla y su fuente. El agente salió
  solo de ella.
* **El hito 1, comprobado por §4c** sobre una copia de la base de auditoría, con `sqlite3` en modo inmutable:
  * el recibo `16305fd8…` es anterior a la escritura y está dentro de la ventana;
  * su `block_sha256` es el SHA-256 de `Prueba\n`;
  * la tabla `writes` registra esa escritura con ese recibo.
* **La instalación, deshecha en `~/Documents/noticias`:** la evidencia, copiada antes; después
  `git reset --keep 1676538` y fuera `tools/`, `.data/`, el `.claude/` de la raíz y los dos hooks de git. El trabajo
  sin commitear del autor quedó intacto. Comprobado: `HEAD` en `1676538`, al día con `origin/v3-exp`.
* **Los clones de prueba viejos, borrados por el autor,** con la evidencia de los intentos 2 y 3 y de la 2b guardada
  antes en `~/Documents/actuarii-evidencia/`. El clon de Actuarii con la historia anterior a la reescritura, y con
  la información personal, ya no está en la máquina.

**Decidido (autor)**
* El intento 5 vale como la medida V4, con sus desviaciones anotadas, si se cumple el hito 1 por §4c. Se cumple.

**Salió mal y se aprendió**
* **El bloque instala donde está la terminal,** y la terminal seguía en el repositorio de trabajo del autor. Que el
  instalador escriba solo ficheros nuevos y commitee solo los suyos permitió deshacerlo sin pérdida. Pero dice dónde
  instala solo después de escribir.
* **El mensaje del chat con la limpieza se cerró sin su contenido:** la caja de la pregunta se mostró antes que el
  texto. Lección: el texto va antes de la pregunta.

**Siguiente**
* **El autor decide** si el destino se nombra antes de escribir (ESTADO, pendiente 1).
* **La sección de límites del README** y, después, el README con la cifra de V4.
* Restos de la medida, sin prisa: `~/Documents/actuarii`, `~/Documents/noticias-medida-3` y `~/.venvs/actuarii`.

## 2026-10-18 (mañana)

La medida en macOS se paró en el paso 3 y quedó en ensayo (intento 4). La guía pasa a ser un solo bloque que se pega.

**Hecho**
* **El intento 4,** en `docs/design/PRUEBA_EN_LIMPIO.md` §5: ensayo, sin cifra. Se copiaron tal cual las rutas del
  ejemplo del paso 3 de la guía (`~/src/actuarii`, `~/src/your-repo`). Es el roce del intento 2, que se había
  corregido con un aviso en prosa. Además, `~/src` no existe en esta máquina.
* **`INSTALL.md` en un solo bloque (ADR-028)** que se pega desde la raíz del repositorio. Saca la ruta de
  `git rev-parse`, clona Actuarii al lado, crea y activa el entorno fuera y ejecuta el instalador; cada paso, unido
  con `&&`. El instalador encuentra su clon por su propia ruta (`Path(__file__)`), así que no hace falta `cd`. Sin
  ejecutar el bloque de punta a punta: el sandbox no deja clonar desde la red ni crear el entorno en `~/.venvs`, y el
  shim deniega `python3.11 -m venv`. Lo prueba la medida.
* **La enmienda §4e:** el bloque pegado tal cual, con el clon de Actuarii dentro del tiempo, anotado en su propio
  parcial.

**Decidido (autor)**
* **ADR-028:** la instalación, en un bloque que se pega; la orden única con pantalla propia, en la v0.2.

**Salió mal y se aprendió**
* **El chat dio, antes de medir, las órdenes de los clones con rutas que no eran las de la guía,** y el `cd` del
  paso 3 ya no podía funcionar. Lección: en una medida, el chat da el método, nunca órdenes.
* **Un aviso en prosa no corrige un roce de copiar y pegar:** el del intento 2 volvió. Lo que lo corrige es que la
  orden copiada sea la correcta.

**Siguiente**
* **El autor:** el push de `main`, borrar `~/.venvs/actuarii` y repetir la medida con §4e. El destino,
  `~/Documents/noticias-medida-4`: el bloque clonará Actuarii en `~/Documents/actuarii`, que no existe.

## 2026-10-18 (mañana, cierre del 17)

La sesión del 17 sigue abierta. La entrada de abajo se escribió a media tarde, antes de la tabla de V5; esta cierra
el resto del día.

**Hecho**
* **La tabla «Resumen» de `docs/adversarial-audit/CASES.md` (V5, ADR-026),** en `da3ccd0`, en la rama
  `v01/limites`:
  * ocho problemas, cada uno con su motivo, sus casos con su estado y sus límites de AGENTS §9; al pie, A17, A20,
    A22, A27 y los controles del primer día;
  * comprobado con `grep`: los 35 casos y los 28 límites de §9 salen una vez cada uno. Suite: 3681 en verde;
  * los commits citados son los merges a `main` de F1–F4 y del sandbox, como en `docs/process/PROCESO.md`; para
    A20, A31 y A34, el commit de la corrección;
  * A05, corregido por F4b, con lo que queda en §9. A09, corregido en la sesión, y A10, corregido para `Bash`. A18,
    sin el commit de su arreglo parcial: queda «reabierto como A21».
* **`main` avanzado hasta `v01/limites`** sin reescribir el árbol. **El push, del autor:** `origin/main` en
  `da3ccd0`.

**Salió mal y se aprendió**
* **El ESTADO se quedó viejo una noche:** la entrada y el ESTADO del 17 se escribieron con el commit de las ADR, y la
  tabla llegó después. Lección: se cierran después del último commit de la sesión.

**Siguiente**
* **La medida en macOS (V4),** del autor, hoy. Mientras mide, el chat no ejecuta la suite: comparten la máquina, y
  la suite mueve los tiempos.
* **La sección de límites del README,** la otra mitad de V5, en `v01/readme`. Esa rama va dos commits por detrás de
  `main`: antes de seguir, se le trae `main`.
* `v01/limites` ya está en `main`; se puede borrar.
* Disco: 6,6 GiB libres, desde 9 GiB el 17.

## 2026-10-17 (tarde)

Sesión del sábado 17, desde las 16:15. Dos decisiones del autor sobre cómo se cuentan los límites y cuándo sale el
texto. Sin cambios de código.

**Hecho**
* **Al arrancar:** sandbox activo y los dos hooks instalados; `main` igual que `origin/main` en `2efa73a` (el push
  del 16, hecho); en `origin`, solo `main`; árbol limpio en `v01/readme`. D5 se mantiene: el contexto de esta
  sesión no trae la memoria automática.
* **ADR-026 y ADR-027,** con el ROADMAP (§1, V5, V9, §3, §4 y §5) y el ESTADO al día.

**Decidido (autor)**
* **ADR-026:** los límites, por problemas y no por casos: cuatro de gobernanza (v0.1) y cuatro de seguridad
  (v0.2), siguiendo el perfil A y B de la auditoría. El autor añadió que el problema 2 se nombre por lo que le falta:
  ninguna persona aprueba los recibos ni sus motivos (*human in the loop*).
* **ADR-027:** el repositorio se abre el 25, el texto sale el martes 27 y la puerta pasa al martes 24 de noviembre.

**Salió mal y se aprendió**
* El ESTADO decía que ADR-012 y ADR-023 «sustituyen» a ADR-022 y ADR-024; es al revés. Corregido.

**Siguiente**
* **La medida en macOS (V4),** del autor, como tarde el domingo 18. Hasta entonces no se tocan `INSTALL.md`,
  `tools/install.py` ni `AGENTS.md`.
* **Los límites, por problemas (V5),** el lunes 19.
* Disco: 9 GiB libres.

## 2026-10-16 (tarde)

Sesión nueva del viernes 16, de las 13:00 a las 17:45. La enmienda de la prueba en limpio para V4 entró en `main`, y
el README tiene su primer borrador, en su rama hasta después de la medida. Suite: 3681 en verde, sin cambios de
código.

**Hecho**
* **Al arrancar:** sandbox activo y hook de integridad instalado; `main` en `f4d1d9d`, igual que `origin/main` (el
  push del 15, hecho); árbol limpio.
* **D5, comprobado:** es la primera sesión nueva después de `0116031`, y su contexto ya no trae la sección de la
  memoria automática. El directorio de esa memoria sigue vacío desde el 5 de octubre.
* **La enmienda §4d de `docs/design/PRUEBA_EN_LIMPIO.md`** (`abb0d83`), para medir V4 con la instalación en una
  orden:
  * un entorno nuevo, fuera del destino y sin las dependencias de `noticias`;
  * respuestas fijas al instalador: ninguna ruta extra, sí a `pydantic` y sí al commit;
  * un cronómetro con un parcial por paso, y el registro como contraste;
  * después, sin cronómetro, el commit de `AGENTS.md`, que tiene que llevar `Actuarii-Record: matches`.
* **El borrador del README (V6),** en la rama `v01/readme`, sin push:
  * en el orden de V6: la frase con su primer límite, el marco, la tabla de canales, 12 garantías, el coste, lo que
    cae en la persona, la v0.2 y la licencia;
  * cada garantía nombra su test. Los 20 tests citados se ejecutaron: 89 casos, todos en verde;
  * tres huecos marcados «Draft»: los límites (V5), la cifra de la instalación (V4) y el caso de Traianus.
* **Fuera de `main` hasta después de la medida (Claude):** §1 de la prueba en limpio toma como guía la del commit
  que se prueba. Si el README llegara al clon antes de medir, la medida leería otra guía. En su rama, el push de
  `main` del autor no lo lleva.

**Decidido (autor)**
* La enmienda §4d, tal cual.
* La frase del README es la de ADR-009. Ya lleva «trazabilidad», que sustituyó a «seguimiento o transparencia» en la
  sesión del 14.
* El caso de Traianus va en el README. El autor dirá cuál es y si sus commits son públicos.
* El borrador del README se commitea en local, sin push.

**Salió mal y se aprendió**
* **El autor no reconoció la frase del README.** Los registros y la transcripción de la sesión del 14 mostraron que
  era la decidida. Lección: un texto decidido se presenta con su ADR, para que se reconozca.
* **La cifra del coste es del 7 de octubre.** Desde entonces, `validate_proposal` está en `permissions.allow`
  (ADR-022) y la puerta guarda lo que deja cada escritura (ADR-016). No se ha vuelto a medir; el README lo dice.
* **V7, encontrado:** la descripción de `pyproject.toml` («Governance kit for coding agents: rules enforced in
  code…») no coincide con la frase. Además, «5 Radicals» o «Blind by construction» siguen en
  `RECIBO_CONTENIDO.md`, `ENTORNO_PROPIO.md`, `PRIOR_ART.md`, `PROCESO.md` y el `SKILL.md` de `examples/traianus`,
  y la exención de `.claude/**`, en `SANDBOX.md`.

**Siguiente**
* **El autor:** el push de `main`, que lleva `abb0d83` y no el README.
* **La medida en macOS (V4),** del autor, el sábado o el domingo, con un clon nuevo de `main` desde GitHub.
* **La tabla «Resumen» (V5),** de A13 a A35, como tarde el lunes 19.
* **El caso de Traianus:** el autor dice cuál, si sus commits son públicos y si se puede leer su repositorio. Las
  ramas locales `feat/p1-engine-gate` y `feat/p1-qwen3-provider` parecen las de los dos casos del PLAN.
* **V7,** con lo encontrado arriba.
* Disco: 9 GiB libres.

## 2026-10-16 (mediodía, cierre de la sesión del 15)

La sesión del jueves 15 por la tarde siguió abierta para seguir las dos que el autor arrancó desde su tarjeta: la
del segundo contrato del instalador y, desde ella, la de D5. Su trabajo está en las dos entradas de abajo; esta solo
cierra.

**Hecho**
* **Comprobado en el repositorio,** no solo en los informes de esas sesiones: `main` en `3d59864`, 13 commits por
  delante de `origin/main`, árbol limpio, y `"autoMemoryEnabled": false` en `.claude/settings.json`. Sus
  verificadores no se repitieron aquí; la suite, sí, antes de este commit (3681 en verde).

**Salió mal y se aprendió**
* **Esta sesión no vale como la comprobación de D5:** arrancó el 15, antes de `0116031`, y su contexto sigue
  trayendo la instrucción de la memoria automática. No escribió nada allí. La comprobación es de la próxima sesión
  nueva.

**Siguiente**
* **El autor:** el push de `main`.
* **La medida en macOS (V4)** y lo que sigue en `ESTADO.md`.
* Disco: 11 GiB libres.

## 2026-10-16 (mediodía)

Segunda sesión del viernes, abierta desde la primera. El contrato pequeño de D5 entró en `main`: la memoria
automática de Claude Code, apagada en este repositorio. Suite: de 3676 a 3681 en verde.

**Hecho**
* **Al arrancar:** sandbox activo y hook de integridad instalado; `main` en `daf478a`, 10 commits por delante de
  `origin/main`; árbol limpio.
* **El ajuste, comprobado en la documentación** (code.claude.com/docs/en/memory y /settings-reference, leídas el
  16): `autoMemoryEnabled`, booleano, vale en cualquier fichero de ajustes; con `false`, Claude Code ni lee ni
  escribe la memoria automática. Un `.claude/settings.local.json` lo supera, y `CLAUDE_CODE_DISABLE_AUTO_MEMORY`
  manda sobre él en los dos sentidos.
* **La memoria automática, apagada (D5, ADR-010)** (contrato `docs/design/MEMORIA_AUTOMATICA.contrato.json`,
  `57e7a5c`; implementación `0116031`, `sonnet`, 23 min):
  * `.claude/settings.json` lleva `"autoMemoryEnabled": false`, y un test nuevo lo fija
    (`tests/security/test_auto_memory_setting.py`);
  * la fijación de las claves de `settings.json` (`test_registration_changes_nothing_else_in_settings`) la cuenta
    como el séptimo cambio deliberado;
  * el instalador no cambia: del clon solo copia `permissions` y `hooks`. Dos tests de guarda lo fijan: una
    instalación nueva no añade la clave, y un `true` del destino se conserva;
  * `.claude/memory/MEMORY.md` ya no dice que la opción (c) deniega esa memoria: dice que la apaga un ajuste, que no
    es una denegación, y qué puede volver a encenderla (texto elegido por el autor);
  * verificado por el chat con `verify_red_green.py`: T1 y T2 rojos, T3 de guarda, suite 3681. El alcance,
    comprobado a mano: los 5 ficheros del contrato. Las cinco actas del commit dicen `matches`.
* `main` avanzado sin merge hasta `0116031`.

**Decidido (autor)**
* La línea de `MEMORY.md`, con el límite: un `.claude/settings.local.json` o la variable pueden volver a encender la
  memoria automática.

**Salió mal y se aprendió**
* **El efecto no se puede ver en esta sesión:** el hook de `ConfigChange` no aplica a la sesión en curso un cambio
  de los ajustes del proyecto, y esta sesión arrancó con la memoria automática encendida (su contexto trae la
  instrucción de escribirla). No se escribió nada allí; el directorio sigue vacío desde el 5 de octubre.
* El primer `commit_message` del contrato pasaba de 100 caracteres y el validador lo rechazó; se acortó.

**Siguiente**
* **La sesión siguiente comprueba** que su contexto ya no trae la sección de la memoria automática.
* **El autor:** el push de `main`.
* **La medida en macOS (V4),** con la enmienda de `docs/design/PRUEBA_EN_LIMPIO.md` commiteada antes; la hace el
  autor, como tarde el domingo 18.
* Después, lo que sigue en `ESTADO.md`.
* Disco: 12 GiB libres.

## 2026-10-16

Sesión empezada el jueves 15 a las 16:50, cortada por el límite de uso y seguida el viernes 16 por la mañana. El
segundo contrato del instalador salió en dos, el acta en git y las preguntas, y los dos entraron en `main`. El acta
registró su primer commit real. Suite: de 3382 a 3676 en verde.

**Hecho**
* **Al arrancar:** sandbox activo y hook de integridad instalado; `main` en `1f7e49d`, 5 commits por delante de
  `origin/main`; árbol limpio.
* **Las elecciones del autor** antes de los contratos (ADR-025): dos contratos, el acta primero; sin acta cuando la
  puerta no puede calcular lo que deja una escritura; solo una ruta o una carpeta seguida de `/**` como ruta
  gobernada extra; `INSTALL.md`, del chat.
* **El acta en git (V3, ADR-016)** (contrato `docs/design/ACTA_EN_GIT.contrato.json`, `31a3567`; implementación
  `d5aa611`, `sonnet`, 1 h 12 min):
  * antes de dejar pasar un `Edit`, `MultiEdit` o `Write` gobernado, la puerta guarda en la tabla `writes` de la base
    de auditoría el hash del fichero antes, el del resultado y los recibos que lo cubren; si no puede guardarlo,
    deniega;
  * `tools/git/commit-msg` y `tools/git/commit_record.py`: cada commit lleva, por cada fichero gobernado que cambia,
    `Actuarii-Record: matches: <ruta>` con los motivos de las escrituras que llevan de `HEAD` al commit, o
    `changed outside the channel`. Nunca impide un commit: si falla, lo dice (`not made`);
  * el instalador pone el `commit-msg` junto al `pre-commit`;
  * AGENTS.md v2.3.0: la cláusula 2.7 y dos límites nuevos en §9;
  * verificado por el chat con `verify_red_green.py`: T1–T3 y T5–T9 rojos, T4 y T10 de guarda, suite 3526. El
    alcance, comprobado a mano: los 11 ficheros del contrato.
* **El hook `commit-msg`, instalado en este repositorio** (autor).
* **Las preguntas del instalador (V2)** (contrato `docs/design/INSTALADOR_PREGUNTAS.contrato.json`, `2a445f1`;
  implementación `ba6a120`, `sonnet`):
  * qué más gobernar, por pregunta o con `--govern`, con su entrada de `denyWrite`; una configuración con rutas extra
    se adopta en la vuelta siguiente;
  * `pip install` solo con un sí o `--install-pydantic`, nunca para un entorno dentro del destino;
  * el commit de la instalación solo con un sí o `--commit`, con los ficheros que escribió y nada más;
  * `--no-input`, para la CI y los tests;
  * verificado por el chat: T1–T6 rojos, T7, X1 y X2 de guarda, suite 3676. El alcance: los 2 ficheros del contrato.
* **La primera acta real:** el commit `ba6a120` lleva `Actuarii-Record: matches:` en sus dos ficheros, con los
  motivos de sus 13 y 19 escrituras.
* **`INSTALL.md`, reescrito:** el entorno fuera del repositorio, la orden única con sus preguntas, el modo sin
  preguntas y el acta.
* `main` avanzado sin merge hasta `ba6a120`.

**Decidido (autor)**
* **ADR-025:** el acta en git y las preguntas del instalador, en dos contratos, con las elecciones de arriba.

**Salió mal y se aprendió**
* **El contexto del contrato A pesaba 68 KB,** por encima del tope de 40 KB de `context_pack`. Se recortó a 38 KB con
  símbolos y rangos cortos. Lección: un contrato que toca muchos ficheros sirve símbolos, no ficheros enteros.
* **`run_process` devuelve texto UTF-8 estricto,** y el contrato A pedía el hash de los bytes de un blob. Se vio
  repasando el contrato antes de lanzarlo: un blob que no es UTF-8 queda como `changed outside the channel`, y está
  declarado en §9.
* **El implementador de B se cortó por el límite de uso** con los tests escritos. Se retomó por la mañana con su
  contexto y terminó en 23 min.
* **Una desviación de A, aceptada:** la puerta lee el fichero también en un `NotebookEdit`, y deniega si el sistema
  no la deja leerlo; el contrato decía que esas decisiones no cambiaban. Es el lado seguro, y solo afecta a escrituras
  que fallarían igual.
* **Las actas son largas:** un fichero con 19 escrituras lleva 19 líneas de motivo. Es lo decidido (los motivos
  distintos, en orden).
* **Encontrado por el implementador de A, fuera de su alcance:** `project_config.path_matches` traduce `**` sin
  `re.DOTALL`, así que un fichero cuyo nombre tiene un salto de línea, bajo `src/**`, no queda gobernado.
* **Menores de B:** un `git add` o un `git commit` del instalador que pase de 300 s acaba con una traza de Python; y si
  el ejecutable que nombra la comprobación está dentro del destino con el intérprete fuera, no se pregunta por `pip` y
  ninguna línea dice por qué.
* El implementador de A dejó copias de trabajo en `/tmp/claude-501/acta-work` y `/tmp/claude-501/scratch`, fuera del
  repositorio; `rm` le está denegado.

**Siguiente**
* **El autor:** el push de `main`.
* **El contrato pequeño de D5:** `autoMemoryEnabled: false`, con su test y la línea de `.claude/memory/MEMORY.md`.
* **La medida en macOS (V4),** con el instalador nuevo y la enmienda de `docs/design/PRUEBA_EN_LIMPIO.md`
  commiteada antes; la hace el autor, como tarde el domingo 18.
* Después, lo que sigue en `ESTADO.md`.
* Disco: 12 GiB libres.

## 2026-10-15 (tarde)

Segunda sesión del jueves. La sonda del perímetro salió bien, la puerta dejó de bloquear los textos largos
(ADR-024, que sustituye a ADR-023) y el primer contrato del instalador entró en `main`. Suite: de 3296 a 3382 en
verde.

**Hecho**
* **Al arrancar:** sandbox activo y hook de integridad instalado; `main` igual a `origin/main` (`71b58b5`), con
  el push del cierre anterior hecho; árbol limpio y suite en verde (3296).
* **La sonda del perímetro (ADR-022):** `ls`, `git status` y `git for-each-ref refs/heads` pasaron sin pedir
  permiso, y `git commit --dry-run` preguntó (autor, en la segunda pasada, una orden por llamada). La sesión
  corría en modo auto; según el autor, la configuración hace que no cambie el resultado.
* **La medida del límite de un nombre, en el macOS del autor:** un nombre ASCII de 260 bytes da
  `File name too long`; uno de 86 «€» (258 bytes) se admite. APFS cuenta caracteres; ext4, bytes.
* **La puerta con los textos largos** (ADR-024; contrato `docs/design/PUERTA_NOMBRES_LARGOS.contrato.json`,
  `a0eb3cb`; implementación `cfa6ebf`, `sonnet`):
  * `ENAMETOOLONG` es «no es una ruta» solo si el sistema rechaza uno de los nombres de la ruta resuelta buscado
    solo bajo la raíz (`os.lstat` con `dir_fd`); con todos los nombres admitidos, la puerta sigue denegando;
  * `canonical` y `_same` no cambian, y el cambio vale igual para las herramientas que escriben y para las que la
    puerta no conoce;
  * verificado por el chat con `verify_red_green.py`: T1 y T2 rojos, T3–T6 de guarda. T4, el nombre de «€»,
    corre en macOS y se salta donde el sistema lo rechaza (ext4). El alcance, comprobado a mano.
* **El primer contrato del instalador (V2)** (`docs/design/INSTALADOR_ENTORNO.contrato.json`, `888d62d`;
  implementación `8902b4e`, `sonnet`):
  * el perímetro del clon llega al destino detrás de sus propias entradas, una vez cada una; un `defaultMode` que
    ya esté se respeta;
  * `includeGitInstructions: false`, y cualquier otro valor es un choque;
  * un `"Bash"` o un `"Bash(*)"` en `ask` o `deny` del destino da un aviso;
  * `tools/check_pydantic.py`: el instalador busca el intérprete del servidor como lo hará Claude Code (el
    `command` de `.mcp.json` en el `PATH`, desde el destino y saltándose el shim), lo ejecuta sin opciones y dice
    si tiene el `pydantic` fijado, con la orden de `pip` cuando no; nunca ejecuta un intérprete de dentro del
    destino;
  * verificado por el chat: T1–T7 y X1 rojos, T8 y X2 de guarda, suite 3382. El alcance, comprobado a mano. Un
    `--dry-run` real sobre un repositorio vacío nombró `~/.pyenv/versions/3.11.6/bin/python3` con
    `pydantic==2.13.3`.
* `main` avanzado sin merge hasta `8902b4e`.

**Decidido (autor)**
* **ADR-024**, que sustituye a ADR-023: solo un nombre que el sistema rechaza por sí solo deja de ser una ruta.
* El segundo contrato del instalador va en una sesión nueva.

**Salió mal y se aprendió**
* **ADR-023, tal como estaba, fallaba en abierto:** el sistema da el mismo `ENAMETOOLONG` para un nombre
  demasiado largo y para una ruta entera demasiado larga con los nombres cortos, y en el segundo caso el fichero
  puede existir.
* **Mi primera redacción de ADR-024, «más de 255 bytes», era falsa en macOS.** El autor la aceptó, la medida la
  desmintió y se corrigió antes del commit. La lección del 14 otra vez: un límite del sistema se mide antes de
  escribirlo en una decisión.
* **`deny_python_escapes.py` denegó un `grep`** cuyo patrón contenía la ruta del Python del sistema. Lee el
  texto, no la orden; está declarado en §9 («Clever shell»).
* **El tiempo de espera de 60 s de la comprobación de `pydantic` no tiene test:** el test tendría que esperar
  60 s.
* **Límite que queda de ADR-024:** la puerta pregunta al sistema de ficheros de la raíz. Un sistema montado
  dentro del repositorio que admita nombres más largos, junto con una ruta entera demasiado larga, la engañaría.
* **El `--dry-run` real avisó** de que el `~/.claude/settings.json` del autor no fija
  `sandbox.allowUnsandboxedCommands: false`. Lo decide el autor.

**Siguiente**
* **El autor:** el push de `main`.
* **Una sesión nueva, con el segundo contrato del instalador:** las preguntas (qué rutas gobernar, el commit y el
  permiso para `pip install`), el modo sin preguntas, el acta en git (V3: el `commit-msg` y la puerta que escribe
  en la base) e `INSTALL.md` reescrito con el entorno fuera del repositorio. Corte: viernes 16.
* Después, lo que sigue en `ESTADO.md`.
* Disco: 14 GiB libres.

## 2026-10-15

Primera sesión del jueves. Empezó poniéndose al día y siguió por otro lado: el autor dijo que seguía habiendo
demasiados permisos manuales, y la causa resultó ser el perímetro del 14, que en Claude Code no aprobaba nada. Se
arregló por contrato, con dos fallos del contrato corregidos después del resultado. El instalador no empezó.
Suite: de 3278 a 3296 en verde.

**Hecho**
* **Al arrancar:** sandbox activo y hook de integridad instalado; `main` igual a `origin/main` (`34f603a`), árbol
  limpio y suite en verde (3278).
* **La medida de los permisos,** en las transcripciones desde el 13: 795 llamadas a `Bash`. De las 352 del chat
  principal del 14, con la lista de AGENTS 7.1 habrían preguntado 231: 67 porque escribían, 80 por la forma de la
  orden (variables, `cd`, bucles) y 84 por una orden de lectura fuera de la lista (`cut`, `jq`, `awk`, `xargs`…).
* **La causa,** en la documentación de permisos de Claude Code (code.claude.com/docs/en/permissions, con el
  navegador integrado):
  * las reglas se evalúan deny, luego ask, luego allow, y una `ask` gana a una `allow` más estrecha;
  * `Bash` a secas cubre todas las órdenes.

  El `"Bash"` que encabezaba `ask` hacía preguntar todas las llamadas, también las que Claude Code ejecuta sin
  preguntar por sí mismo (`ls`, `git status`). La lista del 14 no aprobó nada en Claude Code; en OpenCode, donde
  gana la última regla, sí funciona.
* **La memoria** (`805884d`): `pocas-peticiones-al-autor.md` recoge la forma de las órdenes y la causa, y su línea
  del índice la resume.
* **Contrato del perímetro** (`docs/design/PERIMETRO_SIN_COMODIN.contrato.json`, `176ece9`, corregido en
  `cb43f28`) e implementación (`c9248dd` y `bc151d2`, `sonnet`):
  * sin `"Bash"` en `ask`: lo que pregunta por el resto es el modo `default`;
  * la lista gana `cut`, `tr`, `jq`, `cmp`, `date` (sin argumento o con formato `+`), `git merge-base`,
    `git rev-list` y `git for-each-ref`. `git branch` sigue preguntando, y las ramas se listan con
    `git for-each-ref`;
  * un test comprueba que ninguna regla `ask` o `deny` tapa una `allow`, comparándolas como lo hace Claude Code;
  * AGENTS 7.1, reescrito; §9 declara el `--output` de `git diff`, `git log` y `git show`;
  * `implementer.md`: una orden por llamada, sin variables, `cd`, bucles ni `$(...)`, y los globos entre comillas.
  * Verificado por el chat con `verify_red_green.py`: T1 y T3–T6 rojos, T2 y T7 de guarda, suite 3296. El
    alcance, comprobado a mano.
* `main` avanzado sin merge hasta `bc151d2`.

**Decidido (autor)**
* **ADR-022:** el perímetro sin comodín y con la lista ampliada, en un contrato pequeño antes del primero del
  instalador. Sustituye a ADR-012.
* **ADR-023:** la puerta lee `File name too long` como «no es una ruta», en un contrato pequeño en la sesión
  siguiente, después de la sonda.

**Salió mal y se aprendió**
* **El perímetro del 14 estuvo un día sin efecto en Claude Code.** Los tests fijaban la configuración y la
  normalizaban como si Claude Code resolviera las reglas igual que OpenCode, y nadie lo comprobó en una sesión. Es
  la lección del hueco de `.claude/memory/`: lo que hace un tercero se comprueba con una sonda. Y antes de escribir
  un test que modela a un tercero, se lee su documentación.
* **Mi primera cifra, un 66 % de llamadas que preguntaban, daba por buena la lista.** La memoria salió con ella y
  se corrigió en la misma sesión, después de leer la documentación.
* **Peticiones de más al autor, mías:** al empezar, órdenes con `cd`, variables y `awk`, y dos
  `grep --include=*.py` sin comillas que zsh rechazó.
* **El contrato tenía dos fallos, y se corrigió después del resultado** (D14), una desviación de AGENTS 8.6:
  * T2 no podía salir rojo: la función y sus casos viven en el fichero de tests que el verificador copia a la
    base. Lección: un test cuyo código está en el mismo fichero de tests es una guarda;
  * D9 citaba una cláusula de AGENTS.md en `implementer.md`, que el instalador copia a otros repositorios, y el
    implementador partió la cadena para pasar `test_kit_independence.py`. Lo paró la revisión del diff. Lección:
    un texto que el instalador copia no cita cláusulas, y un test no se esquiva troceando una cadena.
* **El primer implementador tardó 2 h 7 min,** con cada `Bash` pidiendo permiso: el coste de arreglar el perímetro
  desde una sesión con el perímetro roto.
* **Al cerrar, la puerta denegó una llamada a `start_session`.** `require_boundary_validation.py` revisa cada texto
  de una herramienta que no conoce, por si nombra una ruta gobernada. Un texto de más de 255 bytes sin barras da
  `File name too long`, la puerta lo toma por «no se puede verificar» y deniega. En un repositorio con el kit,
  cualquier herramienta con un campo de texto largo queda bloqueada. No se esquivó troceando el texto.
* **El commit del cierre pasó `pytest` por `| tail`,** así que la cadena comprobaba el código de salida de `tail`.
  La salida decía 3296 pasados; la orden no lo garantizaba.

**Siguiente**
* **El autor:** el push de `main`.
* **La puerta y los textos largos (ADR-023),** después de la sonda y antes del instalador.
* **Una sesión nueva** y, lo primero, la sonda: `ls`, `git status` y `git for-each-ref refs/heads` sin pedir
  permiso, y `git commit` preguntando. Si algo no sale así, se mira antes de seguir.
* **El primer contrato del instalador (V2):** el perímetro de ADR-022 en los destinos, `includeGitInstructions` y
  `pydantic`; el `denyWrite` ya lo lleva. Corte: viernes 16.
* Después, lo que sigue en `ESTADO.md`.
* Disco: 14 GiB libres.

## 2026-10-14 (noche)

Tercera sesión del miércoles. Se cerró la sonda del `denyWrite`; se escribió el ROADMAP, que el autor corrigió
y decidió entero, y se reescribió la historia sin la información personal y con el correo *noreply* de GitHub,
en un repositorio nuevo. Al final, las decisiones pasaron a un registro que solo se amplía
(`docs/DECISIONES.md`). Ningún cambio de código. Suite: 3278 en verde.

**Hecho**
* **La sonda del `denyWrite`:** desde `Bash`, abrir `.claude/memory/MEMORY.md` para añadir cero bytes da
  `operation not permitted`, y el sha queda igual. El hueco de la memoria queda cerrado en una sesión con los
  ajustes nuevos.
* **`docs/ROADMAP.md`** (`2891230`, `b66417b`):
  * los criterios de la v0.1, V1–V9, cada uno con su comprobación, su corte y lo que pasa si no se cumple el 25;
  * cómo se cuenta la señal, la puerta del 22 de noviembre y los criterios de la v0.2;
  * las decisiones D1–D7, todas tomadas.
* **La memoria de Claude Code, comprobada** con su documentación (code.claude.com/docs/en/memory, con el
  navegador integrado) y con las transcripciones:
  * `autoMemoryEnabled: false` la apaga en un proyecto, y `autoMemoryDirectory` la mueve, pero solo con una
    ruta absoluta;
  * la memoria normal de Actuarii está vacía desde el 5 de octubre;
  * de 31 transcripciones de subagentes, ninguna recibió la memoria automática, y 6 recibieron el índice de
    `.claude/memory/` a través de `CLAUDE.md`.
* **La historia, reescrita** con `git filter-repo`, sobre todas las ramas y etiquetas locales:
  * se quitó la información personal que fijó el autor: nueve líneas de cuatro ficheros en la versión actual,
    y diez variantes a lo largo de la historia. La lista no se guarda en el repositorio;
  * el correo de los 288 commits pasa a la dirección *noreply* de GitHub;
  * antes, un ensayo en copias desechables: ningún término queda en la historia, el diff es solo de esas
    líneas y la suite pasa;
  * la pasada real la lanzó el autor, después de guardar una copia local de la carpeta entera;
  * las 120 citas de commits de `docs/` se rehicieron con el mapa de `filter-repo` (`b837223`). Cada una apunta
    al commit con el mismo asunto que antes. La cita del HEAD de Traianus (`49d2434`) queda como estaba;
  * en GitHub, el repositorio viejo pasa a `actuarii-antiguo` y el autor empujó `main` a un `actuarii` nuevo,
    privado. Solo `main`: las ramas y las etiquetas viejas se quedan en local;
  * la CI del repositorio nuevo, en verde, y el viejo, borrado por el autor (`449e204`).
* **Una revisión sincera de Claude,** a petición del autor. Lo principal:
  * el proceso se sigue comiendo al producto. Desde el 5 de octubre hay 106 commits de documentación frente a
    24 de código, `docs/` tiene más líneas que el código del kit y el README tiene 0;
  * el recibo decide poco, y lo que aporta es el motivo guardado;
  * la adopción es el mayor riesgo para la señal.

  De ahí salieron un resumen ordenado del estado y, en `ESTADO.md`, una regla hasta el 25, como recomendación de
  Claude: cada tarea tiene que acercar el instalador o el README.
* **`docs/DECISIONES.md`:** ADR-001 a ADR-020 recogen las decisiones en vigor, cada una con su fecha y dónde
  está su razonamiento, y ADR-021 es el propio registro. `ESTADO.md` las lista, y el ROADMAP y el PLAN apuntan
  a él.

**Decidido (autor)**
* **D1, el acta en git:** compara el contenido del commit con el que dejaron las escrituras con recibo y lo
  dice («coincide» o «cambió fuera del canal»). El resultado esperado lo calcula la puerta que ya corre antes
  de cada escritura, sin hook `PostToolUse`. La puerta pasa a escribir en la base y, si no puede guardar,
  deniega.
* **D2, la historia:** se quita lo personal que fijó el autor, también de la historia, con una frase de
  `.claude/memory/autor.md`. Va en un repositorio nuevo, porque GitHub sirve los commits viejos por su hash.
* **D3:** el primer límite del README, justo debajo de la frase, es A30.
* **D4:** A33 y A34 no se cuentan a Anthropic. Son comportamiento documentado de Claude Code; el README los
  describe con su versión, como límites del kit.
* **D5:** `autoMemoryEnabled: false` en todo el proyecto, no solo para las revisiones ciegas, que ya no reciben
  ninguna de las dos memorias. Va en un contrato pequeño, después del instalador, con la corrección de la línea
  de `MEMORY.md` que dice que la opción (c) la deniega. La memoria bajo código se publica el 25.
* **D6:** el marco del README explica por qué las reglas viven fuera del modelo; la seguridad frente a un
  agente adversario es la v0.2.
* **D7:** las propuestas de V2–V9 y de §3–§5 del ROADMAP, aceptadas.
* El correo de los commits, la dirección *noreply* de GitHub, también en la configuración global de git.
* `git filter-repo` en una copia desechable antes de la pasada real (AGENTS 4.3: Python no commiteado).
* **ADR-021:** las decisiones del autor van en un registro que solo se amplía. Desde aquí, el DEVLOG las cita por
  su número.

**Salió mal y se aprendió**
* **El ensayo no reproducía el estado.** `cp -R` no conserva las fechas, así que `filter-repo` tomó por reciente
  la marca de la extracción del 5 de octubre y continuó aquella pasada sin preguntar. El mapa de las copias no
  era el de la pasada real: el primer script rehízo por error el hash de Traianus, y su comprobación no habría
  visto una cita sin mapa. Lo destapó la pregunta de la pasada real. El script se reforzó: cada hash se
  resuelve contra la copia de seguridad y se busca exacto en el mapa. Además, cada cita se comprobó por su
  asunto. Lección: un ensayo reproduce el estado que lee la herramienta, no solo la orden.
* **La orden que se dio al autor no avisaba de la pregunta de `filter-repo`,** y se contestó con una tecla de
  flecha. `filter-repo` toma como «no» todo lo que no es `y`, que aquí era lo correcto. Lección: antes de dar
  una orden interactiva, leer en el código de la herramienta qué pregunta y qué hace con cada respuesta.
* El borrador del ROADMAP salió de 211 líneas, no de una o dos páginas como se dijo.
* El resumen del cierre contó solo esta sesión; el autor recordó que el miércoles tuvo tres. `ESTADO.md`
  recoge el día entero.

**Siguiente**
* **El autor:** la CI en verde del repositorio nuevo; después, borrar `actuarii-antiguo` y, cuando esté
  conforme, la copia local de antes de reescribir. El push de este cierre.
* **Jueves 15 y viernes 16: el instalador en una orden (V2), en dos contratos.**
  * El primero lleva lo que el kit necesita en el destino: el perímetro, `includeGitInstructions`, el
    `denyWrite` y `pydantic`.
  * El segundo, las preguntas y el `commit-msg` con D1. Cambia la puerta, así que ordena sus ediciones según
    AGENTS 6.5. Tiene que buscar los tests que fijan que la puerta abre la base solo para leer.
* **Después del instalador:** el contrato de D5. El domingo 18, la medida en macOS (V4).
* **Lunes 19:** la tabla «Resumen» de `CASES.md` (V5).
* Disco: 14 GiB libres.

## 2026-10-14 (tarde)

Segunda sesión del miércoles, después de reiniciar Claude Code. El validador con el motivo y el perímetro nuevo ya
rigen; los tres contratos que se quedan en la v0.1 están implementados y verificados, y AGENTS.md pasa a la
v2.2.0. Después, una revisión de otro agente destapó un hueco en el sandbox y una fecha mal puesta; los dos
quedaron corregidos, y las sesiones pasan a cargar un estado corto. Suite: de 3166 a 3278 en verde. Dos pushes
del autor; la CI, en verde.

**Hecho**
* **Al arrancar:** el servidor MCP nuevo exige el motivo. Lo comprobó una sonda sobre
  `docs/probe-rationale.md`, que no existe. La base real se migró al primer uso y conserva sus 392 filas. El
  esquema de `validate_proposal` que muestra la sesión es una copia vieja, sin `Rationale`; el servidor acepta
  el campo igual.
* `main` avanzado sin merge hasta `8af0e14`, el final de la cadena del motivo y del perímetro.
* Las decisiones de hoy, anotadas en el PLAN (`7eea77a`).
* **A20** (`332e847`): el `pre-commit` solo se escribe dentro del `.git` propio del destino. Son conflicto, sin
  escribir nada: un `core.hooksPath` global o que sale del destino, un directorio de hooks del árbol de
  trabajo, un *worktree* enlazado y un `.git` que es un fichero. Verificado: T1–T5 y X1 rojos, T6 y X2 de
  guarda, suite 3177.
* **A31** (`a55b86b`; contrato `ef822eb` y su ampliación `51f7f8b`): la raíz entra en `sys.path` solo para
  `import tools` y sale enseguida. Vale para los nueve scripts: los tres hooks, `commit_integrity.py`, el
  validador, el instalador y los tres de auditoría. En los hooks va dentro del `try` que deniega. Verificado:
  T1–T4, X3 y X4 rojos, T5, X1 y X2 de guarda, suite 3233.
* **A34** (`03c7cf7`; contrato `f9daebd` y `f12825a`):
  * el revisor ciego lleva `omitClaudeMd: true`, y los ajustes, `includeGitInstructions: false`;
  * `build --lock` no pone el candado si falta alguno de los dos;
  * la skill separa lo que se cumple de lo que solo se declara.
  * Verificado: T1–T3, T5 y X1 rojos, T4 de guarda, suite 3278.
* **AGENTS.md v2.2.0** (`2a25a4c`):
  * 5.1 dice lo que cumple la revisión ciega;
  * 6.2 pierde su [enforced];
  * §9 declara lo que deja acta (A30), el arranque de las puertas (A19, A32), las herramientas de ficheros
    (A33), las credenciales (A35), los canales sin regla (A29), los enlaces (A26), lo que sigue recibiendo el
    revisor (A34), y A21, A23, A24, A25 (en «Forged logs») y A28.
* **Primer push del autor** (`b40adf1`). La CI en Linux, en verde en 1 min 17 s.
* **Una revisión de otro agente**, que pegó el autor. Lo principal:
  * el acta registra que se pidió escribir, no que se escribió. No hay hook después de la escritura, la base
    es local, git la ignora, `Bash` puede tocar sus ficheros `-wal` y `-shm`, y no se enlaza con ningún
    commit;
  * el coste: el matcher `*` lanza dos procesos de Python en cada llamada a cualquier herramienta, también en
    `Read` y `Grep`; y A30 es un argumento contra el diseño, no un límite más;
  * el hueco de `.claude/memory/` y la fecha mal puesta, comprobados los dos con una sonda y con `git log`.
* **Fechas corregidas** en esta entrada y en el PLAN (`87a656a`).
* **`docs/ESTADO.md`** (`4c9be7a`): un estado corto que `CLAUDE.md` y `opencode.jsonc` cargan en lugar del
  PLAN, que pasa a ser documento de consulta.
* **El hueco de `.claude/memory/`** (contrato `015d5db`, implementación `92df87a`):
  * cada ruta gobernada tiene su `denyWrite`, sin eximir `.claude/**` ni `.mcp.json`, aquí y en el
    instalador;
  * el test comprueba la regla de AGENTS 7.3 en vez de fijar la exención.
  * Verificado: T1, T2 y X1 rojos, T3 de guarda, suite 3278. Falta la sonda en una sesión con los ajustes
    nuevos.
* **Segundo push del autor** (`92df87a`).

**Decidido (autor)**
* Se quedan A20, A31 y A34. A19, A32, la opción (c) con A33 y A35 pasan a la v0.2, declarados.
* La 2b se cierra sin el caso (b); para el informe queda la tabla «Resumen» de `CASES.md`.
* A21, A23, A24, A25 y A28 se declaran en §9, sin contrato.
* El push, sí. Lo lanza el autor, porque el sandbox no deja salir a la red a `Bash`.
* **El acta en git:** sí, solo registrando. Un hook `commit-msg` añade a cada commit los motivos de los recibos
  de sus ficheros gobernados. Entra en los contratos del instalador, y es la única función nueva antes del
  lanzamiento.
* Los campos de la propuesta se renombran con nombres llanos en la v0.2.
* `CLAUDE.md` carga un estado corto en vez del PLAN.
* **Una hoja de ruta** (`docs/ROADMAP.md`) con los criterios de la v0.1 y de la v0.2. Claude la redacta, el
  autor la corrige, y se commitea antes de los contratos del instalador. Sirve para cortar el alcance y para
  que la revisión del 22 de noviembre se haga contra algo escrito antes.

**Salió mal y se aprendió**
* **A31 se paró a medias.** Dos tests fijaban las importaciones de los scripts y el contrato no los listaba:
  es la segunda vez en dos días que falla AGENTS 6.4. Lección: además de los tests que construyen un formato y
  de los que fijan un comportamiento, hay que buscar los que leen el código como texto (las importaciones, el
  patrón de una cabecera). Antes de A34 se buscó así, y apareció `test_root_off_sys_path.py` (D13).
* **La ampliación de A31 se commiteó después del resultado, no antes.** La copia de trabajo tenía el trabajo
  del implementador a medias, y la suite no pasaba. Es una desviación de AGENTS 8.6, anotada aquí.
* **Al retomar la conversación, el esquema de la herramienta que ve la sesión es una copia vieja.** La sonda
  lo resolvió, y los contratos lo avisan: D10 de A20, D8 de A31 y D12 de A34.
* **Un selector `paragraph` de `context_pack` no encuentra un elemento de lista que no abre bloque.** Se usó
  un rango de líneas.
* **El candado de A34 lee la cabecera del revisor línea a línea, no como YAML.** Lo encontró su
  implementador, y queda declarado en §9.
* **Esta entrada y el PLAN salieron fechados el 2026-10-15, jueves, y era miércoles 14.** Se tomó el día del
  mensaje del autor («estamos a jueves») sin mirar el reloj, aunque el sistema daba el 14. Lo vio la revisión
  de otro agente; se corrigió aquí y en el PLAN. Los contratos de A20 (D9), A31 (D11) y A34 (D11) dicen
  2026-10-15 para decisiones del 14: se dejan como se lanzaron. Lección: la fecha de un registro sale del reloj,
  no de la conversación.
* **El hueco de `.claude/memory/` venía de un test que fijaba lo que creíamos que protege Claude Code**, en vez
  de comprobarlo. El 12 se dio por hecho que su sandbox protege todo `.claude/`, y solo protege una parte.
  Lección: lo que hace un tercero se comprueba con una sonda, no se fija en un test.
* **La frase del README volvió a prometer más que el kit:** «every action leaves a record that it happened»,
  cuando el acta registra la petición y no la escritura. Se corrige con el acta en git.

**Siguiente**
* **La sonda pendiente:** en una sesión con los ajustes nuevos, abrir `.claude/memory/MEMORY.md` para escribir
  desde `Bash` tiene que salir denegado (D6 del contrato).
* **El ROADMAP** (`docs/ROADMAP.md`). Lo redacta Claude y lo corrige el autor antes de commitearlo. Contiene:
  * los criterios de la v0.1, cada uno con su forma de comprobarlo y con lo que pasa si no se cumple el 25;
  * la ventana de señal y cómo se cuenta;
  * la puerta del 22 de noviembre;
  * la v0.2 con sus criterios: E1–E9, los casos A como batería de pruebas, el coste por debajo de 1 s, y
    Claude Code y OpenCode.
* **Jueves 15 y viernes 16: el instalador en una orden, con el acta en git.**
  * Sin A35.
  * Lleva a los destinos el perímetro nuevo, el motivo, `includeGitInstructions` (sin él, `build --lock` no
    pone el candado en un destino, D5 de A34) y el hook `commit-msg`.
  * Reescribe `INSTALL.md`, con el entorno fuera del repositorio.
  * Después, la nueva medida en macOS.
* La tabla «Resumen» de `CASES.md` hasta A35, con lo corregido y lo declarado, para el lunes 19.
* El README, desde el viernes.
* `docs/design/SANDBOX.md` §6 e `INSTALL.md` todavía describen la exención de `.claude/**`.
* `examples/traianus/skills/instrument-audit/SKILL.md` sigue diciendo «Blind by construction».
* Sin la opción (c), la memoria normal de Claude Code sigue abierta; falta decidir cómo se evita o se declara.
* Disco: 15 GiB libres.

## 2026-10-14

Una sesión, abierta la noche del 13 después de la entrada de ese día y seguida el 14. Empezó con una revisión
sincera del proyecto y acabó con dos contratos implementados y verificados, encadenados en la rama
`v01/perimetro`, todavía fuera de `main`. Suite: de 3080 a 3166 en verde.

**Hecho**
* **Revisión del proyecto,** en el chat y sin documento. Lo principal:
  * el recibo no decide nada que no decida ya el hook: la cita es el `old_string`, que `Edit` ya exige, y
    `Intent_Class` y `Safety_Abort` los declara el propio agente;
  * la tesis de la v0.1 prometía más de lo que hay: A20, A21, A23, A24 y A31 son fallos de implementación del
    kit, no caminos alrededor de una regla;
  * falta la literatura: las «tres cosas a la vez» del PLAN son la *lethal trifecta* de Simon Willison, y ni
    CaMeL, ni el patrón dual LLM, ni los entornos aislados que ya existen están en `PRIOR_ART.md`;
  * el proceso se come al producto: ningún cambio de código del kit del 9 al 13, y el README sin empezar;
  * antes de hacer público el repositorio, `docs/PLAN.md` cuenta en la historia la situación personal del
    autor, y A33 y A34 tocan comportamiento de Claude Code que convendría contar antes a Anthropic.
* **El objetivo de la v0.1, reescrito** en `docs/PLAN.md` (`6fccf88`): actas de trabajo para agentes de código.
* **Contrato del motivo** (`docs/design/MOTIVO.contrato.json`, `6fccf88`) e implementación (`a635ec0`, `sonnet`):
  * `Rationale` obligatorio en la propuesta (de 1 a 1000 caracteres, no solo espacios), guardado en
    `audit_log` con cada decisión, también las denegadas;
  * las bases de auditoría viejas se migran al primer uso, sin perder filas;
  * ningún `EXECUTE_SAFE` sin su acta: el acta y el recibo van en una transacción y, si falla,
    `ABORTED_NOT_RECORDED`, sin recibo;
  * un fallo al escribir el rastro ya no se silencia: deja una línea en stderr, sin ruta;
  * «5 Radicals» pasa a «the proposal schema» en AGENTS 2.2, las skills, el implementador y la descripción de
    la herramienta.
  * Verificado por el chat con `verify_red_green.py`: T1–T7 y X1–X2 rojos en la base, T8 de guarda, suite 3150.
    El alcance (los 23 ficheros del contrato), comprobado a mano.
* **Medida de los permisos** en la transcripción de ese implementador: 52 `Bash`, 51 `validate_proposal` y 60
  `Edit` o `Write`; 161 llamadas caían en «preguntar». Con el perímetro nuevo, 70 (10 de ellas `Bash`); con
  `acceptEdits`, 10.
* **Contrato del perímetro** (`docs/design/PERIMETRO.contrato.json`, `12cc5a1` y `2934c1a`) e implementación
  (`f5517ae`):
  * sin preguntar en los dos entornos: `pytest`, `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `df`, `echo`,
    `sed -n`, `sort`, `uniq`, `diff` y `validate_proposal`;
  * una lista cerrada, con su test; el resto de `Bash` sigue preguntando;
  * en OpenCode, el validador va con el nombre `boundary-validator_validate_proposal`, sin comprobar ejecutando
    OpenCode;
  * AGENTS 7.1, reescrito.
  * Verificado por el chat: T1, T2 y T4 rojos, T3 y T5 de guarda, suite 3166.
* **AGENTS §9** (`f9f951d`): `sort`, `uniq` y `sed -n` escriben o ejecutan con sus opciones (en GNU `sed`, `e`
  ejecuta una orden), sin preguntar; el sandbox las contiene. Lo vio el implementador del perímetro.

**Decidido (autor)**
* La seguridad frente a un agente adversario no es de esta versión. El objetivo anterior («demostrar que hace
  falta un middleware») pasa a ser la motivación de la v0.2.
* La frase de la v0.1: «Actas de trabajo para agentes de código. Cada actuación deja constancia de que se hizo
  y de por qué. Para entornos donde la trazabilidad es lo primero.» En inglés: «Work records for coding agents.
  Every action leaves a record that it happened, and why. Built for settings where traceability comes first.»
* El motivo, obligatorio; sin acta no hay recibo; «the proposal schema» en vez de «5 Radicals»; el contrato se
  lanza en su rama, dentro de la ventana de la 2b, y `main` se avanza el jueves.
* Quitar los permisos que no deciden nada; la lista, ampliada con `echo`, `sed -n`, `sort`, `uniq` y `diff`; el
  contrato, encadenado al del motivo.
* Declarar en §9 lo de `sed` y `sort` en vez de quitarlas de la lista.

**Sin decidir**
* Qué contratos de seguridad se quedan. Propuesta: se quedan A20, A31 (recortando el contrato de A19 a lo de
  `sys.path`) y A34; A19, A32, la opción (c) con A33 y A35 pasan a la v0.2, declarados. La memoria bajo código
  contaba con que (c) denegara la memoria normal.
* La auditoría con `/code-review ultra`. Recomendación: no hacerla ahora; si se hace, sobre la rama del
  instalador en una orden, que es lo que toca el repositorio de otra persona.
* El primer límite del README, justo debajo de la frase: solo deja acta lo que pasa por el canal gobernado
  (A30).
* El párrafo «Marco» del README en el PLAN (von Neumann, inyección) sigue en clave de seguridad.
* Antes de hacer público: la información personal de `docs/PLAN.md` en la historia, las ramas de Traianus, y
  contar A33 y A34 a Anthropic.

**Salió mal y se aprendió**
* **El contrato del motivo no listó un segundo test que fijaba el fail-open** (`test_content_receipt.py`). El
  implementador lo cambió según D5 y lo dijo. Lección (AGENTS 6.4): buscar también los tests que fijan el
  comportamiento que el contrato quita, no solo los que construyen el formato.
* **El contrato del perímetro casi se lanza sin decir que el servidor de la sesión no acepta el motivo.** Se
  añadió D12 (`2934c1a`). Lección: al encadenar contratos, la sesión sigue con el servidor y los ajustes con que
  arrancó, y el contrato siguiente tiene que decirlo.
* **El primer mensaje de commit del perímetro pasaba de 100 caracteres;** lo paró `delegation_contract.py`.
* **El primer recuento de permisos partía los `grep` con `\|` entre comillas.** Se rehízo quitando antes lo
  entrecomillado.
* **En T4, T5 y T6 del motivo, la base falla primero por otra razón:** allí una propuesta con motivo ya es
  `INVALID_JSON`. El implementador comprobó la razón declarada con una copia de la base, fuera del verificador.
  Es el límite «Red for the stated reason» de §9.
* **Una lista «de solo lectura» se comprueba opción por opción** (`sort -o`, `uniq` con fichero de salida,
  `sed` con `w` o `e`). Lo vio el implementador, no el contrato.
* Restos fuera del repositorio: `$TMPDIR/basecopy` y `$TMPDIR/probe`, del implementador del motivo (`rm`
  denegado).

**Siguiente**
* **Abrir una sesión nueva:** la copia de trabajo ya tiene los dos cambios, así que arranca con el validador que
  exige el motivo y con el perímetro nuevo, y migra `.data/` en la primera validación. Medir otra vez la ida y
  vuelta del validador (la hipótesis de `COSTE.md` §4) y los permisos de una tarea delegada.
* **Jueves 15:** avanzar `main` hasta el final de `v01/perimetro` (`git branch -f main v01/perimetro` y
  `git switch main`), si `main` no se ha movido.
* Decidir la tabla de contratos de seguridad y, con ella, recortar el contrato de A19.
* Lo que quedaba de la 2b para el miércoles: el caso (b), los menores, la tabla «Resumen» de `CASES.md` hasta
  A35 y limpiar `~/Documents/noticias-2b`.
* El instalador en una orden tiene que llevar a los destinos el perímetro nuevo y el validador con el motivo.
* `docs/` y `examples/` siguen hablando de cinco radicales (`PROCESO.md`, `ENTORNO_PROPIO.md`, `PRIOR_ART.md`,
  `RECIBO_CONTENIDO.md` y el `engine-implementer` de Traianus).
* El README, esta semana.
* Disco: 5,5 GiB libres.

## 2026-10-13

Una sesión larga, primer día de la ventana de la 2b. Empezó como puesta al día y acabó en cuatro contratos
listos, cinco casos nuevos (A31–A35) y el diseño del entorno propio para la v0.2. Sin cambios de código del
kit: documentos, contratos, configuración (`CLAUDE.md`, `opencode.jsonc`) y la memoria nueva. Suite: 3080 en
verde en cada commit. Sin push.

**Hecho**
* Puesta al día y línea base: `main` en `6715a83`, 3080 en verde.
* **Decisión de A19 rehecha** (`7b04cee`, corregida en `81d64b1`; `docs/design/ARRANQUE_PUERTAS.md`):
  * `-I` no impide A19: en el `site.py` de 3.11.6, `sitecustomize` se ejecuta también con `-I`. Solo `-S`
    lo evita.
  * Las puertas pasan a arrancar con un lanzador llamado con `/bin/sh` por ruta absoluta, que quita del
    `PATH` los directorios del repositorio, y con `-I -S`.
  * La raíz entra en `sys.path` solo para `import tools`.
  * El validador va con `-I` y una guarda de configuración.
* **A31** (C1): las puertas ponen la raíz delante de la biblioteca estándar; un `dataclasses.py` en la raíz
  se ejecuta en cada hook, en el validador y en el `pre-commit` de la persona. Reproducido a nivel de hook
  en un clon del scratchpad, con aprobación del autor porque salta el shim.
* **A32** (C1): con el `.venv` del repositorio activado, el `python3`, el `sh` y el `git` de las puertas se
  buscan en `.venv/bin`, que `Bash` escribe dentro del sandbox (probado). Ni `-I` ni `-S` sirven.
  Reproducido igual que A31.
* **A33** (C1, `d6af9e3`): `Write` escribe `.git/hooks/pre-commit`, `.git/config` y `.vscode/tasks.json` sin
  recibo; el sandbox se los impide a `Bash`. Probado con cargas al hook y sondas que no escriben nada.
* **A34** (C1, `06e51e6`, `c6b58aa`): la revisión ciega no es ciega por construcción.
  * Las 6 transcripciones del auditor de Traianus contienen `CLAUDE.md`, `AGENTS.md` y el índice de la
    memoria automática, con resultados previos.
  * La documentación de Claude Code confirma qué recibe un subagente: `CLAUDE.md`, la instantánea de git y
    el mensaje de encargo. `omitClaudeMd` e `includeGitInstructions` quitan los dos primeros.
* **A35** (C2, `60d93b0`): `Bash` abre `~/.ssh` y `~/.config/gh` dentro del sandbox. Comprobado con
  `test -r`, sin leer nada.
* **Principios de diseño** en `docs/PLAN.md` (`da0a58a`): el agente aislado; toda salida pasa por una regla;
  lo que corre fuera no se fía de lo que el agente escribe.
* **Cuatro contratos validados en código, con su paquete de contexto servido; ninguno lanzado:**
  * A19, A31 y A32 (`e6b9df4`);
  * A20 (`ad5b3c9`): el `pre-commit` solo dentro del `.git` del destino;
  * la opción (c) con A33 (`ad5b3c9`): las herramientas de ficheros con el alcance de `Bash`;
  * A34 en su parte de la v0.1 (`f5ccfa0`).
* **Memoria bajo código** (`e0299ef`): tres recuerdos y su índice en `.claude/memory/`, cada uno con su
  recibo, cargados por `CLAUDE.md` y `opencode.jsonc`.
* **Documentación de Claude Code** leída con el navegador integrado: memoria, subagentes, ajustes, referencia
  de ajustes, sandbox y entornos aislados.
* **Diseño del entorno aislado propio para la v0.2** (`f6bf3d6`, `docs/design/ENTORNO_PROPIO.md`):
  * el agente entero en un entorno;
  * un intermediario MCP fuera que valida y escribe;
  * revisión ciega y delegación en entornos aparte;
  * adaptadores finos;
  * los casos de las auditorías como batería de prueba.

**Decidido (autor)**
* La decisión revisada de A19 sustituye a la del 12, aceptada con una condición: los tests nuevos tienen
  que salir rojos en la base y verdes al final.
* A31, A32, A33, A34 y A35 entran en la 2b.
* **Opción (c):**
  * las herramientas de ficheros no escriben fuera de la raíz salvo `writable_outside_root`, y nunca `.git`,
    `.vscode` ni `.idea`;
  * Actuarii permite el scratchpad y `~/.claude/plans/**`;
  * el instalador permite el scratchpad y la memoria normal del destino.
* **El entorno de Actuarii, fuera del repositorio:** `INSTALL.md` deja una sola opción, y
  `ACTUARII_PYTHON` permite trabajar con el entorno del proyecto activado.
* **El instalador se niega con un `core.hooksPath` en el árbol** (`.husky`): esos proyectos integran el
  hook a mano.
* **La memoria del agente es obligatoria:**
  * en Actuarii, bajo código y desde ya;
  * en los destinos, la normal, permitida;
  * es el corpus del piloto de la fase 4, y antes del lanzamiento no se toca Traianus.
* **Revisión ciega:**
  * el revisor no tiene memoria, y las reglas de auditoría van en el paquete;
  * en la v0.1: `omitClaudeMd`, `includeGitInstructions: false` y el candado que lo exige;
  * en la v0.2: el mensaje de encargo comprobado por código, el veredicto validado y un proceso aparte.
* **Credenciales:** `denyRead` del sandbox y reglas `Read(...)` de denegación, en el contrato del
  instalador, con la diferencia con OpenCode declarada en AGENTS 7.1.
* **El entorno aislado propio, independiente del proveedor, va en la v0.2.** La v0.1 sale el 25 sin más
  parches de Claude Code que los contratos ya escritos. El README cuenta que su frontera es prestada y por
  dónde se escapa.
* **Orden de lanzamiento:** A19 → A20 → (c) → A34, desde el jueves. Las pautas no dejan corregir durante la
  auditoría.
* **Ya escrita esta entrada:**
  * El objetivo de la v0.1 es demostrar que hace falta un middleware para usar agentes de forma segura. La
    prueba es la 2b; la forma, el monitor de referencia de `ENTORNO_PROPIO.md`.
  * El entorno de internet va separado del de código, con su propia regla de salida, porque pedir una URL ya
    es emitir datos. Triarii, el proyecto de la hackathon de mayo, queda como antecedente: capacidades por
    efecto físico, punycode y credenciales en un proxy (`b8295a6`).

**Salió mal y se aprendió**
* **La decisión del 12 ponía `-I` en los hooks**, aunque el DEVLOG del 10 ya decía que `-I` no impide A19.
  Lección: comprobar la semántica de una opción en el código fuente antes de decidir con ella.
* **El primer diseño ponía la raíz al final de `sys.path` (`7b04cee`).** Al preparar el contrato apareció
  en el `site-packages` de pyenv un paquete `tools` ajeno (`deepcode_hku`) que habría tapado el kit en el
  validador de esta misma sesión. Se corrigió antes del contrato (`81d64b1`). Lección: mirar el intérprete
  real antes de fijar un orden de importación.
* **El mismo diseño quitaba del `PATH` los directorios temporales.** Eso dejaría fuera los `tmp_path` de
  pytest en Linux. Se declaró en su lugar.
* **`81d64b1` se commiteó antes de pasar la suite;** se pasó después y salió en verde. Es la regla de siempre
  y se volvió a saltar.
* **Se propuso `blockReadsOutsideWorkingDirectories` para las credenciales y el autor lo aprobó.** La sección
  enlazada de la documentación decía que, con el sandbox, también quita a `Bash` la lectura de `~/.pyenv`.
  Se retiró antes de redactarlo. Lección: leer las secciones enlazadas de un ajuste antes de proponerlo.
* **La primera propuesta para (c) dejaba a Claude sin memoria en Actuarii.** El autor la rechazó: sin
  memoria no vale. De ahí salió la memoria bajo código.
* **El índice de la memoria nombraba Traianus;** el test de la fase 1 que mantiene genérico el kit lo
  rechazó, y se corrigió el texto, no el test.
* **Dos garantías marcadas **[enforced]** prometen más de lo que hacen:** 5.1 (A34) y 6.2 (A28). La de la
  revisión ciega solo se descubrió al preguntar por su memoria. Lección: lo que un agente «ve» se comprueba
  contra lo que el harness le inyecta, no solo contra las herramientas que puede llamar.
* **Roces con las propias puertas:** el hook de `Bash` denegó con razón una ruta que contenía `python3.11` y
  `ls .venv/bin/python3` (el falso positivo ya conocido), y una expresión regular que no podía tokenizar. Un
  bucle de zsh no partió una lista, y `ls` leyó como opción un directorio que empezaba por `-`.

**Siguiente**
* **Miércoles 14, lo que queda de la 2b:**
  * el caso (b), la copia redirigida en vivo, que prepara el autor;
  * los menores;
  * la tabla «Resumen» de `CASES.md` hasta A35;
  * limpiar `~/Documents/noticias-2b`.
* **Desde el jueves 15, los contratos en orden,** con la base renovada y validados otra vez en el momento de
  lanzarlos. Pasos de la persona después de A19:
  * abrir una sesión nueva (o reconectar el MCP);
  * volver a copiar `.git/hooks/pre-commit`;
  * actualizar `noticias-2b` a mano.
* **El cambio único de `AGENTS.md`:**
  * 1.1: con la configuración inválida, también se deniega fuera de la raíz;
  * la regla nueva de las herramientas de ficheros (opción (c) y A33);
  * 5.1 (A34) y 6.2 (A28);
  * 7.1 y 7.3: las credenciales (A35);
  * en §9:
    * los enlaces en rutas gobernadas (A26);
    * los canales fuera del sandbox (A29);
    * rutas, no tareas (A30);
    * la terminal de la persona y su `PATH` (A32);
    * los temporales en el `PATH`;
    * `.python-version`;
    * las herramientas de clase 3 fuera de la raíz;
    * en la revisión ciega: el mensaje de encargo, el `CLAUDE.md` de la organización y las versiones
      anteriores a la 2.1.271.
* **Los dos contratos del instalador en una orden:**
  * las credenciales;
  * `ACTUARII_PYTHON` y la comprobación de `pydantic` con `-I`;
  * reescribir `INSTALL.md` (el entorno fuera, la memoria).

  Después, la nueva medida en macOS.
* **Sin contrato todavía, para decidir si se corrigen o se declaran:** A21, A23, A24, A25 y A28.
* **El informe de la 2b en inglés,** el lunes 19.
* **Disco:** quedan 4,0 GiB, y el verificador crea *worktrees* temporales.
* **El push de los commits de hoy.**

## 2026-10-12 (tarde)

Sesión de tarde: la auditoría 2b reducida. Doce casos nuevos (A19–A30) en `CASES.md`, sección «2b
(2026-10-13)». Sin cambios de código; todo en `docs/`.

**Hecho**
* **Caso (a), A19 (C1), confirmado en vivo** (`bfb329a`): código en el arranque del intérprete. Con el
  `.venv` dentro del repo, un `sitecustomize.py` testigo plantado en su `site-packages` se ejecutó en
  11 procesos (hooks y servidor MCP) fuera del sandbox, en una sesión abierta desde el `.venv` activado
  sobre `noticias-2b`. El validador no puede usar `-S` porque necesita `pydantic`: la carga se ejecuta
  siempre. El montaje que recomienda `INSTALL.md` es el vulnerable.
* **Casos en el scratchpad**, con `trap`/respaldos, sin tocar nada real:
  * A20 (c, C1, `23341a1`): el instalador escribe el `pre-commit` fuera del destino con un
    `core.hooksPath` global absoluto; rompe I1 y puede bloquear los commits de los demás repos.
  * A21 (l, C3, `4d5c4d7`): A18 reabierto; un `params`/`arguments` no-dict no vacío tumba el servidor MCP.
  * A22 (k, OK, `4d5c4d7`): integridad del commit; media preparación, modo y grafía rechazados.
  * A23 (i, C2, `4d5c4d7`): `Glob` con llaves esquiva el análisis estático del confinamiento de la
    revisión ciega; el hook permitió `{..,x}/**` con `path` dentro del paquete.
  * A24 (d, C2, `ce8ba37`): el anuncio afirma «Bash cannot write the governed paths» sin comprobar
    `denyWrite`; en Actuarii acierta por el harness, miente para una ruta propia sin su `denyWrite`.
  * A25 (e, C2, `ce8ba37`): `.data/` escribible por `Bash`; solo el fichero `.db` está en `denyWrite`.
  * A26 (g, límite, `ce8ba37`): una ruta gobernada que es enlace simbólico se gobierna por el destino;
    no alcanzable por el agente y el `pre-commit` rechaza enlaces en rutas gobernadas.
  * A27 (h, OK, `9a831da`): el sandbox bloquea crear un enlace duro a un fichero gobernado.
  * A28 (j, C2, `9a831da`): nada obliga a correr `verify_red_green.py` (6.2 se sobreafirma) y el
    verificador no compara el diff con `files_may_touch`/`files_must_not_touch`.
  * A29 (m, límite, `331f468`): inventario documental de los canales a la web/host fuera del sandbox
    (navegador, Chrome, conectores que envían, artifacts, host, programadores).
  * A30 (n, límite, `331f468`): el desplazamiento del trabajo a rutas no gobernadas, con la evidencia de
    la prueba en limpio.

**Decidido**
* La clasificación de cada caso es propuesta; la cierra el autor. De prioridad 1, (a) y (c) salieron C1,
  como se temía; no queda ningún C1 nuevo inesperado fuera de ellos.
* **Arreglo de A19 y A20 por contrato:** se empezó a preparar al cierre y se pasa a otra sesión. Decisión
  del autor sobre la parte del MCP de A19: **venv fuera del repositorio, impuesto** — los hooks llevan
  `-I` (seguro: los tres que importan `tools.*` insertan `REPO_ROOT`, los otros tres son solo-stdlib, y
  el shim acepta `-I`); el validador rehúsa arrancar si su `site-packages` está dentro de la raíz del
  repo; INSTALL.md hace del venv fuera el predeterminado. (`pydantic_core` es compilado y no se puede
  vendorizar: la vía «solo stdlib» queda para la v0.2.) A20: el instalador resuelve el destino del hook
  y, si cae fuera del target, lo registra como conflicto sin escribir nada, y avisa del `core.hooksPath`.
  Pendiente para la próxima sesión: enumerar los tests que fijan las cadenas de comando de los hooks
  (6.4) antes de redactar el contrato de A19.

**Salió mal y se aprendió**
* El primer testigo de (a) se corrompió: `printf` interpretó los `%` del `sitecustomize.py`. La primera
  ejecución en vivo no valía. Se rehízo con un heredoc entrecomillado. Lección: no construir Python con
  `printf`.
* La primera sesión de (a) no arrancó desde el `.venv` activado, así que el testigo no disparó; el
  intérprete de los hooks no era el del `.venv`. Hay que abrir `claude` desde la terminal con el `.venv`
  activado (`which python3` → el del `.venv`).
* El test de (g) usó al principio `ln -s AGENTS.md`, un enlace **relativo** a `docs/AGENTS.md` (que no
  existe); se rehízo con `../AGENTS.md`.
* Los gates se aplican también al auditor: `deny_python_escapes` (R1/R2) bloqueó varias veces el `Bash`
  de esta sesión (`.venv/bin/python3` por ruta, un `python3 -c` sobrante). El `rm` suelto lo deniega la
  política (7.1); la limpieza se hizo con `trap` dentro de comandos aprobados.
* El test de (A23) necesita poner el lock de la revisión real; se creó y borró dentro de un solo comando
  con `trap` para no confinar la propia sesión. Quedó un instante tras el comando; se borró enseguida y
  se comprobó `.data/` limpio. Riesgo a recordar: un `review_lock.json` colgado confina los `Read`.
* Dos matices que afinan los hallazgos informales: en (d) el harness sí protege `.claude/**` y
  `.mcp.json` (el problema es el anuncio no verificando, que muerde a rutas propias del adoptante); en
  (g) el `pre-commit` no «decide por el destino», sino que **rechaza** el enlace.

**Siguiente**
* **(b)** la copia redirigida, en vivo (lo prepara el autor: clon `noticias-2b` restaurado, tres
  ejecuciones desde el mismo commit). Es el único de prioridad 1 que falta.
* Los **menores** (§3 de las pautas) agrupados como limpieza/falsos positivos, y la tabla **Resumen** de
  `CASES.md`, que sigue acabando en A12, por extender a A13–A30.
* El **informe en inglés** (lunes 19, según la enmienda de las pautas).
* Limpiar `~/Documents/noticias-2b` del caso (a): el `sitecustomize.py` del `.venv` y `~/caseA_witness.log`.

## 2026-10-12 (mañana)

Sesión de mañana; por la tarde sigue otra. Suite: 3080 en verde, sin cambios de código. Se cerró la
prueba en limpio en macOS y quedaron aprobadas las pautas de la 2b reducida.

**Hecho**
* Entradas del 9 y del 10 de este DEVLOG, reconstruidas de las transcripciones (`8a99dc6`). Los
  hallazgos de la auditoría informal del 10, que solo estaban fuera del repositorio, entran en él. Push;
  la CI pasa en verde con el commit del kit instalado con su hook (`3c9faf7`).
* Segundo ensayo de la prueba en limpio, sin cifra (`32a4cb0`). Empezó como medida y pasó a ensayo
  cuando el autor pidió ayuda con el argumento del instalador. Primera aplicación del método del hito 1
  por el registro (§4c): se cumple. `INSTALL.md` corregido: el argumento es el repositorio de destino, y
  las rutas de los ejemplos hay que sustituirlas.
* **Medida en macOS** (`70f7508`): los dos hitos se cumplen; 612,8 s en total, de los que el agente tarda
  35 s; pasa de los 300 s. Sin cronómetro: los tiempos salen del reflog, de las fechas de los ficheros y
  de la transcripción.
* **Caso real** (`1c20d18`): el agente escribió los 16 tests en `tests/unit/`, fuera de las rutas
  gobernadas, «para no pedir el recibo». El shim denegó un `python3 -c` y el agente siguió sin él. El
  cambio de configuración, que se pidió al agente en vez de hacerlo a mano, pasó por el canal gobernado
  y dejó dos recibos `SPEC`.
* Pautas de la 2b reducida, aprobadas y commiteadas antes de empezar (`5c4b107`): G14–G17, las promesas
  del instalador I1–I4 y 14 casos por riesgo. Entre ellos, la copia redirigida, con el módulo, el texto
  y las tres ejecuciones fijados antes.
* Instalación en una orden, decidida y apuntada en `docs/PLAN.md` (`3394a63`).

**Decidido (autor)**
* La medida del intento 3 vale, con los tiempos del registro en lugar del cronómetro.
* Primero se aceptó la cifra sin optimizar (opción a). Revisado el mismo día: la instalación pasa a ser
  una orden antes del lanzamiento, después de la 2b, y se vuelve a medir. Pregunta solo las rutas extra,
  con su `denyWrite`, y pregunta antes de commitear. Comprueba `pydantic==2.13.3` y pide permiso antes
  de instalarlo. El informe de la 2b pasa al lunes 19.
* «El kit gobierna rutas, no tareas» es un límite no declarado. Se declara en la v0.1 (`AGENTS.md` §9 y
  README), sin una skill, porque sería gobernar por instrucción. El anuncio se corrige en la 2b para que
  nombre las rutas gobernadas sin `denyWrite`. El mapa de gobierno va a la v0.2.
* La comparación de configuraciones (`COSTE.md` §6) va a la v0.2.
* Las cinco decisiones previas de la 2b, tal como las proponían las pautas: martes y miércoles; el caso
  (a) en vivo con un `.venv` que crea el autor; el caso (b) como está; el caso (m) documental; y el
  informe en inglés.

**Salió mal y se aprendió**
* El recap de la mañana no vio la sesión del 10 ni que la medida del 9 se había parado tras el clon:
  salió de `git log` y del DEVLOG. Lección: antes de un recap, leer las transcripciones de las sesiones
  posteriores a la última entrada.
* Las rutas de ejemplo de `INSTALL.md` (`~/src/actuarii`, `~/src/your-repo`) se tomaron tal cual, y el
  clon y el destino se confundieron en el argumento.
* En la medida se repitió el paso 1 de la guía: Actuarii se clonó otra vez, desde GitHub y dentro del
  destino, aunque la guía dice «never inside it». El protocolo da el clon por hecho y la guía empieza
  por él; los dos documentos no casan.
* Desviaciones del protocolo: la medida, sin cronómetro; el ensayo 2, con el texto «crea AGENTS.md» y
  no el fijo; la preparación del caso real, pedida al agente y no hecha a mano. Todas quedan anotadas en
  §5. Los tiempos del registro resultaron más precisos por paso que un cronómetro.
* El chat sospechó que el `denyWrite` del instalador dejaba fuera `.claude/**` y `.mcp.json`. Antes de
  anotarlo, leyó el test que fija esa exclusión como diseño: esas rutas las protege el propio sandbox.
* El caso real enseñó algo que las pruebas a nivel de hook no ven: el coste del recibo desplaza la
  escritura del agente. La 2b lo prueba con la copia redirigida.

**Siguiente**
* Esta tarde, o mañana como fijan las pautas: la 2b, empezando por el caso (a). El autor prepara
  `~/Documents/noticias-2b` con el kit instalado y un `.venv` dentro.
* Jueves 15 y viernes 16: correcciones C1, declaraciones de §9 en un solo cambio de `AGENTS.md`, los dos
  contratos del instalador en una orden y la nueva medida, con su enmienda del protocolo antes.
* Pendiente del autor: qué hacer con las ramas heredadas de
  Traianus antes de hacer público el repositorio.

## 2026-10-10

Una sesión, sin cambios en el repositorio. Entrada reconstruida el 12 a partir de la transcripción y del
resumen que dejó la sesión fuera del repositorio
(`~/.claude/plans/haz-una-auditor-a-del-serialized-stream.md`).

**Hecho**
* Auditoría informal de solo lectura sobre `main` en `1b4c084`, pedida por el autor para gastar los
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
  `fase2/shim-ficheros` (`3c9faf7`):
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
* `INSTALL.md` (`0f3118a`): dónde clonar, rutas explícitas, el primer commit del kit instalado en la
  terminal antes de abrir Claude Code (dentro de la sesión, el shim rechaza `commit_integrity.py`
  hasta que está en `HEAD`), un entorno sin `.venv` y cómo leer `pip check`.
* Hito 1 de la prueba en limpio reformulado antes de medir (`1b4c084`; `PRUEBA_EN_LIMPIO.md` §4c):
  se comprueba por el registro del kit (la transcripción, la tabla `receipts` por hash y el
  `git diff` del destino), no por la conducta del agente. En §5, qué roces del ensayo quedan corregidos
  y dónde.
* Idea para la v0.2 en `docs/PLAN.md` (`1b4c084`): las operaciones sobre rutas gobernadas sin canal
  gobernado.
* Medida en macOS preparada: copia del ensayo borrada, clon de Actuarii en `~/Documents/actuarii-medida`
  (`1b4c084`) y clon de `noticias` en `~/Documents/noticias-medida` (`v3-exp`, `1676538`). El clon de
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
* El commit `1b4c084`, que solo toca documentos, se hizo con `test_ci_workflow.py` en verde (el único
  test que los lee) y no con la suite entera. La suite había pasado en `0f3118a`.
* Los tres commits del día no se subieron: `main` quedó 3 por delante de `origin`, y la CI no ha
  ejecutado todavía el test del commit con el hook.

**Siguiente**
* `git push`, para que la CI compruebe `3c9faf7`.
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
  (`33e7001`, del 7).
* Idea para la v0.2 apuntada en `docs/PLAN.md` (`d433b91`): un núcleo independiente del proveedor,
  para que cualquier entorno de agentes se enganche y las reglas se ejecuten en un paquete. Tres
  piezas: adaptadores finos por entorno sobre una decisión central; el sandbox del sistema por fuera
  del agente entero (`@anthropic-ai/sandbox-runtime` o un contenedor), con la configuración sacada de
  `.actuarii.json`; y un intermediario de escritura por MCP, que escribe las rutas gobernadas tras
  comprobar la propuesta, de modo que la frontera no dependa de los hooks de cada entorno.
* Fase 2, adelantada desde el 12 de octubre:
  * Decisiones de la fase y protocolo de la prueba en limpio, commiteados antes de medir (`35258dd`;
    `docs/design/PRUEBA_EN_LIMPIO.md`).
  * Instalador, `tools/install.py` (`7c52129`): copia el kit, fusiona `settings.json` con su
    `sandbox` y `.mcp.json`, instala el `pre-commit` y añade `.data/` al `.gitignore`. Comprueba
    todo antes de escribir; con un choque no escribe nada; una segunda ejecución no cambia nada.
    Biblioteca estándar, Python 3.9. 57 tests, uno de punta a punta: en un repositorio recién
    instalado, el hook copiado deniega sin recibo y permite con el recibo del validador copiado.
  * Corrección del hito 1 (`c6b289b`): sin base de auditoría, el hook de escritura deniega con su
    regla y la llamada a `validate_proposal`, en vez de «unable to open database file». Las
    consultas de `hook_gate` siguen fallando sin base, como fijaban sus tests.
  * `LICENSE` (texto oficial de Apache-2.0, de dos copias locales independientes e idénticas,
    SHA-256 `cfc7749b…3d30`) y `NOTICE` (`7bf6654`); `pyproject.toml` de la v0.1.0 (`16c60d0`).
  * Cada cambio de código, por contrato validado al implementador (`sonnet`), con
    `verify_red_green.py` repetido por el chat principal antes de fusionar: salió 0 las tres veces.
* Marco del README en `docs/PLAN.md` (`7707cc3`) y casos de partida de la 2b reducida, el instalador
  y el navegador integrado (`5561616`).
* Repositorio privado en GitHub, `AlexusPacicus/actuarii`, creado por el autor con `gh`.
* CI en Linux (`a9709e5`): acciones fijadas por SHA, Python 3.11, la secuencia de la prueba en limpio
  como paso propio y la suite. Primera ejecución en verde: 3 tests de la secuencia en 2 s y la suite
  en 50 s, 3055 pasan y 14 se saltan (los casos que piden un sistema de ficheros que no distinga
  mayúsculas, por la cuenta de sus condiciones). Resultados en `docs/design/PRUEBA_EN_LIMPIO.md` §5.
* Enmienda de la prueba en limpio antes de medir (`43cd7a8`): destino un clon de `noticias` en
  `v3-exp`, y el agente recibe solo la tarea. Comparación de configuraciones (sin gobierno, gobierno
  por instrucción, Actuarii) apuntada en `docs/design/COSTE.md` §6, sin medir.
* Guía de instalación, `INSTALL.md` (`943358c`).
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
  texto que no es JSON sí se aplica (`af973ab`).
* F4b, primitivas por `ast` sobre el fichero resultante, decididas en la puerta (`1f4c1fd`), en dos
  pasos porque el servidor MCP en marcha conservaba la matriz léxica hasta reconectarlo (`e8e48de`,
  `42a79c6`). Diseño en `docs/design/RECIBO_CONTENIDO.md` §4.1.
* Sandbox de Claude Code investigado, probado (casos S1–S9) y adoptado como frontera de `Bash`
  (`546730b`). Detalle en `docs/design/SANDBOX.md`.
* Integridad del commit con un hook `pre-commit` (`4ee3691`), instalado y probado en este repositorio.
* `AGENTS.md` v2.1.0, la skill `boundary-validator` y la plantilla `implementer` al día (`cad6b77`,
  `0fc8cf9`, `901b90d`); `PROCESO.md` con el estado de las correcciones (`d4fd8d6`).
* F6, los hooks deciden igual con y sin el shim y con el Python 3.9.6 del sistema (`a391b0e`).
* A15, la fase roja y la verde de los tests se comprueban en código (`3162f65`).
* Coste de una escritura gobernada medido con la regla commiteada antes (`c4ae80e`, `48ba34c`) y
  diseño de optimización para la v0.2 (`7be8667`, `0df813c`). Detalle en `docs/design/COSTE.md`.
* Traspaso y decisiones de la semana 1 en `docs/PLAN.md` (`1456738`, `0df813c`).

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
  sistema de ficheros que no distingue mayúsculas; se corrigió antes de fusionar (`19b2896`).
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
* Fase 1, pasos 5 y 6: el anuncio al abrir sesión (`387c6b6`), la revisión ciega configurable
  (`4368b50`), fuera lo que solo servía a Traianus (`887b486`) y `AGENTS.md` genérico con sus
  subagentes y skills (`a678a95`). Fase 1 cerrada con 1979 tests (`fcd3f78`).
* Búsqueda previa: no hay nada igual; se ajusta la presentación, no el kit (`a7fe384`).
* Auditoría adversarial con pautas aprobadas antes de empezar (`8e2d894`): casos A01–A18 y plan de
  correcciones F1–F7 (`a5bdacb`).
* F1, el cableado del kit gobernado (`1059787`); F2, la puerta deniega por defecto (`0ef7221`); F3,
  entrada estricta del validador (`a489919`); F4a, el recibo ata el contenido exacto (`7bb93c1`).

**Decidido (autor)**
* Calendario de tres semanas hasta el 25 de octubre y criterio de utilidad para retomar Traianus
  (`de8cabf`).
* La auditoría adversarial se adelanta al empaquetado. F2 deniega por defecto y la matriz léxica se
  elimina en F4 (`72ce7da`).

## 2026-10-05

Reconstruida. Suite: 1497 en verde al cerrar la fase 0, 1768 al final del día.

**Hecho**
* Extracción del kit desde Traianus con la historia conservada; plan y `CLAUDE.md` (`dfa29f6`).
* Fase 0: la suite pasa sin Traianus instalado (`87e3bc7`).
* Fase 1, pasos 1 a 4: los hooks no dependen del directorio actual (`060db60`), la configuración del
  proyecto en `.actuarii.json` (`a5736f4`), los directorios del shim (`aca4ea7`) y el registro de
  contratos (`b39c5cd`) salen de ella.
