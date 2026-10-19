# Actuarii — decisiones

Registro de las decisiones del autor. Solo se amplía: una entrada no se edita nunca, y revisar una decisión es
añadir otra que dice a cuál sustituye. Las que están en vigor se listan en `docs/ESTADO.md`. Las decisiones
técnicas de un contrato se quedan en el contrato. La fecha de cada entrada sale del reloj.

ADR-001 a ADR-020 se escribieron el 2026-10-14 y recogen las decisiones en vigor ese día, tomadas entre el 5 y
el 14 de octubre. Cada una lleva la fecha en que se tomó y dónde está su razonamiento. Lo anterior no se migra.

## ADR-001 — Nombre, licencia y relación con Traianus (2026-10-05, autor)

**Contexto:** el kit nació gobernando Traianus y se extrae a un repositorio propio.
**Decisión:** se llama Actuarii, con licencia Apache-2.0, y conserva su historia con `git filter-repo`. Este
repositorio es el canónico: Traianus guarda una copia vendorizada, y los cambios entran aquí primero y se portan
a mano.
**Consecuencias:** cuando Traianus levante la congelación de su `pyproject.toml`, pasa a depender del paquete.
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Decisiones tomadas».

## ADR-002 — Primero el kit; Traianus como memoria de agentes, solo con señal (2026-10-05, autor)

**Contexto:** hay dos líneas posibles: el kit, que se usa sin Traianus, y Traianus como memoria de agentes.
**Decisión:** primero el kit. La fase 4, Traianus como memoria de agentes, empieza solo si el kit da señal
(ADR-005) y se cumple su criterio de utilidad.
**Consecuencias:** nada de Traianus antes del lanzamiento (ADR-004).
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Decisiones tomadas» y «Fase 4».

## ADR-003 — Se publica el 25 de octubre, esté como esté (2026-10-06, autor)

**Contexto:** tres semanas hasta el lanzamiento y cuatro de ventana para la señal, con horas y créditos
limitados.
**Decisión:** la v0.1 se publica el 25 de octubre. Si faltan horas, se recorta alcance y la fecha no se mueve. Lo
que no esté listo pasa a la v0.2.
**Consecuencias:** cada criterio de la v0.1 dice qué pasa si no se cumple el 25 (ADR-017).
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Calendario».

## ADR-004 — Lo que no se hace antes del lanzamiento (2026-10-06, autor)

**Contexto:** el riesgo es que el trabajo se vaya a lo que no llega al lanzamiento.
**Decisión:** antes del 25 no se hace nada de Traianus, ninguna mejora de gobernanza que no responda a un fallo
real y ninguna función nueva fuera del plan. La única función nueva admitida es el acta en git (ADR-016,
2026-10-14).
**Consecuencias:** las ideas que se salen del camino se apuntan en «Ideas para la v0.2» del PLAN y esperan.
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Calendario»; `docs/DEVLOG.md`, 2026-10-14 (tarde).

## ADR-005 — La señal de éxito (2026-10-07, autor)

**Contexto:** hace falta saber, con un criterio escrito antes, si el kit le interesa a alguien.
**Decisión:** cuatro semanas desde la publicación. Éxito si al menos 5 personas ajenas lo instalan o abren una
issue, o si nace una conversación de trabajo. Si no llega, se revisa con datos, sin reencuadrar. Cómo se cuenta y
qué pasa el 22 de noviembre está en el ROADMAP, §3 y §4 (ADR-017).
**Consecuencias:** sin señal no empiezan la v0.2 ni la fase 4.
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Decisiones de la semana 1»; `docs/ROADMAP.md`.

## ADR-006 — Repositorio privado hasta el 25 y un solo DEVLOG (2026-10-07, autor)

**Contexto:** antes de publicar hay que decidir dónde vive el trabajo y su registro.
**Decisión:** el repositorio de GitHub es privado hasta el 25 y público al publicar. Hay una sola bitácora,
`docs/DEVLOG.md`, sin LEDGER y sin nada en las de Traianus.
**Consecuencias:** —
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Decisiones de la semana 1».

## ADR-007 — La distribución de la v0.1: un instalador que copia el kit (2026-10-08, autor)

**Contexto:** el shim solo ejecuta scripts commiteados del propio repositorio y el kit se gobierna a sí mismo.
La clave `sandbox` y el `pre-commit` se escriben en el proyecto de todos modos, y un plugin vive fuera del
repositorio.
**Decisión:** un instalador escrito con la biblioteca estándar de Python, que importa con un Python 3.9 de
sistema, copia el kit en `tools/` del destino. Si algo choca, se para, dice qué choca y no escribe nada. El
plugin queda para la v0.2.
**Consecuencias:** el validador necesita `pydantic` en el entorno.
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Decisiones de la fase 2».

