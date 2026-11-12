# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 502.4 s, $0.023, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest

**Auditor:** heimdall_muse (Cycle 2 — final review)

---

### 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting:**

| Their finding | I missed it? | Why |
|---|---|---|
| **GLM C1: `router.release()` race vs `complete()`** — `OllamaLocalBackend.release()` can `stop()` the model while `complete()` is in `llm._post()` | **Yes, missed.** I noted `service.py:85-99` flock fix but did not trace the `release()` vs `complete()` interleaving. GLM's analysis is correct that the window exists, though mitigated by `free==3` guard and `_busy` counter added in this diff. |
| **GLM C2: `_settle` partial-branch `len(failed) < windows_failed` can silently drop new moments** | **Yes, missed.** I flagged `mine.py:304-315` score-discarding but not the `service.py:256-258` append-gate logic. This is a real correctness bug — if retry produces different moments with same failure count, they are never appended but `moments` count is overwritten. |
| **Qwen: `offset_before` bisection on unsorted file** | **Partially missed.** I noted `ledger.py:110-135` interleaving risk and called it "acceptable" with 1-day margin. Qwen correctly identified the file was not sorted by `mined.at` (pass START vs append END). The diff fixes this by stamping under lock — I should have flagged the pre-fix state as P0, not "acceptable." |
| **Qwen: `stats.py` N+1 / loading all waiting rows** | **Missed.** I did not review `stats.py` query patterns. The consensus correctly identifies `SELECT reason FROM videos WHERE state=MINE_WAIT` loading all rows to count outages — should be `COUNT(*)`. |
| **GLM: `Health.allow` half-open probe stuck forever if validator crashes non-`Invalid`** | **Missed.** I noted `providers.py` health logic was sound. GLM correctly traces that `validate()` raising `RecursionError` etc. exits `_try` without `record()`, leaving `probing=True` forever. The diff partially fixes this (catches `Exception` broadly, adds `abandon()`), but the `BaseException` path still needs `abandon()`. |
| **Integrator B1-B4 blockers** | **Partially missed.** I caught B4 (age-gate vs rate-limit overlap) as "CORRECT FIX" but did not independently identify B1 (tripwire halts Heimdall permanently), B2 (80-min outage → silent loss), B3 (GPU0 lease as env string) as blocking. I treated the spend meter as "NOTIFY only" without verifying `Router.available` actually enforced that. |

---

### 2. WHERE DO I AGREE OR DISAGREE?

#### GLM findings:

| # | Finding | Verdict | Reason |
|---|---|---|---|
| C1 | `release()` race | **Agree** — real, low-probability. Diff mitigates with `_busy` counter (`providers.py:490-491`: `if self._busy: return`) but race window still exists between `complete()` grabbing `llm` ref and `release()` checking `_busy`. Fix is correct in practice because `mine_once` only releases when `free==3` (no inflight). |
| C2 | `_settle` partial-branch drops moments | **Agree** — genuine bug. Condition `len(failed) < windows_failed` conflates "fewer failures" with "new moments." A retry that mines different moments with same failure count loses them. Should compare moment sets or always append when `lines` differs. |
| C6 | Outage count loads every row | **Agree** — `stats.py:85` and `service.py:335` both do `SELECT ... WHERE state=MINE_WAIT` then count in Python. Fix: `SELECT COUNT(*)`. Done in diff for `stats.py:85-86`. |
| C10 | Ledger bisection | **Agree with consensus disposition** — premise valid, loss refuted by 1-day margin proof, but fix (stamp under lock) makes it exact. Correct. |
| C41 | Judge role entirely frozen | **Agree** — `providers.json:61` mine chain is now `["heimdall_qwen27b", "local_gemma"]` only; judge chain `["xai_frontier", "gemini_frontier", "anthropic_frontier"]` is all frozen vendors. No judge available. Disclosed, not a code bug. |

#### Qwen findings:

| # | Finding | Verdict | Reason |
|---|---|---|---|
| P0 | `offset_before` broken | **Partially agree** — premise correct (file not sorted), "silent data loss" overstated (1-day margin covers it per proof), fix (stamp under lock) is correct. Qwen's severity was too high; GLM/muse assessment was more precise. |
| P0 | Stats N+1 | **Agree** | |
| Ledger race (append vs set_state crash) | **Disagree on severity** — Qwen calls it critical; it's actually handled: `q.recover()` re-queues `MINING→TRANSCRIBED`, re-mines, re-appends, reader deduplicates by `moment_id`. Design handles this explicitly. Not a bug. |

#### Integrator B1-B4:

