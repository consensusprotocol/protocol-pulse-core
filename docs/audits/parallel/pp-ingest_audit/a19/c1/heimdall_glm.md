# heimdall_glm (z-ai/glm-5.3-flash, 412.1 s, $0.006, finish stop)

# FORENSIC CODE REVIEW — pp-ingest (branch pp-ingest, working tree 016965a4)

Review scope: the 16 new files + the A19 purge diff. I verified every claim against the code as printed. Where I could not verify something from the code, I say so.

---

## SECTION 1: CORRECTNESS

### 1.1 The A19 change (the diff under review) — the main flow

Flow: `run_pass` → `delivered()` (now also returns `units`) → collect `copies` from targets → `kept_copies()` → per-file loop: kept copy / unresolved / other-copy → delete.

**C1. `kept_copies` can keep a copy that is not in any target — and then the "one copy" is not protected from deletion.** `kept_copies` (purge.py:269–272) searches `own` = `<unit>/sources/<fn>` and `<unit>/run/sources/<fn>`, then `copies[v]` (target copies only). But `_own_media` (purge.py:222–230) — used for the *unlisted* branch — also accepts `run/sources/`. The `own` list in the PROVENANCE branch (purge.py:267–268) does NOT check the extension, the `_vid_of(basename) == v` match, `os.path.isfile`, or `not os.path.islink` the way `_own_media` does; it relies on `same()` which does check `isfile`/`islink`. That part is fine. However: if the PROVENANCE's `fn` is e.g. `K.mp4` but the delivery's own file is `K.mp4` while the *attested* copy is found in `copies` — good. The real gap: **`own` paths are built without checking they are inside the unit's real path**; if `fn` were `../x.mp4` the `os.path.basename(fn) == fn` guard (purge.py:268) prevents it. OK — verified safe.

**C2. A delivery whose PROVENANCE names a video twice, or two deliveries of the same video: the second delivery's resolution can be silently satisfied by the first's kept copy.** `copies[v]` is the *global* target-copy list, not per-delivery. Delivery A (hash H1) keeps its own file; delivery B (same video, hash H2) finds no copy with H2 → unresolved → every copy kept. Correct (fail closed). But if B's hash H2 happens to match a *third* copy in an unrelated replay run, B keeps that replay's copy and A's copy is "other" → deleted. That is exactly the ruling's intent (one copy per delivery, by hash). Verified correct.

**C3. `kept_of` (purge.py:483) computes the kept copies *by basename* of the kept real paths, filtered by `other` — but for a non-`other` file it is computed and discarded.** Minor: `kept_of` is computed for every file (the generator runs even when `other` is False because of the `if other and` inside the comprehension — actually the comprehension evaluates `_vid_of` for every kept path on every file, delivered or not). With 46 kept copies and ~200 target files this is negligible, but it is an O(files × kept) scan inside the innermost loop. Not a bug; a note.

**C4. Race: the `copies` snapshot vs. the deletion loop.** `copies` is collected (purge.py:406–415) before the deletion loop. If a *third* process (a render) creates a new copy of a delivered video between the snapshot and the loop, that copy is not in `copies`; if it is the only copy with the attested hash, `kept_copies` already ran and marked the video unresolved → every copy kept → the new copy survives. Fail closed. If the video was already resolved, the new copy is deleted as "other" — correct. No lost-copy race. Verified.

**C5. `sha256_of` cache key uses `os.stat` (follows symlinks) but `same()` rejects symlinks — consistent.** However the cache key (purge.py:211) is `(realpath, size, mtime_ns)`: a file replaced *in place* with the same size and the same mtime_ns (a same-size rewrite within the same nanosecond — practically impossible) would be stale. A file replaced by `os.replace` gets a new inode; `realpath` is the same, size may match, mtime_ns differs → cache miss → re-hash. Correct. **But**: the cache is module-global `_SHA` (purge.py:205) and never pruned — in a long-lived watcher (the service runs for days) it grows by one entry per (path, size, mtime) triple ever seen. At ~200 files/pass × 144 passes/day, with rewrites, this is thousands of entries/day — bounded in practice, but it is an unbounded dict in a daemon. P3.

**C6. `published()` (purge.py:294–311) — the `_latest` midnight rule is applied to the queue's `published_at` too, keyed on `published_source` being falsy.** The queue always writes `published_source` when it writes `published_at` (fetch.py:155), so the midnight rule effectively only fires for main-store metas without a source. Consistent with the docstring. Verified.

**C7. `newest_mtime` (purge.py:348–358) walks the *whole unit* (the whole run directory, including `out/`, `qa/`, `VERIFY/`, transcripts) to decide idleness.** For a run with thousands of render intermediates this is a full `lstat` walk per unit per pass, every 600 s, for every target unit — and the same unit is walked once per target that matches it (here: `run_sources` and, if a run were also under lock_precheck, twice). With 10+ runs this is the purge's dominant cost. Measured 3.36 GB / 121 copies suggests hundreds of files; acceptable, but it is O(total files under runs/) every 10 min, forever, even when nothing changed. P2.

