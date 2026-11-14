# heimdall_qwen (qwen/qwen3.8-27b, 391.1 s, $0.011, finish stop)

This is a review of the `pp-ingest` feature, specifically focusing on the **A19 (One Copy Per Delivery)** change in `pipeline/ingest/purge.py` and its integration with the broader ingest pipeline.

### SECTION 1: CORRECTNESS

**1. Critical Logic Error in `kept_copies` (Hash Mismatch Handling)**
In `pipeline/ingest/purge.py`, the function `kept_copies` (lines 233-282) determines which file to keep for a delivered video.
*   **The Logic:** It iterates through `PROVENANCE.json` sources. For each source, it checks if the delivery's *own* file matches the hash. If not, it looks for *any* target copy that matches the hash.
*   **The Bug:** If the delivery's own file does **not** match the hash, but a *different* target copy **does** match the hash, the code marks the *different* copy as `keep` (line 272). However, it does **not** mark the delivery's own file as "safe to delete" explicitly in the `keep` dict, nor does it flag it as "unresolved".
*   **Consequence:** In `run_pass` (line 459), the check `if rp in kept_paths` will be `False` for the delivery's own file (since it wasn't added to `kept_paths`). It will also be `False` for `vid in unresolved` (since a valid copy *was* found). Therefore, `other` becomes `True` (line 466). The delivery's own file is treated as a "cached copy" and is subject to deletion if it is expired and idle.
*   **Impact:** This violates the "One Copy Per Delivery" intent if the delivery's own file is the *only* copy that exists in the `runs/` target, but the hash matches a copy in `references/` (which is protected). Wait, `references/` is not a target for deletion. If the hash matches a copy in `runs/`, that copy is kept. The delivery's own file (which has a different hash) is deleted. This is actually **correct behavior** for "One Copy Per Delivery" *if* the goal is to keep the *attested* content. However, the design doc says: "Keep the acquired source section(s) the delivered pin's PROVENANCE names, by hash". If the PROVENANCE names a hash, and the local file doesn't have it, but another file does, keeping the other file and deleting the local one is logically consistent with "keep the attested content".
*   **However**, there is a subtle failure mode: If the delivery's own file is the *only* file in the `runs/` target, and the hash matches a file in `references/` (protected), `kept_paths` will contain the `references/` path. The `runs/` file will be deleted. This is fine.
*   **Real Bug:** Look at line 269: `found = next((p for p in own if same(p, h)), None) or next((p for p in sorted(copies.get(v, [])) if same(p, h)), None)`.
    *   `own` is the delivery's own files.
    *   `copies` is *all* target files for that video.
    *   If `own` has a match, `found` is that file.
    *   If `own` does NOT have a match, but `copies` (which includes `own` and others) has a match, `found` is that other file.
    *   **The Issue:** `copies` is built in `run_pass` (lines 407-415) by globbing `spec["targets"]`. `spec["targets"]` includes `runs/*` and `lock_precheck/*`. It does **not** include `references/*`.
    *   So, if the attested hash is only found in `references/` (protected), `copies` will be empty for that video (or contain only non-matching files). `found` will be `None`. The video is marked `unresolved` (line 274). **All copies are kept.** This is fail-closed and correct.
    *   **Verdict:** The logic is actually robust. The "bug" I suspected is handled by the `unresolved` fallback.

**2. Race Condition in `sha256_of` Cache**
`pipeline/ingest/purge.py` line 205: `_SHA = {}` is a global dictionary.
*   `sha256_of` (line 208) reads/writes `_SHA` without a lock.
*   `run_pass` is called from the `purge` loop in `service.py` (line 739).
*   `service.py` runs `purge_once` in a thread (line 825).
*   If `purge_once` is called concurrently (e.g., manual CLI `purge --apply` while the service is running), or if the service restarts and overlaps, the global cache is not thread-safe.
*   **Impact:** `dict` operations in Python are atomic for single keys, but the check-then-set pattern (`if h is None: ... _SHA[k] = ...`) is not. Two threads could compute the same hash twice (performance hit) or, worse, if the file changes between `stat` and `read`, the cache key `(path, size, mtime)` might be stale. However, since the key includes `mtime_ns`, a file change invalidates the key. The main risk is redundant computation, not corruption.
*   **Severity:** Low.

