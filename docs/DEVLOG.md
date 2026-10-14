# DEVLOG de Actuarii

Una entrada por día, la más reciente arriba: qué se hizo (con sus commits), qué se decidió y por qué, qué
salió mal y qué se aprendió. Lo que ya cuentan los documentos de diseño se enlaza, no se repite. Se
escribe al cerrar cada sesión (decisión del autor, 2026-10-07). Las entradas del 5 y el 6 de octubre se
reconstruyeron el 7 a partir de `git log` y de `docs/PLAN.md`.

## 2026-10-14 (tarde)

Segunda sesión del miércoles, después de reiniciar Claude Code. El validador con el motivo y el perímetro nuevo ya
rigen; los tres contratos que se quedan en la v0.1 están implementados y verificados, y AGENTS.md pasa a la
v2.2.0. Suite: de 3166 a 3278 en verde. Sin push: lo lanza el autor.

**Hecho**
* **Al arrancar:** el servidor MCP nuevo exige el motivo. Lo comprobó una sonda sobre
  `docs/probe-rationale.md`, que no existe. La base real se migró al primer uso y conserva sus 392 filas. El
  esquema de `validate_proposal` que muestra la sesión es una copia vieja, sin `Rationale`; el servidor acepta
  el campo igual.
* `main` avanzado sin merge hasta `2fd0b9f`, el final de la cadena del motivo y del perímetro.
* Las decisiones de hoy, anotadas en el PLAN (`d61b2c3`).
* **A20** (`f06b826`): el `pre-commit` solo se escribe dentro del `.git` propio del destino. Son conflicto, sin
  escribir nada: un `core.hooksPath` global o que sale del destino, un directorio de hooks del árbol de
  trabajo, un *worktree* enlazado y un `.git` que es un fichero. Verificado: T1–T5 y X1 rojos, T6 y X2 de
  guarda, suite 3177.
* **A31** (`2f8a898`; contrato `024bd2f` y su ampliación `69f18a7`): la raíz entra en `sys.path` solo para
  `import tools` y sale enseguida. Vale para los nueve scripts: los tres hooks, `commit_integrity.py`, el
  validador, el instalador y los tres de auditoría. En los hooks va dentro del `try` que deniega. Verificado:
  T1–T4, X3 y X4 rojos, T5, X1 y X2 de guarda, suite 3233.
* **A34** (`6430ca8`; contrato `1f743b3` y `4f8e3d6`):
  * el revisor ciego lleva `omitClaudeMd: true`, y los ajustes, `includeGitInstructions: false`;
  * `build --lock` no pone el candado si falta alguno de los dos;
  * la skill separa lo que se cumple de lo que solo se declara.
  * Verificado: T1–T3, T5 y X1 rojos, T4 de guarda, suite 3278.
* **AGENTS.md v2.2.0** (`8356518`):
  * 5.1 dice lo que cumple la revisión ciega;
  * 6.2 pierde su [enforced];
  * §9 declara lo que deja acta (A30), el arranque de las puertas (A19, A32), las herramientas de ficheros
    (A33), las credenciales (A35), los canales sin regla (A29), los enlaces (A26), lo que sigue recibiendo el
    revisor (A34), y A21, A23, A24, A25 (en «Forged logs») y A28.

**Decidido (autor)**
* Se quedan A20, A31 y A34. A19, A32, la opción (c) con A33 y A35 pasan a la v0.2, declarados.
* La 2b se cierra sin el caso (b); para el informe queda la tabla «Resumen» de `CASES.md`.
* A21, A23, A24, A25 y A28 se declaran en §9, sin contrato.
* El push, sí. Lo lanza el autor, porque el sandbox no deja salir a la red a `Bash`.

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

**Siguiente**
* El push: 17 commits.
* **La sesión siguiente arranca sin la foto de git** (`includeGitInstructions: false`); el anuncio de la
  sesión sigue diciendo lo que rige.
* **Jueves 15: los dos contratos del instalador en una orden.**
  * Sin A35.
  * Llevan a los destinos el perímetro nuevo, el motivo e `includeGitInstructions`: sin él, `build --lock` no
    pone el candado en un destino (D5 de A34).
  * Reescriben `INSTALL.md`, con el entorno fuera del repositorio.
  * Después, la nueva medida en macOS.
