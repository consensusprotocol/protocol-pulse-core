# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 36971 / out 1314 usd~0.218 (upper-bound price)

**CYCLE 2 CODE AUDIT — pp-selectid-0108B (Package B)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I reported “P0/P1/P2: none verifiable from diff” and SHIP yes. I completely missed: (a) the would_seal_under_grok edge case when all shadows are missing or unreadable (glm P1, qwen P1-2 — “nothing was verified: None, never True”); (b) the still-stale inline comment in the new hook_ratings except block that still says “(it was one re-ask of the same model)”; (c) replay85.decide()’s legacy contract tolerance for pre-ruling-61 Grok recordings (glm B3) and the compare() step-A “both fail (different rules) == agree” logic that could mask a lost REFERENT_OUTSIDE; (d) the manual router.down.pop + sleep(30) on 429 in replay85.one() and its interaction with the spend ledger and resumability. The Cycle 1 consensus correctly identified these; the fixed diff addresses the would_seal logic, the docstring, and adds explicit comments, but not everything.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- GLM B1 (kind kwarg silently dropped on old Router): agree it was a merge-risk; the rebased diff now passes kind="step_a_first"/"step_a_second" and updates every call site and test helper — fixed.  
- GLM B3 (replay85.decide legacy tolerance for clips_alone/coherence): agree the parsers diverge from production _strict/parse closures; the diff keeps the disclosed legacy path (“both before ruling 61”) and the ruling-88(b) hook numbers use the strict parser — acceptable but still a P2 documentation/maintenance smell.  
- Qwen P1-1 (429 handling bypasses backoff/spend cap): partially agree — the pop/sleep is a measurement-tool workaround; the refuted part (SpendLimit is still raised and ledger-protected) holds, but a persistent 429 can still cause repeated 30 s sleeps with no progress marker, which I missed.  
- Qwen P1-2 / GLM on would_seal: fully agree; the new logic (`None if not texts or (missing and not on_pin)`) plus the explicit comment citing “audit 0108 C1 (glm)” is the right conservative fix.  
- Qwen P2 stale comment & regex: agree the docstring was updated but the inline comment at pipeline/package.py:279 still references the old re-ask behavior.  
Overall the consensus findings were accurate; the rebased diff resolved the P0/P1 blockers.

3. **NEW FINDINGS FROM THIS REVIEW**  
Combined analysis plus the rebased diff reveals two minor residual issues:  
- **P2: pipeline/package.py:279** — the except comment still reads `# (it was one re-ask of the same model)` even though the docstring (lines 227-229) and the call_parsed usage now correctly describe “moves on to the next model”. Concrete scenario: a maintainer reading only the except block gets the wrong mental model of attempt count.  
- **P2: tests/package/replay85.py:570-581** — the legacy “hook” key tolerance and regex `re.findall(r'"(clip_\d+)": 1\b', prompt)` are still present and exercised only on old recordings. The TABLE.md agreement percentages for clips_alone/coherence therefore use a looser contract than production parsers; this is disclosed but not isolated to a “legacy-replay-only” code path. No functional impact on routing (hook path is strict), but inflates historical numbers.  
No new P0 or P1; outages still produce measured=False, parse funcs are verbatim extractions, call_parsed except blocks are exhaustive, shadow never marks clean on missing/unreadable, and spotlight pin_texts coverage was mechanically merged.

4. **REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2          | Why changed |
|------------------------|---------|------------------|-------------|
| Verdict call sites (call_parsed migration, kind, bounds) | P2 none | P2 none          | Fixes + mechanical rebase fully address prior concerns; parse funcs identical |
| Shadow report (would_seal, streak, pin_texts) | P1 none | P2 minor comment | would_seal=None edge case fixed per consensus; spotlight coverage added |
| Replay driver (decide, compare, TABLE.md, 429 handling) | P1 none | P2 (legacy tolerance + stale comment) | Missed these in Cycle 1; now visible but non-blocking after fixes |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL**: none.  
**P1 HIGH**: none.  
**P2 MEDIUM**:  
- pipeline/package.py:279 — remove or update the inline comment that still says “one re-ask of the same model”.  
- tests/package/replay85.py:570-581 — either isolate legacy contract handling behind an explicit “replay_legacy” flag or add a comment that the TABLE.md percentages for clips_alone/coherence are not directly comparable to production contract.  
- (optional) replay85.one(): after N consecutive 429s, write an explicit error row instead of returning None so the resume logic cannot spin forever on a permanently rate-limited model.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The systematic replacement of raw router.call + inline JSON/contract checks with providers.call_parsed (plus the extracted parse closures and kind= routing) enforces the “out-of-contract moves to next model, outage is never a verdict” rule uniformly while preserving every existing except-clause outcome.

7. **PRODUCTION READY?**  
**Yes with conditions**. Conditions: (1) clean the remaining stale comment at pipeline/package.py:279, (2) run replay85.py end-to-end once (or confirm the proof/TABLE.md 884-row artifact matches the new parsers), (3) verify that a build with routing=heimdall_first produces a SHADOW86.md that correctly shows would_seal=None when shadows are absent. These are documentation and verification items only — no safety invariants are violated.  

**SHIP: yes with conditions**