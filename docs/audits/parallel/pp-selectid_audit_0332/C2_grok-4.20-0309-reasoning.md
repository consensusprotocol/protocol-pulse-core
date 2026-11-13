# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 51 s finish=stop usage in 18391 / out 1205 usd~0.122 (upper-bound price)

**P0: None verifiable from the fixed diff.**  
**P1: None.** All Cycle 1 P1 items (risk mangling, marker-edge measurement, caption cache, 20 s limit alignment) are resolved by the explicit TypeError, new tests exercising edges/None/markers, `LB.SNAP_MAX_S == PK.SEG_MAX_S` assertion, and consensus-verified L-v2 hard gate.  
**P2-1: ledger_build.py:75** — lazy `import vo_fidelity as VF` inside `snap_risk` (kept from C1). Works but hides the dependency; a future VF change could surface only on snapped rows.  
**P2-2: tests/package/funnel.py:248-253 & 170** — regex parser for new "snapped outward..." messages and hardcoded `sys.path` + `INGEST_ROOT`. Offline-only test tooling; breaks silently if error strings are edited.  

**SHIP: yes with conditions** (lazy-import moved to top; funnel regex pinned to a constant).

---

**CYCLE 2 REVIEW**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   GLM's P1-1 (non-list `risk` becoming mangled keys/characters via `list(risk or [])`) was not in my Cycle 1 notes; the explicit `isinstance` guard + `TypeError` (now tested) is the right fix. GLM also flagged the caption-cache sha key vs. possible store drift (P1-3); I had only noted the `None` return path. Qwen/Grok correctly highlighted that the new funnel tools are pure read-only analysis (no mutation, replay=True), which I had not examined. The consensus table (K1–K4) surfaced the L-v2 blocking-gate verification (`transcript_truth.verify_segment` + `REQUIRED_GATES`) that I had not pulled in Cycle 1.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - GLM P1-1 / consensus K4: fully agree — now fixed, pre-existing bug made explicit.  
   - GLM P1-2 (asymmetric 1.0 s marker window): agree the design is declared; disagree it remains P1 — new test at 529 explicitly exercises edge (`a+0.5`, `b-0.5`, `None`, raw `">>"`) and L-v2 is confirmed blocking.  
   - GLM P1-4 (20 s measurement): agree on word-clock consistency; the new test `test_the_snap_limit_is_the_packagers_clip_limit` and `> SNAP_MAX_S` message close the gap.  
   - Qwen on `startswith(tuple)` and `lstrip()`: disagree this is even P2 — standard library behavior, matches `pp-ingest` contract, and `">>>"` still fails closed (kept per consensus).  
   - Grok's "exact per ruling" and "SHIP: yes": agree after fixes.  
   - Consensus K3 (L-v2 hard gate): agree — `turn_change_inside is False` is required for `ok`.

3. **NEW FINDINGS FROM THIS REVIEW**  
   Only the two P2 items above. No new P0/P1. The removal of `SNAP_GUARD` is safe: every added word is now inside the span judged by L-s (`context_integrity`), exclusion_verdict (hard L-u risks on full moment text), L-v2 (numbers/negations both ways + speaker), and `usable()`. `snap_risk` cannot remove flags (only appends). Non-anchoring rows still produce `report["not_anchored"]` and are dropped. Dedup-by-time-overlap, window path, and verbatim `E.Span` + `E.spoken` are untouched. `marker_inside` correctly treats edge/None/no-cap as "no measurement" (L-m) and defers to L-v2.

4. **REVISED SCORES**  
   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | reanchor + snap logic  | P1      | P2      | Risk guard, limit test, L-v2 verification, and edge-case tests added |
   | snap_risk              | P1      | P0      | TypeError now prevents silent mangling; price logic matches ruling |
   | marker_inside + edges  | P1      | P2      | Tests cover 0.5 s / edge / None; consensus confirms L-v2 blocks |
   | funnel tools + tests   | P2      | P2      | New offline analysis strengthens auditability; minor maintainability notes remain |

5. **FINAL PRIORITY LIST**  
   **P0 CRITICAL:** None.  
   **P1 HIGH:** None.  
   **P2 MEDIUM:**  
   - pipeline/ledger_build.py:75 — move `import vo_fidelity` to top-level.  
   - tests/package/funnel.py:170,248 — extract regex to constant or tie it to the error string defined in `reanchor`.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   Replacing brittle `SNAP_GUARD` negation detection with full downstream gates on the *complete* verbatim sentence span (while adding a hard 20 s + interior-speaker-marker check) eliminates an entire class of "words the ledger never saw" while preserving fail-closed behavior.

7. **PRODUCTION READY?**  
   **Yes with conditions:** (a) move the lazy `vo_fidelity` import to module level, (b) pin the funnel regex to a constant shared with the error message so the offline table cannot silently desync. With those two trivial changes the diff is ready to ship.