## ADR-008 — La instalación en una orden, con el entorno fuera del repositorio (2026-10-12, autor)

**Contexto:** la medida en macOS dio 612,8 s, y casi todo ese tiempo fue la persona siguiendo la guía.
**Decisión:** `tools/install.py` lo hace todo con una orden: comprueba, instala y escribe la configuración.
* Solo pregunta qué rutas gobernar, además de las mínimas, y si hace el commit.
* Comprueba `pydantic` en el intérprete con que arrancará el servidor, y pide permiso antes de instalarlo.
* Tiene un modo sin preguntas.

El entorno de Actuarii vive fuera del repositorio (2026-10-13).
**Consecuencias:** dos contratos al implementador y una medida nueva (ROADMAP, V2 y V4).
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Instalación en una orden» y «Principios de diseño».

## ADR-009 — La v0.1 son actas de trabajo; la seguridad, en la v0.2 (2026-10-13, autor)

**Contexto:** la auditoría (A19–A35) mostró que una frontera montada sobre Claude Code tiene demasiadas salidas
frente a un agente adversario.
**Decisión:** la v0.1 son actas de trabajo para agentes de código: «Work records for coding agents. Every action
leaves a record that it happened, and why. Built for settings where traceability comes first.» La seguridad
frente a un agente adversario no es de esta versión: pasa a la v0.2, con un entorno aislado propio
(`docs/design/ENTORNO_PROPIO.md`).
**Consecuencias:** AGENTS.md §9 declara lo que la v0.1 no cubre. El objetivo anterior, demostrar que hace falta
un middleware, pasa a ser la motivación de la v0.2.
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Fase 3» e «Ideas para la v0.2»; `docs/DEVLOG.md`, 2026-10-14.

## ADR-010 — La memoria del agente, bajo código; la automática de Claude Code, apagada (2026-10-13, autor)

**Contexto:** sin memoria, el agente no vale. La memoria automática de Claude Code vive fuera del repositorio,
sin recibo ni versiones, y la opción (c), que iba a denegarla, pasó a la v0.2.
**Decisión:** la memoria del agente es la de `.claude/memory/`: un recibo por escritura y git guarda cada
versión. El 2026-10-14 se decidió apagar la automática en todo el proyecto con `autoMemoryEnabled: false`. Va en
un contrato pequeño, después del instalador, que corrige también la línea de `MEMORY.md` sobre la opción (c).
**Consecuencias:** la memoria se publica el 25, y los recuerdos se escriben sabiéndolo. En los proyectos donde se
instala el kit, la memoria automática no se toca.
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Principios de diseño»; `docs/ROADMAP.md`, D5.

## ADR-011 — El motivo, obligatorio, y ningún recibo sin acta (2026-10-14, autor)

**Contexto:** para que el «por qué» de las actas sea verdad, tiene que guardarse con cada decisión.
**Decisión:** `Rationale` es obligatorio en cada propuesta (de 1 a 1000 caracteres) y se guarda con cada
decisión, también con las denegadas. Si el acta no se puede escribir, no hay recibo. «The proposal schema»
sustituye a «5 Radicals».
**Consecuencias:** las bases de auditoría viejas se migran al primer uso.
**Sustituye a:** —
**Fuente:** `docs/design/MOTIVO.contrato.json`; `docs/DEVLOG.md`, 2026-10-14.

## ADR-012 — El perímetro de permisos (2026-10-14, autor)

