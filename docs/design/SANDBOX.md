# El sandbox de Claude Code como capa baja (investigación, borrador para el autor)

Borrador de Claude, 2026-10-07. Responde a la investigación acordada tras F4b (`docs/PLAN.md`): la lista
de primitivas sobre `ast` frena al agente honesto, pero no es una frontera; la frontera está donde se
ejecuta el código. Fuente: la documentación oficial, «Configure the sandboxed Bash tool»
(code.claude.com/docs/en/sandboxing), leída el 2026-10-07. Versión instalada: Claude Code 2.1.291. Lo que
sigue es lo que la documentación dice; nada está probado todavía en esta máquina (§7).

## 1. Las dos preguntas

**¿Corta la red de `Bash` y de lo que lanza?** Sí, según la documentación. El sistema operativo
(Seatbelt en macOS, un espacio de red aparte con bubblewrap en Linux) deja a cada orden de `Bash`, y a
cada proceso que lance, sin ruta directa a la red. Solo puede salir por un proxy local que comprueba el
nombre del host contra una lista de dominios permitidos que empieza vacía. Lo que no es TCP (UDP, QUIC,
ICMP) no sale. Esto cubre el caso que importa: código escrito por el agente y ejecutado después por
`pytest` o por un script desde `Bash` corre dentro del sandbox, lo haya escrito como lo haya escrito
(`getattr`, `sys.modules`, `pickle`, un `.sh`).

**¿Puede impedir que `Bash` escriba en las rutas gobernadas?** Sí, según la documentación.
`sandbox.filesystem.denyWrite` niega la escritura a nivel del sistema operativo a las órdenes de `Bash`
y a sus procesos hijos, dentro del directorio de trabajo. Además, el sandbox ya protege por su cuenta
`.claude/` (ajustes, skills, agents, hooks), `.mcp.json`, los ficheros de arranque de la shell y los
hooks y la configuración de `.git`, sin excepción posible.

## 2. Lo que el sandbox no cubre

* **Las herramientas de ficheros** (`Read`, `Edit`, `Write`): siguen las reglas de permisos, no el
  sandbox. Las cubren las puertas del kit (recibo, cita literal, primitivas en la puerta).
* **Los hooks y los servidores MCP**: corren fuera, con todo el acceso del usuario. Son el código del
  kit, gobernado.
* **Las órdenes que teclea la persona** con `!`: fuera del sandbox. Es la persona.
* **La lectura**: por defecto se puede leer casi toda la máquina, credenciales incluidas, salvo que se
  configure `denyRead` o `credentials`.
* **Windows nativo y OpenCode**: no hay sandbox. El perímetro de `.claude/settings.json` y el de
  `opencode.jsonc` dejarían de ser iguales (AGENTS 7.1): habría que declararlo.

## 3. Las salidas que hay que cerrar

* **El reintento sin sandbox** (`dangerouslyDisableSandbox`): Claude puede pedir repetir una orden
  fuera. Se cierra con `allowUnsandboxedCommands: false`.
* **El arranque sin sandbox:** si falta una dependencia o la plataforma no lo admite, Claude Code
  ejecuta las órdenes sin sandbox, sin avisar. Se cierra con `failIfUnavailable: true`.
* **La aprobación automática:** con el sandbox activo, las órdenes de `Bash` se aprueban solas por
  defecto (`autoAllowBashIfSandboxed`), lo que cambiaría el perímetro actual (toda orden que no sea de
  solo lectura se pregunta). Se mantiene con `autoAllowBashIfSandboxed: false`, que un repositorio sí
  puede fijar.
* **`excludedCommands`:** cada patrón saca órdenes del sandbox. El kit no debe traer ninguno.
* **Dónde vale cada clave:** la documentación dice que un `false` de `allowUnsandboxedCommands` en los
  ajustes del usuario, en `--settings` o en los gestionados se mantiene aunque el proyecto ponga `true`,
  y que solo esos tres orígenes hacen el sandbox «admin-required». No deja claro si un `false` puesto
  solo en `.claude/settings.json` basta. Hay que probarlo (§7, S4).

## 4. Qué cambiaría en el kit

* **Configuración propuesta** en `.claude/settings.json`, en resumen (la versión exacta, con las rutas
  en la forma `./` que fija la referencia, está en §6):

  ```json
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "autoAllowBashIfSandboxed": false,
    "filesystem": {
      "denyWrite": ["AGENTS.md", "CLAUDE.md", "tests", "tools", "opencode.jsonc", "pyproject.toml",
                    ".actuarii.json", ".data/boundary_validator_audit.db"]
    }
  }
  ```