| # | Finding | Verdict |
|---|---|---|
| B1 | Tripwire halts Heimdall | **Agree — was blocking, now fixed.** Diff changes `Router.available` to NOT check meter state; instead `Router.order()` moves metered backends last. `spend.py:150-171` correctly implements NOTIFY-only. Verified. |
| B2 | 80-min outage → silent loss | **Agree — was blocking, now fixed.** Diff replaces `MINE_MAX_TRIES=8` with `MINE_RETRY_S`/`MINE_CONTENT_PASSES`/`MINE_HORIZON_S` model. Outage retries forever without consuming tries; rejected retries 3 times then goes `MINED_PARTIAL` (never counted as mined). `coverage.py:78` and `stats.py:29` correctly exclude partial. |
| B3 | GPU0 lease as env string | **Agree — was blocking, now fixed.** Diff replaces `PP_INGEST_GPU0_LEASE_HELD` env check with `gpu0.held()` + `gpu0.require()`/`swap_to` per request + `_busy` guard + `release()` on idle. Verified against `main 4867a74a` contract. |
| B4 | Age-gate trips breaker | **Agree — was blocking, now fixed.** `watch.py:24-27` splits `AGE_GATE_MARKS` from `RATE_LIMIT_MARKS`, checks age-gate first, adds `calm()`. `fetch.py:103-104` checks age-gate before unavailable. Verified. |

---

### 3. NEW FINDINGS FROM THIS REVIEW

**N1 — `service.py:283` `mine_once` reads `q.due()` outside `ilock` (low severity):**
```python
if free == 3 and not self.q.due(Q.MINE_DUE, 1): self.router.release()
```
`free` is computed under `ilock` but `q.due()` is outside it. Between the two, another thread could `claim()` a video. Result: `release()` called when work exists, briefly unloads local model unnecessarily. Next `mine_once` 5s later reloads it. Wasteful, not incorrect. **P2.**

**N2 — `providers.py:747` cache check uses `enabled()` which now checks `gpu0.held()`:**
```python
if use_cache and self.backends[bid].enabled():
    out = self._cached(...)
```
For `local_gemma`, `enabled()` returns `False` when GPU0 lease not held, so cached replies from local model are never reused outside the lease. This is intentional per docstring ("a stored validated reply costs nothing and may still be reused" — but code contradicts for local backend). If local model mined windows and produced cached replies, those caches are invisible when lease is not held. **P2** — either intentional (local cache only valid under lease) or should use a separate `cache_enabled` check.

**N3 — `ledger.py:44-45` torn-tail handling still has a subtle issue:**
The fix prepends `b"\n"` to new data when file doesn't end with `\n`. But `os.pread` + `os.write` are not atomic — another process could append between the `pread` check and `write`. Mitigated by `flock(LOCK_EX)` — actually safe since both paths hold the lock. **Not a bug** — retracting my Cycle 1 note about misleading comment; the comment is now accurate.

**N4 — `service.py:268` `moments` overwrite on outage retry:**
```python
moments = len(lines) if lines else int(v.get("moments") or 0)
```
When a partial video is retried and hits an outage (all windows fail, `lines=[]`), it keeps the old `moments` count. Correct. But when it partially succeeds (some windows mined, `lines=[new moments]`), it sets `moments=len(lines)` — only the *new* pass's moments, not cumulative. However `ledger.append` appends new lines and reader deduplicates by `moment_id` keeping latest, so the ledger has all moments but `videos.moments` column only reflects the last pass. `stats.py:35` sums `moments` column, undercounting partial videos. **P1** — `moments` should be cumulative or recomputed from ledger.

**N5 — `ab.py:265` `gen_models` set vs `judge` selection:**
```python
gen_models = {router.backends[b].model for b in gens}
judge = next((j for j in ... if router.backends[j].model not in gen_models ...))
```
Compares by `model` string, not backend ID. If two backends share the same model string (e.g., `heimdall_qwen27b` and a hypothetical second Qwen backend), the judge exclusion is over-broad. Minor. **P2.**

---

