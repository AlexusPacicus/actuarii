# Actuarii — hoja de ruta

Borrador de Claude del 2026-10-14, para que lo corrija el autor antes de commitearlo (decisión del autor,
2026-10-14). Sirve para dos cosas: cortar el alcance antes del 25 de octubre y que la revisión del 22 de
noviembre se haga contra algo escrito antes. Las propuestas de Claude en V2–V9 y en §3–§5 las aceptó el autor el
2026-10-14 (D7); lo que sigue abierto está en §6.

El porqué de cada decisión está en `docs/PLAN.md`; el trabajo de cada día, en `docs/ESTADO.md`. Después del
commit, un cambio de criterio lo decide el autor y se añade a `docs/DECISIONES.md` con su motivo. El 22 de noviembre este
documento solo se toca para anotar el resultado.

## 1. Tres fechas

| Cuándo | Qué |
|---|---|
| Domingo 25 de octubre | Se publica la v0.1, esté como esté (autor, 2026-10-06) |
| Del 26 de octubre al 22 de noviembre | La ventana de señal (§3) |
| Domingo 22 de noviembre | La puerta: se mira la señal y se decide si empieza la v0.2 (§4) |

## 2. La v0.1

**Qué es:** «Work records for coding agents. Every action leaves a record that it happened, and why. Built for
settings where traceability comes first.» **Qué no es:** una frontera frente a un agente adversario; eso es la
v0.2.

Un criterio que no se cumple el 25 no mueve la fecha. Cada uno dice cómo se comprueba, cuándo se corta y qué
pasa si no se cumple.

**V1. La suite, en verde.**
* Comprobación: `pytest` sale con 0 en macOS, y la CI de Linux está en verde, sobre el commit que se publica.
* Si no se cumple: se publica el último commit de `main` en verde.

**V2. La instalación en una orden.**
* Qué: `tools/install.py` deja el destino como este repositorio:
  * el validador con el motivo y el perímetro de permisos de AGENTS 7.1;
  * `includeGitInstructions: false`, sin el que `build --lock` no pone el candado;
  * un `denyWrite` por cada ruta gobernada;
  * los hooks `pre-commit` y `commit-msg` (V3);
  * `pydantic` comprobado en el intérprete con que arrancará el servidor, con permiso antes de instalarlo;
  * solo pregunta qué rutas gobernar y si hace el commit, y tiene un modo sin preguntas.

  `INSTALL.md` se reescribe, con el entorno fuera del repositorio.
* Comprobación: los tests del instalador y los pasos 1 a 4 de la prueba en limpio en la CI.
* Corte: viernes 16 por la noche.
* Si no se cumple: el primer contrato lleva lo que el kit necesita para funcionar en el destino
  (perímetro, `includeGitInstructions`, `denyWrite` y `pydantic`); el segundo, las preguntas y el
  `commit-msg`. Lo que no entre queda como paso a mano en `INSTALL.md`, y el README lo dice.

**V3. El acta en git.**
* Qué: un hook `commit-msg` añade al mensaje de cada commit, como *trailers*, los motivos de los recibos de sus
  ficheros gobernados, y dice si el contenido del commit coincide con el que dejaron esas escrituras (D1). Solo
  registra; no bloquea (autor, 2026-10-14).
* Comprobación: un test hace el commit de un fichero gobernado con recibo y encuentra su motivo en
  el mensaje; otro, el de un fichero cambiado sin recibo, encuentra que el mensaje lo dice.
* Corte: viernes 16, con el segundo contrato del instalador.
* Si no se cumple: la frase del README pierde «that it happened» y dice lo que queda: el motivo de
  cada escritura gobernada, en la base local.

**V4. Instalar en menos de 5 minutos.**
* Qué: la prueba en limpio de `docs/design/PRUEBA_EN_LIMPIO.md`, en macOS, con el instalador nuevo y su
  enmienda commiteada antes de medir. La última medida dio 612,8 s (2026-10-12).
