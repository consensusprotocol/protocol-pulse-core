# heimdall_glm (z-ai/glm-5.3-flash, 441.3 s, $0.005, finish stop)

# FORENSIC CODE REVIEW — pp-ingest (ruling 77 fixes + ruling 80 hook pass)

---

## SECTION 1: CORRECTNESS

### 1.1 The hook pass flow, step by step

`hook_once` (service.py:380-396) → `hook_due` (queue.py:177-183) → `hook_video` (service.py:322-378) → `mine.mine_video(kind="hook")` → `_append` → `set_hook`.

**BUG 1 (real, will lose hook rows): `hook_video`'s crash handler discards the `finally`-clause's `hook_inflight.discard` interplay with `hook_once`'s claim — no, that part is fine. The real one:**

**`hook_video` catches `Exception` but the `finally` at service.py:376-378 discards from `hook_inflight` — correct. However `hook_once` (service.py:387-392) adds the video to `hook_inflight` *before* submitting, and if `self.hooks.submit` raises (executor shutdown), the video stays in `hook_inflight` forever.** `submit` only raises after `shutdown()`; in the long-running service this is only at process exit, so it's benign. Minor.

**BUG 2 (real): `hook_due` selects `state IN (MINED, MINED_PARTIAL)` but does not exclude videos whose *moments* are expired relative to hooking — that's by design (HORIZON_S = EXPIRY_H). But it also does not exclude videos where `published_ts` is NULL.** `published_ts >= ?` with NULL evaluates to NULL → not true → excluded. Fine.

**BUG 3 (real, correctness): the hook pass's cost query double-counts.** service.py:347-348:
```python
cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND role='hook'", ...)
```
This sums **all** hook calls ever made for the video, including previous failed passes (retries). After 3 passes, `hook_cost_usd` is the cumulative cost, not the pass's. That's arguably intended ("cost" cumulative), but the moment pass (service.py:241-242) does the same with `COALESCE(role,'mine')='mine'` — cumulative too. Consistent, but the report line `what` (service.py:352-354) prints it as if it were this pass's cost. Cosmetic-to-misleading. Note the moment-pass fix in this diff (service.py:241-242, `COALESCE(role,'mine')='mine'`) is **correct and necessary** — without it the hook pass's calls would have inflated the moment cost. Good catch by the author.

**BUG 4 (real): `mine_video`'s `role` parameter is now dead-ish but still overrides.** mine.py:381-389: `role = role or KINDS[kind]["role"]`. If a caller passes `role="mine"` with `kind="hook"`, the prompt is the hook prompt but the role is `mine` — the reply would be validated as `{"hooks": ...}` against the `mine` role's back-ends. Currently no caller does this (service.py:239, 345 pass neither), so it's latent. But `ab.py:281` calls `mine.mine_video(..., only=b, ...)` without `kind` — fine. Latent trap, not a bug today.

**BUG 5 (real, the most important one): the hook duration filter uses `duration_s`/`duration_estimate_s` computed from token start/end, but for `timing == "segment"` the tokens' `start`/`end` are the *record's interpolated* times — the design says so (§4: "start/end are the record's interpolated times (a locator), duration_s is null and duration_estimate_s is flagged").** In `build_line` (mine.py:351-353, 364-365):
```python
start, end = toks[w0].get("start"), toks[w1].get("end")
...
"duration_s": dur if timing == "word" else None,
"duration_estimate_s": None if timing == "word" else dur,
```
So for segment timing, `duration_estimate_s` = end-start of the span. Then the hook filter (mine.py:430-441):
```python
d = l["duration_s"] if l["duration_s"] is not None else l["duration_estimate_s"]
```
This is the **span's** duration, not the "4 to 14 seconds read aloud" of the hook *as it would be cut*. For segment-timed captions, the last token's `end` is the segment's end, which can overrun the spoken words (a segment often trails). This will systematically push hooks over 14 s and drop them. It's a *measurement* question, not a crash — but the ruling says "4 to 14 seconds" and the code measures something slightly larger. Given the design explicitly calls these times "a locator" and says the packager re-anchors, using them as a hard 4-14 gate is a defensible-but-lossy reading. **Flag as P1: the 4-14 s gate on segment timing will silently drop good hooks whose trailing segment padding exceeds 14 s.** The report counts them in `dropped` (good — at least it's measured, L-m satisfied).

**BUG 6 (real): `carry_forward`'s `about_bitcoin` conjunction vs. the in-pass dedupe's conjunction — inconsistent semantics between passes.** In `mine_video` (mine.py:422-424), within one pass, a range seen twice gets `about_bitcoin = a AND b` (conjunction) — fail-closed. In `carry_forward` (ledger.py:201), across passes: `fx["about_bitcoin"] = bool(fx.get("about_bitcoin") is True and ex.get("about_bitcoin") is True)` — also conjunction. Consistent. And `altcoin`: in-pass `or` (mine.py:424), cross-pass `bool(fx.get("altcoin") is not False or ex.get("altcoin") is not False)` (ledger.py:200). For a hook line, `flags_ext` is always present (build_line:376), so `fx.get("altcoin")` is a bool — the `is not False` dance handles the case where an earlier line lacks `flags_ext` (pre-§5 lines). But: **if the earlier line's `flags_ext` is missing entirely, `ex.get("altcoin")` is None, `None is not False` → True, so `altcoin` becomes True.** That's the *wrong* direction for fail-closed on altcoin (altcoin=True *excludes* the moment at ledger.py:306). A pre-`flags_ext` line (mined before §5) would have its hook-line successor marked altcoin=True and be excluded as "altcoin or not about Bitcoin" even though neither observation said so. Same for `about_bitcoin`: `ex.get("about_bitcoin")` None → `is True` → False → conjunction False → excluded. So **a hook re-observation of a legacy line (no `flags_ext`) is guaranteed to be excluded by the adapter.** In practice all current lines have `flags_ext` (§5 shipped before ruling 80), so this only bites legacy/foreign lines. P2.

**BUG 7 (real, race): `_append`'s read-then-write is only atomic *within this process* (wlock, service.py:269-271).** Two processes (e.g. the watcher and a manual `tools/ingest_watch.py once`) — the flock on service.lock (service.py:104-118) prevents that. But `flagcheck.simulate_adapter` (flagcheck.py:348-358) *rewrites a copy* — no race. And `ledger.append` itself takes an flock (ledger.py:47) — so cross-process appends are serialized at the OS level, but `carry_forward`'s read (service.py:270) happens *before* `append`'s flock is taken. Two processes appending the same moment_id concurrently: each reads the other's absence, both append, both lines lack the other's flags. The adapter takes the latest line — which may be the *earlier-flags* one. Within one service this can't happen (wlock). Across the service and a manual `once`... prevented by service.lock. **OK, actually safe. But note: `mine_once`'s 3 video-threads and `hook_once`'s 2 hook-threads share `self.wlock` — correct, that's the point.** However: `hook_video` and `mine_video` for the *same* video can run concurrently (a video in MINED_PARTIAL is in MINE_DUE *and* MINED_PARTIAL is in hook_due's states). Both call `_append(v, lines)` — serialized by wlock, and `carry_forward` reads the ledger *inside* the lock, so the second one sees the first's lines. **Correct.** Good.

