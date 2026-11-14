# heimdall_glm (z-ai/glm-5.3-flash, 223.8 s, $0.005, finish stop)

# heimdall_glm — CYCLE 2 REVIEW (pp-ingest, A19 one-copy-per-delivery, 016965a4 + cycle-1 fixes)

Scope: the diff as printed, the cycle-1 fixes (kept_copies → {real path: (vid, why)}, SHA_CACHE_MAX, the new tests), the other models' cycle-1 outputs, and the consensus. I re-verified every claim against the printed code. Where I cannot verify from the printed code, I say so.

---

## 1. WHAT THE OTHERS CAUGHT THAT I MISSED

**Muse (C1-2, adopted):** `deleted.jsonl`'s `kept_copies` was derived from the kept file's *name* (`_vid_of(basename(k))`). I noted the O(files × kept) cost in my C3 but missed the correctness half: a PROVENANCE `file` not named by its video id (e.g. `section_1.mp4`) would have logged `kept_copies: []` beside a deletion. Their fix — keying `kept_paths` by `(video id, why)` and computing `kept_of` only when `other` — is right, and the parametrized test (`KKKKKKKKKKK.mp4` / `section_1.mp4`) is the proof. I missed this. Honest.

**Qwen (C1-2, the double-read of PROVENANCE):** I flagged the TOCTOU in my C10 but truncated mid-sentence before stating the consequence. Qwen's sharper point: `unit_videos` flags an unreadable PROVENANCE as a *problem* (pass aborts), so `kept_copies`' `prov=None` branch only fires when the file was readable at `delivered()` and unreadable by `kept_copies()` — a narrow TOCTOU window. Both readings agree: defensible, fail-closed. My C10 was incomplete; theirs was the better statement.

**Consensus C1-4 (the omitted-video test's weak assertion):** I did not check that the last assertion of `test_a_delivered_run_whose_provenance_omits_a_video_it_cut...` passed for either of two reasons. They added an expired publish time so only the unresolved rule keeps it, and they now assert the keep reason. Good catch; I missed it.

**What nobody caught (mine, cycle 2 — see §3):** the `copies` snapshot's *unit-level* asymmetry with the deletion loop, and the `unresolved`-dict's cross-delivery overwrite.

---

## 2. AGREE / DISAGREE WITH THEIR KEY FINDINGS

**Muse, "copies scan includes files that later fail protect/FORBIDDEN/islink — wasteful, not a bug":** Agree, with a sharper consequence they missed — see N1 below. The wastefulness itself is trivial (the extra candidates just fail `same()`).

**Muse, "the two ifs, not elif, are correct but fragile":** Agree. I verified the truth table: `rp in kept_paths` → keep+continue; else `vid in unresolved` → keep+continue; else `other=True`. A file in `kept_paths` whose vid is also in `unresolved` (possible: delivery A resolved, delivery B unresolved, same vid) correctly keeps it via the first branch. An `elif` would read better; no behavior change. Their "actually correct but fragile" verdict is exactly right.

**Muse, kept_of realpath-basename note:** They concluded it's correct; the cycle-1 fix made it moot (keyed by vid). Agree, superseded.

**Qwen, "sha256_of cache not thread-safe":** Agree with their severity (low) and their reasoning, but their mechanism is slightly off. `run_pass` holds `purge.lock` (purge.py:376–380) exclusively for the whole pass, and both the watcher's loop and the manual CLI go through `run_pass` — so two passes never overlap *by construction*. The unlocked `_SHA` dict is therefore only ever touched by one pass at a time. Their "two threads could compute the same hash twice" scenario needs two concurrent passes, which the flock prevents. What *is* true: the GIL makes dict check-then-set effectively atomic here, and even a redundant re-hash is harmless (the key includes mtime_ns). So: agree it's a non-issue, disagree that the thread-safety argument is what makes it one — the flock does.

**Qwen, "the delivery's own file is treated as another copy and deleted":** They walked it to the right answer themselves ("actually correct"). One nuance they stated but didn't land: when the delivery's own file does NOT match the attested hash and a *target* copy does, the own file is deleted as `other` — which is exactly the ruling's intent (keep the attested bytes, not the delivery's stale re-acquisition). Their test `test_a_delivery_whose_own_file_is_not_the_attested_one...` proves it. Agree.

