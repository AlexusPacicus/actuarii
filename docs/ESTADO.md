# Actuarii — estado

Lo que una sesión nueva necesita saber, y nada más. Se actualiza al cerrar cada sesión, junto con la entrada
del `docs/DEVLOG.md`. La historia y el razonamiento de cada decisión están en `docs/PLAN.md`, que se lee
cuando hace falta y no se carga en cada sesión (autor, 2026-10-14). Los criterios de la v0.1, la señal, la
puerta del 22 de noviembre y la v0.2 están en `docs/ROADMAP.md`.

Actualizado: 2026-10-14, noche.

## La v0.1

* **Qué es:** actas de trabajo para agentes de código. La frase del README: «Work records for coding agents.
  Every action leaves a record that it happened, and why. Built for settings where traceability comes
  first.»
* **Qué no es:** una frontera de seguridad frente a un agente adversario. Eso es la v0.2, con su entorno
  propio (`docs/design/ENTORNO_PROPIO.md`). AGENTS.md §9 declara lo que la v0.1 no cubre.
* **Publicación:** el 25 de octubre, esté como esté. El repositorio es privado hasta entonces.
* **Señal de éxito, comprometida:** en las cuatro semanas siguientes, 5 personas ajenas que lo instalan o
  abren una issue, o una conversación de trabajo. Si no llega, se revisa con datos, sin reencuadrar. Cómo se
  cuenta, en el ROADMAP §3.

## Dónde estamos

* Hechos y verificados:
  * el motivo (`Rationale`) en cada propuesta;
  * el perímetro de permisos;
  * A20, A31 y A34;
  * AGENTS.md v2.2.0;
  * cada ruta gobernada con su `denyWrite`, sin exenciones, comprobado con una sonda;
  * el ROADMAP, con D1–D7 decididas;
  * la historia reescrita sin la información personal y con el correo *noreply*, en un repositorio nuevo
    de GitHub (V8).

  Suite en verde (3278). El detalle, con sus commits, en el DEVLOG.
* Pendiente, en este orden (cada criterio, con su corte, en el ROADMAP):
  1. **El instalador en una orden (V2),** en dos contratos. El primero lleva lo que el kit necesita en el
     destino: el perímetro, `includeGitInstructions`, el `denyWrite` y `pydantic`. El segundo, las preguntas
     y el acta en git. Reescribe `INSTALL.md`.
  2. **El acta en git (V3, D1),** en el segundo contrato. Un hook `commit-msg` añade los motivos de los recibos
     y dice si el contenido del commit coincide con el que dejaron las escrituras con recibo. El resultado
     esperado lo calcula la puerta, que pasa a escribir en la base y deniega si no puede guardarlo.
  3. **La memoria automática de Claude Code, apagada (D5):** `autoMemoryEnabled: false`, con su test y la
     corrección de la línea de `.claude/memory/MEMORY.md` sobre la opción (c). Va en un contrato pequeño.
  4. **La medida en macOS (V4),** del autor, como tarde el domingo 18.
  5. **La tabla «Resumen» de `docs/adversarial-audit/CASES.md` (V5),** hasta A35. Pasa a ser la sección de
     límites del README.
  6. **El README en inglés (V6),** con su primer límite (A30, D3) y su marco (D6).
  7. **Lo publicado no contradice el kit (V7),** y el texto para HN y Reddit (V9).

## Calendario hasta el 25

| Cuándo | Qué |
|---|---|
| Miércoles 14 | El hueco de la memoria, el ROADMAP y la historia reescrita (hecho) |
| Jueves 15 y viernes 16 | El instalador con el acta en git; el README empieza el viernes |
| Sábado 17 y domingo 18 | El contrato de la memoria; la medida en macOS (el autor) |
| Lunes 19 | La tabla «Resumen» y la sección de límites |
| Martes 20 a jueves 22 | El README |
| Viernes 23 y sábado 24 | Lo publicado frente al kit, y el texto para HN y Reddit |
| Domingo 25 | Publicar |

## Decisiones vigentes

* Los criterios del ROADMAP no mueven la fecha del 25. Un cambio de criterio lo decide el autor y queda en el
  DEVLOG con su motivo.
* La seguridad frente a un agente adversario no es de esta versión. A19, A32, la opción (c) con A33 y A35
  pasan a la v0.2; A21, A23, A24, A25 y A28 quedan declarados en §9 sin corregir.
* Los campos de la propuesta se renombran con nombres llanos en la v0.2. Antes del lanzamiento solo se
  limpia la jerga de las descripciones y del README.
* Antes del lanzamiento no se hace nada de Traianus, ninguna mejora de gobernanza que no responda a un fallo
  real y ninguna función fuera del plan, salvo el acta en git.
* La distribución de la v0.1 es un instalador que copia el kit en `tools/` del destino; el plugin, en la
  v0.2.

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
* **Se commitea solo si `pytest` sale con 0,** comprobando su código de salida. Antes de una suite completa,
  se mira el espacio en disco.
* **Sin atribución a Claude** en commits ni PR. El correo de los commits es la dirección *noreply* de GitHub.
* **La historia se reescribió el 2026-10-14:** los hashes de antes ya no existen, y las citas de `docs/` están
  rehechas. El repositorio de GitHub es el nuevo, con la CI en verde; el viejo está borrado (autor,
  2026-10-14).
* **Python:** solo scripts commiteados, a través del shim; `pytest` por su propio punto de entrada.
* **El DEVLOG,** al cerrar cada sesión, con la fecha del reloj y no la de la conversación.
* **Las ideas que se salen del camino** se apuntan en el PLAN y esperan.
* **La memoria del agente** es la de `.claude/memory/`, bajo código, con un recibo por escritura. Se publica
  el 25: los recuerdos se escriben sabiéndolo. La memoria automática de Claude Code no se usa, y el contrato
  de D5 la apaga.

## Cómo empezar una sesión

1. Leer el anuncio de la sesión: el sandbox tiene que estar activo y el hook de integridad instalado.
2. Leer la última entrada del DEVLOG.
3. Seguir por el primer pendiente de la lista de arriba.