**C8. `open_paths` (purge.py:317–341) reads every PID's fds.** On a busy box this is hundreds of `readlink` calls per pass. Fine. But: a file deleted-then-recreated between the `opened` snapshot and `os.unlink` — the unlink succeeds (POSIX), the render's fd stays valid. Correct.

**C9. `run_pass` holds `purge.lock` (purge.py:376–377) for the whole pass including hashing.** A manual `--apply` while the watcher's pass runs blocks, not fails — correct (the flock is blocking, not `LOCK_NB`). Verified: `fcntl.flock(lock, fcntl.LOCK_EX)` — blocking. Good.

**C10. `kept_copies` reads PROVENANCE.json a second time (purge.py:253–256) after `unit_videos` already read it (purge.py:139–147).** If it changed between the two reads (a render finishing writes PROVENANCE), the delivered-set (from the first read) and the kept-set (from the second) can disagree. Consequence: a video in `vids_delivered` whose second-read PROVENANCE no longer lists it → falls into the `vids - listed` branch → its own section kept by name. Fail closed, no lost copy. But the *reverse* (first read lists it, second read doesn't) → `listed` misses it → own-section branch → if no own section, unresolved → every copy kept. Still fail closed. Verified safe, but the double-read is a latent inconsistency. P3.

**C11. `same()` catches only `OSError` (purge.py:244–248).** `sha256_of` calls `os.stat(path)` then `open(path)`. If the path disappears between `isfile` and `stat`, `FileNotFoundError` (an `OSError`) is caught → returns False → the copy is not attested → if it was the only one, unresolved → every *other* copy kept. Fail closed. But if the file disappears *during* the read (partial read), `hashlib` raises `OSError` mid-iteration → caught → False. Correct. However: a *partial* read that succeeds (file truncated by the writer mid-read, read returns short) yields a **wrong hash silently** — `f.read(1<<20)` until b"" — if the writer truncates, the read just ends early and the hash is of the truncated content. Then `same()` compares it to the attested hash → mismatch → not attested → unresolved (fail closed) or another copy attested. No wrong-keep. Verified: the failure mode is "kept, not deleted" — safe.

**C12. The `other` flag and the `unresolved` check order (purge.py:458–466).** If `rp in kept_paths` → kept. Else if `vid in unresolved` → kept. Else `other = True`. But `unresolved` is keyed by video id, and a video can be unresolved for delivery A while *resolved* for delivery B (B's PROVENANCE named a hash that a copy matches). Then: the copy B attested is in `kept_paths` → kept; the *other* copies: `vid in unresolved` is True (A's entry) → they are kept as "not identified". So A's unresolved-ness keeps every copy — which is the documented fail-closed behavior ("a delivered video whose copy cannot be identified keeps EVERY copy"). But note the copy B attested is counted in `kept_copies` while the others are kept via the unresolved branch — the report's `other_copies` count will be 0 for that video even though extra copies exist. Cosmetic reporting inaccuracy, not a correctness bug. P3.

**C13. `summary()` (purge.py:544–550) reads `rep.get("one_copy_per_delivery")` — but the *refused* path (purge.py:390–393) returns before `one` is set.** `summary` uses `.get(...)` with a default `{}` → prints "0 kept, 0 other copies... 0 unresolved" for a refused pass. Slightly misleading (a refused pass kept *everything*), but the `refused` line prints first. Cosmetic. P3.

**C14. `cmd_purge` (tools/ingest_watch.py:185–201) prints `rep["delivered_runs"]` — present in both paths. But it prints `f['age_h']` from `would_delete` — present. And `--measure` runs `measure_reported` which globs `segment_v*/**` recursively — on the real tree this can be slow (thousands of files) but it is on-demand only.** Verified.

**C15. `test_a_delivered_run_whose_provenance_omits_a_video_it_cut...` asserts `VIDS["C"] in unresolved` and that `runs/pinned_old/sources/VIDS['C'].mp4` exists — but the fixture's `pinned_old` unit's idleness/publish-time state depends on the shared fixture's `_age_dir(3h)`.** I cannot verify the fixture (not printed); the test's correctness depends on `pinned_old`'s publish time being unknown *and* its unit being idle. The comment "(its publish time is unknown too)" says the keep reason is the publish time, not the unresolved-ness — but the assertion only checks existence, so the test passes either way. Weak assertion, not a bug. P3.

### 1.2 Pre-existing code (spot-checks; the diff is the review target but the package is in scope)

**C16. `ledger.append` (ledger.py:34–66): the torn-tail check `os.pread(fd, 1, size - 1) != b"\n"` runs under the flock — but `seal()` (ledger.py:69–85) at service start does its own read-then-write *without* the append's O_RDWR|O_APPEND fd; it opens `O_WRONLY|O_APPEND` and writes `b"\n"`.** If the last line is complete (ends in `\n`), `seal` returns False without writing — correct. If torn, it writes one `\n` — but it does not re-check under the same lock the concurrent `append` uses. In practice `seal` runs at Service.__init__ before any append (service.py:144), and the flock in `seal` (ledger.py:79) is taken — but `append`'s flock is on a *different* fd of the same file; flock locks are per-open-file-description, so two different fds DO conflict — the locks do exclude. Verified: `seal`'s flock (ledger.py:79–82) and `append`'s flock (ledger.py:47) are both LOCK_EX on the same inode → mutually exclusive. Correct.

**C17. `Router.run` (providers.py:837–885): the cache check (851–856) happens *before* `available()` — a frozen back-end's stored reply is reused.** Documented and intended. But note: the cache path is keyed by `(bid, model, prompt-sha, schema, max_tokens)` (providers.py:906–908) — `max_tokens` includes the `max_tokens_floor` adjustment (850), so a role whose floor changed invalidates the cache. Intended.

**C18. `Router._try` (providers.py:927–1004): on a `BackendError`, `h.record(False, ...)` is called (970) — but on the *retryable* path (965–969) the failure is NOT recorded; only after retries are exhausted.** So a back-end that 429s 3 times then succeeds records... nothing for those failures, and one success. The breaker's `window`-fraction rule (providers.py:624) therefore undercounts. Deliberate? The docstring of `record` says failures are judged on a failure — the design records only the *final* outcome of a `_try` call. This means a back-end that 429s every call but always recovers on retry never trips the consecutive-failure breaker. Given the throttle already backs off, this is defensible, but it means the "5 consecutive failures" breaker (providers.json health) fires 5× later than a reader would assume (5 *calls* vs 5 *attempts-sequences*). Worth noting; not a violation.

**C19. `mine.windows` (mine.py:372–390): the overlap computation `i = max(j - min(overlap, (j - i) // 2), i + 1)`.** If `j == i` (a single sentence longer than... no, the inner while guarantees `j > i` when it breaks on words, and `j - i < max_sent` — if the *first* sentence alone exceeds `max_words`, `j` advances past it because the `j > i` guard skips the word check for the first sentence). So `j >= i+1` always → `i` strictly increases → termination. Verified.

**C20. `service.mine_once` (service.py:619–643): `free == 3` gates the idle-release check — if 1–2 videos are in flight, `router.release()` is never called even when idle... but if videos are in flight, mining is not idle. Correct. However `_last_mining` is only updated when the early-return is *not* taken (633) — so after the last video finishes, the next loop with `free==3` and nothing due hits the early return, and `clock() - _last_mining` grows → release fires. Correct.

**C21. `service.check_once` (service.py:571–617): `self._check_seen` is set only when `len(todo) <= CHECK_INFLIGHT - len(self.check_inflight)` (607–608) — i.e. everything due is being started. But `todo` was already truncated to `CHECK_ROWS`/`room` at 610 — the comparison at 607 uses the *pre-truncation* `todo`? No: 607 runs before 610's truncation... actually 606–610: `todo.sort`, then the `if len(todo) <= ...` check, then `todo = todo[:...]`. So the "seen" marker is set when the *full* due list fits in the remaining room — correct: everything due is started, so the next loop may skip. But if `todo` was empty (nothing due), `0 <= room` → `_check_seen = seen` → next loop skips the ledger read until the file changes or a retry is due. Correct.

**C22. `downsignal.noted` (downsignal.py:146–161): `self.pending["fail"]` is set only when it is None (158–159) — the *first* failure after the last answer. But the flush (294) notes answer-then-fail in that order; if two failures arrive, only the first is noted, and the module's 15-min clock uses the noted time. If the gateway keeps failing, the *first* failure's time is the clock's start — correct (the clock should start at the first failure). But if an answer arrives *between* two failures within one tick, `pending["answer"]` and `pending["fail"]` are both set; the flush notes the answer (which resets the module's clock) then the failure (which starts it) — the failure's time is after the answer's. Correct ordering (294: `((True, p["answer"]), (False, p["fail"]))` — answer first). Verified.

