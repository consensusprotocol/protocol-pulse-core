# heimdall_glm (z-ai/glm-5.3-flash, 198.3 s, $0.005, finish stop)

# FORENSIC CODE REVIEW — pp-ingest, ruling 40 P1/P2 diff (a9a5491a → working tree)

Scope: the diff (ledger.py, flagcheck.py, service.py, stats.py) reviewed against the full package. Only issues verifiable from the provided code.

---

## SECTION 1: CORRECTNESS

### 1.1 The main flow, traced

`check_once` (service.py:453-493) → `check_row` (service.py:418-451) → `flagcheck.ask` → `flagcheck.record` → `Service._append` → `ledger.carry_forward` → `ledger.append`. The adapter (`ledger.best_unused_moments`) then reads `effective_risk`.

**Verified correct:**
- Release logic: `check_valid` (ledger.py:215-226) requires flag ∈ RELEASE_ON_CHECK, answer ∈ ANSWERS, prompt_version == flagcheck.PROMPT_VERSION, model present and ≠ mined.model. `effective_risk` (ledger.py:229-241) releases only on a counting "no". Accusation is not in RELEASE_ON_CHECK (ledger.py:212), so it can never be released. Answers Q1.
- Fail-closed: any exception in `check_row` (service.py:444-448) sets `check_next` retry and records nothing; the flag stands. `ask` returning `{"answer": None, ...}` → `record` returns None (flagcheck.py:305-311) → nothing appended. Answers Q3.
- `carry_forward` (ledger.py:207-209) uses `setdefault(f, c)` so the new line's own answer wins; earlier answers travel. Answers Q2 partially.
- The stored ledger line keeps the miner's labels; only the adapter's returned view is rewritten (`_view`, ledger.py:244-246). The exclusion at ledger.py:347 now reads `eff`, not `l["risk"]`. Correct.

### 1.2 Bugs found

**B1 (real, P1): `check_once` reads the ledger WITHOUT the `mined.at`-order guarantee it assumes, and its `latest`-line selection can pick a line whose `risk` no longer contains the flag.** `latest[l["moment_id"]] = l` (service.py:470) takes the *last* line in file order. That is correct under the append-stamp ordering, but the hook pass and the moment pass both append; a hook line for the same moment_id carries the same `risk` (carry_forward unions, never shrinks — ledger.py:197), so this is safe. However: `check_row` then re-reads nothing — it appends `new` built from the *stale* line `l` it was handed (service.py:433). If a hook pass appended a newer line for the same moment between `check_once`'s read and `check_row`'s append, the check's new line will *not* carry the hook's `role_hint`/flags... except `carry_forward` (ledger.py:187-209) fixes exactly this, because `_append` re-reads earlier lines under `wlock` (service.py:282-285). **So this is actually closed.** Good design. But note: `carry_forward`'s `since` in `_append` is `discovered_ts - 86400` (service.py:282) — a moment whose video was discovered >24 h before... impossible here since expiry is 12 h. OK.

**B2 (real, P1): `check_row`'s appended line can lose the `mined.at`-order invariant that `offset_before` (ledger.py:122-149) depends on — marginally.** `append(stamp=config.iso)` (service.py:285) stamps *all* lines of the append with the *current* time, but the line's `mined.at` field inside `mined` was copied from the stale line `l` (via `json.loads(json.dumps(l))`, service.py:433) and then overwritten by the stamp — fine. But the *bisection* in `offset_before` assumes lines are in mined.at order; the check loop appends concurrently with the hook loop, both under `wlock`, both stamped at append time — order is preserved. OK. No bug. (Documented margin of 1 day covers it; ledger.py:127-128.)

**B3 (real, P0-adjacent): `check_once`'s calibration runs *inside* the 30 s loop thread and blocks it.** `watcher_checkers` → `calibrate` (flagcheck.py:271-302) asks 24 probes × N back-ends synchronously. At start (`check_calibrated = 0.0`) this runs on the first `check` loop iteration; with muse's documented 84 s latencies (providers.json:42) and 6 workers, this can take many minutes. Meanwhile the loop's `_loop` delay calculation (service.py:616) just delays the *next* iteration — no crash, but the check loop is effectively down for the calibration duration, and this happens **again every 24 h** (CHECK_RECALIBRATE_S, service.py:61). Not a correctness bug, but the "every 30 s" claim (service.py:12) is false during calibration. Also: calibration cost is *not* counted against any budget guard — `calibrate` calls `router.run` directly with no `can_spend` (flagcheck.py:281), unlike `ask` (flagcheck.py:256). Under the spend freeze this is Heimdall-only so it's cents, but it's an inconsistency: the A/B and flagcheck main paths both honour budgets; the watcher's recurring daily calibration does not.

