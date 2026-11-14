# heimdall_glm (z-ai/glm-5.3-flash, 723.0 s, $0.007, finish length)

# FORENSIC CODE REVIEW — pp-ingest (branch pp-ingest, working tree + diff a2a9386d)

Scope note: the review covers the 17 files provided plus the change under review (downsignal.py probe-claim uptake). Where the review depends on modules NOT in the diff (transcript_store, eligibility, select_by_id, heimdall_health, canon, story_semantics, gpu0), I say so explicitly rather than speculate.

---

## SECTION 1: CORRECTNESS

### 1.1 The change under review (probe-claim uptake) — the primary question

**Q1: Is the signature check sound?**

`downsignal.py:120-123` (post-diff numbering; the diff hunk at old 110-120):

```python
try:
    takes_who = "who" in inspect.signature(self.hh.probe_due).parameters
except (TypeError, ValueError):
    takes_who = False
self.probe_kw = {"who": WHO + " probe"} if takes_who else {}
```

Sound, with one caveat:

- `probe_due` in the builder's diff is a **plain module-level function** (`def probe_due(path=STATE, now=None, who="")`), so `inspect.signature` resolves it. For a plain function, `Signature` construction can raise `ValueError` (unresolvable annotation, e.g. `from __future__ import annotations` absent + a forward-referenced type) or `TypeError` (a C function / builtin without signature). Both are caught. ✔
- **Caveat (P3):** the check is done once at `__init__` (downsignal.py:119-123) and cached in `self.probe_kw`. If the module were reloaded, the kw would be stale — but the module is loaded once per process (the change note says so: "the watcher loads the module once at start, so a restart takes up 11ed255f"), so this is consistent with the deployment model. Not a bug; a documented constraint.
- **Caveat 2 (P3):** the check tests the *parameter name* only, not whether it is keyword-accepted vs positional-only. If a future module made `who` positional-only (`def probe_due(path, now, who, /)`), `probe_due(now=..., who=...)` would raise `TypeError: got some positional-only arguments passed as keyword arguments`. That TypeError would be caught by `_call`'s broad `except Exception` (downsignal.py:188-190) and read as "signal not read" — fail-closed, but it would silently disable the probe. Given the builder's contract, this is theoretical. Note it.

**Q2: Does the claim change the probe life cycle?**

Walk the cycle:

1. `tick()` (downsignal.py:151-175): `_flush()` → `_report_probe()` → if `now >= next_mode`, `mode()` → if not `_probing()` and no drill, `probe_due(now=..., **probe_kw)`.
2. With the builder's diff, a `True` from `probe_due` **stamps `last_probe_utc`/`last_probe_by`**. So the claim happens *inside* the module, under its flock, before this watcher's `_start_probe()` runs. ✔
3. `_start_probe()` (downsignal.py:213-228) spawns the probe thread; the thread's outcome lands in `self.probe_out` under `self.lock`.
4. Next `tick()`: `_report_probe()` (downsignal.py:230-259) reports via `probe_result(answered, now=_utc(t), ...)`. The builder's diff says `probe_result` **re-stamps `last_probe_utc`** (answer-anchored). So the slot's next-due time moves to the report time. ✔

**Interaction with `_probing()` (downsignal.py:177-182):** the guard prevents a second probe while one is in flight *in this process*. With the claim, the module also prevents a second probe *across processes* within the slot. These compose correctly: this watcher claims, then `_probing()` returns True until the thread finishes and the outcome is reported. ✔

**Interaction with the C2-1 kept report (downsignal.py:247-255):** when `probe_result` returns None (the shared state did not take it — e.g. its flock was held), the outcome is kept in `self.probe_out` while younger than `PROBE_EVERY_S` (default 120 s, read via `getattr(self.hh, "PROBE_EVERY_S", 120)` at downsignal.py:249). Meanwhile:

- `_probing()` returns True (probe_out is not None), so no new probe starts. ✔
- The kept outcome is retried at the next tick (5 s later). If the state takes it, `probe_result` re-stamps `last_probe_utc` — the slot's next-due moves *later* than the claim. If the state never takes it within 120 s of the outcome's time, the report is dropped and counted (`probe_reports_lost`), and the next `probe_due` will be due again (claim-anchored, since no report re-stamped). ✔ — this is exactly the "a claimer that never reports leaves the slot spent from its claim" semantics the builder's docstring promises.

**One subtle interaction (P2, not a bug but worth stating):** the claim stamps `last_probe_utc` at claim time. If the probe *call itself* takes longer than `PROBE_EVERY_S` (60 s deadline per back-end, two back-ends → up to ~120 s+), the slot is already spent; when the report finally lands, `probe_result` re-stamps — so the *next* slot starts from the report. But if the report is dropped (C2-1 expiry) after a long probe, the next `probe_due` becomes due immediately (the claim stamp is now >120 s old), and this watcher's `_probing()` guard has already cleared. So: claim → long probe → dropped report → immediate re-claim. That is correct behavior (the slot was spent, the report lost, the state needs a fresh probe), but it means a systematically-losing-report scenario produces a probe every ~120 s + probe duration, not every 120 s. Acceptable; the builder's design.

**Q3: Any path where passing `who` could make a module call fail?**

- `probe_due(now=..., who=...)`: the builder's diff accepts `who=""` default; passing a non-empty string is fine. ✔
- `note`, `mode`, `probe_result`: unchanged signatures (the builder's message says so, and the diff only touches `probe_due`); this watcher calls them without `who`... wait, no: downsignal.py:200, 206, 247 pass `who=WHO` / `who=WHO + " probe"` to `note` and `probe_result` **already** (pre-existing code, lines 200, 206, 247). So those functions already accepted `who` in 125e7381. The change only adds `who` to `probe_due`. ✔
- The `load_module` check (downsignal.py:55-59) requires `note, mode, probe_due, probe_result, HealthUnreadable, STATE, MODES` — all present in both versions. ✔

**Verdict on the change: correct, minimal, fail-closed.** The only weakness is the once-at-init signature check (documented) and the theoretical positional-only future.

### 1.2 Pre-existing correctness (the 17 files) — the findings that matter

**C1. `mine.py:286` — window advance can loop forever or skip sentences.**

```python
i = max(j - min(overlap, (j - i) // 2), i + 1)
```

If `j == i` (the first sentence alone exceeds... no, `j > i` is guaranteed after the inner loop when `j < len(rows)` because the inner loop always consumes at least one row when `j == i`). Actually: inner loop starts `j = i`, condition `j - i < max_sent` (0 < 40 ✔), then `n = len(rows[j]["text"].split())`, `if j > i and words + n > max_words: break` — at `j == i` the condition `j > i` is False, so the row is always consumed. So `j >= i+1` after the inner loop, and `i = max(j - min(6, (j-i)//2), i+1)`. With `j - i == 1`: `min(6, 0) = 0`, so `i = max(j, i+1) = j = i+1`. ✔. With `j - i == 40`: `min(6, 20) = 6`, `i = j - 6`. ✔. Termination: `i` strictly increases. ✔. But: **the overlap guarantee "consecutive windows share at most `overlap` sentences"** — with `j - i == 1` (one gigantic sentence), the next window starts at `j` (the *next* sentence), sharing 0. With `j - i == 2`: `min(6,1)=1`, `i = j-1`, sharing 1. ✔. With `j - i == 12`: `min(6,6)=6`, `i = j-6`, sharing 6. ✔. OK — the "at most half a window" clause: `min(overlap, (j-i)//2)`. For `j-i = 13..∞`, `(j-i)//2 >= 6`, so overlap = 6 = half of 12... for `j-i = 13`, half is 6.5, floor 6. ✔. Sound. (The test `test_windows_of_huge_sentences_never_walk_one_sentence_at_a_time` covers it.) No finding.

**C2. `mine.py:497` — hook duration check reads `duration_s` first, then `duration_estimate_s`.**

```python
d = l["duration_s"] if l["duration_s"] is not None else l["duration_estimate_s"]
```

For caption records, `timing == "segment"`, so `duration_s` is None (mine.py:424-425) and `duration_estimate_s` carries the interpolated duration. For word-timed records, `duration_s` is set. Correct. But: **a hook row whose duration is unmeasured is dropped** (mine.py:498-499, `why = ... "duration not measured" if d is None`), and the ruling says "A row outside 4-14 s (or unmeasured) is not written" — ✔ matches. No finding.

**C3. `ledger.py:55-56` — torn-tail close reads one byte via `os.pread` under the flock, but `seal()` (ledger.py:69-85) reads the last byte WITHOUT the flock.**

`seal()` (ledger.py:73-76):
```python
with open(path, "rb") as f:
    f.seek(-1, os.SEEK_END)
    if f.read(1) == b"\n":
        return False
fd = os.open(path, os.O_WRONLY | os.O_APPEND)
```

Between the read and the `os.open`, a concurrent `append()` (from another process — the design says one service per store, but `flagcheck.main` (flagcheck.py:566) and `ab.main` (ab.py:260) also open the ledger... no, they open *different* ledgers/cache dirs; `simulate_adapter` (flagcheck.py:399-409) reads the ledger, never writes). Within one store, only the service appends, and `seal()` runs at service start (service.py:119) before the loops start. So the race is theoretical. But `seal()`'s read-then-write is not atomic even against itself: two `seal()` calls concurrently could both see a torn tail and both append `\n` — harmless (an extra blank line, skipped by `read`'s `if not raw.strip(): continue` at ledger.py:167-168). ✔. P3.

**C4. `ledger.py:122-149` — `offset_before` bisection assumes mined.at order; the docstring (ledger.py:124-128) admits "at most one mining pass (minutes) out of order, which the caller's one day of margin covers".**

The margin: `cutoff = min(since, now - horizon_h) - timedelta(days=1)` (ledger.py:309). A line mined *before* `cutoff` but physically *after* the bisection point... the bisection finds the first line with `t >= cutoff` scanning forward from `mid`; a line out of order by more than the margin would be skipped. The test `test_the_bounded_read_is_exact_while_lines_are_out_of_order_by_less_than_its_margin[20]` pins 20 s of disorder. Is 20 s the real bound? The docstring says "one mining pass (minutes)". A mining pass for one video: 3 videos concurrently, each with windows; the *append* happens at pass end with one `stamp()` (service.py:296, `stamp=config.iso`), so all lines of one append share one timestamp. But the *hook* pass appends later (service.py:387) with a later stamp — still monotonic. The `check_row` appends (service.py:453) also later. So the file is in append order = stamp order, except: **`carry_forward` + `_append` under `self.wlock` (service.py:294-296) — the read of earlier lines and the append are one step *for this process*, but the stamp is taken inside `ledger.append` (ledger.py:50-52) under the *file* lock.** Two threads of the same process: `wlock` serializes them. ✔. Two processes: the flock in `append` (ledger.py:47) serializes. ✔. So mined.at is monotonic except when a *long* pass's lines are appended after a *short* pass's — but each append's stamp is taken at append time, so still monotonic. The only disorder: a line whose `mined.at` was stamped, then the process crashed before... no, the stamp and the write are in the same critical section. ✔. Actually the disorder the docstring mentions: "lines written before that stamp carry their pass's start" — that's the *pre-stamp* era (lines appended without `stamp=`), not this code. For this code, order holds. The 1-day margin is generous. ✔. No finding.

