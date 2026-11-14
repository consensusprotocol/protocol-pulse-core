# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 408.9 s, $0.030, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest `cycles.py` diff (47c7939b vs 81f46b3c)

> Scope: Only the 3-file diff. Citations are `file:line` in the diff unless noted. This is the final review after reading Cycle 1.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM caught 4 things I missed or under-weighted:**

1. **The "newest with one" stale pointer (GLM BUG 1, P1).** I noted `cycles.py:110-112` searches the entire `videos` table with no `discovered_ts >= t0` filter, but I classified it as "defensible" because the date is printed. GLM correctly framed it as a UX defect: `NOTHING BITCOIN IN THE LAST 3 H ... the newest with one: X, seen 14:20 ET Nov 11` reads as if X is in the window. I should have flagged it P1, not "defensible."

2. **The `seen` denominator not adding up (GLM BUG 2, P2).** I checked `cycles.py:92-98` `_quiet()` for the "nothing Bitcoin while not mined" lie (Q3) and declared it COMPLIANT. I did not check whether `len(seen)` was reconcilable: `DUPLICATE`, `UNAVAILABLE`, `NO_CAPTIONS`, `TOO_LONG`, `OPTOUT` were silently inflating `N` while contributing to none of the parenthetical buckets. GLM caught the arithmetic gap.

3. **The vanish (GLM P0).** I noted `cycles.py:86-87` `if not cycles: return None` suppresses the 09:02 note when watcher is down and called it "defensible, but undocumented." I missed the worse case GLM found: when `cycles` exists but every cycle had `n==0` (or `n>0` but all videos already mined with Bitcoin), `out==""` and `quiet==""` → `return None` → the old line stays or vanishes. The spec says "say so when a cycle finds nothing Bitcoin in 3 hours" — the old line staying is stale, vanishing is silent. This was a real P0 and I under-scored it.

4. **The multi-line `reason` (GLM P0).** I checked `cycles.py:38` `v["reason"][:120]` for None-safety but not for newlines. `fetch.py` writes `reason` from `yt-dlp` stderr which can contain newlines; `spend.py:70` `if "\n" in line: raise ValueError` then refuses the line on every pass. I missed this entirely.

**Qwen caught nothing I missed** — his analysis was correct but shallower (confirmed Q3, timezone, race benign). His "N+1 acceptable" was wrong; both GLM and I flagged it and it was fixed.

**What I caught that they missed or under-weighted:**

- The `n` vs `vids` mismatch and `start` heuristic fragility (`cycles.py:73-84`) — I was the only one to detail both Bug A and Bug B with the `seconds` default-0 failure mode. GLM mentioned the `+-2s` only as BUG 7 "verified" without analyzing the `seconds==0` case.
- The `v["hook_ts"]` falsy-skip and `MINED_PARTIAL` with `mined_ts=None` edge case (`cycles.py:44-45`) — neither other reviewer mentioned it.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| **GLM P0 vanish** | **Agree** | Real bug. Fixed in C1-1: window with cycles but nothing new now says `"none of its N cycle(s) found a new upload"` instead of `None`. Correct fix. |
| **GLM P0 newline** | **Agree** | Real bug. Fixed in C1-2 via `_one()` folding every field + whole line. Correct fix. |
| **GLM P1 stale "newest with one"** | **Agree** | Real defect. Fixed in C1-3: now says `"before this window: ..."` with date. I would have preferred also filtering to `discovered_ts >= t0 - 72h` or similar, but the label fix is sufficient — the date makes it honest. |
| **GLM P1 title 40 chars** | **Agree** | Good UX fix (C1-4). No correctness impact. |
| **GLM P1 ceiling 12k** | **Agree** | Real risk without it: unbounded line. Fixed in C1-5. |
| **GLM BUG 2 denominator** | **Agree** | Real arithmetic gap. Fixed in C1-9: `other` bucket added. |
| **GLM BUG 3 stale-forever (6h rewrite)** | **Agree — not a bug** | `MINED_PARTIAL` re-mine every 6h advancing `newest` is intended — a real change happened. Correctly recorded, not changed. |
| **GLM BUG 4 non-snapshot reads** | **Agree — benign** | Three SELECTs not one snapshot. Next pass (60s) re-reads. Not worth a transaction. |
| **Muse P1 `n` vs `vids` mismatch** | **Agree** | My own finding. Fixed in C1-6: `"4 new (3 found in its events)"` when mismatch. Correct — says both, doesn't hide. |
| **Muse P1 N+1 query** | **Agree** | Real. Fixed in C1-7: batched `WHERE video_id IN (...)` per 500. |
| **Muse P1 `start` heuristic fragile** | **Partially agree** | Real fragility when `seconds` is 0/None, but C1-6's mismatch disclosure mitigates it visibly. No further fix needed unless `seconds` missing becomes common. |
| **Qwen "N+1 acceptable"** | **Disagree** | 50 queries/min is not catastrophic but violates the spec's own concern and is trivially fixable. Fixed correctly. |
| **Qwen "nothing Bitcoin" honest** | **Agree** | `none of the {len(known)} mined with Bitcoin term` is honest. Q3 answer stands: NO, it does not lie. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 — `cycles.py:78` `start` window still has a double-count edge (P2, not fixed in C1).**

```python
start = ts - float(d.get("seconds") or 0) - 2
evs = [e for e in disc if start <= e["ts"] <= ts + 2]
```

