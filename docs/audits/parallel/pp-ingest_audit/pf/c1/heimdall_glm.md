# heimdall_glm (z-ai/glm-5.3-flash, 331.1 s, $0.006, finish stop)

# FORENSIC CODE REVIEW — pp-ingest (branch pp-ingest, diff a49aac40 → 98a57406)

## SECTION 1: CORRECTNESS

### 1.1 The changed flow (poll_channel, watch.py:177–235)

The diff moves the listing order into a loop over two closures. Walking it:

**Path A — playlist first, playlist succeeds.** `playlist()` returns `(entries, "uploads_playlist")`, loop breaks. `upd` stays `{}` — correct, since the playlist path never touches ETag/Last-Modified. `channel_update` at watch.py:232–234 spreads `**upd` (empty) — no ETag corruption. ✔

**Path B — playlist first, playlist fails, RSS answers.** `err` accumulates `"playlist_unreadable: ..."`; then `rss()` runs. Note the error-join logic at watch.py:211:

```python
err = f"{err + '; ' if err else ''}{e.kind}" + (f": {e.detail[:160]}" if get is playlist else "")
```

This is correct but subtly asymmetric: when the *playlist* fails first, its detail is included (`playlist_unreadable: <detail>`); when *RSS* then also fails, only the kind is appended (`...; rss_http_404`), detail dropped. That matches the old behavior (old code: RSS error recorded kind-only, playlist error recorded kind+detail) — so no regression, but the asymmetry is now less obvious because both failures flow through one line. Verified against the old code: old RSS branch did `err = f"{e.kind}"` (detail dropped), old playlist branch did `err + '; ' + kind + ': detail'`. ✔ Behavior preserved.

**Path C — playlist first, playlist fails, RSS skipped (`rss_mode` False).** The loop: `get is rss and not rss_mode → continue`. Then loop ends, `entries is None`, error path at watch.py:212–217. `err` = the playlist's kind+detail. Backoff incremented. ✔ Matches old behavior (old: RSS skipped, playlist tried, its error recorded).

**Path D — playlist_first=False (old order).** `(rss, playlist)`: if `rss_mode` False, RSS is skipped, playlist runs. If RSS raises, `err = "rss_http_404"` (no detail), then playlist runs. If playlist also raises, `err = "rss_http_404; playlist_unreadable: <detail>"`. ✔ Identical to old.

**Path E — RSS 304 (not_modified).** `rss()` returns `([], "rss")` — an empty *list*, not None. The loop breaks on it (`entries, source = get(); break` — the break fires because no exception). Then the `for e in entries` loop at watch.py:220 does nothing, `new = 0`, and `channel_update` still records `last_ok_at`, `last_source="rss"`, and `**upd` carries the (possibly refreshed) ETag. ✔ Same as old.

**Path F — the `upd`-on-exception subtlety.** In `rss()`, `upd.update(...)` happens *before* the return, inside the closure. If `rss_list` raises, `upd` is never touched (the exception propagates before the update) — good. But if `rss_list` *succeeds* and then... nothing else can fail in `rss()` (the list comprehension over `ents` — could `_parse_iso(e["published"]).timestamp()` raise? No: `rss_list` already filtered entries where `_parse_iso` returns None at watch.py:115). ✔

**One real behavioral difference worth flagging (not a bug, but a change):** in the old code, when `rss_mode` was True and RSS *succeeded*, the playlist was never tried. In the new default (playlist first), when the playlist *succeeds*, RSS is never tried — meaning **ETag/Last-Modified validators go stale**. They're preserved in the DB (`upd` not overwritten — watch.py:194–195 does `headers.get("ETag") or row.get("etag")`, and the closure only runs when RSS runs), so when the code later falls back to RSS, the stored validators are still there and conditional headers are sent. ✔ No loss. But note: while the playlist succeeds continuously, the stored `etag`/`last_modified` are never refreshed — they'll be whatever the last RSS success gave. When RSS is later needed, a stale ETag yields either 200 (full feed, fine) or 304 (empty, also fine — the playlist already caught the new items). No video loss either way. ✔

### 1.2 Does any path lose or double-count a video?

`add_video` (queue.py:142–158) is `INSERT OR IGNORE` keyed on `video_id` — idempotent across sources. A video listed by both sources in successive cycles is added once; the second listing's `add_video` returns `new=False`. **No double-count.** ✔

