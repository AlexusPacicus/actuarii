# Entorno aislado propio (v0.2): diseño, borrador para el autor

Borrador de Claude, 2026-10-13. Decisión del autor del mismo día: la v0.1 sale el 25 de octubre como «motor
de reglas más adaptador de Claude Code», y el entorno propio se construye en la v0.2. Este documento se
commitea antes de cualquier prototipo, y su plan de prueba (§8) antes de cualquier resultado.

Desarrolla la idea de la v0.2 de `docs/PLAN.md` («Núcleo independiente del proveedor») con lo que enseñó la
auditoría 2b (A19–A35) y la documentación de Claude Code leída el 2026-10-13 con el navegador integrado:
code.claude.com/docs/en/sandbox-environments, …/sandboxing, …/sub-agents, …/memory y …/settings-reference.
Lo marcado «a verificar» no está comprobado.

## 1. Por qué

La v0.1 toma la frontera prestada de Claude Code. El sandbox de Claude Code solo envuelve `Bash`; las
herramientas de ficheros, los hooks, los servidores MCP y lo que Claude Code mete en el contexto quedan
fuera. La 2b enseñó por dónde se escapa:

| Caso | Por dónde |
|---|---|
| A19, A31, A32 | Las puertas corren fuera y cargan el intérprete, el `site-packages` y módulos de la raíz que el agente escribe |
| A33 | `Write` escribe `.git/hooks`, `.git/config` y `.vscode`, que el sandbox protege de `Bash` |
| A34 | Claude Code mete `CLAUDE.md`, memoria e instantánea de git en el revisor ciego |
| A35 | Las credenciales se leen desde la sesión |
| A29 | Navegador, conectores y herramientas del host, fuera de toda regla |
| A25 | El rastro y el candado viven en `.data/`, al alcance de `Bash` |

Cada corrección de la v0.1 es un ajuste propio de Claude Code (`omitClaudeMd`, `includeGitInstructions`,
`denyRead`…): depende de la versión (A34 mostró un cambio de comportamiento entre versiones) y no protege
nada en OpenCode, que no tiene sandbox. Eso no escala.

## 2. El principio

Los tres principios de `docs/PLAN.md` («Principios de diseño»), por construcción y no por parche:

1. **El agente, aislado.** El proceso entero de la herramienta (sus herramientas de ficheros, hooks,
   servidores MCP y todo lo que lance) corre dentro de un entorno que no hace daño por defecto.
2. **Toda salida pasa por una regla.** Escribir una ruta gobernada, salir a la red y tocar la historia de
   git solo se hacen a través de algo de fuera que aplica una regla.
3. **Lo que corre fuera no se fía de lo de dentro.** Las puertas viven fuera del entorno y fuera del
   repositorio, y de dentro solo leen como datos lo que validan.

El adaptador de cada herramienta queda reducido a cómo se lanza dentro y cómo se le configura el MCP.

## 3. Garantías que tiene que dar

| Id | Garantía |
|---|---|
| E1 | Ninguna herramienta de dentro (`Bash`, ficheros, MCP, hooks) escribe una ruta gobernada salvo a través del intermediario (§4.3) |
| E2 | Dentro no se lee lo que no se da: ni el directorio personal (credenciales, memoria e instrucciones del usuario), ni el rastro de auditoría, ni el resto del disco |
| E3 | Dentro no se escribe `.git`: la historia la escriben el intermediario o la persona |
| E4 | La red solo llega a lo que permite la configuración (la API del modelo y poco más), por un proxy de fuera |
| E5 | Las puertas y el intermediario corren fuera, instalados fuera del repositorio, y no cargan nada que el agente alcance |
| E6 | Una revisión ciega corre en un entorno aparte que solo ve el paquete, con el mensaje de encargo escrito por código |
| E7 | Un implementador delegado solo puede escribir los ficheros que su contrato lista |
| E8 | Lo mismo con Claude Code y con OpenCode: lo propio de cada herramienta es un adaptador fino |

## 4. Arquitectura

