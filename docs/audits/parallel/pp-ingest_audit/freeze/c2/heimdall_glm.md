# heimdall_glm (z-ai/glm-5.3-flash, 247.6 s, $0.004, finish stop)

# heimdall_glm (z-ai/glm-5.3-flash, cycle 2)

# CYCLE 2 — FINAL REVIEW — pp-ingest (branch pp-ingest, diff 9500030f)

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting, finding by finding:

**qwen's `offset_before` bisection premise (P0).** I caught the *symptom* (C10 in my cycle 1, "verified sound with the 1-day margin") but I did not state the mechanism as crisply as qwen: `mined.at` was the pass **start** while lines are appended at the pass **end**, so the file was in mined.at order only to within one mining pass. I had the margin argument right (a skipped line X satisfies mined.at(X) ≤ append(X) ≤ append(L) ≤ mined.at(L) + one pass < cutoff + 1 day, so it is never returnable) — but I presented it as "verified sound" without flagging that the *invariant was accidental, not by construction*. The integrator's fix (stamping `mined.at` under the append lock, `ledger.append(stamp=config.iso)`, ledger.py:47-50) is the right one and I should have demanded it. **Missed the leverage; caught the math.**

**The outage notice visibility (muse-adjacent, integrator c1).** I noted the outage path in C1/C2 but never asked "how does the integrator *see* a 3-day outage without polling the queue?" The `_outage_notice` → STATE-file mechanism (service.py:331-354, spend.py:53-65) is exactly the kind of operational surface I review and didn't. Missed.

**`mine_tries` semantics under the new partial regime (qwen-adjacent).** I read `_settle`'s `passes = int(v.get("mine_tries") or 0) + (1 if rejected else 0)` (service.py:249) and moved on. The subtlety — that an *outage* pass does not increment `passes` (correct: it "uses no try", service.py:34-35) but *does* overwrite `mine_tries` via `common` — means a video that oscillates outage→rejected→outage→rejected accumulates `passes` only on the rejected legs, which is the intended reading, but the *reason string* at service.py:277 prints "pass {passes} of 3" where `passes` counts only rejected legs. Cosmetic, but I missed that the counter and the message disagree about what a "pass" is.

**`fetch_once`'s BaseException handler re-raises into `ex.map` (glm C8, my own cycle-1 finding, but the *consequence* I missed).** service.py:187-191: the `except BaseException` branch sets state then `raise`s. Inside `list(ex.map(one, claimed))` (service.py:198), a KeyboardInterrupt in one worker propagates out of `ex.map` — but the `ThreadPoolExecutor` context manager (service.py:197) then calls `shutdown(wait=True)` *while the other workers are still running their `one()`*, and those workers' `except BaseException` handlers will also try to `self.q.set_state(...)` — which takes `self.q.lock`, which the main thread does not hold. Fine. But the *other* futures' results are discarded, and their videos stay `PROBING` until the next `recover()`. I said "the video is not left `probing`" (my C8) — true for the *raised* one, false for its siblings. Missed the sibling case.

**`stats.live`'s `span_h` when `disc` is empty.** stats.py:25: `min([d["discovered_ts"] for d in disc] or [now_ts])` — I read this as guarded, and it is. But `fresh`/`new` are then empty and `videos_seen_per_hour` = 0/1e-9 → 0.0. Correct. Nobody flagged it; neither did I; it's fine. (Listed here for completeness, not a miss.)

**What nobody caught, including me, until this pass — see §3.**

---

## 2. WHERE DO I AGREE OR DISAGREE?

### qwen3.8-27b