**C23. `spend._rewrite_top` (spend.py:35–63): the notice block is rebuilt as `[switch lines] + [non-switch lines]` (57) — this *reorders* the non-switch notices (outage, purge, spend, signal) into whatever order they happened to be in `block`, which is `[line] + kept + others`. `others` preserves the original head order, so relative order of others' notices is preserved. But `kept` (this writer's kept line) is placed *before* `others` — so this writer's notice jumps to the top of the non-switch block. For the outage writer, its own notice jumps above the spend notice. Each writer replaces only its own line (the `mine` filter) — but the *position* of other writers' notices relative to each other is preserved, while this writer's jumps. The spec says "each writer replacing only its own lines" — position jumping is not prohibited, and the switch line is kept first. Cosmetic.

**C24. `coverage.check` (coverage.py:43–95): `rep["coverage"]` divides by `rep["eligible"]` — Shorts are excluded from eligible (77) but `published` includes them. A day with only Shorts → `eligible == 0` → coverage None → "unmeasured" in the MD (110) even though the report *is* measured (`rep["measured"]` is about unmeasured *channels*).** The MD prints "coverage unmeasured" (110) which conflates "no eligible videos" with "channels unmeasured". Cosmetic.

**C25. `fetch.process` (fetch.py:150–151): `rss_pub` is derived from `v["listing_ts"]` when `discovered_via == "rss"` — but `listing_ts` for an RSS-discovered video is the RSS published *epoch* (watch.py:194), converted via `_dt(...).isoformat()`. Then `publish_time(j, rss_published=rss_pub)` (fetch.py:152) prefers `release_timestamp` for was_live, then `rss_published`.** So an RSS-discovered *regular upload* gets its publish time from the RSS feed's second-precision timestamp — good. But an RSS-discovered *livestream VOD* gets `release_timestamp` (stream start) — documented (INGEST-FAIL-03). Correct.