`discovered_via` records whichever source *first* added it — with playlist-first, that's now usually `"uploads_playlist"` instead of `"rss"`. That's the intended change. One consequence: `fetch.process` at fetch.py:150–151 derives `rss_pub` only when `discovered_via == "rss"`:

```python
rss_pub = _dt(v.get("listing_ts")).isoformat() if v.get("discovered_via") == "rss" and _dt(v.get("listing_ts")) else None
```

With playlist-first, `listing_ts` is the playlist's *approximate* timestamp (`--extractor-args youtubetab:approximate_date`, watch.py:130–131), and it's not used as `rss_published` — correct, because `publish_time` (fetch.py:30–41) prefers `release_timestamp`/`timestamp` from the per-video probe, which is exact. The design doc says "The publish time is not the listing's: it is yt-dlp's own per video at fetch" — the code does exactly this. ✔

**Edge: a video listed by the playlist whose probe later fails repeatedly.** `PROBE_RETRY_S` (fetch.py:23) caps at 3600 s; `tries` grows unboundedly but `_retry_at` clamps via `min(tries, len-1)`. No runaway. ✔

**Edge: `newest_published` (watch.py:229–231).** With playlist entries, `p = e.get("published") or _ts_iso(ts_)` — playlist entries have no `published` key (watch.py:144–145: only `video_id, title, ts, live_status, duration, url`), so `p = _ts_iso(ts_)` — an ISO string of the *approximate* epoch. RSS entries have exact `published`. Mixing formats in one comparison field: both are ISO-8601 UTC with `+00:00`, so lexicographic comparison (`p > newest`) works *only if* the formats are identical. `_ts_iso` produces `2026-11-14T12:34:56+00:00`; RSS `published` is `2026-11-14T12:34:56+00:00` (YouTube'sAtom format, e.g. `2026-11-14T12:34:56+00:00`). Both same shape → string comparison is order-correct. ✔ (Fragile but correct today; noted in P3.)

### 1.3 Race conditions

- `poll_channel` runs in 4 threads (service.py:228–229, `ThreadPoolExecutor(max_workers=4)`) over *different* channels — no shared-row races. `q.add_video`/`channel_update` are behind the queue's RLock (queue.py:84, 147). ✔
- The 3-slot `YouTubeGate.sem` (watch.py:40) is shared with fetch's probe/captions (service.py:268 uses `YTDLP_CONCURRENCY` workers, and `gate.run`/`gate.sem` inside `fetch._store_captions` at fetch.py:225). Listing now *always* consumes gate slots (before, when RSS answered, it didn't). This is question 2 of the brief — see 1.5.
- `first_sight = row["listed"] == 0` (watch.py:188) read before the loop; `listed` updated at the end. Two cycles can't overlap for the same channel (the watch loop is sequential per cycle; within a cycle each channel appears once). ✔

### 1.4 N+1 / performance

- `q.channel(cid)` once per channel per cycle — 64 SELECTs + 64 INSERT-or-IGNORE + 64 UPDATEs per 10-min cycle. Trivial for SQLite. Not an N+1 in the harmful sense.
- `add_video` does one INSERT + (on new) one event INSERT per entry — 30 entries × 64 channels = up to 1,920 inserts/cycle worst case, but `INSERT OR IGNORE` on existing ids short-circuits the event. Acceptable; the `videos_dup`/`videos_fp` indexes (queue.py:47–48) keep `find_duplicate` cheap. ✔

### 1.5 The cost question (reviewer question 2)

Old steady state (RSS healthy): 64 RSS HTTP GETs/cycle, ~0 yt-dlp processes for listing. New steady state: **64 `yt-dlp -J --flat-playlist` processes per 10-min cycle** through the 3-slot gate, sharing it with probes and caption downloads.

