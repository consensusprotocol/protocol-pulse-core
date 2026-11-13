# pp-selectid audit 0530 (ruling 33 part 2 at the pin stage, item 42): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** Verdicts:
- grok: "SHIP: no", on one P0 that rests on a misreading (K1) and a policy objection (K5);
- qwen: two P0s, one a misreading (K2), the other the same design question from the opposite side (it argues the
  pin should be sealed with the verdict pending, which is what the code does);
- glm: ten numbered "P0"s. glm was cut at 24000 output tokens (finish=length). Each is answered below; four were real
  defects and are fixed.

## Misreadings (verified from the code)

| # | claim | the code |
|---|---|---|
| K1 | grok P0: with rate=None, check_edl fails a trimmed segment closed, so r["ok"] cannot be True | stand_alone_check builds its EDL with NO selection_lock (package.py, the edl dict: index, text, channel, duration). trimmed_word(s) is None, so trimmed_opener never runs at the pin stage, and the opener rule judges the TRIMMED text's own first word. glm P0-4 and P0-9 read this correctly: a divergence from the render by design, which is the policy question in K5. |
| K2 | qwen P0-1: the acoustic onset rule (a) is measured on the ORIGINAL cut | hook_onset_for(m, ...) passes m["words"][0] and m["start"], and for a variant those are the trimmed ones: words = [w0 + 1, w1], start = the next word's start (trim_variant). The trimmed cut is what is measured. |
| K3 | glm P0-1: the variant's end is never recomputed | The kept words still END at w1. end is unchanged by construction, and duration_s = end - the new start. That is the contract ("start/end bound the KEPT words"). |
| K4 | glm P0-5 / P0-6: the trimmed word is the recogniser's first word, or i == 0 | P0-5: prev is None, so the existing IN rule applies (the file head, or a >= 700 ms stretch from the window's start). P0-6: the failure record reads `ws[i - 1]["text"] if i > 0 else None`, which is guarded. |

## Real defects: FIXED

| # | finding | fix |
|---|---|---|
| F1 | glm P0-2: a variant inherits the original's eligibility, so a trimmed text could fall under the 5-word statement minimum | trim_variant needs at least E.MIN_STATEMENT_TOKENS (5) canonical tokens in the kept words. Tested ("But Bitcoin wins now." gives no variant). |
| F2 | glm P0-8: trim_problems' float(s["start"]) could raise a non-PinRefused exception out of to_pin | Every number is checked first (bools excluded); a missing or non-numeric start is a refusal reason. Tested. |
| F3 | glm P0-10: a trimmed word with no canonical token fell back to the untrimmed IN rule | It fails closed: "the trimmed word has no canonical token". Tested with "" and "...". |
| F4 | glm P0-7: a generator used as a membership list | Replaced by a plain token check (`tok[0] in TRIM_WORDS`). |

## K5: the policy question (open, put to the orchestrator)

- **The design:** item 42 says "use ruling 33 part 2 now". The pin stage cannot run the render's clip scorer (GPU0;
  this session may not use a GPU).
  - Each trimmed segment is sealed with its scorer verdict listed as PENDING in the stand_alone row (scorer_pending).
  - The row's PASS covers what the pin stage measured: the trimmed text's opener and topic, and the medley rule.
  - Ruling 33's (a), the acoustic onset at the trimmed cut, and (c), step A on the trimmed span, are measured at the
    pin stage, and a failure keeps the variant out.
  - The render runs its scorer on every trimmed segment at validate, fails it closed without a verdict, and holds the
    pin before any cut.
- **grok:** "pending at the render" is not defensible under L-m ("nothing measured is never a pass"). qwen argues the
  pin must be sealable with the verdict pending. glm notes the pin's check and the render's judge different things.
- **Disposition:** the code is kept as built. The commit WAITS for the orchestrator's explicit yes or no on sealing a
  trimmed segment with the scorer's verdict pending at the render, because the reviewers split on a standing law. If
  the answer is no, trimmed segments cannot be sealed at the pin stage at all (no scorer there), and item 42 is a
  no-op until a scorer is available to it.

## Verification

- test_medley, test_angles, test_speakers, test_gates and test_hook_onset OK, with the F1-F3 tests added.