* Comprobación: el hito 2 llega en menos de 300 s (regla de su §4).
* Corte: domingo 18. La hace el autor.
* Si no se cumple: el README da la cifra, y el autor decide con los tiempos por paso (regla de su §4).

**V5. Los límites, completos.**
* Qué: la tabla «Resumen» de `docs/adversarial-audit/CASES.md` cubre de A01 a A35 (hoy llega a A12), con lo
  corregido y su commit, lo declarado en AGENTS §9 y lo que pasa a la v0.2. Es la sección de límites del
  README.
* Comprobación: cada caso de `CASES.md` tiene su fila, y cada fila «declarado», su línea en §9.
* Corte: lunes 19.
* Si no se cumple: el README enlaza `CASES.md` y §9 tal como estén.

**V6. El README en inglés.**
* Qué, en este orden:
  * la frase y su primer límite (D3);
  * el problema (D6) y qué canal decide quién;
  * los límites (V5);
  * la instalación;
  * el coste por escritura gobernada, con su cifra (1875 ms de mediana, `docs/design/COSTE.md`);
  * lo que cae en la persona (`merge`, `switch`, borrar);
  * la v0.2 en una frase;
  * el caso de Traianus, con sus commits.
* Comprobación: cada cosa que el README dice que el kit hace cumplir nombra el test que lo
  comprueba; si no lo tiene, se quita.
* Corte: jueves 22.
* Si no se cumple: se recorta en este orden: primero el caso de Traianus (queda un enlace al
  DEVLOG), después la tabla de canales. La frase, los límites y la instalación no se recortan.

**V7. Nada de lo publicado contradice el kit.**
* Qué: fuera de los registros (DEVLOG, PLAN y contratos), ningún documento describe lo que ya no es así:
  * la exención de `.claude/**` en `docs/design/SANDBOX.md` §6 e `INSTALL.md`;
  * «Blind by construction» en `examples/traianus/skills/instrument-audit/SKILL.md`;
  * «5 Radicals» en `docs/` y `examples/`.
* Comprobación: una lectura de esos documentos, y un `grep` de las dos frases fuera de los registros que sale
  vacío.
* Corte: viernes 23.
* Si no se cumple: se publica, con una issue abierta en el propio repositorio por cada documento.

**V8. Antes de abrir el repositorio.**
* Qué:
  * la información personal que fijó el autor, fuera del árbol y de la historia de `main` (D2). Está en
    `docs/PLAN.md`, `docs/DEVLOG.md` y `docs/adversarial-audit/PAUTAS.md` desde `de8cabf`, y en
    `.claude/memory/autor.md`; la lista de términos no se guarda en el repositorio;
  * en `origin`, solo `main`.
* Comprobación: `git log -p main` no contiene los términos que fije el autor, y `git ls-remote --heads origin`
  lista solo `main`.
* Corte: sábado 24.
* Si no se cumple: es el único criterio que retrasa abrir el repositorio, porque lo publicado no se
  recoge. Decide el autor.

**V9. El texto para HN y Reddit.**
* Qué: un texto técnico corto en inglés, con las reglas de autopromoción de cada sitio revisadas antes.
* Corte: sábado 24.
* Si no se cumple: el repositorio se abre el 25 y el texto sale en la primera semana de la ventana.

**Fuera de la v0.1 (decidido):**
* A19, A32, la opción (c) con A33 y A35 pasan a la v0.2, declarados en §9. A21, A23, A24, A25 y A28 quedan
  declarados sin corregir (autor, 2026-10-14).
* Nada de Traianus, ninguna mejora de gobernanza que no responda a un fallo real y ninguna función nueva salvo
  el acta en git (autor, 2026-10-06 y 2026-10-14).
* Los nombres llanos de los campos, el plugin y la optimización del coste van a la v0.2.

## 3. La ventana de señal

**El compromiso (autor, 2026-10-07):** en las cuatro semanas siguientes a la publicación, éxito si al menos 5
personas ajenas lo instalan o abren una issue, o si nace una conversación de trabajo. Si no llega, se revisa con
datos, sin reencuadrar.

