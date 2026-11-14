# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 275.5 s, $0.030, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (diff 98a57406)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting:**

*   **GLM caught the ETag staleness implication more precisely than I did.** I noted `upd` stays `{}` on playlist path and ETags survive mode switch. GLM walked the consequence: stale ETag on fallback yields either 200 or 304, both safe, no video loss. I flagged it as "worth noting" without closing the loop on safety. GLM closed it.
*   **Qwen caught the `calm()` decay interaction with concurrent breaker.** I stated "no deadlock" and "no race across channels" but did not analyze `calm()` decrementing `trips` on any success while breaker is open. Qwen correctly identified that an in-flight success can shorten a concurrent trip's backoff. I missed this nuance. It is by design (exponential backoff with decay), not a bug, but I should have named it.
*   **Consensus C1-1 / C1-2 were not in my Cycle 1 P1s.** My P1s were (1) RSS detail dropped on fallback, (2) ETag staleness note. The consensus P1s that actually shipped — breaker-open fallback to RSS without backoff, and `publish_to_discovered_min_by_source` — were identified by GLM and Muse respectively. I described the fallback correctly in correctness analysis but did not elevate the breaker-open behavior to a P1 with a pinning test. Muse's per-source metric I did not propose at all.

**What I caught that they underweighted:** The RSS-detail asymmetry on the fallback path (watch.py:211) — I flagged it explicitly as inconsistent; GLM noted it as "subtly asymmetric" but dismissed as preserved behavior; Qwen did not flag it. It remains the only logic inconsistency in the diff.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| **No video lost / double-counted; queue records preserved** (all three) | **Agree** | `INSERT OR IGNORE` on `video_id`, `discovered_via` correctly records first source, `newest_published` uses `published` or `_ts_iso(ts_)`, ETag preserved via `upd` not overwritten. Verified independently. |
| **Error text joins both sources as before** (all three) | **Agree** | Old: RSS kind-only, playlist kind+detail. New: same via `if get is playlist` guard. Behavior preserved. |
| **C1-1: breaker-open falls back to RSS, no backoff while RSS answers** (GLM P1, taken) | **Agree — should have been my P1** | `YouTubeGate.run` raises `rate_limited` immediately when `open_for()>0`; `poll_channel` catches `ListError` and tries next source. If RSS answers, `entries` is set, no error path, no `backoff_until` increment. Correct and important. Pinned by test. |
| **C1-2: `publish_to_discovered_min_by_source` per-source p50/p90/n** (Muse P1, taken) | **Agree — should have been my P1** | Without it the 6-min median gain is unmeasured in prod and regression invisible. `stats.by_source` correctly filters `live_m` (live discoveries with measured `published_ts`) and groups by `discovered_via`. |
| **Muse P1 "BACKFILL_H 71h old video seen_old"** — refuted | **Agree with refutation** | Only on `first_sight` (`listed==0`), only at 72h edge, and `EXPIRY_H=12h` means any video >12h old is past usable window anyway. No usable row lost. |
| **GLM P1 "rotate channel order (253s tail)"** — recorded | **Agree with recorded** | Mean 76s vs 600s period; tail ~60s extra vs 360s gain. Not a blocker; per-source metric will show if it matters. |
| **Qwen: `calm()` shortens later pause** | **Partially agree** | Correct observation, but by design. With `YTDLP_CONCURRENCY=3`, at most 2 in-flight successes can decrement `trips` by 2 before breaker fully opens. Acceptable for scraper; not a defect. |
| **Qwen: cache-before-available with frozen vendor** | **Disagree — not applicable to this diff** | Qwen's scenario (frozen vendor's cache hit for new window) is outside `pp-ingest` listing change. Cache reuse for frozen vendors is intentional per `providers.py:851-856` comment: "a stored validated reply costs nothing and may still be reused." Not a bug. |
| **RSS detail dropped on fallback** (my P1) | **Maintain** | Minor but real inconsistency. When playlist fails then RSS fails, RSS detail (e.g. `rss_http_500` body) is discarded. Preserved from old code, but now playlist is primary so the fallback's detail is more likely to be the actionable one. |