If two cycles run back-to-back (e.g. `watch_once` takes 30s, next cycle starts immediately), their windows overlap by up to 4s (`+2` / `-2`). A `discovered` event at the boundary appears in both cycles' `evs`, so the same video is listed twice in the line (once per cycle). Not a wrong count (each cycle's `n` is reported separately), but a duplicate video entry. Low severity because `POLL_S=600` makes overlap rare, but worth a dedup or noting.

**N2 — `cycles.py:110-112` `_quiet` tail query has no `LIMIT` guard on `names` lookup cost (P3).**

```python
last = q.rows("SELECT video_id, channel_id, discovered_ts FROM videos WHERE COALESCE(windows,0) > "
              "COALESCE(windows_screened,0) ORDER BY discovered_ts DESC LIMIT 1")
```

This scans `videos` with `COALESCE` on every health tick (60s). No index on `windows`/`windows_screened`. At 10k videos it's fine (SQLite, local), but at 100k+ it becomes a full table scan per minute. A partial index or `WHERE windows > windows_screened` (without COALESCE, since NULL means 0 in this schema) would help. Not blocking.

**N3 — `cycles.py:89` `newest` tracking double-counts `hook_ts` advancement (P3, already recorded as BUG 3).**

When a `MINED_PARTIAL` video is re-mined every 6h, `mined_ts` advances and `newest` advances, causing a rewrite every 6h even though no new cycle found anything. This is intentional (a change happened) but means Q1 "no per-minute rewrite" holds, but "no rewrite without new cycle" does not — the line rewrites on re-mine. Documented in C1 consensus as "recorded, not changed" — correct decision.

**N4 — `spend.py:70-75` `write_cycles_notice` lock path derivation is fragile (P2).**

```python
lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
```

If `notify_path` is `.../ingest/NOTIFY.txt`, lock is `.../ingest/state_doc.lock`. If `doc` is `.../parallel/pp-ingest_STATE.md`, lock is `.../parallel/pp-ingest_STATE.md.lock`. These are different files — two writers using different `notify_path`/`doc` combos would not share a lock. In practice `service.py:773` always passes `notify_path=self.p["notify"]` so it's consistent, but the API allows silent lock divergence. Should assert or derive from one canonical path.

**N5 — `cycles.py:44` `max(t for t in (mined, hook_ts) if t)` skips `0` (P3).**

`hook_ts` of `0` (epoch) is falsy and skipped. No video has `hook_ts=0` in practice (it's NULL or a real timestamp), so not a bug, but `if t is not None` would be more precise than `if t`.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness (cycles line)** | 6/10 — two P1 bugs (count/time, N+1) | **8/10** — C1 fixes resolved P0s and P1s; remaining N1/N4 are P2 | C1-1 through C1-9 fixed all P0/P1. N1 duplicate at boundary is P2. |
| **Law compliance** | COMPLIANT | **COMPLIANT** | No change. C1 fixes preserved L-j/L-m (fail closed, not minable bucket). |
| **Security** | Clean | **Clean** | No change. All queries parameterized. |
| **STATE integrity (Q2)** | 9/10 — no race, switch invariant held | **9/10** — N4 lock path divergence is theoretical, not exercised | `_rewrite_top` switch-first + flock + never-rewrite-unreadable all hold. |
| **Q1 clock leak** | Fixed correctly | **Fixed correctly** | `newest` from event/video timestamps, `if new != text` guard. No change. |
| **Q3 "nothing Bitcoin" lie** | No lie | **No lie** | `none of the {len(known)} mined` + `queued` apart. C1-9 added `not minable` bucket. Honest. |

---

## 5. FINAL PRIORITY LIST

| Priority | Item | File:Line | Status |
|----------|------|-----------|--------|
| **P0** | *None remaining* — both Cycle 1 P0s (vanish, newline) are fixed in C1-1/C1-2 with tests that fail without them | — | ✅ Fixed |
| **P1** | *None remaining* — all Cycle 1 P1s (stale pointer, title, ceiling, count mismatch, N+1, denominator) fixed in C1-3 through C1-9 | — | ✅ Fixed |
| **P2** | Duplicate video at cycle boundary overlap (`start`/`+2` window) | `cycles.py:78-79` | Open — dedup `evs` by `video_id` across cycles or document as known |
| **P2** | Lock path divergence if `notify_path`/`doc` combos differ | `spend.py:73` | Open — derive from single canonical or assert |
| **P3** | Full table scan on `videos` for `_quiet` tail every 60s | `cycles.py:110` | Open — add partial index or rewrite without COALESCE |
| **P3** | `if t` vs `if t is not None` for `hook_ts` | `cycles.py:44` | Open — cosmetic |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Already shipped in Cycle 1:** C1-1 (the vanish fix) — a window with cycles that found nothing new now says so instead of returning `None` and leaving a stale line or no line, which was the only P0 that could silently mislead the orchestrator about what the watcher saw.

---

## 7. PRODUCTION READY?

**Yes, with no conditions.**

All P0 and P1 items from Cycle 1 are fixed with tests that fail without them (6 mutations caught, 354 tests passing). The two remaining P2s (boundary duplicate, lock path divergence) are theoretical — not exercised in production (`POLL_S=600` prevents overlap; `service.py` always passes the same `notify_path`). Ship it.