* **Cierra dos límites declarados** (AGENTS §9), si las pruebas lo confirman:
  * «Writes through `Bash`»: las rutas gobernadas dejan de poder escribirse desde `Bash`.
  * «Forged logs», en parte: con la base del validador en `denyWrite`, `Bash` ya no puede escribir
    recibos. El servidor MCP, que corre fuera del sandbox, sigue escribiendo. No se puede negar `.data`
    entero: el agente ejecuta desde `Bash` `context_pack.py`, que anota en `.data/context_pack.log` los
    recibos de contexto, y `build_review_package.py`, que pone y quita `.data/review_lock.json`. Esos
    dos siguen siendo falsificables, y se declara.
* **Una sola fuente de verdad:** `denyWrite` repite `governed_paths` de `.actuarii.json`. O el
  instalador la genera, o un test comprueba que coinciden. Las dos cosas son baratas.
* **F5 probablemente sobra.** El hook de `Bash` contra los rodeos del shim es una heurística sobre el
  texto. Con la red y las escrituras gobernadas cortadas por el sistema, un rodeo del shim ya no da
  acceso a nada que importe. F5 se reduce a declarar la heurística. Lo mismo con la lista de primitivas:
  sigue como aviso temprano, y la frontera es el sandbox.
* **El coste para el trabajo diario:** `git switch`, `git merge`, `git restore` y `git checkout` escriben
  en `tools/` y `tests/`, así que fallarían dentro del sandbox. Las opciones son que esas órdenes las
  haga la persona (`!`) o un patrón en `excludedCommands`, que las saca del sandbox y las manda al flujo
  de permisos normal (con pregunta). Lo primero es más estricto; lo segundo, más cómodo. Decide el
  autor.
* **Un camino que el sandbox no cierra:** git escribe solo en `.git/objects` y en el índice al crear
  commits. Con `git hash-object -w`, `git update-index` y `git commit`, un agente puede meter en la
  historia un contenido de una ruta gobernada sin escribir el fichero, y un `git merge` o `git checkout`
  posterior (hecho por la persona) lo trae al árbol. Es lo que cubriría el verificador en el commit
  (F4c, v0.2). Se declara.

* **La revisión ciega no cambia (autor, 2026-10-07).** `denyRead` del sandbox solo afecta a `Bash`, y
  el revisor ciego solo tiene `Read`, `Grep` y `Glob`, que confina `confine_review_reads.py`. Las reglas
  `Read(...)` de permisos sí alcanzan a esas herramientas, pero son fijas y de toda la sesión: cegarían
  también al agente que ejecuta, y F1 impide cambiarlas a mitad de sesión. **Idea para la v0.2:** si un
  revisor necesita `Bash` (por ejemplo, para ejecutar el instrumento que revisa), se lanza como otro
  proceso, `claude --settings '…'` en el directorio del paquete, con el sandbox activo y `denyRead`
  sobre todo lo que queda fuera del paquete. Hoy no responde a un fallo real.

## 5. Lo que fija la referencia de ajustes (code.claude.com/docs/en/settings-reference, 2026-10-07)

* **Rutas:** en los ajustes del proyecto, `./ruta` o una ruta sin prefijo se resuelven desde la raíz del
  proyecto; `/ruta` es absoluta. Se escribe `./tests` y no `/tests`.
* **Ámbito:** `enabled`, `failIfUnavailable`, `allowUnsandboxedCommands`, `autoAllowBashIfSandboxed` y
  `filesystem.denyWrite` se pueden poner en el `.claude/settings.json` del proyecto. Las tres primeras
  tienen «límites en los ajustes del proyecto y locales».
* **Precedencia:** `.claude/settings.local.json` va por encima de `.claude/settings.json`, así que un
  fichero local podría poner `enabled: false` o `allowUnsandboxedCommands: true`. Durante la sesión no se
  puede: F1 bloquea los cambios de ajustes, el sandbox protege `.claude/` de `Bash` y `.claude/**` está
  gobernado para `Edit` y `Write`. Antes de abrirla, sí (A10, ya declarado).