**3. `unit_videos` and `PROVENANCE.json` Parsing**
`pipeline/ingest/purge.py` line 139: `for r in list(records) + ["PROVENANCE.json"]:`.
*   It reads `PROVENANCE.json` to extract video IDs.
*   It also reads `PROVENANCE.json` again in `kept_copies` (line 253).
*   **Inefficiency:** Double I/O and parsing.
*   **Correctness:** If `PROVENANCE.json` is corrupt, `unit_videos` adds a problem (line 146), stopping the pass. `kept_copies` catches `OSError/ValueError` and sets `prov = None` (line 255), leading to `unresolved` for all videos in that unit. This is consistent.

**4. Missing `run/sources` in `copies` Collection**
`pipeline/ingest/purge.py` line 412: `for p in glob.glob(os.path.join(unit, t["files"])):`.
*   `t["files"]` is `"sources/*"` for `run_sources` target.
*   This globs `<unit>/sources/*`.
*   Does it glob `<unit>/run/sources/*`?
*   `purge.json` line 10: `"files": "sources/*"`.
*   `purge.json` line 12: `"files": "sources/*"`.
*   The design doc mentions `run/sources` in `kept_copies` (line 267: `os.path.join("run", "sources")`).
*   **Bug:** If a video's media is in `<unit>/run/sources/`, it is **not** collected into `copies` in `run_pass` (lines 407-415) because the glob is only `sources/*`.
*   **Consequence:** `kept_copies` looks for a hash match in `copies`. If the only matching file is in `run/sources/`, it won't be in `copies`. `found` will be `None` (unless the delivery's own `own` list finds it).
*   `own` (line 267) **does** check `run/sources`. So if the delivery's own file is in `run/sources/` and matches, it is kept.
*   But if the delivery's own file is in `sources/` (mismatch) and the *correct* file is in `run/sources/` (match), `copies` misses it. `found` is `None`. Video is `unresolved`. All copies kept.
*   **Impact:** Fail-closed. No data loss, but potential failure to free space if the "attested" copy is in `run/sources/` and the delivery's own copy is in `sources/`.
*   **Fix:** The glob in `run_pass` should include `run/sources/*` or the target definition in `purge.json` should be updated. Given `purge.json` is static, the code should handle both.

**5. `stats.py` and `live.json`**
`pipeline/ingest/stats.py` line 106: `out["purge"] = {"expiry_h": ..., "last_pass": last, ...}`.
*   `last` comes from `q.kv_get("purge_last")`.
*   `service.py` line 745: `self.q.kv_set("purge_last", json.dumps({...}))`.
*   The `rep` dict from `run_pass` includes `one_copy_per_delivery`.
*   `stats.py` does **not** expose `one_copy_per_delivery` details in `live.json`. It only shows `last_pass` (which contains the full `rep` if we look at `service.py` line 746-748: `json.dumps({... "deleted": rep["deleted"], "kept": rep["kept"], ...})`).
*   Wait, `service.py` line 746: `json.dumps({"at": ..., "freed_bytes": ..., "refused": ..., "deleted": ..., "kept": ..., "delivered_videos": ..., "seconds": ...})`.
*   It **omits** `one_copy_per_delivery` from the `kv` record.
*   **Impact:** The live status does not show the A19 metrics (kept copies, unresolved videos). This is a visibility gap.

### SECTION 2: LAW COMPLIANCE

*   **L-j / L-m (Fail Closed):**
    *   `purge.py` line 389: `if problems: rep["refused"] = ...; return rep`.
    *   `purge.py` line 274: `unresolved.setdefault(v, ...)`.
    *   `purge.py` line 462: `if vid in unresolved: keep(...)`.
    *   **Compliant.** If the delivered set is unreadable or a copy cannot be identified, nothing is deleted.
*   **L-u (Exclusions):**
    *   The purge respects `FORBIDDEN` paths (line 449).
    *   **Compliant.**
*   **L-x (No Single Model):**
    *   Not applicable to purge logic.
*   **Attribution Law (A19):**
    *   The code attempts to implement "One Copy Per Delivery".
    *   **Partial Compliance:** Due to the `run/sources` glob miss (Section 1.4), it may fail to identify the correct copy in some layouts, defaulting to "keep all". This is safe but not fully compliant with the *intent* of freeing space.

### SECTION 3: SECURITY

*   **Path Traversal:**
    *   `purge.py` line 449: `if not rp.startswith(unit_real) ...`.
    *   `unit_real` is `os.path.realpath(unit) + os.sep`.
    *   `rp` is `os.path.realpath(p)`.
    *   This prevents deleting files outside the unit.
    *   **Compliant.**
