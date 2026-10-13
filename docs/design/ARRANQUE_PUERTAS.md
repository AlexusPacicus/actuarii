# Lo que cargan las puertas al arrancar (A19, decisión revisada)

Escrito por Claude el 2026-10-13, antes del contrato de A19. Revisa, a petición del autor, la decisión
del 2026-10-12 (`docs/DEVLOG.md`, «Decidido»): los hooks llevan `-S`. Al revisarla salieron dos caminos
más del mismo tipo, A31 y A32, reproducidos a nivel de hook (§8). Aprobado por el autor el mismo día
(§9). Nada está aplicado todavía.

## 1. Por qué se revisa

* La decisión del 12 ponía `-I` en los hooks, y `-I` no impide A19:
  * `-I` equivale a `-E -s -P`: quita las variables `PYTHON*`, el `site` del usuario y el directorio del
    script.
  * `site.main()` sigue procesando los `.pth` del `site-packages` del intérprete y ejecutando
    `sitecustomize`. En el `site.py` de 3.11.6, `-I` solo se salta el autocompletado (línea 607), y
    `execsitecustomize()` se llama siempre (línea 609).
  * Solo `-S` evita `main()` (líneas 615-616): sin `site-packages`, sin `.pth` y sin `sitecustomize` ni
    `usercustomize`.
  * Ya lo decía el DEVLOG del 2026-10-10 (H1): «`-I` no lo impide y `-S` sí».
* `-S` cierra A19 para los hooks, pero no A31 ni A32, que entran en el mismo contrato.

## 2. A31: la raíz del repositorio va delante de la biblioteca estándar

Comprobado al leer el código y reproducido a nivel de hook (§8; `CASES.md`, A31).

* Las puertas que importan `tools.*` hacen `sys.path.insert(0, REPO_ROOT)`. Después importan módulos que
  cargan otros de la biblioteca estándar que todavía no estaban cargados:

  | Puerta (todas fuera del sandbox) | `insert(0, …)` | Módulos estándar que se cargan después |
  |---|---|---|
  | `tools/hooks/require_boundary_validation.py` | :70 | `sqlite3` (`hook_gate`), `dataclasses` → `inspect`, `ast`… (`project_config`), `ast` (`primitives`) |
  | `tools/hooks/require_contract_context.py` | :48 | `dataclasses` → `inspect`, `ast`… |
  | `tools/hooks/announce_governance.py` | :24 | `dataclasses`…, `subprocess` (`run_process`) |
  | `tools/git/commit_integrity.py` (la ejecuta la persona en cada `git commit`) | :34 | `dataclasses`…, `subprocess` |
  | `tools/boundary_validator/validator.py` (servidor MCP) | :11 | `logging`, `pydantic` y lo que `pydantic` importe |

* La raíz no está gobernada. Un `sqlite3.py`, un `dataclasses.py` o un directorio `pydantic/` se escriben
  ahí con `Write` sin recibo, o con `Bash` dentro del sandbox. La siguiente llamada a la puerta los importa
  en lugar del módulo estándar y los ejecuta fuera del sandbox. El módulo plantado puede cargar después el
  verdadero, y la puerta sigue funcionando como siempre.
* No depende de dónde esté el venv, y alcanza a `commit_integrity.py`, que corre en la terminal de la
  persona, sin sandbox.
* No alcanza a los módulos ya cargados antes del `insert` (`json`, `os`, `re`, `pathlib`, `typing`…) ni a
  los congelados en el intérprete.
* Perfil A: un destino con un `inspect.py` o un `logging.py` propio en la raíz rompe las puertas. Los
  `try` de los hooks lo convierten en denegación (falla cerrado), pero el validador no arranca.

## 3. A32: el intérprete de las puertas se busca en un `PATH` con directorios del repositorio

Probado y reproducido a nivel de hook (§8; `CASES.md`, A32).

