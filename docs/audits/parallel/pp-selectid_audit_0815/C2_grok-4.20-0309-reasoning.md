# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 32 s finish=stop usage in 9198 / out 920 usd~0.069 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0815 (Ruling 52)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
Grok’s P1 on integral floats (type(x) is not int) was missed in my Cycle 1; the contract has always been that strict for clips and is now uniformly applied to hook parts. GLM’s concern about the unseen tail of the `ok=` line and the exact placement of the derivation relative to the try/except was also missed; the full diff now shows the derivation runs only after contract validation and that `min(v["clips"].values())` occurs after the hook rating is injected. Qwen and the Claude consensus correctly highlighted that the sealed medley row and all downstream readers use `.get()` or explicit whitelists, so the new top-level `hook`/`hook_rule` keys are inert; I had flagged that as a potential shape-break.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- Grok P1 (float): fully agree — consistent with prior contract, fails-closed, outside scope of Ruling 52.  
- GLM P1-1/P1-3 (ok tail, derivation outside try): agree; the provided C2 diff resolves both.  
- GLM P1-2 (verdict keys): agree with consensus that no strict-shape reader exists.  
- All three on K1 (min derivation): agree; min is the chosen formula, documented in HOOK_RULE, and tests assert “every part must reach the bar”.  
- Qwen’s “SHIP: yes” and Claude’s resolution of all prior points: agree. No material disagreements.

3. **NEW FINDINGS FROM THIS REVIEW**  
None at P0/P1. One P2: pipeline/package.py:67 now demands `set(v) == {"through_line", "hook", "clips", "joins"}` exactly. The test suite exercises every missing/extra/malformed case, but the error path does not distinguish “extra top-level key” from “missing hook parts”; both become the generic “measured=False, rejected”. This is acceptable but reduces debuggability for future prompt drift.

4. **REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Prompt & JSON template | P2      | None    | Full diff + new test explicitly verify new wording, removed hook through-line rating, and correct clip_keys |
| Contract validation    | P1      | P2      | Derivation now visibly post-validation; float check shown to be pre-existing; all malformed cases in test_out_of_contract_is_not_measured_and_rejected |
| Derivation & pass rule | P1      | None    | `min(...)` injection into `v["clips"]["hook"]` occurs before `ok=` line (now visible); tests assert derived 3 → FAIL and 4 → PASS |
| Downstream compatibility | P1    | None    | Consensus + code confirm `.get()` usage everywhere; sealed row never sees extra keys |
| Test coverage          | P2      | None    | reply() helper, new ruling-52 test, updated out-of-contract cases give 100 % coverage of the new contract |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL:** None.  
**P1 HIGH:** None.  
**P2 MEDIUM:**  
- pipeline/package.py:67 — consider a more specific error message when extra top-level keys appear (aids future prompt maintenance).  
- pipeline/package.py:78 & test_medley.py:140 — the HOOK_RULE string is duplicated between constant and test assertion; a single source of truth would be cleaner.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Injecting the derived `min()` hook rating into `verdict["clips"]["hook"]` *after* strict contract validation but *before* the unchanged `min(v["clips"].values())` pass rule, so the hook can no longer pass/fail on a through-line score.

7. **PRODUCTION READY?**  
Yes. All Cycle 1 P1 items are resolved by the C2 diff, the test suite (82 OK) exercises the new contract, derivation, prompt text, and failure modes, downstream readers are unaffected, and the implementation matches Ruling 52 (including chosen K1 min formula) exactly. No further changes required.