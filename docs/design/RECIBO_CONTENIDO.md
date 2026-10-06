# F4: el recibo ata el contenido (diseño, borrador para el autor)

Borrador de Claude, 2026-10-07. Corrige A04 (el recibo no ata lo que se escribe) y A05 (matriz léxica).
Decisiones del autor del 2026-10-07: A04 se corrige en la v0.1, y la matriz léxica se elimina. Este
documento se commitea, el autor lo corrige, y solo entonces se implementa.

## 1. La idea

Un recibo deja de significar «este fichero, durante 15 minutos» y pasa a significar **«este cambio
exacto en este fichero»**. Los 5 Radicales ya lo decían: `Topological_Grounding` es la cita literal
del fichero e `Implementation_Block` el texto exacto que se inserta. El validador solo tiene que
recordarlo, y la puerta, comprobarlo.

Cada herramienta de escritura se corresponde con una propuesta así:

| Herramienta | `Topological_Grounding` | `Implementation_Block` |
|---|---|---|
| `Edit` | `old_string` | `new_string` |
| `MultiEdit` | `old_string` de cada edición | `new_string` de cada edición (un recibo por edición) |
| `Write` | una cita del fichero si existe; vacía si es nuevo (como ya exige F3) | `content` entero |
| `NotebookEdit` | no se ata (la entrada solo trae `cell_id`) | `new_source` |
| Clase 3 (herramientas desconocidas, F2) | — | — (se mantiene el recibo por fichero) |

## 2. El recibo

* **Dónde:** una tabla nueva, `receipts`, en la misma base de auditoría, que se escribe solo con
  `EXECUTE_SAFE`. Columnas: `case_id`, `timestamp`, `target_file`, `grounding_sha256` y
  `block_sha256`. `audit_log` no cambia (sigue siendo append-only y sigue registrando cada decisión).
* **Qué se compara:** el SHA-256 de los bytes UTF-8 exactos, saltos de línea incluidos. Nada se
  normaliza: un espacio de más es otro contenido.
* **Uso:** un recibo no se consume. Repetir el mismo cambio dentro de la ventana es inofensivo:
  escribe lo mismo.

## 3. La puerta

* `Edit`: permite si hay un recibo vigente para ese fichero con `grounding_sha256 = sha(old_string)`
  y `block_sha256 = sha(new_string)`.
* `MultiEdit`: cada edición necesita su recibo; basta con que falte uno para denegar.
* `Write`: permite si hay un recibo vigente con `block_sha256 = sha(content)`.
* `NotebookEdit`: permite si hay un recibo vigente con `block_sha256 = sha(new_source)`.
* Clase 3: como hoy, recibo por fichero.
* La denegación dice qué falta: «no hay un recibo para este cambio» y, si lo hay para el fichero pero
  con otro contenido, lo dice también. Así un agente del perfil A entiende que resumió en vez de
  copiar.
* `replace_all` de `Edit` no se ata: solo decide cuántas veces se aplica el mismo cambio aprobado.
  Se declara.

## 4. La comprobación de primitivas (sustituye a la matriz léxica)

* **Solo ficheros Python** (`.py`). En los demás no hay comprobación; se declara.
* **Sobre el resultado, no sobre el fragmento.** Un `new_string` suelto no suele ser Python válido.
  El validador aplica el cambio al fichero actual (sustituye la cita por el bloque, o toma el bloque
  entero si es un `Write`) y analiza el fichero resultante con `ast`.
* **Solo lo que el cambio introduce.** Se comparan las primitivas del fichero antes y después, y se
  deniega solo lo nuevo. Así `tools/audit/run_process.py`, el módulo designado que ya usa
  `subprocess`, se puede seguir editando sin abrir una excepción en la configuración.
* **Qué es una primitiva:**
  * importar `subprocess`, `socket`, `urllib`, `http`, `ftplib`, `telnetlib`, `xmlrpc`, `webbrowser`,
    `importlib`, `ctypes` o `pty`, y los módulos de terceros de la matriz actual (`requests`,
    `httpx`, `aiohttp`, `urllib3`);
  * acceder a `os.system`, `os.popen`, `os.exec*`, `os.spawn*`, `os.fork`;
  * llamar a `__import__`, `eval`, `exec` o `compile`, que es como se esquiva un import por su nombre
    (A05).
* **Si el resultado no es Python válido:** `SYNTAX_ERROR` (el valor de `Safety_Abort` que ya existe).
* **Límite declarado:** es una lista negra sobre el árbol sintáctico; frena al perfil A. El perfil B
  tiene otros caminos (`pickle`, extensiones nativas). No es un sandbox.

## 5. Lo que cambia para el agente

* Cada escritura gobernada necesita su propuesta con el texto literal: la cita es el `old_string` y el
  bloque el `new_string`. En la práctica la propuesta repite los argumentos del `Edit`.
* Cuesta tokens: un `Write` de un fichero grande lleva el fichero entero dos veces. Conviene preferir
  `Edit`.
* Se actualizan `AGENTS.md` (§2), la skill `boundary-validator` y la plantilla `implementer`.

## 6. El verificador en el commit (decisión del autor)

Es el punto único por el que pasan todas las escrituras, `Bash` incluido (ver la conversación del
2026-10-07 sobre F2).

* **Cómo:**
  * un hook `PostToolUse` anota el SHA-256 del fichero entero tras cada escritura con recibo;
  * un `pre-commit` comprueba que cada fichero gobernado que se va a commitear tiene ese hash;
  * una escritura por `Bash` deja un hash que no cuadra, y el commit se bloquea.
* **Límites:**
  * `git commit --no-verify` lo salta; habría que denegarlo en el perímetro (`ask` hoy);
  * la CI no lo puede comprobar, porque el rastro es local (`.data/`).
* **Tamaño:** un hook, un script de `pre-commit` y su instalación.
* **Propuesta de Claude:** v0.2, para que la v0.1 no crezca. Pero, si F4 sale en un día, cabe en la
  v0.1 y cierra el límite declarado más importante (las escrituras por `Bash`). Decide el autor.

## 7. Cómo se implementa

* **F4a, el recibo de contenido:**
  * la tabla `receipts`;
  * el validador guarda los hashes;
  * la puerta los compara para `Edit`, `MultiEdit`, `Write` y `NotebookEdit`.
* **F4b, las primitivas por `ast`:** sustituyen a `FORBIDDEN_MATRIX`.
* **Documentos (Claude):** `AGENTS.md`, la skill, la plantilla `implementer` y `PROCESO.md`.
* **F4c, el verificador en el commit,** solo si el autor lo mete en la v0.1.

Cada parte por contrato, con los tests primero. El servidor MCP de la sesión en curso sigue con el
código anterior hasta que se reinicie: el cambio se nota en la sesión siguiente.
