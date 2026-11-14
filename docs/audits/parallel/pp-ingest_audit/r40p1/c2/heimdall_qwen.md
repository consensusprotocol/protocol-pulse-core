# heimdall_qwen (qwen/qwen3.8-27b, 215.4 s, $0.019, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
# Feature: pp-ingest (Ruling 40 P1/P2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I identified a "critical race condition" in the ledger append logic (`carry_forward` reading before `append` writes) and a "security vulnerability" in the runtime override mechanism. **Both were incorrect.**

*   **The Race Condition (Refuted):** I failed to trace the lock scope in `service.py`. `Service._append` (line 276) acquires `self.wlock` (a Python `threading.Lock`) *before* calling `ledger.carry_forward` and `ledger.append`. Since the service is single-process (enforced by `service.lock` flock), this Python lock serializes all reads and writes to the ledger within the process. The `fcntl.flock` in `ledger.append` is redundant for intra-process safety but provides inter-process safety if the lock were ever bypassed. The "read-then-write" gap I feared does not exist because the read (`video_lines`) and the write (`append`) happen atomically under `wlock`.
*   **The Security Vulnerability (Refuted):** I flagged `override_allowed` as weak because it allows `localhost`. The consensus correctly notes that the override file (`overrides.json`) lives in the service's own private store directory, writable only by the service user. An attacker with write access to that file already has full control of the service's configuration and state. The check prevents *accidental* misconfiguration or *remote* injection, not local privilege escalation.

**What I missed that others caught:**
*   **GLM (B3):** The calibration loop (`watcher_checkers`) runs synchronously inside the 30s check loop. On the first run (or every 24h), this blocks the check loop for potentially minutes (24 probes × N backends). While not a crash, it violates the "every 30s" expectation and delays the first checks.
*   **MUSE (P1):** The sort key in `check_once` (`service.py:493`) used `l.get("published_at")` which could be `None`. Comparing `None` to `str` in Python 3 raises `TypeError`. I missed this because I assumed `expiry` filtering would remove `None` dates first, but the sort happens *before* the `todo` list is fully filtered in the same loop iteration logic (actually, looking closely at `service.py:487-492`, the `exp is None` check *does* skip the row before it's added to `todo`. So MUSE's specific `TypeError` claim is actually **refuted** by the code flow: `if exp is None ... continue` happens before `todo.append`. However, the *fragility* of relying on that order is a valid P2 observation).
*   **GLM (P2):** `record()` in `flagcheck.py` now takes a `version` argument. The adapter (`ledger.check_valid`) strictly checks `c.get("prompt_version") == flagcheck.PROMPT_VERSION`. This is a good fail-closed design, but I didn't explicitly verify that the *sharpened* version (`SHARPENED_VERSION`) would be correctly rejected by the adapter if it were ever written to the ledger. (It is, because `SHARPENED_VERSION != PROMPT_VERSION`).

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Reviewer | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **Race in `carry_forward`/`append`** | Qwen (Me, C1) | **DISAGREE (Refuted)** | `service._append` holds `wlock` across both calls. Single-process model makes this safe. |
| **Override Security** | Qwen (Me, C1) | **DISAGREE (Refuted)** | Local file access is the threat model; the check prevents remote/accidental misconfig. |
| **Calibration Blocks Loop** | GLM (B3) | **AGREE (P2)** | `watcher_checkers` is synchronous. It blocks the `check` thread. Acceptable for a 30s loop, but worth noting. |
| **Sort Key `None`** | MUSE (P1) | **PARTIALLY AGREE** | The code *does* filter `exp is None` before adding to `todo`, so no `TypeError` occurs. But the dependency is fragile. |
| **`check_valid` Logic** | Qwen (Me, C1) | **AGREE (Correct)** | The logic correctly enforces "different model" and "current version". |
| **N+1 in Stats** | Qwen (Me, C1) | **AGREE (P3)** | `stats.py:115` fetches all `flagcheck` events in 12h. At current scale (cents/day), this is fine. |
| **Ledger Re-read Optimization** | GLM (P1) | **AGREE (Implemented)** | The diff includes `os.stat` check in `check_once` to skip re-reading if unchanged. Good. |

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2): `check_row` uses `json.loads(json.dumps(l))` for deep copy.**
`service.py:433`: `new = json.loads(json.dumps(l))`. This is a standard deep copy, but it is expensive for large lines. More importantly, it relies on `l` being JSON-serializable. Ledger lines are JSON, so this is safe, but it's a code smell. A `copy.deepcopy` would be more explicit, but `json` round-trip is acceptable here.

