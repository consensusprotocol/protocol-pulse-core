# pp-selectid audit 0338 (rulings 38 + 39: the IN edge's 4 s window, 700 ms pause and file head; canonical edge match): cycle 1 consensus

Synthesis by the pp-selectid session, 03:31 ET Nov 13, written before cycle 2.

**Run.** C1_STEP.diff covers transcript_truth.py and test_angles.py. No P0. Verdicts:
- grok: no P0 and no P1, "SHIP: yes";
- qwen: "yes with conditions";
- glm: "yes with conditions".

## Consensus (each verified from the code or the data, no code change needed)

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | The pause (b) and the file head (c) are measured on the recogniser's word timing alone. Speech it missed could pass (glm P1-3, qwen P1-3 / P2; both "condition, not blocker", both note the ruling's wording) | KEPT, as the ruling's measure. Ruling 38: "the independent recogniser must show a sentence end before the clip, or a measured pause of at least 700 ms with no speech". The pin stage's CUTTABLE judges SENTENCE boundaries with the independent recogniser. The acoustic check of every cut is the render's: cut acceptance (check_cut_acoustics) and G16 hold any cut not inside a measured pause. An acoustic confirmation of (b) at the pin stage is offered to the orchestrator in STATE. |
| K2 | self_repair at j = -1 could wrap to the last word (glm P2-3, its condition 1) | VERIFIED, no defect. self_repair starts with `if not 0 <= i < len(words) - 1: return False` (transcript_truth.py:138), so j = -1 is never a self-repair. |
| K3 | A caller passing wav= without wav_start, with a file cut with the old 1.5 s pad, would misalign (glm P2-4, its condition 2) | VERIFIED, no such caller. The only explicit-wav caller, tests/package/run_given_package.py:268, passes wav_start from covering_wav(); the tests pass it; package.truth_for uses audio_window(). main's pipeline does not import transcript_truth (grep). |
| K4 | Does canon treat a bare "%" or "$", and hyphen splits, safely (glm P2-1 / condition 3, qwen P1-1)? | VERIFIED. canon_tokens("% of their portfolio") = ['percent', 'of', 'their', 'portfolio'], so a bare "%" never matches a clip's "25"; "$ 5 million" = ['5000000', 'dollars']. canon does NOT merge "Bit- coin" (['bit', 'coin']). That is a false negative the old 4-letter rule shares, and no regression: the canonical match only ADDS a candidate, it never removes one. |

## Refuted or kept (with evidence)

- **glm P1-1 (a recognised word inside the gap could be skipped):** REFUTED with data. gap = the opening word's start minus the end of ws[j], with j = i - 1 (or the word before a self-repair). With the recogniser's words in time order, no recognised word lies between them. All 99 recorded transcriptions in tests/package/fixtures/replies have their words in time order (0 out of order).
- **glm P2-2 (the canonical OR widens the candidate set; ci[0] is the earliest):** KEPT. A false earlier candidate needs the same canonical token within 0.6 s before the clip's first word. The old 4-letter rule had the same selection rule.
- **glm P1-2 (the "window starts at the clip" test uses a synthetic wav_start):** KEPT. It is a unit test of edges(), whose wav_start can be any value; audio_window's clamp is tested separately.
- **qwen P2 items (comments, CANON_RUN = 6, empty cached files):** no change. CANON_RUN covers the longest spoken numbers seen ("one hundred twenty-five thousand", 4 words) with room.

## Verification

- test_angles 26 OK (20 existing, 6 new); test_hook_onset, test_medley, test_gates, test_ledger_build, test_speakers and test_providers OK on the change.
