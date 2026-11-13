# Heimdall audit

**Question:** Batch 46 = THE APPROVED L-y MEDLEY AS A PROTECTED REFERENCE AND REGRESSION FIXTURE (orchestrator note 2026-11-12 '23:35'; PBX on the medley: "yooo!!!!! YES!!!!"). The run is copied read-only to references/pulse_medley_2026-11-12/, with SHA256SUMS over every file. check_reference_manifest.py, already audited in batch 41, verifies those bytes. It is a reference for SHAPE (law L-y: hook, then the clips back to back, ONE closing VO line after the last clip, the sign-off; no intro, no bridge), for clip-to-clip FLOW and for LAYOUT. It is NOT a reference for recency, caption, title or takeaway wording.
New pipeline/check_medley_reference.py, the "re-render to the same shape" fixture in the spirit of Law 22, reproduces the decisions with the CURRENT code on the reference's frozen files, without the renderer:
- shape: edl_rules.rule_r11 on its EDL; pinned.moments_vo on its PIN gives the same VO slots (intro present or not, each line's after_clip);
- selection: pinned.validate_range gives i0 / i1;
- cut: sentence_law.write_lock_cut_table, on a scratch copy of the EDL with linked sources / transcripts, is within 10 ms;
- flow: head_tail lead-in / tail is within 10 ms of TRANSITIONS.json, and pulse_transitions.plan gives the junctions each render log printed (here [] = hard cuts);
- layout: vertical_layout.classify gives the classes and boundaries.
Exit codes: 0 = reproduced, 1 = changed, 2 = missing. pipeline/regression.sh step 8 runs: the manifest check, the tag ref-pulse-medley-2026-11-12, git diff against the tag, then this check; any failure exits 1.
The tests make a scratch copy (small files copied, media linked) and change one decision each.
FIND:
- any way a changed decision passes, e.g. a comparison that is vacuous, compares a value with itself, zips silently, or swallows an exception into a pass;
- the junction comparison accepting a log line it did not parse;
- the scratch copy or the temp dir writing into the read-only reference;
- the shell step not failing when it should;
- tests that do not test what they claim.
Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0032
## Consensus findings (majority of panel agrees)
- **[high] pipeline/check_medley_reference.py:95** The junction comparison is vacuous when the render log line is absent: the regex is not anchored to a specific transition type, and if it fails to match, `want` is set to None and the check `got != want` compares the real plan output against None. This does not verify the log; it only fails if the log is missing. More critically, the regex `r"Transitions \(\w+\): (\[.*\])"` uses a greedy `.*` that, combined with `re.search` (first match), can capture across multiple lines or mismatch the intended transition block, and the test only asserts the literal string `Transitions (crossfade): []` exists once — so a log that contains a different, unparsed transition line would be silently ignored while the crossfade line is parsed, letting a changed decision pass.
  - evidence: `m = re.search(r"Transitions \(\w+\): (\[.*\])", f.read())
        want = ast.literal_eval(m.group(1)) if m else None
        if got != want:`
  - fix: Anchor the regex to the exact transition type the plan uses (e.g. `Transitions \(crossfade\): (\[.*?\])` with non-greedy match and re.MULTILINE), require exactly one match, and fail (append to bad) if the expected line is missing rather than comparing against None.
  - raised by qwen27b:F1; agree: qwen27b, glm
- **[medium] pipeline/check_medley_reference.py:~78** The junction comparison accepts a log line it did not parse: if the regex finds no 'Transitions (...)' line, want becomes None and the comparison proceeds; got != None then reports a change, but if plan also returns [] and the log line is absent/misnamed, got==None is False so it fails — actually the real defect: when m is None, want=None and got (a list, even []) != None, so a missing/unrenamed log line is reported as a changed decision rather than a parse failure, masking a fixture problem as a regression. Also, if the log line's kind differs only in spelling the regex \w+ silently matches, so a log printed with a different kind word is still compared.
  - evidence: `m = re.search(r"Transitions (\w+): (\[.*\])", f.read())
        want = ast.literal_eval(m.group(1)) if m else None
        if got != want:`
  - fix: Distinguish 'log line not found' (exit 2 / explicit error) from 'junctions changed'; require the expected kind word in the regex.
  - raised by glm:F1; agree: qwen27b, glm
- **[low] pipeline/check_medley_reference.py:~66** The cut-table loop iterates only over what write_lock_cut_table returns; if it silently returns fewer rows (e.g. a clip errors out and is omitted), the missing clip's cut is never compared — a changed/absent cut decision passes. The set(cuts) check earlier only validates the reference's own cuts_final.json, not the freshly computed table.
  - evidence: `for c in L.write_lock_cut_table(tmp):
            want = cuts[c["clip_id"]]`
  - fix: Compare the set of clip_ids returned by write_lock_cut_table against sorted(cuts) and report any missing clip.
  - raised by glm:F2; agree: qwen27b, glm

## Raised but not agreed
- qwen27b:F2 [high] The scratch copy symlinks the read-only reference's `sources` and `transcripts` directories into the temp dir, but `write_lock_cut_table` is documented to run on a scratch copy of the EDL with linked sources. If `write_lock_cut_table` (or any helper it calls) writes to or mutates any file under those symlinked directories, it writes directly into the protected read-only reference, violating the 'never touch the reference' invariant. The code performs no check that the reference is read-only and no copy-on-write for the linked dirs. (agree: 1)
- qwen27b:F3 [medium] `test_a_changed_layout_fails` only mutates the `hook` entry in VERTICAL_LAYOUT.json and runs with layout=True, but the check iterates over every clip in VERTICAL_LAYOUT.json. The test claims to verify a changed layout fails, yet it only changes one clip's class to 'single' — if `classify` for the hook happens to still produce 'single' (or if the hook is not in the reference's VERTICAL_LAYOUT.json), the test passes vacuously. The test does not assert that the mutation actually differs from the reference's stored value before running the check. (agree: 0)
- glm:F3 [low] The test edits cuts_final.json (the reference side) rather than the EDL/inputs, so it only proves the comparison notices a changed want; it does not test that a genuinely changed cut decision (from the EDL/sources) fails. Similarly test_a_changed_lead_in_fails edits TRANSITIONS.json, which is both the compared value and the input to TR.plan, so the junction comparison in that test compares plan output against the edited reference — partially self-fulfilling. (agree: 0)

