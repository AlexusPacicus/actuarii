# Búsqueda previa: herramientas parecidas a Actuarii

Hecha el 2026-10-06, antes de empaquetar (semana 1 del calendario de `docs/PLAN.md`). Responde a la
pregunta de la fase 3: si ya existe algo igual, se replantea ahora, no después.

## Conclusión

**No se ha encontrado nada igual. No hay que replantear el kit, pero sí cómo se presenta.**

* Nadie hace lo que forma el núcleo de Actuarii: escribir solo con un recibo de una propuesta
  validada, exigir que se haya servido el contexto de un contrato antes de editar, hacer una revisión
  ciega por construcción y delegar trabajo con contratos validados en código.
* El terreno de alrededor está lleno. Bloquear órdenes destructivas, guardar un registro de auditoría
  y aplicar políticas de permitir, denegar o preguntar ya lo hacen muchas colecciones de hooks para
  Claude Code y, a escala de empresa, Microsoft (Agent Governance Toolkit, con plugin para Claude
  Code).
* **Consecuencia para el README:** no presentar Actuarii como «guardrails para agentes». Ese hueco
  está saturado y tiene un actor grande. Lo distinto es que **gobierna el procedimiento**: qué se
  escribe, con qué justificación, con qué contexto leído y quién lo revisa, con pruebas que quedan.
* Publicar la lista de límites declarados ya **no distingue**: lo hacen `andreybuilt/agent-guardrails`,
  `agent37-platform/claude-code-hooks` y el plugin de Microsoft. Es lo mínimo exigible, no un
  argumento de venta.

## Método y alcance

* **Herramienta:** navegador integrado de la app (WebFetch y WebSearch están denegados en el
  perímetro del repositorio; el autor eligió esta vía el 2026-10-06). Buscador: DuckDuckGo. Fuentes:
  los README y las páginas de cada proyecto, leídos ese día.
* **Consultas:** colecciones de hooks para Claude Code, hooks que exigen aprobación antes de editar,
  guardrails para agentes de código, contexto obligatorio antes de editar, contratos estrictos para
  subagentes, revisión ciega, recibos y procedencia de acciones de agentes, gateways MCP con
  aprobación y auditoría, y bloqueo de Python inline.
* **Límites de esta búsqueda:**
  * No se ha instalado ni ejecutado nada; lo que se dice de cada herramienta es lo que dice su
    documentación.
  * No se ha medido la actividad de los proyectos (estrellas, commits, usuarios).
  * `roboticforce/agent-guardrails`, `EvanL1/claude-code-hooks`, AgentCheck y `blink.review` se vieron
    solo en los resultados del buscador, sin leer su documentación.
  * El ecosistema de Codex, Cursor y Copilot se ha mirado solo de pasada.

## Qué compara

Las seis piezas del kit (`docs/PLAN.md`, «Qué es»), frente al equivalente más cercano encontrado:

| Pieza de Actuarii | Lo más cercano encontrado | Diferencia |
|---|---|---|
| **Puerta de propuestas:** un MCP valida cada mutación (5 Radicales, cita literal, matriz zero-trust) y deja rastro | Motores de políticas sobre llamadas a herramientas (Agent Governance Toolkit, `claude-approve`, gateways MCP) | Ellos deciden por regla sobre la acción; Actuarii exige que el agente formule y fundamente la mutación antes de hacerla. |
| **Escritura con recibo:** `Edit`/`Write` en rutas gobernadas solo con un `EXECUTE_SAFE` reciente | Aprobación ligada al hash del contenido (Agent Hooks, AGENT-HOOKS-0.1) | No hay un equivalente para hooks de Claude Code. Agent Hooks ata la aprobación al contenido y nuestro recibo solo al fichero (límite declarado). |
| **Revisión ciega:** con un paquete bloqueado se deniega toda lectura fuera de él | Nada | No se ha encontrado nada parecido. |
| **Contexto obligatorio:** no se edita una ruta registrada sin un recibo de que se sirvió su contrato | Hooks que inyectan contexto en cada operación; `tdd-guard` (precondición antes de editar) | Inyectar contexto lo empuja; Actuarii exige prueba de que se sirvió, ligada al hash del contrato. `tdd-guard` es la idea más próxima: una precondición de proceso en `PreToolUse`. |
| **Python cerrado:** el shim solo deja ejecutar scripts commiteados | Clasificadores de Bash (`andreybuilt`, AGT, `agent37`) | Ellos deniegan formas peligrosas (lista negra); Actuarii permite solo lo commiteado en HEAD (lista blanca por identidad). |
| **Delegación por contrato:** JSON estricto validado en código, de ida y de vuelta | `vytharion/claude-code-subagent-output-schema`; salidas estructuradas de Claude | Ellos validan solo la respuesta del subagente; Actuarii valida también el encargo, y el implementador queda bajo las mismas puertas. |

## Candidatos, por categoría

### Colecciones de hooks para Claude Code

