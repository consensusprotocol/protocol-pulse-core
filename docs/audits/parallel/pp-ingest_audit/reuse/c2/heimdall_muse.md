# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 285.4 s, $0.029, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (diff 32fd1d99)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Heimdall_glm caught what I glossed over:** The full gate-by-gate walkthrough of `_reuse_calibration` with explicit attention to the `asked_at` set semantics and the `config.aware(None) -> None` path. I noted the future-timestamp check was correct but dismissed it as "worth noting" — glm correctly elevated it to a verified gate (Gate 4) and tied it to the injected `clock` vs `config.iso()` clock agreement. I also under-weighted the `effective()` filtering consequence: glm explicitly called out that a disabled *or frozen* backend correctly invalidates reuse via `set(cal) != set(eff)` — I mentioned it in passing but didn't frame it as the intentional fail-closed behavior it is.

**Heimdall_qwen caught nothing I missed on this diff** — its "critical race" analysis self-corrected mid-paragraph to "actually quite tight." Its initial `KeyError` alarm was wrong because `set(cal) != set(eff)` guards line 596. I had already verified this in Cycle 1 (item 2). Qwen's value was as a negative control: a second pair of eyes confirming no race.

**What all three of us missed in Cycle 1 that the C1 consensus surfaced:** The coupling of `check_calibrated = t.timestamp()` (the *live* calibration's start, not restart time) to the daily schedule. I noted it was "correct" but didn't flag it as the highest-risk semantic property — that the next due fires a day after the live calibration, not a day after restart. The fake-clock test (C1-1) that pins this was the most important test added in 592c2443, and I under-emphasized it.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| **glm: Every reuse gate fails closed to live calibration** | **Agree** | Verified independently. Six gates, each returns `False` → `_calibrate_checkers()` live. No path lets a stale/cached-era/crash/future record set `check_allowed`. |
| **glm: `not cal[b].get("unmeasured")` is redundant given `of==16==right` but harmless** | **Agree** | If `unmeasured>0` then `of<16` by construction (`calibrate` only increments `of` on answered). Redundancy is defensive, not a bug. |
| **glm: `model` check is configured model, not served model — inherent limitation** | **Agree** | Documented in providers.json:32. No code can detect a gateway silently swapping models behind same name. Out of scope. |
| **muse (me) Cycle 1: Shorts URL detection leaks Shorts into fetch queue** | **Agree with myself, but P2** | `watch.py:216` `/shorts/` check misses yt-dlp flat-playlist Shorts without that path. `fetch.py:157` `media_type=="short"` is the real gate, so no incorrect mining — just wasted probe. Not in this diff's scope. |
| **muse (me) Cycle 1: `_reuse_tried` never reset is correct** | **Agree** | One-shot at start is intentional. Fallback is live calibration via `check_allowed is None` branch. |
| **qwen: "Critical race condition" in `_reuse_calibration`** | **Disagree — no race** | Qwen self-retracted. `set(cal) != set(eff)` before `cal[b]` access prevents `KeyError`. Single-threaded `check_once` loop, no concurrent writer to `check_allowed`. |
| **C1 consensus: Outage calibration never reused** | **Agree** | Outage calibration has `allowed=[]` (nobody passed: `of<16` or `right<16` or `unmeasured>0`). Gate 5 `why = "no back-end passed it"` → `return False` → live. Correct. |
| **C1 consensus: Refusal logging (C1-2) is required** | **Agree** | Design 16 says so. The four refusal tests assert the reason string. Without this, silent fallback to live would be unobservable. |

## 3. NEW FINDINGS FROM THIS REVIEW (Cycle 2)

**N1 — `config.aware` vs `self.clock()` clock skew is bounded but worth naming (P2, not P0):**
`asked_at` is written via `config.iso()` → `datetime.now(timezone.utc)` (wall clock). `self.clock()` defaults to `time.time` (also wall clock) but is injectable in tests. In production they agree. If NTP steps the clock backward between calibration and restart, `clock() - t.timestamp()` goes negative → correctly rejected as future → live calibration. This is fail-closed and correct. No change needed, but the code comment `# (negative: the clock went back)` on line 599 is the right annotation — it was added in 592c2443 precisely for this.

**N2 — `kv_get("check_calibration")` stores JSON-stringified JSON (double encoding) — intentional but subtle (P2):**
`_calibrate_checkers` does `kv_set("check_calibration", json.dumps({...}))` where `kv_set` itself does `json.dumps(v)`. So the stored value is a JSON string containing JSON. `_reuse_calibration` does `json.loads(kv_get(...))` — `kv_get` does `json.loads` once, yielding the inner JSON string, then the outer `json.loads` parses it. Wait — actually `kv_get` returns `json.loads(r[0]["v"])` which is the `json.dumps({...})` string → a string, not a dict. Then `json.loads(that_string)` → dict. This is correct but fragile: if anyone writes `kv_set("check_calibration", {...})` directly (without pre-stringifying), the read path breaks. Current code is consistent (both writer and reader agree on double-encoding), and the `except ValueError` catches corruption. No bug, but a future maintainer could easily break it. A comment would help.

**N3 — `check_recal_s` reset to `CHECK_RECALIBRATE_S` on reuse is correct and intentionally discards outage backoff (P2, verified):**
If the previous calibration was an outage ( `check_recal_s == 600` doubling), and then a good calibration succeeded, `check_recal_s` was already reset to 86400 by `_calibrate_checkers`. Reuse then also sets it to 86400. If the previous calibration was an outage and we're reusing... we can't be, because outage calibrations have `allowed=[]` and are rejected. So the only reusable record already has `check_recal_s=86400` semantics. Correct.

**N4 — No new P0/P1 found.** The combined Cycle 1 analysis plus the C1-1/C1-2 test additions cover the risk surface of this diff.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `service._reuse_calibration` | 9/10 | 10/10 | C1-1 fake-clock test + C1-2 refusal logging close the two gaps I flagged as "worth noting." Every gate now has a mutation-checked test. |
| `flagcheck.watcher_probes` factoring | 10/10 | 10/10 | No change. Pure refactor, same 16 quotes. |
| `purge.kept_copies` (A19) | 9/10 | 9/10 | Already audited 2 cycles. No new defect. |
| `providers` / `ledger` / `watch` / `fetch` / `mine` | 9/10 | 9/10 | Unchanged by this diff. Prior P2s (Shorts URL, metrics surface) remain out-of-scope. |
| **Overall pp-ingest** | **Ready** | **Ready** | No P0. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — none.** No path lets an unmeasured backend answer, no schedule corruption, no F1 violation.

**P1 HIGH — none in this diff.** 

**P2 MEDIUM — ship without fixing, fix when touching the area:**

- `service.py:584-585` — Add comment on double-JSON encoding of `check_calibration` kv value (`kv_set` does `json.dumps` on an already-`json.dumps`'d string). Not a bug, but a maintenance trap. One-line comment.
- `watch.py:216` — Shorts detection via `"/shorts/" in url` misses flat-playlist Shorts without that path. Low cost (one wasted probe, caught by `fetch.py:157`). Fix when watch.py is next touched.
- `providers.py:851` — Cache reuse for frozen vendors is intentional per spec, but the `enabled` vs `frozen` distinction in the cache gate deserves a comment referencing the SPEND FREEZE spec. Already has one.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Already shipped:** Pinning `check_calibrated = t.timestamp()` (live calibration's start, not restart time) with the fake-clock test — because a wrong anchor silently shifts the daily schedule by up to 24h and the bug would only manifest as a missed or doubled calibration a day later, invisible at restart.

## 7. PRODUCTION READY?

**Yes.** 

Conditions: None beyond the existing ones (store guard, provider config validation, single service per store). This diff is safe to ship as-is. The 32 live calls saved per restart eliminate the false-outage trigger (09:16 incident) without weakening F1's live-measurement guarantee — every reused record was itself asked live within the day, with at least one backend passing all 16 quotes.

*Answers to the three reviewer questions:*
1. **No.** Cached-era (no `asked_at` → `t is None`), another model (`model != current`), crash record (`cal is None/{} → "none stored"` or `allowed=[] → "no back-end passed it"`), future `asked_at` (negative delta → `asked N h ago`), two `asked_at` values (`len(asked)==2 → t is None`) — all rejected to live.
2. **No.** Reuse sets `check_recal_s=86400` and `check_calibrated=t.timestamp()` (live start), so next due is a day after live. Outage retry (`CHECK_RETRY_S` doubling) is untouched — outage calibrations have `allowed=[]` and are never reused.
3. **Yes.** F1 kept: reused record must have `of==right==16` and `unmeasured==0` for at least one backend, which only a live calibration with `fresh=True, rounds=3` can produce. An outage calibration (unanswered quotes → `unmeasured>0` or `of<16`) is rejected at Gate 5.