**BUG 8 (real): `hook_once`'s `free` computation races.** service.py:383-385:
```python
with self.hlock:
    free = HOOK_VIDEOS - len(self.hook_inflight)
if free <= 0: return 0
for v in self.q.hook_due(HOOK_HORIZON_S, HOOK_VIDEOS * 2):
    with self.hlock:
        if v["video_id"] in self.hook_inflight or len(self.hook_inflight) >= HOOK_VIDEOS: continue
        self.hook_inflight.add(v["video_id"])
    started.append(self.hooks.submit(self.hook_video, v))
```
The re-check inside the loop's lock makes this correct. But `hook_due` returns up to `HOOK_VIDEOS*2 = 4` rows; if 2 are already inflight (impossible here since free>0 means ≤1 inflight)... fine. **One real issue: if `self.hooks.submit` raises (ThreadPoolExecutor at max? No — `submit` queues, it doesn't reject until shutdown), the video stays in `hook_inflight`.** Only at shutdown. Benign.

**BUG 9 (real): `hook_video`'s `finally` discards from `hook_inflight` — but if the *submit* succeeded and the function raised before `finally`... it can't, `finally` always runs. OK.**

**BUG 10 (real, the biggest one): `hook_video`'s success path calls `self._append(v, lines)` then `self.q.set_hook(vid, hook_ts=...)`. If the process crashes between the append and the set_hook, the hook rows are in the ledger but `hook_ts` is NULL → `hook_due` returns the video again → the pass re-runs → `carry_forward` merges → duplicate lines in the ledger (the latest wins, by the contract).** The design explicitly blesses this (§7: "a crash between the two re-appends identical lines on restart: readers keep the latest line per moment_id"). **Compliant by design.** But note: the re-run's lines get a *new* `mined.at` (stamp=config.iso at service.py:271), so the ledger grows. Bounded by the 12 h window. Acceptable.

**BUG 11 (real): `mine.py:434` — `d = l["duration_s"] if l["duration_s"] is not None else l["duration_estimate_s"]`.** For `timing == "word"`, `duration_estimate_s` is None and `duration_s` is the value — correct. For segment timing, `duration_s` is None, `duration_estimate_s` is the value — correct. But what if `timing` is neither "word" nor "segment" (a future/foreign record)? Both are None → `d` is None → "duration not measured" → dropped. Fail-closed. Good.

