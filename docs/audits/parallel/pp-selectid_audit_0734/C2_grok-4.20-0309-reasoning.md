# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 39 s finish=stop usage in 17913 / out 1404 usd~0.125 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0734**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   GLM's (d) on the double `nv_order()` call (pipeline/package.py:274 vs :176) and the closure variables (`cleared`, `doomed`, `held_map`) that *could* mutate between the in-loop decision and the later `no_voice()` call. I had not explicitly traced that the `break` exits the takeaway loop but that later bookkeeping (`t_refused`, `v_lost`, `last_fid` updates) and the outer `if v_novoice` path sit between the two sites. Grok's extraction note on `a_use(pk3)` → dict-comp also escaped my first pass; the diff alone does not define `a_use`. Qwen's doomed-clip test idea (now implemented) was absent from my Cycle 1.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - GLM (d): partially agree — the latent recomputation risk exists in the diff (closure state), but the added `test_a_doomed_clip_is_never_the_added_clip` plus mutation M21 killing all 16 variants makes it non-breaking. The in-loop `break` + identical arguments guarantee same return for all concrete test inputs.  
   - GLM (b)/Grok extraction: agree — `fixed_caption_gates` reconstructs exactly the `man`, `pk3["medley"]`, `a_by` dict, and `merge_fid` that the old `rewrite_alone` path used. Existing ruling-65 tests + M19 (drop fallback) kill the voiced path; behaviour preserved.  
   - GLM (c)/ (e): fully agree — lone-slot guard, `fixed_caption_gates` re-check, removed `no_voice_fits` (no other callers found in grep), and the replaced count tests are sufficient.  
   - Qwen "critical" on stale `dropped`/`doomed`: disagree — its own text correctly concludes the calls are deterministic with identical inputs; the test added in C2 kills the mutation.  
   - Grok's `added_clip` key and `by_id` vs `cleared`: agree these were un-obvious from diff alone; the C2 tests and `assemble_medley` copy now make the provenance clear.

3. **NEW FINDINGS FROM THIS REVIEW**  
   <medium> **pipeline/package.py:240 (the combined cheap/fid/cx guard after first cheap check)**: concrete input — a no-voice line-up whose *first* `cheap_checks` returns a single RUNTIME violation on the caption slot *and* a clip-exclusion failure (so `paid_gates` never runs). The early `if cheap and lone_slot(cheap) != "caption"` is bypassed (lone caption), but the later `if cheap or not fid["ok"] or not cx["ok"]` sees `cheap` truthy, `cx` never bound, and `lone_slot(cheap + fid["violations"])` cannot be evaluated. Current code would NameError or treat unbound `cx` as falsy, skipping the fixed-caption path that (C) requires. (The test suite never hits a clip-gate failure *after* a lone-caption cheap failure.)  
   <medium> **tests/package/test_medley.py:399 (contexts_pass stub)**: the lambda hard-codes `"measured": True` but the real `CI.check_contexts` can return measured=False on replay. The fixed-caption test that expects a context failure (test_c_the_fixed_caption_still_passes_its_own_gates_or_the_line_up_ends) overrides the stub but leaves the ruling-3 path test using the measured=True version, leaving one edge unexercised.

4. **REVISED SCORES**  
   | Subsystem                  | Cycle 1     | Cycle 2          | Why changed |
   |----------------------------|-------------|------------------|-------------|
   | nv_order / ruling-91 path  | 2 mediums   | 1 medium         | GLM (d) + new guard bug raised visibility; doomed test lowered severity |
   | fixed_caption_gates extraction | 1 medium | 2 mediums        | New NameError scenario on cheap+clip-gate combo; extraction itself still clean |
   | Test coverage & mutations  | 0           | 0                | Added tests kill all listed mutations; no change |
   | Overall risk               | medium      | medium           | One new latent crash path, but narrow |

5. **FINAL PRIORITY LIST**  
   **P1 HIGH** — pipeline/package.py:240: add `cx is not None and cx["ok"]` (or restructure to always bind `fid, cx` before the guard) so a cheap lone-caption + later clip gate failure still reaches `fixed_caption_gates`.  
   **P2 MEDIUM** — pipeline/package.py:240 and tests/package/test_medley.py:399: extend `contexts_pass` to also test measured=False and add a Rig case that produces cheap caption violation *plus* an excluded clip after the first cheap check.  
   **P2 MEDIUM** — pipeline/package.py:128 and :274: capture the *exact* `nv_plan` dict from the in-loop call and pass it to `no_voice(..., plan=nv_plan)` instead of recomputing; eliminates the closure-variable divergence entirely.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   Make the in-loop `nv_plan` object the single source of truth passed through to `no_voice` (and reuse its `order`/`added`/`why_not` fields) so the decision and execution can never diverge and the guard at line 240 can be simplified.

7. **PRODUCTION READY?**  
   Yes with conditions: (a) fix the unbound-`cx` path at pipeline/package.py:240 so lone-caption cheap failures cannot be masked by later clip-gate failures, (b) extend the context stub and add the combined cheap+clip-gate test, (c) adopt the plan-object reuse suggested above. With those three changes the diff implements (A) and (C) exactly, all attacks are closed, and every mutation is killed.

**Findings**  
<medium> pipeline/package.py:240 — cheap lone-caption + subsequent clip-exclusion failure reaches `if cheap or not fid["ok"] or not cx["ok"]` with `cx` unbound → NameError or wrong `why_not`; fixed-caption path (C) bypassed.  
<medium> tests/package/test_medley.py:399 — stub always forces measured=True; the measured=False case for fixed-caption context failure is untested on the ruling-3 path.  

SHIP: yes with conditions