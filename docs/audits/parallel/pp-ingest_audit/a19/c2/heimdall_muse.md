# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 360.2 s, $0.030, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (purge A19)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM caught 3 things I missed or under-weighted:**

1. **SHA cache unbounded growth (GLM C5 → fixed C1-3).** I noted the TOCTOU on `sha256_of` but dismissed the cache as "low risk, acceptable." GLM correctly identified it as an unbounded dict in a daemon running for days (200 files/pass × 144 passes/day). This was a real leak. Fixed at `SHA_CACHE_MAX=4096` with `clear()` — I should have flagged it P1, not P3.

2. **`kept_of` by basename vs. by video_id (GLM C3 / my note on `kept_of`).** I flagged the O(n*m) scan as "trivial, not a bug" and noted the basename extraction *worked* for current data. GLM correctly identified the semantic bug: `PROVENANCE.file` is not required to be `<vid>.<ext>` — it can be `section_1.mp4`. My analysis said "actually correct" because all 152 real entries happen to be `<id>.<ext>`. That's testing against current data, not the contract. The fix (store `(vid, why)` per kept path, filter by `kv==vid`) is correct and I should have called it P1.

3. **`own` paths in `run/sources/` (GLM C1-1).** I verified the `basename` guard prevented traversal but didn't verify the second `own` path `run/sources/<file>` was actually checked. GLM's test proved it matters — a reference's attested copy lives in `run/sources/` and would have been missed without it.

**Qwen caught nothing I missed that survived scrutiny.** Qwen's P1 ("run/sources/ not in copies → unresolved") was correctly refuted in consensus: `copies` is intentionally target-only; `kept_copies` checks `own` (including `run/sources/`) *before* `copies`. Qwen's analysis was thorough but its one P1 was a misread of the design.

**What I caught that they under-weighted:** The `copies` snapshot including files that later fail `protect`/`FORBIDDEN`/`islink` checks (wasteful but harmless) — neither of them flagged this, and it's still worth noting for clarity.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| GLM C5: unbounded SHA cache | **Agree** — was P1, now fixed | Daemon leak, correctly bounded at 4096 |
| GLM C1-1: `run/sources/` own path | **Agree** — was P1, now fixed | Required for reference deliveries |
| GLM C3 / my `kept_of` note: basename bug | **Agree** — was P1, now fixed | Contract allows `section_1.mp4`, basename fails |
| GLM C1-4: omitted-video test weak assertion | **Agree** — was P1, now fixed | Publish time unknown → kept for wrong reason |
| Qwen P1: `run/sources/` not in `copies` | **Disagree** — refuted | `copies` is target-only by design; `own` covers it |
| Qwen: `sha256_of` thread safety | **Partially agree** | `dict` ops are atomic in CPython, check-then-set races only cause redundant hashing, not corruption. Low severity. Not a ship-blocker. |
| GLM C2/C4: race on `copies` snapshot vs deletion | **Agree** — correctly analyzed as fail-closed | New file between snapshot and loop: if unresolved → kept, if resolved → correctly deleted as "other" |
| My Cycle 1: `if`/`if` vs `elif` fragility | **Agree with myself** — still fragile | Logic is correct but two bare `if`s with `continue` is easy to misread. `elif` would be clearer. P2. |
| Consensus: fail-closed everywhere | **Agree** | Verified: unreadable PROVENANCE → problem → pass refused; no sha → unresolved → every copy kept; unreadable candidate → `same()` returns False → unresolved |

## 3. NEW FINDINGS FROM THIS REVIEW (Cycle 2)

**N1. `SHA_CACHE_MAX` clear is not LRU — it drops everything (P2).**
`purge.py:219-220`: `if len(_SHA) >= SHA_CACHE_MAX: _SHA.clear()`. When the 4097th entry arrives, all 4096 are dropped, including hot entries for delivered videos' kept copies that will be re-hashed next pass. Correct but wasteful. An LRU or `popitem` would be better. At 200 files/pass and 600s intervals, the cache refills in ~20 passes (3 hours). Not a correctness bug — the re-hash is just I/O. But the comment says "emptied at this size" and the test asserts correctness after clearing, so this is intentional simplicity. **P2 — acceptable as-is, note for future.**

**N2. `copies` deduplication missing — same file counted twice if two targets overlap (P2).**
`purge.py:410-418`: `copies[v]` appends every matching path from every target. If `runs/*` and `lock_precheck/work/*` ever overlap (e.g., a symlink or mount), the same real path appears twice. `kept_copies` then hashes it twice. Harmless — `same()` will match on first occurrence and `keep` deduplicates by `realpath` key. But `copies` could be a `set` per vid. **P2 — no fix needed.**

**N3. `published()` cache is per-pass, not per-video — re-reads `meta.json` for same vid across targets (P3).**
`purge.py:402,470`: `cache={}` is checked in `published()` but `copies` collection doesn't populate it. Each file of the same `vid` in different units re-reads `meta.json` or `q.video()`. At 121 deletions of ~15 vids, that's ~8 redundant reads per vid. Trivial I/O. **P3 — ignore.**

