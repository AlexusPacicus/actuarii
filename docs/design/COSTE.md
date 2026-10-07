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

## 4. Resultados

(Se añaden después de medir.)