*   **Symlinks:**
    *   `purge.py` line 445: `if not stat.S_ISREG(st.st_mode): keep(...)`.
    *   `purge.py` line 410: `if os.path.islink(unit) ... continue`.
    *   **Compliant.** Symlinks are never followed or deleted.
*   **Secrets:**
    *   No secrets in `purge.py`.
    *   **Compliant.**

### SECTION 4: FRONTEND QUALITY

*   **N/A:** This is a backend service. The "frontend" is `live.json` and `STATE.md`.
*   **Visibility:** As noted in Section 1.5, `live.json` lacks A19 metrics. This is a quality gap for operators.

### SECTION 5: BACKEND QUALITY

*   **Error Handling:**
    *   `purge.py` line 247: `except OSError: return False` in `same()`.
    *   `purge.py` line 255: `except (OSError, ValueError): prov = None`.
    *   **Good.** Fail-closed.
*   **Performance:**
    *   `sha256_of` is cached.
    *   `glob` is used extensively. For large `runs/` directories, this can be slow.
    *   **Acceptable** for a 10-minute loop.
*   **Logging:**
    *   `service.py` line 751: `self.log(purge.summary(rep))`.
    *   `purge.py` line 537: `summary` includes A19 stats.
    *   **Good.**

### SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Missing `run/sources` in Target Collection:** A professional system would ensure all defined media locations are scanned for identity. The current code misses `run/sources` in the `copies` map, leading to unnecessary "unresolved" states.
2.  **Live Status Opacity:** Operators need to see *why* space wasn't freed. `live.json` should include `one_copy_per_delivery` stats (kept, unresolved, other_copies).
3.  **Global Cache Thread Safety:** While low risk, a `threading.Lock` around `_SHA` is standard practice for global mutable state in a threaded service.

### SECTION 7: SCORES

*   **Backend logic:** 85/100 (Robust fail-closed, but the `run/sources` gap is a logic hole).
*   **Frontend/UI:** 70/100 (Live status lacks A19 details).
*   **Error handling:** 95/100 (Excellent fail-closed behavior).
*   **Security:** 95/100 (Path traversal and symlink protection are solid).
*   **Performance:** 80/100 (Globbing and hashing are efficient enough, but double-parsing PROVENANCE is wasteful).
*   **Law compliance:** 90/100 (Fail-closed is respected, but A19 intent is partially missed due to the glob gap).
*   **World-class gap:** 75/100 (Missing observability and the glob gap).
*   **OVERALL:** 85/100

### SECTION 8: PRIORITY ACTION PLAN

**P1 HIGH | Fix `run/sources` glob in `run_pass` | `pipeline/ingest/purge.py:412` | The `copies` map misses files in `run/sources/`, causing valid attested copies to be marked "unresolved" and preventing space reclamation.**
*   *Fix:* Change the glob to include `run/sources/*` or iterate over both `sources` and `run/sources` subdirs.

**P2 MEDIUM | Add A19 stats to `live.json` | `pipeline/ingest/service.py:746` | Operators cannot see the impact of the A19 ruling (kept vs. deleted vs. unresolved) in the live status.**
*   *Fix:* Include `rep["one_copy_per_delivery"]` in the `kv_set` payload.

**P3 LOW | Add lock to `_SHA` cache | `pipeline/ingest/purge.py:205` | Prevents redundant hash calculations in concurrent threads.**
*   *Fix:* Use a `threading.Lock` around `_SHA` access.

**P3 LOW | Cache `PROVENANCE.json` parse | `pipeline/ingest/purge.py:139, 253` | Avoids double I/O and parsing.**
*   *Fix:* Pass the parsed `prov` from `unit_videos` to `kept_copies`.

### SECTION 9: THE ONE THING

**Fix the `run/sources` glob gap in `purge.py` to ensure the "One Copy Per Delivery" logic can actually find and keep the attested file, preventing unnecessary "unresolved" states that block space reclamation.**

### SECTION 10: FINAL VERDICT

The code is **safe** and **fail-closed**, meaning it will not delete data it shouldn't. However, it is **not fully effective** at its primary goal (freeing space) due to the `run/sources` glob omission, which will cause many delivered videos to be marked "unresolved" and kept in full. This must be fixed before the feature can be considered production-ready for its intended purpose.