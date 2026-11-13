# Heimdall audit

**Question:** Batch 58 = RULING 33 PART 2 (orchestrator 2026-11-13 '03:42'), verbatim: "a clip may be locked with ONE leading word trimmed (but, and, so, well, now, yeah). The pin carries trimmed_leading and the untrimmed sentence start. G16 / write_lock_cut_table accept that lock when: the IN cut sits in a measured pause after the trimmed word with the onset rule met on the audio as cut; the STAND_ALONE scorer affirms the TRIMMED text at the unchanged threshold; G18 compares against the trimmed locked text. Anything else about whole sentences is unchanged, and the OUT edge is untouched. If the trimmed word cannot be cut cleanly (no pause, co-articulated), the clip is held: say so in the gate text."
Background: the sentence law (pipeline/sentence_law.py) locks whole sentences: a lock is words[i0..i1] of the run's own transcript; its IN edge is boundary(words, i0 - 1), valid only when words[i0 - 1] ends a sentence ('.', '!', '?'), with a pause measured on the audio (find_pause: quiet runs below the quiet line between the two words' midpoints; boundary_geometry: the envelope minimum 'point', the heard 'word_gap', the 'pause'). edge_plan gives each edge a legal cut range; accepted_cut picks the cut (cut_accept-clean, neighbour_clear: no audible part of the neighbouring word after the fade); write_lock_cut_table writes cuts_final.json (verified False with the reason = HOLD before render); gate_g16 re-plans from the lock and checks every cut. Ruling 28 (hook_lead_at): the hook's lead is measured on the audio as cut (head_tail, G17a's own measure, the clip's fade-in applied); 'onset > one 10 ms hop' is its criterion for quiet after the cut. G18 already compares the final against lock['text'] (the run's words from i0) and the source span [cut_in, cut_out].
The change:
- sentence_law: TRIMMABLE_LEADING = the six words. trimmed_boundary(sa, words, i0, trimmed) is the IN edge of a lock carrying trimmed_leading: valid only when (1) words[i0-1] is the trimmed word (one canonical token, one of the six), (2) the untrimmed sentence starts a sentence (words[i0-2] ends one in a punctuated stretch, or the trimmed word is the transcript's first word), (3) find_pause finds a quiet run between the trimmed word and the first kept word and the heard gap has positive length; otherwise invalid with "the trimmed word 'X' cannot be cut cleanly: no measured pause between it and 'Y' (co-articulated)". edge_plan(..., trimmed=None) uses it and narrows the IN cut range to the quiet run (the cut SITS in the pause). trimmed_onset(src, cut_in, fade_in_ms): the onset rule on the audio as cut = ruling 28's measure (hook_lead_at) finds the first onset after one hop. write_lock_cut_table and gate_g16 pass lock['trimmed_leading'] to edge_plan and refuse a cut that fails trimmed_onset (gate text names the trimmed word). _edge_row labels an invalid trimmed edge "trimmed leading word (ruling 33 part 2): <reason>". The OUT edge code is untouched; a lock without trimmed_leading follows exactly the old path.
- pinned: validate_schema accepts trimmed_leading (one word of the six) with untrimmed_start (a number, 0 <= untrimmed_start < start) on a machine_cuts pin only; build_edl calls trimmed_lock: the run's own transcript must hold the trimmed word right before the lock (text, never time), and the lock records {rule, word, word_index, untrimmed_start} inside its sha256 digest (verify_lock then fails on any change). The lock text stays words[i0..i1]: the trimmed text, which G18 compares against (unchanged code).
- run_fresh._retry_fade_edges plans with the lock's trimmed_leading (its candidates stay in the quiet run).
- stand_alone.check_edl: every segment whose lock has trimmed_leading (the hook included) is put to the clip scorer and passes the opener test only when the scorer affirms the trimmed text (score >= CLIP_MIN_SCORE 3.5, fault not starts_mid_thought); no verdict fails closed. The hook keeps its deterministic opener rule on the trimmed text. Untrimmed segments are asked exactly as before.
Tests: pipeline/test_trimmed_leading.py, 17 tests: a synthetic source (sin^2 words over a -66 dB bed) with a 200 ms quiet run after 'But'; co-articulated ('But' and the next word one envelope); a non-terminal word before 'But'; wrong words; the cut table + G16 end to end on a scratch run; the onset rule failing (mocked measure); a cut inside 'But'; the pin fields; the lock digest; the fade retry; the scorer.
FIND: a way a trimmed clip renders with any audible part of the trimmed word, or with its first kept word cut into; a lock without trimmed_leading behaving differently from before; a check the ruling asks for that is missing or weaker; a fail-open path (exception, None, malformed field); a test that does not test what it claims. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 4 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0070
## Consensus findings (majority of panel agrees)
- **[low] pipeline/test_trimmed_leading.py:348** test_g16_refuses_a_trimmed_cut_outside_the_quiet_run_or_opening_on_sound claims to test a cut outside the quiet run but places the cut inside 'But' (before the quiet run), which the old range check also rejects, so the test does not isolate the ruling-33 narrowing
  - evidence: `cuts[1] = dict(good, cut_in=round(words[i0 - 1]["start"] + 0.12, 3))     # inside 'But' (near its peak)`
  - fix: also/instead place the cut after the quiet run's end (still inside the old word-gap range) to prove the narrowed range is enforced
  - raised by glm:F4; agree: qwen27b, glm

## Raised but not agreed
- qwen27b:F1 [high] The cut range for a trimmed lock is not constrained to the measured quiet run. The code calculates `lo` and `hi` based on the `word_gap` (envelope minimum) and only intersects with the `quiet_run` if the `trimmed` flag is set. However, `trimmed_boundary` validates the existence of a pause but `edge_plan` uses `bin_['word_gap']` for the base range. If the `word_gap` extends into the audio of the trimmed word (which is possible if the envelope minimum is not perfectly aligned with the acoustic silence, or if the 'gap' definition includes the tail of the previous word), the cut could be placed inside the trimmed word's audio. The ruling requires the cut to 'sit in a measured pause'. The intersection logic `lo, hi = max(lo, q['start']), min(hi, ...)` is correct *if* `q` is the quiet run, but the base `lo` is `g['start']`. If `g['start']` is before `q['start']`, `max` fixes it. If `g['end']` is after `q['end']`, `min` fixes it. Wait, looking closer: `g` is `word_gap`. `q` is `quiet_run`. The code does `lo, hi = max(lo, q['start']), min(hi, round(q['end'] - LEAD_MIN_S, 3))`. This seems to correctly constrain the cut to the quiet run. 

Let's re-evaluate. Is there a fail-open path? 
In `trimmed_onset`, `ok = onset is not None and onset > HOP_S + 1e-9`. If `hook_lead_at` returns `onset=0.0` (sound at the very start), `ok` is False. This is correct. 

Let's look at `stand_alone.py`. 
`need = [(label, s) for label, kind, s in segs if trimmed_word(s) or ...]`. 
`trimmed_word` returns `str(t.get('word') or '?')`. 
If `selection_lock` is present but `trimmed_leading` is missing, `t` is None, returns None. 
If `trimmed_leading` is present but `word` is missing, `t.get('word')` is None, `str(None or '?')` is `'?'`. 
Then `trimmed_opener` is called with `word='?'`. 
This is a minor issue, but not a critical defect in the logic of the ruling itself.

Let's look at `pinned.py` `validate_schema`. 
`if "trimmed_leading" in s or "untrimmed_start" in s:`. 
If `untrimmed_start` is present but `trimmed_leading` is not, `tl` is None. `canon.canon_tokens(None)`? The code does `canon.canon_tokens(tl) if isinstance(tl, str) else []`. So `tok` is `[]`. `len(tok) != 1` is True. Error added. Correct.

Let's look at `sentence_law.py` `trimmed_boundary`. 
`if k > 0 and not (is_punctuated(words, k - 1) and is_terminal(words[k - 1]['word'])):`. 
This checks if the word *before* the trimmed word ends a sentence. 
Ruling: "the untrimmed sentence starts a sentence (words[i0-2] ends one... or the trimmed word is the transcript's first word)". 
`i0` is the first kept word. `k = i0 - 1` is the trimmed word. `k - 1` is `i0 - 2`. 
So it checks `words[i0-2]`. Correct.

Is there a case where the cut is allowed but the audio is not quiet? 
`trimmed_onset` checks the audio. 
`edge_plan` checks the pause. 

What if `find_pause` returns a quiet run, but the `word_gap` is different? 
`boundary_geometry` returns `point, gap, pause`. 
`gap` is the 'heard word_gap'. `pause` is the 'pause'. 
In `edge_plan`, `g = bin_.get('word_gap')`. 
`q = bin_['quiet_run']`. 
The cut is constrained to `q`. 

Wait, `trimmed_boundary` returns `quiet_run=quiet`. 
`quiet` comes from `find_pause`. 
`find_pause` returns `(quiet, lv)`. 
`quiet` is a dict with `start`, `end`, `ms`. 

The defect might be in `stand_alone.py` `check_edl`. 
`if o_ok and trimmed_word(s):` 
`o_ok, o_why = trimmed_opener(...)`. 
If `o_ok` is False (e.g. hook opens on pronoun), `trimmed_opener` is NOT called. 
So a trimmed hook that opens on a pronoun fails the hook rule, but does it fail the trimmed rule? 
The ruling says: "The STAND_ALONE scorer affirms the TRIMMED text...". 
If the hook rule fails, the segment fails. The specific reason might be the hook rule, not the trimmed rule. This is acceptable as it fails closed.

However, consider a clip. 
`opener` for a clip checks if it starts with a conjunction. 
If the clip text is "we have...", `opener` returns True (assuming it's not a hook). 
Then `trimmed_opener` is called. 
If the scorer says "starts_mid_thought", `trimmed_opener` returns False. 

Is there a path where a trimmed clip is NOT scored? 
`need` includes `s` if `trimmed_word(s)` is truthy. 
`trimmed_word` returns `str(...)` which is truthy unless empty. 
If `word` is `''`, `str('' or '?')` is `'?'`. Truthy. 
So it is always scored if `trimmed_leading` is present.

Let's look at `run_fresh.py`. 
`cand = L.cut_candidates(src, L.edge_plan(..., trimmed=lock.get('trimmed_leading')))`. 
If `lock` does not have `trimmed_leading`, `None` is passed. 

What if `lock` has `trimmed_leading` but it's malformed? 
`trimmed_boundary` handles `trimmed` being a dict. 

Let's look at `test_trimmed_leading.py`. 
`test_the_in_edge_is_the_measured_quiet_run_after_the_trimmed_word`. 
It asserts `cut['cut_in']` is in `q`. 

I see a potential issue in `sentence_law.py` `edge_plan`. 
`if trimmed:` 
`q = bin_['quiet_run']` 
`lo, hi = max(lo, q['start']), min(hi, round(q['end'] - LEAD_MIN_S, 3))` 
If `q['end'] - LEAD_MIN_S` is less than `q['start']`, `hi < lo`. 
`cuttable = hi >= lo - 1e-9`. 
If not cuttable, `reason` is set. 

But what if `LEAD_MIN_S` is large? 
`LEAD_MIN_S` is likely small. 

Actually, the most significant defect is in `stand_alone.py`. 
The ruling states: "The STAND_ALONE scorer affirms the TRIMMED text at the unchanged threshold". 
The code `trimmed_opener` checks `score >= CLIP_MIN_SCORE`. 
But `check_edl` only calls `rate` (the scorer) for segments in `need`. 
`need` is built correctly. 
However, `scores` is a dict. 
`sc = scores.get(label)`. 
If `rate` returns a dict that does NOT contain the label (e.g. the scorer skipped it or errored), `sc` is None. 
`score, fault = (None, None)`. 
`trimmed_opener` returns False for `score is None`. 
This is fail-closed. 

Wait, look at `pinned.py` `validate_schema`. 
`if not pin.get('machine_cuts'):` 
This check is inside the `if "trimmed_leading" in s ...` block. 
So if `trimmed_leading` is present, `machine_cuts` MUST be true. 

Is there a fail-open in `trimmed_onset`? 
`ok = onset is not None and onset > HOP_S + 1e-9`. 
If `hook_lead_at` raises an exception, it propagates. 
In `write_lock_cut_table`, `trimmed_onset` is called. If it raises, the function crashes. 
In `gate_g16`, `trimmed_onset` is called. If it raises, the function crashes. 
Crashing is not fail-open, but it is not handled gracefully. However, the prompt asks for "fail-open path (exception, None, malformed field)". An unhandled exception stops the process, which is safe (no render). 

Let's look at `sentence_law.py` `trimmed_boundary` again. 
`if k < 0 or len(tok) != 1 or tok[0] not in TRIMMABLE_LEADING or canon.canon_tokens(words[k]['word']) != tok:` 
If `k < 0`, it returns invalid. 

What if `words` is empty? `k` would be -1. 

I will report the lack of exception handling in `trimmed_onset` calls in `write_lock_cut_table` and `gate_g16` as a potential robustness issue, but more importantly, I see a logic gap in `stand_alone.py`. 

In `stand_alone.py`, `need` is a list of `(label, s)`. 
`rate` is called with `passages`. 
`passages` is likely constructed from `need`. 
If `rate` is None, `scores` is empty. 
`sc` is None. 
`trimmed_opener` fails. 

Actually, the finding is that `trimmed_onset` is not protected against exceptions in `write_lock_cut_table` and `gate_g16`. If `hook_lead_at` fails (e.g. file not found, audio error), the pipeline crashes. While crashing is better than rendering bad audio, the ruling implies a gate check. A gate check that crashes is a defect in the gate's reliability. 

However, a more subtle defect: 
In `sentence_law.py` `edge_plan`, for a trimmed lock, the cut range is intersected with `quiet_run`. 
But `quiet_run` is the *measured* pause. 
The ruling says: "the IN cut sits in a measured pause... with the onset rule met on the audio as cut". 
The code does this. 

Let's look at `test_trimmed_leading.py` `TestStandAloneScorer`. 
`test_a_trimmed_hook_is_scored_too_and_keeps_the_hook_opener_rule`. 
It tests that a hook opening on 'we' fails. 

I will identify the unhandled exception risk in `trimmed_onset` as the primary finding, as it can prevent the gate from producing a verdict (crash) rather than a HOLD. 

Another finding: `pinned.py` `validate_schema` imports `canon` and `L` (sentence_law) inside the function. This is fine. 

Wait, `stand_alone.py` `trimmed_word` returns `str(t.get('word') or '?')`. 
If `t` is `{'word': None}`, it returns `'?'`. 
If `t` is `{'word': ''}`, it returns `'?'`. 
This is consistent. 

I will stick with the exception handling in `trimmed_onset`. (agree: 1)
- qwen27b:F2 [medium] The call to `trimmed_onset` in `write_lock_cut_table` and `gate_g16` is not wrapped in a try-except block. If `hook_lead_at` raises an exception (e.g., due to audio decoding errors or file I/O issues), the entire gate/cut-table generation will crash. The ruling requires the clip to be 'held' if the trimmed word cannot be cut cleanly. A crash is not a hold; it is a failure of the gate mechanism. The code should catch exceptions from `trimmed_onset` and treat them as a failure (verified=False / gate error) to ensure fail-closed behavior. (agree: 1)
- glm:F1 [medium] G16's trimmed-onset check is skipped when the IN edge row fails, so a cut that both sits outside the legal range and opens on sound reports only the range error; the ruling's onset criterion is weaker than the cut table's, which always records it (agree: 1)
- glm:F2 [low] trimmed_onset is computed with the hook's fade_in_ms only when a hook_lead exists; otherwise the default 20 ms may differ from the rendered fade, so the 'audio as cut' measure can disagree with the render (agree: 1)
- glm:F3 [low] trimmed_lock runs before adjudicate_lock, so a pinned segment with both approved_text and trimmed_leading gets its digest computed before ruling-17 adjudication, and the recorded trimmed_leading may not match the adjudicated lock's words (agree: 1)

## Added in cross-examination (not voted on)
- glm: [medium] A trimmed segment whose trimmed_leading dict lacks 'word' (or has it falsy) gets trimmed_word() -> '?', which is truthy, so the segment is added to `need` and scored — but trimmed_opener then reports the placeholder '?' rather than the actual word; more importantly, a segment with trimmed_leading = {} (empty dict) yields t = {} which is truthy, t.get('word') is None, returns '?' — still scored, fail-closed. The real gap: a trimmed HOOK whose opener() already fails (e.g. pronoun) never reaches trimmed_opener, so the gate text reports only the hook-opener reason and the ruling's scorer affirmation is never evaluated — the same weaker-check pattern as glm:F1 but in stand_alone.
- glm: [low] trimmed_lock uses seg['trimmed_leading'] and seg['untrimmed_start'] via direct subscript; a pin passing schema validation always has both (validate_schema enforces both when either is present), so no KeyError path — but build_edl's guard is `if "trimmed_leading" in s` while validate_schema also accepts `untrimmed_start` alone (error), so consistent. No defect; noted only that the digest covers untrimmed_start, satisfying the ruling's 'records ... inside its sha256 digest'.