**Cómo se cuenta:**
* Se cuentan personas, no acciones: quien lo instala y además abre una issue cuenta una vez.
* **Ajena:** no es el autor ni alguien de su entorno cercano a quien le pidió que lo probara.
* **Lo instala:** hay algo que se puede enseñar: lo dice en una issue, un comentario o un mensaje, o tiene un
  repositorio público con `.actuarii.json`. Los clones, las visitas y las estrellas de GitHub no son
  instalaciones; se anotan como contexto.
* **Abre una issue:** una issue o un pull request de una cuenta que no es del autor y que no es spam.
* **Conversación de trabajo:** un intercambio sobre trabajo pagado o sobre una colaboración que nombra Actuarii,
  con respuesta de las dos partes. Basta una.
* **Dónde se anota:** GitHub solo guarda 14 días de tráfico. Cada domingo (1, 8, 15 y 22 de noviembre) va una
  línea en el DEVLOG con lo que cuenta, enlazado cuando es público, y el tráfico como contexto. De una
  conversación privada se anota que existe, sin nombres: el DEVLOG es público.
* **Hasta cuándo:** cuenta lo que llega hasta el domingo 22 de noviembre a las 23:59, hora de Madrid.

## 4. La puerta del 22 de noviembre

Se mira la cuenta del §3, con sus pruebas, y nada más.

* **Si se cumple:** empieza la v0.2 (§5). La fase 4, Traianus como memoria de agentes, necesita además su
  criterio de utilidad (`docs/PLAN.md`).
* **Si no se cumple:**
  * no empieza la v0.2 ni la fase 4;
  * el DEVLOG anota qué llegó, con las cifras, y por qué cree el autor que no llegó;
  * lo que venga después es un plan nuevo, con su propia señal escrita antes, no la continuación de este;
  * cuatro personas de cinco no cuentan como señal.

## 5. La v0.2

**Qué es:** el entorno aislado propio de `docs/design/ENTORNO_PROPIO.md`: el agente entero dentro, y las
puertas y un intermediario de escritura fuera. Su motivación es la que la v0.1 dejó de lado: que hace falta un
middleware para usar agentes de forma segura (autor, 2026-10-13). Empieza solo si se pasa la puerta.

**Criterios:**
* Las garantías E1–E9 (`ENTORNO_PROPIO.md` §3).
* La batería de su §8: cada caso de las dos auditorías que aplica, y los casos «Internet», sale como se espera,
  en Claude Code y en OpenCode.
* El coste: la mediana del tiempo añadido por escritura gobernada, por debajo de 1 s, con el método de
  `docs/design/COSTE.md` (en la v0.1, 1875 ms).
* La instalación: de cero en menos de 300 s, con el método de `docs/design/PRUEBA_EN_LIMPIO.md`.
* Los campos de la propuesta, con nombres llanos (autor, 2026-10-14).
* La regla de cada medida, commiteada antes de medir.

**Orden:** las fases v0.2-a a v0.2-e de `ENTORNO_PROPIO.md` §9, con las decisiones de su §10 tomadas antes del
prototipo.

**Fecha y alcance:** la fecha se fija el 22 de noviembre, con la regla de la v0.1: no se mueve, se
recorta alcance. De «Ideas para la v0.2» del PLAN entra solo lo que haga falta para un criterio de aquí.

## 6. Decisiones pendientes

Cada una lleva la recomendación de Claude y, si ya está tomada, la decisión del autor. Todas están tomadas y
pasaron a `docs/DECISIONES.md`: D1 es ADR-016; D2, ADR-020; D3 y D6, ADR-018; D4, ADR-019; D5, ADR-010, y D7,
ADR-017.