**Contexto:** de las llamadas de un implementador, 161 pedían permiso, y la mayoría no decidían nada.
**Decisión:** en Claude Code y en OpenCode, sin preguntar:
* `pytest`;
* una lista cerrada de órdenes de lectura: `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `df`, `echo`, `sed -n`,
  `sort`, `uniq` y `diff`;
* `validate_proposal`.

El resto de `Bash` sigue preguntando. Lo que `sort`, `uniq` y `sed` pueden escribir con sus opciones se declara
en §9, en vez de quitar esas órdenes de la lista.
**Consecuencias:** AGENTS 7.1, con su test de paridad entre los dos entornos.
**Sustituye a:** —
**Fuente:** `docs/design/PERIMETRO.contrato.json`; `docs/DEVLOG.md`, 2026-10-14.

## ADR-013 — Qué correcciones de la auditoría entran en la v0.1 (2026-10-14, autor)

**Contexto:** con la seguridad fuera de la v0.1 (ADR-009), solo hace falta corregir lo que rompe algo a quien
instala el kit, aunque nadie ataque.
**Decisión:**
* se corrigen A20, A31 y A34;
* A19, A32, la opción (c) con A33 y A35 pasan a la v0.2, declarados en §9;
* A21, A23, A24, A25 y A28 quedan declarados, sin corregir;
* la 2b se cierra sin el caso (b).

**Consecuencias:** AGENTS.md v2.2.0. La tabla «Resumen» de `CASES.md` recoge lo corregido y lo declarado
(ROADMAP, V5).
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Ideas para la v0.2»; `docs/DEVLOG.md`, 2026-10-14 (tarde).

## ADR-014 — Los campos de la propuesta, con nombres llanos en la v0.2 (2026-10-14, autor)

**Contexto:** los nombres del esquema de la propuesta son jerga.
**Decisión:** `Topological_Grounding` e `Implementation_Block` pasan a nombres llanos (`old_string`, `new_string`
o `reason`) en la v0.2. Antes del lanzamiento solo se limpia la jerga de las descripciones y del README.
**Consecuencias:** —
**Sustituye a:** —
**Fuente:** `docs/PLAN.md`, «Ideas para la v0.2».

## ADR-015 — Un estado corto al abrir cada sesión, en lugar del PLAN (2026-10-14, autor)

**Contexto:** el PLAN crecía y se cargaba entero en cada sesión.
**Decisión:** `CLAUDE.md` y `opencode.jsonc` cargan `docs/ESTADO.md`, que se pone al día al cerrar cada sesión.
El PLAN pasa a ser un documento de consulta.
**Consecuencias:** —
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-14 (tarde).

## ADR-016 — El acta en git (2026-10-14, autor)

**Contexto:** el rastro registra que se pidió escribir, no que se escribió. Guarda hashes y no el texto, y vive
en una base local que git ignora.
**Decisión:**
* Un hook `commit-msg` añade al mensaje de cada commit, como *trailers*, los motivos de los recibos de sus
  ficheros gobernados.
* El *trailer* dice si el contenido del commit coincide con el que dejaron las escrituras con recibo. El
  contenido esperado lo calcula la puerta antes de cada escritura, sin proceso nuevo, y si no puede guardarlo,
  deniega la escritura.
* El hook solo registra: no bloquea el commit. Lo instala el instalador.

**Consecuencias:** la puerta pasa a escribir en la base, y el segundo contrato del instalador crece. Si no llega a
tiempo, la frase del README pierde «that it happened» (ROADMAP, V3).
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-14 (tarde); `docs/ROADMAP.md`, D1.

## ADR-017 — El ROADMAP (2026-10-14, autor)

**Contexto:** hace falta cortar el alcance antes del 25, y que la revisión del 22 de noviembre se haga contra
algo escrito antes.
**Decisión:** `docs/ROADMAP.md` fija:
* los criterios de la v0.1 (V1–V9), cada uno con su comprobación, su corte y lo que pasa si no se cumple el 25;
* cómo se cuenta la señal;
* la puerta del 22 de noviembre;
* los criterios de la v0.2.

Las propuestas de Claude que contiene se aceptaron enteras.
**Consecuencias:** ningún criterio mueve la fecha. Solo V8, la historia limpia, podía retrasar la apertura del
repositorio, y ya se cumple.
**Sustituye a:** —
**Fuente:** `docs/ROADMAP.md`.

## ADR-018 — El README: su primer límite y su marco (2026-10-14, autor)

**Contexto:** la frase del README prometía más de lo que el kit cumple, y el párrafo del marco estaba escrito en
clave de seguridad.
**Decisión:** justo debajo de la frase va el primer límite: solo deja acta lo que pasa por el canal gobernado,
y lo que hace `Bash` o lo que va a rutas no gobernadas no la deja (A30). El marco explica por qué las reglas
viven fuera del modelo, y presenta la seguridad frente a un agente adversario como lo que trae la v0.2.
**Consecuencias:** —
**Sustituye a:** —
**Fuente:** `docs/ROADMAP.md`, D3 y D6.

## ADR-019 — A33 y A34 no se cuentan a Anthropic (2026-10-14, autor)

**Contexto:** A33 y A34 tocan comportamiento de Claude Code.
**Decisión:** no se cuentan.
* A34 es comportamiento documentado, con su interruptor (`omitClaudeMd`).
* A33 se sigue del diseño documentado: el sandbox cubre `Bash`, y las herramientas de ficheros pasan por los
  avisos de permiso.

El README los describe con su versión, como límites del kit y no como fallos de Claude Code.
**Consecuencias:** se reconsidera si una prueba muestra que Claude Code escribe sin preguntar donde dice que
pregunta.
**Sustituye a:** —
**Fuente:** `docs/ROADMAP.md`, D4.

## ADR-020 — La historia, sin lo personal y con el correo *noreply* (2026-10-14, autor)

**Contexto:** el repositorio se hace público el 25, y su historia tenía información personal y el correo
personal del autor.
**Decisión:**
* Se quita del árbol y de la historia la información personal que fijó el autor. La lista no se guarda en el
  repositorio.
* El correo de los commits pasa a la dirección *noreply* de GitHub, también en la configuración global de git.
* La historia reescrita va a un repositorio nuevo y el viejo se borra, porque GitHub sigue sirviendo los commits
  viejos a quien pida su hash.

**Consecuencias:** los hashes anteriores a la reescritura ya no existen; las citas de `docs/` están rehechas.
**Sustituye a:** —
**Fuente:** `docs/ROADMAP.md`, D2; `docs/DEVLOG.md`, 2026-10-14 (noche).

## ADR-021 — Las decisiones van en este registro, que solo se amplía (2026-10-14, autor)

**Contexto:** las decisiones vivían en seis sitios: el PLAN, el DEVLOG, `ESTADO.md`, el ROADMAP,
`ENTORNO_PROPIO.md` y los contratos. Al revisarlas, se editaban encima.
**Decisión:**
* Las decisiones del autor van en `docs/DECISIONES.md`.
* Una entrada no se edita nunca: revisar una decisión es añadir otra que dice a cuál sustituye.
* Las que están en vigor se listan en `docs/ESTADO.md`.
* Las decisiones técnicas de un contrato se quedan en el contrato.
* El DEVLOG cita las decisiones por su número. El PLAN queda como historia hasta el 14 y solo recibe las ideas
  que esperan.

**Consecuencias:** lo anterior al 14 no se migra: ADR-001 a ADR-020 recogen lo que estaba en vigor ese día. Que el
kit haga cumplir el «solo se añade» queda como idea para la v0.2.
**Sustituye a:** —
**Fuente:** esta entrada.

## ADR-022 — El perímetro de permisos, sin comodín y con la lista ampliada (2026-10-15, autor)

**Contexto:** el autor seguía viendo demasiados permisos manuales. Claude Code evalúa deny, luego ask y luego
allow, y el `"Bash"` a secas que encabezaba `ask` hacía preguntar todas las llamadas a `Bash`: la lista de
ADR-012 no aprobaba nada en Claude Code.
**Decisión:**
* Sin preguntar, en Claude Code y en OpenCode: `pytest`; las órdenes de lectura de ADR-012 más `cut`, `tr`, `jq`,
  `cmp` y `date` (sin argumento o con formato `+`); las órdenes de git de lectura más `git merge-base`,
  `git rev-list` y `git for-each-ref`; y `validate_proposal`.
* En Claude Code, ninguna regla `ask` o `deny` tapa una `allow`, y lo que pregunta por el resto es el modo
  `default`, no un comodín. OpenCode mantiene su `"*": "ask"` primero.
* Las órdenes de git y de `gh` que escriben siguen preguntando. `git branch` también, y las ramas se listan con
  `git for-each-ref`.
* Lo que algunas órdenes de la lista escriben con sus opciones (`sort`, `uniq`, `sed`, y el `--output` de
  `git diff`, `git log` y `git show`) se declara en §9.
* Va en un contrato pequeño, antes del primero del instalador, que lleva este perímetro a los destinos.

**Consecuencias:** AGENTS 7.1 reescrito, con un test de que nada tapa una `allow`. En otro modo de permisos, el
modo decide lo que ninguna regla nombra. `implementer.md` pide una orden por llamada, sin variables, `cd` ni
bucles. Rige desde la sesión siguiente a su commit.
**Sustituye a:** ADR-012.
**Fuente:** `docs/design/PERIMETRO_SIN_COMODIN.contrato.json`; `docs/DEVLOG.md`, 2026-10-15.

## ADR-023 — La puerta no toma por ruta un texto que no puede serlo (2026-10-15, autor)

**Contexto:** con una herramienta que no conoce, la puerta revisa cada texto que parece una ruta y le pregunta al
sistema de ficheros adónde apunta. Si un nombre entre barras pasa de 255 bytes, el sistema responde
`File name too long`, y la puerta deniega por no poder verificar. En un repositorio con el kit, una herramienta
con un texto largo en una sola línea, que contenga por ejemplo «y/o», queda bloqueada. Pasó al proponer una sesión
desde el chat.
**Decisión:**
* `ENAMETOOLONG` al resolver un candidato se lee como «no es una ruta»: el sistema dice que ningún fichero puede
  llamarse así, ni uno que exista ni uno por crear. Los demás errores del sistema siguen denegando.
* Va en un contrato pequeño, en la sesión siguiente, después de la sonda del perímetro y antes del primer contrato
  del instalador.

**Consecuencias:** el instalador copia a los destinos la puerta ya corregida.
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-15.

## ADR-024 — Solo un nombre demasiado largo deja de ser una ruta (2026-10-15, autor)

**Contexto:** ADR-023 lee todo `ENAMETOOLONG` como «no es una ruta», pero el sistema da ese error en dos casos:
* un nombre entre barras más largo de lo que admite el sistema de ficheros: ningún fichero puede llamarse así;
* una ruta entera de más de 1024 bytes en macOS (4096 en Linux) con cada nombre admisible: el fichero sí puede
  existir, y una herramienta lo alcanza por una ruta relativa.

En el segundo caso, dejar pasar el texto sería fallar en abierto (AGENTS 8.4). La prosa no llega a él: la puerta se
para en el primer nombre que no existe, y ese error solo sale con un árbol real de directorios muy profundo.

El límite de un nombre no es una cifra fija. En el macOS del autor, un nombre ASCII de 260 bytes da
`File name too long` y uno de 86 «€», con 258 bytes, se admite: cuenta caracteres. En Linux, con ext4, cuenta
bytes. Contar 255 bytes tomaría por demasiado largo un nombre legal en macOS.
**Decisión:**
* `ENAMETOOLONG` al resolver un candidato se lee como «no es una ruta» solo si el sistema rechaza también uno de
  los nombres de la ruta resuelta por sí solo, buscado relativo a la raíz del repositorio, para que la ruta que
  recibe sea corta. La puerta no cuenta bytes ni caracteres: le pregunta al sistema. Si el sistema admite cada
  nombre solo, la puerta sigue denegando, como con los demás errores del sistema.
* Va en el contrato pequeño que preveía ADR-023, antes del primer contrato del instalador.

**Consecuencias:** el instalador copia a los destinos la puerta ya corregida.
**Sustituye a:** ADR-023.
**Fuente:** `docs/DEVLOG.md`, 2026-10-15 (tarde).

## ADR-025 — El acta en git y las preguntas del instalador, en dos contratos (2026-10-15, autor)

**Contexto:** el segundo contrato del instalador llevaba las preguntas, el modo sin preguntas, `pip`, el commit, el
acta en git (ADR-016) e `INSTALL.md`. Era grande, cambiaba la puerta y dejaba abiertas varias elecciones de
política.
**Decisión:**
* Dos contratos: primero el acta en git (`docs/design/ACTA_EN_GIT.contrato.json`), que es lo más arriesgado y cuyo
  corte quita «that it happened» del README; después las preguntas (`docs/design/INSTALADOR_PREGUNTAS.contrato.json`).
* Cuando la puerta no puede calcular lo que deja una escritura (`NotebookEdit`, una herramienta que no conoce, un
  `Edit` sobre un fichero que no es UTF-8 o que no puede aplicar), la deja pasar sin acta, como antes, y el commit
  dice de ese fichero `changed outside the channel`. El acta se equivoca hacia el lado seguro: solo dice `matches`
  cuando las escrituras registradas llevan al contenido del commit.
* La pregunta de qué más gobernar, y `--govern`, solo admiten una ruta o una carpeta seguida de `/**`, porque cada
  una se traduce exacta a su entrada de `denyWrite`.
* `INSTALL.md` lo reescribe el chat cuando los dos contratos están en `main`.

**Consecuencias:** AGENTS.md v2.3.0: la cláusula 2.7 y dos límites nuevos en §9. La puerta escribe en la base de
auditoría. El hook `commit-msg` se instala a mano en este repositorio y con el instalador en los destinos.
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-16.

## ADR-026 — Los límites, por problemas: gobernanza en la v0.1 y seguridad en la v0.2 (2026-10-17, autor)

**Contexto:** V5 pedía una fila por caso de `docs/adversarial-audit/CASES.md`, de A01 a A35. Una lista de casos dice
lo que se probó, no por qué falla el kit. La auditoría ya separaba dos perfiles: el A, el agente honesto que se
equivoca, y el B, el que busca la salida. Es la línea de ADR-009 entre la v0.1 y la v0.2.
**Decisión:**
* Los límites se cuentan por problemas, cada uno con su motivo. Son ocho.
* Gobernanza: el acta queda incompleta sin que nadie lo busque (v0.1).
  1. El acta solo cubre su canal: se hace en la llamada a la herramienta, no en el disco. A01, A08, A29 y A30.
  2. Ninguna persona aprueba los recibos ni sus motivos: no hay *human in the loop*. El agente se emite su recibo
     y escribe su motivo, y el validador comprueba la forma y la cita, no que el motivo sea verdad. Con la fase
     roja y la delegación pasa lo mismo: el agente que ejecuta se comprueba a sí mismo. A02, A03, A04, A12, A15,
     A16 y A28.
  3. El kit confía en cómo lo instala la persona: enlaces simbólicos, `core.fileMode` o el `PATH` de la sesión; el
     anuncio informa y no comprueba. A11, A14, A24 y A26.
  4. Cuando el validador cae, el trabajo se para: sin servidor no hay recibos, y cada escritura gobernada se
     deniega. A18 y A21.
* Seguridad: un agente que busca la salida la encuentra (v0.2).
  5. Las puertas arrancan en un entorno que el agente alcanza: corren fuera del sandbox, con el Python, el `PATH` y
     los ajustes del repositorio. A09, A10, A19, A31, A32 y A33.
  6. Las comprobaciones son texto, no una frontera: listas de prohibidos y heurísticas de shell; la frontera es el
     sandbox. A05, A06, A07 y A23.
  7. Fuera de la base de auditoría, los registros se pueden escribir: `.data/`, el candado de la revisión ciega y
     los *trailers*. A13, A25 y A34.
  8. La sesión tiene lo que tiene la persona: el kit corre con sus permisos. A35.
* A17, A20, A22 y A27 no son límites: van al pie de la tabla, con su commit.
* La tabla «Resumen» de `CASES.md` pasa a ir de problema a casos, con lo corregido y su commit. La sección de
  límites del README da los ocho problemas, cada uno con su motivo, un ejemplo y lo que cambia en la v0.2, sin los
  ids de los casos.
* V5 se comprueba así: cada caso de `CASES.md` y cada límite de AGENTS §9 están en un problema.
* Poner a una persona en el bucle de los recibos es una función nueva: no entra antes del 25 (ADR-004).

**Consecuencias:** cambia V5 del ROADMAP (ADR-017). AGENTS §9 no se reordena antes de la medida en macOS (V4),
porque el instalador lo copia.
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-17.

## ADR-027 — El texto para HN y Reddit, el martes 27; la puerta, el martes 24 de noviembre (2026-10-17, autor)

**Contexto:** el 25 de octubre es domingo. El fin de semana, HN y Reddit tienen menos tráfico, y el público del kit
lee de lunes a viernes; no se ha medido, porque las sesiones no buscan en la web. ADR-003 fija el 25 para publicar
y ADR-005 cuenta cuatro semanas desde la publicación.
**Decisión:**
* El repositorio se abre el domingo 25, como dice ADR-003.
* El texto para HN y Reddit (V9) sale el martes 27 hacia las 14:00 de Madrid, las 9:00 de Nueva York: esa semana
  Europa ya ha cambiado de hora y Estados Unidos no.
* Las cuatro semanas de la señal (ADR-005) se cuentan desde el texto: cuenta lo que llegue hasta el martes 24 de
  noviembre a las 23:59, hora de Madrid, y la puerta pasa a ese día.
* Los dos días no son margen de trabajo: ADR-004 sigue en vigor.

**Consecuencias:** cambian §1, §3, §4, §5 y V9 del ROADMAP (ADR-017). Se decide antes de tener datos de la
ventana, así que no es un reencuadre.
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-17.

## ADR-028 — La instalación, en un solo bloque que se pega; la orden con pantalla, en la v0.2 (2026-10-18, autor)

**Contexto:** en el intento 4 de la prueba en limpio, como en el 2, se copiaron tal cual las rutas del ejemplo de
`INSTALL.md`. El aviso que las marcaba como de ejemplo estaba en prosa. Además, el paso 1 empezaba en `~/src`, que
puede no existir. El autor propuso una sola orden, con una pequeña interfaz de instalación.
**Decisión:**
* `INSTALL.md` instala con un solo bloque que se pega desde la raíz del repositorio, sin nada que editar:
  * saca la ruta del repositorio de `git rev-parse`;
  * clona Actuarii al lado;
  * crea y activa el entorno fuera del repositorio;
  * ejecuta el instalador, cuyas preguntas son la interfaz.

  Cada paso va unido al siguiente con `&&`, así que el bloque se para en el primer fallo. El instalador no cambia.
* La medida en macOS (V4) se repite con la enmienda §4e de `docs/design/PRUEBA_EN_LIMPIO.md`.
* Una orden única con pantalla propia, sea un plugin de Claude Code o un programa de arranque, es una función nueva:
  va a la v0.2 (ADR-004). Un `curl … | sh` no se usa: es mala primera impresión para un kit de trazabilidad.

**Consecuencias:** la sección de instalación del README usa el mismo bloque. Cambia la línea «Fuera de la v0.1» del
ROADMAP (ADR-017).
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-029 — El instalador nombra el destino en la primera pregunta, antes de escribir (2026-10-18, autor)

**Contexto:** en la medida en macOS (intento 5), el bloque de `INSTALL.md` instaló el kit en el repositorio de trabajo
del autor: la terminal estaba allí, y el bloque instala donde está la terminal (ADR-028). El instalador dice dónde
instala (`installing into …`) solo en el informe, después de escribir. Se deshizo sin pérdida, porque el instalador
solo escribe ficheros nuevos y solo commitea los suyos.
**Decisión:**
* En una ejecución que pregunta, la pregunta de qué más gobernar empieza con una línea que nombra el destino y dice
  que no se escribe nada hasta responder y que Ctrl-C para ahí. No se añade ninguna pregunta.
* Como las demás preguntas, solo se escribe cuando la entrada estándar es un terminal. Con `--govern`, `--no-input`
  o `--dry-run` no hay pregunta y nada cambia.
* Va en un contrato al implementador (`docs/design/DESTINO_NOMBRADO.contrato.json`). ADR-004 lo admite, porque
  responde a un fallo real.

**Consecuencias:** `INSTALL.md` lo dice en la sección de las preguntas. La medida V4 no se repite: la línea añade una
lectura, no un paso.
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-030 — El caso real del README, en noticias v3: los dos defectos del clasificador (2026-10-18, autor)

**Contexto:** V6 pedía el caso de Traianus, con sus commits. Un caso nuevo en Traianus choca con ADR-004, y el del 5
de octubre es de antes de la v0.1: no tiene motivos ni acta en git. `noticias` (AI-Papers-Engine) es público, con
AGPL-3.0, y su rama `v3-exp` tiene trabajo real ajeno al kit. El caso real de la prueba en limpio (2026-10-12)
encontró dos defectos del clasificador léxico, `explorations/v3/scripts/classify_method_family.py`, y siguen ahí:
* la familia `gan` se cuenta dentro de palabras como `organization`, porque las claves se buscan como subcadenas;
* un texto con `diffusion transformer` empata siempre entre `diffusion` y `diffusion_transformer_or_hybrid`, y sale
  `other`.

**Decisión:**
* El caso real del README es arreglar esos dos defectos, con los tests primero, con la v0.1 tal como se publica.
* Se hace en un clon limpio de `origin/v3-exp`, con `explorations/v3/**` gobernado.
* El plan se escribe antes de hacerlo (`docs/design/PRUEBA_EN_LIMPIO.md` §4f), y el README cuenta lo que pase, salga
  como salga.
* El caso de Traianus queda para cuando se abra su repositorio.

**Consecuencias:** cambia V6 del ROADMAP (ADR-017): el caso es este, y sigue siendo lo primero que se recorta. La
copia de trabajo del autor no se usa: tiene el `.env` y notas privadas sin commitear.
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-031 — La denegación de `python3 -m pytest` nombra `pytest` (2026-10-18, autor)

**Contexto:** en el caso real (ADR-030), el agente lanzó tres veces `python3 -m pytest` y no probó `pytest` hasta
que la persona se lo dijo. La regla es correcta: el perímetro deniega `python3 -m` y permite `pytest`. Pero esa
denegación es una regla `deny` de Claude Code, con su mensaje genérico, y en el destino nada dice que los tests se
ejecutan con `pytest`. El hook de `Bash` del kit no mira `-m`. La documentación de Claude Code
(`code.claude.com/docs/en/hooks`, leída el 2026-10-18) dice que las reglas de permisos se evalúan sobre lo que
devuelve el hook `PreToolUse`, y que el motivo de su denegación se le muestra al agente: el hook actúa antes que la
regla `deny`.
**Decisión:**
* El hook de `Bash` (`tools/hooks/deny_python_escapes.py`) gana una regla, R7. Deniega `pytest` lanzado a través de
  un intérprete que cubre el shim (`python3 -m pytest`) y nombra la orden que vale: `pytest`, por su propio punto de
  entrada, con los mismos argumentos.
* El anuncio de la sesión gana una línea: los tests se ejecutan con `pytest` por su propio punto de entrada, y
  `python3 -m` y `python3 -c` se deniegan.
* La regla `deny` del perímetro no cambia: sigue denegando lo que el hook no reconozca.
* Va en un contrato al implementador (`docs/design/PYTEST_NOMBRADO.contrato.json`). ADR-004 lo admite, porque
  responde a un fallo real.

**Consecuencias:** el instalador copia el hook y el anuncio nuevos a los destinos. El README cierra el caso real
con el commit del arreglo.
**Sustituye a:** —
**Fuente:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-032 — The published tree is in English; the history stays as it is (2026-10-18, author)

**Context:** the repository opens on 25 October. The kit, its tests and the reference documents (README, INSTALL,
AGENTS, agents and skills) are in English. `docs/`, about 6,400 lines, and the agent's memory are in Spanish, and so
are the messages of the 329 commits. The author decided that the project cannot be published in Spanish, and that
the documents need edits for a reader from outside.
**Decision:**
* Every document of the published tree is translated into English, and edited for a reader from outside. The work
  goes in this order, so that it can be cut:
  1. what the README links: `CASES.md`, `PRUEBA_EN_LIMPIO.md`, `COSTE.md`, `ENTORNO_PROPIO.md`, `SANDBOX.md` and
     `ROADMAP.md`;
  2. this register, `DECISIONES.md`;
  3. the other records: `DEVLOG.md`, `PLAN.md`, `ESTADO.md`, the audit guidelines, `PROCESO.md`, `PRIOR_ART.md`,
     `ARRANQUE_PUERTAS.md`, `RECIBO_CONTENIDO.md`, the memory and the contracts.
* What is not translated by 25 October leaves the tree; the history keeps it in Spanish.
* The git history is not rewritten. Rewriting it would change every hash, including those the README, the clean-room
  results and the development log cite as evidence. The README says that the project was written in Spanish up to
  v0.1.
* From now on the repository's documents are written in English: the development log, the status, new decisions and
  the memory. The conversation with Claude may stay in Spanish.
* File names stay as they are: tests, the CI, `CLAUDE.md` and `opencode.jsonc` cite them.
* A translated record keeps its dates and what it said then. Where it describes something that has since changed, it
  says so in a dated note that names what replaced it.

**Consequences:** V6 and V7 of the ROADMAP change (ADR-017). Entries of this register written before this one keep
their meaning once translated; what each one decided does not change.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-033 — The published tree is shortened, document by document (2026-10-18, author)

**Context:** ADR-032 translates every document of the tree. They are about 6,400 lines of records written for the
work itself, against a kit of about 30 files. A reader from outside will not read most of them, and translating them
all competes with the launch. The author agreed that the tree should be shortened.
**Decision:**
* The published tree is shortened. The author reviews each document with Claude, and each one either stays
  (translated), is condensed (translated, keeping what a reader from outside needs), or leaves the tree. The history
  keeps every one, in Spanish.
* Claude's proposal is the starting point of that review, not a decision:
  * stays: the README, `INSTALL.md`, `AGENTS.md` and `ROADMAP.md`;
  * condensed: the "Resumen" of `CASES.md` with a link to each case, the results of `PRUEBA_EN_LIMPIO.md`, and
    `COSTE.md`, `ENTORNO_PROPIO.md` and `SANDBOX.md`, reduced to what the README needs;
  * condensed as a register: the decisions of `DECISIONES.md`, one line of decision and one of reason each;
  * out of the tree: the DEVLOG, the PLAN, the audit guidelines, `PROCESO.md`, `PRIOR_ART.md`, the contracts and
    the other designs.
* What the code, the tests, the CI, `CLAUDE.md` or `opencode.jsonc` need stays wherever the review puts it, or the
  review says what changes with it.
* When the review reaches `ROADMAP.md`, the author stops to work on v0.2 and research it; ideas or changes that come
  out of it go to this register.

**Consequences:** the first point of ADR-032 changes: not every document is translated, only those that stay or are
condensed. The rest of ADR-032 holds: English from now on, the history as it is, dated notes in the records that
stay. V10 of the ROADMAP is checked on the shortened tree.
**Supersedes:** ADR-032, in part (its first point).
**Source:** `docs/DEVLOG.md`, 2026-10-18.