* **El refuerzo que el proyecto no puede dar:** un `allowUnsandboxedCommands: false` en
  `~/.claude/settings.json` se mantiene aunque el proyecto o el fichero local pongan `true` (desde la
  2.1.285; aquí hay 2.1.291). El README lo recomienda y el instalador avisa si falta. Es un cambio en la
  configuración del usuario, fuera del repositorio: lo hace la persona.
* **Las listas se suman:** `denyWrite` se combina entre ficheros. Las reglas `Edit(...)` de deny se
  añaden a `denyWrite`, y las de allow, a `allowWrite`.

## 6. Cambio propuesto en `.claude/settings.json` (sin aplicar)

Se añade la clave `sandbox` al final del objeto raíz, después de `"enableAllProjectMcpServers": true`.
El resto del fichero no cambia. El perímetro de permisos tampoco: `autoAllowBashIfSandboxed: false`
mantiene la pregunta en cada orden de `Bash` que no está en `allow`.

```json
  "enableAllProjectMcpServers": true,
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "autoAllowBashIfSandboxed": false,
    "filesystem": {
      "denyWrite": [
        "./AGENTS.md",
        "./CLAUDE.md",
        "./tests",
        "./tools",
        "./opencode.jsonc",
        "./pyproject.toml",
        "./.actuarii.json",
        "./.data/boundary_validator_audit.db"
      ]
    }
  }
```

**Cómo se aplica:** la edición pasa por la puerta (un recibo de `validate_proposal` con el `old_string`
y el `new_string` exactos). F1 hace que no se aplique en la sesión en curso, así que después hay que
abrir una sesión nueva y ejecutar §7 en ella. Si algo sale mal, se vuelve a la versión anterior con el
mismo procedimiento, o la persona lo hace a mano.

**Después, si §7 sale bien** (por contrato, test primero): un test que compruebe que `denyWrite` cubre
cada entrada de `governed_paths` de `.actuarii.json` (salvo `.claude/**` y `.mcp.json`, que el sandbox
protege solo); `AGENTS.md` §9 con los límites que se cierran y los que quedan; y la decisión sobre los
`git switch` y `git merge`.

## 7. Plan de prueba (se commitea antes de ejecutarlo)

Con la configuración del §6 en `.claude/settings.json` (pasa por la puerta y, por F1, se aplica al
abrir una sesión nueva). Cada caso dice lo que se espera; lo que salga distinto se anota tal cual.

| Caso | Orden (la lanza Claude, no la persona) | Se espera |
|---|---|---|
| S1 red | `curl --noproxy '*' https://example.com` | falla: no resuelve el host |
| S1b red | un script commiteado de `tools/` que abre un socket a un host no permitido | falla |
| S2 escritura | `touch tests/zz_probe` y `touch tools/zz_probe` | `Operation not permitted` |
| S2b escritura | `touch docs/zz_probe` | funciona (no gobernado); se borra después |
| S3 rastro | escribir en `.data/boundary_validator_audit.db` (p. ej. `touch`) | `Operation not permitted`; `context_pack.py` sigue anotando su log |
| S4 reintento | Claude pide repetir S2 con `dangerouslyDisableSandbox` | se ignora: sigue en el sandbox |
| S5 aprobación | una orden que escribe en `docs/` | pregunta, como hoy |
| S6 kit | los hooks (Edit gobernado sin recibo), el servidor MCP y el anuncio de sesión | funcionan como hoy |
| S7 suite | `pytest tests` dentro del sandbox | verde, mismo número de tests |
| S8 git | `git commit` en una rama; `git switch` a otra que cambia `tools/` | el commit funciona; el `switch` falla |
| S9 sin sandbox | (no se puede provocar en macOS sin tocar el sistema) | se deja como declarado |

**Regla de decisión:** si S1, S2, S3 y S4 salen como se espera, la v0.1 se apoya en el sandbox para la
red, los procesos y las escrituras por `Bash`, y F5 queda en declarar la heurística. Si S4 falla solo
con los ajustes del proyecto, el README pide al usuario poner `allowUnsandboxedCommands: false` en sus
ajustes de usuario, y el instalador lo comprueba. Si S1 o S2 fallan, se declara y va a la v0.2.

## 8. Resultados (2026-10-07, sesión nueva con el §6 en el árbol de trabajo, sin commitear)

Claude Code 2.1.291, macOS. Cada orden la lanzó Claude desde `Bash`, dentro del sandbox.