**B4 (real, P1): race between `check_once`'s in-flight registration and `check_row`'s retry.** `check_inflight.discard(key)` happens in `check_row`'s `finally` (service.py:449-451) *before* the next `check_once` may re-add it — fine. But `check_next[key]` is set inside `check_row`'s exception handler *and* for partial answers (service.py:429-431), while `check_inflight` is cleared in `finally` — the ordering is: exception handler sets check_next, then finally discards. Correct. However, if `check_row` succeeds fully, `check_next` is never cleared/updated — the next `check_once` recomputes `flags` via `check_valid` (service.py:481) which now finds the answer, so the row drops out. Correct. No bug.

**B5 (real, P2): `miners` in `check_once` collects back-ends/models from *every* line of the video (service.py:471-473), including hook-pass lines.** `checkers` (flagcheck.py:241-247) then excludes any back-end whose id or model mined *any* line. Since the hook pass uses the same chain as `mine` (providers.json:83-84), this is usually the same set — but if a re-mine ever used a different back-end, the checker pool shrinks. With the flagcheck role's two Heimdall back-ends (glm, muse) and the mine chain (qwen, local_gemma), there's no collision today. Latent, not active. But: if the mine chain ever gains glm or muse, `checkers` returns [] and *nothing is ever checked* — silently, logged only at calibration. Fail-closed, but invisible.

**B6 (real, P2): `check_row`'s `v` fallback (service.py:435).** `self.q.video(l["video_id"]) or {"video_id": ..., "discovered_ts": self.clock()}` — if the video row is missing (purged? no, videos rows are never deleted; but a handoff-only ledger line would lack one), `_append`'s `since` becomes `now - 86400`, which may miss earlier lines of that video if it was discovered >24 h ago. Given the 12 h expiry, harmless. Note only.

**B7 (verified non-issue):** `stats.py` `ck["rows_checked"] += 1` counts *events*, not rows — one event per check_row invocation with ≥1 answer (service.py:437). A row with 2 flags = 1 event. The field name says "rows_checked"; it counts check *batches*. Minor mislabel; the answers dict is accurate.

