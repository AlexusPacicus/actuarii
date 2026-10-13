---
name: pocas-peticiones-al-autor
description: Al diseñar un cambio o un contrato, contar los pasos que caen en el autor y buscar el diseño que no los necesite
metadata:
  type: feedback
---

El sandbox deja a la persona todo lo que toca rutas gobernadas fuera del canal de recibos: `merge`, `switch`,
`restore`, borrar, reconectar el servidor MCP, volver a copiar el `pre-commit`. Cada uno es una petición al autor.

**Why:** el 2026-10-09 el autor señaló que había demasiadas peticiones para él; el contrato se rediseñó para que la
conversión la hiciera el instalador, que ya ejecuta la persona (`docs/DEVLOG.md`).

**How to apply:** en cada contrato, listar los pasos de la persona y buscar el diseño que los evite. Si `main` no se
ha movido desde la rama, avanzarlo por fast-forward dentro del sandbox (`git branch -f main <rama>` y
`git switch main`) en vez de pedir un merge. Relacionado: [[autor]].