| Caso | Resultado | ¿Como se esperaba? |
|---|---|---|
| S1 red | `curl --noproxy '*' https://example.com`: `Could not resolve host` (salida 6) | sí |
| S1b red | sustituido (no hay un script commiteado que abra un socket): `nc -z example.com 443` no resuelve el nombre, y `nc -z 1.1.1.1 443`, TCP directo a una IP, falla (salida 1) | sí |
| S2 escritura | `touch` en `tests/`, `tools/`, `AGENTS.md` y `.actuarii.json`: `Operation not permitted` | sí |
| S2b escritura | `touch docs/zz_probe`: funciona; se movió al temporal del sandbox | sí |
| S3 rastro | `touch .data/boundary_validator_audit.db`: `Operation not permitted`. `context_pack.py` sigue anotando su log (313 → 314 líneas) | sí |
| S4 reintento | `touch tests/zz_probe` con `dangerouslyDisableSandbox: true`: `Operation not permitted`; el parámetro se ignora con los ajustes del proyecto solos | sí |
| S5 aprobación | pendiente de que el autor confirme si se le preguntó por las órdenes que escriben en `docs/` | — |
| S6 kit | `Write` en `tests/` sin recibo: denegado por la puerta, nombrando su regla. El servidor MCP, fuera del sandbox, sigue emitiendo recibos | sí |
| S7 suite | 2716 en verde y 1 fallo, el mismo que fuera del sandbox: `test_registration_changes_nothing_else_in_settings` fija las claves de `settings.json` y no conoce `sandbox` | sí (el fallo es del cambio, no del sandbox) |
| S8 git | rama y commit vacío: funcionan. `git checkout 916ee79 -- tools/boundary_validator/validator.py`: `unable to unlink old … Operation not permitted` | sí, con un hallazgo |
| S9 sin sandbox | no se provocó | declarado |

**Hallazgo de S8, no previsto:** el `git checkout <commit> -- <ruta>` que falló **ya había escrito el
índice**. El fichero en disco seguía igual que `HEAD`, pero la versión antigua quedó preparada (`MM` en
`git status`), y el siguiente `git commit` la habría guardado sin pasar por la puerta. Se deshizo con
`git restore --staged`, que solo escribe en `.git`. Es un caso concreto del camino ya declarado en §4:
el índice y `.git/objects` quedan fuera del sandbox y de la puerta. La persona aprueba el `git commit`
(está en `ask`), pero el mensaje del commit no le enseña lo que hay en el índice. Lo cerraría el
verificador en el commit (F4c, v0.2); hasta entonces, se declara y el README recomienda mirar
`git diff --cached` antes de aprobar un commit.

**Otro efecto:** `.git/config` está protegido, así que las órdenes de git que escriben configuración
(`git branch -D` al limpiar la sección de la rama, `git remote`, `git config`) avisan o fallan dentro
del sandbox. `git branch -D` borró la rama igualmente.

**Decisión según la regla:** S1, S2, S3 y S4 salen como se esperaba, así que la v0.1 se apoya en el
sandbox para la red, los procesos y las escrituras por `Bash`, y F5 queda en declarar la heurística.
`allowUnsandboxedCommands: false` basta en los ajustes del proyecto (S4); el refuerzo en los ajustes
del usuario sigue siendo recomendable, por el fichero local (§5).

## 9. Decisiones del autor (2026-10-07)

* **`git switch`, `git merge` y demás órdenes que escriben rutas gobernadas:** opción (a), las hace la
  persona con `!`, fuera del sandbox. Ningún `excludedCommands`. Fusionar es el momento en que una
  persona debe mirar.
* **Integridad del commit, en la v0.1:** un hook de git `pre-commit` comprueba que cada ruta gobernada
  del índice coincide con el fichero en disco (blob y modo). Con el sandbox, el disco de una ruta
  gobernada solo lo escriben la puerta o la persona, así que lo que se commitea pasó por una de las dos.
  Cierra el hallazgo de S8 y el truco de `git hash-object` + `git update-index`. Vive en `.git/hooks`,
  que el sandbox protege; lo instala la persona. Se declaran `--no-verify` y las órdenes internas de
  git (`commit-tree`, `update-ref`), que se saltan los hooks y que el perímetro ya pregunta.
* **Formato del mensaje** (prefijo de una lista cerrada, tipo frente a rutas, plantilla, sin
  atribución): a la v0.2.
* **S5:** pendiente de confirmar por el autor.