**BUG 12: `stats.py:108-113` — `SUM(hook_ts IS NOT NULL)` in SQLite returns 0/1 per row summed — correct. `SUM(COALESCE(hook_rows,0))` — correct. But the query counts videos in state MINED/MINED_PARTIAL with `published_ts >= h0` — a video mined *after* the 12 h window (published 13 h ago, mined now) is counted in `mined_videos` but its hook pass never runs (hook_due's horizon).** So `hooks_12h.mined_videos` > `hook_pass_done` forever for those. That's the intended semantics ("of the mined videos in the window, how many had their hook pass") — but it will永远 show a residual. Cosmetic.

**BUG 13: `queue.py:87-89` — the HOOK_COLUMNS migration.** `cols` is read *once* (line 84) before the `first_sight` check; the HOOK_COLUMNS loop reuses the same `cols` set. If `first_sight` was just added, it's not in `cols` — but it's not a hook column, so no issue. However: **the migration is not wrapped in a transaction with the schema creation.** `isolation_level=None` (queue.py:77) = autocommit; each `ALTER TABLE` commits immediately. If the process dies mid-migration, some hook columns exist, some don't — but the `if c not in cols` check re-runs on next start and adds the missing ones. **Self-healing. Good.**

**BUG 14: `cmd_hooks` (tools/ingest_watch.py:151-164) — `sum(r['hook_cost_usd'] or 0 for r in rows)` sums *all* rows' cost, including not-yet-run ones (None → 0). Correct. But `done` filters on `hook_ts` truthy — `hook_ts` is a REAL (epoch); a video hooked at epoch 0 would be "not done". Never happens. Fine.**

**BUG 15: `hook_due`'s `COALESCE(hook_next_ts, 0) <= ?` — a video whose hook pass waited (hook_next_ts set) and then succeeded has `hook_next_ts=None` (service.py:363) → COALESCE→0 → always due, but `hook_ts IS NOT NULL` excludes it. Correct.**

**BUG 16 (real, subtle): `service.py:355` — `if failed and tries < HOOK_TRIES:` → wait. Else (no failed, or tries >= HOOK_TRIES): append + mark done. But `tries` counts only *rejected* passes (`+ (1 if rejected else 0)`, service.py:351). A pass with 3 outage-failed windows and 0 rejected: tries stays 0, `failed and 0 < 3` → wait, retry in 10 min. Correct (outage = no try used, matches the moment pass's B2 semantics). A pass with 1 rejected + 2 outage: tries=1... after 3 such, `tries >= 3` → the good windows' hooks are written even though 2 windows are still in outage.** Matches the moment pass's `MINE_CONTENT_PASSES` semantics (service.py:300: `rejected and passes >= MINE_CONTENT_PASSES`). Consistent. But note the moment pass *also* requires `was_partial or (rejected and passes >= ...)` — the hook pass's condition is just `not (failed and tries < HOOK_TRIES)`, i.e. it writes when `not failed` OR `tries >= 3`. If `failed` is all-outage (rejected=0, tries=0) and... `failed and 0<3` → wait. Correct. If failed=[outage] and tries=3 from *previous* rejected passes: writes. Matches. OK.

**BUG 17: `mine.py:134` — `_AXES_TEXT = PROMPT[PROMPT.index("SCORES (integers"):PROMPT.index("\nFLAGS\n")].split("\n", 1)[1].rstrip()`.** This slices the *module-level PROMPT* at import. If PROMPT's wording changes (e.g. "SCORES (integers 0-5" → "SCORES (0-5"), the slice silently yields wrong/empty text — no error. There's a test (`test_the_hook_prompt_states_the_rulings_hook_and_the_moment_prompts_own_flags`) that presumably catches it. Fragile-but-tested. P3.

**BUG 18: `hook_prompt` (mine.py:249-254) does not pass `reason_max`... wait, it does: `reason_max=REASON_MAX`. But HOOK_PROMPT's REMINDER says "1 to {max_s}" where max_s=HOOK_MAX_SENTENCES=3 — and the "WHAT A HOOK IS" section says "1 to {max_s} consecutive whole sentences". Consistent. But the OUTPUT example shows `"count": 1` — fine. However: **HOOK_PROMPT's `{max_h}` appears in "Return at most {max_h} hooks" — and `hook_prompt` passes `max_h=HOOK_MAX=3`. But the ruling says "the 1 to 3 lines" — the prompt says "point to the 1 to {max_h} lines" (line 139-140: "the 1 to\n{max_h} lines"). With max_h=3: "the 1 to 3 lines". Matches the ruling. Good.**

**BUG 19: the hook reply's `count` enum is `list(range(1, max_count+1))` = 1-3 (schema() with max_count=3, mine.py:33-47, called at mine.py:340). The validator checks `1 <= n <= MAX_MOMENT_SENTENCES` where MAX_MOMENT_SENTENCES=3 (the closure's local, mine.py:277). Consistent. But the *schema* sent to the back-end says enum 1-3 while the *validator* would accept... no, the validator also checks 1-3. Consistent. However: **the schema's `count` enum for the hook is 1-3, but the *prompt* says "1 to {max_s}" = 1 to 3 — and the ruling says "1 to 3 lines". But a "line" here = a sentence? The ruling says "the 1 to 3 lines in this window" — and the code treats a line = a sentence-range of 1-3 sentences. Is a "line" a sentence? The ruling's hook definition says "4 to 14 seconds; starts at a sentence start and ends at a sentence end" — so a hook can be 1-3 *sentences* (4-14 s). The prompt's "lines" is ambiguous but the "WHAT A HOOK IS" section clarifies "1 to {max_s} consecutive whole sentences". Defensible.**

**BUG 20 (real): `hook_video` does not check `v["state"]` — `hook_due` filters MINED/MINED_PARTIAL, but between `hook_due` and `hook_video`'s execution, the moment pass could have moved the video... no, MINED is terminal for the moment pass (next_at=10**9). MINED_PARTIAL: the moment pass's retry (next_at = now + 6h) could fire while the hook pass runs. Both call `_append` — serialized by wlock, carry_forward inside the lock. Safe. But: the moment pass's `_settle` calls `self._ledger_count(v)` which reads the ledger — if the hook pass appended between the moment pass's `_append` and `_ledger_count`... both under wlock? `_ledger_count` (service.py:273-277) does NOT take wlock. It calls `ledger.video_moment_ids` → `ledger.read` — a read, no lock. A concurrent hook append (under wlock, but the reader doesn't hold it) could see a partially-written... no: `ledger.append` writes under flock + fsync, and `read` opens the file — on Linux, a reader sees either the old or new content; a *torn* line is possible mid-write? `append` writes the whole blob with `os.write` (ledger.py:58-60) — a single write(2) of <PIPE_BUF... no, regular files: a single write(2) is atomic w.r.t. other writers with O_APPEND, but a *reader* without a lock can read while the write is in progress. In practice, `os.write` of a few KB to a regular file is effectively atomic for readers (the page cache is updated in one go for small writes), and the code already tolerates torn tails (read skips unparseable lines, counts them as bad). **Acceptable; the design says so.**

### 1.2 N+1 / performance

- `hook_video` → `mine.mine_video` → `contract.sentences(rec)` — parses the whole record. Then `build_line` → `contract.fingerprint()` (mine.py:374) — **`fingerprint()` is called once per *line*** (build_line:374). It's memoized (`_FP` global, contract.py:85-103), so it's once per process. Fine.
- `mine_video`'s dedupe loop (mine.py:413-429) — O(n²) in the worst case (each cand vs. by_range dict) — it's a dict lookup, O(1). Fine.
- `ledger.read` in `_append` → `video_lines` → `read(path, from_time=since)` → `offset_before` (bisection) — the design says 16-25 s per 100k lines *before* the bisection; with it, the recent tail. But `_append` is called on every hook pass (every 5 s, up to 2 videos) — each does a full `read` of the tail. With the bisection + 1-day margin, this is the recent tail only. **Acceptable, but note: `hook_video`'s `_append` → `video_lines(since = discovered_ts - 86400)` — for a video discovered 12 h ago, that's a 13-day... no, 1.5-day window. The bisection cutoff is `min(since, now-72h) - 1day` (ledger.py:267) — wait, that's `best_unused_moments`'s cutoff. `video_lines` passes `since` directly to `read(from_time=since)` → `offset_before(path, since)`. For a video discovered 12 h ago, since = 13 days... no: `discovered_ts - 86400` = 12h+1d ago = ~1.5 days ago. The bisection finds the offset at 1.5 days ago — that's most of a 12 h-window ledger. Fine at current scale (201 moments).**

### 1.3 Edge cases

- **Empty ledger + hook pass**: `video_lines` → `read` → FileNotFoundError → ([], []) (ledger.py:157-159). `carry_forward` with empty earlier → no-op. `append` creates the file. Correct.
- **`hook_video` when `meta.json` is missing** (a video mined but meta gone — purge keeps non-media, so it shouldn't happen): `open(...)` raises FileNotFoundError → caught by `except Exception` (service.py:371) → hook_note="hook pass crashed: FileNotFoundError". Retried in 10 min. Forever. **No give-up.** For a video whose meta is permanently gone, the hook pass retries every 10 min until the 12 h horizon expires it from `hook_due`. Bounded. OK.
- **`mine_video` with `max_windows=None` for the hook pass** — all windows. A 6 h VOD: ~hundreds of windows, each a Heimdall call. The ruling says "cheap" — but there's no window cap for the hook pass, and the moment pass also has none. For a 6 h video (VOD_MAX_S=21600), at ~40 sentences/window and ~1 sentence/5 s → ~4300 sentences → ~107 windows → 107 Heimdall calls × 2 (moment + hook) = 214 calls. At 12 in-flight, ~20-30 s each → ~10-15 min per video. With 3 videos mining + 2 hooking concurrently, the 12-slot Heimdall semaphore is the bottleneck. **This is the design's stated cost; the BTC screen (mine.py:230-231) prunes. Acceptable but worth noting: a 6 h VOD published at 09:00 will hog the hook lane (2 videos) for ~15 min, delaying other videos' hooks.** P3.

### 1.4 Silent failures

- `ledger.append`'s `os.write` loop (ledger.py:58-60): if `os.write` returns 0 (theoretically), infinite loop. Practically never. P3.
- `spend.write_purge_notice`'s `_rewrite_top` (spend.py:29-51): if the STATE doc's directory doesn't exist, `open(doc)` raises OSError → caught (line 38-39, `text = ""`), then `open(tmp, "w")` raises → **uncaught** → propagates to `_purge_blocked` → `purge_once` → the purge loop's `except Exception` (service.py:513). The notice is lost, the purge still ran. Fail-open on the *notice* only. Acceptable (the notice is a NOTIFY, not a gate).

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
|---|---|---|
| **L-x** NO SINGLE MODEL, ULTRON FIRST | **COMPLIANT** | Every role ≥2 back-ends: providers.json:80-86 (`mine` 2, `judge` 3, `hook` 2, `flagcheck` 2); `load_config` enforces it (providers.py:125-128). Vendors/models only in providers.json (test: `test_no_vendor_or_model_name_outside_the_provider_config`). Hook role = the mine chain (Heimdall → local) — the ruling says "Heimdall, cheap" ✓. |
| **L-l** reply counts only whole, nothing repaired | **COMPLIANT** | `validator` (mine.py:272-324) raises `Invalid` on any defect; `_try` re-asks with the reason, 3 attempts (providers.py:845-852, 866-867); never repairs. The hook reply: same, parameterised (mine.py:272-277). |
| **L-j / L-m** fail closed; unmeasured ≠ pass | **COMPLIANT** | Hook duration unmeasured → dropped, counted (mine.py:434-438). `flagcheck` unmeasured → "unmeasured" cell, never agreement (flagcheck.py:277-279, 296-302). Purge: unreadable record → problem → nothing deleted (purge.py:118-150, 296-302). Spend unmeasured → "unmeasured" state, never "ok" (spend.py:118-122). |
| **L-h / L-k** read as spoken; records never rewritten | **COMPLIANT** | `E.spoken(toks[w0:w1+1])` (mine.py:362); the store's own writer (fetch.py:226-237); handoff never overwrites (tools:133, `os.link` fails if dst exists). |
| **L-e** word timing | **COMPLIANT (by delegation)** | `timing: "segment"`, `duration_s: null`, `duration_estimate_s` flagged (mine.py:364-365); the packager re-anchors. The hook's 4-14 s gate uses the estimate — a *mining-time* judgement, the packager re-judges. Defensible. |
| **L-u** hard exclusions | **COMPLIANT** | `HARD_RISKS` (mine.py:23-24); the adapter excludes (ledger.py:304-305); the hook row carries the same flags (build_line:368, 376); `carry_forward` unions risk (ledger.py:197) — a hook line never *loses* a hard flag. |
| **L-v** speaker change; re-uploads | **COMPLIANT** | `turn_change_inside` measured (contract.py:129-135); the adapter excludes `True` (ledger.py:308-309); the hook prompt says "a hook never contains one after its first sentence" (mine.py:155-156) — but note: **the hook validator does not *check* turn_change_inside; it's the adapter's exclusion (ledger.py:308) that enforces it.** A hook row spanning a marker IS written, then excluded by the adapter. The question "Can a row... spanning a speaker change be written as a hook?" — **YES, it can be written; the adapter then excludes it.** That's the documented design (the packager requires false; the adapter pre-applies). Not a violation, but the prompt's claim "a hook never contains one" is enforced only post-hoc. |
| **L-q** moments first | **COMPLIANT** | The hook pass runs *after* the moment pass (hook_due: state MINED/MINED_PARTIAL, queue.py:181). |
| **L-r** no GPU | **COMPLIANT** | `local_gemma` enabled:false (providers.json:13); `OllamaLocalBackend.enabled` requires `gpu0.held()` (providers.py:461-465). |
| **Secrets** | **COMPLIANT** | Keyring (providers.py:147-187); `redact` (208-214); `_NoRedirect` (289-294) — the key never follows a redirect; `override_allowed` (135-144) — the base-URL override only to this machine or the configured host. |
| **SPEND FREEZE** | **COMPLIANT** | `frozen()` (providers.py:692-695) — fail-closed when a back-end names no vendor; `available()` (713-722) and `_try` (800-801) both refuse. The hook role's chain is Heimdall → local — no frontier. ✓ |
| **B1** (notify, never halt) | **COMPLIANT** | `Router.order` moves metered back-ends last, never out (providers.py:700-706); `CreditMeter.state` (spend.py:118-122); the notice (spend.py:151-172). |
| **B2** (nothing lost) | **COMPLIANT** | Outage → MINE_WAIT, no try (service.py:316-319); rejected → tries, partial after 3 (service.py:300-311); the hook pass mirrors it (service.py:355-360). |
| **B3** (GPU0 lease) | **COMPLIANT** | `gpu0.held()` is a check, never an acquisition (providers.py:443-445, 461-465); `release()` unloads at idle (service.py:405-407, IDLE_RELEASE_S=120). |
| **B4** (age gate) | **COMPLIANT** | watch.py:24-27, 69; fetch.py:103-104, 133-136 — the age gate is matched first, terminal. |
| **Ruling 76+77** (12 h expiry, purge) | **COMPLIANT** | `expires_at` (config.py:62-65; mine.py:360); the adapter's earlier-of rule (ledger.py:238-244); the purge's fail-closed fixes (see §1.1, purge.py:65-93, 118-150, 226-250, 296-302). |

**One PARTIAL: the ruling-80 requirement "Give the judge's three-part hook definition... in the prompt verbatim: get it from the builder's code".** The code hardcodes `JUDGE_HOOK_QUESTION` as a *string literal* in mine.py:129-133, with a test (`test_the_hook_question_is_the_builders_judge_question_verbatim`) that compares it to the builder's source. That's "verified-identical", not "imported" — if the builder changes their question, the test fails (good, fail-closed) but the code must be hand-edited. The design doc says "a test compares it with the builder's source" — so this is the documented, accepted mechanism. **COMPLIANT as documented, but note it's a copy-verified-by-test, not a single source of truth.** Similarly `_AXES_TEXT`/`_FLAGS_TEXT` (mine.py:134-135) are *sliced* from PROMPT at import — those ARE single-source. Inconsistent approach within the same feature; the axes/flags are derived, the judge question is copied. P3.

---

## SECTION 3: SECURITY

- **SQL injection: none.** All queries are parameterised (queue.py:102-104, 173-175, 181-183, 223-231; stats.py:109-111; tools:155-157). The only f-string SQL is `queue.py:128` (`UPDATE channels SET {cols}`) and `queue.py:189` (`UPDATE videos SET {cols}`) — column names from `**f`/`**kw` validated against `VIDEO_FIELDS`/`HOOK_COLUMNS` (queue.py:155-157, 186-188). Values are bound. **Safe.** `set_hook`'s column names come from `dict(HOOK_COLUMNS)` — a fixed tuple. Safe.
- **Secrets: none hardcoded.** `env_file` path in providers.json:10 (a path, not a secret). Keys read by name/prefix (providers.py:198-200). `__repr__` shows only counts (providers.py:177-178). Error text redacted (providers.py:820-822). ✓
- **Redirect: refused** (providers.py:289-294) — the bearer key never follows one. ✓
- **Override: constrained** (providers.py:135-144) — only 127.0.0.1/localhost/::1 or the configured host+scheme. ✓ But: `override_allowed` compares `u.hostname == c.hostname` — an IPv6 literal in the configured URL (`[::1]`) — `urlsplit().hostname` strips brackets, so `::1` matches the literal `"::1"` in the tuple. ✓. A DNS-rebinding-style override to *another* port on the same host: allowed (port not compared) — the key goes to the same host, different port. Documented ("the configured host"). ✓
- **Unvalidated input to the filesystem**: `purge.run_pass` deletes only paths matching `spec["media_ext"]` under `spec["targets"]`, validated by `load_spec` (purge.py:53-94) — absolute, no `..`, outside FORBIDDEN. `os.path.realpath` + `startswith(unit_real)` (purge.py:343-344). Symlinks never followed (lstat, purge.py:333; islink check, purge.py:320). ✓
- **`/proc` scanning** (purge.py:226-250): read-only, `os.readlink` — no injection. ✓
- **Rate limiting**: the Router's per-backend semaphore + global 20 (providers.py:679-681); the Throttle's shared backoff (609-636); the circuit breaker (542-606). The A/B and flagcheck runs *add* their own in-flight to the live watcher's — both cap at `a.max_inflight` (ab.py:252, flagcheck.py:449) and the help text says "the two together stay under ~20" (ab.py:417-418, flagcheck.py:532-533). **This is a convention, not an enforcement** — nothing stops an operator running the A/B at 20 while the watcher also runs at 20 → 40 in-flight on a shared gateway. The gateway's 429+backoff absorbs it. P3.
- **Prompt injection**: `<sentences>` / `<quote>` blocks with SECURITY notes (mine.py:104-110, 177-183; flagcheck.py:117-124); `_untrusted` escapes `<` → `‹` so the text can't close the block (mine.py:234-237). The channel/title are also escaped (mine.py:244-245, 252-253; flagcheck.py:140-142). **Good, unusually thorough.** One gap: `_q` truncates with `…` (U+2026) — not escaped, but it's outside the text. And `_mmss` output is digits+colons. ✓

---

## SECTION 4: FRONTEND QUALITY

There is no UI in this diff. The "frontend" is the STATE file, `live.json`, the coverage MD, and the CLI reports. Judged as such:

- **STATE notice** (spend.py:151-172, 175-185): the 90% notice, the outage notice, and the purge notice share the top block, each writer replacing only its own lines (spend.py:29-51, `NOTICE_RE` at :22). Tested (`test_the_outage_and_spend_notices_share_the_top_and_each_writer_replaces_only_its_own`). ✓
- **`cmd_hooks`** (tools:151-164): a readable report — count, rows, cost, per-video state. But: **no `--json`** (the other commands have it: `purge --json`, `coverage` prints JSON). For a "tell the builder the moment the first batch is in the ledger" workflow, a machine-readable output would help. P3.
- **`stats.hooks_12h`** (stats.py:108-113): in `live.json` — the orchestrator can see it. ✓
- **Coverage MD** (coverage.py:105-125): the missed table, the unmeasured flag. ✓
- **Empty/error states**: `cmd_hooks` with 0 rows prints "0 mined videos... hook pass done on 0" — correct, not a crash. `flagcheck` with no callable back-end: `SystemExit` with a reason (flagcheck.py:467-468). ✓
- **Hardcoded values**: `COVERAGE_HOUR_UTC = 11` (service.py:43) — 06:00 ET, but ET is EDT half the year; 11:00 UTC = 07:00 EDT. The comment says "06:00 ET" — it's 06:00 EST / 07:00 EDT. Cosmetic. `HOOK_VIDEOS=2`, `HOOK_RETRY_S=600`, `HOOK_TRIES=3` (service.py:49-51) — constants, not config. The ruling says "cheap" — these are reasonable. P3.

**Score: this is not a UI product; as a headless service its "presentation" (STATE, live.json, reports) is disciplined and tested. 88/100.**

---

## SECTION 5: BACKEND QUALITY

- **DB writes**: SQLite, `isolation_level=None` (autocommit), one connection, one RLock (queue.py:77-79). Every write is a single statement — autocommit is correct here; no rollback needed for single statements. `PRAGMA synchronous=FULL` + WAL (queue.py:81-82) — durable. ✓. **But: `Queue.__init__` runs `executescript(SCHEMA)` + migrations on every construction — `cmd_status`, `cmd_hooks`, `cmd_coverage` each open a Queue; if the service holds the DB, WAL allows concurrent readers. ✓.**
- **External calls**: every back-end call has a timeout (providers.json `timeout_s` per back-end; `OpenAICompatBackend._request` passes it, providers.py:318; Anthropic `timeout=self.timeout` :367; Gemini `http_options.timeout` :415). Retry: `transport_retries=3` + the Throttle + the circuit breaker + the role chain. Graceful degradation: `AllBackendsFailed` with `outage` (providers.py:60-68). ✓
- **Loop failure**: `_loop` (service.py:508-517) catches `Exception`, logs, continues. A `BaseException` (KeyboardInterrupt) propagates — the thread dies, the process's `stop.wait` loop (551-552) keeps the others. Hmm: a `BaseException` in a *thread* kills that thread silently (the `except Exception` at :513 doesn't catch it, and there's no `except BaseException` → the thread's `run` raises → the thread dies, the event loop never notices). The `fetch`/`mine` loops' *inner* functions do catch BaseException (service.py:204-208, 252-257) — good. But `_loop` itself: a SystemExit inside `fn()` that's not caught by fn's own handler kills the loop thread. In practice `fn` are the `*_once` methods, which catch broadly. **Latent, low risk.** P3.
- **Memory**: `Health.events` deque(maxlen=50) (providers.py:548) — bounded. `SpendBook.spent` — one key per back-end. `attempts` in ab.py/flagcheck.py — in-memory lists, bounded by the run. `ledger.read` loads the *tail* into memory — bounded by the bisection. `mine_video`'s `done` dict — one Outcome per window. **No leaks.** The `executors` (service.py:85-88) are never shut down until `close()` — 3+20+2 = 25 threads, idle. Fine.
- **Logging**: `_log` (service.py:131-138) — ISO timestamp + message, to stdout *and* a file. Errors: `traceback.format_exc()[-2000:]` into the event (service.py:202, 250, 374). **Good context.** One gap: `_on_attempt` (service.py:140-146) writes the *full* reply content to `replies_log/<day>.jsonl` — for 100k-token judge replies, that's 100 KB/line. At the A/B's scale, fine; at the watcher's, the mine replies are ~2 KB. ✓. But: **`_on_attempt` is called for every attempt including retries — a 3-attempt failure writes 3 lines. Intended ("EVERY attempt, accepted or not", §2). ✓**
- **`close()`** (service.py:120-127): shuts down the executors, releases the router (the local model unloads), releases the flock. But: **`close()` does not wait for in-flight hook/mine futures** — `self.videos.shutdown(wait=True)` does wait. ✓. And `run()`'s final `t.join(timeout=30)` (service.py:554) — a stuck loop thread (e.g. a hung `coverage.check` without a timeout... `rss_list` has timeout=15, `playlist_list` timeout=120) — bounded. ✓

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Genuinely excellent (say so):**
1. **The fail-closed discipline is the best I've seen in a codebase of this size.** Every unmeasured thing is *counted and reported*, never silently treated as a pass: `flagcheck`'s "unmeasured" cell (flagcheck.py:277-279), the coverage report's `unmeasured_channels` (coverage.py:62, 94), the spend meter's `unmeasured` state (spend.py:118-122), the hook's "duration not measured" drop (mine.py:435). This is the L-m law made mechanical, and it's *tested*.
2. **The prompt-injection hygiene** (`_untrusted`, the SECURITY blocks, the evidence-must-be-copied validator at flagcheck.py:164-169) is Bloomberg-grade.
3. **The circuit breaker's "a success that closes the circuit starts a fresh window"** (providers.py:569-575) — the subtlety that the outage's old failures must not re-open a recovered back-end is the kind of thing that takes a production incident to learn. It's *documented in the code*.

**Material gaps:**

1. **No integration test of the hook pass's *cost* semantics.** `hook_cost_usd` is cumulative across passes (see 1.1 BUG 3) — the ruling asks "cost" per the report; the report's `what` line prints the cumulative as if it were the pass's. A test asserting the cumulative-vs-per-pass semantics would pin it. (There IS `test_the_hook_pass_mines_the_12_h_window_newest_first_and_its_rows_carry_earlier_flags` — but nothing on cost.)
2. **The 4-14 s gate on segment timing** (1.1 BUG 5) — the ruling's "4 to 14 seconds" is measured on the *caption segment's* interpolated end, which systematically overruns. A professional would measure the *spoken* duration (the last *word's* end within the segment, or the packager's re-anchored time) or at least record both. The current gate will drop hooks whose *trailing silence/padding* pushes the segment past 14 s — exactly the good ones. **This is the highest-impact correctness issue in the diff.**
3. **No backpressure between the hook lane and the moment lane.** Both share `self.executor` (the window executor, 20 workers) and the Heimdall semaphore (12). A 6 h VOD's hook pass (≈107 windows) will starve the moment lane. A professional would either cap the hook pass's windows (the moment pass has `max_windows` — used only by the A/B) or give the hook lane its own semaphore. The ruling says "cheap" — it is *per-call* cheap, not *per-video* cheap.
4. **`hook_due` has no index.** `hook_due` (queue.py:181-183) filters `state IN (?,?) AND hook_ts IS NULL AND published_ts >= ?` — the existing indexes are `videos_due(state, next_at)` and `videos_channel(channel_id, published_ts)`. At 201 moments / ~50 videos, a full scan is free. At 10k videos, it's a scan per 5 s. Add `CREATE INDEX videos_hook ON videos(state, hook_ts, published_ts)`. P2, not P1 — the scale doesn't demand it yet.
5. **The `role`/`kind` divergence trap** (1.1 BUG 4) — `mine_video(role=..., kind=...)` where `role` wins if given. One argument too many; a professional would derive `role` from `kind` only, or assert they're consistent.

---

## SECTION 7: SCORES

- **Backend logic: 88/100** — the concurrency design (wlock + carry_forward + the flock) is correct and subtle; the 4-14 s segment-timing gate and the cumulative-cost reporting are the deductions.
- **Frontend/UI: 88/100** — headless, but the STATE/live.json/CLI reports are disciplined, tested, and have proper empty/error states. No `--json` on `hooks` is the only gap.
- **Error handling: 92/100** — fail-closed everywhere, every loop catches, every call has a timeout+retry+breaker, every unmeasured thing is counted. The `_loop` BaseException gap and the notice's uncaught OSError are the only cracks.
- **Security: 93/100** — parameterised SQL, redacted keys, no-redirect, constrained overrides, prompt-injection hygiene. The "convention not enforcement" in-flight cap across processes is the only note.
- **Performance: 84/100** — the bisection read, the memoized fingerprint, the bounded deques are all right. The hook lane's uncapped windows on a 6 h VOD and the missing `videos_hook` index are the deductions.
- **Law compliance: 95/100** — every law traced to lines; the only PARTIAL is the judge question being a verified copy rather than an import (documented, tested).
- **World-class gap: 85/100** — the fail-closed discipline and injection hygiene are genuinely world-class; the gaps (segment-timing gate, lane backpressure, cost semantics) are the difference between very good and Bloomberg.
- **OVERALL: 89/100**

---

## SECTION 8: PRIORITY ACTION PLAN

**P0 CRITICAL | Measure the hook's 4-14 s on the spoken span, not the caption segment's interpolated end | mine.py:351-353, 364-365, 430-441 | For `timing == "segment"`, the last token's `end` is the *segment's* end (trailing padding included); the 4-14 s gate will systematically drop good hooks whose segment trails past 14 s — exactly the ones the ruling wants. Either clamp to the last *word's* end, or record both and gate on the spoken one, or (minimum) report the segment-vs-spoken delta in `dropped` so the loss is measured (L-m).**

**P1 HIGH | Make the hook pass's cost semantics explicit: cumulative vs. per-pass | service.py:347-348, 352-354, 362 | `hook_cost_usd` sums every hook call ever (all passes); the log line prints it as this pass's. After 3 passes the number is 3× the pass. Either name it `hook_cost_usd_total` or subtract the prior value; add a test.**

**P1 HIGH | Cap the hook pass's windows (or give the hook lane its own semaphore) | service.py:345, mine.py:381-393 | A 6 h VOD → ~107 hook windows, each a Heimdall call, sharing the 12-slot semaphore with 3 concurrent moment passes. The moment lane starves; the ruling's "cheap" is per-call, not per-video. `mine_video` already has `max_windows` — use it for the hook pass (e.g. 20) or add a hook-specific semaphore.**

**P2 MEDIUM | Add the `videos_hook` index | queue.py:45-48, 181-183 | `hook_due` runs every 5 s filtering `state IN (MINED,MINED_PARTIAL) AND hook_ts IS NULL AND published_ts >= ?`; no index covers it. Free at 50 videos, a scan at 10k. `CREATE INDEX videos_hook ON videos(state, hook_ts, published_ts)`.**

**P2 MEDIUM | Fix `carry_forward`'s legacy-line `flags_ext` handling | ledger.py:199-201 | When the earlier line has no `flags_ext` (pre-§5), `ex.get("altcoin")` is None → `None is not False` → True → the hook line is marked altcoin=True and excluded by the adapter (ledger.py:306); `about_bitcoin` → False → excluded. A legacy line's hook re-observation is guaranteed excluded. Default the missing side to the *other* line's value (or to the "no information" neutral: altcoin=False, about_bitcoin=True only if both say so *and the earlier line has the field*).**

**P2 MEDIUM | Derive `role` from `kind` in `mine_video`; drop or assert the `role` parameter | mine.py:381-389 | `role = role or KINDS[kind]["role"]` lets a caller pass `role="mine", kind="hook"` → the hook prompt validated against the mine role's back-ends. Today no caller does; tomorrow one will. `role = KINDS[kind]["role"]` (ignore the parameter) or `assert role in (None, KINDS[kind]["role"])`.**

**P3 LOW | Add `--json` to `tools/ingest_watch.py hooks` | tools:151-164, 215-217 | The other report commands have it (`purge --json`); the "tell the builder" workflow wants machine-readable output.**

**P3 LOW | Guard `_loop` against BaseException | service.py:508-517 | `except Exception` misses SystemExit/KeyboardInterrupt in the loop thread → the thread dies silently. Add `except BaseException` → set `self.stop` (or log) so the process notices.**

**P3 LOW | Note the EDT/EST drift in `COVERAGE_HOUR_UTC` | service.py:43 | 11:00 UTC is 06:00 EST / 07:00 EDT; the comment says "06:00 ET". Either use `zoneinfo` or fix the comment.**

**P3 LOW | Guard `ledger.append`'s `os.write` against a 0-byte write | ledger.py:58-60 | `while view: n = os.write(fd, view)` — if `os.write` returns 0, infinite loop. Add `if n == 0: raise OSError("short write")`.**

---

## SECTION 9: THE ONE THING

**Measure the hook's 4-14 seconds on the spoken words, not the caption segment's interpolated end — right now the gate (mine.py:430-441) uses the segment's trailing padding, so it will silently discard exactly the good hooks the ruling 80 pass was built to find, and you'll only discover it because `dropped` counts them.**

---

## SECTION 10: FINAL VERDICT

This is production-ready *now* for the current scale, and the fail-closed discipline, prompt-injection hygiene, and concurrency design (wlock + carry_forward + flock) are genuinely better than what most teams ship. Before the hook pass is trusted to feed the builder, fix the 4-14 s segment-timing measurement (P0 — it will drop the very rows the ruling wants) and make the hook cost semantics explicit (P1), because both silently distort the numbers the orchestrator will read. Everything else is polish on an already-disciplined foundation.