**C5. `ledger.py:200-204` — `carry_forward`'s three-valued logic for `about_bitcoin`/`altcoin`.**

```python
fx["altcoin"] = True if True in (a_new, a_old) else (False if a_new is False else None)
fx["about_bitcoin"] = False if False in (b_new, b_old) else (True if b_new is True else None)
```

- `altcoin`: OR-like (True if either True); if new is False and old is None → None (missing). If new is None and old is False → None. If new is False, old is False → False. ✔ (matches the comment "an earlier MISSING value adds nothing; a missing value of THIS line stays missing").
- `about_bitcoin`: AND-like (False if either False); if new is True, old is None → None. ✔.

But: the adapter (ledger.py:349) refuses `flags.get("altcoin") is not False or flags.get("about_bitcoin") is not True` — so a None (missing) value excludes the moment. Is that right? The comment at ledger.py:204-205 says "the adapter refuses it: L-m" — fail closed, a missing measurement is not a pass. ✔. But note: `build_line` (mine.py:436) always sets `flags_ext` with concrete booleans from the validator (which requires bools, mine.py:373-375), so a None can only arise if an *earlier* line lacked the field — i.e. lines from before `flags_ext` existed. Then the new line's concrete value combines with the old's missing → for `about_bitcoin`: `b_new=True, b_old=None` → `False if False in (True, None)` → no → `True if True in (True, None)` → True. Wait: `False in (True, None)` is False, so we go to `True if b_new is True` → b_new is True → **True**. But the comment says "a missing value of THIS line stays missing" — here the *old* is missing, the new is present. For AND semantics: old missing, new True → should the result be True (the only measurement says True) or None? The code gives True. For `altcoin`: `a_new=False, a_old=None` → `True in (False, None)`? No → `False if a_new is False` → **False**. So: old missing + new concrete → the new's value wins (for both). Old concrete + new missing → for `about_bitcoin`: `b_new=None, b_old=True` → `False in (None, True)`? No → `True if b_new is True`? b_new is None → **None**. For `altcoin`: `a_new=None, a_old=False` → `True in (None, False)`? No → `False if a_new is False`? a_new is None → **None**. So: new missing + old concrete → None (the new line's missing value "stays"). That's asymmetric: a *new* line that somehow lacks the field (impossible via the validator, but possible via a hand-edited or older-format line) downgrades the flag to missing, excluding the moment. Fail closed. ✔. The test `test_an_earlier_missing_value_adds_nothing_and_a_missing_value_of_the_new_line_stays_missing` pins exactly this. ✔. No finding — the semantics are deliberate and tested.

**C6. `providers.py:786-787` — the cache is consulted BEFORE `available()`, so a frozen/disabled back-end's stored reply is reused.**

```python
if use_cache and self.backends[bid].cfg.get("enabled", True):
    out = self._cached(...)
    if out is not None:
        ...
        return out
ok, why = self.available(bid, breaker)
```

The design says "a stored validated reply costs nothing and may be reused" (frozen / no lease: reused) — ✔ intentional, and `test_a_frozen_vendors_stored_reply_costs_nothing_and_may_be_reused` / `test_a_stored_reply_is_reused_when_the_back_end_is_enabled_but_not_callable_now` pin it. But note: a **disabled** back-end's cache is also consulted (the `enabled` check at :786 uses the *config* flag, and `available()` would later say "disabled"). `test_a_disabled_back_end_with_a_cache_is_not_used` — the test name says "not used", but the code at :786 checks `cfg.get("enabled", True)`: if the config says `enabled: false`, the cache is NOT consulted (the `if` fails). So a disabled back-end's cache is skipped. ✔ consistent. But `OllamaLocalBackend.enabled()` (providers.py:476-480) additionally requires the GPU0 lease — a back-end with `enabled: true` in config but no lease: the cache IS consulted (config enabled), then `available()` → `b.enabled()` → False → skipped. So the cache is used, the live call is not. ✔ matches "no lease: reused". ✔.

**C7. `providers.py:846` — the semaphore is acquired INSIDE the while loop, but `th.wait()` (the throttle sleep) is OUTSIDE.**

```python
while attempt < attempts:
    th.wait()
    rec = {...}
    with self.sems[bid], self.gsem:
        try:
            r = b.complete(p, schema, max_tokens)
```

`th.wait()` (providers.py:646-652) sleeps in 5 s slices while `until` is in the future. During that sleep, the thread holds NO semaphore slot. ✔ good (a 429-paused back-end doesn't waste slots). But: the throttle's `until` is shared by every thread of the back-end (providers.py:637), so after a 429, ALL threads of that back-end sleep — including ones that already passed `th.wait()` and are now inside `b.complete()`. Those in-flight calls are not cancelled. ✔ correct (they're already sent). New calls wait. ✔.

**C8. `providers.py:864-868` — the transport-retry sleep.**

```python
if r.retryable and transport_left > 0:
    transport_left -= 1
    if r.kind not in ("http_429", "overloaded"):
        self.sleep(min(2.0 * (4 - transport_left), 10.0))
    continue
```

`2.0 * (4 - transport_left)`: after the first decrement, `transport_left` = 2 (from 3), so `2.0 * (4-2) = 4.0` s. Second: `transport_left=1`, `2.0*3=6.0`. Third: `transport_left=0`, `2.0*4=8.0`. So delays 4, 6, 8 s. But the *first* retry (transport_left 3→2) sleeps 4 s — the doubling sequence 2,4,8 was presumably intended; this gives 4,6,8. Not a bug (bounded, jitterless), just a different curve than the docstring's "2 s doubling to 60 s" (which describes the *throttle* for 429/overloaded, providers.py:636-637, not this). ✔. P3: the two backoff curves (throttle's 2→60 s doubling for 429/overloaded; this 4/6/8 s for network/timeout/server/empty) are easy to confuse; the module docstring (providers.py:5-6) says "queue-aware backoff on HTTP 429 / 503" which is the throttle. Fine.

**C9. `providers.py:836-838` — `_NoHealth` for breaker-free roles, but the *throttle* still applies.**

`_try` (providers.py:834): `b, th = self.backends[bid], self.throttle[bid]` — the throttle is always the real one. For the probe role (`breaker: false`, providers.json:110), a 429 on the probe still pauses the probe back-end's throttle — but the probe back-ends are *separate* back-end ids (`heimdall_qwen27b_probe`, providers.json:78) with their own Throttle. ✔. And `transport_retries: 0` (providers.json:110) → `rc.get("transport_retries", ...)` → 0 → no retry. ✔. And `attempts: 1` → one call per back-end. ✔. Matches "no transport retry" (ruling 87). ✔.

**C10. `providers.py:731-732` — `order()` moves metered back-ends last when the meter is not 'ok'.**

```python
ch = [b for b in ch if not self._metered(b)] + [b for b in ch if self._metered(b)]
```

Stable: preserves relative order within each group. ✔. But: this runs on EVERY `run()` call (via `self.order(role)` at :773 and `effective()` at :737). `self.meter.state()` takes the meter's lock (spend.py:130-133) — a hot path taking a lock per call. At ~1,000 calls/day, negligible. ✔.

**C11. `service.py:309` — `passes = int(v.get("mine_tries") or 0) + (1 if rejected else 0)`.**

`v` is the row as read by `due()` at the START of the pass (service.py:534). If two passes happen... `mine_tries` is updated in `_settle` (service.py:312, `mine_tries=passes`), and the next pass reads the fresh row. ✔. But: `was_partial = v.get("state") == Q.MINED_PARTIAL` (service.py:310) — `v`'s state is the state *before* this pass's claim (`claim(v["video_id"], Q.MINE_DUE, Q.MINING)` at :535, where `Q.MINE_DUE` includes MINED_PARTIAL). So `was_partial` correctly reflects whether the *previous* pass left it partial. ✔.

**C12. `service.py:319` — `n = self._ledger_count(v) if (was_partial or v.get("moments") is not None) else len(lines)`.**

For a first-time-mined video (`was_partial` False, `moments` None), `n = len(lines)` — the lines just appended. But `lines` here is the *deduplicated* list from `mine_video` (mine.py:470-492, `by_range`), so `len(lines)` = distinct moment ids. ✔. For a re-mine (moments already set), the ledger count. ✔. But: **a video mined twice with DIFFERENT moment ids** (e.g. the contract definitions changed → different w0/w1 → different moment_id): the ledger count counts BOTH generations. The design says "readers keep the latest line per moment_id" — different moment_ids are different moments. Is the old generation's line still returned by the adapter? `best_unused_moments` (ledger.py:314-317) keys by `moment_id` — both generations survive as separate moments. For a 12-h-expiry product, the stale generation would also be returned (it's not expired, not delivered, passes exclusions... unless its `contract_fp` differs → the drift check at ledger.py:357-364 re-derives and drops it if the ids no longer give its text). If the definitions changed such that the ids STILL give the text (e.g. a whitespace-only change in `spoken`), both generations coexist → the packager could cut the same words twice (different moment_ids, same text). The dedupe against re-posts is the builder's (by moment_id), so it would NOT catch this. **P2: a contract-definitions change that preserves text but shifts w0/w1 (or vice versa) produces duplicate moments in the adapter's output.** Mitigated by: the drift check only fires when `contract_fp` differs, and `verify_line` (contract.py:162-181) requires the *exact* words AND text AND moment_id to match — so a w0/w1 shift fails `verify_line` (contract.py:174-175, "words ... != ... under the current definitions") and the line is dropped. So: if the definitions changed, the old line is dropped (drift) — no duplicate. If they didn't change, the same window gives the same moment_id → the latest line wins. ✔. Actually sound. Downgrade to P3/nothing.

**C13. `service.py:452` — `check_row`'s `v` fallback.**

```python
v = self.q.video(l["video_id"]) or {"video_id": l["video_id"], "discovered_ts": self.clock()}
```

`_append` (service.py:293) uses `v.get("discovered_ts")` → for the fallback dict, `self.clock()` (a float) → `datetime.fromtimestamp(float(...) - 86400, timezone.utc)` ✔. But `v` lacks other keys — `_append` only uses `video_id` and `discovered_ts`. ✔.

