# heimdall_minimax (minimax/minimax-m3.1-flash, 392.5 s, $0.010, finish length)

# PROTOCOL PULSE — CYCLE 2 (final) REVIEW: pp-ingest / A19 "one copy per delivery"

I did not file a cycle-1 report, so this is an independent second pass over the same diff, cross-read against the three cycle-1 outputs and the cycle-1 consensus (which already fixed C1-1…C1-4). Everything below is verified against the code as printed in this prompt.

---

## 1. WHAT THE OTHER MODELS CAUGHT THAT I MISSED

Since I filed nothing in cycle 1, the honest framing is: here is what I found independently, and where the cycle-1 reviewers were right and I would have said the same.

| Cycle-1 finding | My cycle-2 view |
|---|---|
| glm C5: the module-level sha256 cache grew for the watcher's lifetime → fixed with `SHA_CACHE_MAX = 4096` | **Agree, but the fix is half a fix.** The bound is now a *thundering-herd clear*: `_SHA.clear()` at purge.py:219-221 throws away every entry, so the pass after the clear re-hashes every copy of every delivered video (see my P1-1). Dead paths (deleted files) are never evicted, so the cache fills with garbage and then clears. |
| glm C3 / muse: `kept_of` was derived from the kept file's *name* → fixed by keying `kept_paths` on the video id | **Agree, fixed correctly.** purge.py:275/282 now store `(video_id, why)` and purge.py:486 filters on `kv == vid`. The `section_1.mp4` case is now right. |
| glm C1: the attested copy in a reference's `run/sources/` was not found → fixed by adding `run/sources/` to the `own` paths | **Agree, fixed correctly** (purge.py:270-271), and the basename guard (`os.path.basename(fn) == fn`) closes the traversal hole. |
| qwen P1: "run/sources/ is not collected into `copies`, so attested copies there are unresolved" | **Agree with the refutation.** `copies` is the set of files the purge *may delete*; a file in `run/sources/` is never a target, so it must not be in `copies`. The `own` list is the right place. |
| qwen: the sha256 cache is not thread-safe | **Agree, but low.** `dict` ops are atomic; the worst case is a duplicate hash. The real concurrency hazard is the *pass* itself, not the dict (see P2-1). |
| qwen: PROVENANCE.json is read twice (unit_videos + kept_copies) | **Agree, P3.** Two reads of the same file per delivery per pass; harmless at 15 deliveries. |
| glm C7: `newest_mtime` walks the whole unit per target per pass | **Agree, P2.** It is the dominant cost after the hashing (P1-1) and it is walked once per target unit, not once per unit. |
| muse: the `copies` scan is done before the deletion loop and re-globs the same patterns | **Agree, P3** (wasteful, not wrong). |

**What nobody in cycle 1 caught** (my new findings, §3): the *global* `unresolved` key (semantic gap in the ruling), the hash-search cost with the unused `bytes` field in PROVENANCE, the wholesale cache clear, the missing "two deliveries of the same video" test (A43 is asserted in the STATE assumptions but has no test), and the STATE document's A19 text still stating the old rule.

---

## 2. WHERE I AGREE / DISAGREE

**Agree (all three):** the diff is fail-closed and safe to ship. I independently re-derived the safety argument and it holds:

* The attested copy is protected by **realpath** (purge.py:275 `keep[os.path.realpath(found)]` vs purge.py:451/462 `rp = os.path.realpath(p)`; `rp in kept_paths`). The same file reached by two different path spellings yields the same realpath → protected.
* `same()` (purge.py:247-251) rejects symlinks (`not os.path.islink`) and non-files, and swallows `OSError` → an unreadable candidate is never taken as the attested copy.
* The `own` path is built only from a plain basename (purge.py:271) → no traversal out of the unit.
* The kept copy is exempt from *every* later rule (expiry, unit idle, open-in-a-process) because the loop `continue`s at purge.py:462-464 → a kept copy can never be deleted by any later branch.
* An unresolved video is checked **before** the "other copy" branch (purge.py:465-468) → it can never lose a copy.
* The `copies` snapshot vs. the deletion loop race is fail-closed: a copy created after the snapshot is either not in `copies` (→ the video was already resolved → it is an "other copy" and is deleted, correct) or the video was unresolved (→ every copy kept).

**Disagree (muse, partially):** muse's "the two `if` blocks should be an `elif`" — I agree the *current* order is correct (kept copy wins over unresolved) and that an `elif` would be equivalent, but the fragility is not a defect: the order is the fail-closed one and is now covered by the C1-2 test. No change needed; a comment would help.

**Disagree (qwen, partially):** qwen's "the delivery's own file is deleted when another copy has the hash" was called a possible violation of the ruling. I agree with the *outcome* (the ruling says keep the copy whose bytes the PROVENANCE attests; the delivery's own re-acquired file is a different byte string and is "another cached copy"), and the test `test_a_delivery_whose_own_file_is_not_the_attested_one_keeps_the_copy_with_its_hash` pins it. But qwen's framing "the delivery's own file is deleted" deserves a STATE line, because it is the one case where a *delivery's own* file is deleted — an operator reading "one copy per delivery" could reasonably expect the opposite. **P2, documentation.**

**Disagree (glm, on C1):** glm's C1 concluded the `own` path construction is "verified safe" but stopped at the basename guard. It is safe, but glm did not check the *other* half: `own` is not filtered by media extension, so a PROVENANCE naming `file: "K.txt"` with a matching hash would be recorded as the attested copy. Harmless (a `.txt` is never a target), but it means `kept_copies` can count a non-media file. **P3.**

