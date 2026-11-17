# qwen3.8-27b (qwen/qwen3.8-27b) 126 s finish=stop usage in 8032 / out 6843 usd_reported=0.005253 usd~0.127 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
## Feature: pp-selectid-20261117_1305 | RULING 107 (1) — two gaps in the "nothing new" guard

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Gemma-4-31B-IT:** Nothing I would have missed. Her analysis of the atomicity of `list.append` under the GIL, the set-difference logic, and the "refused-before-API-hit" cost model is accurate and complete. She correctly identified that a build stopped by money costs $0.00 and produces no reply, so the retry is free until the budget resets.

**Qwen3.8-27B:** Two findings worth acknowledging:

- **[P2] Unbounded retry loop (spend limit never resets):** I initially would have flagged this more strongly. Qwen's trace is correct: a build that *starts* (passes `start_refused`) but then refuses mid-build writes a FINGERPRINT with `open_work > 0`, guaranteeing the next build runs, which will refuse again, and so on. However, the consensus ruling is correct that this is **by design** — the day's stop resets at 21:10 ET, builds are paced by the watcher (30-minute fallback), and each retry costs $0.00 (refusal precedes the API call). I now agree this is not a defect but a documented operational characteristic.

- **[P2] Untested `main()` wiring:** I would have noted this but perhaps not as sharply. The single line `money = list(router.spend_refused)` → `open_work(res, sp, money)` at :767-:773 is the only path from the router's in-memory list to the FINGERPRINT.json. A typo (e.g., passing `res` where `money` is expected, or omitting the argument) would silently drop all refusal counts. The 6-of-7 mutation kill rate confirms this is the surviving mutation. The risk is low (one line, visible in the next build's log), but it is the single point of failure in the entire fix.

**What I would have caught that they didn't:** Backward/forward compatibility of the FINGERPRINT.json schema. The new `"spend_refused"` key is additive. Older code reading a newer FINGERPRINT ignores unknown keys. Newer code reading an older FINGERPRINT (no `spend_refused` key) still sees the correct `open_work` value (0, which was the old "nothing left" semantics). No migration needed. Neither model explicitly addressed this.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | My Verdict | Reasoning |
|---|---|---|---|
| No P0/P1/P2 defects | Gemma | **Agree** | The mechanism is correct. I traced every path independently and found no escape or false-positive. |
| [P2] Unbounded retry loop | Qwen | **Agree it's real, disagree it's a defect** | By design. Daily reset at 21:10 ET. Each retry costs $0.00. The watcher paces builds. A max-consecutive-refused counter would be a nice-to-have but is out of scope for this ruling. |
| [P2] Untested main() wiring | Qwen | **Agree, severity P2** | Disclosed. One line. The next build's log line and FINGERPRINT.json are the integration test. A 10-line mock test would close the gap but is not a blocker. |
| [P3] GIL dependency for `list.append` | Qwen | **Agree, P3** | Correct for CPython 3.12. A comment would help future readers. Not a code change. |
| [P3] Nested `.get()` chain | Qwen | **Agree, P3** | Cosmetic. Every level defaults to `{}`. The test at line 152 (`{"never_empty": {"stage": "2a"}}` → 0) confirms the chain handles partial structures. |
| [P3] Backend names, not call identities | Qwen | **Agree, P3** | By design. The count drives the retry; the names are diagnostic evidence in FINGERPRINT.json. |
| Set difference correctness | Both | **Agree** | I verified all four test cases by hand. The soft pass re-runs step A on the same pool, so its holds are a superset of the clean pass's. The set difference correctly isolates the new holds. |
| No double-payment | Both | **Agree** | `Router.call` reads the reply record before any reservation. Replayed calls cost $0. Refused calls never hit the API. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] FINGERPRINT.json schema is additive-only — no migration risk.**
The new `"spend_refused"` key at line 70 is purely additive. The "nothing new" guard (proof_ledger.py:207, :219) reads `open_work` from the JSON, not `spend_refused`. Older builds that wrote FINGERPRINT.json without the key are still readable. No version bump or migration script needed. Neither Cycle 1 model stated this explicitly.

