# Actuarii — estado

Lo que una sesión nueva necesita saber, y nada más. Se actualiza al cerrar cada sesión, junto con la entrada
del `docs/DEVLOG.md`. La historia y el razonamiento de cada decisión están en `docs/PLAN.md`, que se lee
cuando hace falta y no se carga en cada sesión (autor, 2026-10-14). Los criterios de la v0.1, la señal, la
puerta del 24 de noviembre y la v0.2 están en `docs/ROADMAP.md`, y las decisiones, en `docs/DECISIONES.md`.

Actualizado: 2026-10-17, tarde.

## La v0.1

* **Qué es:** actas de trabajo para agentes de código. La frase del README: «Work records for coding agents.
  Every action leaves a record that it happened, and why. Built for settings where traceability comes
  first.»
* **Qué no es:** una frontera de seguridad frente a un agente adversario. Eso es la v0.2, con su entorno
  propio (`docs/design/ENTORNO_PROPIO.md`). AGENTS.md §9 declara lo que la v0.1 no cubre.
* **Publicación:** el repositorio se abre el 25 de octubre, esté como esté, y es privado hasta entonces. El texto
  para HN y Reddit sale el martes 27 hacia las 14:00 de Madrid (ADR-027).
* **Señal de éxito, comprometida:** en las cuatro semanas desde el texto, hasta el martes 24 de noviembre, 5
  personas ajenas que lo instalan o abren una issue, o una conversación de trabajo. Si no llega, se revisa con
  datos, sin reencuadrar. Cómo se cuenta, en el ROADMAP §3.

## Dónde estamos

* Hechos y verificados:
  * el motivo (`Rationale`) en cada propuesta;
  * el perímetro de permisos, sin el comodín `Bash` de `ask` y con la lista ampliada (ADR-022), comprobado con
    la sonda;
  * la puerta con los textos largos (ADR-024);
  * el instalador en una orden (V2): el perímetro, `includeGitInstructions`, la comprobación de `pydantic`, las
    preguntas (qué más gobernar, `pip` con permiso y el commit), `--no-input` e `INSTALL.md` reescrito;
  * el acta en git (V3, ADR-016): la puerta guarda lo que deja cada escritura y el `commit-msg` lo compara con el
    commit; instalado en este repositorio, con su primera acta real en `ba6a120`;
  * la memoria automática de Claude Code, apagada en este repositorio (D5, ADR-010), con su test; el instalador no
    la toca en los destinos;
  * A20, A31 y A34;
  * AGENTS.md v2.3.0;
  * cada ruta gobernada con su `denyWrite`, sin exenciones, comprobado con una sonda;
  * el ROADMAP, con D1–D7 decididas;
  * la historia reescrita sin la información personal y con el correo *noreply*, en un repositorio nuevo
    de GitHub (V8);
  * la enmienda §4d de `docs/design/PRUEBA_EN_LIMPIO.md`, para medir con la instalación en una orden (`abb0d83`);
  * el primer borrador del README (V6), en la rama `v01/readme`, sin push;
  * el push de `main` del 16: `origin/main` en `2efa73a`;
  * los límites, por problemas (ADR-026), y el texto para HN y Reddit, el martes 27, con la puerta el 24 de
    noviembre (ADR-027).

  Suite en verde (3681). El detalle, con sus commits, en el DEVLOG.
* Pendiente, en este orden (cada criterio, con su corte, en el ROADMAP):
  1. **La medida en macOS (V4),** del autor, como tarde el domingo 18, con un clon nuevo de `main` desde GitHub y
     el método de §4d. Hasta entonces no se tocan `INSTALL.md`, `tools/install.py` ni `AGENTS.md`, que la medida
     lee o instala.
  2. **Los límites, por problemas (V5, ADR-026):** la tabla «Resumen» de `docs/adversarial-audit/CASES.md`, de
     problema a casos, y la sección de límites del README, con los ocho problemas y su motivo.
  3. **El README (V6),** en `v01/readme` hasta después de la medida: si llegara antes al clon, la medida leería otra
     guía (§1 de la prueba). Le faltan los límites (V5), la cifra de la instalación (V4) y el caso de Traianus: el
     autor dice cuál es y si sus commits son públicos.
  4. **Lo publicado no contradice el kit (V7),** y el texto para HN y Reddit (V9). V7 ya tiene su lista en el
     DEVLOG del 16 por la tarde, con la descripción de `pyproject.toml`; lo de `INSTALL.md`, después de la medida.
* Pendientes menores, sin fecha (DEVLOG, 2026-10-16): `**` sin `re.DOTALL` en `project_config`; la traza de Python
  de un `git` del instalador que pasa de 300 s.

## Calendario hasta el 27

| Cuándo | Qué |
|---|---|
| Miércoles 14 | El hueco de la memoria, el ROADMAP y la historia reescrita (hecho) |
| Jueves 15 y viernes 16 | El perímetro sin comodín, la puerta con los textos largos, los dos contratos del instalador, con el acta en git, el contrato de la memoria, la enmienda de la prueba en limpio y el borrador del README (hecho) |
| Sábado 17 y domingo 18 | La medida en macOS (el autor); ADR-026 y ADR-027 (hecho) |
| Lunes 19 | Los límites, por problemas |
| Martes 20 a jueves 22 | El README |
| Viernes 23 y sábado 24 | Lo publicado frente al kit, y el texto para HN y Reddit |
| Domingo 25 | Se abre el repositorio |
| Martes 27 | El texto en HN y Reddit, hacia las 14:00 de Madrid |