* Claude Code lanza cada puerta con una orden (`python3 …`, `sh …`) que se busca en el `PATH` con que
  arrancó. Si en ese `PATH` hay un directorio del repositorio, lo que haya allí con ese nombre es la
  puerta. El caso típico es el `.venv` del proyecto activado en la terminal desde la que se abre Claude
  Code: el montaje de A19 en vivo (`which python3` → `.venv/bin/python3`).
* **Probado (2026-10-13, en Actuarii, con un fichero y un enlace inofensivos, retirados con `mv`):**
  `Bash` crea ficheros y enlaces en `.venv/bin` dentro del sandbox. `.venv/**` no está en `denyWrite`
  ni en `governed_paths`. `Write` también lo escribe sin recibo.
* Un `python3` cambiado en `.venv/bin` se ejecuta en cada puerta, fuera del sandbox, antes de que exista
  ningún intérprete de Python. **Ni `-I` ni `-S` sirven.** Lo mismo pasa con:
  * el `sh` de `session_python_gate.sh`;
  * el `git` que lanzan `announce_governance.py` y `commit_integrity.py`.
* `tools/git/pre-commit` busca `git` y `python3` en el `PATH` de la terminal de la persona. Con el
  `.venv` del repositorio activado, se ejecuta lo que el agente haya dejado allí.
* Va más allá del kit: con un directorio escribible por el agente al principio del `PATH`, cualquier
  orden que la persona teclee en esa terminal se puede suplantar. El kit no gobierna la terminal de la
  persona; solo puede evitar sus propias búsquedas y avisar (§6).

## 4. El principio

Una puerta corre fuera del sandbox, con todo el acceso de la persona. Ni su intérprete, ni el código que
carga, ni las órdenes que lanza pueden salir de un sitio que el agente alcance a escribir: ni con `Bash`
(lo impide el sandbox) ni con las herramientas de ficheros (lo impiden las puertas). La única entrada del
agente que una puerta lee es la que valida: la carga del hook o la propuesta.

## 5. Decisión propuesta

### 5.1 Un lanzador, con `/bin/sh` por ruta absoluta

* Lanzador nuevo, gobernado: `tools/hooks/launch.sh`.
  * Quita del `PATH` las entradas vacías o relativas, las que no resuelven a un directorio y las que,
    resueltas físicamente, caen dentro de la raíz del proyecto.
  * No quita los directorios temporales. Nadie pone en su `PATH` uno que el sandbox deje escribir, y
    quitarlos todos dejaría fuera los `tmp_path` de pytest en Linux. Se declara (§6).
  * Exporta el `PATH` limpio, para que lo hereden también `git` y los demás hijos.
  * Hace `exec python3 -I -S` sobre el hook que recibe como argumento. Solo acepta hooks de
    `tools/hooks/`.
* Las órdenes de hook pasan a `/bin/sh "$CLAUDE_PROJECT_DIR"/tools/hooks/launch.sh <hook>.py`. Por ruta
  absoluta, el propio `sh` no se busca en el `PATH`. `session_python_gate.sh` pasa a
  `/bin/sh "$CLAUDE_PROJECT_DIR"/tools/hooks/session_python_gate.sh`.
* `tools/git/pre-commit` limpia el `PATH` de la misma forma antes de llamar a `git` y a
  `python3 -I -S … commit_integrity.py`.
* El servidor MCP arranca igual: `/bin/sh` con un lanzador que hace `exec python3 -I`, sin `-S` (§5.3).
* `/bin/sh` existe en macOS y en Linux. En Windows nativo no hay sandbox y ya está declarado.

### 5.2 Hooks y `commit_integrity.py`: `-I -S`, y la raíz solo para importar `tools`

* Las puertas usan solo la biblioteca estándar (por eso importan con el Python 3.9 del sistema, AGENTS
  §9), así que `-S` no les quita nada. `-I` y `-S` existen en 3.9.
