# heimdall_glm (z-ai/glm-5.3-flash, 363.5 s, $0.004, finish stop)

# FORENSIC CODE REVIEW — pp-ingest, ruling 76+77 change (expiry + rolling purge)

Scope note: I reviewed the diff (config.py, ledger.py, mine.py, purge.py, purge.json, service.py, stats.py, tools/ingest_watch.py) against the full working-tree files provided. Everything below cites the working-tree line numbers as printed in the package.

---

## SECTION 1: CORRECTNESS

### 1.1 The expiry path (Q3) — the core of ruling 76

The adapter's expiry logic is `ledger.expiry()` (ledger.py:213-219): the EARLIER of the recorded `expires_at` and `published_at + 12h`, computed via `config.expires_at()` (config.py:62-65). The check is `if exp is not None and now >= exp: drop(...)` (ledger.py:269-270).

**Correctness of the "earlier of" rule: verified.** A line mined before the field existed has no `expires_at`; `config.aware(None)` returns None (config.py:53-59), so `expiry()` falls back to `published_at + 12h` alone. A line whose recorded `expires_at` is *later* than publish+12h (e.g. a bug or a future horizon change) is still capped by the recomputed value. A line whose recorded value is *earlier* (a shorter horizon) is honoured. This is genuinely fail-closed and matches A18.

**Boundary semantics: `now >= exp` means a moment expires exactly at publish+12h, i.e. it is usable for exactly 12h.** The ruling says "usable only within 12 h of its video's publish time, then never again" — inclusive-at-12h-exactly is the defensible reading. Fine.

**Edge: a line with no measured publish time.** `expiry()` returns None when neither term is measurable (ledger.py:217-219). Then the expiry branch is skipped — but the *next* branch catches it: `elif pub is None or pub > now: drop("publish time not measured or in the future")` (ledger.py:273). So an undated line can never leak through the expiry gate. Good — this is the "refused as before" the docstring promises (ledger.py:216-217), and it holds.

**Edge: a re-mined row.** `latest[l["moment_id"]] = l` (ledger.py:250) keeps the *last* line in file order. Since the service stamps `mined.at` under the append lock (ledger.py:49-52, service.py:270/280), the latest line wins. Each new line carries a fresh `expires_at` computed from the *same* `meta.get("published_at")` (mine.py:258) — the publish time never changes between passes (meta.json is write-once, fetch.py:212-217, 235-240), so a re-mined row cannot extend its life. **Verified: no path returns a moment past publish+12h.**

**One subtle asymmetry worth flagging (not a bug):** the *inclusion* filter (ledger.py:248-250) admits a line if `mined_at >= since` OR `pub >= now - horizon_h`. With the default `horizon_h=12` (ledger.py:223), a video published 11h59m ago whose mining is *delayed* past the 12h mark (e.g. a long outage) will be included (its pub is inside the horizon) but then immediately dropped as expired. That's correct behavior, just wasteful — the row is read, counted in `report["lines"]`, and dropped. No correctness issue.

**`since` interaction:** the cutoff for the bounded read is `min(since, now - horizon) - 1 day` (ledger.py:242). Because the expiry filter now runs *after* the read, and the read's margin (1 day) exceeds the maximum out-of-orderness of `mined.at` (one mining pass, per the comment at ledger.py:124-128), a line cannot be missed by the bisection and then expire silently. The expiry check itself does not depend on `mined.at` ordering (it uses `published_at`), so even a line read slightly out of order is judged correctly. **No leak.**

### 1.2 The purge (Q1, Q2)