## Decisiones en vigor

Están en `docs/DECISIONES.md`, que solo se amplía. Hoy están en vigor de ADR-001 a ADR-027, salvo ADR-012 y
ADR-023, sustituidas por ADR-022 y ADR-024:

| ADR | Decisión |
|---|---|
| 001 | Nombre, licencia y relación con Traianus |
| 002 | Primero el kit; Traianus como memoria de agentes, solo con señal |
| 003 | Se publica el 25 de octubre, esté como esté |
| 004 | Lo que no se hace antes del lanzamiento |
| 005 | La señal de éxito |
| 006 | Repositorio privado hasta el 25 y un solo DEVLOG |
| 007 | La distribución de la v0.1: un instalador que copia el kit |
| 008 | La instalación en una orden, con el entorno fuera del repositorio |
| 009 | La v0.1 son actas de trabajo; la seguridad, en la v0.2 |
| 010 | La memoria del agente, bajo código; la automática de Claude Code, apagada |
| 011 | El motivo, obligatorio, y ningún recibo sin acta |
| 013 | Qué correcciones de la auditoría entran en la v0.1 |
| 014 | Los campos de la propuesta, con nombres llanos en la v0.2 |
| 015 | Un estado corto al abrir cada sesión, en lugar del PLAN |
| 016 | El acta en git |
| 017 | El ROADMAP |
| 018 | El README: su primer límite y su marco |
| 019 | A33 y A34 no se cuentan a Anthropic |
| 020 | La historia, sin lo personal y con el correo *noreply* |
| 021 | Las decisiones van en este registro, que solo se amplía |
| 022 | El perímetro de permisos, sin comodín y con la lista ampliada |
| 024 | Solo un nombre demasiado largo deja de ser una ruta |
| 025 | El acta en git y las preguntas del instalador, en dos contratos |
| 026 | Los límites, por problemas: gobernanza en la v0.1 y seguridad en la v0.2 |
| 027 | El texto para HN y Reddit, el martes 27; la puerta, el martes 24 de noviembre |

## Cómo se trabaja

* **El sandbox está activo:** `Bash` no escribe las rutas gobernadas ni sale a la red. Las órdenes de git
  que reescriben rutas gobernadas (`switch`, `merge`, `restore`) y el `push` las ejecuta el autor con `!`.
  Si `main` no se ha movido desde una rama, el chat la avanza sin reescribir el árbol (`git branch -f main
  <rama>` y `git switch main`).
* **El chat principal no escribe código.** El código y los tests van al subagente `implementer`, con
  `model: "sonnet"`, mediante un contrato JSON validado con `delegation_contract.py`. Después, el chat:
  * valida el informe;
  * pasa él mismo `verify_red_green.py`;
  * revisa el diff y comprueba a mano que solo toca los ficheros del contrato;
  * avanza `main`.
* **Un contrato lista todos los tests que le afectan** (AGENTS 6.4): los que construyen el formato, los que
  fijan el comportamiento que cambia y los que leen el código como texto.
* **El servidor MCP del validador ejecuta el código con el que arrancó la sesión.** Un cambio en el
  validador rige en la sesión siguiente. El esquema de la herramienta que muestra una sesión retomada puede
  ser una copia vieja: el motivo se envía igual.
* **El hook `commit-msg` está instalado en este repositorio:** cada commit que cambia un fichero gobernado lleva su
  acta (`Actuarii-Record`, `Actuarii-Rationale`). Un `changed outside the channel` inesperado se mira antes de seguir.
* **Se commitea solo si `pytest` sale con 0,** comprobando su código de salida. Antes de una suite completa,
  se mira el espacio en disco.
* **Sin atribución a Claude** en commits ni PR. El correo de los commits es la dirección *noreply* de GitHub.
* **La historia se reescribió el 2026-10-14:** los hashes de antes ya no existen, y las citas de `docs/` están
  rehechas. El repositorio de GitHub es el nuevo, con la CI en verde; el viejo está borrado (autor,
  2026-10-14).
* **Python:** solo scripts commiteados, a través del shim; `pytest` por su propio punto de entrada.
* **El DEVLOG,** al cerrar cada sesión, con la fecha del reloj y no la de la conversación.
* **Una decisión del autor** se añade al final de `docs/DECISIONES.md`, con el siguiente número, y se lista
  arriba. El DEVLOG la cita por su número, sin copiarla. Una entrada vieja no se toca: si se revisa, la nueva
  dice a cuál sustituye, y la vieja sale de la lista.
* **Hasta el 25** (recomendación de Claude, 2026-10-14), cada tarea responde a una pregunta: ¿acerca el instalador o el README? Si no, se apunta en el
  PLAN y espera. El único documento nuevo antes del lanzamiento es el README.
* **Las ideas que se salen del camino** se apuntan en el PLAN y esperan.
* **La memoria del agente** es la de `.claude/memory/`, bajo código, con un recibo por escritura. Se publica
  el 25: los recuerdos se escriben sabiéndolo. La memoria automática de Claude Code está apagada
  (`autoMemoryEnabled: false` en `.claude/settings.json`, ADR-010); si el contexto de una sesión trae su
  instrucción, no se sigue y se mira por qué.

## Cómo empezar una sesión

1. Leer el anuncio de la sesión: el sandbox tiene que estar activo y el hook de integridad instalado.
2. Leer la última entrada del DEVLOG.
3. Seguir por el primer pendiente de la lista de arriba.
