# Heimdall audit

**Question:** pp-selectid, tonight's BY-HAND fixes that sealed the first video since Nov 13 (pin afd8977d143e). The diff also holds
ruling 156's plain fallback lines (fallback_fields / fallback_subject / LINE_ONLY_WRITES / the fb_state loop branch),
audited already (20261123_2143, two cycles, no open P0/P1). REVIEW THESE (all in the never-empty pass, `soft`):
(1) the line-up stage's `lost` set keeps a clip whose CUTTABLE failure is only a sentence edge at a word boundary
    (soft_edges(t)); any other cut failure, an exclusion or an L-v 2 failure still drops it.
(2) context_soft: a context-integrity failure whose EVERY violation is a step-A soft code (STEP_A_SOFT) on a CLIP
    segment flags as step A's (add_flags on the clip; cx ok, violations emptied); a code on our lines, a VO-caused
    code (NOT_ENTAILED / POLARITY / STRONGER), a hard code or an unmeasured verdict stay as before.
(3) step_a_sentence: ONE flag sentence for all of step A's soft codes on the package's clips (ruling 157 (2)(a)/(5)).
(4) FALLBACK_FLAG reworded + package_pin.OUR_LINES_KIND: the fallback row and the closing line's value row are ONE kind
    (ruling 157 (2)(b)); the value row's flag is the fallback sentence when the sealed takeaway is the fallback.
(5) fallback_vo_soft: when the sealed closing line IS the plain fallback, a coherence verdict failing ONLY on its
    VO-point rating passes; the through-line (sound), every clip rating at the floor, the hook's own bar and a measured
    verdict stay required.
(6) package_pin.flags_cap: a sealed kinds_cap row (status PASS, int cap above REVIEW_FLAGS_MAX up to KINDS_CAP_MAX 8,
    a reason) raises THAT package's cap; package.chain_cap follows the driver's KINDS_CAP; the inventory writes the row
    only when the driver set KINDS_CAP and its reason (ruling 157 (1): this one package; the standing cap stays 3).
The integrator's pin check imports package_pin.py live. Only report what the code shows; quote it.
PLEASE CHECK: can any of (1)-(6) let a HARD failure through (a cut mid-word, a lock hold, a VO-caused context failure,
a missing through-line, a clip under its floor), raise the cap without a sealed reason, or count two different kinds
as one?

**Panel:** qwen27b, gptoss, glm  |  **Cost:** $0.0218
## Consensus findings (majority of panel agrees)
- **[high] pipeline/package.py:630** context_soft uses `is False` to test the measured flag, so an unmeasured verdict (measured=None or key absent) is NOT caught by the guard. If such a verdict carries violations that all happen to be STEP_A_SOFT codes on clip segments without a slot, the function returns a non-None dict and the caller overwrites cx with ok=True, violations=[], silently converting a hard context-integrity failure into a soft flag. The sibling function fallback_vo_soft correctly uses `is not True` for the same semantic.
  - evidence: `if (cx or {}).get("measured") is False or not vs or not all(
        v.get("rule") in STEP_A_SOFT and v.get("segment") in labels and not v.get("slot") for v in vs):
    return None`
  - fix: Change `is False` to `is not True` so that a missing or None measured value is treated as unmeasured and the function returns None (stays as a hard failure), matching the pattern already used in fallback_vo_soft: `if c.get("measured") is not True or ...`.
  - raised by qwen27b:F1; agree: qwen27b, gptoss
- **[medium] pipeline/package.py:4897** When step_a_sentence returns None (no clip's codes intersect the four-entry STEP_A_PHRASE dict), the inventory still emits status FLAGGED with flags=[None]. The guard `soft_a and len(a_rows) >= 1` only guarantees that step A produced rows, not that every code in those rows has a phrase in STEP_A_PHRASE. A soft code present in STEP_A_SOFT but absent from STEP_A_PHRASE yields a None flag in a FLAGGED row, which downstream consumers (pin rendering, kind counting) will treat as a missing or crash-prone value.
  - evidence: `"flags": [step_a_sentence({lb: lab_codes[lb] for lb in (a_by or {})}, who)]`
  - fix: Guard the list: `"flags": [s] if (s := step_a_sentence(...)) else []`, or fall back to the old kind_sentences path when step_a_sentence returns None, so a FLAGGED row never carries a None entry.
  - raised by qwen27b:F2; agree: qwen27b, gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