## 3. NEW FINDINGS FROM THIS REVIEW

**Nothing new that changes the ship decision.** Combined analysis confirms:

1.  **The `playlist_list` approximate timestamp is correctly not used as `rss_published`.** `fetch.py:150-151` gates `rss_pub` on `discovered_via=="rss"`. With playlist-first, `listing_ts` is approximate (`youtubetab:approximate_date`) and is correctly ignored for publish time. `publish_time()` falls through to `timestamp`/`release_timestamp` from per-video probe, which is exact. All three reviewers verified this; I did in Cycle 1 Step 3.

2.  **The `BACKFILL_H` interaction with approximate dates is bounded.** Playlist `ts` is approximate (day granularity). A video published 71.5h ago could have `ts` rounded to 72h+ and be marked `SEEN_OLD` on first sight, or vice versa. But this only affects first listing of a channel, and `EXPIRY_H=12h` makes it moot for usable moments. No new risk.

3.  **Cost trade-off is sound and measured.** 64 channels × 1 yt-dlp call per cycle through 3-slot gate = ~76s mean cycle (measured over 102 cycles, 6500 listings, 0 rate limits). RSS was 7s but 6 min slower to discover. The 69s extra cycle time is well within the 360s gain. Captions share the gate but `fetch.py:220-223` correctly waits on `gate.open_for()` before caption download.

4.  **No new breaker risk.** Playlist-first does not increase breaker trips: same number of yt-dlp calls per cycle (1 per channel either way), just different endpoint. Breaker behavior is actually improved (C1-1: fallback to RSS while breaker open).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness (watch/poll_channel)** | 9/10 | 9/10 | No change. Logic is correct; minor RSS-detail asymmetry remains but is pre-existing. |
| **Law Compliance (BUILD, L-x, L-l, L-j/m)** | 10/10 | 10/10 | No change. Diff touches only listing order. |
| **Observability** | 7/10 | 9/10 | **Upgraded.** C1-2 `by_source` metric closes the gap I missed. Now the gain is measured. |
| **Resilience (breaker, backoff, fallback)** | 8/10 | 9/10 | **Upgraded.** C1-1 fallback-while-breaker-open is now pinned and correct. Better than before. |
| **Overall** | 8.5/10 | 9/10 | Combined fixes address the two real gaps. |

## 5. FINAL PRIORITY LIST

| Priority | Item | File:Line | Status |
|----------|------|-----------|--------|
| **P0** | *None* | — | No ship-blocker. |
| **P1** | **Done (C1-1):** Breaker-open fallback to RSS without backoff | `watch.py:60-66, 204-211` | Taken. Test `test_a_rate_limited_playlist_falls_back_to_rss_and_backs_nothing_off` fails without it. |
| **P1** | **Done (C1-2):** Per-source `publish_to_discovered_min_by_source` in live.json | `stats.py:82, 155-163` | Taken. Test fails when not split by source. |
| **P2** | RSS error detail discarded on fallback path | `watch.py:211` | Pre-existing, minor. When both sources fail, RSS detail (HTTP status body) is dropped. Consider `e.detail[:80]` for RSS too, or at least for `rss_http_5xx`. Not blocking. |
| **P2** | ETags go stale while playlist succeeds continuously | `watch.py:192-199` | By design, safe (stale ETag → 200 or 304, both handled). Could add periodic RSS refresh (e.g. every Nth cycle) if RSS cache semantics matter, but not needed now. |

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Ship it as-is — the two Cycle 1 fixes (breaker fallback + per-source latency metric) already capture all the leverage; the remaining P2s are polish.**

## 7. PRODUCTION READY?

**Yes.**

Conditions: None beyond what is already merged (C1-1 and C1-2). The diff is measured (A/B: median 6 min gain, 0 errors in 540 listings), safe (no video loss, no double-count, publish time independent of listing source), and now observable (per-source p50/p90/n in live.json) and resilient (breaker-open fallback pinned).

Suite: 361 tests passed.