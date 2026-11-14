# heimdall_minimax (minimax/minimax-m3.1-flash, 336.9 s, $0.010, finish stop)

# CYCLE 2 — FINAL REVIEW (pp-ingest, playlist-first)

*(I produced no cycle-1 output; the cycle-1 consensus is the baseline I am revising. Below: what the others caught that I would have missed, where I agree/disagree, and what the combined analysis newly exposes.)*

---

## 1. WHAT THE OTHERS CAUGHT THAT I MISSED

Since I did not answer in cycle 1, everything in the cycle-1 consensus is new to me. The items I would **not** have found on my own:

- **C1-1 (glm):** the gate raises `rate_limited` *immediately* while the breaker is open (it never blocks), so a playlist-first channel falls back to RSS and is never backed off while RSS answers. This is the single most important behavioural fact of the change and it is only visible by reading `YouTubeGate.run` (watch.py:65-66) together with the new loop (watch.py:204-211). I would have assumed the fallback path was blocked.
- **C1-2 (muse):** `publish_to_discovered_min_by_source` in live.json — the measurement that makes the 6-minute gain visible. I would have asked for it and not built it.
- **The error-text asymmetry** (muse P1, glm): RSS's `detail` is dropped, the playlist's is kept (watch.py:211). I would have noticed the *shape* but not that it is a faithful preservation of the old behaviour.
- **The `calm()`-on-any-success decay** (qwen): a concurrent success shortens a later pause. By design, but it interacts with the new listing volume (see N1).

---

## 2. WHERE I AGREE / DISAGREE

| Cycle-1 finding | My position |
|---|---|
| **No video lost, double-counted, or mis-recorded** (all three) | **Agree.** `add_video` is `INSERT OR IGNORE` on `video_id` (queue.py:148-153); `upd` is only populated inside `rss()` (watch.py:193-195), so a playlist success writes no ETag and cannot corrupt one; `newest_published` is a max over ISO strings (watch.py:229-231). The old order is intact behind `playlist_first=False`. |
| **muse P1: RSS detail dropped on the fallback path** | **Partially agree — record, do not change.** It is a faithful carry-over of the old code (old RSS branch: `err = f"{e.kind}"`; old playlist branch: kind + detail). Changing it now would make the error text incomparable with the pre-change history. |
| **muse P1: ETags survive a mode switch** | **Agree, no action.** A stale ETag yields 200 (full feed) or 304 (empty) — both safe, and the playlist already caught the new items. |
| **qwen: the cache is consulted before `available()`** | **Disagree (not a violation).** providers.py:851-856 is the documented spend-freeze policy: "a stored validated reply costs nothing and may still be reused" (providers.py:10-13). A frozen vendor's *stored* reply is explicitly allowed. |
| **qwen: `calm()` shortens a later pause** | **Agree it is by design**, but see N1: with playlist-first the *volume* of successes that can calm the breaker is ~64 per cycle, so the breaker decays faster than before. |
| **C1-1 (the fallback keeps a channel alive while the breaker is open)** | **Agree, with a refinement (see N1b):** the fallback protects the *listing*, but the breaker still blocks the *captions* for its whole 10-60 min window (fetch.py:220-224 defers while `gate.open_for() > 0`). The win is real; it is not a win for the caption path. |
| **C1-2 (the by-source metric measures the gain)** | **Agree that a metric is needed; disagree that this metric measures the gain** — see N2. It compares different populations, not the same video under both sources. |
| **Cycle-1 consensus: "ready for production"** | **Agree with conditions** (below). The change is sound; the *cost* is concentrated in the shared gate, and that is where the conditions are. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### N1 (P1) — The shared 3-slot gate now carries 64 playlist listings per cycle, and the fetch path queues behind them
`YTDLP_CONCURRENCY = 3` (config.py:27) is shared by listing, probe and captions (watch.py:38-74, fetch.py:92, fetch.py:225). Before this change, a cycle with RSS up made **zero** yt-dlp listing calls; now it makes **64** (one per channel), each up to `timeout=120` (watch.py:130-131).

