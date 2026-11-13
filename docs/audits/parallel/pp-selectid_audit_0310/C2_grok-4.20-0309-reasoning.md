# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 24 s finish=stop usage in 12558 / out 1151 usd~0.092 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**
In my Cycle 1 I completely missed the `out["usable"]` / `n_usable` restoration (glm P2-2 / consensus K4) and the fact that `inventory()` evidence rows are now exercised by `test_inventory_writes_a_FAIL_row_with_its_evidence`. I also did not notice that `stand_alone.py` is byte-identical at 5be6f301 (consensus K1) nor that `package_pin.to_pin` forces label="bitcoin" for every moments pin, which legitimizes the hardcoded subject. Those were blind spots; the Cycle 1 consensus and the FIXED diff made them obvious.

**2. WHERE DO YOU AGREE OR DISAGREE?**
- GLM P1-1 / Qwen P1-1 (EDL shape + hardcoded subject): partially agree on the original risk; now **agree** it is VERIFIED. The FIXED diff's docstring, the byte-identical module, the `get("channel_name")`/`get("duration_s")` defensive keys, and the pinned-verdict test close the loop. The subject is intentionally fixed and documented.
- GLM P1-3 (unguarded `r['opener']['why']`): agree it was a legitimate concern in the first diff; the new test and `stand.get("rows") or []` plus the guarantee from `stand_alone.check_edl` that every row always has both dicts make the crash path impossible.
- Qwen P1-2/P1-3 and GLM P1-2 (stricter-than-render behavior): **agree** it is intentional and lawful. The governing laws explicitly allow additive stricter pre-filters and require fail-closed (L-j, "never seal a lineup the render would hold"). The pronoun-hook test and "fails closed" docstrings now make the trade-off explicit.
- Grok's "no P1, SHIP yes": agree on the final outcome but it was too optimistic in Cycle 1; the evidence-row test and usable-count fix were still missing then.
- Qwen P2 items (parseable rows, dense comment, Rig helper, log coupling): agree they are stylistic; all but the comment have been left as-is (human evidence is acceptable per consensus) and the comment was split.

**3. NEW FINDINGS FROM THIS REVIEW**
- `stand_alone_check` builds an EDL that supplies `channel` and `duration_s` (lines 20-21) even though the docstring correctly states they are ignored with `rate=None`. This is harmless but unnecessary; the render's real EDL shape may differ on missing keys.
- The two `lineup_for(..., need_stand_alone=True)` call sites (lines 98-102) duplicate the `need_onset=True` pattern; if a future signature change adds another flag the duplication becomes a maintenance foot-gun (P2).
- `no_role_on_screen` imports `stand_alone` on every call (line 30). Because the module is pure Python this is cheap, but it is the third import-inside-function in the file and slightly violates "smallest diff" purity.
- Test `test_build_leaves_no_role_moments_out_before_the_angle_and_seals_the_row` still relies on an opaque `Rig` helper whose definition is outside the diff; auditability is reduced but not broken.

All are P2 at worst; none violate the standing laws.

**4. REVISED SCORES**
| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|----------------------------|---------|---------|-------------|
| Render fidelity (EDL/subject) | P1     | P0     | Consensus K1 + byte-identical confirmation + pinned verdicts + explicit docstring on bitcoin label |
| no_role / usable semantics | P2     | P2     | Fix for n_usable is correct but the semantic change remains (still acceptable) |
| Gate row & inventory       | P1     | P0     | FAIL-row test added; guarded access confirmed |
| Test coverage & regression | P2     | P1     | New dedicated TestStandAloneAtThePinStage is excellent; minor opacity around Rig remains |
| Overall risk               | Low    | Very Low | All Cycle-1 P1s resolved; stricter-is-safe principle upheld |

**5. FINAL PRIORITY LIST**
**P0 CRITICAL:** None.
**P1 HIGH:** None.
**P2 MEDIUM:**
- pipeline/package.py:20-21 — unnecessary channel/duration keys in EDL (cosmetic).
- pipeline/package.py:98-102 — duplicated `need_stand_alone=True` call sites.
- pipeline/package.py:30 — third import-inside-function; consider hoisting if style allows.
- tests/package/test_medley.py:234 — Rig helper not shown in diff.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**
The stand-alone gate plus the no_role pre-filter (with restored usable count and explicit FAIL-row test) is the highest-leverage change: it enforces the render's exact STAND_ALONE check at pin time without GPU, never lets a bad lineup reach the integrator, and satisfies "nothing measured is never a PASS" while remaining strictly fail-closed.

**7. PRODUCTION READY?**
Yes. The Cycle-1 P1 concerns have been addressed, the new tests pin the render's exact verdicts on the held pin, the stricter filter complies with all listed laws, and the gate prevents any lineup the render would reject. No conditions.