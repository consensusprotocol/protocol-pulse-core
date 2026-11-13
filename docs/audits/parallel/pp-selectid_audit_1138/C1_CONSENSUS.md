# pp-selectid audit 1138 (RULING 56 under RULING 60, re-based onto 58 + 59): cycle 1 consensus

**Run:**
- grok: no P0 or P1, "SHIP: yes".
- glm: "SHIP: yes, with conditions". Its 8 numbered "P1" items close themselves or are by design (below).
- qwen: four "P0" items with one root cause (refuted below). It stopped at its 16,000-token limit, after retracting
  every P1 it raised ("No P1 here. I retract").

No P0 or P1 holds. Nothing changes in the code; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P0-2..P0-5: package_pin.affirmed_verdict checks only that scorer_sha is present, not that it equals the render's code NOW, so a pin sealed under an older scorer passes after the render changes, against L-j | The pin-stage verdict is a pre-filter, never the release gate for the scorer. The render's validate asks its OWN scorer again at render time, on its current code. The integrator's contract (main pipeline/stand_alone_scorer.py, docstring line 6, read only): "Validate re-checks at render as now. Nothing is loosened." The sha equality IS checked where a verdict enters this build: scorer_verdicts() requires the file's scorer_sha == render_scorer_sha() recomputed at the build's start, or uses nothing. A pin carrying a verdict made under older code can therefore at worst be refused at validate: one pin wasted, never a release authorised on a stale verdict. package_pin is also imported by the integrator's seal check (check_pin_only recomputes seal() only), so it stays free of reads of the render's files. |
| R2 | glm P1-4: scorer_problems tests the first word with SA._words against SA.CONJUNCTIONS / REPLY_FRAGMENTS; a capitalised token ("But") would miss the lower-case lists, so a conjunction opener could seal without a verdict | stand_alone._words lower-cases: it is canon.canon_tokens(text, heads=True), "Lower-case word tokens". Measured on this code: _words("But Bitcoin wins.") -> ['but', 'bitcoin']; _words("Yeah, Bitcoin.") -> ['yeah']. The render's check_edl classifies with the same function and the same lists (stand_alone.py, the render's module copied read only), so the two classifications are one. |

## Recorded (no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-2: verdict_of checks only the text sha, so it trusts its producer | The only producer is scorer_verdicts(), which keeps a verdict only when "affirmed" equals the render's moments rule (a disagreeing one is dropped). The pin's affirmed_verdict is the strict, independent check at the seal. A hand-made verdict cannot reach a build: build() strips any carried verdict (with_verdict) and attaches only the index's. |
| G2 | glm P1-5: the candidates are computed on copies without verdicts, so an opener admitted this pass is asked about again | By design (reading K3, tested): the set is independent of verdicts, so it stays stable across passes. The integrator reuses a rated text and pays only for new ones. |
| G3 | glm P1-1 / P1-3 / P1-6 / P1-7 / P1-8 | They close themselves in glm's own text: the "no verdicts" branch; the log's guards; approved_text vs text precedence (equal at seal, and only `text` exists before to_pin); the sealed affirmed flag is the re-derived one; clip_scorer's model life (the render's own function, never called by this builder). |

## Verification

- test_medley 113 OK; all 11 suites OK on the scratch copy (dev19, base 4b047332).
- Dry run on the real verdicts file, read only: 145 read, 9 affirmed, 0 disagree; scorer_sha = the render's code now.
