# DEVLOG de Actuarii

Una entrada por día, la más reciente arriba: qué se hizo (con sus commits), qué se decidió y por qué, qué
salió mal y qué se aprendió. Lo que ya cuentan los documentos de diseño se enlaza, no se repite. Se
escribe al cerrar cada sesión (decisión del autor, 2026-10-07). Las entradas del 5 y el 6 de octubre se
reconstruyeron el 7 a partir de `git log` y de `docs/PLAN.md`.

## 2026-10-08

Escrita al cerrar la sesión, que siguió a la del 7. Suite: 2976 en verde, sin cambios de código.

**Hecho**
* DEVLOG creado, con las entradas del 5 al 7 y la regla de escribirlo al cerrar cada sesión
  (`d1d67c4`, del 7).
* Idea para la v0.2 apuntada en `docs/PLAN.md` (`c74dc54`): un núcleo independiente del proveedor,
  para que cualquier entorno de agentes se enganche y las reglas se ejecuten en un paquete. Tres
  piezas: adaptadores finos por entorno sobre una decisión central; el sandbox del sistema por fuera
  del agente entero (`@anthropic-ai/sandbox-runtime` o un contenedor), con la configuración sacada de
  `.actuarii.json`; y un intermediario de escritura por MCP, que escribe las rutas gobernadas tras
  comprobar la propuesta, de modo que la frontera no dependa de los hooks de cada entorno.

**Decidido (autor)**
* El núcleo independiente del proveedor va a la v0.2 o a la v1; antes del lanzamiento no se hace. El
  README de la v0.1 dice la dirección en una frase.

**Siguiente**
* Fase 2, el empaquetado, desde el 12 de octubre (traspaso en `docs/PLAN.md`).

## 2026-10-07

Escrita al cerrar la sesión. Suite: de 2350 a 2976 en verde.

**Hecho**
* F3 comprobada en la llamada real: Claude Code convierte el texto JSON en objeto, y el rechazo de un
  texto que no es JSON sí se aplica (`2268ef5`).
* F4b, primitivas por `ast` sobre el fichero resultante, decididas en la puerta (`74177b4`), en dos
  pasos porque el servidor MCP en marcha conservaba la matriz léxica hasta reconectarlo (`28f2c80`,
  `b6888ca`). Diseño en `docs/design/RECIBO_CONTENIDO.md` §4.1.
* Sandbox de Claude Code investigado, probado (casos S1–S9) y adoptado como frontera de `Bash`
  (`750ac0c`). Detalle en `docs/design/SANDBOX.md`.
* Integridad del commit con un hook `pre-commit` (`15c8ad0`), instalado y probado en este repositorio.
* `AGENTS.md` v2.1.0, la skill `boundary-validator` y la plantilla `implementer` al día (`f4189ea`,
  `429d5ff`, `1bdcd90`); `PROCESO.md` con el estado de las correcciones (`6c5ee4b`).
* F6, los hooks deciden igual con y sin el shim y con el Python 3.9.6 del sistema (`a21fbfc`).
* A15, la fase roja y la verde de los tests se comprueban en código (`17a05e1`).
* Coste de una escritura gobernada medido con la regla commiteada antes (`86a4550`, `6c2aa74`) y
  diseño de optimización para la v0.2 (`bc89176`, `fee798c`). Detalle en `docs/design/COSTE.md`.
* Traspaso y decisiones de la semana 1 en `docs/PLAN.md` (`7a7e362`, `fee798c`).

**Decidido (autor)**
* La lista de primitivas queda cerrada: cada forma nueva sería otro parche. La frontera de lo que se
  ejecuta es el sandbox, no la lista.
* Las órdenes de git que reescriben rutas gobernadas las ejecuta la persona con `!`.
* La integridad del commit entra en la v0.1; el formato del mensaje, en la v0.2.
* `.opencode/` no se gobierna: OpenCode se usa aquí solo para opinar, y se declara.
* El coste por escritura (1875 ms de mediana, umbral de 1 s) no se optimiza antes del lanzamiento.
* Decisiones de la semana 1: la señal de éxito, GitHub privado hasta el 25 de octubre y este DEVLOG.

**Salió mal y se aprendió**
* El implementador de F4b-2 cableó el hook antes de su `import`; el hook, que se relee en cada
  llamada, dio `NameError` y denegó todas las escrituras en `.py` gobernados, también la que lo
  arreglaba. Se devolvió a `HEAD` con permiso del autor. Ahora es AGENTS 6.5.
* La revisión de la integridad del commit encontró que `TESTS/x.py` pasaba junto a `tests/x.py` en un
  sistema de ficheros que no distingue mayúsculas; se corrigió antes de fusionar (`ceef6a7`).
* Un `git checkout <commit> -- <ruta>` que falla en el sandbox ya ha escrito el índice (S8): de ahí la
  integridad del commit.
* Errores del chat principal: un `python3 -` suelto en una orden (no ejecutó nada, pero AGENTS 4.2 lo
  prohíbe); un commit hecho con un test en rojo porque el `&&` seguía al `tail` y no a `pytest` (se
  rehízo; desde entonces se mira el código de salida de `pytest`); una lectura equivocada de la
  transcripción en S5 que el autor corrigió; y dos contratos con un detalle falso (`.actuarii.json`
  fuera de `governed_paths`, y que `deny_python_escapes.py` deniega `python3 -c`), que el implementador
  detectó y resolvió bien.

## 2026-10-06

Reconstruida. Suite: de 1768 a 2350 en verde.

**Hecho**
* Fase 1, pasos 5 y 6: el anuncio al abrir sesión (`453fd01`), la revisión ciega configurable
  (`1bce3ce`), fuera lo que solo servía a Traianus (`c199173`) y `AGENTS.md` genérico con sus
  subagentes y skills (`28848f5`). Fase 1 cerrada con 1979 tests (`4c68bdf`).
* Búsqueda previa: no hay nada igual; se ajusta la presentación, no el kit (`b13f88d`).
* Auditoría adversarial con pautas aprobadas antes de empezar (`d00af1e`): casos A01–A18 y plan de
  correcciones F1–F7 (`cac165d`).
* F1, el cableado del kit gobernado (`afe12bb`); F2, la puerta deniega por defecto (`65f6d30`); F3,
  entrada estricta del validador (`47f29be`); F4a, el recibo ata el contenido exacto (`d87032d`).

**Decidido (autor)**
* Calendario de tres semanas hasta el 25 de octubre y criterio de utilidad para retomar Traianus
  (`7910a63`).
* La auditoría adversarial se adelanta al empaquetado. F2 deniega por defecto y la matriz léxica se
  elimina en F4 (`c1669dc`).

## 2026-10-05

Reconstruida. Suite: 1497 en verde al cerrar la fase 0, 1768 al final del día.

**Hecho**
* Extracción del kit desde Traianus con la historia conservada; plan y `CLAUDE.md` (`5497eb4`).
* Fase 0: la suite pasa sin Traianus instalado (`49a6464`).
* Fase 1, pasos 1 a 4: los hooks no dependen del directorio actual (`cc81355`), la configuración del
  proyecto en `.actuarii.json` (`6cf5eb9`), los directorios del shim (`f7f1182`) y el registro de
  contratos (`7d5498a`) salen de ella.