```
host (la persona) ──────────────────────────────────────────────────────────────────
  intermediario (fuera, residente)          proxy de red (fuera)
    valida 5 Radicales, cita y primitivas     solo los dominios de la configuración
    escribe las rutas gobernadas              puede añadir la credencial de la API
    rastro de auditoría (fuera del repo)
         ▲ socket de Unix                          ▲
         │                                         │
  ┌──────┴── entorno aislado (sandbox del SO, contenedor o VM) ──┴──────────────────┐
  │ agente: Claude Code, OpenCode, …, lanzado con una configuración vacía por sesión │
  │ repositorio: escribible salvo rutas gobernadas, .git y lo que la configuración   │
  │ proteja; sin $HOME, sin .data, sin el kit                                        │
  └──────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 El entorno

Opciones, de más ligera a más fuerte (la comparación de la documentación de Claude Code):

| Opción | Qué es | Pros | Contras |
|---|---|---|---|
| Runtime de sandbox (`@anthropic-ai/sandbox-runtime`) | El mismo Seatbelt o bubblewrap del sandbox de Claude Code, alrededor del proceso entero | Sin Docker; macOS y Linux; envuelve cualquier orden (`claude`, `opencode`); ya probado en esta máquina (S1–S9) | Vista previa beta, formato de configuración que puede cambiar; dependencia de npm; en Linux la lista de denegaciones se fija al arrancar |
| Contenedor de desarrollo o propio | Docker u OCI con el proyecto montado y cortafuegos | Montajes de solo lectura por ruta; estándar; CI | Docker en macOS (una VM); más pesado de instalar |
| Máquina virtual o microVM | Núcleo propio | La separación más fuerte | La instalación más cara |

**Propuesta:** el prototipo, con el runtime de sandbox, porque es el paso más corto desde lo que ya funciona y
no exige Docker. El contenedor queda como segundo nivel, para repositorios no fiables y la CI. Es una
dependencia nueva: necesita la aprobación del autor y comprobar su estabilidad (decisión 1, §10).

### 4.2 Qué ve el agente

* **El repositorio:** escribible, salvo las rutas gobernadas, `.git` y lo que el runtime ya protege
  (`.git/hooks`, `.git/config`, `.mcp.json`, `.claude/agents`, `.claude/commands`, ficheros de arranque de la
  shell).
* **Gobernar todo por defecto se vuelve barato:** el entorno puede dejar escribir solo los directorios
  declarados de trabajo y el resto en solo lectura. Es la alternativa de fondo del mapa de gobierno (A30) y
  se decide aquí (decisión 4).
* **La configuración de la herramienta:** un directorio vacío por sesión (`CLAUDE_CONFIG_DIR` u
  homólogo), con solo lo necesario para autenticarse. Sin `~/.claude`: ni `CLAUDE.md` del usuario, ni su
  memoria, ni sus plugins, ni sus ajustes. La documentación avisa de que un `~/.claude` escribible desde
  dentro deja persistir hooks y servidores MCP que correrán sin sandbox la próxima vez: con un directorio por
  sesión, eso desaparece.
* **La memoria del agente:** la bajo código del repositorio (`.claude/memory/`), que se lee dentro y se
  escribe a través del intermediario. Es la misma que hoy, sin la memoria normal.
* **La credencial de la API:** dentro como variable, o mejor en el proxy, que la añade a cada petición sin
  que el agente la vea. Así lo hace la nube de Claude Code con el token de GitHub (a verificar con
  suscripción y OAuth).

### 4.3 El intermediario

Un servidor MCP residente, fuera del entorno, que el agente alcanza por un socket de Unix: dentro hay un
cliente mínimo, de solo lectura, que traduce stdio al socket. Es el «intermediario de escritura por MCP» del
PLAN y el proceso residente de `docs/design/COSTE.md` §5.

* **`propose_write`:** recibe la propuesta de 5 Radicales, la valida (esquema, cita, primitivas) y, si pasa,
  **escribe él** el contenido exacto. El recibo deja de ser un paso aparte: lo que se valida es lo que se
  escribe (A03 y A04, por construcción).
* **Operaciones sin canal gobernado hoy:** borrar, renombrar y cambiar el modo de una ruta gobernada, con
  recibo (la idea del PLAN del 2026-10-09).
* **`commit`:** el único camino a la historia desde dentro, con las reglas que hoy aplica el `pre-commit`
  (índice igual al disco, grafía, sin enlaces) y las del formato del mensaje. `push`, `merge` y lo que sale
  del repositorio siguen siendo de la persona.
* **El rastro de auditoría,** fuera del repositorio y fuera del entorno (A25, por construcción).
* **Instalado como paquete fuera del repositorio:** nada en la raíz del proyecto puede taparle un módulo
  (A31), ni su intérprete ni su `site-packages` están al alcance del agente (A19, A32).
* **Sin intermediario, nada se escribe:** si no responde, las rutas gobernadas siguen en solo lectura. Falla
  cerrado sin tener que decidirlo.
* Lo que ya existe se reutiliza: el validador, `project_config` (las rutas gobernadas son la tabla de
  permisos del entorno) y la comprobación de primitivas.

### 4.4 La red

Todo sale por un proxy de fuera con lista de dominios. Por defecto, solo la API del modelo (y lo que la
herramienta necesite para autenticarse). Lo que el agente lee llega al proveedor del modelo con o sin
entorno: es la naturaleza de la herramienta y se declara.

### 4.5 La revisión ciega

Un entorno aparte, lanzado por código y no por el agente principal:

* solo ve el paquete, en un directorio fuera de cualquier repositorio: sin `CLAUDE.md` que encontrar al
  subir, sin instantánea de git y con una configuración vacía, así que sin memoria;
* el mensaje de encargo lo escribe `build_review_package.py`, no el modelo, y se le pasa en modo no
  interactivo (`claude -p` u homólogo);
* el veredicto sale como JSON estricto validado en código, y sin él no se quita el candado.

Es A34 por construcción, incluido el mensaje de encargo, que en la v0.1 queda declarado.

### 4.6 La delegación

El implementador corre en su propio entorno, sobre un *worktree* de su rama, con permiso de escritura solo
para los ficheros de `files_may_touch`: el contrato es la tabla de permisos (A28, por construcción). Sus
tests corren dentro. `verify_red_green.py` también corre en un entorno, porque ejecuta código que escribió
el agente.

### 4.7 Los adaptadores

Lo único propio de cada herramienta:

* cómo se lanza dentro, con un directorio de configuración vacío;
* cómo se le declara el servidor MCP del intermediario;
* qué dominios necesita para autenticarse;
* qué protecciones trae su propio sandbox, si lo tiene, para no duplicarlas.

Claude Code y OpenCode primero; el segundo es la prueba de que el núcleo no depende del primero.

### 4.8 Lo que hace la persona

* Arrancar la sesión con una orden (`actuarii run claude`, o similar), que levanta el intermediario, el proxy
  y el entorno.
* Aprobar lo que sale del repositorio: `push`, `merge` y publicación.
* Menos preguntas: dentro, la herramienta puede correr en modo automático o sin preguntas, porque la
  frontera es el entorno. Es lo que la documentación de Claude Code recomienda para trabajo desatendido.

## 5. Qué cambia del kit actual

| Pieza | En la v0.2 |
|---|---|
| Hooks de escritura, shim de Python, `deny_python_escapes` | Innecesarios para la frontera: la sustituyen los permisos del entorno y el intermediario. Siguen en el adaptador de la v0.1 |
| Sandbox de Claude Code y `denyWrite` | Los sustituye el entorno; se puede seguir usando dentro como capa extra |
| Recibos con ventana | El intermediario escribe lo que valida |
| `pre-commit` de integridad | Pasa al `commit` del intermediario; se mantiene como defensa |
| Validador, primitivas, `project_config` | Se reutilizan dentro del intermediario |
| Contratos de delegación y verificador rojo/verde | Se reutilizan; el verificador corre en un entorno |
| Paquete de revisión | Se reutiliza; además escribe el mensaje de encargo y lanza el entorno del revisor |
| Anuncio de sesión | Pasa a ser un informe del entorno, generado de su configuración real (A24, por construcción) |

## 6. Lo que no resuelve

* **La inyección de prompt:** el agente sigue leyendo contenido no fiable. Lo que cambia es que no puede
  actuar fuera del entorno.
* **Lo que llega al proveedor del modelo:** todo lo que el agente lee.
* **El código que la persona ejecuta fuera:** si la persona corre fuera el código que escribió el agente, lo
  corre con todos sus permisos. La regla es ejecutarlo dentro.
* **La terminal de la persona** (A32 en su sentido amplio) y su `PATH`.
* **Las rutas no gobernadas** (A30), salvo que se gobierne todo por defecto (decisión 4).
* **Escapes del sistema operativo o del contenedor.** El runtime es una vista previa; la VM es la opción
  fuerte.
* **En Linux, el runtime fija sus denegaciones al arrancar:** lo que el agente crea después (un `git init`
  anidado) no queda cubierto. Hay que verificarlo y declararlo.

## 7. Antes de construir

1. **Búsqueda previa de entornos aislados para agentes.** La del 2026-10-06 cubrió herramientas de
   gobierno, no entornos (`docs/prior-art/PRIOR_ART.md`). Hay que mirar al menos el runtime de sandbox, el
   contenedor de desarrollo de referencia de Claude Code, Docker Sandboxes, los servicios gestionados de
   ejecución y la guía de despliegue seguro del Agent SDK, y decir en qué se parece y en qué no. Si algo ya
   hace esto, se adopta, no se reinventa.
2. **Verificar en el README del runtime:**
   * el esquema de su configuración (lectura, escritura, red);
   * si deja pasar un socket de Unix concreto (en Linux, el filtro seccomp los bloquea);
   * cómo resuelve los enlaces;
   * cómo se comporta con `CLAUDE_CONFIG_DIR` y con la autenticación por OAuth.
3. **Elegir la tecnología** (decisión 1) y aprobar la dependencia.

## 8. Plan de prueba (se commitea antes del prototipo)

Los casos de las dos auditorías pasan a ser la batería del entorno. Cada uno se repite dentro y se anota lo
que pasa. Lo esperado:

| Casos | Intento dentro del entorno | Esperado |
|---|---|---|
| A01, A08, A33 | Escribir una ruta gobernada, `.git/hooks`, `.git/config` o `.vscode` con `Write`, `Bash` o un MCP | Denegado por el sistema |
| A09, A10 | Cambiar los ajustes que apagan las reglas, o borrar `.actuarii.json` | Denegado: los ajustes del entorno están fuera y la configuración es de solo lectura |
| A19, A31, A32 | Plantar `sitecustomize.py`, `dataclasses.py` o un `python3` falso | Nada de fuera lo carga |
| A23, A34 | Revisión ciega: leer fuera del paquete, o recibir instrucciones, memoria o git | Imposible: solo existe el paquete |
| A25 | Tocar el rastro o el candado | No existen dentro |
| A28 | Un implementador escribe un fichero fuera de su contrato | Denegado por el sistema |
| A29 | Salir a la red por cualquier herramienta | Solo los dominios permitidos, registrados por el proxy |
| A35 | Leer `~/.ssh` | No existe dentro |
| A03, A04 | Escribir un contenido distinto del validado | No hay paso aparte que separar |
| A21 | Una petición malformada al intermediario | Se rechaza y el intermediario sigue vivo |

**Regla de decisión:** el prototipo vale cuando cada caso aplicable sale como se espera, en Claude Code y en
OpenCode. Además se miden, con su método de siempre:
* el coste por escritura gobernada (`docs/design/COSTE.md`; hoy, 1875 ms de mediana);
* la instalación de cero (`docs/design/PRUEBA_EN_LIMPIO.md`).

Las cifras se comparan con las de la v0.1; la regla de cada medida se commitea antes de medir.

## 9. Fases

1. **v0.2-a:** la búsqueda previa, las verificaciones de §7 y la elección de tecnología. Se commitean el
   plan de prueba y sus reglas.
2. **v0.2-b:** el prototipo con Claude Code (el entorno, el intermediario con `propose_write` y la red) y la
   batería de §8.
3. **v0.2-c:** el adaptador de OpenCode y la misma batería.
4. **v0.2-d:** la revisión ciega y la delegación en entornos propios.
5. **Después, la fase 4:** la memoria bajo código pasa a Traianus a través del intermediario
   (`propose_write` sobre la memoria pasa a ser `/ingesta`), cuando se cumpla su criterio de utilidad.

## 10. Decisiones del autor

1. **Tecnología del entorno:** runtime de sandbox (propuesta), contenedor o VM, después de §7.
2. **La historia de git:** commits solo a través del intermediario (propuesta) o solo por la persona.
3. **Permisos dentro:** modo automático o sin preguntas, con la frontera en el entorno (propuesta), o
   mantener las preguntas.
4. **Gobernar todo por defecto:** escribir solo en los directorios declarados de trabajo (propuesta, A30),
   o seguir con la lista de rutas gobernadas.
5. **La credencial de la API:** en el proxy (propuesta, si la autenticación lo permite) o dentro.
6. **Distribución:** el kit fuera del repositorio, como paquete (`pipx` o similar), con una orden que lo
   instala y otra que lanza la sesión. Sustituye a la copia en `tools/` de la v0.1.