| finding | verdict | why |
|---|---|---|
| P0 `offset_before` bisects an unsorted file | **Partially agree, now moot** | The premise was right (order only to within one pass); the "silent data loss" was wrong (the 1-day margin covers it, exactly as the integrator's proof shows). The `stamp=` fix makes it exact by construction; tests `test_the_bounded_read_is_exact_while_lines_are_out_of_order_by_less_than_its_margin[1/20]` and `test_the_service_stamp_puts_the_file_in_mined_at_order` cover it. Downgrade to resolved. |
| P0 stats loads every waiting row | **Agree** | Fixed: stats.py:64 `SELECT state, COUNT(*) AS n FROM videos GROUP BY state`, and service.py:335 / stats.py:85-86 use `COUNT(*)` + `LIKE 'OUTAGE%'`. Resolved. |
| Ledger append race | **Agree (non-bug)** | qwen's own analysis concludes the reader's latest-wins dedup handles the crash-between-append-and-set_state window. I concur — and note the *cost*: the re-mine re-asks only failed windows (cache), so the duplicate lines are cheap. Resolved by design, correctly disclosed. |
| (its §1 "critical logic error" on AllBackendsFailed) | **Disagree — it refutes itself** | qwen's own §1 walks through the chain, finds heimdall not frozen, local_gemma skipped→`("skipped",...)`→`outage=True`, and concludes "the logic seems correct *if* AllBackendsFailed is raised" — which it is, via the exhausted-chain path at providers.py:768. There is no bug. This finding is 40 lines of thinking that conclude "no finding". |

### muse-spark-open-816b

| finding | verdict | why |
|---|---|---|
| watch.py:216 `/shorts/`-only Short detection | **Agree, P2** | Correct: playlist entries for Shorts frequently carry `watch?v=` URLs; the watcher marks them DISCOVERED, burns one probe, then fetch.py:157 (`media == "short"`) terminates them. One wasted yt-dlp probe per Short, and the coverage report counts it as published-then-Short (coverage.py:72-76 handles it: `is_short` checks the *state* OR the URL, so the report is right; only the probe is wasted). Real, minor, correctly priced. |
| watch.py:221-223 ISO string comparison | **Agree, P3** | `p > newest` on ISO-8601: both producers (watch.py:194 RSS `published`, `_ts_iso(ts_)` playlist) emit `+00:00`-suffixed UTC. Fragile only if a future producer emits `Z` — and `_parse_iso`/`_ts_iso` are the only producers. Correctly non-blocking. |
| fetch.py:173-176 future-dated `pub_ts` | **Agree, P2** | `now_ts - pub_ts > BACKFILL_H*3600` with `pub_ts` in the future → negative → not SEEN_OLD → proceeds to mine. But note: coverage.py:67 *does* bound the future side (`now_ts + 600`), so a future-dated video is invisible to coverage until its clock catches up, while the miner happily mines it. Asymmetric, harmless, worth one line in the reason. |
| mine.py:304-315 second observation's scores discarded | **Agree, P2** | Muse is right that the *better* score can be lost; the docstring (mine.py:277-279) discloses it. But the union-of-flags fix (mine.py:310-314) is the fail-closed direction for L-u, and scores-are-first's is deterministic. I'd take `max(rank_score)` — but it's a quality nit, not correctness. |
| ledger.py:44-45 torn-tail comment | **Agree, P3** | The comment "closed, so the first new line stays whole" is accurate; muse's "slightly misleading" is fair — the torn line is *isolated*, not *repaired*, and stays one bad line forever (read.py:169-171 counts it). Docstring at ledger.py:7 already says this. No action. |
| ledger.py:66-74 `seal()` (truncated in what I received) | **Agree, P3** | `seal` opens `O_WRONLY|O_APPEND` without `O_RDWR` — it never reads, only writes `b"\n"`, so it's correct; the flock is advisory but `append` takes the same advisory lock, so they互斥. Fine. |

### Consensus items (c1)

- **Outage count → SQL COUNT**: agreed, done, tested. stats.py:85-86, service.py:335.
- **Ledger order made exact**: agreed, done, *the right fix* (by construction beats by-argument). One residual: `append(stamp=...)` mutates the caller's `lines` in place (ledger.py:49-50) — `mine_video`'s lines are freshly built each pass so this is safe today, but `ab.py`'s results dict holds the same line objects and is re-serialized to `ab.json` *after* `router.release()` (ab.py:325-330) — the stamped `mined.at` therefore leaks into the A/B report's saved lines. Harmless (the report doesn't compare mined.at) but it's shared-mutable-state nobody noted.
- **Judge role entirely frozen**: agreed, disclosed, and the evidence (glm + muse reviewing 100k+ tokens coherently at effort none) is the right justification for a Heimdall-served judge later. Note the *consequence* nobody priced: with the judge frozen, `ab.py`'s `judge` is None, so `pairs` reports only overlap/hard-flag agreement — the A/B that decides whether mining migrates to the local model currently has **no quality dimension at all**. That's a process gap, not a code bug, but it means the next A/B run's conclusions are weaker than the design (§8) intends. P2.

---

## 3. NEW FINDINGS FROM THIS REVIEW

Things the combined cycle-1 record does not contain:

**N1. `mine_once`'s idle-release can starve a just-claimed video's back-end (service.py:292-294).** Sequence: `mine_once` runs, `free == 3`, `due(MINE_DUE, 1)` is empty → `router.release()` → `OllamaLocalBackend.release()` unloads the model. But `mine_once` returns *before* checking `due(MINE_DUE, free)` — no, wait, it returns. Next iteration 5 s later: a video became due in between; it's claimed; `mine_video` → `mine_window` → `router.run` → `local_gemma.complete` → `self._llm is None` → **`sm.LocalLLM(model=...).start()`** — a full model load, synchronously, inside the window's `_try`, under the back-end semaphore (`max_inflight: 1`) and the global one. With `timeout_s: 600` the *load* isn't timed by the HTTP timeout machinery at all (it's inside `complete`, before `_post`), so a slow Ollama load blocks one of 3 video workers for its full duration with no health recording (the `h.record` only fires on outcomes). Meanwhile the *other* two workers' windows queue on `self.sems[bid]`... which is the same semaphore, so they queue too. Net: one cold-start stalls the entire local leg. This is *by design* (B3: the integrator enables it under the lease) but the interaction — release-on-idle every 5 s of quiet, cold-start on next use, no load-timeout, no health signal — means an intermittently-quiet queue (exactly what a 10-min poll cadence produces) thrashes the model load/unload. **P2, real, nobody priced it.** Mitigation: release only after a longer idle (e.g. one POLL_S), or record the load as a latency event.

**N2. `_settle`'s `moments` count can exceed the ledger's lines for that video — permanently (service.py:267).** `moments = len(lines) if lines else int(v.get("moments") or 0)`. Consider: pass 1 rejected×3 → MINE_WAIT, `mine_tries=1`, no append. Pass 2: 1 window still rejected, others mined → `lines` = 4, appended; `moments=4`, MINED_PARTIAL. Pass 3 (6 h later): the last window now mines, `lines` = 6 (4 old + 2 new, the 4 old re-derive identical moment_ids) → appended (latest wins, correct), `moments=6`, still MINED_PARTIAL (no: `not failed` → MINED, moments=6). Good. Now: pass 3 is an *outage* → `lines=[]` → `moments = int(v.get("moments") or 0)` = 4. Correct. But pass 4: the last window *still* rejected, others re-mine → `lines` = 4 (same 4) → appended again (harmless, latest-wins) → `moments=4`. Now the ledger holds 6 distinct moment_ids for this video (4 + the 2 from pass 3) but the row says 4, and pass 3's 2 lines are in the ledger, returned by the adapter, yet never counted. **The row's `moments` is a count of the *latest pass's* lines, not of the video's ledger lines** — and since MINED_PARTIAL videos' moments are counted in `stats.moments` (stats.py:35, "partial videos' moments are in the ledger too"), the *sum* double-counts nothing but *under-counts* what the ledger actually holds. The adapter is the source of truth and is correct; the stat is a lower bound. Nobody stated this precisely. P2, disclosure-level: the docstring at stats.py:35 says "in the ledger too" — true; the number is just not the ledger's count.

**N3. `coverage.check`'s future-published bound vs. `fetch`'s unbounded one (coverage.py:67 vs fetch.py:173).** Already noted in §2 (muse's finding) — the *new* part: a video whose `pub_ts` is >6 h in the future (clock skew, scheduled-then-published-early) passes fetch's SEEN_OLD check, gets mined, and then sits *outside* coverage's `now_ts + 600` window for its entire skew. It is mined, in the ledger, returned by the adapter (the adapter's only future-check is `pub > now`, ledger.py:253, which passes once the clock catches up) — but the coverage report for its entire first day lists it as... nothing: not published (coverage.py:67 skips it), so not missed, not mined. **A mined video invisible to the coverage metric.** Self-healing after the skew, but the day's report under-counts. P2.

**N4. `Keyring.redact`'s 8-char threshold drops short keys silently (providers.py:185).** `if len(v) >= 8 and v in s` — a 6-char key value (plenty of staging-gateway keys are short) is never redacted from error bodies that reach `calls.error`, `replies_log`, and the STATE notice. The docstring (providers.py:17-18) promises "never logged". P3; the fix is one line (drop the threshold, or make it 4).

**N5. `spend._rewrite_top`'s tmp file is per-PID, not per-(PID,call) (spend.py:47).** Two concurrent `_rewrite_top` calls from the same process (the health loop's `_meter_change` and `_outage_notice` can both fire within one `health_once` — service.py:314, 331-354) are serialized by the flock, so the *file* writes are safe; but both would use the same `tmp` path. They can't actually race: both are called from the same (health) thread, sequentially. However `write_state_notice` is also called from `_meter_change` which fires from `meter.measure()` inside `health_once` — same thread. And `cmd_once`'s `health_once` — same. So: no race today, but the safety rests on "only the health thread writes the STATE doc", which is nowhere stated. One-`f"tmp.{threading.get_ident()}"`-away from robust. P3.

