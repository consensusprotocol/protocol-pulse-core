# C1 CONSENSUS — pp-selectid audit 20261115_1554 (RULING 116 Q3: the calibrated line-up bar)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0; its "[P1]" headings are the QUESTION's checks, each verified); glm-5.3-flash
FAILED (RemoteDisconnected: no answer), so the driver asked Grok (0). Cycle 1: $0.0477 vendor-reported. No P1.

qwen verified each check: the floors only for the calibrated rater's verdicts (floors_for), every site that judges the
line-up ratings excludes the hook's slot and reads the verdict's own floors (medley, coherence, last_clip_only, the
ruling-63 reorder, the two weak-clip sets, the takeaway-only rewrite), the file's floors from the source, the mark
outside the seal.

ACTED ON:
- qwen [P2] "the takeaway-only rewrite names the hook's label as the string 'hook'": it now reads the package's own
  first segment label (pk["segments"][0]["label"]), as every other site reads labs[0]. Tests pass (225); mutation L8 (the
  hook's rating back inside that min) re-aimed at the new text and KILLED after a control run.

NOT CHANGED:
- Grok [P2] "the timestamp checks duplicate hook_bar's": kept side by side on purpose (each file's refusal names its
  own calibration); both are tested the same way.
- Grok [P2] "the file carries the approved runs in full (through-lines, story ids)": they are its source, as the hook
  file carries its approved hooks; the live-file test derives the floors from proof/clips116 on every run, so a hand
  edit or a stale copy fails it. A new prompt version needs a new measurement either way (the floors are only valid
  for the question they were measured under).
- Grok [P3] (wording, the two patching styles in the two-bar tests, a namedtuple): noted.
- qwen [P2] "STANDARD_LINEUP / valid_h / the rig": as designed and tested (the standard bar is COHERENCE_MIN for every
  part; valid_h null and its refusals are hook_bar's rule; the rig now answers as production does).