**N4. No finding on Q1 (attested copy deletion) — verified safe.**
Walked every path form:
- `PROVENANCE.file` must be plain basename (`basename(fn)==fn`) — traversal blocked ✓
- `own` paths checked via `same()` which requires `isfile && !islink && sha256==h` ✓
- `kept_paths` keyed by `realpath`, compared against `rp = realpath(p)` in deletion loop ✓
- Symlink to kept copy: `lstat` → `S_ISREG` fails for symlink, kept as "not a regular file" ✓
- Symlink *inside* unit pointing outside: `realpath` check `rp.startswith(unit_real)` fails ✓
- Unit that is both target and delivery: its own `sources/<file>` is in `own`, found first, kept ✓
- Hash cache stale (same size+mtime, different content): practically impossible (mtime_ns granularity); even if stale, `same()` would return wrong boolean — but `os.stat` inside `sha256_of` re-reads mtime, so a replaced file gets new mtime_ns → cache miss → re-hash ✓
- Unresolved video: `vid in unresolved` check keeps every copy, before `other=True` ✓

**No new P0/P1 found in Cycle 2.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| purge `kept_copies` logic | 8/10 | 9/10 | C1 fixes (own path, kept_of by vid) resolved my two open nits; logic verified against all path forms |
| purge `sha256_of` / cache | 6/10 | 8/10 | Unbounded growth fixed; clear-all vs LRU is P2, not P1 |
| purge `run_pass` integration | 8/10 | 9/10 | `copies` snapshot race correctly fail-closed; delivered gate unchanged |
| purge `delivered()` / `unit_videos()` | 9/10 | 9/10 | No change; fail-closed gate solid |
| Tests (test_purge.py) | 7/10 | 9/10 | C1 added 4 mutation-checked tests covering the 3 fixed bugs; coverage now matches spec |
| Overall pp-ingest | 8/10 | 9/10 | A19 diff is production-ready; remaining items are P2 polish |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — must fix before ship: _None._**

All P0s from Cycle 1 were fixed and mutation-checked. No new P0 found.

**P1 HIGH — should fix before ship: _None._**

All P1s from Cycle 1 were fixed. No new P1 found.

**P2 MEDIUM — fix when convenient:**

| # | File:line | Issue |
|---|-----------|-------|
| P2-1 | `purge.py:462-468` | Two bare `if` with `continue` instead of `if`/`elif` — correct but fragile. A future editor adding code between them could break the fallthrough to `other=True`. Use `elif` for the `unresolved` check. |
| P2-2 | `purge.py:219-220` | `SHA_CACHE_MAX` clear drops all entries including hot ones. Consider `collections.OrderedDict` LRU or at least `next(iter(_SHA))` eviction. Current behavior is correct, just wasteful for 3h after each clear. |
| P2-3 | `purge.py:406-418` | `copies` built before `kept_copies` but uses same globs as deletion loop — includes files that will later be rejected by `protect`/`FORBIDDEN`/`islink`. Harmless (they just become hash candidates that are never deleted) but wasteful hashing. Could filter by `realpath` checks at collection time. |

**P3 LOW — record, don't block:**

| # | File:line | Issue |
|---|-----------|-------|
| P3-1 | `purge.py:348-361` | `newest_mtime` walks entire unit per target per pass — dominant cost at scale. Same unit walked twice if matched by two targets. Cache per `unit_real` per pass. |
| P3-2 | `purge.py:483-486` | `kept_of` linear scan of all kept_paths per deletion — O(n*m), trivial at current scale (46×121). |

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Already done:** the four C1 fixes (own `run/sources/` path, `kept_of` by video_id, bounded SHA cache, hardened omitted-video test) — without them, a reference's attested copy could be missed and every `section_1.mp4` deletion would log `kept_copies: []`.

**Going forward:** change `purge.py:465` from `if vid in unresolved` to `elif vid in unresolved` — one keyword that makes the keep/unresolved/other trichotomy impossible to misread and impossible to break by inserting code between the branches.

## 7. PRODUCTION READY?

**Yes — with no conditions.**

The A19 diff is production-ready as written at `016965a4` + C1 fixes:

- Fail-closed on every path: unreadable delivered set → pass refused; no sha / no matching copy / unreadable candidate → unresolved → every copy kept; unknown publish time → kept; active unit / open file → kept.
- Attested copy cannot be deleted: verified across all path forms, symlink cases, realpath comparison, and hash cache staleness.
- SHA identity is correct: `(realpath, size, mtime_ns)` cache key re-hashes replaced files; partial reads produce non-matching hash → unresolved → fail-closed; cost is one hash per file per mtime change, bounded at 4096 entries.
- Tests prove it: 6 A19-specific tests, 4 C1-added tests, each mutation-checked (fails without its fix). Dry run on real data: 15 deliveries, 0 unresolved, 46 kept, 121 other copies (3.36 GB) correctly identified.
- Remaining P2s are polish, not correctness.
