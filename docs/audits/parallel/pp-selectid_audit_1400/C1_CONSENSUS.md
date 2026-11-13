# pp-selectid audit 1400 (RULING 67: the attested-text re-seal): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", P2s only.
  - glm: "SHIP: yes, with conditions", single-model P1s.
  - qwen: "SHIP: Yes with conditions", after two "P0"s its own text contradicts.
- No P0 holds against the code.
- Nothing changes in the code; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code / the evidence |
|---|---|---|
| R1 | qwen "P0": the repetition test checks the wrong side (delete/insert swapped), so "immediate repetition" never fires | difflib's get_opcodes describes turning the FIRST sequence into the SECOND. diff() is `SequenceMatcher(None, r, p)` with r = the run's tokens, p = the pin's. 'delete' means r[i1:i2] is in the run and not the pin (j1 == j2); 'insert' means p[j1:j2] is in the pin and not the run (i1 == i2). carry_class tests `delete -> repeats(r, a, b)` and `insert -> repeats(p, c, d)`: the side that HOLDS the tokens. Evidence: (1) the real held clip's op is ('delete', 38, 40, 38, 38), whose run tokens "that's why" are classed "immediate repetition" (the dry run); (2) test_a_number_a_name_a_negation_or_a_content_word_is_never_carried asserts "we buy it we buy it now" vs "we buy it now" -> ["immediate repetition"]. "buy" is not a function word, so only the repetition branch can return that, and the suite passes (qwen notes the contradiction itself). |
| R2 | qwen "P0": a name opening a sentence is not critical | critical() is the render's _lv2_critical rule exactly (pipeline/pinned.py:335-347 in the main tree, read only): "a capitalised word that does not open a sentence; 'I' excepted". The point is to classify exactly as the render's lock does. A sentence-opening name that is not repeated is a content word, so its class is None (refused, "re-judged first"). |
| R3 | qwen P1: the integrator's package_pin may lack "attested" in SEALED_LATER, so the seal mismatches | The integrator's check_pin_only loads THIS worktree's pipeline/package_pin.py (spec_from_file_location on /home/ultron/worktrees/pp-selectid/pipeline/package_pin.py). The integrator confirmed it in writing at 14:0x: '"attested" in SEALED_LATER is picked up with no change on my side ... make sure the commit adding it lands in your worktree before you send READY'. The commit lands before READY, and check_pin_only is run on the re-sealed pin before it is sent. |

## Answered

| # | finding | the answer |
|---|---|---|
| A1 | glm P1-2: is attest.reads() behaviourally identical to the render's reads()? | Yes, verified against pipeline/pinned.py (adjudicate_lock: amap + reads). The same equal-opcode alignment map, the window `range(max(lo - 1, 0), min(hi + 1, len(x)))`, the consecutive check, and the start / end anchors `(lo > 0 or xmap[idx[0]] == 0) and (hi < len(x) or xmap[idx[-1]] == len(s) - 1)`. The only change: s is a parameter instead of a closure variable. |
| A2 | glm P1-4: the recomputed diff is never compared with the diff the render's hold recorded | On the real data it is equal: the dry run's differences are [["in", "you"], ["that's why", ""]], the hold's `at [['in', 'you'], ["that's why", '']]` verbatim, and the run decode joined from words 32-73 is the hold's quoted run_decode. Single-model; cycle 2 decides whether the explicit check is consensus. |
| A3 | grok P2: no test of a split inside one approved word | test_the_attested_text_is_a_minimal_edit_with_the_run_tokens asserts that `attested_text("a well-known fact", "a well made fact".split())` raises. canon splits "well-known" into two tokens, and the difference falls on the second. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-1: a repetition the matcher emits as 'replace' is refused | It fails closed: the class is None and the re-seal refuses ("re-judged first"). This pin's repetition is a 'delete'. Recorded as a known refusal case. |
| G2 | glm P1-3 / grok P2: the second-pass lookup matches start / end rounded to 3 places | The pin rounds start / end to 3 places from the same moment the record holds (755.454 / 764.214 on both). A miss refuses and writes nothing. |
| G3 | glm P2-1..P2-8 | All fail closed (format coupling, the duplicated law lists, the final write outside the try, a zero-token word). The law lists are the render's, copied. |

## Verification

- All 12 suites OK on dev23 (base d08108a1): test_attest 7 new; test_speakers 16, with the btc_screen fix.
- The real-data dry run on a copy of the held pin re-seals with the attested text. Its differences equal the render's
  hold verbatim.