**C26. `queue.find_duplicate` (queue.py:219–235): the title+duration branch requires `duration` truthy — a duration of 0.0 skips the title check. A 0-second video is pathological. Fine.

**C27. `stats.live` (stats.py:29): `span_h = max(1e-9, min(hours, (now_ts - min(discovered_ts))/3600))` — if `disc` is empty, `min([] or [now_ts])` → now_ts → span 1e-9 → `videos_seen_per_hour` = 0/1e-9 = 0.0. Correct.

**C28. `service._settle` (service.py:329–373): `passes = int(v.get("mine_tries") or 0) + (1 if rejected else 0)` — but `v` is the row *as claimed*; if two passes raced... they can't (the claim is atomic, service.py:635). Correct.

**C29. `hook_video` (service.py:375–469): `cost` sums `role IN ('hook','spotlight')` for the video — but the *moment* pass's cost is excluded, and a previous hook pass's cost is included (cumulative "so far", the log says so at 432). Correct.

**C30. `flagcheck.ask` (flagcheck.py:252–271): `cands` filters `checkers(router, miner)` by `allowed`. If `allowed` is an empty list (no back-end passed calibration), `cands` is empty → returns "no checker..." — but the watcher's `check_once` returns 0 early when `not self.check_allowed` (service.py:577–578), so `ask` is never called with empty allowed from the watcher. The `elif "no checker" in str(ans.get("unmeasured"))` (service.py:506) — `ans["unmeasured"]` is a *string* in the no-cands case but a *list* in the tried case (flagcheck.py:271); `str(list)` contains "no checker" only if... it doesn't. So the log line at 507 fires only for the string case. For the list case (all back-ends failed), nothing is logged — the unanswered question is silently retried later. The spec says "a question no back-end answered is unmeasured, never agreement" — it is (nothing recorded). But the "never silent" comment (service.py:506, "audit r40p1 c2, glm") is only honored for one of the two unmeasured shapes. Minor.

### 1.3 N+1 / performance

**C31. `service.check_once` → `ledger.read(self.p["ledger"], from_time=now - 13 days)` (service.py:589) — a full bisect + read of the tail every time the ledger changes (size/mtime) or a retry is due.** With the 30 s loop and an active ledger, this re-reads the 13-day tail every 30 s. The `offset_before` bisect bounds it, but the *read* itself parses every line in the window. At 100k lines/13 days this is the documented 16–25 s → the recent tail. Every 30 s. That is the design (the `check` loop), and the `_check_seen` guard skips it when nothing changed — but the ledger *always* changes while mining. So during active mining: a 13-day-tail parse every 30 s. This is the heaviest recurring cost in the process. P2.

**C32. `ledger.best_unused_moments` → `record_by_sha` (ledger.py:254–269) — called per drifted line, opening and JSON-parsing transcript files.** Only on contract-fp drift; rare. Fine.

**C33. `mine.mine_video` → `contract.sentences(rec)` (mine.py:571) — full tokenization per pass; the hook pass re-derives it (service.py:386→401).** Each pass re-reads and re-parses the transcript. For a 3-hour VOD this is the dominant per-video cost. Not a leak; noted.

### 1.4 Edge cases

**C34. Empty ledger / empty queue:** `ledger.read` on a missing file returns ([], []) (ledger.py:157–159). `coverage.check` with no channels → `rep["measured"] = True`, coverage None. `stats.live` with no rows → zeros. Verified.

**C35. `purge.run_pass` with `spec["targets"]` all disabled:** `copies` empty, `kept_copies` still runs (PROVENANCE hashes checked against nothing → unresolved → but no target files to keep, so nothing happens). `one["kept_copies"]` = 0. Correct.

**C36. A delivered video whose only copy is in a *reference* (protected, never a target):** `copies` (targets only) won't include it; if the PROVENANCE hash matches nothing in targets → unresolved → "every copy kept" — but there are no target copies, so nothing to keep; the reference copy survives because references are never targets. Correct, and test_a_reference_holding... (test_purge.py, 4th new test) covers the case where the reference *is* the attested copy — wait: in that test the reference's file IS found? `copies` only includes target paths; the reference's `sources/K.mp4` is under `/references/` which is in FORBIDDEN (purge.py:46) — but is it a *target*? Targets are `runs/*/sources/*`, lock_precheck, /tmp/word_pass_*. The reference's file is NOT in `copies`. So `kept_copies` for the reference delivery: `own` = `<ref>/sources/K.mp4` — the `own` list is built from the unit's own dirs regardless of targets (purge.py:267–268) → found → `keep[realpath]` → the reference's copy is the kept one. Then the run's copy: `other` → deleted. The test asserts exactly this. **Verified: the `own`-path mechanism is what makes references work as attested-copy holders.** Good — this is the subtle case and it is handled.

