---
name: autor
description: Cómo trabajar con el autor de Actuarii: decide él; explicaciones sencillas con una recomendación; lo técnico se prueba ejecutándolo
metadata:
  type: user
---

El autor decide; Claude propone, recomienda y explica. Se trabaja en español.

Algunas decisiones dependen del detalle de los intérpretes y de los entornos de Python.
Cuando una decisión depende de ese detalle:
* explicarla con una imagen sencilla (las puertas son el árbitro: no pueden usar nada que el agente toque) y dar una
  recomendación, no un repaso de opciones;
* proponer que la prueba sea la ejecución (tests rojos en la base y verdes al final, con `verify_red_green.py`), para que
  no tenga que fiarse de la lectura de Claude.

Claude tiene que tener memoria: sin ella no es válido (autor, 2026-10-13). En Actuarii es la de este directorio, bajo
código. Ver [[preguntar-ante-ambiguedad]] y [[pocas-peticiones-al-autor]].
