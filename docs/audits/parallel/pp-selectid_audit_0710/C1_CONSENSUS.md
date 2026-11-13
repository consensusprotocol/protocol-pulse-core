# pp-selectid audit 0710 (item 42's gap: the trimmed cut measured as the render measures it): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers sentence_law.py, hook_onset.py, package.py, funnel.py, test_hook_onset.py and
test_medley.py. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- glm: no P0, "SHIP: yes" (its P1s are notes it verifies as fail-closed itself);
- qwen: "SHIP: yes with conditions", with two "P0"s, both misreadings (K1, K2).

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | qwen P1-3 (its condition 2): the trim_cut comment "the hook lead decides only the hook" can be misread | it now says that the hook lead decides only whether a trimmed clip may OPEN the medley (hook_onset "pass", need_onset), never whether it may play as a clip. |
| F2 | qwen P2-6 (its condition 3): the passing test does not check the fade | the test asserts that the fade accepted_cut picked lies in law L-b's bounds (FADE_MIN_S 10 ms .. VALLEY_FADE_S 83 ms). |

## Misreadings (verified from the code)

| # | claim | the code |
|---|---|---|
| K1 | qwen "P0-1" (its condition 1): _cut_head, _head_tail_of and hook_lead_at are new, not the render's | They ARE the render's. `git show c6605895:pipeline/sentence_law.py` (the integrator's branch, combo-letterbox-quoteonly-v2) defines them at lines 718 (_cut_head), 730 (_head_tail_of) and 743 (hook_lead_at). The render's trimmed_onset calls hook_lead_at. An AST source comparison (ast.get_source_segment of each top-level def) found all seven names byte-identical to that file: TRIMMABLE_LEADING, trimmed_boundary, trimmed_onset, edge_plan, _cut_head, _head_tail_of, hook_lead_at. |
| K2 | qwen "P0-2": the pin stage measures the onset on the UNCUT source window, not on the audio as cut | trim_onset calls SL.trimmed_onset(sa.path, cut_in, fade_in_ms). Through hook_lead_at, that calls _cut_head(src, c, fade_ms): ffmpeg `-ss c` decodes FROM the cut, and the clip's linear fade-in is applied to the first fade_ms. The measure is the audio AS CUT, exactly the render's function. Only the file differs: the render's source mp4, the pin stage's L-v 2 window of the same video. Hence the one-frame margin. |
| K3 | qwen P1-5 / glm P1-2: when the trimmed plan is not reached, the synthesised "trim" record copies a "why" that is not about the trimmed cut | Every early return of _measure is ON the trimmed cut's path: "no source audio" / "the clip's words are not inside its audio window" (NOT MEASURED), "no cut plan: <exception>" (edge_plan with the trimmed word raised), and "no cut after the trimmed word 'So': <trimmed_boundary's reason>" (FAIL). Each names why the trimmed cut has no measure or no plan. No change. |
| K4 | glm P2-7: `trims` in the log line is not shown | build() defines it (item 42's change, 1d928276): `trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}`, the variants that JOIN. |
| K5 | glm P1-5's reasoning (K1 of the brief): "the token list is the full record's" | Not so: measure builds `words` from the tokens INSIDE the audio window (idx). So when the trimmed word is the window's first word, trimmed_boundary's sentence-start check is vacuous there, exactly as the brief states. glm's conclusion (the assumption is sufficient) stands for the brief's reason: eligibility verified the untrimmed sentence's start on the full word record, and the variant inherits that verdict. |

## Recorded, not changed

- glm P1-1 / qwen P0-2's spirit: the margin can only make the pin stage stricter (fail closed).
- glm P1-4: the trimmed edge reuses the render's shared reason "no room before the first word". These are the
  render's own strings, copied verbatim; changing them would diverge from the render.
- glm P2-3: _cut_head's fade endpoint (np.linspace(0, 1, k)) is the render's own measure. Whether the render's PREPARE
  fades the same way is the render's concern; the pin stage measures with the render's own measure.
- glm P2-1 / P2-2 / P2-5: report shapes (passed_lead, cut-relative onset_s, the variant's "under N" seconds), read
  nowhere in a build.

## Verification

- test_hook_onset 9 OK (4 new, on a generated audio file); test_medley 72 OK on this change alone (80 once
  rebased on 45 + 44, which is committed).
- The other suites are OK.