* La raíz entra en `sys.path` solo para `import tools`:
  * se pone la primera, se importa el paquete y se quita (si ya estaba, no se toca);
  * los submódulos del kit se cargan por `tools.__path__`, sin buscar en `sys.path`;
  * ningún otro import, estándar o de terceros, busca en la raíz, se haga cuando se haga;
  * un fichero de la raíz con el nombre de un módulo estándar deja de cargarse.
* **Por qué no al final:** el intérprete de esta máquina (pyenv 3.11.6) tiene en su `site-packages` un
  paquete `tools` de primer nivel, el de `deepcode_hku`. Con la raíz al final, el validador importaría
  ese `tools` en lugar del kit. Con `-S` los hooks no lo ven, pero el validador sí.
* Mismo patrón en `tools/install.py`, que la persona ejecuta fuera del sandbox desde el clon.

### 5.3 Validador: `-I` sin `-S`, con otro orden de arranque

* `-S` no sirve aquí:
  * el validador necesita `pydantic` del `site-packages`;
  * con `-S` ni siquiera se sabe cuál es: en un venv, `sys.prefix` lo fija `site.venv()` (línea 528),
    que entonces no corre;
  * reproducir esa lógica en el validador es frágil (builds de framework, `dist-packages` de Debian,
    conda).
* Por tanto, con un `site-packages` escribible, la carga se ejecuta antes que la primera línea del
  validador. **La defensa es dónde está el entorno, no una comprobación**: fuera del repositorio, que el
  sandbox no deja escribir a `Bash`, y fuera del alcance de las herramientas de ficheros (§6).
* Orden de arranque de `validator.py` cuando se ejecuta como programa:
  1. Solo biblioteca estándar.
  2. **Guarda:** si alguna entrada de `sys.path` cae dentro de `REPO_ROOT`, fuera del directorio del
     kit (`tools/`, gobernado), rehúsa arrancar y dice por qué. Lo que haya en esa entrada ya se ha
     ejecutado antes de esta línea, así que es una guarda de configuración, no una defensa. Falla
     cerrado: sin servidor no hay recibos.
  3. `logging` y `pydantic`, sin la raíz en `sys.path`.
  4. `import tools` con la raíz puesta solo para ese import (§5.2). Si `tools` no viene de
     `REPO_ROOT/tools` (por ejemplo, porque un `.pth` lo importó antes desde el `site-packages`), rehúsa.
  5. Los submódulos de `tools`.
* Importado como módulo (los tests), no comprueba nada al importarse y se comporta como hoy.

### 5.4 El entorno de Actuarii, fuera del repositorio (decidido)

* `INSTALL.md` deja una sola opción: un entorno propio de Actuarii fuera del repositorio. Se quita la del
  entorno del proyecto: tanto un `.venv` dentro como una instalación editable del proyecto meten en el
  camino del validador código que el agente escribe, y la guarda de §5.3 lo rechaza.
* El lanzador del servidor usa `$ACTUARII_PYTHON` si está definida. Tiene que ser una ruta absoluta
  fuera del repositorio; si no, rehúsa. Sin ella, usa el primer `python3` del `PATH` limpio. Así la
  persona puede trabajar con el entorno de su proyecto activado y el kit sigue usando el suyo. Lo fija el
  contrato del instalador en una orden.
* El instalador en una orden comprueba `pydantic==2.13.3` con el mismo intérprete y las mismas opciones
  con que arrancará el servidor (`-I`). Con ellas no cuenta un `pydantic` instalado con `pip --user`.

### 5.5 Lo que no cambia

* La lectura de `python_script_dirs` en el shim (`"$real" -I "$KIT/project_config.py"`): corre bajo
  `Bash`, dentro del sandbox; no es una salida.

## 6. Lo que queda