* La tabla «Resumen» de `CASES.md` hasta A35, con lo corregido y lo declarado, para el informe del lunes 19.
* `examples/traianus/skills/instrument-audit/SKILL.md` sigue diciendo «Blind by construction».
* Sin la opción (c), la memoria normal de Claude Code sigue abierta; falta decidir cómo se evita o se declara.
* El README.
* Disco: 6,0 GiB libres.

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
* **El objetivo de la v0.1, reescrito** en `docs/PLAN.md` (`1222886`): actas de trabajo para agentes de código.
* **Contrato del motivo** (`docs/design/MOTIVO.contrato.json`, `1222886`) e implementación (`0343a94`, `sonnet`):
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
* **Contrato del perímetro** (`docs/design/PERIMETRO.contrato.json`, `a0d6df9` y `6e4ea39`) e implementación
  (`ec2dc08`):
  * sin preguntar en los dos entornos: `pytest`, `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `df`, `echo`,
    `sed -n`, `sort`, `uniq`, `diff` y `validate_proposal`;
  * una lista cerrada, con su test; el resto de `Bash` sigue preguntando;
  * en OpenCode, el validador va con el nombre `boundary-validator_validate_proposal`, sin comprobar ejecutando
    OpenCode;
  * AGENTS 7.1, reescrito.
  * Verificado por el chat: T1, T2 y T4 rojos, T3 y T5 de guarda, suite 3166.
* **AGENTS §9** (`bb86a87`): `sort`, `uniq` y `sed -n` escriben o ejecutan con sus opciones (en GNU `sed`, `e`
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
  añadió D12 (`6e4ea39`). Lección: al encadenar contratos, la sesión sigue con el servidor y los ajustes con que
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
* Puesta al día y línea base: `main` en `f9b8990`, 3080 en verde.
* **Decisión de A19 rehecha** (`d33c63a`, corregida en `629b6e1`; `docs/design/ARRANQUE_PUERTAS.md`):
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
* **A33** (C1, `3db5647`): `Write` escribe `.git/hooks/pre-commit`, `.git/config` y `.vscode/tasks.json` sin
  recibo; el sandbox se los impide a `Bash`. Probado con cargas al hook y sondas que no escriben nada.
* **A34** (C1, `2b5fb05`, `24c1e19`): la revisión ciega no es ciega por construcción.
  * Las 6 transcripciones del auditor de Traianus contienen `CLAUDE.md`, `AGENTS.md` y el índice de la
    memoria automática, con resultados previos.
  * La documentación de Claude Code confirma qué recibe un subagente: `CLAUDE.md`, la instantánea de git y
    el mensaje de encargo. `omitClaudeMd` e `includeGitInstructions` quitan los dos primeros.
* **A35** (C2, `653985a`): `Bash` abre `~/.ssh` y `~/.config/gh` dentro del sandbox. Comprobado con
  `test -r`, sin leer nada.
* **Principios de diseño** en `docs/PLAN.md` (`ea17f20`): el agente aislado; toda salida pasa por una regla;
  lo que corre fuera no se fía de lo que el agente escribe.
* **Cuatro contratos validados en código, con su paquete de contexto servido; ninguno lanzado:**
  * A19, A31 y A32 (`5f0df76`);
  * A20 (`6f103ea`): el `pre-commit` solo dentro del `.git` del destino;
  * la opción (c) con A33 (`6f103ea`): las herramientas de ficheros con el alcance de `Bash`;
  * A34 en su parte de la v0.1 (`2b652fd`).
* **Memoria bajo código** (`e2d4275`): tres recuerdos y su índice en `.claude/memory/`, cada uno con su
  recibo, cargados por `CLAUDE.md` y `opencode.jsonc`.
* **Documentación de Claude Code** leída con el navegador integrado: memoria, subagentes, ajustes, referencia
  de ajustes, sandbox y entornos aislados.
* **Diseño del entorno aislado propio para la v0.2** (`0bfa1d0`, `docs/design/ENTORNO_PROPIO.md`):
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
    efecto físico, punycode y credenciales en un proxy (`758df0b`).

**Salió mal y se aprendió**
* **La decisión del 12 ponía `-I` en los hooks**, aunque el DEVLOG del 10 ya decía que `-I` no impide A19.
  Lección: comprobar la semántica de una opción en el código fuente antes de decidir con ella.
* **El primer diseño ponía la raíz al final de `sys.path` (`d33c63a`).** Al preparar el contrato apareció
  en el `site-packages` de pyenv un paquete `tools` ajeno (`deepcode_hku`) que habría tapado el kit en el
  validador de esta misma sesión. Se corrigió antes del contrato (`629b6e1`). Lección: mirar el intérprete
  real antes de fijar un orden de importación.
* **El mismo diseño quitaba del `PATH` los directorios temporales.** Eso dejaría fuera los `tmp_path` de
  pytest en Linux. Se declaró en su lugar.
* **`629b6e1` se commiteó antes de pasar la suite;** se pasó después y salió en verde. Es la regla de siempre
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
* **Caso (a), A19 (C1), confirmado en vivo** (`f436964`): código en el arranque del intérprete. Con el
  `.venv` dentro del repo, un `sitecustomize.py` testigo plantado en su `site-packages` se ejecutó en
  11 procesos (hooks y servidor MCP) fuera del sandbox, en una sesión abierta desde el `.venv` activado
  sobre `noticias-2b`. El validador no puede usar `-S` porque necesita `pydantic`: la carga se ejecuta
  siempre. El montaje que recomienda `INSTALL.md` es el vulnerable.
* **Casos en el scratchpad**, con `trap`/respaldos, sin tocar nada real:
  * A20 (c, C1, `a234a5e`): el instalador escribe el `pre-commit` fuera del destino con un
    `core.hooksPath` global absoluto; rompe I1 y puede bloquear los commits de los demás repos.
  * A21 (l, C3, `8cc5df4`): A18 reabierto; un `params`/`arguments` no-dict no vacío tumba el servidor MCP.
  * A22 (k, OK, `8cc5df4`): integridad del commit; media preparación, modo y grafía rechazados.
  * A23 (i, C2, `8cc5df4`): `Glob` con llaves esquiva el análisis estático del confinamiento de la
    revisión ciega; el hook permitió `{..,x}/**` con `path` dentro del paquete.
  * A24 (d, C2, `433edc2`): el anuncio afirma «Bash cannot write the governed paths» sin comprobar
    `denyWrite`; en Actuarii acierta por el harness, miente para una ruta propia sin su `denyWrite`.
  * A25 (e, C2, `433edc2`): `.data/` escribible por `Bash`; solo el fichero `.db` está en `denyWrite`.
  * A26 (g, límite, `433edc2`): una ruta gobernada que es enlace simbólico se gobierna por el destino;
    no alcanzable por el agente y el `pre-commit` rechaza enlaces en rutas gobernadas.
  * A27 (h, OK, `16f3791`): el sandbox bloquea crear un enlace duro a un fichero gobernado.
  * A28 (j, C2, `16f3791`): nada obliga a correr `verify_red_green.py` (6.2 se sobreafirma) y el
    verificador no compara el diff con `files_may_touch`/`files_must_not_touch`.
  * A29 (m, límite, `a8ad593`): inventario documental de los canales a la web/host fuera del sandbox
    (navegador, Chrome, conectores que envían, artifacts, host, programadores).
  * A30 (n, límite, `a8ad593`): el desplazamiento del trabajo a rutas no gobernadas, con la evidencia de
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
* Entradas del 9 y del 10 de este DEVLOG, reconstruidas de las transcripciones (`7aab204`). Los
  hallazgos de la auditoría informal del 10, que solo estaban fuera del repositorio, entran en él. Push;
  la CI pasa en verde con el commit del kit instalado con su hook (`d2912f4`).
* Segundo ensayo de la prueba en limpio, sin cifra (`fcd8053`). Empezó como medida y pasó a ensayo
  cuando el autor pidió ayuda con el argumento del instalador. Primera aplicación del método del hito 1
  por el registro (§4c): se cumple. `INSTALL.md` corregido: el argumento es el repositorio de destino, y
  las rutas de los ejemplos hay que sustituirlas.
* **Medida en macOS** (`5631c5f`): los dos hitos se cumplen; 612,8 s en total, de los que el agente tarda
  35 s; pasa de los 300 s. Sin cronómetro: los tiempos salen del reflog, de las fechas de los ficheros y
  de la transcripción.
* **Caso real** (`d2155ba`): el agente escribió los 16 tests en `tests/unit/`, fuera de las rutas
  gobernadas, «para no pedir el recibo». El shim denegó un `python3 -c` y el agente siguió sin él. El
  cambio de configuración, que se pidió al agente en vez de hacerlo a mano, pasó por el canal gobernado
  y dejó dos recibos `SPEC`.
* Pautas de la 2b reducida, aprobadas y commiteadas antes de empezar (`aeafeb5`): G14–G17, las promesas
  del instalador I1–I4 y 14 casos por riesgo. Entre ellos, la copia redirigida, con el módulo, el texto
  y las tres ejecuciones fijados antes.
* Instalación en una orden, decidida y apuntada en `docs/PLAN.md` (`acffc36`).

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