**C14. `service.py:493` — `check_once` reads the ledger with `from_time=now - timedelta(hours=EXPIRY_H, days=1)`.**

`timedelta(hours=12, days=1)` = 36 h. The adapter's cutoff (ledger.py:309) is `min(since, now - 12h) - 1day`. Here `since` is effectively... `check_once` doesn't use `since`; it reads 36 h back. A moment published 13 h ago (expired) is still read and skipped by the `exp` check (service.py:503-504). ✔. A moment whose *line* was mined 40 h ago but published 10 h ago (mined before publish? impossible — mined after publish). A line mined 40 h ago for a video published 39 h ago: published_ts 39 h > 12 h → expired, skipped. ✔. A line mined 40 h ago, published 20 h ago: expired. ✔. What about a line mined 40 h ago, published 5 h ago? Impossible (mined after publish). So 36 h of ledger covers every still-usable moment (published ≤12 h ago → its line was mined ≤12 h + (mine latency) ago; mine latency could exceed 24 h? A video published, then mined 30 h later (outage) → its line's mined.at is 30 h after publish; published 5 h ago → mined 5 h - 30 h = -25 h... no: published 5 h ago means published_at = now-5h; mined after that, so mined.at > now-5h, within 36 h. ✔. But a video published 13 h ago, mined 30 h AFTER publish = 13-30 = -17 h, i.e. mined 17 h ago... wait: published 13 h ago, mined 30 h after publish → mined 13-30 = 17 h BEFORE now? 13 h ago + 30 h = 17 h in the future. Impossible. Mined at most (now - published) after publish. So mined.at >= published_at > now-12h. Within 36 h. ✔. Sound.

**C15. `queue.py:184-186` — `hook_due`'s SQL.**

```python
SELECT * FROM videos WHERE state IN (?, ?) AND hook_ts IS NULL AND COALESCE(hook_next_ts, 0) <= ? AND published_ts >= ? ORDER BY published_ts DESC LIMIT ?
```

`hook_ts IS NULL` — a video whose hook pass *crashed* mid-`set_hook`... `set_hook` (queue.py:188-193) is a single UPDATE, atomic. But `hook_video`'s success path (service.py:390-393) calls `set_hook` TWICE (once for episode_markers/episode_tpm, once for the rest) — not in one transaction. Between them, a crash leaves `hook_ts` NULL but `episode_markers` set → the next `hook_due` picks it up again (hook_ts still NULL) → the pass re-runs. Idempotent (the ledger's latest-line-wins + carry_forward). ✔. But: the FIRST `set_hook` (service.py:389) sets `episode_markers`/`episode_tpm` — if the second fails, the video's episode measure is recorded but `hook_ts` is NULL → the stats query (stats.py:115-116, `hook_ts IS NOT NULL`) won't count it. Consistent. ✔.

**C16. `queue.py:203-219` — `find_duplicate`'s `before` for a new video.**

```python
me = self.video(vid)
before = me["discovered_ts"] if me else self.clock()
```

`discovered_ts` is a REAL (epoch); `self.clock()` also. ✔. But `me["discovered_ts"]` could be None? The column is `NOT NULL` (queue.py:36). ✔.

**C17. `watch.py:214` — `old = first_sight and ts_ is not None and now_ts - float(ts_) > backfill_h * 3600`.**

`ts_` from RSS is `_parse_iso(e["published"]).timestamp()` (watch.py:194) — a float. From the playlist, `e.get("timestamp")` — could be None (approximate_date). If None, `old` is False → the video is DISCOVERED even if it's a 3-month-old backfill video → it will be probed, then `fetch.process` (fetch.py:173-176) marks it SEEN_OLD. ✔ (two-layer backfill). But: a playlist-listed old video gets a probe (a yt-dlp -J call) before being marked SEEN_OLD — for a 64-channel backfill at 30 videos each, that's up to 1,920 probes on first sight. The design says "uploads older than this are recorded as seen, not processed" (watch.py:28) — but the playlist path can't know the age without the probe (approximate dates). Actually `--extractor-args youtubetab:approximate_date` (watch.py:130) — does `timestamp` come through? The test `test_the_uploads_playlist_is_used_and_lists_streams_and_shorts` presumably uses a fixture. If yt-dlp's flat-playlist entries DO carry `timestamp` (they usually do, approximately), then `old` works. If not, the probe path handles it. Either way, correct, possibly wasteful. P3.

**C18. `fetch.py:150-151` — `rss_pub` uses `v.get("listing_ts")` when `discovered_via == "rss"`.**

```python
rss_pub = _dt(v.get("listing_ts")).isoformat() if v.get("discovered_via") == "rss" and _dt(v.get("listing_ts")) else None
```

`listing_ts` for an RSS-discovered video is the RSS published timestamp (watch.py:194, `e["published"]` → `.timestamp()`). But `publish_time(j, rss_published=rss_pub)` (fetch.py:152) prefers `release_timestamp` for was_live (fetch.py:33-34) over rss_published. For a regular upload, RSS's published (exact, second precision) vs yt-dlp's `timestamp` (also exact) — RSS wins (fetch.py:35-36). ✔. But: the RSS published time is the *feed entry's* published, which for YouTube is the actual publish time. ✔. And `_dt(v.get("listing_ts"))` — `listing_ts` is a REAL; `_dt` requires int/float ✔.

**C19. `fetch.py:193` — `any(k.startswith("en") for k in manual) or auto`.**

`manual` is sorted subtitle-language keys; `auto` is `["en"]`-filtered (fetch.py:46: `k in ("en", "en-orig")`). So `auto` is non-empty only if YouTube lists `en` or `en-orig` auto captions. But `manual` could have `en-US`, `en-GB` → `startswith("en")` ✔. What about a video with ONLY `en-orig` auto? `auto = ["en-orig"]` → truthy ✔. What about `en` manual + `en-GB`? Both caught. ✔. But: a video with manual `fr` and auto `en` → `auto` truthy → proceeds. Then `ts.fetch_captions` presumably prefers manual... not our code. ✔.

**C20. `coverage.py:68` — `now_ts - hours*3600 <= float(pts) <= now_ts + 600`.**

`pts` = the queue's `published_ts` or the listing's `ts`. For an RSS-listed video not yet in the queue, `e["ts"]` is the RSS published (exact). For a playlist-listed one, approximate. The 600 s future slack covers premieres. ✔. But: `v is None and age_min*60 <= POLL_S + POLL_JITTER_S + RSS_CACHE_S` (coverage.py:85) — `age_min*60` is seconds; `POLL_S + POLL_JITTER_S + RSS_CACHE_S` = 600+60+900 = 1560 s = 26 min. A video published 25 min ago, not in the queue: "inside the discovery window". ✔. But the discovery window is actually poll (10 min) + RSS cache (15 min) = 25 min + jitter 1 min = 26. ✔. Plus: the *playlist* fallback has no 15-min cache, so the window is overstated for playlist discoveries — conservative, fine.

**C21. `stats.py:29` — `span_h = max(1e-9, min(hours, (now_ts - min(discovered_ts))/3600))`.**

If `disc` is empty, `min([] or [now_ts])` = now_ts → span 0 → 1e-9 → division fine. ✔.

**C22. `spend.py:53-56` — `_rewrite_top`'s "only a MISSING file starts empty".**

```python
try:
    with open(doc) as f:
        text = f.read()
except FileNotFoundError:
    text = ""
```

An unreadable (permissions) STATE file raises OSError → propagates → caught by the callers (service.py:182-184, 592-596, 644-645) → logged, retried next pass. ✔ (the docstring says exactly this). But: `lines = text.split("\n") if text else []` — an EMPTY (0-byte) existing file: `text = ""` → `lines = []` → the notice is written. ✔. A file whose last line has no trailing newline: `split("\n")` gives a last element without one; `new = "\n".join(...)` — if the notice block is prepended, the last line loses... no: `"\n".join(block + lines)` — the original last line (no trailing newline in the file) becomes a list element, and the join adds `\n` between all → the rewritten file gains a trailing newline. Harmless. ✔.

**C23. `spend.py:56` — the switch line is forced first.**

```python
block = [h for h in block if SWITCH_RE.match(h)] + [h for h in block if not SWITCH_RE.match(h)]
```

If there are MULTIPLE switch lines (the design says "one physical line" holding every switch — `write_switch_head`'s `merged` (spend.py:211-213) joins them into ONE line), there's exactly one. But if a *previous* version left two, both sort first, preserving their order. ✔.

**C24. `purge.py:198-199` — `_latest`'s midnight rule.**

```python
if t is not None and not source and (t.hour, ...) == (0,0,0,0):
    return t + timedelta(days=1)
```

A bare date (midnight) with no recorded source → treated as end of that day. But the pp-ingest queue's `published_at` ALWAYS has a source (`published_source`), so this only fires for the main store's meta.json when `published_at_source`/`published_source` is absent. ✔ (the comment says 4 such metas). But: a legitimately midnight-published video WITH a source → not bumped → could be deleted up to 1 h early (published 00:00, +12h = 12:00; if the actual publish was 00:00:30, deleted at 12:00:00, 30 s early). Trivial. ✔.

**C25. `purge.py:344` — `rp.startswith(protect)` where `protect = realpath(store_root) + os.sep`.**

The FORBIDDEN list (purge.py:41-42) already includes `/data/editorial/`. Double protection. ✔. But: `store_root` defaults to `config.store_root()` (purge.py:307) which is the *staging* store (`<repo>/data/editorial`) — and FORBIDDEN's `/data/editorial/` matches the *main* store's path component. If the repo IS `/home/ultron/protocol_pulse`, both coincide. If the repo is elsewhere (a worktree), the staging store is `<worktree>/data/editorial/` — FORBIDDEN's `/data/editorial/` still matches (it's a substring check: `b in rp`). ✔.

**C26. `downsignal.py:203` — the flush order: "the failure, if any, came after the answer".**

```python
for answered, t in ((True, p["answer"]), (False, p["fail"])):
```