* **Las herramientas de ficheros fuera del repositorio: opción (c), decidida por el autor.**
  * La puerta deniega por defecto toda escritura de las herramientas de ficheros fuera de la raíz, con
    una lista de excepciones en `.actuarii.json`. Quedan con el mismo alcance que `Bash`.
  * Cierra, para esas herramientas, el entorno de Actuarii de fuera, `~/.zshrc` y `~/.claude/settings.json`.
    El kit deja aplicar en la sesión los cambios de los ajustes del usuario (`block_config_changes.py:7`).
  * Contrato aparte. Puntos que fija:
    * el nombre de la clave y si cambia la versión del esquema (`actuarii-config/1`);
    * qué hace el mínimo incorporado sin configuración (propuesta: denegar, como todo lo que no se puede
      verificar);
    * qué herramientas cuentan como escritura (la clasificación que ya tiene la puerta, F2);
    * los tests que construyen el formato de la configuración (AGENTS 6.4).
  * Coste: lo que Claude Code escribe fuera por su cuenta necesita una excepción declarada. Son los
    planes en `~/.claude/plans/`, la memoria en `~/.claude/projects/…/memory/` y el scratchpad. Decide el
    autor qué excepciones lleva este repositorio.
* **La terminal de la persona** (A32): con el `.venv` del repositorio activado, lo que se teclea se busca
  primero allí. Propuesta:
  * el anuncio avisa de cada directorio del `PATH` de Claude Code que cae dentro de la raíz sin su
    entrada en `denyWrite`, en el mismo cambio que la corrección de A24;
  * `INSTALL.md` recomienda `denyWrite` para el `.venv` de un proyecto que lo tenga dentro (sin red en
    el sandbox, el agente tampoco puede instalar paquetes en él);
  * se declara en §9.
* **Un directorio temporal en el `PATH`.** El lanzador no lo quita (§5.1). Si la persona pone en su
  `PATH` un directorio que el sandbox deja escribir a `Bash` (`/tmp/claude…`), se suplanta como uno del
  repositorio. Se declara.
* **El intérprete lo elige el estado del repositorio.** Con un gestor de versiones en el `PATH` (aquí,
  pyenv 2.6.12), un `.python-version` en la raíz, sin gobernar, cambia el intérprete de las puertas.
  pyenv solo deja elegir versiones instaladas, que quedan fuera del alcance del agente. Con §5.2, los
  hooks solo cargan su biblioteca estándar. Lo peor es un intérprete sin `pydantic`: el validador no
  arranca y las escrituras gobernadas se deniegan. Se declara.

## 7. Para el contrato

* **Tests que fijan las órdenes (AGENTS 6.4):**
  * comparan la orden entera: `test_config_change_hook.py:121`, `test_contract_context_hook.py:30-31`
    (y 673, 683-690), `test_write_gate_tools.py:268-270` y `test_python_gate_wiring.py:21-22` (y 57, 78 y
    las cargas de 109-160);
  * toman `shlex.split(command)[1]` como ruta del hook, que pasa a ser el lanzador:
    `test_hook_project_dir.py:32` y `test_hooks_without_shim.py:93`;
  * siguen solos: `test_installer.py` compara con el clon, y `test_config_perimeter.py` toma el último
    argumento. `.mcp.json` y `opencode.jsonc` cambian juntos (AGENTS 7.1 y 7.2).
* **Tests nuevos, rojos en la base.** Todos sobre un kit instalado en `tmp_path`, **nunca en la raíz
  real:** los hooks vivos de la sesión cargarían lo plantado.
  * Un venv con un `sitecustomize.py` testigo, primero en el `PATH`: ninguna orden de hook lo ejecuta.
  * Un `dataclasses.py` y un `sqlite3.py` testigos en la raíz: ni los hooks ni `commit_integrity.py` los
    cargan.
  * Un `python3`, un `sh` y un `git` falsos en un directorio de la raíz, primero en el `PATH`: ninguna
    orden de hook ni el `pre-commit` los ejecutan.
  * El validador rehúsa arrancar con una entrada de `sys.path` dentro de la raíz y con un `tools` que
    un `.pth` haya importado antes desde fuera del kit.
  * Con un paquete `tools` en su `site-packages`, el validador arranca y usa el del kit.
  * El lanzador rehúsa un `$ACTUARII_PYTHON` relativo o dentro de la raíz.