**C37. `kept_copies`'s `own` paths are NOT filtered by `exts`** (purge.py:267–268) — unlike `_own_media` (which filters by extension, purge.py:227). So a PROVENANCE naming `file: "K.mp4"` finds `sources/K.mp4` even if `.mp4` were not in `media_ext` — harmless (the kept set is a keep-set; extra keeps are conservative). But the *reverse*: if PROVENANCE's `fn` has an extension not in `media_ext` (e.g. `.part`), the kept copy is registered, and the deletion loop only sees files whose extension IS in `media_ext` — the `.part` file is never a deletion candidate anyway. Consistent. However: if the delivery's own file is `K.mp4` and PROVENANCE names `K.mp4` but the *target* copy with the right hash is `K.mp4` in another run — `own` is checked first; if the own file's hash differs, the target copy is used. If BOTH the own file and a target copy have the right hash, the own file wins (the `next(... ) or next(...)` — note: `next((p for p in own if same(p,h)), None) or next(...)` — if the own generator yields a path, it wins). Documented preference (A43: "its own sources/ copy preferred when the hash matches"). Verified.

**C38. `same()` uses `os.path.isfile(p)` (follows symlinks) then `not os.path.islink(p)` — a symlink to a regular file: `isfile` True, `islink` True → returns False.** So a symlinked own-section is never attested → unresolved → every copy kept. Fail closed, consistent with the "a symlink is never followed" rule (purge.py:446). But `_own_media` also rejects symlinks (purge.py:228) — consistent. Verified.

---

## SECTION 2: LAW COMPLIANCE

- **L-x (no single model, one provider interface, ≥2 back-ends/role, no vendor/model outside providers.json):** COMPLIANT. `load_config` enforces ≥2 (providers.py:158–161); `validate_config` requires `vendor` per back-end (109–111); the probe role's back-ends must all be the signal's vendor (140–142). Tests `test_no_vendor_or_model_name_outside_the_provider_config` / `test_no_vendor_name_in_the_code_outside_the_provider_config` exist. The `mine_paid` role lifts the freeze only with a cap (128–129, 811–812). One nuance: `downsignal.PROBE_PROMPT` (downsignal.py:38) is a *prompt* in code, not a vendor/model — fine.
- **L-l (a reply counts only whole; nothing repaired; a failed call is never a pass):** COMPLIANT. `Invalid` (providers.py:58–59); the retry-with-reason (987–988) is a *new* ask, not a repair; `AllBackendsFailed.outage` (70) distinguishes outage from rejection; `flagcheck`'s unmeasured is never agreement (flagcheck.py:344–346, 365–369).
- **L-j / L-m (fail closed; nothing measured is never a pass):** COMPLIANT. `config.aware` returns None for a naive time (config.py:53–59); `ledger.expiry` takes the earlier of the two (280–286); `coverage`'s unmeasured channel → `measured: False` (94) and the report is retried (service.py:701–704); the purge's unreadable /proc or delivered-set refuses the pass (purge.py:386–393); `state()`'s "unmeasured" (spend.py:130–134). The A19 unresolved→keep-every-copy is fail closed (purge.py:264–281).
- **L-h / L-k (read as spoken; stored records never rewritten):** COMPLIANT. `eligibility.spoken` via `contract.sentences` (contract.py:123); the store's records are written once (`_write_once`, fetch.py:236, 240); the ledger is append-only (ledger.py:34–66); `verify_line` re-derives (contract.py:162–181).
- **L-e (word timing at cut time):** COMPLIANT. `timing: "segment"`, `duration_s: null` for segment timing (mine.py:543–544); the packager re-anchors (documented; the code records `duration_estimate_s`).
- **L-u (hard exclusions flagged and excluded before ranking):** COMPLIANT. `HARD_RISKS` (mine.py:23–24); the adapter pre-applies them (ledger.py:347–348); the ruling-40-P1 release only via `effective_risk` (ledger.py:229–241) with accusation never released (212, and the test). The A19 change does not touch exclusions.
- **L-v (a moment never spans a speaker change; re-uploads excluded; publish time):** COMPLIANT. `turn_change_inside` measured (contract.py:129–135), the adapter requires... actually the adapter *drops* on `is True` (ledger.py:351–352) and leaves null (not measured) to the packager — matches the spec ("the packager requires false"). Re-uploads: `find_duplicate` (queue.py:219–235) + the adapter's `duplicate_of` drop (ledger.py:353–354). Publish time: `published_at_source` recorded (fetch.py:62, 155).
- **Secrets (keys by name from the env file; never printed/logged/written):** COMPLIANT. `Keyring` (providers.py:180–221); `redact` on error detail and raw (953–955); `__repr__` shows only counts (210–211); the redirect refusal (322–327, 304–306); the override host allowlist (168–177). Tests: `test_keys_never_appear_in_repr_or_errors`, `test_a_redirect_is_refused...`, `test_error_text_is_redacted...`.
- **SPEND FREEZE:** COMPLIANT. `frozen()` (783–786) — a back-end with no vendor is frozen (fail closed); `available()` (806–818) and `_try`'s second check (931–932) both refuse; the cache bypass (851–856) is the documented "stored reply costs nothing"; `mine_paid`'s `freeze_lifted` + `daily_cap_usd` (providers.json:116–119) with `RoleCaps` (687–726) and the priced worst case (899–904). The 90% tripwire notifies, never halts (spend.py:163–184; `order()` moves metered back-ends last, 791–797).
- **Integrator B1–B4:** B1 (notify, never halt) — spend.py + `order()`. B2 (outage vs rejected; nothing lost) — `AllBackendsFailed.outage` + `_settle` (329–373) + the tests. B3 (GPU0 lease, `gpu0.held()` a check) — `OllamaLocalBackend.enabled` (494–498), `release()` (526–532), the idle release (service.py:630–631). B4 (age gate vs rate limit) — watch.py:24–27, 69–72, fetch.py:103–104, 133–136. All answered.