- Measured: mean cycle 76 s, max 253 s (the diff's own evidence).
- **Tail:** the worst case is bounded but large — 64 channels ÷ 3 slots × 120 s ≈ **43 min**, longer than `POLL_S = 600`. `_loop` (service.py:863) computes `delay = every - elapsed`, so a 43-min cycle is followed immediately by the next one: the gate is then **permanently saturated by listings**, and the probe and the caption download never get a slot. The change optimises publish→mined while lengthening publish→probe, which is the first half of the same latency.
- **Fix (cheap, testable):** reserve a slot for the fetch path — e.g. give the listing 2 of the 3 slots (`gate.run` with a listing-only semaphore), or add a fourth slot used only by `fetch`. Second: bound the watch cycle (skip the remaining channels when the cycle is over a budget, e.g. 120 s) so a slow YouTube cannot monopolise the gate.

### N1b (P1, refinement of C1-1) — The fallback keeps the *listing* alive while the breaker is open, but the captions still stall
While the breaker is open, `gate.run` raises `rate_limited` at once (watch.py:65-66), so every channel's playlist attempt fails instantly and falls back to RSS — no backoff, no video lost (C1-1, correct). But `fetch._store_captions` explicitly refuses to download while `gate.open_for() > 0` (fetch.py:220-224) and `fetch.probe` gets the same `rate_limited` (fetch.py:142-143). So a single trip still costs the caption path 10-60 min. The change does not make the breaker *more* likely (see §Q3 below), but it does not protect the captions from it either. Worth stating in the design so nobody reads C1-1 as "the breaker is now harmless".

### N2 (P2) — `publish_to_discovered_min_by_source` cannot measure the gain it was built for
`by_source` (stats.py:155-163) buckets live mined videos by `discovered_via`. But `discovered_via` is **first-source-wins** (`INSERT OR IGNORE`, queue.py:148-153): a video listed by the playlist is never re-attributed to RSS. So the `rss` bucket contains only the videos the *playlist missed* — i.e. the channels where the playlist failed — while the `uploads_playlist` bucket contains everything else. The two buckets are different populations, not the same video under two sources. The A/B's 6-minute median was a **paired** measurement (the same 25 uploads listed by both sources); live.json cannot reproduce it, and the `rss` bucket will be near-empty in production (RSS is only used when the playlist fails), so the figure will read as "playlist p50 = X, n = 1" and prove nothing.
**Fix:** record *both* sources' first-seen times (a per-video `first_seen_playlist` / `first_seen_rss`, or a per-channel pair) so the comparison is paired; or, if that is too heavy, keep the metric but label it honestly as "the videos each source discovered" and not as the gain.

### N3 (P2) — The queue's write volume doubles with playlist-first, and each write is its own fsync
`add_video` is one `INSERT OR IGNORE` per entry (queue.py:142-158) on a connection with `PRAGMA synchronous=FULL` and `isolation_level=None` (queue.py:82-87) — i.e. **one fsync'd transaction per entry**, each taking the queue's global `RLock` that the fetch and mine threads also need. The playlist lists 30 entries per channel where RSS listed ~15: **~1,920 fsync'd transactions per cycle instead of ~960**. Pre-existing pattern, but this change doubles it, and the lock contention lands on the fetch loop's state updates. **Fix:** one transaction per channel (or per cycle) with `executemany`.

### N4 (P2) — The coverage check still lists in the *old* order, so its report no longer describes the watcher
`coverage.check` uses RSS when the canary says RSS answers, else the playlist (coverage.py:48-63) — it ignores `config.PLAYLIST_FIRST`. So the daily report's `listing` field ("rss") and its 24 h edge (RSS-exact publish dates, coverage.py:116-117) describe a listing the watcher no longer performs, while the watcher uses the playlist's approximate dates. The report's "never discovered by the watcher (a watcher miss)" verdict is still sound (it matches on video id), but the report's own framing is now inconsistent with the watcher. **Fix:** make `coverage.check` use the same order (`config.PLAYLIST_FIRST`) and label the source it actually used.

### N5 (P2) — No runtime kill switch
`poll_channel(..., playlist_first=None)` supports the old order, but nothing exposes it: `service.watch_once` (service.py:229) never passes it, and `config.PLAYLIST_FIRST` is a source constant. Reverting to RSS-first requires a **code edit and a restart**. A one-line env override (`PP_INGEST_PLAYLIST_FIRST=0`) would give the orchestrator a same-minute rollback without touching the tree. Cheap insurance for a change whose whole justification is a 3-hour A/B.

### N6 (P2) — `by_source` can report a negative publish→discovered
`by_source` computes `(discovered_ts - published_ts) / 60` with no clamp (stats.py:161). A future publish time (a scheduled premiere whose `release_timestamp` is ahead) or clock skew yields a negative p50, which reads as nonsense in live.json. Clamp at 0 and count the negatives.

### N7 (P2, documentation) — The publish time's *source* silently moved
`fetch.process` derives `rss_pub` only when `discovered_via == "rss"` (fetch.py:150-151). With playlist-first, almost every video is `uploads_playlist`, so `rss_pub` is `None` and `publish_time` falls through to yt-dlp's `timestamp` (fetch.py:37-38). That is **exact** (yt-dlp's `timestamp` is the full `uploadDate`, not the date-only `publishDate`), so there is no precision loss — but the diff's claim "RSS's exact time when RSS listed it, else yt-dlp's timestamp" now describes the *minority* path. The measurement's source has changed for nearly every video; the design should say so, and the `published_source` column will now read `yt-dlp timestamp` almost everywhere (which is correct, but a reader comparing to the pre-change history should know).

