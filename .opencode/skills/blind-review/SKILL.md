---
name: blind-review
description: Use when reviewing a record (a specification, a design or an instrument) blind to what its author wants to be true: before the code it specifies exists, or before that code is first used. Gives file:line evidence and a PASS/CHANGES verdict.
---

# Blind review

The question is never "is the author right" but "does this do what its record says, and can it
fail". The record is the document under review: what will be built, what it includes and
excludes, the rule that decides whether it worked, and the controls that can show it did not.

## Blindness

Run in a session that has not seen the expected result. Read **only** the review package: this
procedure, the base documents, the record and the files they cite. Do not look for anything the
package does not hold. If the expected result or a prior result is already in context, say so and
stop: the review is not blind.

## Phases and gates

Identify the phase first: a record whose code does not exist yet is reviewed in phase 1 only.

1. **Specification**, before the code exists.
   - Every step names the exact operation, its inputs, and what it includes and excludes.
   - Alternatives that are compared do the same work on the same inputs, or the difference is
     declared.
   - Nothing reads the answer it is judged against.
   - The decision rule and every threshold are fixed in advance, with where each comes from. A
     threshold without a source is a CHANGES item.
   - There is a control that must come out one way, and the record says what happens if it does
     not. A control that cannot fail is a CHANGES item.
   - Every shortcut the record takes (a simplified form standing for a full one) cites the base
     document that justifies it, and its conditions hold here. A missing justification is
     blocking.
   - Gate: every item answered, and the record committed (the caller's git facts show it). After
     the third round on one design, report the remaining non-blocking items for phase 2. A
     blocking item never passes to phase 2.
2. **Code**, before its first use.
   - Each record line maps to code, cited `path:line`. Unmapped lines, and code the record does
     not describe, are CHANGES items.
   - Seeds, data sources and parameters are the ones the record names.
   - Every shortcut has a test that checks it against the full form on inputs that satisfy its
     conditions. A shortcut without its test is blocking.
   - The tests can fail: they reject the bad inputs the record names, and a broken control makes
     one of them red. Tests that cannot fail are blocking.
   - Gate: every line mapped, and the record's commit precedes any commit holding a result of
     this code.
3. **Verdict**
   - `PASS`, or `CHANGES` with a numbered list, each item citing the record line and, in phase 2,
     `path:line`.
   - Tag every item **blocking** (it would change a result, a threshold, or whether a control can
     fail) or **non-blocking** (wording, a citation, a clarification). Only blocking items make
     the verdict `CHANGES`.
   - Give the text of the record's `Reviewed by:` line: reviewer, date, phase, commit reviewed,
     verdict.

## Rules

- **Read-only.** Never fix the record or the code yourself: report; the author changes it; the
  review runs again.
- **Blind by construction** (Claude Code): the package is built by
  `tools/audit/build_review_package.py build --lock` from the `review` key of `.actuarii.json`;
  while the lock is set, `tools/hooks/confine_review_reads.py` denies every Read, Grep and Glob
  outside the package. The caller clears the lock (`unlock`) when the verdict is in.
- **No code execution** of any kind. The review is done by reading.
- **No judgement of results.** If a result exists already, the review is late: say so in the
  verdict.
- **A failed control invalidates the run, not the rule.** Never suggest loosening a rule after a
  result is known.
