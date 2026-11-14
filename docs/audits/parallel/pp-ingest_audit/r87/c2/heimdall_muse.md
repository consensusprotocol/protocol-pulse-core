# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 309.3 s, $0.028, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (diff ca17cb97, ruling 87)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM caught 6 real defects in the new diff that I missed or under-rated:**

- **C1-1 (duplicate switch head on restart):** I noted the ledger race but missed the `write_switch_head` non-idempotency. Qwen flagged it as P0; GLM as D1. The fix (idempotent `head in cur` check in `spend.py:211-213`) is correct. I missed it because I focused on the ledger path, not the STATE notice path.
- **C1-2 (error/time torn store):** `downsignal.py:291-292` stored `error` before `error_since` in two steps; `check_notice` could read `error` with `error_since=None` → `now - None` TypeError. I missed this entirely. Fix (store time first, snapshot read) is correct.
- **C1-3 (double probe in one slot):** `tick()` called `probe_due()` before `_report_probe()`, so a probe that finished after the tick started was not yet stamped `last_probe_utc` → second probe in same 120s slot, doubled streak. I noted the `probe_out` race as "5s delay, not a bug" — wrong, it was a correctness bug at ~1/6 slots. Fix (report first, guard `probe_out is not None`) is correct.
- **C1-4 (non-numeric kv):** `int(seen)` on corrupt `signal_switches_seen` raised every tick. I missed it. Fix (catch `ValueError`, re-record) is correct.
- **C1-5 (`_rewrite_top` swallowing OSError):** `except OSError: text=""` treated an unreadable STATE file as empty → rewrite would truncate the file. I missed this. Fix (only `FileNotFoundError` → empty, else raise) is correct and the callers now handle `OSError`.
- **C1-6 (signal notice label):** `lambda h: h.startswith(prefix)` with old label left stale line. I missed it. Fix (`SIGNAL_RE` any label) is correct.

**Qwen's framing of C1-1 as "critical" was overstated** — Claude's consensus correctly downgraded to P2 (informational line, never a decision). But the defect was real.

**What I caught that they missed:** The `mine.py:481` `rank_score` missing `risk` penalty during overlap dedup, and the `watch.py:216` Shorts fragility — neither GLM nor Qwen flagged these (they were outside the diff, but still live defects).

## 2. WHERE I AGREE / DISAGREE

| Finding | Verdict | Why |
|---------|---------|-----|
| **GLM D1 (stale answer resets 15-min clock)** | **Disagree — refuted** | Claude's refutation is correct: `noted()` at `downsignal.py:133` does `pending["answer"], pending["fail"] = t, None` — a later answer *replaces* both. The trace GLM gave contradicts the code. No defect. |
| **Qwen: `_seen` not atomic** | **Agree defect, disagree severity** | Real, but Claude's fix (idempotent `write_switch_head`) makes it at-least-once, not exactly-once. Correct tradeoff — losing a switch would be worse than duplicating a head. |
| **Qwen: `_flush` ordering** | **Agree no defect** | Qwen's own walkthrough shows the compression is correct. No issue. |
| **GLM: probe `AllBackendsFailed` handling** | **Agree correct** | `called` check at `downsignal.py:214` correctly distinguishes "no probe" from "probe failed." |
| **GLM: `write_switch_head` idempotency** | **Agree — fixed** | Was real, now fixed. |
| **GLM: `_fail` torn store** | **Agree — fixed** | Was real, now fixed. |
| **GLM: double probe** | **Agree — fixed** | Was real, now fixed. My Cycle 1 dismissal was wrong. |

## 3. NEW FINDINGS FROM COMBINED ANALYSIS

**N1 — The 7 reviewer questions (answering with file:line):**

1. **Ordering (stale answer clearing failure):** Not a defect. `downsignal.py:133` — later answer atomically clears `fail`. The module's `HEARTBEAT_S=30` dedup is per-process and only suppresses *writes* while healthy; it does not suppress the failure clock. The 15-min rule self-heals on next answer >30s after last written one. Bounded to one compressed answer, not a stuck state.

2. **Two processes probing:** Both can see `probe_due() == True` and both call `probe_result()`. This is **the module's responsibility** — `probe_due()` does not claim the slot (no CAS). The module's `probe_streak` is global; two concurrent probes that both answer increment it by 2 in one round, reaching `BACK_AFTER=3` in 2 rounds instead of 3. Acceptable: the contract says "3 probe answers in a row" — two processes answering concurrently *is* two answers. The alternative (distributed lock on probe) would add complexity for a 30s acceleration of recovery. Not a defect in this watcher.

3. **http_4xx as "not answered":** Correct per A23 and the contract ("down, refused, empty or late"). A 400 is the gateway refusing *this* request, not answering it. It should count as failure — if the watcher sends bad requests, the signal should reflect that the gateway is not serving it. The builder's `note(False)` is the right call. If 4xx were excluded, a misconfigured watcher would never trip the signal even though it gets no service.

