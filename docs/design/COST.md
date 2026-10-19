# Cost of a governed write (method and rule, before measuring)

Claude, 2026-10-07, with the author's thresholds. This document was committed before any figure was taken, and the
results were added afterwards, in §4, without touching §1 to §3.

Translated from Spanish on 2026-10-19 (ADR-033), with §6 reduced to a note. The original is in the history: this file
at `d3c3b41`.

## 1. What is measured

Besides the write itself, a governed write (`Edit`, `MultiEdit`, `Write`) costs:

1. **Tokens:** the proposal for `validate_proposal` repeats the text of the change (in an `Edit`, the `old_string` and
   the `new_string`; in a `Write`, the whole file).
2. **Validator time:** the MCP call to `validate_proposal`, round trip.
3. **Hook time:** the write's `PreToolUse` hooks (`require_boundary_validation.py` and `require_contract_context.py`),
   one Python process each.

## 2. How

* **Tokens and validator time:** from the transcript of the session of 2026-10-07, with `jq`:
  * each call to `validate_proposal`, with its input and its response;
  * the overhead of an `Edit`: the characters of the input of `validate_proposal` divided by the characters of the
    input of the `Edit` it gives the receipt to (the next `Edit` on the same file);
  * validator time: the time of the response minus the time of the call.
  * Tokens are estimated as characters divided by 4: there is no exact counter, and the ratio between the proposal and
    the `Edit` does not depend on that constant.
* **Hook time:** each hook command of `.claude/settings.json` that acts on an `Edit`, run 20 times with a fixed input:
  an `Edit` on a real governed `.py` file with its valid receipt (the full path: configuration, audit trail, computing
  the result and `ast`). Timed with `perl` and `Time::HiRes`, inside the sandbox, as they run in the session. The
  median of each hook is taken and the medians are added up (an upper bound: Claude Code can launch them in parallel).

## 3. Decision rule (author, 2026-10-07)

* **Nothing is optimised before the launch** if both hold:
  * the median time added per write (validator plus hooks) is below **1 s**;
  * the median token overhead of an `Edit` is below **3 times** its own size.
* If either fails, an optimisation design is written for v0.2, and the README declares the cost with the figures; the
  date of 25 October does not move.
* If what blows up is the cost of large `Write` calls, the action is to document in the README that `Edit` is
  preferred (which the `boundary-validator` skill already says), not to change the kit.

## 4. Results (2026-10-07)

**Sample:** 15 governed writes from two transcripts, each paired with its receipt by its exact content (the
`new_string` or the `content` is the `Implementation_Block`), without duplicates (the resumed session repeats the
history of the previous one): 13 `Edit` and 2 `Write`. Calls to the validator that were probes, with no write behind
them, are left out.

| Measure | Values (sorted) | Median |
|---|---|---|
| Validator round trip, ms | 189 204 208 440 446 493 1070 1378 1465 1557 1686 1741 1757 1984 2262 | **1378** |
| Hook `require_boundary_validation.py`, 20 runs, ms | min. 245, max. 354 | **254** |
| Hook `require_contract_context.py`, 20 runs, ms | min. 237, max. 259 | **243** |
| Token overhead of an `Edit` (characters of the proposal / of the `Edit`) | 1.01 1.01 1.02 1.03 1.03 1.05 1.06 1.08 1.09 1.09 1.12 1.21 1.26 | **1.06** |

**Applying the rule (§3):**
* Time added per write: 1378 + 254 + 243 = **1875 ms**, above 1 s. **Not met.**
* Token overhead of an `Edit`: **1.06 times**, below 3. Met. The two `Write` calls of the sample were one-line files
  (ratios 2.0 and 2.1, because of the fixed fields of the proposal).
* **Decision, by the rule:** nothing is optimised before the launch; an optimisation design is written for v0.2, and
  the README declares the cost with these figures.

**Breakdown, outside the rule (it does not change it):**
* The validator's server, run on its own with 20 requests in one process: **4 ms** per request; starting the server
  (435 ms) happens once per session. Almost all of the 1378 ms round trip is not the kit's work but the harness's.
