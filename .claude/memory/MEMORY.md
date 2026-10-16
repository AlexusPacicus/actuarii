# Memoria de Claude en Actuarii

Memoria bajo código (decisión del autor, 2026-10-13):
* un fichero por recuerdo en `.claude/memory/`, con este índice, que `CLAUDE.md` carga al abrir cada sesión;
* cada escritura pide recibo (`.claude/**` está gobernado), `Bash` no la toca (el sandbox protege `.claude/`) y git
  guarda cada versión;
* la memoria automática de Claude Code (`~/.claude/projects/…/memory/`) está apagada en este proyecto:
  `autoMemoryEnabled: false` en `.claude/settings.json` (ADR-010). Es un ajuste, no una denegación: un
  `.claude/settings.local.json` o la variable `CLAUDE_CODE_DISABLE_AUTO_MEMORY` pueden volver a encenderla;
* será el corpus del primer piloto de la memoria de agentes de la fase 4 (`docs/PLAN.md`).

Cada recuerdo lleva el formato de la memoria de Claude Code: frontmatter con `name`, `description` y `metadata.type`
(`user`, `feedback`, `project` o `reference`). No se guarda lo que ya registran el repositorio, el DEVLOG o el PLAN.

- [Cómo trabaja el autor](autor.md) — decide él; explicaciones sencillas con una recomendación; lo técnico se prueba ejecutándolo.
- [Preguntar ante la ambigüedad](preguntar-ante-ambiguedad.md) — una respuesta ambigua no es una decisión del autor.
- [Pocas peticiones al autor](pocas-peticiones-al-autor.md) — contar los pasos que caen en él y buscar el diseño que los evite; en `Bash`, solo órdenes de la lista, sin variables, `cd` ni bucles.