**No violations found.** One PARTIAL: the "never silent" unmeasured log (C30) — the list-shaped `unmeasured` (all back-ends tried and failed) is not logged, only recorded in the returned dict which the watcher discards. It is a logging gap, not a law gap (the flag still stands).

---

## SECTION 3: SECURITY

- **SQL injection:** COMPLIANT. Every query is parameterized (`queue.py:97–103, 242–250, 254–256`; the f-string SQL at 133–134, 165–166, 208–209 interpolates only *column names* from code-owned constants, never user input). `stats.py`'s queries are constant strings with bound params.
- **Auth:** N/A (no routes; a local tmux process). The service lock (service.py:152–166) is the only "auth" — flock, correct.
- **Rate limiting:** the Router's per-back-end throttle + breaker + global semaphore (providers.py:654–682, 769–771) and the YouTubeGate (watch.py:37–73) bound concurrency. The A/B and flagcheck CLIs *override* `global.max_inflight` (ab.py:252, flagcheck.py:569) with the documented "the two together stay under ~20" — this is a convention, not enforced; running the A/B while the watcher mines can exceed 20 in flight on the shared gateway. P3 (documented, not enforced).
- **Secrets in code:** none. `providers.json` holds paths and variable *names* (`key_env`, `key_env_prefix`), not values (providers.json:21, 31, 40, 50, 57, 65, 72, 81, 90). The env file path is hardcoded (`/home/ultron/protocol_pulse/.env`, providers.json:10) — a deployment assumption, documented.
- **Unvalidated input → fs/shell:** `yt-dlp` is invoked via `config.ts()._ytdlp(args, ...)` (not shown) with code-built arg lists (watch.py:129–130, fetch.py:92–93) — video ids come from YouTube's own responses and are matched against `VIDEO_ID` where it matters (ledger.py:27, purge.py:102–104). `cmd_handoff`'s `os.link` (tools:143) is write-once. `purge`'s `os.unlink` (purge.py:491) operates only on paths that passed the realpath/forbidden checks (449). `overrides.json` URLs are allowlisted by host (providers.py:168–177). No `shell=True` anywhere. **One note:** `purge.json`'s targets are trusted (the spec validates them, purge.py:58–99) — `glob.glob(t["units"])` with a spec-controlled pattern; the spec validation requires absolute paths and forbids `..` (81). Good.
- **Prompt injection:** the prompts fence the transcript in `<sentences>` and mark it untrusted (mine.py:104–110, flagcheck.py:144–151); `_untrusted` prevents closing the block (mine.py:397–400). The A/B's judge prompt fences the lists too (ab.py:61–69). Thoughtful.

---

## SECTION 4: FRONTEND QUALITY

There is no UI. The "frontend" is the CLI (`tools/ingest_watch.py`) and the STATE/live.json/coverage-MD reports.

- **CLI:** clean argparse, subcommand help, `--hours`/`--limit`/`--json` where useful. `cmd_purge` prints a human summary + per-file would-delete lines + optional JSON (185–201). Good.
- **Coverage MD (coverage.py:105–125):** the table escapes nothing — a title containing `|` breaks the row. P3. The "unmeasured" wording conflates zero-eligible with unmeasured channels (C24).
- **live.json / STATE:** the notice machinery (spend.py) is unusually careful (idempotent, flock, only-rewritten-when-changed, the switch line kept first). This is better than most production notice systems.
- **Loading/error/empty states:** the CLI's `status`/`hooks`/`moments` print empty-state summaries (e.g. tools:177–182 "hook pass done on 0; 0 hook rows; $0.0000"). Errors: `cmd_moments` raises SystemExit on an unreadable optout (98). `cmd_coverage` prints the report path. Adequate.
- **Hardcoded values:** `COVERAGE_HOUR_UTC = 11` (service.py:60) — documented as 06:00 ET; correct only while the US/Eastern offset is -5 (it is, in November; DST would make it 07:00 ET for 3 weeks in March/November — a known, unhandled nit). `MAIN_TREE = "/home/ultron/protocol_pulse"` (config.py:14) and the worktree paths (contract.py:22, providers.json:103, 127) are deployment-constants, documented as assumptions.