**N6. `ab.py`'s `spent()` budget check is per-outer-iteration, not per-window (ab.py:274, 296).** `if spent() >= a.budget_usd: break` — checked once per *video*, so one video's windows can overshoot the budget by (windows−1)×cost. With `--budget-usd 25` and $0.0008/window this is noise; with a frontier judge at $0.02+/call it's 8% of the budget. P3, disclosed by "reached: stopping" semantics.

**N7. `contract.fingerprint()` imports `sentence_law` bare (contract.py:92) — after `config.ts()` (line 93) has put `pipeline/` on sys.path (config.py:17-18), so it resolves to the *pipeline's* `sentence_law`, not the selectid worktree's.** Meanwhile `eligibility`/`select_by_id` may have been loaded from the worktree via `_load_file` (contract.py:62-63). If the two trees' `sentence_law` diverge, the fingerprint mixes definitions from two trees while `verify_line` (contract.py:161-180) re-derives through `contract.sentences` → the *same* mixed sources, so it's self-consistent — but the *fingerprint* recorded in lines mined today would differ from one mined after the worktree's `sentence_law` changes even if the eligibility modules didn't, and vice versa. That's exactly what a fingerprint is for. Actually correct. But: `import sentence_law` at contract.py:92 happens *inside* `fingerprint()`, *after* `modules()` may have inserted worktree paths — no, `_load_file` uses `spec_from_file_location` and does NOT add the worktree to `sys.path` (contract.py:33-48), so `import sentence_law` always resolves via the `pipeline/` dir that `config` put on sys.path. Deterministic. **Not a bug; documenting it because I had to trace it twice.** (P3: one comment line.)

