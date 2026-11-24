# Batch 124 (ruling 159 (b) at G18's edges), cycle 1
Seats: gemma (medium) PASS; glm (effort none) PASS 0.6 with 1 note; qwen27b (medium) PASS 0.72 with 4 notes; qwen at high
effort and gpt-oss: no verdict (token limit / no JSON), recorded.
- qwen Q2 (medium), "difflib aligns a one-word shift near a repeated word as replaces": DISPROVED by running it. For
  ['the','the','cat','sat'] against ['the','cat','sat','the'], difflib gives delete / equal(3) / insert, and
  _edges_substituted_only returns False (HARD). The same holds for 'so I think ...' -> 'I think ... is', for
  'I think I think ...' -> 'I think ...' and for 'we we hit ...' -> 'we hit ... today': all False. The longest-block
  alignment keeps a shift a shift.
- qwen Q1/Q3 (low), "a cut mid-word read as a same-length word relies on G17c": TRUE BY DESIGN. G17c (the edge words'
  own audio, natural decay at full level against the source) is REQUIRED and review-blocked (release_auth REQUIRED;
  telegram.REVIEW_NOT_DROPPABLE "G17_onset_tail"). The interior audio check plus G17c cover the clip, fades included.
- qwen Q4 (low), "normalised words lose a ticker's capitals": DISPROVED. _material passes the original texts, and
  pinned._lv2_critical finds the token's capitalised occurrence there ('AAPL' -> material), exactly as on the identity path.
- glm (medium), "an edge-touching replace that extends past the window": CONSERVATIVE, not a defect. The whole replace
  is checked: every word must be a one-for-one non-material substitution, or the edge stays HARD.