`noted()` (downsignal.py:139-142) sets `pending["answer"] = t, pending["fail"] = None` on an answer; on a failure, only sets `pending["fail"]` if it's None. So within one flush window: answer at t1, failure at t2>t1 → both noted, failure last ✔. Failure at t1, answer at t2: `pending["fail"] = t1` (set), then the answer sets `pending["answer"]=t2, pending["fail"]=None` — the failure is ERASED. Is that right? The module's `note(True, ...)` then never sees the failure. The semantics: the latest outcome is what matters; an answer after a failure means the gateway answered. But the *first failure after the last answer* is what the module wants (the docstring at downsignal.py:11-12: "the latest answer and the first failure after it"). Here, a failure BEFORE the latest answer is discarded — correct per that semantics. But what about: answer t1, failure t2, failure t3? `noted` for t3: `pending["fail"]` is t2 (not None) → not overwritten. So only the FIRST failure after the answer is noted. ✔ exactly the documented semantics. ✔. And: answer t1, failure t2, answer t3, failure t4 — within one window: t1 noted, t2 noted (fail=t2), t3: answer=t3, fail=None (t2 erased), t4: fail=t4. So the module sees answer(t1), failure(t2)... no: the flush sends note(True, t1) then note(False, t2)? No — after t3/t4, pending = {answer: t3, fail: t4}. The flush sends note(True, t3) then note(False, t4). The t1/t2 pair is lost. Is that a problem? The module's 15-min rule: it needs to know when failures started. If t1..t4 all happen within one 5-s tick, the module gets answer(t3), failure(t4) — the failure's time is t4, close enough. ✔.

**C27. `downsignal.py:249` — `float(getattr(self.hh, "PROBE_EVERY_S", 120))`.**

If the module defines `PROBE_EVERY_S` as a non-numeric (a string), `float` raises → caught? No: this is inside `_report_probe`, not wrapped. It would propagate to `tick()` → the signal loop's `_loop` catches (service.py:654-656) → the loop logs and continues. But the probe_out is already consumed (popped at :234-235) → the outcome is lost, counted? No: `probe_reports_lost` is only incremented in the else branch. The exception happens BEFORE. So the outcome is silently dropped, and `out["logged"]` was already set → the evidence line was written. Next tick: no probe_out → nothing. The next probe_due (claim-anchored) fires. Recoverable. P3.

**C28. `service.py:529` — `if free == 3 and not self.q.due(Q.MINE_DUE, 1)`.**

`free == 3` means nothing in flight. If 1-2 videos are in flight, the idle-release check is skipped — correct (the release should only happen when truly idle). But: `self._last_mining` is only updated when NOT (free==3 and nothing due) — i.e. when work was started OR when free<3. If free<3 (videos in flight) but nothing NEW due, `_last_mining` is refreshed → the idle clock resets. Is that right? "no mining due this long: the local model leaves GPU0" — if videos are in flight, the model may be in use, so don't release. ✔. But: if the in-flight videos finish between the `free` check and the next loop, and nothing is due, the NEXT loop sees free==3, nothing due, and `_last_mining` was just refreshed → waits another 120 s. ✔ intended.

**C29. `service.py:104-108` — the executors.**

`self.executor = ThreadPoolExecutor(max_workers=global.max_inflight)` (20) — the WINDOW executor, shared by up to 3 concurrent `mine_video` calls. Each `mine_video` submits ALL its windows (mine.py:458) — a video with 30 windows submits 30 futures into a 20-worker pool. Three videos → 90 futures, 20 workers. The `as_completed` (mine.py:461) consumes them. ✔. But: `self.videos` (3 workers) runs `mine_video`, which submits to `self.executor` and BLOCKS on `as_completed`. If 3 `mine_video` threads each block, and the window executor's 20 workers are all running... no deadlock (the window futures complete independently). ✔. But: **the hook pass uses `self.hook_windows` (4 workers, service.py:108) while the moment pass uses `self.executor` (20)** — the design says "HOOK_WINDOWS = 4: hook windows in flight at once, all hook passes together: the moment passes of new uploads keep the rest of the back-end's slots". But the *back-end* slots are governed by `Router.sems` (providers.py:706), NOT by these executors. So: 3 moment videos × their windows + 2 hook videos × their windows, all funneling into `Router.sems[heimdall_qwen27b]` (12) and `gsem` (20). The executors (20+4=24 potential) exceed the router's 20 global — the excess waits on the semaphore. ✔ (the semaphore is the real bound; the executors just queue). The comment "the moment passes keep the rest of the back-end's slots" is aspirational: the hook's 4 window-workers + the moment's 20 = 24 threads, but the semaphore caps at 12/20. A hook window waiting on the semaphore holds a hook-window THREAD (1 of 4) — so 4 hook windows + 16 moment windows can be in flight; the 17th+ moment window waits. ✔ roughly as documented. No starvation of the moment pass? The semaphore is FIFO-ish (Python's BoundedSemaphore wakes waiters in order) — a hook window that arrives first holds the slot. With 4 hook + 16 moment, the moment pass gets 16/20 of the slots. ✔.

**C30. `service.py:238` — the claim-then-probe race.**

```python
claimed = [v for v in self.q.due(Q.FETCH_DUE, limit)
           if not self.stop.is_set() and self.q.claim(v["video_id"], (v["state"],), Q.PROBING)]
```

`due` reads, then `claim` does an atomic conditional UPDATE (queue.py:166-172). Two concurrent `fetch_once` calls (the loop is single-threaded, but `once` + the service could overlap — no, one service per store). Within the service, `fetch_once` runs on the fetch thread only. ✔. But: `v["state"]` is the state AS READ; if another path changed it between `due` and `claim`, the claim fails (the WHERE clause) → skipped. ✔.

**C31. `mine.py:458` — `futs = {executor.submit(...): (i, w) for i, w in jobs}`.**

If `executor` is shut down (the service stopping), `submit` raises RuntimeError → propagates out of `mine_video` → caught by `mine_video`'s except (service.py:272-276) → the video goes to MINE_WAIT. ✔. But: the RuntimeError happens MID-iteration of the dict comprehension — some futures already submitted, never awaited → they run anyway (the executor's shutdown(wait=True) at service.close() waits). Actually `close()` (service.py:145-146) shuts down `self.videos` FIRST (wait=True), then `self.executor`. So the mine_video threads finish (their futures complete) before the window executor shuts down. ✔.

**C32. `ledger.py:368` — `out.sort(key=lambda l: (-mine.rank_score(l), l["moment_id"]))`.**

`rank_score` (mine.py:387-393) reads `line["scores"]` — a dict; and `line.get("risk")`. For a line where `risk` was replaced by `effective_risk`'s notes-view (`_view`, ledger.py:244-246: `dict(l, risk=eff, risk_notes=notes)`) — `rank_score` reads `line.get("risk")` = eff (the released risk) → the penalty uses the EFFECTIVE risk. ✔ (a released flag no longer penalises). Is that right? Ruling 40 P1: a released flag "stays as a recorded note, not an exclusion" — should it still penalise the RANK? The rank is the packager's ordering; a note-ified flag arguably shouldn't penalise. ✔ defensible.

**C33. `flagcheck.py:521` — `miners = {r["video_id"]: ({r["miner"]["backend"]}, {r["miner"]["model"]}) for r in rows}`.**

For the remeasure, each row's miner is its OWN recorded backend/model. But `checkers` (flagcheck.py:241-247) excludes back-ends/models that mined ANY line of the video — here only the ONE line's miner. If the video had lines mined by TWO back-ends (a re-mine), the remeasure's miner set is incomplete → a checker could be the other miner. Minor: the remeasure is a measurement, not the adapter. P3.

**C34. `ab.py:269` — `spent = lambda: sum((r.get("cost_usd") or 0.0) for r in attempts)`.**

`attempts` grows; `spent()` is O(n) per call, called per video per back-end → O(n²). With ~30 videos × 2 back-ends × ~10 attempts = 600 records, 60 calls → 36,000 iterations. Negligible. ✔.

**C35. `ab.py:105` — `ts.segments_sha256(rec["segments"]) == sha` — a second hash check.** ✔ (the design: "hash-checked").

**C36. `config.py:113` — `if "transcript_store" in sys.modules and os.path.realpath(sys.modules["transcript_store"].STORE_DIR) != root`.**

If `transcript_store` was imported but has no `STORE_DIR` (an older version), AttributeError → not caught → propagates. The design says the store's layout is fixed; the check at :121-122 (`_TS.STORE_DIR`) would also fail. Fail-closed. ✔.

**C37. `config.py:76` — `root.startswith(main + os.sep)`.**

`root = /home/ultron/protocol_pulse` exactly → `root == main` → the first clause. `root = /home/ultron/protocol_pulse2` → startswith(main + "/")? "protocol_pulse2" does not start with "protocol_pulse/" → False → not inside. ✔.

**C38. `watch.py:52` — `self.until = self.clock() + min(600 * 2 ** (self.trips - 1), 3600)`.**

Trips: 1→600, 2→1200, 3→2400, 4→3600 (min(4800,3600)), 5+→3600. The design says "10, 20, 40, 60 min" — 3600 s = 60 min ✔. But `calm()` (watch.py:55-57) decrements trips on ANY successful call — so one success after a 60-min trip drops to 30 min. The docstring (watch.py:61-63) says "Any answer that is not one calms the breaker by one step (so a past trip does not make every later one the 60 min pause)". ✔ deliberate.

**C39. `watch.py:69` — `if not any(m in err for m in AGE_GATE_MARKS) and any(m in err for m in RATE_LIMIT_MARKS)`.**

`err = r.stderr or ""` — but `r` is the result of `config.ts()._ytdlp(args, timeout=timeout)`. If yt-dlp SUCCEEDS (rc 0) but its stderr mentions "not a bot" (a common diagnostic), the gate trips! `RATE_LIMIT_MARKS` includes "not a bot" (watch.py:24) — yt-dlp's verbose output often says "not a bot" when it passes the check. Does `_ytdlp` return the full stderr? Not our code. If it does, a SUCCESSFUL call whose stderr contains "not a bot" would trip the breaker AND raise ListError("rate_limited") — even though the call succeeded. **P2: a successful yt-dlp call whose stderr mentions a rate-limit mark is treated as a failure.** Mitigation: the caller (`probe`, fetch.py:89-107) catches ListError and returns (None, (kind, detail)) — the video is retried. And `playlist_list` (watch.py:127-134) would raise. But the RESULT `r` is discarded — the work is lost. Whether this fires depends on `_ytdlp`'s stderr discipline (not in the diff). Flag as P2-conditional.

**C40. `mine.py:146` — `_AXES_TEXT = PROMPT[PROMPT.index("SCORES (integers"):PROMPT.index("\nFLAGS\n")].split("\n", 1)[1].rstrip()`.**

Fragile string surgery: if PROMPT's wording changes (e.g. "SCORES" moved), this silently produces the wrong axes text in HOOK_PROMPT. There IS a test (`test_the_hook_prompt_states_the_rulings_hook_and_the_moment_prompts_own_flags`) — presumably it checks the axes appear. But it can't check they're the RIGHT ones. P3.