### 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| **watch.py** | 7/10 | 8/10 | B4 fixed (age-gate/breaker), `calm()` added. Remaining: `/shorts/` URL-only Short detection still wasteful (minor). |
| **fetch.py** | 7/10 | 8/10 | B4 fixed, breaker respect added (`gate.open_for()` check before captions). Remaining: future-dated `pub_ts` edge (trivial). |
| **mine.py** | 6/10 | 7/10 | Flag union fixed (fail-closed), `_untrusted` escaping added. Remaining: score/reason still first-observation-wins (quality, not correctness). |
| **ledger.py** | 6/10 | 9/10 | Stamp-under-lock makes order exact, `line_problems` validation added, `VIDEO_ID` check added, torn-tail handled under lock. Remaining: N4 moments count (P1). |
| **providers.py** | 5/10 | 8/10 | B1/B3 fixed (NOTIFY-only meter, real GPU0 lease, `frozen()`/`order()`/`effective()`), redirect guard, key redaction, `abandon()` added. Remaining: N1/N2 minor. |
| **queue.py** | 7/10 | 8/10 | `MINE_DUE` includes `MINED_PARTIAL`, indexes added. Clean. |
| **service.py** | 5/10 | 7/10 | B1/B2/B3 fixed (outage vs rejected distinction, single-instance guard, `close()`/`release()`), `BaseException` handling. Remaining: C2 partial-append gate (P1), N4 moments count. |
| **coverage.py** | 6/10 | 8/10 | B2 fixed (partial not counted as mined), approximate-date disclosure added. Clean. |
| **stats.py** | 5/10 | 7/10 | B2 fixed (partial excluded from mined count), vendor breakdown added, `COUNT(*)` for outage. Remaining: N4 undercount. |
| **spend.py** | 5/10 | 8/10 | B1 fixed (NOTIFY-only, `_rewrite_top` with flock, outage notice). Clean. |
| **ab.py** | 6/10 | 8/10 | B3 fixed (real lease), freeze respect, SECURITY notices, `release()` at end. Clean. |
| **Overall** | **5.5/10** | **7.8/10** | All 4 blockers resolved. Remaining issues are P1/P2, not blocking. |

---

### 5. FINAL PRIORITY LIST

| Priority | File:Line | Issue | Fix |
|---|---|---|---|
| **P1 HIGH** | `service.py:264-268` | **Partial retry `moments` undercount.** `moments = len(lines)` on partial retry only counts new pass, not cumulative. `stats.py:35` sums this column → undercount. Also GLM C2: `if lines:` gate means a retry that produces different moments with same `len(failed)` is handled, but `_settle`'s `was_partial` branch always appends — actually re-reading the diff, `service.py:265-266` does `if lines: ledger.append(...)` unconditionally for partial. So C2 is **fixed** in this diff. Only N4 remains. | Set `moments = int(v.get("moments") or 0) + len(new_moment_ids)` or recompute from ledger. |
| **P1 HIGH** | `providers.py:747` | **Local cache invisible without lease.** `enabled()` gates cache re-read; local model's validated replies can't be reused outside lease despite docstring promise. | Cache check should not gate on `gpu0.held()` — use `cfg.get("enabled")` only for cache path. |
| **P2 MEDIUM** | `watch.py:216` | **Short detection URL-only.** Playlist Shorts without `/shorts/` in URL misclassified as `DISCOVERED`, waste one probe cycle. | Add `duration < 60 and live_status is None` heuristic or rely on `fetch.py:157` as sole Short gate and remove watcher Short classification. |
| **P2 MEDIUM** | `service.py:283` | **`mine_once` TOCTOU on `q.due()` outside `ilock`.** Unnecessary `release()` when work appears between `free` check and `due()` check. | Move `q.due()` inside `ilock` or accept as harmless (5s reload cost). |
| **P2 MEDIUM** | `mine.py:304-315` | **Score/reason first-wins on overlapping windows.** Better-scoring observation silently discarded. Quality issue. | Use `max(rank_score)` to pick better observation, or merge scores with `max()`. |
| **P2 MEDIUM** | `ab.py:265` | **Judge exclusion by model string, not backend ID.** Over-broad if two backends share a model. | Compare by `bid` instead of `model`. |

**No P0 remaining.** All 4 blocking findings (B1-B4) are resolved in this diff.

---

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The `OUTAGE` vs `REJECTED` distinction in `service.py:_settle()` — because it is the difference between "videos wait and are mined later" (correct, nothing dropped) and "videos silently become partial with missing windows counted as mined" (data loss hidden by coverage).**

---

### 7. PRODUCTION READY?

**Yes, with conditions.**

**Conditions (all P1, non-blocking but should be fixed within one sprint):**

1. Fix `service.py:268` partial `moments` count — cumulative, not last-pass-only.
2. Fix `providers.py:747` local cache visibility — don't gate cached re-read on `gpu0.held()`.
3. Verify `ledger.py:stamp` path under concurrent `mine_video` — the `config.iso` callable is evaluated under `flock`, but `mine.py:build_line` also sets `mined.at` to `config.iso(now_dt)` at build time; confirm the stamp overwrites it (it does — `l["mined"]["at"] = at` — verified).

**Operational requirements (not code):**

- `pipeline/gpu0.py` must exist on the deploy host or `local_gemma` is never available (1 callable backend → WARNING logged, videos queue until Heimdall returns — by design).
- `PP_INGEST_STORE` must not be inside `MAIN_TREE` without `PP_INGEST_ALLOW_MAIN_STORE=1` (enforced by `StoreGuard`).
- Spend freeze lift requires editing `providers.json` `spend_freeze.vendors` and restarting the service.
