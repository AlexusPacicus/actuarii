# Actuarii: el proceso completo

Para la revisión del autor (2026-10-07). Describe el kit tal como está en `main` (`2457da6`), con
cada hallazgo de la auditoría (`docs/adversarial-audit/CASES.md`) marcado en el punto del flujo
donde ocurre: **⚠ A0x**.

## 0. Mapa

| Pieza | Fichero | Cuándo actúa |
|---|---|---|
| Configuración | `.actuarii.json`, leída por `tools/project_config.py` | En cada llamada de cada hook y del shim |
| Cableado | `.claude/settings.json` (hooks y permisos), `.mcp.json` (servidor MCP) | Al abrir la sesión ⚠ A08, A09 |
| Anuncio | `tools/hooks/announce_governance.py` | `SessionStart` |
| Puerta del shim | `tools/hooks/session_python_gate.sh` + `tools/bin/python3` | `SessionStart` y cada `python3` en `Bash` |
| Validador de propuestas | `tools/boundary_validator/validator.py` (MCP `validate_proposal`) | Cuando el agente lo llama |
| Rastro de auditoría | `.data/boundary_validator_audit.db` (tabla `audit_log`) | Lo escribe el validador y lo lee la puerta |
| Puerta de escritura | `tools/hooks/require_boundary_validation.py` + `tools/boundary_validator/hook_gate.py` | `PreToolUse` de `Edit` y `Write` ⚠ A01 |
| Contexto obligatorio | `tools/hooks/require_contract_context.py` + `tools/audit/context_pack.py` | `PreToolUse` de `Edit` y `Write` |
| Python cerrado | `tools/hooks/deny_python_escapes.py` | `PreToolUse` de `Bash` |
| Revisión ciega | `tools/audit/build_review_package.py` + `tools/hooks/confine_review_reads.py` | `PreToolUse` de `Read`, `Grep` y `Glob` con el candado puesto |
| Delegación | `tools/audit/delegation_contract.py`, `.claude/agents/implementer.md` | Antes de lanzar un subagente y al recibir su informe |

## 1. Al abrir la sesión

1. Claude Code lee `.claude/settings.json` y `settings.local.json`, que tiene más precedencia.
   **⚠ A09:** un `"disableAllHooks": true` en cualquiera de los dos apaga todo lo que sigue, y un
   cambio en mitad de la sesión se aplica sin que nada lo bloquee.
2. `session_python_gate.sh` añade `tools/bin` al principio del `PATH` de cada `Bash` de la sesión (vía
   `$CLAUDE_ENV_FILE`). Sin esa variable avisa por stderr y la puerta del shim no está activa.
3. `announce_governance.py` lee `.actuarii.json` e imprime en el contexto del agente:
   * las rutas que necesitan recibo y la ventana;
   * el registro de contratos y la revisión ciega;
   * dónde corre Python;
   * de dónde salen las reglas.

   **⚠ A10:** si después se borra `.actuarii.json` por `Bash`, el gobierno baja al mínimo y el
   anuncio no se repite hasta la sesión siguiente.

## 2. La configuración

`.actuarii.json` tiene cinco claves, todas obligatorias:

```json
{"schema": "actuarii-config/1",
 "governed_paths": ["AGENTS.md", "tests/**", "..."],
 "python_script_dirs": [],
 "contract_registry": null,
 "review": null,
 "receipt_window_seconds": 900}
```

| Estado | Qué pasa |
|---|---|
| Válida | Rige lo que dice. |
| No existe | Rige el mínimo incorporado: `.actuarii.json`, `AGENTS.md` y `CLAUDE.md`; Python en todo el repositorio, solo commiteado; sin registro ni revisión. |
| Inválida | La puerta deniega todo `Edit` y `Write` dentro de la raíz salvo el de `.actuarii.json`; el shim solo deja el directorio del kit. |

* **Siempre gobernados,** los liste o no la configuración: `.actuarii.json` y el registro de
  contratos. **⚠ A08:** no lo están `.claude/**`, `.mcp.json` ni `opencode.jsonc`, ni, en este
  repositorio, `tools/audit/**`.
* La ubicación de la configuración, del rastro y del candado es un atributo de módulo, nunca una
  variable de entorno: el agente puede fijar su entorno.

## 3. Una escritura gobernada, paso a paso

