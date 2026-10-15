---
name: pocas-peticiones-al-autor
description: Al diseñar un cambio o un contrato, contar los pasos que caen en el autor y buscar el diseño que no los necesite; en Bash, solo órdenes de la lista, sin variables, cd ni bucles
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

**Bash:** cada llamada que pregunta es una petición. Mientras `ask` tenga el comodín `"Bash"`, preguntan todas: Claude Code
evalúa deny, luego ask y luego allow, y el comodín tapa la lista de AGENTS 7.1 (documentación de permisos, comprobado el
2026-10-15). Sin él, de las 352 llamadas del chat principal del 14 habrían preguntado 231: 80 por la forma de la orden
(variables, `cd`, bucles), 84 por herramientas de lectura fuera de la lista (`cut`, `jq`, `awk`) y 67 porque escribían.
El autor lo señaló el 2026-10-15. Una orden por llamada, desde la raíz, con rutas literales del proyecto o del
scratchpad, sin variables, `cd`, bucles ni `$(...)`; los ficheros se leen con `Read`, que no pregunta.