**C41. `mine.py:337` — `MAX_MOMENTS, MAX_MOMENT_SENTENCES = max_n, max_count` inside `validator` — shadowing the module constants.** ✔ deliberate (the closure reads them); the `noqa: N806` acknowledges it. But: the closure ALSO reads `KEYS`, `AXES`, `RISKS`, `REASON_MAX` — the MODULE constants, NOT parameterized. So a hook reply is validated against the same AXES/RISKS/REASON_MAX as a moment. ✔ (the design: "the moment prompt's own score axes and flag list"). ✔.

**C42. `ledger.py:110` — `contract.moment_id(l["video_id"], l["transcript_sha256"], *l["words"])`.** `l["words"]` is `[w0, w1]` — exactly 2 (checked at :104). ✔.

**C43. `queue.py:79` — `sqlite3.connect(path, check_same_thread=False, isolation_level=None)`.**

`isolation_level=None` = autocommit. Every `x()` is one statement, auto-committed. `set_state` (queue.py:157-164) does ONE UPDATE + ONE event INSERT — not atomic. A crash between: the state changed, no event. The design says "Every state change is an `events` row" — a lost event row is a gap in the audit trail, not a correctness issue (the state is the truth). ✔. But: `add_video` (queue.py:144-151) — the INSERT OR IGNORE + the event: the event is only fired if `new` (rowcount==1). ✔. `claim` (queue.py:166-172): the UPDATE + no event — a claim is not a "state change" worth an event? It IS (probing/mining). The design: "Every state change is an `events` row" (section 7). `claim` changes the state WITHOUT an event. **P3: `Queue.claim` (queue.py:166-172) changes the state without writing an event row, contrary to the stated invariant.** Also `recover` (queue.py:195-201) DOES event. And `set_hook` (queue.py:188-193) — no event. P3.

**C44. `queue.py:86-92` — the column-migration reads `PRAGMA table_info(videos)` BEFORE `executescript(SCHEMA)`?** No: `executescript(SCHEMA)` at :85, THEN the pragma at :86. ✔. But: `CREATE TABLE IF NOT EXISTS` — if the table exists WITHOUT `first_sight`, the pragma finds the existing columns; the ALTER adds it. ✔. But the `HOOK_COLUMNS` loop (queue.py:89-91) — `if c not in cols` where `cols` was read BEFORE the ALTER for first_sight. If `first_sight` was just added, `cols` doesn't include it — but the hook columns are different names, so no conflict. ✔. (Style: `cols` is stale after the first ALTER; harmless here.)

**C45. `stats.py:103-105` — `json.loads(q.kv_get("purge_last") or "null")`.** `kv_get` returns the stored JSON (queue.py:111: `json.loads(r[0]["v"])`) — so `q.kv_get("purge_last")` already returns the PARSED object (a dict), and `json.loads(dict)` → TypeError! Wait: `kv_set` (queue.py:114) stores `json.dumps(v)`; `kv_get` does `json.loads(r[0]["v"])` → returns the original object. So `q.kv_get("purge_last")` returns a DICT (or None). Then `json.loads(dict or "null")`: if the dict is truthy, `json.loads(d)` where d is a dict → `json.loads` expects str/bytes → **TypeError: the JSON object must be str, bytes or bytearray**. But it's wrapped: `try: last = json.loads(q.kv_get("purge_last") or "null") except ValueError: last = None`. TypeError is NOT ValueError → **propagates!** Let me check: `json.loads` with a dict input raises `TypeError`. The except catches only `ValueError`. So if `purge_last` is set (a dict), `stats.live()` raises TypeError → `health_once` → the health loop's `_loop` catches (service.py:654) → logged every 60 s, and **live.json is never written**. Is this real? `kv_set("purge_last", json.dumps({...}))` (service.py:610-613) — note: it stores `json.dumps(...)` (a STRING) as the value! Then `kv_set` does `json.dumps(v)` again → the stored value is a JSON-quoted STRING. `kv_get` → `json.loads` → returns the INNER string (a JSON text). Then `json.loads(that_string)` → the dict. ✔! Double-encoded. And `q.kv_get("check_calibration")` (stats.py:134): `kv_set("check_calibration", json.dumps({...}))` (service.py:477) — same double-encoding → `json.loads(json.loads(...))`... wait: `kv_get` returns the inner STRING; `json.loads(inner_string)` → the dict. ✔. And `q.kv_get("signal_switches_seen")` (downsignal.py:276): stored via `kv_set(..., str(len(sw)))` (downsignal.py:280) → `kv_set` stores `json.dumps("3")` = `"\"3\""`; `kv_get` → `json.loads` → `"3"` (a str) → `int("3")` ✔. And `q.kv_get("outage_since")` (service.py:625): stored `str(now)` → kv_get returns the string → `float(since)` ✔. And `q.kv_get("coverage_day")` (service.py:562): stored as a plain string via `kv_set("coverage_day", day)` → stored `json.dumps("2026-11-14")` → returned `"2026-11-14"` ✔. And `q.kv_get("purge_freed_total")` (stats.py:107): stored `str(total)` → returned the string → `float(...)` ✔. And `q.kv_get("purge_blocked_since")` (service.py:581,589): stored `str(since)` → returned the string → `float(...)` ✔; the truthiness check `if self.q.kv_get("purge_blocked_since")` — the STRING "0.0" is truthy! So when `purge_blocked_since` is set to "0.0" (falsy float, truthy string)... it's set to `str(since)` where since = now (a large float) — never "0.0" unless the clock is 0. And the CLEAR path sets `""` (service.py:587) → `kv_set("purge_blocked_since", "")` → stored `json.dumps("")` = `'""'` → `kv_get` → `""` → falsy ✔. OK. So the double-encoding is CONSISTENT because every kv_set of a dict wraps it in `json.dumps` first. Fragile but consistent. **P3: the kv store's double-encoding (kv_set stores `json.dumps(v)`, and callers of dict values ALSO `json.dumps` first) works but is a trap — `kv_get` returns a JSON *string* for dict values, and `stats.py:103`'s `json.loads(...or "null")` relies on it.** Also: `q.kv_get("signal_switches_seen")` returns a STRING "3"; `int(...)` ✔; but the `except (TypeError, ValueError)` at downsignal.py:277 — `int(None)` raises TypeError ✔ caught.

**C46. `stats.py:89` — `reason LIKE 'OUTAGE%'`** — the reason for an outage wait starts with "OUTAGE:" (service.py:342) ✔. But the REJECTED+outage mixed reason (service.py:338-340) starts with "3 window(s) rejected..." → NOT counted as mine_waiting_outage even though the video IS in MINE_WAIT. The stat counts only pure-outage waits. Is that the intent? "Videos waiting on an outage for over 30 min" (the notice) — the notice's `_outage_notice` (service.py:623) uses the SAME LIKE. So a video waiting because of rejected windows (a 10-min retry) doesn't trip the 30-min notice. ✔ (the notice is about OUTAGES). But a MIXED wait (rejected + outage, service.py:338-340) — the reason starts with "3 window(s) rejected" → not counted, though it may ALSO be waiting on an outage. The design (section 7): "Videos waiting on an outage for over 30 min put one line" — a mixed wait's outage component is invisible. P3.

**C47. `coverage.py:57` — `watch._parse_iso(e["published"]).timestamp()`** — if `_parse_iso` returns None, `.timestamp()` → AttributeError → caught? It's inside the `try` at :54-63 which catches `watch.ListError` only. AttributeError → propagates → `health_once` → the loop catches. The whole coverage report for the day is lost. But `rss_list` (watch.py:114) already skips entries whose `_parse_iso(pub.text) is None` → the entries reaching here always parse. ✔.

**C48. `service.py:549` — `if now - self.last_measure >= float(self.cfg["spend_meter"]["measure_every_s"])`.** `last_measure` starts 0.0 → the first health_once measures. But `run()` (service.py:680-681) already measured and set `last_measure`. ✔.

**C49. `providers.py:706` — `min(b.max_inflight, self.cfg["global"]["max_inflight"])`.** If a back-end's `max_inflight` > global, it's clamped. ✔. But `BoundedSemaphore(min(...))` — if `max_inflight` is 0 (a misconfig), `BoundedSemaphore(0)` → acquire blocks forever. `validate_config` doesn't check it. P3.

**C50. `providers.json:104` — the judge chain `["xai_frontier", "gemini_frontier", "anthropic_frontier"]` — ALL THREE vendors are in `spend_freeze.vendors` (providers.json:6).** So under the freeze, `Router.effective("judge")` = [] → the A/B prints "no judge" (ab.py:290-291) ✔ (the design, section 8). But: `load_config` (providers.py:140-142) requires ≥2 back-ends per role — the judge HAS 3, they're just all frozen. ✔. And `flagcheck`'s role (providers.json:107) — both Heimdall (unfrozen) ✔. And `probe` (providers.json:109) — both Heimdall ✔. And `mine` (providers.json:102) — heimdall_qwen27b (unfrozen) + local_gemma (vendor "ultron-gpu0", unfrozen, but `enabled: false`) → effective = [heimdall_qwen27b] → the warning at service.py:676-679 fires. ✔ (the design: "Heimdall is the only callable miner"). ✔.

**C51. `providers.json:114` — `spend_meter.backend: "heimdall_qwen27b"`** — the meter's `get_json("/credits")` uses that back-end's `_request` (spend.py:102) → its key, its base. ✔. But: the meter's backend is ALSO the primary mine back-end — a `/credits` call shares its throttle/semaphore? `get_json` → `_request` → NO semaphore (the semaphore is only in `_try`). So a /credits poll bypasses the in-flight cap. One extra request per 10 min. ✔.

**C52. `spend.py:116` — `self.measured_spend = float(usage) - float(self.c["baseline_usage"])`.** If the gateway RESETS total_usage (a billing cycle), measured_spend goes negative → `state()` (spend.py:133) compares `measured_spend + local_since >= threshold` → negative → "ok" ✔. And the notice: "tripped" only. ✔.

**C53. `spend.py:182` — `keep=(lambda h: False) if state == "tripped" else (lambda h: h.startswith(prefixes[0]))`.**