```
agente ──validate_proposal(proposal, target_file)──▶ validador ──▶ audit_log
agente ──Edit/Write(file_path, contenido)──▶ hooks PreToolUse ──▶ permitir / denegar
```

### 3.1 El agente pide un recibo

Llama al MCP `validate_proposal` con:
* `proposal`: un **texto** con JSON dentro (**⚠ A12**), de 5 Radicales: `Intent_Class`, `Target_File`,
  `Topological_Grounding`, `Implementation_Block` y `Safety_Abort`;
* `target_file`: el fichero, aparte (opcional en el esquema del MCP; sin él el recibo no sirve).

### 3.2 El validador decide, en este orden

1. Un byte nulo en la entrada → `ABORTED_VIOLATES_ZERO_TRUST`.
2. JSON inválido o que no es un objeto → `INVALID_JSON`.
3. Primitivas de red o de procesos en `Implementation_Block` → `ABORTED_VIOLATES_ZERO_TRUST`.
   **⚠ A05:** busca nombres en el texto; `'sub' + 'process'` pasa.
4. Esquema estricto (Pydantic): una clave de más, de menos o un valor fuera de enumeración →
   `INVALID_JSON`, o `BLOCKED_BY_SAFETY_GATE` si lo inválido es el `Safety_Abort`.
5. `Safety_Abort` distinto de `NONE` → `BLOCKED_BY_SAFETY_GATE`.
6. Solo para `FIX`, `REFACTOR` y `AUDIT`: la cita (`Topological_Grounding`) tiene que estar byte a
   byte en `target_file`, dentro de la raíz → si no, `ABORTED_GROUNDING_FAILED`. **⚠ A02:** `TEST`,
   `DOC` y `SPEC` no necesitan cita.
7. Si pasa todo → `EXECUTE_SAFE`.

Cada decisión se escribe en `audit_log` (`case_id`, `timestamp`, `intent_class`, `target_file`,
`decision`, `safety_abort`). **⚠ A03:** el `target_file` del recibo no se compara con el
`Target_File` de la propuesta. **⚠ A04:** ni el `Implementation_Block` ni su hash se guardan: el
recibo no sabe qué contenido autorizó.

### 3.3 El agente escribe y los hooks deciden

**`require_boundary_validation.py`** (solo para `Edit` y `Write`; **⚠ A01:** `NotebookEdit` no pasa):
1. Lee la carga del harness. Si está mal formada, deniega.
2. Resuelve la ruta (`canonical`): enlaces simbólicos, `..` y `~`, y la escribe con los nombres que
   guarda el sistema de ficheros (`TESTS/x.py` es `tests/x.py` en APFS). Fuera de la raíz, permite.
3. Pide la regla a `project_config`: el propio `.actuarii.json`, el registro o la primera entrada de
   `governed_paths` que case. Sin regla, permite. Con la configuración inválida, deniega.
4. Busca en `audit_log` un `EXECUTE_SAFE` para ese fichero dentro de la ventana. Si lo hay, permite;
   si no, deniega nombrando la regla, la fuente, la ventana y la llamada que lo resuelve. Si no puede
   leer el rastro, deniega. **⚠ A04:** no mira el contenido que se va a escribir.

**`require_contract_context.py`**, a continuación, sobre la misma escritura:
1. Lee el registro que nombra `contract_registry` (`null`: permite).
2. Si la ruta casa con una regla del registro, exige que cada sección requerida tenga una línea
   `served` en `.data/context_pack.log`, dentro de la ventana del registro y con el hash del contrato
   tal como está ahora. Si falta alguna, deniega e imprime la orden de `context_pack` que la sirve.

Las dos puertas tienen que permitir; basta una denegación.

## 4. Python cerrado

```
Bash("python3 x.py") ──▶ deny_python_escapes (texto) ──▶ shell ──▶ tools/bin/python3 (shim)
```

1. **El hook de `Bash`** lee la orden como texto y deniega las formas de llegar a un intérprete
   saltándose el shim: un intérprete por ruta, nombres que el shim no cubre, `pyenv exec`,
   reasignar `PATH`, `env -i` y `command -p`.
   * **⚠ A06:** también deniega `echo "PATH=$PATH"`, aunque solo esté en un heredoc de datos.
   * **⚠ A07:** no conoce `uv run`, `pipx run` ni `pytest`, que traen su propio intérprete.