Score: this is a headless service; judged as such it is above average. 78/100.

---

## SECTION 5: BACKEND QUALITY

- **DB writes:** SQLite, `isolation_level=None` (autocommit) with an RLock (queue.py:82–84); `PRAGMA synchronous=FULL` + WAL (86–87). Every write is a single statement — no multi-statement transactions needing rollback. `set_state` + `event` are two statements, not wrapped: a crash between them loses the event, not the state — acceptable (the state is the truth). The ledger's append is fsync'd under flock (ledger.py:61). **Good.**
- **External calls:** every `Backend.complete` maps exceptions to `BackendError` kinds with timeouts (providers.py:344–359, 398–441, 445–471); the Router retries/falls back; the breaker and throttle. `CreditMeter.measure` catches everything and records `last_error` (spend.py:101–114). `rss_list`/`playlist_list` raise typed `ListError`. **Good.**
- **Loop failure isolation:** `_loop` catches `Exception`, logs, records an event, and continues (service.py:784–793). `BaseException` paths (KeyboardInterrupt) are handled in the fetch/mine flows (service.py:254–258, 302–307) and the breaker's `abandon` (providers.py:870–877). **Good.**
- **Memory:** `_SHA` grows unboundedly (C5); `self._conv` is cleared at 5000 (service.py:651–652); `Health.events` is a bounded deque (581); `Throttle`/`SpendBook` are constant. `stats.live` builds the full 24h call list in memory (stats.py:40) — at ~1,000 calls/day documented, fine; the docstring itself flags the daily-accumulator next step (stats.py:4–5). **Acceptable, documented.**
- **Logging:** `_log` writes ISO-timestamped lines to stdout + file (service.py:179–186); events carry `traceback.format_exc()[-2000:]` (252, 300, 465, 526, 540, 790). Errors are redacted (providers.py:953–955). The one gap is C30. **Good.**
- **Threads:** 8 daemon loops + 5 pools; the pools' `max_workers` are derived from the config's inflight caps; `close()` shuts down the video/window pools (168–175) but not `self.checks` or `self.hooks`/`self.hook_windows` — `close()` shuts `videos` and `executor` only (170–171). On `run()`'s exit the process dies anyway (daemon threads), but `cmd_once` → `close()` (tools:63) leaves the check/hook pools running until GC — their threads are non-daemon? `ThreadPoolExecutor` threads are daemon-ish (they are joined at interpreter exit via `atexit`). In `once` mode this delays exit if a check is in flight. Minor. P3.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Genuinely excellent (say so):**
- The fail-closed discipline is consistent *everywhere* — naive times, unreadable files, unmeasured spend, unresolved copies, contract drift. This is the hardest habit to maintain and this codebase has it.
- The notice/STATE machinery (spend.py) with its flock, idempotence, and "never rewrite a file you could not read" (audit r87 C1-5) is production-grade.
- The reply cache + strict validation + "rejected, never repaired" is the right design and the tests prove the negative cases (317 tests, most of them must-fail).
- The A19 diff's fail-closed unresolved→keep-every-copy, and the reference-as-attested-copy case (C36), are handled correctly.

**Material gaps:**
1. **No integration test of the A19 purge against the *real* purge.json paths.** `test_the_real_spec_targets_only_acquired_sources_and_the_word_pass_temp` (test_purge.py) checks the spec's shape, but the 3.36 GB dry-run measurement was manual. A test that runs `run_pass(dry_run=True)` against a fixture shaped like the real tree (runs + references + lock_precheck) and asserts the kept/other partition would catch the `own`-vs-`copies` asymmetry (C37) if it ever regresses. (The 5 new tests use a synthetic `tree` fixture; none exercises `run/sources/` as the `own` location, nor a PROVENANCE `file` that is a plain basename in `run/sources/`.)
2. **The 13-day-tail re-read every 30 s (C31).** A materialized "latest line per moment_id" (even a second SQLite table updated on append) would cut the check loop's cost by ~100×. At 100k lines this is the difference between a 25 s and a 0.2 s loop.
3. **`newest_mtime`'s full-unit walk (C7).** An mtime cache keyed by (unit, dir-contents-mtime) or simply walking only the target subdirs (the idleness signal could come from the unit's *own* dir mtime + the sources/ dir) would make the purge O(target files) instead of O(unit trees).
4. **No metrics/observability beyond live.json.** No counters exported (Prometheus/`/metrics`-style); debugging a production incident means grepping `service.log` and the events table. For a "premium" product the events table is the audit log — there is no retention/pruning policy for `events` or `calls` (they grow forever; `calls` at ~1,000/day × 16 columns is fine for years, but `events` includes 2,000-char tracebacks).
5. **DST: `COVERAGE_HOUR_UTC = 11`** (service.py:60) — use `ZoneInfo("America/New_York")` (already imported in providers.py:684) to compute the hour.