4. **Signal changing miner / blocking / raising:** No path. `noted()` at `downsignal.py:122-137` is O(1), never touches shared file, catches all exceptions. `tick()` runs in its own thread. `check_notice()` at `service.py:554` catches `OSError`. `providers.py:794-796` — breaker-free role re-raises `BaseException` without touching health (correct: no probe slot to abandon). Miner chain unchanged.

5. **`_seen()` kv across restarts / replaced state file:** Correct. `downsignal.py:258` — `seen > len(sw)` (state file replaced/shrunk) re-records count without announcing history. `seen is None` (first sight or corrupt) same. STATE write failure returns before `kv_set` at `downsignal.py:276` → retried next tick. At-least-once with idempotent head.

6. **Thread safety of DownSignal:** Correct. `pending`/`probe_out` under `self.lock`. Module calls only in signal thread. Health thread reads `error`/`error_since`/`busy_since` — now snapshot atomically at `downsignal.py:315`. `check_notice` writes STATE under `state_doc.lock`, same lock as other notice writers.

7. **Probe starvation:** No. Probe back-ends have `max_inflight=1` each, own throttle, `breaker=false`. Miner uses `heimdall_qwen27b`/`local_gemma`; probe uses `heimdall_qwen27b_probe`/`heimdall_glm53flash_probe` — different back-end IDs, different semaphores. Global cap is 20, probe needs 1. Miner cannot starve probe (different semaphores) and probe cannot starve miner (1 slot of 20, 60s timeout, `transport_retries=0`).

**N2 — Remaining defect not fixed in C1:**

- **`downsignal.py:193` — drill note uses `self.clock()` not the drill's time.** Drills are counted (`pending["drills"] += 1`) without timestamps. `_flush` notes `drill=True` with `now=_utc(self.clock())` (flush time, not event time). This is intentional — drills are never counted toward the 15-min rule, only recorded. Not a defect, but the evidence timestamp is ~5s late. Acceptable.

**N3 — `spend.py:56` switch line ordering invariant:**

`_rewrite_top` now forces `SWITCH_RE` lines first via `block = [switch] + [non-switch]`. This is correct per A22 but means a concurrent `write_switch_head` and `write_signal_notice` could interleave: both read the same `head`, both prepend, one overwrites the other. Mitigated by `fcntl.flock` on `state_doc.lock` — both go through the same lock file. Correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Watch** | 7/10 | 7/10 | No change — Shorts fragility remains, outside diff |
| **Fetch** | 8/10 | 8/10 | No change |
| **Mine** | 7/10 | 7/10 | `rank_score` risk bug still present (outside diff, not fixed) |
| **Ledger** | 8/10 | 8/10 | No change |
| **Providers/Router** | 8/10 | 9/10 | Breaker-free + transport_retries correctly implemented and validated |
| **DownSignal (new)** | 6/10 | 9/10 | 6 real defects fixed (C1-1 through C1-6); remaining design is sound |
| **Spend/Notices** | 7/10 | 9/10 | `_rewrite_top` OSError fix + idempotent switch head + label-agnostic signal notice |
| **Service/Health** | 8/10 | 9/10 | Signal loop correctly isolated; purge/outage notice OSError handling added |
| **Overall** | **7/10** | **8.5/10** | Diff is production-ready; remaining deductions are pre-existing outside diff |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — none in this diff.** All 6 C1 defects are fixed and verified.

**P1 HIGH — fix before next cycle (pre-existing, outside diff):**

- `mine.py:481` — `rank_score({"scores": cand["scores"]})` drops `risk` penalty during overlap dedup. Should be `rank_score(cand)` or `rank_score({"scores": cand["scores"], "risk": cand["risk"]})`. Wrong observation can win.
- `ledger.py: read()` vs `append()` — `best_unused_moments` and `check_once` read without `wlock`; torn last line is counted as `bad_lines` not returned (safe but noisy). Consider `ledger.read` taking shared lock or documenting the guarantee.

**P2 MEDIUM:**

- `watch.py:216` — `"/shorts/" in url` fragile; canonical signal is `media_type=="short"` at probe time. Low risk (URL format stable, probe is backstop).
- `fetch.py:212-214` — stale `meta.json` reuse without `channel_id` re-validation. Minor.
- `purge.py:203-220` — N+1 `q.video()` per file in purge scan. Acceptable at current volume.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The 6 fixes in C1 already shipped — the highest remaining leverage is fixing `mine.py:481` to include `risk` in overlap `rank_score`, because it silently picks the wrong observation for overlapping windows and the error is invisible in the ledger.

## 7. PRODUCTION READY?

**Yes, with conditions.**

The diff (ruling 87 downsignal) is **ready to ship** — all 6 defects found in Cycle 1 are fixed, the 7 reviewer questions are answered, and no new P0/P1 was found in the diff.

**Conditions:**
1. `mine.py:481` risk penalty fix in next commit (P1, one-line).
2. Monitor `down_signal` in `live.json` for first 48h — specifically `counts.probes_not_made` (should be 0 outside drills) and `not_read` (should be null).
3. Do not lift the spend freeze without orchestrator explicit — the miner's Plan B remains queue-and-wait regardless of signal mode.