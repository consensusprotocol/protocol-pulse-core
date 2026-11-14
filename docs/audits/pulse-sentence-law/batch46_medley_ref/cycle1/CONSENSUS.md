# Batch 46 cycle 1: consensus and what was done

Implemented:
- C1 [high] and C2 [medium], the junction parse: the render log must hold exactly ONE line
  `^\s*Transitions \(<style>\): [...]$`, with the run's style word, matched with re.M. A missing or duplicated line, a
  different style, or a list that does not parse is reported as CHANGED with that reason. It is never compared as
  None.
- C3 [low]: the cut table's rows must equal the reference's rows; a row the table omits is CHANGED.
- glm, added in cross-examination (medium), "never a silent zip" was only half true: each PIN segment is paired with
  its EDL segment by video_id. A reordered PIN is CHANGED (test_reordered_pin_segments_are_never_paired_by_position).
- glm, cross-examination (low), loops driven by the reference: lead-in / tail is checked for every EDL segment, and
  TRANSITIONS.json must cover exactly the EDL's segments with the EDL's channels. pulse_transitions.plan now takes
  its channels from the EDL, not from the reference. The layout reference must cover exactly the EDL's segments.
- qwen F3 (0 votes), vacuous tests: every must-fail test now asserts the CHANGED reason it causes, not only exit 1.
  New tests: a dropped lead-in entry, a render log without its Transitions line, reordered PIN segments.

Not implemented, with reasons:
- qwen F2 [high, 1 vote], writes through the linked sources / transcripts. The reference is read-only: files are
  0444, directories 0555, and the owner is not root. A write through the links raises PermissionError, which exits 1
  (fail closed). write_lock_cut_table writes only <tmp>/cuts_final.json. After every test run the reference still
  passes check_reference_manifest (200 files identical, none added).
- glm F3 [low, 0 votes], the tests edit the "want" side. The comparison is symmetric: a code change moves the
  recomputed side, a test moves the reference side, and both produce the same difference. The lead-in test is not
  self-fulfilling: plan() uses the RECOMPUTED lead-in / tail and the EDL's channels, never the edited file.
- glm, cross-examination (low), rounding layout boundaries to 0.01 s. Shot boundaries are frame times, 1/30 s =
  33 ms apart, so no real boundary change is under 5 ms. This is the same comparison as check_preview_reference
  (regression step 6).