2. **El shim** decide por el argv:
   * `--version` sí;
   * `-c`, `-m`, stdin o sin script, no;
   * un script solo si es un fichero regular, no un enlace, está dentro del directorio del kit
     (`tools/`) o de una entrada de `python_script_dirs` y está registrado en `HEAD`.

   Para saber los directorios lanza el intérprete real, aislado (`-I`), sobre
   `tools/project_config.py --python-script-dirs`. Si el lector falla, solo vale el directorio del
   kit. **⚠ A11:** no hay test con un `PATH` sin shim ni con un Python 3.9 real.

## 5. Delegación por contrato

1. El agente ejecutor escribe un `DelegationContract` en JSON estricto: rama, commit base, contexto
   (las secciones exactas que hay que leer), problema, decisiones, comportamientos, tests,
   ficheros que se pueden y no se pueden tocar, gates y mensaje de commit.
2. Lo valida en código: `python3 tools/audit/delegation_contract.py contract --emit-context`.
3. Lanza el subagente `implementer`, que:
   * vuelve a validar el contrato;
   * pide el contexto con `context_pack`;
   * escribe los tests y los ve en rojo, y luego el código;
   * pide un recibo antes de cada fichero gobernado;
   * pasa las gates y para en un commit.
4. El implementador responde con un `DelegationReport` validado igual (`... report`).
5. El ejecutor revisa el diff, pasa la suite y hace el merge.

**⚠ A15:** el rojo de cada test (`red_reason`) lo declara el implementador; nada lo comprueba.

## 6. Revisión ciega

1. `build_review_package.py build --record <registro> --commit <sha> --out <dir> --lock`:
   * lee `review` de la configuración (con `null`, no construye);
   * copia, desde ese commit, el procedimiento, los documentos base, el registro y lo que citan
     (un nivel), salvo los prefijos denegados, `.data/` y los demás registros;
   * escribe `MANIFEST.json` con los hashes y pone el candado (`.data/review_lock.json`).
2. Con el candado puesto, `confine_review_reads.py` deniega todo `Read`, `Grep` y `Glob` fuera del
   paquete.
3. El subagente `blind-reviewer`, sin herramientas de escritura ni `Bash`, devuelve un veredicto
   `PASS` o `CHANGES`.
4. El ejecutor anota el veredicto y quita el candado (`unlock`).

## 7. Perímetro de permisos

`.claude/settings.json` y `opencode.jsonc` tienen el mismo perímetro, y los tests lo vigilan:
* permitido: lectura de git y los scripts de `tools/`;
* denegado: `rm`, Python en línea, web fetch y web search;
* todo lo demás se pregunta.

Los hooks son solo de Claude Code. OpenCode comparte permisos, el MCP y las instrucciones, pero no
las puertas.

## 8. Lo que la auditoría deja para corregir

| Corrección | Hallazgos | Qué cambia |
|---|---|---|
| F1 | A08, A09 | Hook `ConfigChange` que bloquea en la sesión los cambios de `project_settings`, `local_settings` y `skills`; `"disableAllHooks": false` en `settings.json`; gobernar `.claude/**`, `.mcp.json`, `opencode.jsonc` y `tools/**`, y el cableado en el mínimo incorporado. |
| F2 | A01 | La puerta de escritura vigila también `NotebookEdit` (`notebook_path`). |
| F3 | A03, A12, A02 | `target_file` obligatorio e igual al `Target_File`; el esquema Pydantic como `inputSchema` del MCP; cita obligatoria si el fichero existe, sea cual sea la intención. |
| F4 | A04 | El recibo ata el contenido. El validador guarda el hash del `Implementation_Block`, y la puerta solo permite el `Edit` o `Write` cuyo texto nuevo tenga ese hash. Es lo que el esquema de 5 Radicales ya decía («texto exacto que se inserta»). |
| F5 | A06, A07 | El hook de `Bash` deja de confundir un argumento entre comillas con una asignación, y conoce `uv run` y `pipx run`. Se declara lo de `pytest`. |
| F6 | A11 | Test de los hooks con un `PATH` sin el shim y, si existe, con `/usr/bin/python3`. |
| F7 | A05, A07, A10, A09 | Declarar en `AGENTS.md` §9 lo que queda: la matriz textual, `pytest`, `.actuarii.json` borrado por `Bash` y un `settings.local.json` que ya existe al abrir la sesión. |

Orden propuesto: F1 → F2 → F3 → F4 (el más grande; su diseño se commitea antes de implementarlo) →
F5 → F6 → F7. Después, A15.
