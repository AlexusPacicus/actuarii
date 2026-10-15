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