---

## SECTION 7: SCORES

- Backend logic: **88**/100 (the A19 logic is correct including the hard cases; deductions for C5/C7/C10/C31, the `_check_seen` subtlety, the unmeasured-logging gap)
- Frontend/UI: **78**/100 (CLI + reports; MD table escaping, the coverage/unmeasured wording, DST)
- Error handling: **90**/100 (fail-closed everywhere, typed errors, tracebacks in events; the C30 silent-list case, `close()` not joining all pools)
- Security: **88**/100 (parameterized SQL, redaction, allowlisted overrides, fenced prompts; the unenforced 20-in-flight convention, hardcoded deployment paths)
- Performance: **74**/100 (C31's 30 s×13-day-tail re-read, C7's full-unit walks, the unbounded `_SHA`; everything else is bounded and documented)
- Law compliance: **95**/100 (no violations; the "never silent" partial, and the A/B's convention-only inflight cap)
- World-class gap: **80**/100 (the discipline is world-class; the missing integration test of the real-tree purge, the check-loop cost, and the absence of any metrics export are what a Bloomberg/Coinbase shop would add)
- **OVERALL: 85/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | none — the diff is production-ready as written; the fail-closed paths hold | — | —

P1 HIGH | Add an integration test of `run_pass` against a fixture that includes a delivery whose attested copy lives in `run/sources/` (the `own` second path) and a PROVENANCE `file` that is a plain basename there | tests/ingest/test_purge.py (new) | the `own` branch (purge.py:267–268) is the only code path with no test; a regression there silently deletes the attested copy of every run/sources delivery
P1 HIGH | Materialize the check loop's "latest line per moment_id" (a queue table updated in `_append`) or shrink the read window | service.py:589, ledger.py:309–310 | a 13-day-tail parse every 30 s while mining; at 100k lines this dominates the process
P1 HIGH | Cache `newest_mtime` per unit (or walk only the target subtrees) | purge.py:348–358, 433 | a full lstat walk of every run tree (including out/qa/VERIFY) every 600 s, forever, even when nothing changed

P2 MEDIUM | Prune or bound the `_SHA` cache (LRU or clear at pass end) | purge.py:205 | unbounded dict in a long-lived daemon; thousands of entries/day
P2 MEDIUM | Read PROVENANCE.json once (pass it from `unit_videos` to `kept_copies`) or re-read under the same problems-check | purge.py:139–147, 253–256 | the delivered-set and the kept-set can be derived from different reads of the same file
P2 MEDIUM | Compute the coverage hour from `ZoneInfo("America/New_York")` | service.py:60 | 06:00 ET becomes 07:00 ET for the DST transition weeks; the "daily" report drifts
P2 MEDIUM | Export counters (a `/metrics`-style snapshot or a periodic event rollup) | service.py (new) | incident debugging currently means grepping logs; the events table has no retention policy
P2 MEDIUM | Escape `|` in the coverage MD's title/channel cells | coverage.py:118–122 | a title with a pipe breaks the Markdown table

P3 LOW | Log the list-shaped `unmeasured` outcome in `check_row` (the "no checker" string case is logged; the all-back-ends-failed list is not) | service.py:506–507, flagcheck.py:271 | the "never silent" intent (audit r40p1 c2) is only half-honored
P3 LOW | Enforce the shared 20-in-flight cap across the watcher and the CLIs (read the watcher's live.json, or flock a counter) | ab.py:252, flagcheck.py:569 | the "~20" is a convention; a concurrent A/B + mining can exceed it on the shared gateway
P3 LOW | `close()` should shut down `checks`, `hooks`, `hook_windows` too | service.py:168–175 | `once` mode can linger at exit while a check is in flight
P3 LOW | `summary()` for a refused pass should say "nothing deleted (refused)" instead of "0 kept, 0 other copies" | purge.py:544–550, 390–393 | the A19 numbers are meaningless when the pass never ran
P3 LOW | Fix the weak final assertion in the C-omission test (assert the *keep reason*, not just existence) | tests/ingest/test_purge.py (last test) | the test passes whether the keep came from unresolved or from the publish-time rule

---

## SECTION 9: THE ONE THING

Add the missing integration test that runs `run_pass` against a fixture where the attested copy lives in `run/sources/` and in a reference — it is the only untested branch of the one code path (purge.py:267–268) whose silent regression would delete the very copies the ruling exists to protect.

---

## SECTION 10: FINAL VERDICT

The A19 diff is correct, fail-closed in every failure mode I could construct, and its hardest case (a reference holding the attested copy, a delivery whose own file no longer matches its PROVENANCE hash) is handled and tested. Ship it. Before or immediately after merge: add the `run/sources`/reference integration test, and put the check loop's 13-day-tail re-read and the purge's full-unit mtime walk on the next-iteration list — they are the only two costs that grow with the data rather than the work.