Measured: 76 s average cycle (max 253 s) for the listing phase alone, ~6,500 listings, no breaker trips (design §3). The gate is a `BoundedSemaphore(3)`; a 253 s stall delays captions by up to ~4 min. Given the 12 h expiry and 10-min poll, a 4-min caption delay is immaterial. The trade is sound **but** it rests on one number: 102 cycles over ~34 h, 6 busy channels in the A/B. 64 channels × 144 cycles/day = 9,216 yt-dlp listings/day. If YouTube's playlist endpoint is heavier than RSS (it is — it's an HTML/JSON page, not a 15-min-cached XML), the breaker (watch.py:50–58, doubling 10→60 min) becomes the single failure mode: when it trips, *listings, probes, and captions all stop* (watch.py:65–66 raises before even acquiring the slot). The design accepts this; the mitigation (RSS fallback) exists but note: **when the breaker is open, `poll_channel`'s playlist call raises `ListError("rate_limited")` (watch.py:65–66), then falls to RSS — which is *not* gated** (watch.py:89–119, plain urllib). So the fallback genuinely covers breaker-open. ✔ Good design. But: `rss_mode` is decided by the canary (service.py:223–224) *before* the cycle, and the canary itself (watch.py:238–246) calls `rss_list` — ungated, fine.

One subtle cost regression: when the playlist succeeds, RSS is never called, so the 15-min RSS cache benefit is discarded — but the playlist gives fresher data, which is the point. Net: more yt-dlp load, less freshness lag. Measured acceptable.

### 1.6 Edge cases that will break

- **`uploads_url` (watch.py:122–125) requires `len(cid) == 24`.** A registry channel id of any other length raises `ListError("bad_channel_id")` — caught in the loop, recorded as an error, backoff. But with playlist-first, a channel that *used to work via RSS* (RSS has no length requirement, watch.py:92) now fails **permanently** (backoff doubles to 60 min, never succeeding) if its id isn't exactly 24 chars. Old behavior: RSS-first meant such a channel never hit `uploads_url` unless RSS failed. **This is a real, if narrow, regression** — the registry (A1: 64 channels) presumably has well-formed ids, but nothing in `poll_channel` guards it. P2.
- **`playlist_list` with 0 entries** (a channel with no uploads): `j["entries"]` is `[]`, loop yields nothing, `new=0`, `listed += 0`. Fine. But `first_sight` stays True forever (`row["listed"] == 0`), so every cycle re-runs the 72 h backfill check — harmless (all old, `SEEN_OLD`), just means `add_video` is called with `first_sight=True` repeatedly for the same old ids; `INSERT OR IGNORE` makes it a no-op. ✔
- **`_parse_iso` on RSS `published`** — already guarded in `rss_list` (watch.py:115). ✔
- **Empty `entries` from a 304 + `newest` comparison** — covered above.
- **`err` when the *first* source succeeds but returns garbage** — `playlist_list` raises `ListError("playlist_unreadable")` on bad JSON (watch.py:133–137); falls to RSS. ✔

### 1.7 Silent failures