## Added in cross-examination (not voted on)
- glm: [medium] The selection-lock loop zips segs with pin['segments'] after only checking lengths, but the earlier guard compares len(segs) to len(pin['segments']) — however the labels are never cross-checked against ps['video_id'] uniqueness or against the EDL clip order; if PIN segments are reordered (same length), the zip silently pairs each EDL segment with the wrong PIN segment (wrong video_id/transcript), and validate_range may still succeed, producing a pass with mismatched pairing. The 'never a silent zip' comment is only half-true: length is checked, order/identity is not.
- glm: [low] The lead/tail loop iterates tr['lead_tail'] (the reference's own TRANSITIONS.json) and computes head_tail from qa/final_<cid>.mp4; if the reference's lead_tail dict is missing a clip that exists in the EDL, that clip's lead-in/tail is silently never checked — the loop is driven by the reference file, not by the EDL's clip list, so a dropped entry shrinks the check rather than failing it.
- glm: [low] The layout comparison rounds both sides to 2 decimals, so a boundary drift of up to ~0.005s (5ms) per shot boundary passes; more importantly, if VERTICAL_LAYOUT.json's hook entry is missing, the loop simply skips it (dict iteration), so a dropped layout decision passes — same reference-driven-iteration weakness as the lead_tail loop, and the rounding hides sub-5ms boundary changes that the 10ms tolerance elsewhere would not.