* The round trip is bimodal: 6 calls below 500 ms and 9 above 1 s, unrelated to the size of the proposal (4676
  characters in 204 ms, 244 in 1741 ms). The session was in auto mode; one hypothesis, not checked, is that some calls
  go through the classifier's review because `validate_proposal` is not in `permissions.allow`.
* Each hook is almost all Python start-up (about 240 ms of the 250).
* The write itself, with its hooks, took a median of 205 ms from call to result in the transcript (the hooks can run
  in parallel).

**Candidates for the v0.2 design** (not decided): put `validate_proposal` in `permissions.allow` and measure again (if
the hypothesis holds, it is the bulk of the cost); join the two write hooks in a single process (about 240 ms less);
start Python with less work (`-S`, `-I`) in the hooks.

## 5. Optimisation design for v0.2

**Goal:** the median time added per governed write below 1 s, measured with the same method (§2) and with the rule
committed again before measuring. Three steps, in this order, each measured on its own to know how much it brings:

1. **The validator in `permissions.allow`.** Add `mcp__boundary-validator__validate_proposal` to the allow list of
   `.claude/settings.json`, and its equivalent to `opencode.jsonc` (AGENTS 7.1 requires the same perimeter). It opens
   nothing: the tool only validates and notes in the audit trail, which the server writes. It tests the hypothesis of
   §4: if the round trip drops to the fast branch (about 200 ms), it was auto mode's review. It is one line of
   configuration and a change in the perimeter's tests.
2. **One process for the write hooks.** Today `require_boundary_validation.py` and `require_contract_context.py` each
   start their own Python for the same write. A single entry hook that imports both and runs them in order, without
   changing their logic or their messages, saves one start-up (about 240 ms). Following AGENTS 6.5: first the new
   hook, tested; then the change to `settings.json`; the two old ones stay as modules.
3. **A lighter Python start-up in the hooks** (`-I`, `-S`, which the shim already accepts): less work at start-up and,
   with `-I`, no `PYTHONPATH` and no user directory, which is also safer. It is measured before deciding; if it saves
   nothing noticeable, it is not done.

**Note (2026-10-19):** step 1 was done on 2026-10-14 (`f5517ae`), for another reason: the permission perimeter of
ADR-012, which ADR-022 keeps, allows `validate_proposal` so that it does not ask. The cost has not been measured again
since. Steps 2 and 3 are not done: the two write hooks still start one Python each, without `-I` or `-S`.

**Alternative to steps 2 and 3 (the author's idea, 2026-10-07): a resident process.** Start Python once per session,
the first time it is needed, and keep it alive: the hooks become minimal clients (an `sh` that passes it the input and
returns its decision), without starting an interpreter at every call. It generalises: it works for every hook, and for
a project that is not in Python the kit stops costing a Python start-up per write. What has to be solved first:
* **Old code running:** like the MCP server, the process runs the code it started with; a change in a gate requires
  restarting it, and today the hooks are read again on every call (AGENTS 6.5). It needs to detect that its code
  changed (by hash) and restart or deny.
* **No process, deny:** if it does not answer, the client denies; the gate is never skipped.
* **A private channel:** a Unix socket with permissions for the user only. The sandbox does not let `Bash` connect to
  Unix sockets by default, so the agent cannot talk to it or impersonate it. It could kill it, and then everything is
  denied: a block, not a hole.
* **Measure it** with the same method as steps 2 and 3 before choosing.

**Estimate** (to be checked, not taken for granted): about 200 ms of validator and about 150 ms of hooks, below 500 ms
in total. **Outside this design:** removing the call to the validator (the receipt is the guarantee) or caching
receipts (it would break the receipt binding an exact change).

## 6. Comparison with other configurations (the author's proposal, 2026-10-08)

A comparison of what it costs to govern with rules in code against governing with instructions in `CLAUDE.md`, on the
same task, was proposed and not run. It could come out for or against the kit, so the README claims nothing about
saving tokens. If it is run, it goes to v0.2, with its configurations, its number of runs and its reading rule
committed before measuring.
