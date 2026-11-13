# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 48 s finish=stop usage in 16590 / out 610 usd~0.098 (upper-bound price)

**P2: pipeline/sentence_law.py:196** (edge_plan) and **hook_onset.py:71**: when trimmed={"word": ...} is supplied, edge_plan routes to trimmed_boundary (lines 164-181) then trims the quiet_run interval (lines 206-208); trim_onset:31 then calls the render's accepted_cut + trimmed_onset (lines 35, 188) on the identical plan dict shape. Matches render usage exactly; the extra HO.MARGIN_MS frame (line 38) only makes the pin-stage onset test stricter.

**P2: pipeline/hook_onset.py:54-57, 92-96**: every trimmed path writes a "trim" dict; any exception, planning failure, or trim_onset failure forces measured=False or pass=False (never a pass, satisfying L-m / L-j / ruling 33(a)). Untrimmed call sites (trimmed=None or absent) execute the pre-existing boundary + lead-only path unchanged (lines 69, 85).

**P2: pipeline/package.py:129-133**: trim_cut only collects trimmed moments whose trim["pass"] is not True and removes them from cleared (out at any place); hook lead still gates "can open a medley". Matches ruling 33(a) exactly; non-trimmed moments and the old hook_onset["pass"] logic are untouched. The STAND_ALONE log line is only textual.

**P2: tests/package/test_hook_onset.py:397-420** (TestTrimmedCut): synthetic 16 kHz WAVs exercise trimmed_boundary (pause vs co-articulated), the k<0 / lexical / sentence-start guards, envelope "not measured" case, and confirm untrimmed path is identical. All four tests verify the render's own onset rule (with pin-stage margin) on the bytes that would be cut.

**P2: tests/package/test_medley.py:477-489** (TestRuling33TrimAtThePinStage): Rig.onset stub supplies realistic "trim" records; trimmed-cut failure excludes from angle_write (never offered); clean-trim + bad-lead stays as non-hook clip. Funnel.py:268-274 only affects reporting (mom() aliasing, no build logic change).

**P2: sentence_law.py:168** (trimmed_boundary k<0 case): returns valid=False ("not the word before the lock"). K1 assumption cannot be verified from this diff alone (no full-transcript eligibility code); render copy is byte-identical per audit note, so behavior is as-shipped by integrator at c6605895. No other divergence found.

No P0 or P1 findings; all required gates (plan, accepted_cut, onset on final cut audio, fail-closed paths, untrimmed invariance) are exercised by the diff and tests. The 05:48 build's two real trimmed moments are now measurable exactly as described.

**SHIP: yes**