---
name: autor
description: How to work with Actuarii's author: the author decides; simple explanations with one recommendation; technical claims are proved by running them
metadata:
  type: user
---

The author decides; Claude proposes, recommends and explains. The conversation is in Spanish; the repository's
documents are in English (ADR-032).

Some decisions depend on the detail of interpreters and Python environments. When a decision depends on that detail:
* explain it with a simple picture (the gates are the referee: they cannot use anything the agent touches) and give
  one recommendation, not a survey of options;
* propose that the proof be a run (tests red at the base and green at the end, with `verify_red_green.py`), so that
  the author does not have to trust Claude's reading.

Claude must have memory: without it, it is not valid (author, 2026-10-13). In Actuarii it is the memory of this
directory, under code. See [[preguntar-ante-ambiguedad]] and [[pocas-peticiones-al-autor]].
