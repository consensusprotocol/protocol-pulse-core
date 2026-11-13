# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 17568 / out 1325 usd~0.121 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0530 (Ruling 33 part 2 at pin stage)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
   - GLM's P0-2 / F1 (kept words must still satisfy MIN_STATEMENT_TOKENS) and P0-8 / F2 (non-numeric start/end handling in trim_problems) were real gaps in my Cycle 1; the added guard at package.py:62-64 and the num() lambda at package_pin.py:162 are now present and tested.
   - GLM's P0-7 (generator used for membership) and P0-10 (trimmed word with no canonical token must fail closed) were missed; both are fixed (package.py:58 now does tok[0] in TRIM_WORDS; transcript_truth.py:278-280 explicitly sets ok=False).
   - The scorer_pending placement in stand_alone_check (package.py:30) and its interaction with an EDL that deliberately omits selection_lock (so trimmed_opener is never invoked at pin) was only partially surfaced in my prior pass.

2. WHERE DO YOU AGREE OR DISAGREE?
   - Agree with GLM on the original end-bound contract (P0-1) and with the consensus resolution: start is updated, duration_s is recomputed from the kept span, and the render contract is satisfied.
   - Agree with Grok on the surface-level tension between rate=None and r["ok"]=True, but disagree on it being a LAW violation; the diff intentionally builds an EDL without selection_lock so the pin-stage check uses the trimmed text's normal opener while still recording scorer_pending. This matches the "pending at render" carve-out.
   - Disagree with Qwen P0-1 and partially with its hook_onset concern: cleared contains the trimmed variant (moment_id ~trim, words=[w0+1,…], start=next word), hook_onset is measured on that variant, and trim_cut removes it at any place (package.py:109-112). The acoustic-onset rule is applied to the trimmed cut.
   - Agree with consensus on K5: the policy reading of item 42 ("use it now… pending at the render") remains the open question; the code faithfully implements the assumption given in the audit prompt.

3. NEW FINDINGS FROM THIS REVIEW
   - None at P0. One P2 (package.py:91): trims dict keys on original moment_id while the appended variant uses "<id>~trim". out["trimmed"] correctly maps original→variant and prescreen["trim_cut"] uses the ~trim mid, but any downstream consumer that only ever looked up by original id (not visible in diff) would miss the mapping. The Rig test and inventory() change (package.py:121) mitigate this inside the diff; uncertain about callers outside it.
   - transcript_truth.py:266-287 ordering is now robust (trimmed check before self_repair) and the no-canonical-token case fails closed as required. No behavioral change for untrimmed paths.

4. REVISED SCORES
   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | trim_variant / build() | P0      | P2      | MIN_STATEMENT_TOKENS guard + explicit canonical check added; inheritance bug fixed |
   | stand_alone / pin      | P0      | P1      | Scorer-pending mechanics clarified by consensus; matches orchestrator assumption |
   | transcript_truth edges | P1      | P2      | All new IN-rule paths for trimmed word now tested and fail-closed |
   | package_pin seal/to_pin| P1      | P2      | trim_problems now exception-safe; SEALED_LATER updated |

5. FINAL PRIORITY LIST
   - P1: pipeline/package.py:29-31 and stand_alone.py:232-233 — confirm with orchestrator that shipping a pin the render will refuse (scorer_pending + rate=None → trimmed_opener fail-closed) is acceptable per item 42. If not, the pin must block trimmed segments.
   - P2: pipeline/package.py:101 ("trimmed" map) and inventory() call site — ensure ~trim ids propagate to delivered/dup/rt_ok maps if those structures ever gate on moment_id (diff shows Rig test uses no_hook={"b~trim"}, but full call graph not visible).
   - P2: pipeline/transcript_truth.py:278 — the "has no canonical token" failure is correctly fail-closed but produces a slightly different error shape than other IN failures; render must handle it.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   The explicit scorer_pending list combined with an EDL that omits selection_lock is the linchpin: it lets (a) and (c) be enforced at pin while faithfully deferring (b) to render, exactly as the audit prompt's assumption requires.

7. PRODUCTION READY?
   Yes with conditions. Conditions: (1) orchestrator must explicitly accept "pending at the render" for trimmed segments (the current design ships pins the render will reject at validate); (2) any downstream code that keys solely on original moment_id must be proven to consult out["trimmed"] or the ~trim variant (or the mapping must be widened). With those two confirmations the diff satisfies Ruling 33, the render contract, all standing laws (L-m, L-j, never change what a check accepts), and every test added in this cycle.

**P0 findings**
None in the fixed diff.

**P1 findings**
- pipeline/package.py:29-31 (stand_alone_check) + stand_alone.py:205-209 (trimmed_opener): when rate=None the pin records scorer_pending but returns ok=True; render with selection_lock will hit the fail-closed path. Matches the stated assumption but collides with "pin must never seal what render would refuse" unless item 42 explicitly carves it out.

**P2 findings**
- pipeline/package.py:91 (trims dict) + 101 (out["trimmed"]): mapping original→~trim id is recorded, but any map keyed only by parent moment_id (delivered, fails, etc.) could silently drop the variant. Test coverage exists inside the diff; uncertain outside it.

SHIP: yes with conditions