* **Orden de las ediciones (AGENTS 6.5):**
  1. `launch.sh` nuevo, antes de que ninguna orden lo use.
  2. La raíz solo para `import tools` en los hooks, `commit_integrity.py` e `install.py`: vale con las
     órdenes de antes y de después.
  3. `validator.py` y su lanzador.
  4. Las órdenes de `.claude/settings.json`, `.mcp.json` y `opencode.jsonc`, con sus tests.
  5. `tools/git/pre-commit`.
* **Pasos que caen en la persona:**
  * Reconectar el servidor MCP. El cambio de `settings.json` lo bloquea en la sesión el hook
    `ConfigChange` y rige en la siguiente.
  * Volver a copiar `.git/hooks/pre-commit`: el sandbox protege `.git` para `Bash`, y el anuncio dirá
    «not installed» hasta entonces (compara bytes).
  * El instalador no actualiza un `pre-commit` que difiere (I2: lo marca como choque), así que
    `noticias-2b` también se actualiza a mano.

## 8. Reproducción de A31 y A32

* Guion preparado en el scratchpad de la sesión (`probe_a31_a32.sh`).
  * Clona Actuarii en un directorio vacío del scratchpad y ejecuta las puertas del clon como las lanza
    Claude Code (la orden de `settings.json`, con `CLAUDE_PROJECT_DIR` y sin el shim en el `PATH`).
  * Primero un control sin nada plantado.
  * Después, con un `dataclasses.py` y un `logging.py` testigos en la raíz:
    * el hook de escritura con la orden de hoy y con `-I -S`;
    * el `pre-commit`;
    * el validador.
  * Al final, con un `python3` falso en `.venv/bin` delante en el `PATH`.
  * Las cargas solo añaden una línea a un fichero del scratchpad y cargan después lo verdadero.
* Se salta el shim a propósito; el autor lo aprobó (AGENTS 4.3).
* Corre dentro del sandbox: lo que prueba es el mecanismo, no la salida del sandbox. La salida la da que
  Claude Code ejecute las puertas fuera, como mostró A19 en vivo.
* **Resultado (2026-10-13, clon de `f9b8990`):**

  | Ejecución | Puerta | Testigo | Decisión de la puerta |
  |---|---|---|---|
  | Control, nada plantado | hook de escritura | nada | deniega (`exit 2`, sin recibo) |
  | A31, orden de hoy | hook de escritura | `dataclasses.py` de la raíz | deniega igual |
  | A31, orden con `-I -S` | hook de escritura | `dataclasses.py` de la raíz | deniega igual |
  | A31 | `pre-commit` → `commit_integrity.py` | `dataclasses.py` de la raíz | `exit 0` (nada preparado) |
  | A31 | validador | `logging.py` y `dataclasses.py` de la raíz | responde al `ping` |
  | A32, orden con `-I -S` | hook de escritura | el `python3` falso de `.venv/bin` | deniega igual |

  Lo previsto en §2 y §3:
  * las cargas se ejecutan sin cambiar la decisión de la puerta, así que desde fuera no se notan;
  * `-I -S` no cierra ni A31 ni A32.

## 9. Decisiones del autor (2026-10-13)

* **§5 sustituye a la decisión del 2026-10-12**, con una condición: los tests nuevos de §7 salen rojos
  en la base y verdes al final (`verify_red_green.py`). La prueba es su ejecución, no la lectura de
  Claude. El autor lo aceptó sin dominar el detalle, con esa condición.
* **A31 y A32 entran en esta auditoría.**
* **Lo que queda de §6: la opción (c),** en un contrato aparte.
* **`INSTALL.md`, solo con el entorno fuera del repositorio** (§5.4).
* **Pendiente:** el caso de la lectura de credenciales (`docs/PLAN.md`, «Principios de diseño»).