**B8 (real, P2): `remeasure`'s `before` key.** flagcheck.py:520: `dict(r, checks={"accusation": c}, before=r["checks"]["accusation"])` — if a saved result's `checks` lacks "accusation" (shouldn't, since `main` always asks all three), KeyError. Saved runs from this same tool always have it. Fragile but not broken.

**B9 (verified):** `prompt(row, flag, sharpened)` (flagcheck.py:163-170) — `SHARPENED` only contains "accusation"; for imperative/SSB with `sharpened=True` it falls through to `DEFINITIONS`/`QUESTIONS` correctly (`flag in SHARPENED` guard). Correct.

**B10 (real, P1): the watcher's check answers are recorded under `PROMPT_VERSION = "flagcheck/1"` (flagcheck.py:39) even though the *sharpened* definition exists.** If the orchestrator later adopts the sharpened definition for the watcher, `check_valid`'s `prompt_version != flagcheck.PROMPT_VERSION` check (ledger.py:223) will invalidate all old answers — correct fail-closed behaviour, but the *remeasure* tool records answers under the same `PROMPT_VERSION` via `record()` (flagcheck.py:310) while actually using `SHARPENED_VERSION` prompts. Those remeasure answers are written to remeasure_accusation.json, not the ledger, so no contamination — but if anyone later merges them into ledger lines, `check_valid` would accept a sharpened-definition answer as a flagcheck/1 answer. Currently latent (remeasure never writes the ledger — flagcheck.py:527-528 confirms). Note it.

**N+1 / performance:** `check_once` reads the whole recent ledger every 30 s (service.py:467). `ledger.read` with `from_time` bisects (ledger.py:161), so it's the tail only — the design doc claims 16-25 s per 100k lines for a *full* read; the bounded read is the mitigation and it's tested (`test_the_bounded_read_returns_exactly_what_a_full_read_returns`). Every 30 s is frequent but the read is bounded. Acceptable; worth noting the constant 30 s polling of a file that changes every few minutes.

**Concurrency:** `check_inflight`/`check_next` guarded by `clock_lock` (service.py:430, 445, 450, 475-488) — consistent. `wlock` serializes all ledger appends. `check_row` runs on `self.checks` (4 workers) while `hook`/`mine` run on other pools; all ledger writes funnel through `_append` → `wlock` → `ledger.append` (which also flocks). Sound.

**Edge cases:**
- Empty ledger: `ledger.read` returns ([], []) (ledger.py:158-159); `check_once` returns 0. Fine.
- All checkers fail calibration: `check_allowed = []` → `check_once` returns 0 after logging (service.py:464-465). Flags stand. Fail-closed. ✓
- `check_row`'s `flags` list: if `ask` returns unmeasured for one of two flags, `got` has 1, `len(got) < len(flags)` → retry scheduled, and the *partial* answer is still appended (service.py:432). Correct: measured answers are kept, unmeasured retried. ✓

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|---|---|---|
| **L-x** (no single model; ≥2 back-ends/role; judge ≠ generator) | **COMPLIANT** | flagcheck role: 2 Heimdall back-ends, neither in the mine chain (providers.json:85-86, 80); `checkers` excludes the miner by id *and* model (flagcheck.py:247); `check_valid` re-checks model ≠ mined.model at read time (ledger.py:224). |
| **L-l** (reply counts only whole; nothing repaired) | **COMPLIANT** | `validator` (flagcheck.py:173-200) strict; `record` returns None for anything not in ANSWERS (flagcheck.py:307); unmeasured → nothing appended, flag stands. |
| **L-j / L-m** (fail closed; unmeasured ≠ pass) | **COMPLIANT** | `effective_risk` keeps the flag on yes/unsure/none/invalid (ledger.py:236-240); `check_once` skips when no checker passed calibration (service.py:464); `check_next` retry on partial/failed. |
| **L-u** (hard exclusions) | **COMPLIANT, with the ruling's own carve-out** | Only imperative/SSB releasable (ledger.py:212); accusation never (P2). Exclusion now on `eff` (ledger.py:347). |
| **L-v** (speaker change; re-uploads) | **COMPLIANT** (unchanged) | ledger.py:351-354. |
| **L-h/L-k** (read as spoken; records never rewritten) | **COMPLIANT** | Stored lines untouched; `_view` copies (ledger.py:246). |
| **Spend freeze** | **COMPLIANT** | flagcheck role is Heimdall-only; frozen vendors refused in `Router.available`/`_try`. |
| **B1-B4 (merge audit)** | **COMPLIANT** | B1: notice-never-halt unchanged. B2: outage/partial logic untouched. B3: gpu0.held check untouched. B4: age-gate marks untouched. |

One **PARTIAL**: the daily recalibration (service.py:61, 457-459) runs `calibrate` with no budget guard (flagcheck.py:281) — inconsistent with `ask`'s `can_spend` (flagcheck.py:256). Not a violation today (Heimdall, cents), but the pattern is there.

---

## SECTION 3: SECURITY

- **SQL**: all queue access is parameterized (`q.rows`/`q.x` with `?`); stats.py:115, 124 use `?` correctly. No injection. ✓
- **Secrets**: `Keyring` never prints values (providers.py:177-187); `redact` applied to error detail/raw before recording (providers.py:820-822); `remeasure`'s `on_attempt` pops `content` (flagcheck.py:500) — but note the *main* `flagcheck.main`'s `on_attempt` also pops content (flagcheck.py:552) while the *service's* `_on_attempt` (service.py:154-160) does NOT — it writes the full `rec` including `content` (the raw reply) to replies_log. That's the reply, not the key; keys are redacted upstream in `_try` (providers.py:820-822). ✓. However `rec` may include `raw` (truncated body) — also redacted. ✓
- **Untrusted prompt content**: `mine._untrusted` escapes `<` (mine.py:234-237); flagcheck's `prompt` uses it for channel/title/date/text (flagcheck.py:167-170). ✓
- **Override host restriction**: `override_allowed` (providers.py:135-144) — hostname must be loopback or match configured scheme+host. ✓. Note: it compares `u.scheme == c.scheme` but not port — a same-host different-port override is allowed, which is the documented drill case. Fine.
- **Filesystem**: `purge` restricts deletions to spec-validated absolute paths outside FORBIDDEN (purge.py:76-77, 344). `handoff` uses `os.link` + finally-unlink (tools/ingest_watch.py:130-135) — write-once, no clobber. ✓
- **Rate limiting**: Heimdall bounded at 12+8+4+4 in-flight, global 20 (providers.json:4, 24, 33, 43); the check loop adds at most 4 concurrent questions (service.py:59). The comment "Heimdall stays under ~20" (service.py:59) — but the *watcher* also runs mine (12) + hook (4) + check (4×1 question each, but each `ask` is one router.run = 1 in-flight) = 12+4+4 = 20, exactly at the global cap, plus the *daily calibration* which uses `int(a.max_inflight)`... no, `watcher_checkers` uses `workers=4` (flagcheck.py:314) — 4 concurrent calibration calls *on top of* whatever mine/hook hold. The Router's global semaphore (providers.py:681) caps it at 20, so it's bounded, but calibration competes with mining for slots. Not a leak, just contention.

No hardcoded secrets found. No auth surface (no HTTP server).

---

## SECTION 4: FRONTEND QUALITY

No UI in this diff. The "reports" are markdown/JSON: `write_md` (flagcheck.py:423-480) renders every table, calibration, Wilson CI, examples — genuinely thorough. `stats.live` → live.json is the operational dashboard; `second_model_checks_12h` (stats.py:114-130) gives answers/released/cost/calibration. Loading/error/empty: N/A (no async UI). Not scored heavily.

---

## SECTION 5: BACKEND QUALITY

- **DB writes**: `Queue` uses `isolation_level=None` (autocommit) with a single connection + RLock (queue.py:77-79). No explicit rollback, but autocommit + WAL + `synchronous=FULL` (queue.py:82) is a defensible choice for this write pattern; a crash mid-`x()` loses nothing that matters (state is re-derivable). The *ledger* is the durable artifact and it's fsync'd + flock'd + torn-tail-sealed (ledger.py:45-66, 69-85). Excellent.
- **External calls**: every `router.run` has timeout, retry, breaker, backoff, budget. `ask` catches `AllBackendsFailed` (flagcheck.py:263-265). `check_row` catches everything (service.py:444). ✓
- **Loop failure**: `_loop` catches Exception, logs, continues (service.py:608-617). ✓. But: a *BaseException* (KeyboardInterrupt) in a loop thread kills that thread silently — `check_once`'s calibration could die this way; the loop's `except Exception` won't catch it and the thread exits. Minor; the other loops have the same exposure and it's a known pattern.
- **Memory**: `check_once` builds `latest`/`miners` dicts from the 12h+1d ledger tail every 30 s (service.py:468-473) — bounded by expiry, fine. `calibrate`'s `res` is small. No leak.
- **Logging**: `check_row` logs answers with moment_id, channel, released flags (service.py:440-443); crashes get full tracebacks in events (service.py:447). Good. `check_once`'s calibration log (service.py:462-463) is the only visibility into *why* nothing is checked — adequate.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Already excellent (say so):** the fail-closed discipline is exemplary — every failure path (outage, crash, unmeasured, calibration miss, definition drift) leaves the flag standing, and it's *tested* (TestSecondModel::test_anything_but_a_counting_no_keeps_the_flag, 6 parametrized cases). The carry_forward mechanism solving the "later line drops earlier knowledge" problem across concurrent passes is the kind of thing most teams get wrong. The calibration-gated checker (a checker that misses a known case never releases anything, flagcheck.py:314-318) is genuinely sophisticated.

**Material gaps:**

1. **No observability into check *latency* or checker identity over time.** `second_model_checks_12h` counts answers but not p50/p95 latency per flag or which back-end answered. When muse's 84 s latencies (providers.json:42) starve the 4-worker check pool, you'll see it only as a rising `check_next` retry count — invisible in live.json. One field: `check_latency_p50_s` from the `calls` table (role='flagcheck', kind='ok').

2. **The 30 s poll of the ledger tail is wasteful and will bite at scale.** Every 30 s: bisect + read + parse the 13-day... no, 12h+1d tail. At 100k lines/day (the design's stated scale) that's ~50k lines parsed 2,880×/day. An mtime check (one `os.stat`) before the read would eliminate 95%+ of the work. Trivial, material.

3. **No per-flag cost attribution in the answers.** `ck["usd"]` is the role's total; you can't answer "what did releasing imperative flags cost vs SSB" without grepping replies_log. Given the ruling's "it is cents" justification, proving it continuously is the difference between a ruling and a hope.

4. **`check_next` is in-memory only.** A service restart loses all retry timers (service.py:104) — harmless (they're recomputed), but `check_inflight` too: a crash mid-`check_row` after `ask` succeeded but before `_append` loses the paid-for answer. The reply is in the Router's cache (providers.py:855-864), so the retry is free — this is actually fine. Say so: the cache makes the in-memory state safe. Good.

5. **What Bloomberg/Coinbase would add:** a *decision log* — when the adapter's exclusion count changes because of a release, the coverage report (or STATE) should say "n moments released by second-model disagreement today". Currently `released_by_the_second_model` (ledger.py:367) lives only in the adapter's report, which the packager consumes but nobody surfaces. The ruling's whole point was precision-vs-coverage tradeoff; the number that proves the tradeoff is right is not surfaced anywhere a human looks.

---

## SECTION 7: SCORES

- Backend logic: **88**/100 (B3/B5/B10 are latent; the core release logic is airtight and tested)
- Frontend/UI: **75**/100 (markdown reports only; thorough but no surfaced decision log)
- Error handling: **92**/100 (fail-closed everywhere; the one gap is calibration's missing budget guard and BaseException-in-loop)
- Security: **90**/100 (parameterized SQL, redaction, host-pinned overrides; no auth surface to miss)
- Performance: **78**/100 (30 s ledger-tail re-read; calibration blocking the loop; otherwise bounded)
- Law compliance: **95**/100 (all laws; the calibration-budget inconsistency is the only dent)
- World-class gap: **80**/100 (excellent mechanics; the *decision* — how many moments the second model freed — is invisible to humans)
- **OVERALL: 86/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | none — the diff is production-safe as written | — | —

P1 HIGH | Add a budget/`can_spend` guard (or at least a cost log) to the watcher's daily recalibration | flagcheck.py:281, service.py:457-459 | the only unguarded model spend in the watcher; it recurs daily forever and competes with mining for the global 20 slots

P1 HIGH | Add an mtime short-circuit to `check_once`'s ledger read | service.py:467 | at the design's 100k-lines/day scale, parsing the 13-day... (12h+1d) tail every 30 s is 2,880 wasted reads/day; one `os.stat` skips ~95%

P1 HIGH | Surface `released_by_the_second_model` (and released moment ids) in the daily coverage report or STATE | ledger.py:367, coverage.py (absent) | the ruling's justification ("it is cents", precision tradeoff) is currently unmeasurable by anyone who doesn't read the adapter's stderr

P2 MEDIUM | Record check latency (p50/p95) and answering back-end per flag in `second_model_checks_12h` | stats.py:114-130 | muse's 84 s p90 (providers.json:42) starving the 4-worker pool is invisible today; you'd see it only as rising retries

P2 MEDIUM | When the mine chain gains a back-end, `checkers` silently returns [] and nothing is ever checked | flagcheck.py:241-247, service.py:464 | fail-closed but silent; log it at calibration (it does, service.py:462) AND in `check_once` when `check_allowed` transitions to empty

P2 MEDIUM | Give the sharpened-definition answers their own prompt_version if they ever enter the ledger | flagcheck.py:310 vs 39 | `record()` stamps PROMPT_VERSION regardless of `sharpened`; today remeasure never writes the ledger, but the trap is armed

P3 LOW | Rename `rows_checked` → `check_batches` in `second_model_checks_12h` | stats.py:114 | it counts events (one per check_row with ≥1 answer), not rows; a 2-flag row is 1

P3 LOW | Guard `remeasure`'s `r["checks"]["accusation"]` with `.get` | flagcheck.py:520 | KeyError on a hand-edited or older saved run

---

## SECTION 9: THE ONE THING

Surface the ruling's payoff — how many moments the second model actually released, per day, per flag, at what cost — somewhere a human reads (coverage report, STATE), because right now the entire P1 mechanism is invisible outside the adapter's stderr and you cannot defend the ruling's "it is cents" without that number.

---

## SECTION 10: FINAL VERDICT

Ready for production. The release logic is correct, fail-closed on every path, and unusually well tested; the concurrency (wlock + carry_forward + reply cache) closes the stale-line traps that usually kill this pattern. Fix the calibration budget guard and the 30 s ledger re-read before the ledger reaches the 100k-lines/day scale, and surface the released-count — those are the only things standing between this and a genuinely exemplary implementation.