---
name: instrument-audit
description: Use when reviewing an instrument audit record (step 2(a) of docs/methodology/METHODOLOGY.md) — before a measurement script is written, or before its first run — blind to the hypothesis, with file:line evidence and a PASS/CHANGES verdict.
---

# Instrument audit review

Step 2(a) of the research loop as a review. The question is never "is the hypothesis right" but
"does this instrument measure what its record says, and can it fail". Record template and
vocabulary: `docs/methodology/instrumentation/INSTRUMENTATION.md`.

## Blindness

Run in a session that has not seen the hypothesis. Read **only** the record's code block and the
source files it names. Do not open the hypothesis, refuters or claims sections of the document
that holds the record, nor any prior result. If the hypothesis is already in context, say so and
stop: the review is not blind.

## Phases and gates

Identify the phase first: a record whose script does not exist yet is reviewed in phase 1 only.

1. **Specification** — before the script exists.
   - Every column names the exact operation, what it includes and excludes, per arm.
   - Every arm does the same operation on the same inputs, or the difference is declared.
   - No arm reads the ground truth or labels it is judged on (leakage).
   - The decision rule and every threshold are fixed, with their derivation. A threshold without
     one is a CHANGES item.
   - There is a control that must come out one way, and the record says what happens if it does
     not. A control that cannot fail is a CHANGES item.
   - Every shortcut the record takes (a simplified form standing for a full one) cites an entry
     in `frontend/audits/derivations.md` whose conditions hold here. A missing entry is blocking.
   - Gate: all items answered; the record is committed (`git log` shows it). After the third
     phase-1 round the record freezes: report remaining items for phase 2, verdict stays open.
2. **Code** — before the first run.
   - Each record line maps to code, cited `path:line`. Unmapped lines, and code the record does not
     describe, are CHANGES items.
   - Check the seven known failure patterns (`docs/methodology/papers/PAPERS.md`): unequal work
     per arm, re-processing earlier state, reflection vs. rotation, skipped work, sequential
     access, unsubtracted harness overhead, labels reused as ground truth.
   - Seeds, data source and frame are the ones the record names.
   - Every derivation the record uses has a unit test that checks the equality on random inputs
     satisfying its conditions. A derivation without its test is blocking.
   - The code matches the measurement's contract in `frontend/audits/contracts.md` down to the
     data layer: digests checked, dtypes and casts, byte order, draw order, thread settings,
     result format. A mismatch is blocking.
   - Gate: every line mapped; the record's commit precedes any commit containing a result of this
     script (`git log --follow` on both).
3. **Verdict**
   - `PASS`, or `CHANGES` with a numbered list, each item citing the record line and, in phase 2,
     `path:line`.
   - Tag every item **blocking** (it would change a result, a threshold, or whether a control can
     fail) or **non-blocking** (wording, a citation, a clarification). Only blocking items make the
     verdict `CHANGES`; with none, the verdict is `PASS` and non-blocking items are listed for the
     author to fix before phase 2.
   - Fill the record's `Reviewed by:` line: reviewer, date, phase, commit reviewed, verdict.

## Rules

- **Read-only** except the `Reviewed by:` line. Never fix the instrument yourself: report, the
  author changes it, the review runs again.
- **As a subagent** (`.claude/agents/instrument-auditor.md`, AGENTS 6.1): the caller supplies the
  git gate facts and writes the `Reviewed by:` line from the verdict; the reviewer changes nothing.
- **No code execution** of any kind, including empty or exploratory `python3` calls (AGENTS 2.5).
  The review is done by reading; `git log` / `git status` are the only commands needed.
- **No judgement of results.** If a result exists already, the review is late; say so in the
  verdict.
- **A failed control invalidates the run, not the rule.** Never suggest loosening a rule after a
  result is known (step 3 of the loop).