**N8. `mine.py:145`'s `i = max(j - overlap, i + 1)` with `overlap=6` and a 1-sentence window.** If a window ends at `j` where `j - i == 1` (a single giant sentence, the C3 case), next `i = max(j-6, i+1) = i+1` — progress, but the *next* window re-derives from `i+1` and, if that sentence is also giant, we walk one sentence per window: O(n) windows of 1 sentence each, each screened, each possibly sent. For a 6-hour VOD of pathological 900-word sentences: ~thousands of windows. Bounded by `max_windows` only in `ab.py` (mine.py:284-285), NOT in the service path (service.py:222 → `mine.mine_video` with no `max_windows`). A 6 h VOD at 150 wpm ≈ 54,000 words ≈ 60+ windows normally — fine — but the degenerate case has no ceiling in the production path. P2: add the service-side `max_windows` (the constant already exists; the plumbing is one argument).

**N9. `queue.claim`'s `from_states` accepts a tuple; `mine_once` passes `Q.MINE_DUE` (a 3-tuple) — service.py:296 — while `fetch_once` passes `(v["state"],)` (service.py:196).** Both correct. But `claim`'s SQL builds `IN (?,?,?)` — with `MINE_DUE`'s *order* mattering not at all. Fine. Listed because I promised myself I'd check every `claim` call: there are exactly two, both correct.