* **[agent37-platform/claude-code-hooks](https://github.com/agent37-platform/claude-code-hooks)**: sin
  dependencias (bash y Python estándar), guardas de Bash y de ficheros, escaneo de secretos, registro
  de auditoría JSONL, contexto de git al abrir sesión. Publica sus límites. Se instala como plugin o
  con un `install.sh` que solo escribe `settings.json` si no existe.
  * Se parece en la forma (biblioteca estándar, hooks, límites honestos, instalador que no pisa).
  * No se parece en el fondo: protege de accidentes; no gobierna el procedimiento.
* **[andreybuilt/agent-guardrails](https://github.com/andreybuilt/agent-guardrails)**: seis hooks que
  deniegan antes de ejecutar, batería adversarial de 108 casos, bypasses abiertos publicados, solo
  biblioteca estándar, 40 837 decisiones registradas en uso real. Uno de sus hooks exige que cada
  subagente declare su modelo.
  * Es el más próximo en filosofía: falla cerrado, una mala autorización es el único error
    inaceptable, y los límites son públicos.
  * Su alcance es la shell. No tiene recibos, contratos ni revisión.
* **[nizos/tdd-guard](https://github.com/nizos/tdd-guard)**: bloquea las ediciones que se saltan TDD.
  Está en el marketplace comunitario de plugins.
  * Es la prueba de que existe demanda de «disciplina de proceso hecha cumplir por hooks».
  * Es un precedente de posicionamiento, no un competidor.
* **Otras:** `dokipen/claude-approve` (reglas TOML que aprueban, deniegan o escalan), PolicyApprovalGate
  y una larga cola de guías y colecciones de hooks de ejemplo (`EvanL1/claude-code-hooks`,
  `decider/claude-hooks`, `cchooks`).

### Gobernanza a escala de framework

* **[microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit)**
  (AGT, vista previa pública): motor de políticas (YAML, OPA, Cedar), identidad, sandbox, cumplimiento
  OWASP y auditoría a prueba de manipulación. Tiene SDK en cinco lenguajes y plugins para Claude Code,
  Codex, Copilot y OpenCode.
  * Su plugin de Claude Code inyecta contexto al abrir sesión, inspecciona los prompts y decide en
    `PreToolUse` si permitir, denegar o preguntar.
  * Guarda un registro encadenado por SHA-256 y declara que ese encadenado no resiste a quien pueda
    reescribir el registro.
  * **Diferencias:**
    * Gobierna acciones por política, no procedimiento por recibos.
    * No tiene contexto obligatorio, revisión ciega, shim de Python ni contratos de delegación.
    * Carga la ruta de la política desde una variable de entorno (`AGT_CLAUDE_POLICY_PATH`), y
      Actuarii rechaza eso a propósito: un agente puede fijar su entorno.
* **[Agent Hooks / AGENT-HOOKS-0.1](https://commandline.microsoft.com/agent-hooks-framework-neutral-ai-governance-contract/)**
  (Microsoft, 2026-08-27): un contrato neutral de interceptación con 8 puntos, 3 veredictos y
  obligaciones de fallar cerrado para el anfitrión. Trae un kit de conformidad de 47 escenarios.
  * Su aprobación se ata a un hash del contenido que vio quien aprueba, y no se puede reutilizar.
  * Es para frameworks de agentes (Agent Framework, Semantic Kernel), no para los hooks de Claude
    Code.

### Recibos y procedencia

* **[Agent Receipts](https://agentreceipts.ai)** (obsigna): recibos firmados con Ed25519, encadenados
  por hash, como credenciales verificables W3C. El firmante y el almacén viven en un proceso aparte,
  así que el rastro aguanta aunque el agente esté comprometido. Tiene un hook para Claude Code y un
  proxy MCP.
  * Registra lo que pasó; no condiciona lo que puede pasar.
  * Resuelve uno de nuestros límites declarados: el log de recibos es un fichero plano que un agente
    puede falsificar desde Bash.
* **Otras:** AgentLedger y `ai-audit-trail` (registros encadenados orientados al cumplimiento de la
  EU AI Act).

### Gateways MCP

* `KiaanKothari/mcp-guardrail`, `yuzhouzhibao/mcp-security-gateway`, el MCP Security Gateway de AGT y
  Obot: listas de herramientas permitidas o denegadas, aprobación, auditoría y detección de
  envenenamiento de herramientas.
  * Controlan qué herramientas MCP se llaman.
  * Actuarii usa un MCP como validador, no como intermediario de otras herramientas.

### Contexto y contratos

* Las guías de hooks que «garantizan la inyección de contexto» y `blink.review` (comercial, comprueba
  las ediciones contra `AGENTS.md`) están cerca del contexto obligatorio. Ninguna prueba que el
  contexto se sirviera ni lo liga al hash del contrato.
* `vytharion/claude-code-subagent-output-schema` valida con Pydantic la salida de subagentes en
  paralelo.

## Lo que la búsqueda aporta al diseño

Ninguna de estas propuestas entra antes del lanzamiento: el calendario prohíbe mejoras de gobernanza
que no respondan a un fallo real. Quedan como candidatas para la v0.2 o como decisiones de la fase 2.

1. **Atar el recibo al contenido, no solo al fichero.** Agent Hooks lo hace con un hash del contenido
   aprobado. Cerraría el límite declarado «el recibo ata un fichero, no el contenido de la edición».
   Para v0.2.
2. **Recibos fuera del alcance del agente.** Agent Receipts firma en un proceso aparte. Actuarii podría
   emitir recibos compatibles en vez de reinventarlos. Para v0.2.
3. **Distribución como plugin (decisión de la fase 2, del autor).** AGT, `agent37` y `tdd-guard` se
   instalan con `/plugin marketplace add`. La fase 2 prevé «una orden que copia los hooks». Hay que
   decidir si esa orden es un plugin, un `install.sh` como el de `agent37`, o los dos.
4. **Batería adversarial como prueba de credibilidad.** `andreybuilt` gana confianza con 108 casos y
   bypasses publicados. Actuarii ya tiene 1795 tests y límites declarados; el README debería
   enseñarlos de la misma forma: qué intenta un agente y qué pasa.