**Target containment.** Files are enumerated as `glob(os.path.join(unit, t["files"]))` (purge.py:277) where `unit` comes from `glob(t["units"])` (purge.py:274). After enumeration, each file is re-verified: `rp = os.path.realpath(p)`; deleted only if `rp.startswith(unit_real) and not rp.startswith(protect) and not any(b in rp for b in FORBIDDEN)` (purge.py:295-297). Because `unit_real` is the realpath of the *matched* unit, a symlinked *file* inside the unit resolves via realpath — note `os.path.realpath` follows the final symlink too, so a symlink `sources/abc.mp4 -> /elsewhere/x.mp4` yields `rp = /elsewhere/x.mp4`, which will fail `rp.startswith(unit_real)` and be *kept* with reason "outside its unit". That's fail-closed (keep), consistent with the docstring "a symlink is never followed or deleted" (purge.py:12). But note the *st* check: `os.lstat(p)` + `stat.S_ISREG` (purge.py:288-293) — a symlink fails `S_ISREG` (lstat gives the link's mode, S_IFLNK), so symlinks are actually caught earlier at purge.py:292-294 and counted as "not a regular file". Either way: kept. **Correct.**

**Can it delete a delivered video's source?** The delivered set is built by `delivered()` (purge.py:134-172): markers (TELEGRAM_DELIVERY.json/.lock, REVIEW_DROP.json) at purge.py:153, the pin-scorer fallback at purge.py:154-165, references with delivery markers at purge.py:169-171. For every delivered run/reference, `unit_videos()` (purge.py:103-131) collects ids from `sources/`, `transcripts/`, `run/sources/` *listings* plus the JSON records. Then the deletion loop checks `if vid in vids_delivered: keep(...)` (purge.py:305-307) *before* the expiry check. **A delivered video's media is kept regardless of age — verified.**

**Gap in the delivered set (real, but bounded):** `unit_videos` reads records with `except (OSError, ValueError): continue` (purge.py:118-121, 129-130). A *corrupt* (unparseable) `edl.json` in a delivered run is silently skipped — the videos it names are not added to the delivered set, and their sources in *other* runs' `sources/` (or in lock_precheck) can then be purged. However: the video's own `sources/`-listing ids (purge.py:108-113) still protect the copies inside the delivered run itself, and PROVENANCE.json's sources (purge.py:122-130) usually name the same videos. So the exposure is: a delivered video whose id appears *only* in a corrupt record, whose media also sits in a *second, non-delivered* unit. Narrow, but it is a silent (not fail-closed) degradation — the pass does not report the unreadable record. Contrast: `delivered()` *does* fail closed on unreadable run_records when the pin path is taken (purge.py:162-163 appends to `problems`), but `unit_videos`'s record reads do not. **Inconsistent failure policy; P2.**

**Publish-time lookup.** `published()` (purge.py:175-191) tries the queue, then the main store's meta.json, else None → "publish time not measured" → keep (purge.py:309-311). Fail-closed. Note the queue's `published_at` for a livestream VOD is the *stream start* (fetch.py:33-34) — consistent with the ledger's `published_at` (same source), so purge and expiry agree on the clock. Good.

**Race with a render.** Two guards: unit-level `newest_mtime` (purge.py:215-223) vs `busy_after` (2h grace, purge.py:318-320), and the `/proc` open-file check (purge.py:321-323). The 2h grace is the primary defense; the /proc check is a snapshot and inherently racy (a process can open the file *after* the scan, before `os.unlink`). On Linux, unlinking an open file is safe (the fd keeps the inode); the render would lose its source mid-read only if it opens *after* unlink — but then the 2h grace almost certainly covers it. Acceptable; the design leans on the grace period, correctly.

**`newest_mtime` failure → treated as in-use** (purge.py:283-285): fail-closed, keep. Good.

**`os.walk` in `newest_mtime` does not follow symlinked dirs** (default `followlinks=False`, purge.py:217) — a symlinked subdirectory's *target* mtime is not scanned, so a unit whose only recent activity is behind a symlinked dir could be judged idle. But the *files* considered for deletion are only direct `sources/*` children (purge.py:277), and a symlinked *file* is never deleted (S_ISREG fails). So the exposure is: a unit whose real activity is in a symlinked dir, whose direct regular files are then deleted while the render writes through the symlink. Extremely narrow; the 2h grace covers the common case. **P3.**