**Consensus, qwen's c1 P1 (run/sources/ not in copies) refuted:** Agree with the refutation. `copies` lists only *target* files (the deletable set); `kept_copies` checks the delivery's own `sources/` and `run/sources/` *before* `copies`. A file in `run/sources/` of a reference is never a target, so it's never deleted, and it's found via `own`. The refined case (own sources/ missing, attested copy in the reference's run/sources/) is exactly what the new parametrized test covers. Correct.

**Consensus C1-3 (SHA_CACHE_MAX):** Agree. 4,096 entries, cleared wholesale. One note: the clear-then-insert means a pass that crosses the bound loses its earlier entries mid-pass and re-hashes them — a one-time cost per 4,096 distinct (path,size,mtime) triples, negligible. Fine.

---

## 3. NEW FINDINGS (cycle 2)

**N1 — `copies` is collected from *all* target units, but the deletion loop's `other` classification is per-target; a kept copy in a unit the purge never walks is invisible to `kept_of` only when it's also not in `kept_paths` — which cannot happen. Verified, no bug.** But the *real* asymmetry nobody stated: `copies` (purge.py:409–418) globs `t["files"]` under each target unit and filters to `v in vids_delivered` — it does NOT check `os.path.islink(unit)`... wait, it does (line 412). It does not, however, check that the *file* is a regular file or that its realpath is inside the unit — the deletion loop's guards (purge.py:448–453) run later. So `copies` can contain a symlink or a file outside its unit; `same()` (purge.py:247–251) re-checks `isfile`/`not islink` before hashing, so a symlinked candidate is never *taken* — but it IS hashed if it's a regular file whose realpath escapes the unit (e.g. a hardlinked or bind-mounted path). Consequence: the attested copy can be recorded as a realpath that the deletion loop will later classify as "outside its unit, or a protected path" and *keep* — which is the desired outcome (kept), so the classification agrees. Fail-closed either way. **Verified: no bug, but the invariant "kept_paths keys are exactly the files the deletion loop will keep" is not enforced — it holds only because both paths fail closed.** Worth one line in the design doc, not a code change.

**N2 — `unresolved` is keyed by video id only, across deliveries (purge.py:268, 277, 284: `unresolved.setdefault(v, ...)`).** Two deliveries of the same video, one resolved and one unresolved: the *first* resolution wins the `setdefault`, so the second delivery's failure reason is silently dropped from the report — but the *behavior* is still correct, because the deletion loop checks `vid in unresolved` (any reason) and keeps every copy. So: report-only. But the converse case is the interesting one: delivery A resolves the video (its copy kept), delivery B is unresolved — the loop keeps every copy *including A's already-kept one* (harmless, it's in `kept_paths` too, first branch) and B's. Correct. And the reverse: A unresolved, B resolved — `unresolved[v]` is set (A's reason), so every copy kept, *including* the copy B's PROVENANCE attested. That copy is kept twice-justified (kept_paths + unresolved) — the loop's first branch catches it. **Verified correct; the only cost is a report that under-reports which delivery failed.** P3, report fidelity.

**N3 — `kept_of` (purge.py:486–487) lists kept copies by video id, but a kept copy recorded for a *different* video whose file happens to... no, it's keyed by the recorded vid, not the basename, post-fix. Verified.** One residual: `kept_of` is computed for every `other`-classified file, i.e. once per deletion — O(deletions × kept). At 121 deletions × 46 kept = ~5,600 comparisons per pass, negligible. Previously I called this out as computed-for-every-file; the cycle-1 fix (compute only when `other`) also fixed my C3. Withdrawn.

**N4 — the dry-run/apply asymmetry in `one["other_copies"]` (purge.py:507–509):** counted only in the non-dry-run branch (inside the `else` of `if dry_run`), while `rep["freed_bytes"]` counts the dry-run's would-delete too (line 510 sums `rep["deleted"]`, which the dry-run also fills — see lines 505–506, they're outside the if/else). So a dry run's `summary()` reports "N other copies (X GB) would go" from `one["other_copies"]` — which the dry run *does* fill? Let me re-read. Lines 505–509:

```python
done["files"] += 1
done["bytes"] += size
if other:
    one["other_copies"]["files"] += 1
    one["other_copies"]["bytes"] += size
```

These are *after* the if/else, so they run in both dry-run and apply. And `rep["freed_bytes"]` (line 510) sums `rep["deleted"]`, which both branches fill. So the dry run's summary correctly says "would go". **Verified: no bug.** I raise it only because I initially misread it — the counting lines' placement after the if/else is load-bearing and worth a comment.

**N5 — `published()` cache (purge.py:402, 313): `cache` is a plain dict, per-pass, keyed by vid.** Fine. But note the *negative* caching: a video whose publish time is not measured is cached as `None` and never re-queried within the pass — correct, and the "3 more copies... stay" measurement confirms the intended behavior. No issue.

**N6 — `newest_mtime` (purge.py:351–361) walks the unit; for the `run_sources` target, `unit` is the *whole run directory* (runs/*), so the walk covers out/, qa/, VERIFY/ — my cycle-1 C7, unchanged, and the consensus took no action.** Still the purge's dominant cost, still O(total files under runs/) every 600 s. With the measured 3.36 GB / 121 copies it's acceptable; at 10× the run count it's the first thing to fix (cache newest-mtime per unit across passes, invalidated by the unit's own mtime). P2, unchanged.

**N7 — the `same()` short-circuit order (purge.py:249): `os.path.isfile(p) and not os.path.islink(p) and sha256_of(p) == h`.** `sha256_of` does `os.stat` (follows symlinks) — but `islink` is already false by then, so `stat` and `open` see the same regular file. However: between `isfile`/`islink` and `sha256_of`'s `os.stat`, the file can be replaced; the hash then corresponds to the *new* inode while the *kept* record stores the realpath. If the replacement changed the bytes, the recorded "attested" copy no longer attests. This is the same TOCTOU class as my C4/C5 — the next pass re-derives everything, so the error is self-healing within 600 s, and the deletion of a *wrongly-kept* copy is impossible (kept is kept). **Verified: benign.**

**N8 — `test_a_hash_no_copy_has...`'s second half monkeypatches `purge.sha256_of` to raise `PermissionError` for *every* path (the test's lambda).** That also makes `same()` return False for the delivery's own file — which is the intended fail-closed demonstration. But note the monkeypatch is process-wide for the remainder of the test: the second `_run(tree)` hashes nothing, so `kept_copies` marks the video unresolved via the `found is None` path, and the *first* delivery (`pinned_dl`, hash "0"×64) also stays unresolved. The test asserts only the second delivery's copies; the first's are kept too (unresolved), which the assertions happen to cover (`pinned_dl_replay` kept). Fine, but the test would be clearer if it asserted the first delivery's unresolved reason too. P3, test clarity.

**N9 — `summary()` (purge.py:548): `one = rep.get("one_copy_per_delivery") or {}` — a *refused* pass (purge.py:393–396) returns before `one` is set, so `summary` prints "0 kept, 0 other copies... 0 unresolved" for a pass that never ran the A19 logic.** Slightly misleading (it reads as "A19 ran and found nothing") but the `refused` short-circuit at line 543–544 prints only the refusal, so the A19 numbers are never shown for a refused pass. **Verified: no bug** — the `or {}` guard is for the *old* passes.jsonl records, not for refused ones. Good defensive coding, correctly placed.

**N10 — the diff's purge.json `order` string says "a delivery without PROVENANCE sources keeps its own section" — but the code (purge.py:278–284) implements: for each video in `vids - listed`, keep own media; if none, unresolved.** A delivery whose PROVENANCE.json *exists but has an empty/missing `sources` key* → `srcs = []` → `listed = ∅` → every video in `vids` goes through the own-media branch. That matches A44. But a delivery whose PROVENANCE lists *some* videos: the unlisted ones also go through own-media (A44's second sentence). The purge.json note and the module docstring (purge.py:20–22) say "a delivery whose PROVENANCE names no sources keeps its own sources/ media" — which is the *empty* case; the *partial* case (some listed, some not) is only in `kept_copies`' docstring ("A video the delivery cut that its PROVENANCE does not list... keeps the delivery's own section(s) by name"). All three texts agree; no contradiction. **Verified.**

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| purge.py A19 core (kept_copies, copies, the loop) | 9/10 | 9.5/10 | The cycle-1 fixes (kept_paths keyed by (vid, why), kept_of only when other) closed my C3 and muse's name-derivation bug; the fail-closed paths held under everyone's attacks. Only report-fidelity nits remain (N2). |
| sha256_of + cache | 8.5/10 | 9/10 | SHA_CACHE_MAX closes the unbounded-growth P3; the flock makes the thread-safety question moot (Qwen's mechanism was wrong, his conclusion right). |
| purge.json / docs | 9/10 | 9/10 | All three texts (order, note, docstrings) agree; A43–A45 are faithfully implemented. |
| Tests | 8.5/10 | 9/10 | The mutation-checked additions (section_1.mp4, the cache bound, the strengthened omitted-video assertion) are exactly what I'd have demanded. N8's clarity nit only. |
| Integration (service, CLI, stats) | 9/10 | 9/10 | `summary()`'s `or {}` guard handles old records; the refused-pass path never shows A19 numbers (N9, verified). |

No score dropped. The cycle-1 fixes were the ones I'd have asked for.

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** none. I concur with the cycle-1 consensus: the fail-closed paths hold, and every attack on the attested-copy identification ends in "kept", never "wrongly deleted" or "wrongly kept-then-deleted".

**P1 HIGH:** none.

**P2 MEDIUM:**
- **P2-1** purge.py:351–361 (`newest_mtime`): O(total files under runs/) every 600 s, forever, unchanged from my cycle-1 C7. Not a correctness issue; the first cost fix when the run count grows. Cache per-unit, invalidate on the unit's own mtime.

**P3 (record, do not block):**
- **P3-1** purge.py:268/277/284 — `unresolved` keyed by video id only: when two deliveries of one video disagree, the first `setdefault` wins and the second delivery's reason is dropped from the report (behavior correct, report under-tells). Key by (vid, unit) or keep a list.
- **P3-2** purge.py:505–509 — the `other_copies`/`done` counting lines sit *after* the if/else and are thus shared by dry-run and apply; load-bearing placement, deserves a one-line comment.
- **P3-3** tests/ingest/test_purge.py (`test_a_hash_no_copy_has...`): the monkeypatched-`sha256_of` half also leaves the *first* delivery unresolved; assert its reason too, so the test documents that both fail closed.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Nothing in the code — the highest-leverage act now is to *ship it* and spend the next review cycle on P2-1's `newest_mtime` cost, because the A19 logic has survived three independent reviewers' fail-closed attacks and every remaining finding is report fidelity or future cost.

---

## 7. PRODUCTION READY?

**Yes.** Conditions (none blocking, all recorded):

1. Land P3-1 (unresolved keyed per delivery) whenever the report is next touched — it's the only place where the code tells you less than it knows.
2. Keep P2-1 on the books: `newest_mtime`'s full-unit walk is the purge's growth path; the measured 3.36 GB / 121-copy workload is fine, 10× is not.
3. The one invariant nobody enforces in code — "kept_paths keys are exactly the files the deletion loop will keep" (my N1) — holds today only because both sides fail closed. If anyone later adds a *fast path* to either side, they must re-derive this invariant; say so in design §12.

Basis: I verified the A19 flow end-to-end against the printed code (delivered → copies → kept_copies → the deletion loop's three-branch classification), the cycle-1 fixes are present and mutation-checked, the three texts agree, the dry-run/apply accounting is symmetric where it must be, and the measured dry run (15 deliveries, 0 unresolved, 3.36 GB) is consistent with the code's semantics. No P0, no P1.