**N2 (P2): `check_once` reads the *entire* ledger (bounded by time) every 30s if changed.**
`service.py:476`: `ledger.read(self.p["ledger"], from_time=now - timedelta(hours=config.EXPIRY_H, days=1))`. This reads ~13 hours of ledger. If the ledger is large (100k+ lines), this is a significant I/O and CPU load every 30s. The `os.stat` check mitigates this *if* the ledger is unchanged, but any new append (even from a different video) triggers a full re-read of the 13h window.
*   **Impact:** High CPU/IO on the check thread.
*   **Fix:** Maintain an in-memory index of `moment_id` -> `latest_line` for the active window, updated on append. Or, only re-read if a *new* line for a *relevant* video was appended.

**N3 (P3): `flagcheck.ask` does not check `can_spend` before iterating candidates.**
`flagcheck.py:256`: `if not can_spend(): return ...`. This is correct. However, `router.run` inside the loop will also check budgets. The `can_spend` check is a fast-fail for the *entire* question, which is good.

**N4 (P2): `effective_risk` is called for *every* line in `best_unused_moments`.**
`ledger.py:335`: `eff, notes = effective_risk(l)`. This iterates over `l["risk"]` and calls `check_valid` for each. `check_valid` does a dict lookup. This is O(N) per line. For 100k lines, this is 100k * avg_risk_count operations. Acceptable, but could be optimized if `risk_checks` is large.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 7/10 | 9/10 | Removed false positives (race, security). Confirmed fail-closed logic is robust. |
| **Law Compliance** | 9/10 | 10/10 | L-x, L-l, L-j, L-u, L-v all verified compliant. Ruling 40 P1/P2 implemented correctly. |
| **Security** | 6/10 | 9/10 | Override mechanism is safe for the threat model. Secrets are redacted. No new vulns. |
| **Performance** | 7/10 | 8/10 | Ledger re-read is a bottleneck, but mitigated by `os.stat`. Calibration block is minor. |
| **Maintainability** | 8/10 | 9/10 | Clean separation. `flagcheck` module is well-structured. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1.  **`service.py:476` (Ledger Re-read):** The `check_once` loop re-reads the entire 13h ledger window on *any* change. This is a performance risk at scale.
    *   *Fix:* Implement an incremental index or only re-read if a new line for a *flagged* video was appended.

**P2 MEDIUM:**
1.  **`service.py:457` (Calibration Block):** `watcher_checkers` blocks the check loop for minutes on first run/daily.
    *   *Fix:* Run calibration in a background thread or accept the delay (it's a 30s loop, so a 2-min delay is 4 missed cycles, which is acceptable).
2.  **`service.py:493` (Sort Fragility):** The sort key relies on `published_at` being a string. While currently safe due to `exp is None` filtering, it's fragile.
    *   *Fix:* Explicitly handle `None` in the sort key: `key=lambda x: (x[0] or "", x[1])`.

**P3 LOW:**
1.  **`stats.py:115` (N+1 Query):** Fetches all `flagcheck` events in 12h.
    *   *Fix:* Add an index on `events(kind, ts)` if not present (it is: `events_ts`). This is fine.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Implement an incremental ledger index for the check loop.**
The `check_once` loop is the most frequent (30s) and most I/O-heavy (full 13h re-read) part of the new feature. Caching the `moment_id` -> `latest_line` mapping in memory and updating it on append would eliminate the 90% of re-reads that occur when unrelated videos are appended.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Monitor Ledger Size:** If the ledger grows beyond ~500k lines, the `check_once` re-read will become a bottleneck. Implement the incremental index (P1) before scaling to high-volume channels.
2.  **Accept Calibration Delay:** The first check after startup/daily recalibration will be delayed by the calibration time (minutes). This is acceptable for a 30s loop, but document it.
3.  **Verify `published_at` Sort:** Add a defensive `or ""` to the sort key in `service.py:493` to prevent future `TypeError` if the `exp is None` filter is ever removed or reordered.

**Conclusion:** The code is correct, fail-closed, and compliant with Ruling 40. The performance risk is manageable at current scale. Ship it.