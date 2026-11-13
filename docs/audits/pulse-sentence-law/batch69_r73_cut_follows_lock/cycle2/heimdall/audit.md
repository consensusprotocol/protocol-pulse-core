# Heimdall audit

**Question:** Batch 69 CYCLE 2 (after cycle 1: every accepted_cut path is clamped into the ranges; the delivered test asserts ruling 73 on every cut) = RULING 73 (orchestrator 2026-11-13 '18:00'), verbatim: "THE CUT FOLLOWS THE LOCK'S WORDS. (a) OUT: the out point is never before the decoded END of the lock's LAST word. A pause inside the locked text is not a cut point, however long: the sentence law looks for the tail pause only AFTER the last locked word. (The hook ended on 'or' at a 130 ms pause before 'reissued'.) (b) IN: the in point is never more than 400 ms before the first locked word's onset (and never less than the head-lead rule requires: 80 ms, or the declared pad). Dead air before the first word is trimmed to that lead; if the audio in that lead is not quiet by the head rule, hold with that reason. (clip_01 opened 3.47 s before 'I'.) (c) Both are checked at the pin-stage pre-check service too (ruling 68 / 72), so the builder learns before the seal that a span cannot be cut to these rules. Must-fail tests: both of 13949b7c's spans fail on the old code and pass on the fix; the three delivered pins' cuts are unchanged by it (0c68b589, 41f29b1f, 37c5b5f5: same in / out to the frame, or say which moved and why)."
Background (measured on the real run pinned_20261113_221758):
- the hook's pause_out (26.99-27.12) lies inside the decoded last word 'reissued.' (26.66-27.54). boundary() searches the quiet run between the two words' MIDPOINTS (a guard for Whisper's off edges), and the hesitation run's end (27.12) just crosses the midpoint (27.10).
- clip_01's decode has a 4.58 s hole before 'I' (14.44). The IN pause found is a 60 ms dip at 10.96, so the clip opens on 3.47 s of non-speech (the second recogniser hears no words; Whisper hallucinates 'thank you').
The change (pipeline/sentence_law.py, pipeline/lock_precheck.py):
- boundary(..., tail=False): with tail=True (only the edge after a lock's last word) the pause is searched from words[k]['end'] to the next word's midpoint. A run inside the last word cannot be chosen; a run crossing the decoded end still can.
- edge_plan calls boundary(sa, words, i1, tail=True), then _ruling73(bin_, bout, words, i0, i1), which narrows the legal ranges:
  - OUT cut_lo >= words[i1]['end'];
  - IN cut_lo >= words[i0]['start'] - IN_LEAD_MAX_S (0.400). The cut is moved to start - LEAD_TARGET_S (0.25) when it was before the bound. A file head keeps its quiet up to the bound.
  - Not cuttable when the range empties, with a reason naming (ruling 73 a / b).
  - The head-lead rule is untouched: ruling 28's hook_lead (80 ms) and the D1 pad still run, now inside the narrowed range.
- accepted_cut: a cut placed at the boundary point (DEC-10 d valley / short gaps) is clamped into [cut_lo, cut_hi], so no path cuts outside the ranges. G16 (_edge_row) reads the same ranges.
- sentence_law.lock_cut(src, words, lock, label): write_lock_cut_table's per-segment body moved verbatim (edge_plan, accepted_cut, hook_lead for the hook, the trimmed onset rule). write_lock_cut_table calls it, and so does the pre-check (c): after ruling 17 / 72 a span whose lock stands is cut with it, and an error holds with "ruling 73: the render cannot cut this span: ...". RULES becomes "ruling 17 + ruling 72 + ruling 73".
MEASURED (the cut table recomputed with the old and the new code on the runs' own files):
- 13949b7c: hook OUT 27.09 -> 27.78 (after 'reissued.'s end); clip_01 IN 10.97 -> 14.04; clip_01 OUT +20 ms; clip_02 unchanged.
- 0c68b589: unchanged (its clip_01 OUT recomputes one 10 ms hop off with the OLD code too).
- Every OUT of every delivered pin: unchanged.
- ONE span moves IN: 'Bitcoin ... ever.' (41f29b1f's hook 14.38 -> 14.57; 37c5b5f5's clip_02 14.38 -> 14.69). It opened 0.56 s before its first word. It is also the protected medley reference's hook, so that reference's reproduction reports the changed decision (an orchestrator ruling is pending; not merged).
Tests:
- test_ruling73.py: _ruling73 unit tests (a, b, file head); the must-fail on 13949b7c's real run (fails on the old sentence_law, passes on the fix); the delivered pins' cuts unchanged but the named span (fails on the old code because the named span did not move).
- test_lock_precheck.py: a span the render cannot cut holds before the seal; a passing span records the render's cut.
- 32 passed.
FIND: a path that can still cut outside the narrowed ranges (OUT before the decoded end, IN more than 400 ms early); a behaviour change for spans the rule does not touch (the refactor of write_lock_cut_table must be verbatim); the head-lead rule weakened; a pre-check verdict that differs from the render's cut table for the same span; a test that does not test what it claims. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 4 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0047
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/sentence_law.py:383** _ruling73's IN branch can raise cut_lo above cut_hi for a non-file-head edge, making the range empty while cuttable stays True
  - evidence: `hi = max(bin_["cut_hi"], bound) if bin_.get("file_head") else bin_["cut_hi"]   # a file head keeps its quiet`
  - fix: For non-file-head edges too, widen: hi = max(bin_['cut_hi'], bound) (or set cuttable=False when hi < bound); as written, e.g. cut_lo=10.0, cut_hi=13.0, first word at 14.0 gives cut_lo=13.6 > cut_hi=13.0 with cuttable=True, so accepted_cut's clamp(x, cut_lo, cut_hi) returns 13.6 > cut_hi and the cut sits outside the recorded range.
  - raised by glm:F1; agree: qwen27b, glm

## Raised but not agreed
- qwen27b:F1 [high] The `hook_lead` function can move the `cut_in` to a value earlier than the `IN_LEAD_MAX_S` bound established by `_ruling73`, violating Ruling 73(b). (agree: 1)
- qwen27b:F2 [medium] In `_ruling73`, the `cut_hi` for the IN edge is not updated when the range is narrowed. If the original `cut_hi` was less than the new `bound` (e.g., due to a short gap), the `ok` check `hi >= bound` will fail, but the `cut_hi` remains the old value. More critically, if `file_head` is true, `hi` is set to `max(cut_hi, bound)`, but if `file_head` is false, `hi` is just `cut_hi`. If `cut_hi < bound`, the range is empty, which is correct, but the `cut` calculation `min(max(target, bound), hi)` might produce a value outside `[bound, hi]` if `hi < bound` (though `ok` would be false). The main issue is that `cut_hi` is not explicitly set to `hi` in the update, so it retains its old value, which might be inconsistent with the new `cut_lo` if the logic for `ok` is subtle. However, the most direct defect is that `hook_lead` (F1) bypasses this. (agree: 1)
- glm:F2 [low] The OUT branch clamps the cut into [end, cut_hi] but never moves cut_lo's companion check of cuttable when the range empties only via cut_lo>cut_hi... actually it does; the real gap: bout['cut'] is clamped to cut_hi even when cut_hi < end, silently recording a cut before the decoded end while cuttable=False (agree: 1)
- glm:F3 [low] The must-fail test's IN assertion also passes on the old code's behaviour for the OUT side only via the new clamp; but the IN test asserts cut_in <= start, which the old code satisfied too (10.97 <= 14.44), so the IN half of the must-fail relies solely on the >= bound check — fine — yet the delivered-pins test's MOVED expectation hard-codes 14.57/14.69, so if the bound computation (LEAD_TARGET_S) changes the test silently pins the old constant, not the ruling (agree: 1)

## Added in cross-examination (not voted on)
- glm: [medium] The pre-check's lock_cut call uses the role's label but the trimmed_leading/adjudicated lock fields may differ from what the render later uses, so a pre-check 'cut' verdict can differ from the final cut table for the same span
- glm: [low] boundary(tail=True) searches the pause from words[k]['end'] but boundary_geometry/point may still land inside the last word when the quiet run's end crosses the next word's midpoint (the 27.12 vs 27.10 case), so the chosen point can precede the decoded end even though the pause was found after it
- glm: [low] test_b_a_file_head_keeps_its_quiet_up_to_the_bound expects cut_hi=13.6=bound, i.e. the file-head branch sets hi=max(cut_hi,bound)=13.6 only because cut_hi(13.0)<bound; with cut_hi>bound the head keeps its wider range, which no unit test covers
