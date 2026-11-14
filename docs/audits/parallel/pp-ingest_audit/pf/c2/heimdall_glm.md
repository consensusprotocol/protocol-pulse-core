# heimdall_glm (z-ai/glm-5.3-flash, 185.1 s, $0.005, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (heimdall_glm, second review)

**Scope:** diff 98a57406 → working tree (b78ae552's changes included), against my Cycle 1 output and the other models' Cycle 1 findings. Same code, one more pass.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting:

- **muse's C1-2 (live.json `publish_to_discovered_min_by_source`)** — I flagged the 253 s tail and the stale-ETag note but did not propose *measuring* the playlist-first gain in production. muse's metric is the right instrument: it turns my "recorded, probably doesn't matter" into a number that either confirms or refutes it. Taken in b78ae552 (`stats.by_source`, watch.py-adjacent, stats.py:155–163). I missed it; it's the better finding.
- **qwen's calm() observation** — I verified `calm()` decrements on any success (watch.py:56–58, 73) but didn't note the *consequence*: with 3 concurrent slots, an in-flight success after a trip shortens the next pause. I'd have called it "by design" too, but qwen said it first and it's correct. Not a defect; a documented-by-accident behavior.
- **muse's N+1 note** — 1,920 autocommit INSERTs/cycle. I walked `add_video`'s idempotency but never counted the transaction cost. Pre-existing, correctly classified by muse as not-a-regression. I missed the framing.
- **The cycles.py hard-ceiling fix (b78ae552)** — I never audited cycles.py in Cycle 1 (it's outside the diff's headline, but it *is* in the working tree). The `_one(head + body + tail, max_chars)` change and the per-row try/except (cycles.py:109–113) are exactly the kind of "one row never loses the whole line" hardening I should have caught. Missed.

What nobody caught that I also didn't: see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

**Consensus items (all three) — "no video lost or double-counted; queue records preserved."** Agree, and I re-verified the two paths the consensus rests on:

- `add_video` (queue.py:142–158) `INSERT OR IGNORE` on `video_id` PK — idempotent across sources; `discovered_via` = first adder. ✔
- `newest_published` (watch.py:229–231): playlist entries carry no `published` key, so `p = _ts_iso(ts_)` — an ISO-8601 UTC string with `+00:00`, same shape as RSS's `published`. Lexicographic comparison stays order-correct. ✔ (My Cycle 1 Path-F analysis; nothing in b78ae552 touches it.)

**C1-1 (rate-limited playlist → RSS fallback → no backoff).** Agree, and the test (mutation-checked) is the right pin. One refinement the consensus line glosses: the *no-backoff* behavior is only correct while RSS answers. If the breaker is open AND the canary says RSS is up but RSS then 404s (the historically common mode — 2026-11-07, 2026-11-12), the channel records `consecutive_errors += 1` and backs off — which is the old, correct behavior. So the fallback's asymmetry (breaker-open → RSS → success → no backoff) is *only* benign because the breaker's own `until` gates the next playlist attempt. Verified: watch.py:65–66 raises before the semaphore, so the next cycle's playlist attempt fails fast, RSS answers, no backoff, and the breaker's exponential `until` (watch.py:53) is the real backoff. Sound, but the *reason* it's sound is the breaker, not the fallback — worth saying because it means the breaker's 10→20→40→60→3600 s ladder is now load-bearing for listing cadence, not just for rate-limit survival. Nobody said this.

**C1-2 (by_source metric).** Agree. One nit: `by_source` (stats.py:155–163) buckets by `discovered_via`, which is the *first* adder. A video listed by the playlist but added by RSS in an earlier cycle (or vice versa) lands in the earlier source's bucket. That's the right denominator for "which source discovered it" but a slightly wrong one for "which source *would have* listed it first" — the A/B question. Not a defect; the metric's docstring says "the video's discovered_via," so it's honest. Recorded.

**muse's refuted BACKFILL_H finding.** Agree with the refutation, and I'd go further: the 72 h edge case requires a channel's *first* listing to land within 1 h of a video's 71st hour — probability ~1/72 per channel per first-listing, and the video is past the 12 h moments' expiry anyway (config.py:40). Double-irrelevant. Correctly refuted.

**glm's (my) rotate-the-order P1.** Still recorded, still agree it's recorded-not-taken: mean 76 s against 600 s period; the C1-2 metric will show whether the tail matters. Self-consistent.

**qwen's providers.py:851 cache-before-`available` "bug."** Partially disagree with its framing. It's not a bug; it's the documented design (providers.py:851–853 comment: "a stored validated reply costs nothing, calls nobody, proves nothing about health (frozen / no lease: reused)"). The `enabled` check at :851 is the *config* enabled, not the *runtime* callable — deliberately, so a frozen vendor's stored replies still serve. qwen's own conclusion ("a stored validated reply costs nothing and may still be reused") is the spec, not a violation. qwen hedged ("Is this a violation?") and never answered; I answer: no.

**muse's "ETags survive the mode switch" note.** Agree, and it's the same observation as my Cycle 1 stale-ETag note from the other direction. Both directions are safe: a stale ETag yields 200 (full feed, fine) or 304 (empty, fine — playlist already caught the items). No loss either way. ✔

## 3. NEW FINDINGS FROM THIS REVIEW

Three things the combined Cycle 1 outputs missed. All verified against the working tree.

**N1 (P2, correctness-adjacent, watch.py:211): the error-join's detail asymmetry is now *order-dependent* in a way the old code wasn't.** Old code: RSS error = kind only; playlist error = kind+detail, *regardless of which was tried first*. New code: detail is kept iff `get is playlist` — so with `playlist_first=True` (the default), a *playlist* failure keeps its detail and an *RSS* failure after it does not; with `playlist_first=False`, the *RSS* failure (tried first) keeps kind-only and the *playlist* fallback keeps detail. Same as old. But: the *first* failure's detail is what survives in `last_error` when both fail, and which failure is "first" now depends on the flag. With the default, `last_error` = `"playlist_unreadable: <detail>; rss_http_404"` — the *fallback's* kind, no detail. When the on-call reads `last_error` to diagnose, the RSS failure's reason (the historically interesting one: 404 vs network) is gone. muse called this "minor but inconsistent" and left it; I'm making it concrete: the diagnostic loss is *new* under the default order, because under the old order the playlist (the fallback, the interesting failure) always kept its detail. One-line fix if wanted: keep detail for both, or for the *last* failure. Not a ship-blocker — `q.event("list_error", ...)` at watch.py:216 records the same joined string, so nothing else has it either.

**N2 (P2, stats.py:82 + 155–163): `by_source`'s denominator silently excludes the metric's purpose.** `by_source(live_m)` filters to `state == MINED` rows (stats.py:34, 36) *and* `published_ts`/`discovered_ts` non-null. A video mined 3 h after publish because its captions were late contributes a 180-min "publish → discovered" lag to the *playlist* bucket even though discovery was 6 min. The metric's name says "publish_to_discovered" but it measures "publish → discovered, for videos that later mined." With playlist-first, the *slow-to-mine* videos dominate the tail, so the p90 will read worse than the discovery gain actually is. Fix: compute from the `disc`/`fresh`/`new` rows (stats.py:26–28) which already have `published_ts`? — no, they don't select it. Two-line fix: add `published_ts` to the :26 SELECT and compute `by_source` over `new` (live discoveries), not `live_m` (mined). The docstring says "live discoveries with a measured publish time only" — the code delivers "mined discoveries," which is a *subset*. Nobody caught this; it's the difference between the metric answering "did playlist-first help discovery" and "did playlist-first help discovery, among videos that also mined promptly." The test (test_service.py::test_live_json_breaks_the_publish_to_discovered_lag_down_by_listing_source) passes either way because it presumably seeds mined rows.

**N3 (P2, watch.py:186–187 + 204–206): the backoff skip-then-error path can record a *stale* `last_poll_at`.** When `row["backoff_until"] > now_ts`, the function returns early at :187 *without* updating `last_poll_at`. Correct. But when the breaker is open (not the channel's backoff — the *global* yt-dlp breaker), the playlist raises `rate_limited` at :66, the loop continues to RSS; if `rss_mode` is also False (canary down), `entries is None` and the error path at :213–215 runs: `backoff_until = now_ts + min(60 * 2**n, 3600)`. So a *global* breaker trip (one channel's 429) sets *per-channel* backoff on every channel polled in that window — they'll skip their next polls even after the breaker closes, for up to 3600 s. This is the "per-channel backoff when RSS is down too" the consensus recorded as unchanged, but the *mechanism* changed: under the old order with `rss_mode=True`, a breaker trip hit RSS first (no breaker — RSS is urllib, not yt-dlp) and succeeded, so no channel backed off. Under the new default, the breaker-trip hits the *playlist* first, RSS answers, no backoff — *unless* `rss_mode` is False, in which case every channel in that cycle backs off. So the new order *reduces* spurious backoff when RSS is up and *introduces* it when the canary is down and the breaker trips. Net: probably better, but it's a behavior change nobody named, and the recorded "per-channel backoff remains only when RSS is down too" is now the *common* case during a canary-down + breaker-trip coincidence, not the rare one. Worth one line in the design doc; no code change.

**N4 (P3, cycles.py:73): `max([t for t in (mined, v["hook_ts"]) if t] or [None]) if (mined or v["hook_ts"]) else None`** — the guard and the `or [None]` are redundant: when the guard is true, the list is non-empty, so `or [None]` never fires; when the guard is false, the ternary returns None without evaluating the left side... actually it does evaluate it (Python evaluates the condition, then only the chosen branch — the left side is the chosen branch when the guard is true). So: guard true → list non-empty → `or [None]` dead. Guard false → returns None. The `or [None]` is unreachable. Harmless; noted for the record since this is a second-pass audit. (b78ae552's own change; nobody flagged it because it's correct, just redundant.)

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| watch.poll_channel (the diff) | 9.0 | 9.0 | No new defect; N1/N3 are behavior notes, not bugs. The C1-1 test + fallback is correctly pinned. |
| stats.by_source (new in b78ae552) | — (not reviewed) | 7.5 | N2: the metric measures mined-discoveries, not discoveries; the docstring promises the latter. Two-line fix. |
| cycles.py hardening (b78ae552) | — (not reviewed) | 8.5 | Good hardening (per-row try, hard ceiling); N4's dead `or [None]` is cosmetic. |
| Error diagnostics (watch.py:211) | 8.5 | 8.0 | N1: the default order now drops the fallback's failure detail, which the old order always kept. |
| Overall | 8.8 | 8.7 | Slight deduction for the metric's denominator and the diagnostic asymmetry; both P2, both cheap. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none. (Unchanged from Cycle 1; the consensus holds and I re-verified its two load-bearing paths.)

**P1 HIGH**
- None. (C1-1 and C1-2 are *taken* — they're in the tree with tests. Nothing new rises to P1.)

**P2 MEDIUM**
1. **N2 — stats.py:26, 34, 82, 155–163:** `by_source` should run over live discoveries (add `published_ts` to the :26 SELECT, compute over `new`), not over mined rows; the docstring (stats.py:156–157) promises discoveries. Otherwise the playlist-first p90 understates the gain.
2. **N1 — watch.py:211:** keep the failure detail for both sources (or at least the last), so `last_error`/`list_error` keeps the fallback's reason under the new default order. One line.
3. **N3 — watch.py:186–187, 213–215:** document (design 3) that a global breaker trip during a canary-down window now sets per-channel backoff on every channel of that cycle — a new, probably-benign coupling.

**P3** — N4 (cycles.py:73, dead `or [None]`); qwen's cache-before-`available` (not a bug, add one clarifying comment if touched).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Fix N2: compute `publish_to_discovered_min_by_source` over live discoveries, not mined ones — it's the one number the orchestrator will read to judge whether this whole change was worth it, and right now it measures something subtly different from what its name promises.

## 7. PRODUCTION READY?

**Yes, with two conditions** (both P2, both ≤5 lines):

1. **stats.py:** `by_source` over live discoveries (add `published_ts` to the stats.py:26 SELECT; compute over `new`), so the metric matches its docstring — this is the number the 6-minute-gain claim will be judged by in production.
2. **watch.py:211:** keep the failure detail for the RSS (fallback) failure too, so `last_error` stays diagnostic under the default order.

Everything else — the consensus's no-loss/no-double-count, the C1-1 fallback+test, the C1-2 metric's existence, the recorded-not-taken items — ships as is. 361 tests collected; the two mutations were caught; the breaker/fallback coupling (N3) is documented-or-accepted, not fixed.