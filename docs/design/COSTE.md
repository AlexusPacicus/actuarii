# Coste de una escritura gobernada (método y regla, antes de medir)

Claude, 2026-10-07, con los umbrales del autor. Este documento se commitea antes de sacar ninguna cifra;
los resultados se añaden después, en §4, sin tocar §1 a §3.

## 1. Qué se mide

Una escritura gobernada (`Edit`, `MultiEdit`, `Write`) cuesta, además de la escritura:

1. **Tokens:** la propuesta para `validate_proposal` repite el texto del cambio (en un `Edit`, el
   `old_string` y el `new_string`; en un `Write`, el fichero entero).
2. **Tiempo del validador:** la llamada MCP a `validate_proposal`, ida y vuelta.
3. **Tiempo de los hooks:** los hooks `PreToolUse` de la escritura (`require_boundary_validation.py`
   y `require_contract_context.py`), un proceso de Python cada uno.

## 2. Cómo

* **Tokens y tiempo del validador:** de la transcripción de la sesión del 2026-10-07
  (`~/.claude/projects/-Users-test-Documents-Actuarii/*.jsonl`), con `jq`:
  * cada llamada a `validate_proposal` con su entrada y su respuesta;
  * sobrecoste de un `Edit`: caracteres de la entrada de `validate_proposal` entre caracteres de la
    entrada del `Edit` al que da el recibo (el siguiente `Edit` sobre el mismo fichero);
  * tiempo del validador: hora de la respuesta menos hora de la llamada.
  * Los tokens se estiman como caracteres entre 4: no hay contador exacto, y la razón entre propuesta
    y `Edit` no depende de esa constante.
* **Tiempo de los hooks:** cada orden de hook de `.claude/settings.json` que actúa en un `Edit`, 20
  veces, con una entrada fija: un `Edit` sobre un `.py` gobernado real con su recibo válido (el camino
  completo: configuración, rastro, cálculo del resultado y `ast`). Se cronometra con `perl` y
  `Time::HiRes`, dentro del sandbox, como corren en la sesión. Se toma la mediana de cada hook y se
  suman (cota superior: Claude Code puede lanzarlos en paralelo).

## 3. Regla de decisión (autor, 2026-10-07)

* **No se optimiza antes del lanzamiento** si se cumplen las dos:
  * la mediana del tiempo añadido por escritura (validador + hooks) es menor de **1 s**;
  * la mediana del sobrecoste en tokens de un `Edit` es menor de **3 veces** su propio tamaño.
* Si falla alguna, se escribe un diseño de optimización para la v0.2 y el README declara el coste
  con las cifras; la fecha del 25 de octubre no se mueve.
* Si lo que se dispara es el coste de los `Write` grandes, la acción es documentar en el README que
  se prefiera `Edit` (lo que ya dice la skill `boundary-validator`), no cambiar el kit.

## 4. Resultados (2026-10-07)

**Muestra:** 15 escrituras gobernadas de las transcripciones `9210c485` y `87a82f04`, cada una
emparejada con su recibo por el contenido exacto (el `new_string` o el `content` es el
`Implementation_Block`), sin duplicados (la sesión retomada repite la historia de la anterior): 13
`Edit` y 2 `Write`. Las llamadas al validador que fueron sondas, sin escritura detrás, quedan fuera.

| Medida | Valores (ordenados) | Mediana |
|---|---|---|
| Ida y vuelta del validador, ms | 189 204 208 440 446 493 1070 1378 1465 1557 1686 1741 1757 1984 2262 | **1378** |
| Hook `require_boundary_validation.py`, 20 veces, ms | mín. 245, máx. 354 | **254** |
| Hook `require_contract_context.py`, 20 veces, ms | mín. 237, máx. 259 | **243** |
| Sobrecoste en tokens de un `Edit` (caracteres de la propuesta / del `Edit`) | 1.01 1.01 1.02 1.03 1.03 1.05 1.06 1.08 1.09 1.09 1.12 1.21 1.26 | **1.06** |

**Aplicación de la regla (§3):**
* Tiempo añadido por escritura: 1378 + 254 + 243 = **1875 ms**, por encima de 1 s. **No se cumple.**
* Sobrecoste en tokens de un `Edit`: **1.06 veces**, por debajo de 3. Se cumple. Los dos `Write` de
  la muestra eran ficheros de una línea (razón 2.0 y 2.1, por los campos fijos de la propuesta).
* **Decisión, según la regla:** no se optimiza antes del lanzamiento; se escribe un diseño de
  optimización para la v0.2 y el README declara el coste con estas cifras.

