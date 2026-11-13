# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 72 s finish=stop usage in 28495 / out 1386 usd~0.177 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I completely missed the original accounting bug (package.py:113 only incrementing calls/cached when measured=True, so unmeasured attempts vanished from the “asked” total — Qwen P0-1 / GLM P0-2). I also missed that the pre-fix cache key omitted prompt/sheet parameters (visual_pin.py:512, now fixed via C1 consensus), the stale-sheet risk when TILES/EVERY_S changed without a VERSION bump, and the bare-except shape on both sheet and verdict paths (visual_pin.py:676,693 — Grok P2). The router’s vision/text skip logic and XAIVisionBackend’s explicit text rejection were only partially covered in my prior pass; the concrete test in test_visual_pin.py:977–983 that a text-only backend is never called for a vision prompt was not highlighted by me.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- Fully agree with Qwen P0-1 / GLM P0-2 on the accounting defect and with the C1 consensus fix (now every non-cached attempt is counted; the log line is truthful).  
- Fully agree with Qwen P0-2 / GLM P1-5 on the original cache-key fragility; the added digest of [PROMPT, TILES, EVERY_S, TILE_W, FORMAT, text] plus on-disk sha256 check (visual_pin.py:665–668, 672–673) eliminates the stale-verdict risk.  
- Agree with Grok P2 on the broad `except Exception` (still present at 676 and 693); it can mask OOM or disk-full as “not measured”.  
- Partially agree with GLM P0-1 on “sealed() can carry measured=False”: the shape exists (sealed() copies whatever keys are present), but the fixed code never reaches a write or gate-PASS with an unmeasured visual (package.py:153–156, 175–182, 209–215, inventory row). The independent computation risk is real but today guarded.  
- Disagree with Qwen P0-3 (router chain): the consensus correctly refutes it — all listed back-ends now have vision=True and the skip logic is symmetric and tested.  
- Agree with all refuted items (R1–R4) and the recorded G1–G2; they match the diff.

**3. NEW FINDINGS FROM THIS REVIEW**  
**P2: pipeline/visual_pin.py:676 and :693** — Bare `except Exception as e: # noqa: BLE001` (both sheet path and verdict retry). Concrete scenario: disk full while saving the contact sheet (OSError subclass) or KeyboardInterrupt during PIL paste is swallowed and returned as measured=False with a generic why. The ruling requires fail-closed only for model/contract failures; unexpected environmental errors should propagate so the build aborts loudly. (Still present after C1.)  

**P2: pipeline/package.py:177** — `if vbad or segs[0].get("visual_hook_block")` only inspects the first segment for hook_block when deciding to reline/doom the entire line-up. If a later clip also fails visual, its why is lost in the logged record. Minor observability gap, not correctness.  

**P2: pipeline/visual_pin.py:623** — No cap on on_screen_text list length (or total flags). A contact sheet with 50 chyrons produces 50 flags sealed into the pin and gate row. Pin hash remains deterministic, but unbounded growth affects storage and PBX rendering. Matches GLM P1-2 but still unresolved.

No new P0 or P1; all critical paths (measured gate, hook block, seal subset, cache hit only on identical bytes, router vision guard, cost upper-bound, recording without image bytes) are now explicitly verified by the updated tests.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1     | Cycle 2     | Why changed |
|------------------------|-------------|-------------|-------------|
| Visual gate & sealing  | P0:1 P1:2   | P0:0 P1:0   | Cache-key + sheet-sha fix and explicit measured checks before any write/gate eliminated the independent-computation risk I originally rated P0. |
| Accounting & reporting | P0:1        | P2:0        | Consensus C2 fix makes call/cached/unmeasured numbers faithful; cost is reported on first build. |
| Cache & replay         | P0:1        | P0:0        | Digest of all judgment inputs plus on-disk sha256 check guarantees byte-identical re-render. |
| Router / vision prompt | P1:1        | P2:1        | is_vision, skip logic, XAIVision rejection, IMAGE_TOKENS_UPPER, and prompt_text sha256 are all exercised in test_visual_pin.py; only remaining broad-except is P2. |
| Exception handling     | (missed)    | P2:2        | Broad excepts now the dominant remaining defect after C1 fixes. |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL:** None verifiable from the diff.  
**P1 HIGH:** None verifiable from the diff.  
**P2 MEDIUM:**  
- pipeline/visual_pin.py:676,693 — narrow excepts to (OSError, ValueError, providers.ProviderError, json.JSONDecodeError, subprocess.TimeoutExpired).  
- pipeline/visual_pin.py:623 — add explicit cap (e.g. first 20 on_screen_text items) with a “truncated” flag.  
- pipeline/package.py:177 — log why for every visual failure, not only segs[0] hook_block.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Narrow the two bare `except Exception` clauses in visual_for (and propagate unexpected errors) so environmental failures cannot be silently treated as “not measured”.

**7. PRODUCTION READY?**  
Yes with conditions: address the three P2 items (primarily tightening the bare excepts at visual_pin.py:676 and :693) before merge. After those changes the visual gate satisfies every clause of RULING 70, K1–K4, fail-closed, one-canon, seal compatibility, and cost reporting.

**P0: None**  
**P1: None**  
**P2: visual_pin.py:676,693 (broad except); visual_pin.py:623 (uncapped flags); package.py:177 (partial why logging)**  
**SHIP: yes with conditions** (tighten excepts + cap flags)