* **D1. Que el acta registre la escritura, no solo la petición.**
  * El problema: el rastro guarda hashes, no el texto. Un `commit-msg` solo puede emparejar recibos y commit
    por fichero y por hora, y entrarían recibos de escrituras que no se hicieron o que se deshicieron. Es lo
    que criticó la revisión de otro agente.
  * **Decidido (autor, 2026-10-14):** el acta compara el contenido del commit con el que dejaron las escrituras
    con recibo y lo dice en el *trailer* («coincide» o «cambió fuera del canal»). El cálculo va dentro de la
    puerta que ya corre antes de cada escritura, sin proceso nuevo; se descarta un hook `PostToolUse`, que
    añadiría unos 250 ms por escritura (`COSTE.md` §4).
  * Consecuencia para el contrato: la puerta deja de abrir la base solo para leer. **Decidido (autor,
    2026-10-14):** si no puede guardar el resultado esperado, deniega la escritura, como el validador sin acta.
* **D2. La historia.**
  * Quitar la información personal de la historia cambia el hash de casi todos los commits desde el 6 de
    octubre. El DEVLOG, los contratos y el caso de Traianus del README citan hashes.
  * **Decidido (autor, 2026-10-14):** se quita lo personal, también de la historia; la lista la tiene el autor.
  * Antes del viernes 16, cuando empieza el README. Con el mapa de commits de `git filter-repo` se rehacen las
    citas, y se comprueba que cada hash citado existe. GitHub puede seguir sirviendo los commits viejos por su
    hash: la historia reescrita se sube a un repositorio nuevo y el viejo se borra.
* **D3. El primer límite del README (A30).** **Decidido (autor, 2026-10-14):** va justo debajo de la frase. Solo
  deja acta lo que pasa por el canal gobernado; lo que hace `Bash` y lo que va a rutas no gobernadas, no.
* **D4. Contar A33 y A34 a Anthropic antes de publicar.**
  * **Decidido (autor, 2026-10-14):** no se cuenta. A34 es comportamiento documentado, y Claude Code ya tiene su
    interruptor (`omitClaudeMd`, desde la 2.1.271). A33 se sigue de su diseño documentado: el sandbox cubre
    `Bash`, y las herramientas de ficheros pasan por sus avisos de permiso.
  * El README los describe con exactitud y con la versión, como límites del kit y no como fallos de Claude
    Code.
  * Se reconsidera si una prueba muestra que Claude Code escribe sin preguntar donde dice que pregunta.
* **D5. La memoria normal de Claude Code en Actuarii.**
  * Sin la opción (c), la herramienta `Write` sigue llegando a `~/.claude/projects/…/memory/`.
  * `.claude/memory/MEMORY.md` todavía dice que la opción (c) la deniega.
  * Claude Code le dice al agente que escriba allí su memoria; lo único que lo impide es una línea de
    `CLAUDE.md`, es decir, una instrucción y no una regla.
  * La documentación de Claude Code (code.claude.com/docs/en/memory, leída el 2026-10-14) da dos ajustes de
    proyecto: `autoMemoryEnabled: false` apaga la memoria automática, y `autoMemoryDirectory` la lleva a otro
    directorio, con una ruta absoluta o que empiece por `~/`.
  * Comprobado el 2026-10-14: la memoria normal de Actuarii está vacía desde el 5 de octubre. De 31
    transcripciones de subagentes, ninguna recibió la instrucción de la memoria automática, y 6 recibieron el
    índice de `.claude/memory/` a través de `CLAUDE.md`. El revisor ciego no recibe ninguna de las dos
    (`omitClaudeMd`), aunque en Actuarii no se ha ejecutado nunca.
  * **Decidido (autor, 2026-10-14):** `autoMemoryEnabled: false` en todo el proyecto, no solo para las
    revisiones ciegas, que ya están cubiertas. Va en un contrato pequeño, después del instalador, con su test y
    la corrección de la línea falsa de `.claude/memory/MEMORY.md`. La memoria bajo código se publica el 25, y
    los recuerdos se escriben sabiéndolo.
* **D6. El marco del README.**
  * El párrafo de von Neumann del PLAN está escrito en clave de seguridad.
  * **Decidido (autor, 2026-10-14):** el marco explica por qué las reglas viven fuera del modelo, y nombra la
    seguridad frente a un agente adversario como lo que trae la v0.2, no la v0.1.
* **D7. Las propuestas de Claude en V2–V9 y en §3–§5.** **Aceptadas (autor, 2026-10-14).**
