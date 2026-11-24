# Heimdall audit

**Question:** Review this diff. ORCHESTRATOR RULING 143 (15:55 ET Nov 17), verbatim in part: "(1) MATERIAL = a number, a negation, a name (letters differ after the canon), a ticker or a currency amount. Everything else is NON-MATERIAL. (2) NON-MATERIAL disagreement NEVER holds. The sealed text takes the two-of-three reading; if all three differ, the run decode's (it is what the render will cut). Sound-alikes (ad/add), fillers of any length (you know, I mean, sort of like), word forms: all here. More than 3 unsettled non-material pairs in one clip adds ONE soft flag: 'The clip (X): the transcript and the audio readers differ on a few small words.' (3) MATERIAL disagreement: if the TWO AUDIO READINGS (the run decode and the second recogniser) AGREE with each other against the transcript, the transcript was wrong: the sealed text takes the audio's reading, numbers included ('$2.35 billion') ... mark it in the note ('transcript corrected from the audio: ...'). If the two audio readings DISAGREE with each other on a material word, HOLD ... 'i've' / 'IBIT' is a ticker: material: holds unless both audio readings agree. (4) Unchanged and HARD: a cut mid-word, an empty or shifted source (the offset guard), a span whose audio readings share under 85 percent of their words (wrong audio, not small words; propose a better number from the records if you have one)."
The integrator's reading of (4), recorded: the share is the run decode's words the second reading heard, in order (the second recogniser also writes the speaker's repeats, false starts and the window's spill: those are not the wrong audio), and a hold needs more than 3 words missing (a short span's one or two small words are not the wrong audio). G18 (a HARD render gate comparing the final's audio decode with the lock text when the lock was adjudicated) decides small-word-only differences by the audio, as ruling 22 already decides omissions, so that (2) holds at render too.
FACTS (unchanged code): reads(x, xmap, lo, hi) is True when the second reading reads x's tokens lo..hi-1 at that position (with one aligned neighbour each side, nothing between); _majority_text writes the settled text from the approved text and the pairs that took 'run', or returns None; _lv2_critical(tok, texts) marks digits, negations, ordinals and capitalised mid-sentence words; canon.word_form marks a possessive / plural / contraction pair; lock_precheck answers outcome 'hold' (final for the builder), 'error' (no verdict) or a pass; G18's ruling 22 block runs span_fidelity (the prepared clip's interior against the source span) and clears the identity difference only when the audio is the same.
Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.
CHECKS:
H1. Can a MATERIAL pair be sealed without both audio readings agreeing on it (run decode and second recogniser), or a material disagreement between them pass (adjudicate_lock, as_spoken, G18)?
H2. Can a NON-MATERIAL difference still hold anywhere (adjudicate_lock, as_spoken, G18 against an adjudicated lock), other than through the wrong-audio rule?
H3. Is the wrong-audio rule as recorded (share of the run's words heard in order; < 0.85 and more than 3 missing), and can it hold the right audio or pass the wrong one?
H4. Can any input raise uncaught, or does anything else change behaviour (the note, the flag text and count, _majority's re-lock, ruling 103's re-listen)?

**Panel:** gptoss  |  **Cost:** $0.0011
## Consensus findings (majority of panel agrees)
- **[high] pipeline/pinned.py:0** `material_pair` is called with string substrings instead of token lists in `adjudicate_lock`, causing incorrect material classification and potential sealing of material pairs without both audio readings agreeing.
  - evidence: ````
    for _, a, b, c, d in ops:                          # RULING 143 (orchestrator 2026-11-17 '15:55'), pair by pair
        pin_ok, run_ok = reads(p, pmap, c, d), reads(r, rmap, a, b)
        mate`
  - fix: Pass token lists to `material_pair` by splitting the substrings: `material_pair(r[a:b].split(), p[c:d].split(), (run_t, pin_t, sec_t))`. Additionally, check that both audio readings agree before sealing: set `took = "run" if run_ok and pin_ok else None` for material pairs.
  - raised by gptoss:F1; agree: gptoss
- **[high] pipeline/pinned.py:0** `audio_share` and `wrong_audio` are invoked with a string (`run_t`) instead of a list of tokens, leading to character‑level comparison and incorrect wrong‑audio detection.
  - evidence: ````
    s = [x for x in canon.canon_tokens(sec_t) if not canon.nonlexical(x)]      # ruling 135 (d): fillers are not words
    readings = {"run_decode": run_t, "approved": pin_t, "second_recogniser": `
  - fix: Pass token lists to `audio_share` and `wrong_audio` by converting `run_t` to a list of tokens: `share = audio_share(r.split(), s)` and `if wrong_audio(r.split(), s) is not None:`. Ensure `r` is a token list before calling these functions.
  - raised by gptoss:F2; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
