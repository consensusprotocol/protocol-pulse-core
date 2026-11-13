# glm-5.3-flash (z-ai/glm-5.3-flash) 60 s finish=stop usage in 7707 / out 1644 usd~0.048 (upper-bound price)

# Audit: item 55 deadline evidence log (C1_STEP.diff)

## Verified from the diff

**Fields the order names.** The order asks for (model, prompt size, seconds). `missed_deadline` (providers.py:50-52) writes `model`, `prompt_chars`, `seconds` (== `deadline_s`, correct: the call is abandoned *at* the deadline), plus `role`, `vendor`, `deadline_s`, `max_tokens`. `answered_slowly` (providers.py:60-64) adds `threshold_s` and token counts. Both kinds carry everything the order names. ✔

**Exactly once.** Each log point sits on a mutually exclusive path: `missed_deadline` inside the `DeadlineExceeded` handler before `continue`; `answered_slowly` after a successful `_settle`, before the empty-reply check. No loop, no retry of the log call itself. ✔

**Cannot change the call's outcome or the ledger.** `_log_slow` (providers.py:28-41) runs after `_settle`/`tried.append` on the success path and after the settle+append on the deadline path; it returns early when `deadline_log` is falsy; the only caught exception is `OSError`, which becomes a notice. It never touches the ledger, `tried`, or the return value. One caveat below (P2-1) on the notice path. ✔ (with caveat)

**Concurrency.** The append is inside `self._log_lock` (providers.py:36-39), and each line is a single `f.write(line + "\n")` — one write call, so even without the lock, POSIX appends of <PIPE_BUF are effectively line-atomic; with the lock, interleaving within one Router instance is excluded. ✔ (caveat: see P2-2)

**Nothing secret.** Both records contain only: kind, role, model, vendor, deadline_s/threshold_s, seconds, prompt_chars, max_tokens, in, out, utc. No prompt text, no keys. ✔

**Tests.** The existing deadline test now asserts the missed line's kind/model/prompt_chars/max_tokens/deadline_s (test:115-117); the new test covers slow-logged (with tokens), fast-not-logged, and no-log-writes-nothing (test:125-145). ✔

## Findings

**P1-1 — `answered_slowly` is silently skipped when the reply is empty.** providers.py:60-65: the slow-answer log sits *before* the `if not (isinstance(text, str) and text.strip())` check, so that ordering is fine — but note the slow log fires even for an *empty* reply that the chain then moves on from. Conversely, if a back-end answers slowly *and* the reply is empty, you get the slow line but the "refused this request: an empty reply" outcome only in `tried`. That's arguably correct (both facts are evidence), but it means the Heimdall team's "answered slowly" count includes calls that produced no usable answer. If the order's "one 8-excerpt screen took 8 min" refers to a call that *did* answer, fine; if it refers to one that timed out at the *router* level, note that a `DeadlineExceeded` raised by the *caller* (not a back-end) — i.e., the whole chain exhausting — is never logged. Only per-back-end misses are. If the intent was "every missed deadline," a chain-level exhaustion (all back-ends miss) still produces one line per back-end, so coverage holds; but a caller-side deadline that aborts the chain before a back-end misses (if such a path exists — I cannot see the full `call()` body, only the excerpt) would go unlogged. **Uncertain: the diff shows only the excerpt; I cannot verify there is no other deadline path.**

**P2-1 — notice list grows unbounded on a persistent write failure.** providers.py:41: every failed write appends to `self.notices` with no cap. A read-only mount or full disk over a long build = one notice per call. Cosmetic; the call still succeeds. Also, `self.notices` is appended without holding `self._lock()` — if `notices` is read concurrently elsewhere, this is a benign-list race I cannot rule out from the diff (the Router's other lock usage isn't shown).

**P2-2 — lock is per-Router, not per-file.** providers.py:20: `threading.Lock` guards only this instance. If two Router instances (e.g., proof_ly.py:96-98 and proof_ledger.py:75-77, or a build + a proof script) point at the same `DEADLINE_LOG` path, their lines can interleave *between* processes/instances. Each line is still a single small `write()` under `open(..., "a")`, so O_APPEND keeps it line-atomic in practice on Linux; risk is theoretical. Also `os.makedirs` runs on every log call inside the lock — trivial cost, but it's per-write.

**P2-3 — `import threading` inside `__init__`.** providers.py:18: works, but module-level import is the file's convention elsewhere (json/os/time are used bare at :34). Style only.

**P2-4 — test asserts `seconds >= 0.2` but the record's `seconds` comes from the back-end's self-reported third return value.** test:128-131, 139: `Took.complete` returns a *constant* 0.25, and the production code logs whatever the back-end reports (`secs`), not a measured wall time. If the production `secs` is measured around the call (not shown in the diff), fine; if it's the back-end's self-report, the "8 min" evidence's accuracy depends on the vendor adapter. **Uncertain — the `secs` computation is not in the diff.**

**P2-5 — `answered_slowly` logs `in`/`out` from `usage` which may be None.** providers.py:63-64: `(usage or {}).get("in")` → `None` is written as JSON `null`. The test (test:137-138) asserts `1000`/`100` because the Fake supplies usage. A real slow answer with no usage report logs `null` tokens — acceptable, just note the Heimdall team may see nulls.

**P2-6 — the missed_deadline record's `seconds` field is redundant (== deadline_s).** providers.py:50-52. Not a defect; aids readability. No action.

## What I could not verify (not findings)

- Whether `secs` is wall-clock measured by the Router or self-reported by the back-end (P2-4).
- Whether any other code path in `call()` can miss a deadline without raising `DeadlineExceeded` (P1-1's uncertainty).
- Whether `self.notices` is consumed anywhere that assumes bounded size or thread-safety.
- Whether the `.jsonl` file's other writers (the backfill, "already done, not in this diff") coordinate with this lock — outside this diff.

## Verdict

**SHIP: yes**

The diff does what the order says, the evidence fields are complete, the log is strictly additive (fail-open by design, correctly documented as "evidence, never a gate"), the tests pin the behavior, and the P2s are cosmetic or theoretical. The one P1 is really a coverage question the author should confirm (chain-level/caller-side deadline paths), not a defect in what's shown.