**[P3] The `money` local variable is a safe snapshot.**
At line 65, `money = list(router.spend_refused)` creates a new list. The subsequent `json.dump` and `say()` use `money`, not the router's live list. Even if (impossibly) another thread appended to `router.spend_refused` after this line, the FINGERPRINT would be consistent. The build's worker pools are joined before `main()` reaches :767, so this is belt-and-suspenders.

**[P3] The `say()` log line at :72-73 is the de facto integration test.**
The format string `f" ({len(money)} of them paid call(s) the spend stop refused)"` will appear in the build log only if `money` is non-empty. If the wiring at :766-767 is broken (e.g., `money` is always `[]`), the log line will say "0 item(s) left undone" with no parenthetical, and the FINGERPRINT will show `"spend_refused": []`. An operator watching the log will notice the discrepancy with the known $0.00 stop. This is not a unit test, but it is a visible signal.

**No new P0, P1, or P2 findings.**

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `pipeline/providers.py` (Router.spend_refused, _reserve → _reserve_capped) | Clean | Clean | No change. The refactor is minimal: old body moved verbatim into `_reserve_capped`, new `try/except SpendLimit` wrapper in `_reserve`. Free/uncapped early return preserved. |
| `proof_ledger.py` (open_work, main wiring) | Clean | Clean | No change. The set difference is correct. The `refused` parameter handles `None`, `()`, and lists. The main() wiring is one line, disclosed as untested. |
| `test_ledger_router.py` (new test class) | Clean | Clean | No change. Uses the real `PLG.build_router`. Covers free, refused, answered, replayed, and unreadable-ledger paths. Verifies `x.calls == 0` for refusals. |
| `test_ruling_107_guard.py` (new test method) | Clean | Clean | No change. Covers all `refused` edge cases and all four soft-pass set-difference scenarios. |
| FINGERPRINT.json schema | Not assessed | Clean | Additive key. No migration risk. Backward-compatible. |
| Thread safety | Clean | Clean | No change. GIL-atomic for CPython 3.12. Snapshot via `list()` in main(). |

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. **[P2]** `tests/package/proof_ledger.py:767-773` — The `main()` wiring (`money = list(router.spend_refused)` → `open_work(res, sp, money)`) is not unit-tested. A typo here silently drops all refusal counts. *Mitigation:* The next build's log line and FINGERPRINT.json are the integration check. *Recommendation (non-blocking):* Add a 10-line test with `unittest.mock.patch` on `json.dump` that asserts the FINGERPRINT contains `"open_work": 1` and `"spend_refused": ["xai:g"]` when the router has one refusal.

**P3 NITS:**
1. **[P3]** `pipeline/providers.py:9` — Add a comment: `# CPython GIL: list.append is atomic; revisit if free-threaded (3.13+ --disable-gil)`.
2. **[P3]** `proof_ledger.py:50` — The 5-level `.get()` chain is correct but fragile to read. A two-line helper (`def _soft_holds(res): ...`) would improve maintainability. Not a defect.
3. **[P3]** `proof_ledger.py:70` — `spend_refused` in FINGERPRINT.json records backend names with duplicates (one per refusal). For debugging, `(backend, role)` tuples would be more actionable. By design: only the count drives the retry.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `except SpendLimit` wrapper in `_reserve` (providers.py:18-22) is the entire fix in one place: it converts a silent "nothing new" skip into a loud "work left undone" signal, and every downstream consumer (open_work, FINGERPRINT.json, the next build's retry) flows from that single `append`.

---

## 7. PRODUCTION READY?

**Yes.**

Conditions (all satisfied or explicitly accepted):
- The two gaps (money refusals, soft-pass holds) are closed. No refusal escapes the count; no non-money failure is counted.
- No double-payment: replayed calls are free; refused calls never hit the API.
- No infinite loop: the daily spend reset at 21:10 ET bounds the retry cycle; each retry costs $0.00.
- Thread safety: `list.append` is atomic under CPython 3.12's GIL; the `main()` snapshot via `list()` is safe.
- Set difference: verified by hand and by four test cases.
- 6 of 7 mutations killed. The surviving mutation (main() wiring) is disclosed, one line, and observable in the next build's log.
- FINGERPRINT.json schema change is additive; no migration required.

The one P2 (untested main() wiring) is a known, disclosed, low-risk gap that does not block shipping. It should be closed in the next test pass.

---

P1_OR_WORSE: 0