**Malformed purge.json.** `load_spec` (purge.py:53-79) validates schema, expiry_h equality with `config.EXPIRY_H` (purge.py:59-60 — nice: the ledger's expiry and the purge's horizon cannot drift), positive every_s/active_grace_s, extension shape, target mode, absolute+non-`..`+non-protected paths, and the presence of all seven `delivered.*` keys. On failure, `Service.__init__` catches (OSError, ValueError) (service.py:89-92) and `purge_once` logs "not run, its spec is refused" every pass (service.py:349-351) — **nothing deleted, loudly. Fail-closed, verified.** Note `SpecError` subclasses ValueError (purge.py:49-50), so the catch in service.py:91 covers it.

**One real spec-validation gap:** `load_spec` does not check that `spec["targets"]` is a *list* (it iterates `spec.get("targets") or []`, purge.py:68 — a dict would iterate keys and then `t.get` would crash on a str... actually `for t in "abc"` gives strings, `t.get` → AttributeError, which is *not* caught by service.py:91's `(OSError, ValueError)`). Similarly `spec["media_ext"]` items are validated but `spec["delivered"]`'s *values* (e.g. `markers` not a list) are not: `for m in d["markers"]` (purge.py:153) with a string would iterate characters; `os.path.lexists(os.path.join(run, "T"))` — harmless but wrong. And `d["runs"]` not a string → `glob.glob` raises TypeError, uncaught in `Service.__init__`'s except clause → **the Service constructor itself would crash**. These are config-edit-robustness issues, not production-logic bugs; the shipped purge.json is well-formed. **P3.**

**`run_pass`'s own exception safety:** the `finally` (purge.py:345-348) unlocks and closes. If `delivered()` or anything between raises (e.g. `spec["expiry_h"]` KeyError — impossible, validated; `spec["media_ext"]` KeyError — validated), the lock is released. But note: an unexpected exception mid-pass means **no `passes.jsonl` line** for that pass (the `_append` at purge.py:343 is only on the success path; the refused path at purge.py:256-257 does log). A crash-looping purge would be invisible in passes.jsonl — though the service's `_loop` catches and logs to the event log (service.py:397-399). Acceptable.

**Double-counting in `done` after a failed unlink:** purge.py:329-333 — on OSError, `keep(...)` then `continue`, so `done` is not incremented. Correct. On success, `done["files"] += 1` (purge.py:339) — but note in *dry_run* mode, `done` is incremented too (purge.py:324-340: the `if dry_run` branch appends to would_delete, then falls through to `done["files"] += 1`). So a dry-run report's `deleted` counts *would-be* deletions. That's intentional and matches `summary`'s "would free" (purge.py:378). Fine.

**`published()` cache is per-pass** (purge.py:263, 190-191) — no staleness across passes. Good.

**`_vid_of`** (purge.py:82-84): `name.split(".")[0]` — a file named `abc123XYZ_9.mp4` → id; `abc123XYZ_9.1.mp4` → `abc123XYZ_9`... wait, `split(".")[0]` of `abc123XYZ_9.1.mp4` is `abc123XYZ_9` (11 chars, matches) — good, section-numbered files work. A file like `transcript.abc123XYZ_9.json` → `transcript` (10 chars, no match) → kept as "no video id" — but transcripts aren't in `sources/` targets anyway. Fine.

**Q1 answer: no, the purge cannot delete a delivered source, provenance record, transcript, pin, or render** — provenance/pins/transcripts are non-media extensions (not in `media_ext`, purge.json:7 — `.json` absent) or outside targets; renders are in `out/`/`qa/`/`VERIFY/` which are (a) not targets and (b) FORBIDDEN (purge.py:41-42). **Media published under 12h ago: kept** by `pub > cutoff` (purge.py:312-314). Verified.

### 1.3 The mining order (ruling 77.4)

`Queue.due` (queue.py:164-168): `ORDER BY COALESCE(published_ts, listing_ts, discovered_ts) DESC` — newest first, for both fetch (service.py:202) and mine (service.py:311). Matches the ruling. Note the *word-pass worker's* tiers ("last 6 h, then 6-12 h") are the integrator's; the design says "tell the integrator" — the STATE/assumption A21 covers it. Nothing in this diff implements the worker tiers, correctly.

### 1.4 stats.py purge reporting

stats.py:102-107: reads `purge_last`/`purge_freed_total` from kv. `json.loads(q.kv_get("purge_last") or "null")` — `kv_get` returns the *stored* value; service.py:356-359 stores `json.dumps({...})`, so this round-trips. If the stored JSON were corrupt, the `except ValueError` (stats.py:104-105) → None. But: `float(q.kv_get("purge_freed_total") or 0)` (stats.py:107) — if the stored string were non-numeric, `float()` raises ValueError *outside* the try. It's only written by service.py:354-355 as `str(total)` of a float, so it's always numeric. Fine.

### 1.5 Races

- **Ledger append vs. read:** `append` holds flock (ledger.py:47-63); `read` does not lock (ledger.py:152-179). A reader can see a torn final line — handled: `seal()` on start (service.py:86-87), `append` closes a torn tail before writing (ledger.py:54-56), and readers skip+count unparseable lines (ledger.py:170-173). The pre-verified contract. The expiry change adds no new writer. **No new race.**
- **`_settle`'s read-then-write of `mine_tries`:** service.py:262 reads `v["mine_tries"]` from the row *claimed* at service.py:312; three videos mine concurrently but each row is claimed by exactly one caller (`claim`, queue.py:156-162). No race.
- **`purge_once` vs. the manual `cmd_purge`:** both take the flock on `purge.lock` (purge.py:241-242, 345-348). Serialized. Good.
- **`stats.write_live`** (stats.py:119-126): tmp+`os.replace` — atomic. Good.

### 1.6 N+1 / performance

- `published()` caches per pass (purge.py:263) — the queue lookup `q.video(vid)` (queue.py:125-127) is a PK hit; the meta.json fallback is one file read, cached. For 200+ files this is fine.
- `newest_mtime` walks the *whole unit* (purge.py:215-223) once per unit — a run with thousands of files costs one lstat each, per 10-min pass. With ~170 runs this is ~10⁴-10⁵ lstats/10min. Measurable but not a problem; note it.
- `delivered()` reads up to 4MB × 5 records per *non-marker* run (purge.py:157-159) — only when `pins` is non-empty and no marker. Bounded.
- `best_unused_moments`'s `record_by_sha` (ledger.py:187-202) is only hit on contract drift (ledger.py:289-292) — not an N+1 in the common path.

### 1.7 Edge cases that will break

- **`cmd_purge` with `--apply` while the watcher runs:** flock-serialized (purge.py:241). But `cmd_purge` does *not* take the store's service.lock — it opens its own `Q.Queue(p["queue"])` (tools/ingest_watch.py:155) while the service holds the SQLite connection. WAL + `timeout=30` (queue.py:73) handles it. Fine.
- **`purge_once` when `self.purge_spec` is None but the spec file is *fixed* later:** the spec is loaded once in `__init__` (service.py:89-92) and never re-read. A fixed purge.json requires a restart. Minor, documented behavior ("a refused spec... says so every pass" — but it never *retries* the load). **P3.**
- **Empty ledger / no runs / no /tmp/word_pass_***: all globs return empty; `run_pass` produces a zero report. No crash. Verified by test_purge.py::test_a_dry_run_deletes_nothing.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|---|---|---|
| **L-x** (no single model) | COMPLIANT (unchanged by this diff) | providers.json:80-84; the diff touches no provider code. |
| **L-l** (reply counts only whole) | COMPLIANT (unchanged) | mine.py:177-226; the diff adds no repair. |
| **L-j / L-m** (fail closed; nothing measured is never a pass) | **COMPLIANT** — this is the diff's strongest suit | purge: unreadable delivered set → nothing deleted (purge.py:253-257); /proc unreadable → nothing deleted (purge.py:250-251, 296... actually 250-251 + 253); unknown publish time → keep (purge.py:309-311); unreadable unit mtime → treated in-use (purge.py:283-285). Ledger: undated line → refused (ledger.py:273); expiry = earlier-of (ledger.py:217-219). |
| **L-h / L-k** (read as spoken; records never rewritten) | COMPLIANT | The ledger is append-only; `expires_at` is a *new field on new lines* (mine.py:258), never a rewrite. `config.aware`/`expires_at` (config.py:53-65) don't touch text. |
| **L-e** (word timing at cut) | COMPLIANT (unchanged) | mine.py:262-263: `duration_s` only when `timing == "word"`. |
| **L-u** (hard exclusions) | COMPLIANT — **not weakened** | ledger.py:279-280: the hard-flag drop is unchanged, now *after* the expiry check (order: expired → delivered → undated → optout → unregistered → hard flags → altcoin/about → speaker → re-upload → drift). Every earlier exclusion still fires; expiry only *removes* rows earlier. Q4: no weakening. |
| **L-v** (speaker change; re-uploads) | COMPLIANT | ledger.py:283-286: both checks intact, merely shifted by the expiry/delivered/undated branches. |
| **Ruling 76** (12h expiry, rows kept) | COMPLIANT | Rows are never deleted from the ledger (append-only, ledger.py:34-66; purge never touches the ledger — it's under `protect`/FORBIDDEN `/data/editorial/`, purge.py:41, 296). |
| **Ruling 77.1** (marked expired, a field, with the time) | COMPLIANT | `expires_at` written at mining (mine.py:258) = publish+12h — this *is* "the time". |
| **Ruling 77.2** (delete media >12h, except delivered; keep transcripts/provenance; report freed+kept) | COMPLIANT | purge.py:312-314 (12h), 305-307 (delivered), purge.json:7 (media_ext excludes .json), report: `deleted`/`kept`/`freed_bytes` (purge.py:244, 341) + `summary` (purge.py:372-380) + live.json (stats.py:106-107). |
| **Ruling 77.3** (no cron; watcher's own loop; say how often) | COMPLIANT | service.py:425: `("purge", self.purge_once, float((self.purge_spec or {}).get("every_s", 600)))` — 600s, from the spec, validated positive (purge.py:61-63). |
| **Ruling 77.4** (newest first) | COMPLIANT | queue.py:167. |
| **Secrets** | COMPLIANT (unchanged) | No key material in the diff; purge.json has paths only. |
| **Spend freeze** | COMPLIANT (unchanged) | The purge uses no model. |

**One PARTIAL worth naming:** the ruling says "a moment whose video published_at is more than 12 h old is marked expired (a field, with the time)". The implementation writes `expires_at` = publish+12h, not a boolean "expired" + the *expiry* time. Functionally equivalent and arguably better (a derived "expired" would need a rewrite, violating append-only). I'd call this the correct reading; noting it because a literalist could disagree. Not a violation.

---

## SECTION 3: SECURITY

- **SQL injection:** none. All queue SQL uses parameter binding (queue.py:95-97, 135-140, 153, 160-162, 166-168, 201-209). `channel_update`/`set_state` build column lists from *code-controlled* dicts, with a whitelist check (queue.py:147-150, VIDEO_FIELDS). No f-string SQL with user data.
- **Filesystem:** the purge deletes only paths matched by validated globs (purge.py:68-73: absolute, no `..`, not FORBIDDEN), re-verified by realpath+prefix (purge.py:295-297). `spec["publish_time"]["main_store_meta"].format(video_id=vid)` (purge.py:186) — `vid` comes from `_vid_of` which enforces `^[A-Za-z0-9_-]{11}$` (purge.py:82-84, ledger.py:27), so no path traversal. **Solid.**
- **Secrets:** none in the diff. (The wider code's keyring/redaction, providers.py:147-187, 208-214, is unchanged and sound.)
- **Shell:** none; `os.unlink`/`os.walk`/`glob` only. No `subprocess` in the diff.
- **Symlink handling:** units that are symlinks are skipped (purge.py:275); file symlinks fail S_ISREG (purge.py:292); `newest_mtime` doesn't follow dir symlinks (purge.py:217). Defense in depth. **Good.**
- **Rate limiting / auth:** N/A for this component (no network surface added).

No findings beyond the P3 spec-strictness notes in 1.2.

---

## SECTION 4: FRONTEND QUALITY

No UI in this change. The "reports" are: `purge --measure` stdout (tools/ingest_watch.py:161-164), `summary()` (purge.py:372-380), and `live.json`'s `purge` block (stats.py:106-107). These are operator-facing, consistent with the product's tmux/JSON-ops model. The `summary` line is genuinely good: freed, kept-by-reason, delivered counts, seconds. Nothing to fix.

---

## SECTION 5: BACKEND QUALITY

- **Try/except on writes:** the ledger append is the only durable write in the diff's path, and it's exemplary (flock, torn-tail repair, fsync, all-or-nothing line validation, ledger.py:34-66). Queue writes go through one connection with `synchronous=FULL` (queue.py:78) — correct for the durability claims. `kv_set` in `purge_once` (service.py:354-359) is *not* wrapped: if it raised, the purge would still have happened (deletions logged in deleted.jsonl) but the totals would lag. Given `Queue.x`'s only failure mode is disk/lock, acceptable.
- **External calls:** the purge makes none. The service's other loops are unchanged.
- **Loop failure isolation:** `_loop` catches Exception, logs, continues (service.py:392-401) — a crashing purge loop cannot kill the watcher. But note: a *repeatedly* failing `run_pass` (e.g. /proc unreadable) writes a `passes.jsonl` line each time (purge.py:256-257) — good, the failure is *measured*, not silent. L-m honored.
- **Memory:** `open_paths()` builds a set of every open fd's realpath — on a busy box, 10⁴-10⁵ strings, twice per 10 min. Trivial. `newest_mtime`'s walk is transient. No leak.
- **Logging:** deletions carry path, bytes, target, video_id, published_at, age_h, unit_idle_h (purge.py:334-338) — you can reconstruct exactly what happened. Passes carry kept-reasons (purge.py:244). This is better than most production code I see.
- **One gap:** `purge_once`'s `dry_run` path (service.py:347-363) — the *watcher* always calls it with `dry_run=False` (service.py:425 → `fn()` → `purge_once()`), so the `if not dry_run` guard is only for tests. Fine, but the watcher's purge failures (spec refused) log *every 10 minutes* (service.py:350) — after a week that's 1,008 identical lines. Cosmetic.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Already excellent (say so plainly):** the fail-closed discipline is consistent and *tested* — every uncertainty (unreadable spec, unreadable delivered set, unreadable /proc, unknown publish time, unreadable unit mtime, symlink, non-regular file) resolves to *keep* and is *counted* with a reason. The `expiry_h` equality check between purge.json and config.EXPIRY_H (purge.py:59-60) is the kind of cross-module invariant enforcement that separates senior code from junior. The earlier-of expiry rule (ledger.py:213-219) handles the schema-evolution case (lines mined before the field existed) that almost everyone forgets. The deletion log (purge.py:334-338) is forensic-grade.

**Material gaps, in impact order:**

1. **No purge *coverage* signal.** The report counts what it deleted and why it kept things, but never answers: "of the media that *should* have been deleted, how much *was*?" If `published()` starts returning None for a whole class of videos (e.g. the queue loses its published_at), the purge silently keeps everything and the only signal is a growing "publish time not measured" count buried in `kept`. A professional ops setup would alert on kept-reason *ratios* (e.g. "not measured" > 20% of by_video files for 3 passes). One derived number in `run_pass`'s report + one line in `summary` would close it.

2. **`unit_videos`'s silent record-read failures** (purge.py:118-121, 129-130) vs. `delivered()`'s fail-closed record reads (purge.py:162-163). Same operation, two policies. A corrupt `edl.json` in a delivered run shrinks the delivered set without a trace. Either collect the failures into `problems` (fail closed, consistent) or count them in the report. This is the one place the diff's otherwise-uniform discipline slips.

3. **The spec is loaded once, at startup** (service.py:89-92). Every other tunable in this codebase (overrides.json, providers' base URLs) is hot-reloadable; the purge spec — the thing you'd most likely tune during a disk-pressure incident — needs a restart. A 5-line mtime check in `purge_once` would match the codebase's own precedent (cf. `Overrides`, providers.py:502-529).

4. **Dry-run and real passes are indistinguishable in `passes.jsonl`** beyond the `dry_run` field (purge.py:244) — actually they *are* distinguished; retract. Instead: **`freed_total_bytes` in live.json (stats.py:107) accumulates across spec changes and expiry_h changes** — if you ever bump EXPIRY_H, the "total freed" mixes regimes. Store it as a list of {since, expiry_h, freed} or reset it. Minor, but it's the kind of number someone will eventually quote wrongly.

Nothing else. This is not a component that needs Bloomberg-grade anything; it needs the two consistency fixes above and it's done.

---

## SECTION 7: SCORES

- Backend logic: **93**/100 (the expiry/purge logic is correct; deductions for the unit_videos inconsistency, the once-only spec load, the unvalidated delivered-value *types*)
- Frontend/UI: **N/A** — operator reports only; score the reports: 90 (summary() is genuinely good; no coverage ratio)
- Error handling: **92**/100 (fail-closed everywhere, counted; the slip is unit_videos' silent continue)
- Security: **95**/100 (path traversal impossible, symlinks doubly defended, no injection; only spec-strictness gaps)
- Performance: **88**/100 (newest_mtime's full-unit walk every 10 min; delivered()'s 4MB×5 reads; both bounded, neither matters at this scale)
- Law compliance: **96**/100 (every law and ruling clause answered; the "marked expired" reading is defensible; nothing weakened)
- World-class gap: **85**/100 (missing: kept-reason ratio alerting, hot-reloadable spec, consistent read-failure policy)
- **OVERALL: 91/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P1 HIGH | Make `unit_videos`'s record-read failures visible (collect into the report or into `problems`) | purge.py:118-121, 129-130 | a corrupt edl.json/PIN.json silently shrinks the delivered set and the purge then deletes a delivered video's copy in another unit — the one silent-failure path in an otherwise fail-closed component

P2 MEDIUM | Add a kept-reason *ratio* to the pass report and `summary` (e.g. "not measured: 43% of by_video files") | purge.py:244, 372-380 | the purge's health is currently invisible; a systemic published_at loss looks like "nothing to do" until someone reads kept counts by hand

P2 MEDIUM | Hot-reload purge.json on mtime change in `purge_once`, mirroring `Overrides` | service.py:89-92, 347-351 | during a disk-pressure incident you cannot tune every_s/expiry_h without restarting the watcher — inconsistent with the codebase's own precedent (providers.py:502-529)

P3 LOW | Validate the *types* of `delivered.markers`/`run_records`/`runs` (list-of-str, str) in `load_spec` | purge.py:74-79 | a wrong-typed edit currently fails late (TypeError in Service.__init__, uncaught by the (OSError, ValueError) at service.py:91) or silently (a string markers iterated char-by-char, purge.py:153)

P3 LOW | Catch the spec-load error in `Service.__init__` more broadly, or re-try the load periodically | service.py:89-92 | a TypeError from a malformed spec crashes the Service constructor instead of disabling the purge

P3 LOW | Reset/segment `purge_freed_total` when expiry_h changes | stats.py:107, service.py:354-355 | the cumulative number mixes regimes after any horizon change

P3 LOW | Consider following symlinked directories in `newest_mtime` (or documenting the exclusion) | purge.py:215-223 | a unit whose recent writes are behind a symlinked dir can be judged idle; the 2h grace makes this theoretical

---

## SECTION 9: THE ONE THING

Make `unit_videos`'s silent `except: continue` as loud as everything else in this diff — collect the unreadable delivered-records into the pass report (or into `problems`) — because it is the single path where this otherwise impeccably fail-closed component can, without a trace, delete a delivered video's media.

---

## SECTION 10: FINAL VERDICT

Ready for production. The expiry logic (earlier-of, undated-refused, re-mine-safe) and the purge (targeted, symlink-safe, fail-closed, forensically logged) are both correct against rulings 76+77, and no earlier check — L-u, delivered, opt-out, contract drift, the spend freeze — is weakened; the exclusions merely gained a *preceding* expiry gate. Before merge, fix the one P1 (unit_videos' silent record-read failures) and add the kept-reason ratio; everything else is polish that can land in a follow-up.