For "unmeasured": keep the AT-90% line (spend doesn't go back down... but the 90% notice was REMOVED? No: `keep` preserves ONE of this writer's lines matching prefixes[0] (the AT-90% line) — so if the meter goes unmeasured AFTER tripping, the AT-90% line stays AND the UNMEASURED line is added. Two spend lines. The docstring (spend.py:164-165) says "A 90 % notice stays once written". ✔. But: when the meter returns to "ok" (state == "ok", line = None): `keep` = (lambda h: h.startswith(prefixes[0])) → the AT-90% line is KEPT. ✔ (spend doesn't go back down). And the UNMEASURED line is removed. ✔. But: the `mine` function's `line` callable path (spend.py:51-52) — `line` here is a plain value (None or the string), not callable, for `write_state_notice`. ✔.

**C54. `downsignal.py:163` — `drills = [b for b in self.router.chain(self.probe_role) if self._drill(b)]`.** `router.chain("probe")` — the probe role's chain. If a drill override is on heimdall_qwen27b (the MINE back-end, not a probe one), `drills` is empty → the probe runs. ✔ (the drill only affects the noted calls, which are skipped as drill=True). ✔.

**C55. `downsignal.py:133` — `if kind in NO_CALL or rec.get("role") == self.probe_role or self.router.vendor(bid) != self.vendor: return`.**

`NO_CALL = {"cache", "disabled"}`. A "skipped" attempt? `_try`'s emissions have kind = the BackendError's kind or "ok"/"invalid"/"cache". A skipped back-end (frozen, circuit open) never reaches `_try` → no emission → no note. ✔. But: `run()`'s `tried` list records skips — not emitted. ✔.

**C56. `downsignal.py:140` — `self.pending["answer"], self.pending["fail"] = t, None`.** If the SAME tick window has answer→fail→answer, the middle fail is erased (C26). ✔.

**C57. `service.py:690` — the signal thread: `("signal", self.hsig.tick, downsignal.SIGNAL_EVERY_S)`.** `tick(wait=False)` — the loop calls `fn()` = `self.hsig.tick` with NO ARGS → wait defaults False ✔. But `_loop`'s signature: `_loop(name, fn, every, jitter=0.0)` → `fn()` — `tick` takes `wait` as a keyword-only? No: `def tick(self, wait=False)` → `self.hsig.tick()` ✔.

**C58. `service.py:689` — the purge loop: `float((self.purge_spec or {}).get("every_s", 600))`.** If the spec is None (refused), `every` = 600 → the loop runs `purge_once` which logs the refusal and calls `_purge_blocked` ✔ (the design: "a refused spec deletes nothing, and says so every pass").

**C59. `mine.py:434` — `"at": config.iso(now_dt)`.** `now_dt` is `datetime.now(timezone.utc)` passed from service.py:265 — the PASS's start. But `ledger.append(stamp=config.iso)` (service.py:296) OVERWRITES `mined.at` with the append time (ledger.py:50-52). So the line's `mined.at` = the append time, and the `build_line`'s value is discarded. ✔ (the design: "each line's mined.at stamped under the append lock"). But: the `cycle` field (mine.py:433) retains the pass's start-cycle. ✔.

**C60. `contract.py:40-47` — `_load_file` sets `sys.dont_write_bytecode` around `exec_module` — but `sys.dont_write_bytecode` affects the INTERPRETER's future imports too, restored in `finally` ✔. However: `spec.loader.exec_module(mod)` may import OTHER modules (e.g. `canon`, `sentence_law`) — those are written to THEIR worktree's __pycache__? `dont_write_bytecode` is global, so during the exec, no bytecode is written anywhere ✔. But: the imported-into-sys.modules modules (canon, sentence_law) — if the pp-selectid worktree's `canon.py` differs from the main pipeline's, WHICH one is imported depends on `sys.path` order. `config.py:17-18` puts PIPELINE_DIR (this repo's pipeline/) at sys.path[0]. `contract.py:56-57` tries `import eligibility` — from THIS repo's pipeline/ if present, else the worktree. So post-merge, the repo's own eligibility.py is used; pre-merge, the worktree's. The `origin` (contract.py:58, 68) records which. And `fingerprint()` (contract.py:88-103) digests the ACTUAL functions. ✔.

**C61. `contract.py:92` — `import sentence_law`** — from where? Not checked. If it's missing, ImportError → propagates → `fingerprint()` raises → `best_unused_moments`'s try (ledger.py:321-324) catches → `report["contract"]` → then EVERY line hits `fp is None` → dropped "contract definitions unavailable" (ledger.py:355-356). Fail closed ✔. But `contract.sentences` (contract.py:119) ALSO imports sentence_law — a ledger append would fail → the video goes to MINE_WAIT (service.py:269-271, ContractUnavailable? No — ImportError is not ContractUnavailable; it's caught by the generic `except Exception` at service.py:272). ✔.

**C62. `mine.py:302` — `rows = "\n".join(f"[S{s['k']} {_mmss(s['start'])}] {_untrusted(s['text'])}" for s in win)`.** `_mmss(s['start'])` — `start` could be None (a token without a start) → `_mmss(None)` → the except → "--:--" ✔.

**C63. `mine.py:411-413` — `dur = round(max(0.0, float(end) - float(start)), 2) if isinstance(start, (int, float)) and isinstance(end, (int, float)) else None`.** If `start`/`end` are None (unmeasured), dur is None → for a hook, dropped "duration not measured" ✔.

**C64. `ledger.py:349` — `elif flags.get("altcoin") is not False or flags.get("about_bitcoin") is not True`.** For a line WITHOUT `flags_ext` at all (pre-flags_ext era): `flags = {}` → `{}.get("altcoin")` = None → `None is not False` → True → dropped "altcoin or not about Bitcoin". So ALL pre-flags_ext lines are excluded. Is that the intent? The design (section 5): "flags_ext {about_bitcoin, altcoin}" is an ADDITION. Old lines lack it → excluded. Fail closed ✔. But: `carry_forward` (ledger.py:199) does `l.setdefault("flags_ext", {})` — so a NEW line always has it. And the hook pass's lines (mine.py:436) always have it. So only lines appended BEFORE flags_ext existed (a historical ledger) are excluded. For a 12-h-expiry product, those are all expired anyway. ✔.

**C65. `flagcheck.py:196` — `if f" {e} " not in q`** — the evidence must be a SUBSTRING of the normalized quote, surrounded by spaces. `_norm` collapses non-alphanumerics to spaces and strips. `q = f" {_norm(text)} "`. If the evidence is the ENTIRE quote, `f" {e} " == q` ✔. If the evidence has different punctuation (normalized away) ✔. If the evidence is a single word at the very start: `q` starts with a space ✔. ✔.

**C66. `flagcheck.py:252` — `cands = [b for b in checkers(router, miner) if allowed is None or b in allowed]`.** If `allowed` is an empty list (no back-end passed the calibration), `b in allowed` → False → cands = [] → "no checker..." ✔ (service.py:481-482 also guards).

**C67. `service.py:507` — `flags = [f for f in ledger.RELEASE_ON_CHECK if f in l["risk"] and ledger.check_valid(l, f) is None]`.** `l["risk"]` — the LATEST line's risk. But `effective_risk` (ledger.py:229-241) is what the adapter uses; here the RAW risk. A flag already released (a "no" recorded) → `check_valid` returns the record (not None) → not in flags → not re-asked ✔. A flag released by a *previous* line but the latest line's risk still has it (carry_forward copies risk_checks via `setdefault` — ledger.py:207-208: `l.setdefault("risk_checks", {}).setdefault(f, c)` — the NEW line's OWN answer wins, but if the new line has NO risk_checks, the earlier's is copied) ✔.

**C68. `service.py:512` — `if len(todo) <= CHECK_INFLIGHT - len(self.check_inflight): self._check_seen = seen`.** If MORE todo than room, `_check_seen` is NOT updated → the next loop (30 s) re-reads. ✔. But: `todo` was already TRUNCATED to `room` (service.py:514) — so `len(todo) <= room` ALWAYS (after truncation). So `_check_seen` is ALWAYS updated, even when rows were left undone! Then the next loop: `seen == _check_seen` and `clock() < due`? `due` = min(check_next) — the undone rows have no check_next (they were never started) → due = inf → `clock() < inf` → True → return 0. **The undone rows are never picked up until the ledger changes or a retry becomes due.** Wait: the undone rows' keys are not in `check_next` → `self.check_next.get(key, 0) > self.clock()` → 0 > now → False → they're not skipped by that. But the EARLY RETURN at :490-491: `if seen is not None and seen == getattr(self, "_check_seen", None) and self.clock() < due: return 0`. `due` = min over check_next.values() — if ANY key has a check_next in the future (e.g. a row answered-fully? no, those are removed... a row that got a partial answer has check_next = now+600), then due = that future time → the early return fires → the undone rows wait until that check_next expires (up to 600 s) OR the ledger changes. **P2: `check_once`'s early-return (service.py:490-491) can starve newly-eligible rows for up to CHECK_RETRY_S (600 s) when another row's retry is pending, because `_check_seen` is updated even when the todo list was truncated (the truncation at :514 makes the `len(todo) <= room` condition at :512 always true).** Actually wait — re-read: the condition at :512 is `if len(todo) <= CHECK_INFLIGHT - len(self.check_inflight)`. At that point, `todo` is the FULL todo list (before truncation). Then :514 truncates. So the condition tests the FULL list against the room. If the full todo ≤ room, everything is started → `_check_seen` updated ✔. If the full todo > room, the condition is False → `_check_seen` NOT updated → the next loop re-reads ✔. I misread the order. :512 comes BEFORE :514. ✔. No finding. Good.

**C69. `service.py:517` — `started = [self.checks.submit(self.check_row, l, flags, miners[l["video_id"]]) for _, _, l, flags in todo]`.** `miners[l["video_id"]]` — KeyError if the video_id isn't in miners? `miners` is built from the SAME lines (service.py:495-499) → every todo line's video_id is there ✔.

**C70. `service.py:453` — `self._append(v, [new])` — ONE line per check.** Each check_row appends a new line. For a moment with 2 flags, TWO appends (one per... no: `got` collects ALL flags answered in THIS check_row call, then ONE append with both). ✔. But: two CONCURRENT check_rows for the SAME moment? `check_inflight` guards by key (service.py:504, 516) → one at a time ✔. But: a check_row's append vs a mine pass's append for the same video — both under `wlock` ✔, and `carry_forward` merges ✔.

**C71. `providers.py:373-374` — `Reply(content, j.get("model") or self.model, j.get("provider"), ...)` — `j.get("provider")`** is the GATEWAY's provider field (OpenRouter-style). Stored as `provider` in the ledger's `mined.provider` ✔ (the design: "mined.provider").

**C72. `providers.py:421` — `Reply(text, resp.model, self.cfg.get("vendor"), ...)`** — for Anthropic, `provider` = the CONFIG's vendor (a string), not an object. `queue.call` (queue.py:229) does `str(rec.get("provider"))` → "anthropic". ✔.

**C73. `ab.py:287-289` — the judge selection: `router.backends[j].model not in gen_models`.** If the judge's model EQUALS a generator's model (e.g. both heimdall_qwen27b), it's skipped ✔. But: `gen_models` is a SET of models — if two GENERATORS share a model, that's fine. If the judge's model happens to equal a generator's, excluded ✔ (the design: "a model of another vendor than every generator" — actually the design says another VENDOR; the code checks MODEL. A different vendor with the same model name (e.g. two gateways serving qwen) would be excluded. Stricter than the design. ✔).

**C74. `ab.py:294` — `rng = random.Random(20261112)`** — a FIXED seed, so the X/Y shuffle is the same on every run. The design says "sides shuffled" — deterministic shuffling is fine for reproducibility, but it means the SAME side assignment every run (no variance). For a blind judge, that's acceptable (the judge doesn't know the seed's meaning). ✔.

**C75. `ab.py:312-313` — `p = JUDGE_PROMPT.format(rows=rows, x=_fmt(results[X][vid]["lines"]), y=...)`.** `_fmt` (ab.py:211-214) uses `l['flags_ext']['about_bitcoin']` — a KeyError if a line lacks flags_ext. But the lines come from `mine.mine_video` → `build_line` → always has flags_ext ✔.

**C76. `ab.py:346-348` — `hits = [recall_hit(res[v["video_id"]]["lines"], v["approved"]) for v in vids if ...]`** — `res[v["video_id"]]` — KeyError if the video wasn't mined (budget reached)? The guard `v["video_id"] in res` ✔ (it's in the comprehension's condition).

**C77. `purge.py:165` — `pins = {m.group(1) for m in (SCORER.match(os.path.basename(p)) for p in glob.glob(d["scorer_results"])) if m}`.** `glob.glob` returns paths; `SCORER` = `^delivered_([0-9a-f]{8})_` — the PIN HASH, not the video id. Then :184: `why = [f"pin {p} ..." for p in sorted(pins) if p in joined]` — the pin hash must appear in the run's records. ✔.

**C78. `purge.py:322` — `files = [p for p in glob.glob(os.path.join(unit, t["files"])) if os.path.splitext(p)[1].lower() in exts]`.** For `word_pass_temp`, `files: "*"` → ALL files, filtered by extension. A directory inside `/tmp/word_pass_*/` (e.g. a subdir) → `glob` returns it, `splitext` of a dir → its extension (often "") → not in exts → skipped ✔. But: a FILE with no extension (e.g. a lock file) → skipped ✔ (the design: "audio and window WAVs").

**C79. `purge.py:363` — `elif newest > abandoned_after`** — for mode "abandoned", if the unit's newest mtime is AFTER the cutoff (12 h ago), keep. So a unit touched 11 h ago keeps ALL its files, even a 20-h-old file inside. ✔ (the design: "a directory nobody touched for 12 h"). But: `newest` is the unit's NEWEST — one recent file keeps everything. For `/tmp/word_pass_*` (per-cycle dirs), each dir is one cycle ✔.

**C80. `purge.py:375` — `rep.setdefault("would_delete", []).append(...)`** — only in dry_run. `cmd_purge` (tools/ingest_watch.py:193) reads it ✔.

**C81. `queue.py:177` — `ORDER BY COALESCE(published_ts, listing_ts, discovered_ts) DESC`.** The design (section 12): "MINING ORDER: newest uploads first, always (Queue.due orders by publish time, newest first, for both the caption fetch and the mining)". ✔ — but `published_ts` is only set AFTER a successful probe (fetch.py:155). A DISCOVERED video (not yet probed) has published_ts NULL → falls to listing_ts (the RSS/playlist ts) → then discovered_ts. So the FETCH order uses the listing time (a good publish proxy) ✔. The MINE order: only TRANSCRIBED+ videos, which HAVE published_ts ✔.

**C82. `coverage.py:73` — `is_short = state == Q.SHORT or "/shorts/" in (e.get("url") or "")`.** For an RSS-listed video, `e["url"]` is the watch URL (watch.py:117: `link.get("href")`) — `https://www.youtube.com/watch?v=...` — NO "/shorts/". So an RSS-listed Short is detected only via the queue's state (SHORT, set by the probe) ✔. For a playlist-listed Short, the URL IS /shorts/ (yt-dlp) → detected early ✔. But: a Short listed via RSS, not yet probed, published 1 h ago → `state` is DISCOVERED, url has no /shorts/ → counted as ELIGIBLE (not a short) → it counts against coverage until probed. Then it becomes SHORT. The report for THAT day: the video was counted eligible+missed. Next day's report: it's a Short. The design: "Shorts reported separately: never mined by policy" — a same-day report before the probe miscounts. Minor: the probe happens within ~10 min. P3.

**C83. `watch.py:191-192` — `upd.update(etag=headers.get("ETag") or row.get("etag"), ...)`.** If the RSS response has NO ETag (YouTube's "return none" per the design), the OLD etag is kept ✔. But: a 200 response WITHOUT validators → the old etag is reused on the next poll → a 304 → "not_modified" → entries = [] → no new videos. If the channel published something between, it's missed until the etag changes. The design: "conditional headers are sent when a feed returns validators; YouTube's return none" — so for YouTube, no etag → no conditional → always a 200 with full entries ✔. The `or row.get("etag")` keeps a STALE etag from... where would a stale one come from? Only if a PREVIOUS response had one. If YouTube never returns one, row.get("etag") is always None ✔.

**C84. `watch.py:226` — `listed=(row["listed"] or 0) + len(entries)`.** For a 304 (entries=[]), listed += 0 ✔. But `newest` (watch.py:211, 221-223): for a 304, entries=[] → newest unchanged ✔.

**C85. `fetch.py:139` — `final = tries + 1 >= UNAVAILABLE_MAX_TRIES`; `next_at=now_ts + (10**9 if final else UNAVAILABLE_RETRY_S)`.** So an unavailable video is retried 4 times over 24 h, then parked. But `UNAVAILABLE` is in `FETCH_DUE` (queue.py:24) — a parked one has next_at = now+1e9 ≈ year 2038 (epoch+1e9 = ~2001+31y... now(~1.77e9)+1e9 = 2.77e9 → year 2057). Effectively never. ✔. But: the state UNAVAILABLE is in FETCH_DUE, so a parked video is "due" again in 2057 — harmless.

**C86. `fetch.py:162` — `nxt = max(float(start) + 900, now_ts + 600) if isinstance(start, (int, float)) else now_ts + config.UPCOMING_REPROBE_S`.** If the scheduled start is in the past (a missed premiere), `start+900` could be < now+600 → nxt = now+600 ✔. If the start is 2 h away → nxt = start+900 (15 min after) ✔. But: `tries=tries+1` — an upcoming video accrues tries; when it finally goes live, `tries` is large → `_retry_at` (fetch.py:110-111) clamps at the last PROBE_RETRY_S. ✔.

**C87. `mine.py:475` — `report["miners"][out.backend] = report["miners"].get(out.backend, 0) + 1`.** Counts WINDOWS per back-end, not moments. The design's `miners {backend: windows}` ✔.

**C88. `service.py:266-267` — the cost query: `COALESCE(role, 'mine')='mine'`.** Records with role NULL (the probe? no, the probe has role='probe') — the A/B's records have role='mine' ✔. But: the HOOK pass's cost (service.py:372-373) uses `role='hook'` — a hook record with role NULL? No, `router.run(role, ...)` sets it ✔.

**C89. `ledger.py:315-317` — the `latest` dict: `if (mined_at and mined_at >= since) or (pub and pub >= now - timedelta(hours=horizon_h))`.** A line with NEITHER a parseable mined.at NOR a parseable published_at: excluded from `latest` → never returned. But `line_problems` (ledger.py:28-31) requires `published_at` to be a STR (not necessarily parseable) and `mined` to be a dict. A line with `published_at: "garbage"` and `mined.at: "garbage"` → both `_aware` → None → the line is silently dropped from the adapter. Fail...closed? The design: "a line without a measured publish time is refused as before" (section 12) — the expiry check (ledger.py:341) would drop it anyway. But here it's dropped EARLIER (not even counted in `excluded`). The report's `lines` count includes it (it was read), but it's not in `latest` → not in any exclusion bucket. **P3: a line with unparseable mined.at AND published_at vanishes from the adapter's report entirely (not counted as excluded).** Minor.

**C90. `ledger.py:336-338` — the expiry check: `if exp is not None and now >= exp: drop(...)`.** If `exp is None` (neither expires_at nor published_at+12h parseable), the moment is NOT dropped for expiry — but the NEXT check (`elif pub is None or pub > now` at :341) catches pub=None. If pub is parseable but expires_at is not: `expiry()` (ledger.py:284-286) computes `config.aware(config.expires_at(l.get("published_at")))` — from pub, so exp is not None. If pub is parseable, exp is always not-None. If pub is NOT parseable: exp = the recorded expires_at only; if that's also not parseable → exp None → falls to :341 → pub None → dropped ✔. Consistent.

**C91. `mine.py:481` — `if rank_score({"scores": cand["scores"]}) > rank_score({"scores": prev["scores"]})`.** Constructs a fake line dict just to call rank_score — works (rank_score reads `line["scores"]` and `line.get("risk")` → the fake has no "risk" → `.get` → None → `sum(... for r in None or [])` → 0 penalty). But `prev` HAS a risk (possibly) — so the comparison is scores-only, ignoring the risk penalty. The comment says "scores and reason those of the better-ranked observation" — the RANK here ignores risk. Minor inconsistency: the final sort (ledger.py:368) DOES include the risk penalty. So the "better" observation chosen by scores-only might rank LOWER overall. P3.

**C92. `service.py:293` — `since = datetime.fromtimestamp(float(v.get("discovered_ts") or self.clock()) - 86400, timezone.utc)`.** If `discovered_ts` is 0 (falsy), `self.clock()` is used — a video discovered at epoch 0 is impossible. ✔.

**C93. `downsignal.py:117` — `self.state_path = state_path or self.hh.STATE`.** If `state_path` is given (tests), the module's OWN STATE constant is ignored — but the module's functions take `path=self.state_path` (downsignal.py:187) ✔. And `_seen` (downsignal.py:264) reads `self.state_path` ✔. Consistent.

**C94. `downsignal.py:187` — `out = getattr(self.hh, fn)(*a, path=self.state_path, **kw)`.** For `note(False, now=..., evidence=..., who=...)`: positional `False` → the module's `note(answered, path=STATE, now=None, evidence=None, who="")`? The builder's signature (from the diff context, `mode(path=STATE, now=None, evidence=None, state_md=None, who="")`) — `note` presumably similar. `*a` = (False,) → answered=False ✔; `path=` kw ✔. But: if the module's `note` does NOT accept `evidence` or `who` (an older version), TypeError → caught by `_call` → "not read". The `load_module` check (downsignal.py:55) only checks EXISTENCE, not signatures. The change's question 3 asks exactly this. For `probe_due`, the signature IS checked. For `note`/`mode`/`probe_result`, it is NOT — but the builder's message says they're unchanged, and the pre-existing code already passed `who` to them (downsignal.py:200, 206, 247) — so they've been tested against 125e7381. ✔. But: **the `evidence` kwarg** — passed to `note`/`mode`/`probe_result` (downsignal.py:200, 206, 160, 247). If 125e7381's `note` lacks `evidence`... the watcher went live at 02:27 ET against 125e7381 (the change note says so) and it works (2 cycles audited). ✔.

**C95. `spend.py:23` — `SWITCH_PATTERN = r"\d\d:\d\d ET: (?:SWITCHED TO PLAN B|BACK TO [A-Z0-9_-]+-FIRST)"`.** The head (downsignal.py:83-85) produces "SWITCHED TO PLAN B" or "BACK TO " + up.upper().replace("_","-") — e.g. up = "all_clear" → "BACK TO ALL-CLEAR". The pattern: `BACK TO [A-Z0-9_-]+-FIRST` — requires the up mode to END in "-FIRST"! If the module's up mode is "all_clear" → "ALL-CLEAR" → does NOT match `-FIRST` → the switch line is NOT recognized by NOTICE_RE (spend.py:26-27) → `_rewrite_top`'s head-parsing (spend.py:49-50) stops at it → it's treated as BODY text → the next notice write would... let me trace: `head` collects leading NOTICE_RE-matching lines. If line 1 is "14:00 ET: BACK TO ALL-CLEAR (...) |" and it does NOT match NOTICE_RE, head=[] → the notice is written ABOVE it? `new = "\n".join(block + lines)` where lines = the FULL original (including the switch line) → the notice goes BEFORE the switch line. But the design says the switch line "stays first whatever other notice comes or goes" (spend.py:200-201). **If the up mode's name doesn't end in "-FIRST", the switch line loses its first position.** What IS the module's up mode? Not in the diff. The test `test_every_switch_opens_state_line_1_newest_first_on_one_physical_line` presumably uses the REAL module (or a fixture with a "-FIRST" mode). The builder's MODES: the diff's docstring says "BACK TO <UP MODE>" and the pattern in spend.py:23 was written for it. If the real up mode is e.g. "qwen_first" → "QWEN-FIRST" ✔. Given the test passes (270 collected, and the signal tests reference the real behavior), the up mode likely ends in -FIRST. But the COUPLING between spend.py:23's regex and the module's mode name is INVISIBLE — a module-side rename breaks the invariant silently. **P2: `spend.SWITCH_PATTERN` (spend.py:23) hard-codes that the module's up mode ends in "-FIRST"; a module-side rename of the up mode (e.g. "all_clear") silently breaks "the switch line stays first" (the notice would be written above it).** Also: the head's `word` for the up case is "BACK TO " + up.upper().replace("_", "-") — if the up mode has NO underscore (e.g. "normal"), it's "BACK TO NORMAL" → no "-FIRST" → same bug. Flag it.

**C96. `downsignal.py:96` — `" ".join(text.upper().split())`** — collapses whitespace and uppercases. The SWITCH_RE (spend.py:24) anchors `^` — the head starts with "HH:MM ET: " ✔. But: the WHY text (from the module, uppercased) could contain "ET: SWITCHED TO PLAN B" — no, SWITCH_RE matches only at the START. ✔. But: the why could contain a NEWLINE → `.split()` collapses ✔.

**C97. `service.py:193` — `self.cycle = "ingest-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")`.** Uses the REAL clock, not `self.clock` — a test-injection inconsistency (the tests presumably don't check the cycle format). P3.

**C98. `config.py:56` — `datetime.fromisoformat(str(s).replace("Z", "+00:00"))`** — Python 3.10's fromisoformat does NOT parse all ISO 8601 (e.g. "2026-11-14T02:27:00.123456789Z" — 9 fractional digits — fails; also "20261114T022700Z" compact). YouTube's RSS published: "2026-11-14T07:00:00+00:00" ✔. yt-dlp's: from `_dt(epoch).isoformat()` ✔. The ledger's: `config.iso()` ✔. But: a THIRD-PARTY published_at in the main store's meta.json (the purge's publish_time, purge.py:214-216) — if it's "2026-11-14 07:00:00+00:00" (space separator), 3.10's fromisoformat DOES accept a space? Actually 3.11+ accepts more; 3.10 accepts `YYYY-MM-DD[T| ]HH:MM:SS[.ffffff][+HH:MM]` — a space IS accepted in 3.10? Testing from memory: 3.10's fromisoformat accepts the space separator (it was 3.11 that added more, but the space was always... actually no: 3.10's docs say it accepts "the format emitted by isoformat()", which uses 'T' by default but `isoformat(sep=' ')` is also valid and 3.10's parser accepts any SINGLE character separator? The 3.10 docs: "the exact format is flexible: it accepts... any single character as the separator" — I believe 3.10 accepts one-char separators. Fractional digits: 3.10 accepts exactly 3 or 6. A 9-digit fraction fails. The purge's `_latest`/`aware` would return None → "publish time not measured" → the file is KEPT ✔ fail closed. P3.

**C99. `queue.py:92` — `CREATE INDEX IF NOT EXISTS videos_hook ON videos(state, published_ts)`** — runs EVERY Queue() construction (a write on a read-only? No, IF NOT EXISTS → a no-op after the first). But: `cmd_status` (tools/ingest_watch.py:69) constructs a Queue → the index DDL runs → a WRITE to the DB while the service holds it. SQLite WAL: concurrent writers are serialized; the DDL is a no-op (the index exists) → still a write transaction? `CREATE INDEX IF NOT EXISTS` when it exists: SQLite short-circuits, no write. ✔.

**C100. `tools/ingest_watch.py:142` — `os.link(tmp, dst)`** — hardlink; fails if dst exists (EXISTS) → the finally unlinks tmp ✔. But: `shutil.copyfile(src, tmp)` then `os.link(tmp, dst)` — the LINK means the main store's file shares an inode with... no, tmp is unlinked, dst is the only link. But the COPY: if the staging file changes later, the main's copy is the OLD inode ✔ (write-once). ✔. But: `os.link` across filesystems (staging and main on different mounts) → EXDEV → the finally unlinks tmp, the error propagates → the remaining plan entries are skipped. The design says the integrator runs it; a cross-fs deployment would fail. P3.

---

## SECTION 2: LAW COMPLIANCE

- **BUILD (continuous ingest, RSS first, ~10 min, ETag, backoff, last-seen, duplicate detection, Shorts/live handled, durable queue; captions via the store's writer into a staging copy; mining by sentence ids on Heimdall, bounded concurrency, 429/503 backoff, ≤~20 in flight, spend vs $460 with a 90% NOTIFY tripwire; append-only pp.moment/1 ledger + adapter; daily coverage; blind A/B):** **COMPLIANT.** RSS-first with a canary (watch.py:88-118, 230-238; service.py:194-197); 600 s ±60 (config.py:25-26; service.py:683); ETag/Last-Modified (watch.py:191-192); per-channel backoff (watch.py:205-208); the last-seen ledger IS the channels table (queue.py:29-33); duplicate by title+duration and text fingerprint (fetch.py:186-191, 241-247; queue.py:203-219); Shorts (fetch.py:157-159) and live (fetch.py:165-168) explicit; SQLite WAL (queue.py:83); captions via `ts.fetch_captions`/`_store`/`_log_attempt` (fetch.py:226-237); sentence ids by import (contract.py:51-76); bounded: per-backend sem + global 20 (providers.py:706-708); 429/503 throttle (providers.py:636-663, 862-863); spend meter vs $460 at 90% NOTIFY (spend.py:97-98, 129-133; providers.json:114); the ledger (ledger.py:34-66) and the adapter (ledger.py:289-370); coverage (coverage.py:43-95); the A/B (ab.py). One caveat: the A/B's judge is entirely frozen (providers.json:6,104) → "no judge" (ab.py:290-291) — the design (section 8) acknowledges this (REQUESTS R9). PARTIAL only in that the blind verdict is currently unmeasurable — but that's the freeze's consequence, documented, not a violation.

- **L-x NO SINGLE MODEL, ULTRON FIRST:** **COMPLIANT.** One Router (providers.py:694); every role ≥2 back-ends enforced (providers.py:140-142); vendors/models only in providers.json (the note; `test_no_vendor_or_model_name_outside_the_provider_config`); the local model first in the mine chain (providers.json:102) but disabled until the A/B (providers.json:13) — "the local model is the default where it meets the bar" (it doesn't yet, documented); the run continues when one vendor is down (the chain + AllBackendsFailed.outage, providers.py:60-68). Note: under the freeze, the mine role's EFFECTIVE callable count is 1 (Heimdall) — the warning fires (service.py:676-679) and the design documents it. The LAW says "≥2 interchangeable back-ends" — the CONFIG has 2; one is disabled. PARTIAL? The law's intent (no single point of failure) is currently violated in practice: Heimdall down = nothing mines (the videos wait, by the orchestrator's own 05:30 ruling). I'll call it **COMPLIANT-with-documented-exception** — the freeze is the orchestrator's order, which supersedes. Also: `flagcheck`'s two back-ends are BOTH Heimdall (providers.json:107) — one VENDOR, two back-ends. The law says "≥2 interchangeable back-ends", not vendors. ✔. But the "run continues when any one vendor is down" — if Heimdall (the only unfrozen vendor) is down, NOTHING runs. That's the freeze's effect, and the Plan B (queue and wait) is the orchestrator's. **PARTIAL** (by the orchestrator's own order).

- **L-l (a reply counts only whole; nothing repaired; a failed call is never a default):** **COMPLIANT.** Strict validators (mine.py:332-384; flagcheck.py:173-200; ab.py:76-93); the retry-with-reason is a NEW ask, not a repair (providers.py:884-885); a failed window is reported, never defaulted (mine.py:465-466); unmeasured ≠ agreement (flagcheck.py:17-18, 328-330; ledger.py:221-226).

- **L-j / L-m (fail closed; nothing measured is never a pass):** **COMPLIANT.** `aware()` returns None for a naive time (config.py:53-59); the expiry uses the EARLIER of the recorded and computed (ledger.py:280-286); an unreadable optout pauses (watch.py:160-173; fetch.py:213-217); an unmeasured spend is "unmeasured" (spend.py:129-132); an unreadable STATE is never rewritten from nothing (spend.py:38-39, 43-46); the coverage's unmeasured channel (coverage.py:61-63, 94); the signal's unreadable state (downsignal.py:305-313).

- **L-h / L-k (read as spoken; records never rewritten):** **COMPLI