- `q.event("list_error", ...)` (watch.py:216) — recorded. ✔
- The `res["errors"]` count in `watch_once` (service.py:231) counts `r.get("error") and not r.get("skipped")` — a backoff-skipped channel returns `error: "backoff", skipped: True` (watch.py:187) and is *not* counted as an error. Correct (it's not an error), but the cycle log then shows `errors: 0` while 60 channels were skipped — the `skipped` key is returned but never surfaced in `res`. Minor observability gap. P3.

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
|---|---|---|
| **BUILD: ~10 min, ETag/backoff, last-seen ledger, durable queue** | **COMPLIANT** | watch.py:177–235 (poll), 212–217 (backoff), 232–234 (last-seen); queue.py:28–61 (SQLite WAL). ETag now only refreshed on RSS successes — preserved, not lost (watch.py:194–195). |
| **L-x NO SINGLE MODEL** | **COMPLIANT** | providers.json:115–131 — every role ≥2 back-ends, enforced at load (providers.py:158–161). Vendors/models only in providers.json (test: `test_no_vendor_or_model_name_outside_the_provider_config`). |
| **L-l reply counts only whole** | **COMPLIANT** | mine.py:447–499 (strict validator, no repair); providers.py:982–989 (reject → re-ask with reason, 3 attempts); flagcheck.py:176–203. |
| **L-j / L-m fail closed** | **COMPLIANT** | coverage.py:94 (`measured = not unmeasured`); ledger.py:299–306 (unreadable optout → raise); spend.py:143–147 (unmeasured → "unmeasured", never "ok"); purge.py:396–400 (any problem → nothing deleted). |
| **L-h / L-k read as spoken, records never rewritten** | **COMPLIANT** | contract.py:123 (`E.spoken`), fetch.py:77–86 (fingerprint over spoken text); store writes via `ts._store`/`_write_once` only (fetch.py:236–240). |
| **L-e word timing at cut time** | **COMPLIANT** | mine.py:543–544 (`duration_s` null for `timing == "segment"`, estimate flagged); design §4. |
| **L-u hard exclusions** | **COMPLIANT** | mine.py:23–24 HARD_RISKS; ledger.py:347–348 (pre-applied, never relaxed); Shorts never mined (fetch.py:157–159). |
| **L-v speaker change / re-uploads** | **COMPLIANT** | contract.py:129–135 (measured, else null); ledger.py:351–354; fetch.py:186–191, 241–247 (duplicate by title+duration / text fp). |
| **Secrets: by name from env, never printed** | **COMPLIANT** | providers.py:180–221 (Keyring, `redact`), 241–247; redirect refused (providers.py:322–327); test `test_keys_never_appear_in_repr_or_errors`. |
| **SPEND FREEZE** | **COMPLIANT** | providers.py:783–786 (`frozen`), 806–818 (`available`); providers.json:5–9; paid route the only exception, capped (providers.py:860–867, 125–132 of providers.json). |
| **90% tripwire notifies, never halts** | **COMPLIANT** | spend.py:176–197; providers.py:791–797 (metered → end of chain, never removed); test `test_the_tripwire_notifies_and_moves_the_metered_back_end_last_never_out`. |
| **L-aa (this diff's law): time savers automatic once measured** | **COMPLIANT** | The diff *is* the measured change: A/B documented in config.py:30–33; `PLAYLIST_FIRST` default True; escape hatch `playlist_first=None`→config (watch.py:181). |

No violations found. One PARTIAL-adjacent note: the **ETag/Last-Modified** machinery (BUILD clause) is now effectively dormant while the playlist succeeds — it's preserved and correct, but the "conditional headers" benefit is unrealized in the new steady state. That's the intended trade (freshness > bandwidth), not a violation.

---

## SECTION 3: SECURITY

- **SQL injection:** All queue access is parameterized (`?` placeholders) — queue.py:108–110, 148–153, 166, 173–175, 179–181, 186–187, 225–226, 242–250. The only f-string SQL is `queue.py:133–134, 165, 208` (`cols = ", ".join(f"{k}=?...")`) where keys come from code-controlled dicts (`VIDEO_FIELDS`, `HOOK_COLUMNS`) — validated at queue.py:161–163, 205–207. **No injection.** ✔
- **Secrets:** providers.py:180–221 — parsed from the env file by name, never logged; `redact` (213–220, 241–247) scrubs error bodies; `_NoRedirect` (322–327) prevents the bearer key following a redirect; `override_allowed` (168–177) constrains runtime base-URL overrides to localhost or the configured host+scheme. ✔
- **Untrusted transcript → prompt:** mine.py:397–400 (`_untrusted` escapes `<`→`‹` so captions can't close the `<sentences>` block); prompt marks the block untrusted (mine.py:105–106, 206–208, 281–283). Prompt-injection via channel/title also escaped (mine.py:407–408). ✔
- **Filesystem:** purge.py:456 — real-path containment check (`rp.startswith(unit_real)`, `protect`, `FORBIDDEN`); symlinks never followed (purge.py:231, 417, 432, 453). `spec` validated strictly (purge.py:58–99: absolute paths, no `..`, protected-path exclusion). ✔
- **Rate limiting (outbound):** the YouTubeGate (watch.py:38–74) + per-backend Throttle/Health (providers.py:654–682, 575–640) + global 20-in-flight semaphore (providers.py:769–771). ✔
- **`PP_SELECTID_PIPELINE` / module loading by path** (contract.py:33–48, downsignal.py:58–70): loads arbitrary Python from a configured path — trusted-ops concern, not a security boundary; acceptable.

No issues.

---

## SECTION 4: FRONTEND QUALITY

There is no UI in this diff (headless service + CLI). Judged as CLI/observability:

- `tools/ingest_watch.py` subcommands have consistent argparse help; `status`/`coverage`/`hooks`/`purge` print human+JSON. ✔
- **Loading/error/empty states:** `coverage` prints counts even when 0; `hooks` prints "waiting (note)" per video (tools:180–182); `purge` prints kept/deleted/unresolved. ✔
- `live.json` (stats.py:161–168) is the operational "dashboard" — atomic via tmp+`os.replace`. ✔
- No mobile/JS concerns. Not applicable beyond CLI.

Score reflects "no UI, CLI is solid, not world-class-graded."

---

## SECTION 5: BACKEND QUALITY

- **DB writes:** single connection + RLock; `isolation_level=None` (autocommit) — no explicit rollback, but every write is a single statement, so SQLite's own atomicity suffices. `PRAGMA synchronous=FULL` + WAL (queue.py:86–87). The one multi-statement sequence (`_settle`: append ledger → set_state) is deliberately crash-tolerant: "a crash between the two re-appends identical lines on restart; readers keep the latest line per moment_id" (design §7; ledger.py:313–317 latest-wins). ✔ Correct by design, not by transaction.
- **Ledger append:** flock + O_APPEND + fsync + torn-tail sealing (ledger.py:44–66, 69–85). Every line validated *before* write; one bad line → nothing written (ledger.py:39–43). Exemplary.
- **External calls:** every yt-dlp/HTTP call has a timeout (watch.py:60, 128; providers.py:229); retries with backoff + jitter + Retry-After (providers.py:672–678); circuit breaker (575–640); graceful degradation via chain (837–885). ✔
- **Threads/loops:** `_loop` (service.py:855–864) catches Exception, logs, continues — a crash in any loop never kills the service. `BaseException` paths re-raise after recording (service.py:258–262, 306–311) so a SIGINT during fetch doesn't strand a video in `probing` (test: `test_a_stop_inside_a_fetch_never_strands_the_video_in_probing`). ✔
- **Memory:** `_SHA` cache bounded at 4,096 (purge.py:206, 219–220); `self._conv` cleared at 5,000 (service.py:706–707); `Health.events` deque(maxlen=50). ✔
- **Logging:** errors carry traceback (truncated to 2,000 chars) into `events` (service.py:256, 261, 304, 469, 530, 544, 861); the service log mirrors stdout. Enough context. ✔

One weakness: `Service._log` (service.py:183–190) writes the log file *without* a lock — two threads can interleave partial lines. Lines are written in one `f.write(line + "\n")` call; on CPython, small writes to a buffered file from multiple threads can interleave. Practically, `print(flush=True)` goes to the tmux pane (GIL-atomic-ish) and the file may rarely interleave. P3.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Genuinely excellent (say so):**
- The ledger's crash semantics (append-only, flock, fsync, torn-tail seal, latest-line-wins, carry_forward) are production-grade — better than most production systems I've audited.
- Fail-closed discipline is *consistent*: unmeasured ≠ pass everywhere (coverage, spend, calibration, purge, signal). This is the hardest habit to maintain and it's maintained.
- The reply cache + "a stored validated reply costs nothing and proves nothing about health" distinction (providers.py:851–856) is a subtle, correct insight.
- The calibration-reuse gate (service.py:577–621) with `prompts_sha` + `asked_at` + exact-backend/model match is exactly how you avoid stale-allowance bugs.

**Material gaps (only these):**

1. **No backpressure signal from the gate to the watch loop.** When the breaker trips, `poll_channel` raises for *every* channel (64×), each recording an error and *doubling its own backoff* (watch.py:213–215) — so one YouTube hiccup puts 64 channels into 60-min backoff even after the breaker (max 60 min) clears. The channel-level backoff and the global breaker compound. A world-class system would distinguish "my breaker" from "their error" and not let the global breaker inflate per-channel backoff. (watch.py:212–217; the breaker raise at 65–66 happens *before* the semaphore, so it's cheap, but it still counts as a consecutive error.)

2. **`newest_published` mixes two time formats** (approximate playlist epoch-ISO vs exact RSS ISO) in one comparison field (watch.py:229–231). Correct today because both are `+00:00`-suffixed ISO; one format change (e.g. YouTube switching to `Z`) silently breaks the "newest" heuristic. It's only used for observability, so the blast radius is small — but it's the kind of latent inconsistency a Bloomberg-grade system would type-erase at the boundary.

3. **No jitter/stagger across channels within a cycle.** All 64 channels are listed in one burst through 3 slots (service.py:228–229). A 253 s cycle means the *last* channel is listed ~4 min after the *first* — the effective discovery latency is the cycle's tail, not the poll interval. Staggering (or priority-rotating the channel order) would cut p90 publish→seen. The design's own metric ("every new upload mined within minutes") is measured at the *median*; the tail is where the playlist's advantage erodes.

4. **`watch_once`'s `ex.map`** (service.py:229) processes channels in registry order; a slow channel (253 s) delays the channels *after* it in the same 4-worker pool. Same root cause as #3.

Everything else — retries, breakers, spend, expiry, purge, signal — is already at or above the bar. Do not add more.

---

## SECTION 7: SCORES

| Dimension | Score | Note |
|---|---|---|
| Backend logic | 92 | Correct, crash-tolerant, idempotent; minor: 24-char id assumption, backoff compounding |
| Frontend/UI | 78 | CLI-only; solid, not graded against a UI spec |
| Error handling | 93 | Fail-closed everywhere; BaseException paths; one bad line → nothing written |
| Security | 90 | Parameterized SQL, redaction, no-redirect, path containment; module-by-path is trusted-ops |
| Performance | 85 | 64×yt-dlp/cycle through 3 slots; 253 s tail; no channel stagger |
| Law compliance | 96 | Every law traced to code; ETag dormancy is a documented trade, not a breach |
| World-class gap | 82 | Ledger/purge/signal are best-in-class; discovery tail + backoff compounding are the gaps |
| **OVERALL** | **89** | |

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | none — the diff is correct; nothing here will lose a video or corrupt the queue | — | —

P1 HIGH | Don't let the global breaker's `rate_limited` raise inflate per-channel `consecutive_errors`/backoff (skip the backoff increment, or cap it, when the error kind is `rate_limited` from the gate) | watch.py:212–217 + 65–66 | one YouTube 429 puts 64 channels into 60-min backoff that outlives the breaker, silently stretching discovery to an hour

P1 HIGH | Stagger or rotate channel order across cycles (or priority-queue by `newest_published` proximity) in `watch_once` | service.py:228–229 | the 253 s cycle tail, not the 10-min poll, sets p90 publish→seen; the playlist's 6-min advantage is erased for the back half of the registry

P2 MEDIUM | Guard/normalize channel-id length before `uploads_url`, or fall back to RSS-only for non-24-char ids | watch.py:122–125, 177–181 | a registry id that isn't exactly 24 chars worked under RSS-first and now fails forever with 60-min backoff

P2 MEDIUM | Type-erase the publish-time format at the boundary: store a parsed epoch alongside `newest_published`, or compare parsed datetimes | watch.py:229–231 | mixed approximate-playlist / exact-RSS ISO strings compared lexicographically; one format change silently breaks the "newest" heuristic

P3 LOW | Surface `skipped` (backoff) counts in the watch cycle event/log | watch.py:187, service.py:227–233 | a cycle where 60/64 channels were in backoff logs `errors: 0` and looks healthy

P3 LOW | Add a lock (or a single-writer queue) to `Service._log`'s file writes | service.py:183–190 | concurrent threads can interleave partial lines in service.log

P3 LOW | When the playlist succeeds continuously, note in the channel row that ETag/Last-Modified are stale-by-design (or refresh them opportuntistically once/day) | watch.py:194–195, 232–234 | avoids a future reader assuming the validators are live

---

## SECTION 9: THE ONE THING

Make the watch loop's *tail* its head: stagger/rotate the 64 channels (and decouple the global breaker's `rate_limited` from per-channel backoff), because your measured 6-minute freshness win is currently consumed by a 253-second, registry-ordered cycle tail — the latency you're optimizing is the p90, not the median.

---

## SECTION 10: FINAL VERDICT

Ready for production. The diff does exactly what it claims: the playlist-first order is correctly implemented with the old order preserved behind `playlist_first=False`, no video is lost or double-counted, ETag state is preserved, and the error-join semantics match the previous behavior. Before/with the next merge, fix the two P1s — breaker-induced backoff compounding and the registry-ordered cycle tail — because they directly erode the "mined within minutes" promise this change was made to deliver.