**N10. `stats.live`'s `usd_all_time_by_vendor` scans the whole `calls` table on every health tick (stats.py:82-83, every 60 s).** With the `calls_backend` index (queue.py:55) it's an index-ordered aggregate — but the index is `(backend, cost_usd)`, so the SUM still reads every row. At 3 videos×~10 windows×3 attempts×24 h×86k s/60 s... ~4320 calls/day → 1.5M rows/year → a 60 s-cadence full-index scan. Cheap today, quadratic-ish growth, no ceiling. P3: add a `day` column or a kv-cached accumulator.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| watch | 8.5 | 8.5 | Muse's Short-URL and ISO-compare findings are real but P3; nothing new. |
| fetch | 8.5 | 8.0 | Muse's future-`pub_ts` + my N3 (mined-but-coverage-invisible) — small, but two independent reviewers now agree the edge is unhandled. |
| mine | 8.0 | 8.0 | Muse's scores-are-first (P2, quality) + my N8 (no production `max_windows` ceiling) offset the genuinely good flag-union fix. |
| ledger | 8.0 | 8.5 | The `stamp=` fix converts my cycle-1 "sound by argument" into "exact by construction", with tests. The in-place mutation of `lines` (N-§2) is the only residue and it's benign. |
| providers | 8.5 | 8.5 | Freeze semantics, redirect-refusal, redaction, abandon() — all landed. N1 (cold-start thrash) and N4 (short-key redaction) are the residue; neither blocks. |
| queue | 8.5 | 8.5 | Stable. |
| service | 8.0 | 8.5 | B2's "nothing is dropped" is now *true* (outage waits indefinitely, partial retries to 72 h, both disclosed and tested). N2's moments-count semantics is the residue. |
| coverage/stats | 8.0 | 8.0 | Muse P1 (unmeasured→retry) landed; N3/N2/N10 are disclosure-level. |
| ab | 7.5 | 7.0 | The frozen judge means the A/B has no quality dimension (§2) — a process gap the code can't fix but the design promised. |
| tests | 8.0 | 8.5 | 161 tests, and the c1 fixes each carry a named regression test. The bounded-read exactness tests are exactly right. |
| **Overall** | **8.1** | **8.3** | Every cycle-1 blocking finding (B1–B4) is fixed and tested; what remains is P2 disclosure-level. |

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none. (B1–B4 are fixed; I verified each against the diff and the test inventory.)

**P1 HIGH**
1. **A/B without a judge** (ab.py:287-291, providers.json:63): the judge role's entire chain is spend-frozen; `judge` is None; the migration decision for the local model rests on overlap + hard-flag agreement only. *Condition, not code:* either lift one judge vendor for the A/B, or record in STATE that the next A/B's quality dimension is unmeasured. (This is the integrator's call; the code correctly discloses it — "no judge: every judge back-end is a generator, disabled, or under the spend freeze".)

**P2 MEDIUM**
2. **No production ceiling on windows** (service.py:222, mine.py:283-285): plumb `max_windows` into the service path or accept the degenerate-1-sentence-window cost (N8). One argument.
3. **Local-model cold-start thrash** (service.py:292-294, providers.py:469-471): release-on-idle at 5 s cadence vs. synchronous untimed `LocalLLM.start()` inside `complete`, invisible to health. Release after POLL_S of idle, or record the load.
4. **`moments` row-count ≠ ledger count for MINED_PARTIAL** (service.py:267, stats.py:35): disclose in the stats docstring that the number is a lower bound on the ledger.
5. **Future-dated publish** (fetch.py:173, coverage.py:67): a mined video can be invisible to coverage for the skew's duration. Clamp or note.
6. **Muse's scores-are-first** (mine.py:307-314): consider `max(rank_score)`; at minimum keep the disclosure.

**P3** — N4 (redact threshold), N5 (tmp naming), N6 (budget granularity), N7 (fingerprint provenance comment), N10 (all-time spend scan), muse's Short-URL probe waste and ISO-fragility, the ledger torn-tail comment.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Stamp `mined.at` under the append lock — already done — so the remaining leverage is: **give the next A/B a judge** (lift one frozen judge vendor for that run, or accept in writing that the local-model migration decision will be made on overlap alone), because every other open item is disclosure, and the A/B is the only mechanism the design trusts to move roles.

---

## 7. PRODUCTION READY?

**Yes, with conditions.**

1. **Ship the freeze as-is** — the orchestrator's 05:30 order is implemented exactly: frozen vendors never called (providers.py:687-690, 710-711, 794-795), Heimdall+local only in the mine chain (providers.json:61), outage → queue → retry forever (service.py:34-40, 280-284), spend meter notifies and reorders but never halts (providers.py:695-701, spend.py:150-171). B1–B4 verified fixed with named tests.
2. **Condition (process, not code):** before the *next* A/B run, either lift one judge vendor or record in STATE that the run's quality dimension is unmeasured — the overlap/hard-flag agreement alone must not be the sole basis for migrating the mine role.
3. **Condition (code, one line, before the 6 h-VODs arrive):** plumb `max_windows` into the service's `mine_video` call, or accept and document the unbounded-window cost.
4. **Condition (disclosure):** add to the stats/coverage docstrings the three lower-bound facts — `moments` counts the latest pass, not the ledger; a future-dated publish is invisible to coverage until the clock catches up; `usd_all_time_by_vendor` scans the full calls table.

Everything else in my list is P2/P3, priced, and none of it loses data: the ledger is append-only with validated lines and a torn-tail discipline; the queue's state machine recovers; the reader's exclusions fail closed; the latest line wins. The "nothing is dropped" promise, which the integrator called false in cycle 1, is now true and tested.