**Desglose, fuera de la regla (no la cambia):**
* El servidor del validador, ejecutado aparte con 20 peticiones en un proceso: **4 ms** por petición;
  el arranque del servidor (435 ms) ocurre una vez por sesión. Casi toda la ida y vuelta de 1378 ms
  no es trabajo del kit sino del harness.
* La ida y vuelta es bimodal: 6 llamadas por debajo de 500 ms y 9 por encima de 1 s, sin relación con
  el tamaño de la propuesta (4676 caracteres en 204 ms, 244 en 1741 ms). La sesión estaba en modo
  automático; una hipótesis, sin comprobar, es que una parte de las llamadas pasa por la revisión
  del clasificador porque `validate_proposal` no está en `permissions.allow`.
* Cada hook es casi todo arranque de Python (unos 240 ms de los 250).
* La escritura misma, con sus hooks, tardó una mediana de 205 ms de llamada a resultado en la
  transcripción (los hooks pueden ir en paralelo).

**Candidatos para el diseño de la v0.2** (sin decidir): poner `validate_proposal` en
`permissions.allow` y medir de nuevo (si la hipótesis se confirma, es el grueso del coste); unir los
dos hooks de escritura en un solo proceso (unos 240 ms menos); arrancar Python con menos trabajo
(`-S`, `-I`) en los hooks.

## 5. Diseño de optimización para la v0.2

**Objetivo:** la mediana del tiempo añadido por escritura gobernada por debajo de 1 s, medida con el
mismo método (§2) y con la regla comprometida de nuevo antes de medir. Tres pasos, en este orden, y
cada uno medido por separado para saber cuánto aporta:

1. **El validador en `permissions.allow`.** Añadir `mcp__boundary-validator__validate_proposal` a la
   lista de permitidos de `.claude/settings.json` y su equivalente en `opencode.jsonc` (AGENTS 7.1 exige
   el mismo perímetro). No abre nada: la herramienta solo valida y anota en el rastro, que escribe el
   servidor. Comprueba la hipótesis del §4: si la ida y vuelta baja a la rama rápida (unos 200 ms), era
   la revisión del modo automático. Es una línea de configuración y un cambio en los tests del
   perímetro.
2. **Un solo proceso para los hooks de escritura.** Hoy `require_boundary_validation.py` y
   `require_contract_context.py` arrancan cada uno su Python para la misma escritura. Un único hook
   de entrada que importe los dos y los ejecute en orden, sin cambiar su lógica ni sus mensajes,
   ahorra un arranque (unos 240 ms). Siguiendo AGENTS 6.5: primero el hook nuevo, probado; después el
   cambio de `settings.json`; los dos antiguos se quedan como módulos.
3. **Arranque de Python más ligero en los hooks** (`-I`, `-S`, que el shim ya admite): menos trabajo al
   arrancar y, con `-I`, sin `PYTHONPATH` ni el directorio del usuario, que además es más seguro.
   Se mide antes de decidir; si no ahorra nada apreciable, no se hace.

**Alternativa a los pasos 2 y 3 (idea del autor, 2026-10-07): un proceso residente.** Levantar Python
una vez por sesión, la primera vez que hace falta, y mantenerlo vivo: los hooks pasan a ser clientes
mínimos (un `sh` que le pasa la entrada y devuelve su decisión), sin arrancar un intérprete en cada
llamada. Es generalizable: vale para todos los hooks, y para un proyecto que no sea de Python el kit
deja de costar un arranque de Python por escritura. Lo que hay que resolver antes:
* **Código viejo en marcha:** como el servidor MCP, el proceso ejecuta el código con el que arrancó;
  un cambio en una puerta exige reiniciarlo, y hoy los hooks se releen en cada llamada (AGENTS 6.5).
  Necesita detectar que su código cambió (por hash) y reiniciarse o denegar.
* **Sin proceso, se deniega:** si no responde, el cliente deniega; nunca se salta la puerta.
* **Canal privado:** un socket de Unix con permisos solo para el usuario. El sandbox no deja a `Bash`
  conectarse a sockets de Unix por defecto, así que el agente no puede hablarle ni suplantarlo; sí
  podría matarlo, y entonces todo se deniega (un bloqueo, no un hueco).
* **Medirlo** con el mismo método que los pasos 2 y 3 antes de elegir.

**Estimación** (a comprobar, no a dar por hecha): unos 200 ms de validador y unos 150 ms de hooks,
por debajo de 500 ms en total. **Fuera de este diseño:** quitar la llamada al validador (el recibo es
la garantía) o cachear recibos (rompería que el recibo ata un cambio exacto).