### Answers to the diff's three questions
1. **Loss / double-count / queue record:** no. Verified path by path (playlist success → `upd={}`; playlist failure → RSS; RSS 304 → empty list, `break`, `new=0`; `rss_mode=False` → playlist only; `playlist_first=False` → the old order). `add_video` is idempotent on `video_id`; `via` becomes `uploads_playlist` (intended); ETag is preserved, never overwritten by the playlist path; `newest_published` is a max.
2. **Cost:** sound **if** N1 is fixed. 64 listings/cycle through 3 shared slots is ~76 s of gate occupancy per 10-minute period — acceptable against a 6-minute median gain, but only because the gate is not starved. Without the N1 fix the tail (43 min) can invert the benefit.
3. **Breaker risk:** **not materially increased.** The A/B did ~540 playlist listings in 3 h (≈3/min) with 0 errors; the watcher's own overnight log did ~6,500 listings in ~8 h (≈13.5/min) with the breaker never opening. The watcher's steady-state rate (64 per 10 min ≈ 6.4/min) is **below** the overnight rate that saw no limit. The playlist endpoint is also a different surface from the RSS feed. The residual risk is the *tail* (N1), not the rate.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| watch / listing (playlist-first) | 4/5 (consensus) | **4/5** | Logic verified again; no loss, no double-count, old order intact. Unchanged. |
| Shared yt-dlp gate / fetch interaction | 3/5 (not separately scored) | **2/5** | N1: the listing now occupies the gate that the probe and captions need; the 43-min tail can starve the fetch path. This is the change's real cost and cycle 1 did not score it. |
| queue | 4/5 | **3/5** | N3: the change doubles ~960 fsync'd single-row transactions per cycle, each taking the global queue lock. |
| stats / observability | 4/5 | **3/5** | N2: the new by-source metric compares different populations and cannot show the gain it was built for. |
| coverage | 4/5 | **3/5** | N4: the coverage check still lists in the old order; its report no longer describes the watcher. |
| mine / ledger / providers / purge / flagcheck / downsignal | unchanged | unchanged | Outside this diff; no regression found. |
| **Overall** | "ready for production" | **Ready with conditions** | The change itself is correct; the conditions are N1 (gate), N5 (kill switch), N2/N4 (measurement honesty). |

---

## 5. FINAL PRIORITY LIST

**P0 — none.** No path loses, double-counts, or corrupts a video; no law (L-aa, L-j, L-m, L-u, L-x) is broken by this diff.

**P1**
1. **Reserve the gate for the fetch path** — `pipeline/ingest/watch.py:38-74` (the gate), `pipeline/ingest/service.py:228-233` (the 64-listing cycle), `pipeline/ingest/fetch.py:220-224` (captions defer while the breaker is open). Give the listing 2 of the 3 slots (or add a fetch-only slot), and/or bound the watch cycle so a slow YouTube cannot hold the gate for 43 min. *Test: a cycle whose listings all hit the 120 s timeout must not prevent a caption download from completing.*
2. **State the breaker's effect on captions in the design** (design 3) — the fallback (C1-1) protects the listing only; the captions stall for the breaker's whole window. No code change; a sentence in the design.

**P2**
3. **A runtime kill switch** — `pipeline/ingest/config.py:30` / `pipeline/ingest/watch.py:181`: honour `PP_INGEST_PLAYLIST_FIRST` so RSS-first can be restored without a code edit and restart.
4. **Make the by-source metric paired, or label it honestly** — `pipeline/ingest/stats.py:155-163` (and the C1-2 test): record both sources' first-seen times, or rename the figure so it is not read as the 6-minute gain.
5. **Batch the queue's inserts** — `pipeline/ingest/queue.py:142-158`: one transaction per channel instead of one per entry (halves the fsyncs and the lock hold time).
6. **Coverage lists in the watcher's order** — `pipeline/ingest/coverage.py:48-63`: use `config.PLAYLIST_FIRST` and label the source actually used.
7. **Clamp `by_source` at 0** — `pipeline/ingest/stats.py:161`: a negative publish→discovered is not a measurement.
8. **Document the publish-time source change** — `pipeline/ingest/fetch.py:150-151`: with playlist-first, `rss_pub` is almost never used and `published_source` becomes `yt-dlp timestamp` nearly everywhere (exact, but a change in the measurement's provenance).

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Reserve one of the three yt-dlp gate slots for the fetch path (probe + captions) and bound the watch cycle's duration** — otherwise playlist-first's 64 listings per cycle can starve the probe and the caption download for longer than the 6-minute discovery gain it buys (watch.py:38-74, service.py:228-233, fetch.py:220-224).

---

## 7. PRODUCTION READY?

**Yes with conditions.**

The change itself is correct and I found no P0: no video is lost, double-counted, or mis-recorded; the old order is intact behind `playlist_first=False`; the error text is preserved; the breaker risk is not materially increased (the watcher's listing rate is below the overnight rate that saw no limit). Ship it **after**:

1. **P1-1** — the gate reservation / cycle bound (the only condition that protects the caption and probe path under a slow or degraded YouTube);
2. **P2-3** — the `PP_INGEST_PLAYLIST_FIRST` kill switch (a same-minute rollback without a code edit);
3. **P2-4** — the by-source metric either made paired or relabelled, so the 6-minute gain is not claimed from a figure that cannot show it.

P2-5 through P2-8 may follow in the next commit; they are improvements, not blockers. The suite (361 tests) passes and the two cycle-1 additions (the rate-limited fallback test, the by-source test) are the right pins for this change.