---

## 3. NEW FINDINGS FROM THIS REVIEW

### N-1 (P1) — `unresolved` is keyed by **video id only**, so one delivery's failure disables the ruling for every other delivery of that video
purge.py:268, 277, 284 all do `unresolved.setdefault(v, …)` where `v` is the video id, and `unresolved` is a single flat dict for the whole pass. purge.py:465 then keeps **every** copy of that video.

Consequence: delivery A (run `pinned_dl`) resolves video K by hash and keeps its copy; delivery B (a *different* run that also delivered K) cannot resolve K (its PROVENANCE names a hash no copy has). `unresolved["K"]` is set → purge.py:465 keeps **all** copies of K, including the ones A resolved and the "other copies" the ruling says to delete. The ruling (A43) is "**one copy per delivery** — two deliveries of the same video keep a copy each"; the implementation degenerates to "one copy per video, and if any delivery is unhappy, keep everything".

It is **safe** (over-keeping, never over-deleting), and the measured run has 0 unresolved, so nothing is lost today. But it is a silent semantic gap, and the report says only `"unresolved": {"K": "…"}` — it does not say *which delivery* failed, so an operator cannot tell a per-delivery failure from a global one.

Fix: key the bookkeeping by `(unit, video)` and treat a video as unresolved only when **no** delivery resolved it; report both maps.

### N-2 (P1) — the hash search hashes every copy of every delivered video: tens of gigabytes on the first pass and after every cache clear
purge.py:272-273: `next((p for p in sorted(copies.get(v, [])) if same(p, h)), None)` — `same()` calls `sha256_of()`, i.e. a **full read** of every candidate until a match. The measured state is 121 other copies of delivered videos at ~1.18 GB each (the Nov 7 runs) → the first pass of a fresh process hashes on the order of **100+ GB**. The `_SHA` cache makes passes 2..N cheap, but the cache is per-process (a service restart re-pays) and is **cleared wholesale** at 4096 entries (purge.py:219-221).

The PROVENANCE source record already carries **`bytes`** (the background states `{video_id, file, sha256, bytes, …}`) and the code ignores it. A size pre-filter (`st.st_size == s["bytes"]`) would skip almost every non-matching copy without reading it. This is the single cheapest large win available.

Cost of the miss: the pass holds `purge.lock` (purge.py:379-380) for minutes, so the watcher's 600 s loop and any manual `purge --apply` serialise behind it, and the pass's own `seconds` grows to minutes.

### N-3 (P2) — the sha256 cache: wholesale clear, no eviction of dead paths, no lock
purge.py:205-222. (a) `_SHA.clear()` at the bound discards every entry, including the hot ones → a rehash storm of the whole corpus (see N-2). (b) Entries for deleted files are never removed, so the cache fills with dead paths and then clears. (c) The dict is shared with no lock; the CLI (`tools/ingest_watch.py:190`) and the watcher can both call `run_pass` — the `flock` serialises them *only* when both pass the same `log_dir` (they do: `p["purge"]`), so the dict is in practice single-threaded, but `run_pass(..., log_dir=None)` (the tests, and any programmatic caller) takes no lock at all.

### N-4 (P2) — the STATE document still states the old rule
The diff updates `purge.py`'s docstring and `purge.json`'s `order`/`note`, but `docs/audits/parallel/pp-ingest_STATE.md` (assumption A19, "a delivered video's media is kept wherever it lies") is not in the diff. The next reader of STATE will implement the pre-A19 rule. The old keep-reason string `"a delivered video's media (attribution law)"` is also gone from the code — anything grepping for it (docs, a dashboard) breaks silently.

### N-5 (P2) — the CLI does not surface the ruling's outcome
`tools/ingest_watch.py:185-201` prints the summary and the `would_delete` lines, but never the kept copy for a video, nor the unresolved list. The ruling says "Report the disk freed" — `summary()` does that — but the *which copy was kept* answer (the whole point of A19) is only in `deleted.jsonl` and in `rep["one_copy_per_delivery"]`. A one-line print of `kept_copies`/`unresolved` would make the ruling auditable from the shell.

### N-6 (P2) — `kept_copies` counts paths, not deliveries
`rep["one_copy_per_delivery"]["kept_copies"] = len(kept_paths)` (purge.py:420) counts distinct real paths. Two deliveries that keep the *same* file (possible when a delivery's own file is a hardlink of another delivery's) count once; and the count mixes target copies with reference copies (references are never targets), so "46 kept" is not "46 copies in the targets". The summary should say which.

### N-7 (P3) — `own` is not filtered by media extension
purge.py:270-271: a PROVENANCE `file` of `K.txt` with a matching hash is recorded as the attested copy. Harmless (never a target) but it inflates `kept_copies` and can make `kept_of` name a non-media path.

### N-8 (P3) — `kept_of` is O(kept) per deleted file
purge.py:486: a linear scan of `kept_paths` for every deleted file. 46 × 121 = 5.6 k comparisons — trivial today, but it is inside the innermost loop and grows with the corpus. A `{video_id: [paths]}` index built once would be O(1).

### N-9 (P3) — `copies` is re-globbed and the deletion loop re-globs the same patterns
purge.py:415 and purge.py:430 glob the same tree twice per pass. Harmless, but the two snapshots can differ (a file created between them is not in `copies` → it is an "other copy" → it is fresh, so its unit is not idle → kept). Fail-closed; noted for completeness.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| A19 core semantics (kept_copies / one-copy-per-delivery) | 8.5/10 | **7.5/10** | N-1: the