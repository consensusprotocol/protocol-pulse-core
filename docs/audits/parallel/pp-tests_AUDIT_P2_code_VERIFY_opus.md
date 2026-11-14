# Frontier verification round (claude-opus-5-5, effort high)

stop_reason: end_turn; model: claude-opus-5-5; usage: in 65135 / out 40215

# Verification round: pp-tests moments-first exam (after fixes)

Corpus sizes as built from the specs in `build_corpora.py`:

| Corpus | Must-reject | Must-accept | False-reject budget |
|---|---|---|---|
| Context integrity (CI) | 42 | 22 | 2 false rejects = 9.1%; 3 = 13.6% (fails) |
| VO fidelity | 27 | 13 | 1 false reject allowed |
| Exclusions | 23 | 12 | 1 false reject allowed |

## 1. Previous findings

| # | Status | Evidence |
|---|---|---|
| 1 CRIT, bridge leak | **RESOLVED** | Pass and fail cases draw intro, bridge, sign-off and order from one pool (`_pick(BRIDGES, "bridge", *key)`). `test_no_package_field_separates_the_verdicts` covers each field. The only fixed bridge, "Not everyone is convinced." (false_dialogue 02), is the trap itself and is exempted. A different, cross-case leak remains (N2). |
| 2 HIGH, order / salt / INDEX / held-out | **PARTLY** | **Fixed:** shuffle `random.Random(seed)`, per-run salt, INDEX restricted to `{"id","file","sha256"}`, hash order. **Held-out refusal: not acceptable as argued.** File permissions are not the only possible seal. A temporal seal needs no unreadable file: the builder commits and hashes its gate first, then this session mines a fresh set (≥15 CI, ≥8 VO, ≥6 exclusions) and the frozen gate sits it. As it stands, the builder can tune on all 135 cases, including their `why` text. |
| 3 HIGH, speaker attribution | **PARTLY** | **Fixed:** the debate clips are gone. **Remaining:** kaifu_apps (`4cfjpf_IDwU` k191, "So …", in a record the exam itself says "has no speaker labels") is still a must-pass. sb_fed's "single narrator" claim is contradicted by the exam's own cases (N3). |
| 4 HIGH, unverified names | **PARTLY** | **Fixed:** no Booth, Moss, Lee or Burnett names in must-pass titles. **Remaining:** "Bitcoin Mechanic: 'The Amount of Freedom…'" and the VO pass line "The Bitcoin Mechanic says…" may name a person (N4). |
| 5 MED, hedges | **PARTLY** | **Fixed:** valek_macro and tftc_iran keep "I Think". **Uncertain:** btcs_dollar. The earlier why cited "'kind of', 'in my opinion'"; the new quoted title "'All of the Currencies, in My Opinion, Are on Their Way Out'" has no "kind of". If the sentence contains it, a hedge is dropped inside quotation marks. |
| 6 MED, bm_bear | **RESOLVED** in the corpus | bm_bear is no longer in POOL or VO. The baseline-contamination point has grown, though (N8). |
| 7 MED, confounds | **PARTLY** | **Fixed:** answer_without_question 02, quoting_opponent 01 (no accusation), and false_dialogue 03 now crosses channels. **Not fixed:** see N6. |
| 8 MED, banned-framing isolation | **RESOLVED** | The three lines are the clip's words plus the verb. Nit: bm_reserve's line adds "A Bitcoin Magazine guest … he", a role and gender not shown anywhere. |
| 9 MED, format leaks | **PARTLY** | **Fixed:** captions dated, uniform 90/80 windows, exclusion ids stripped, blinding test checks values. **Remaining:** constructed exclusion cases are still recognisable (N7). |
| 10 MED, skip by exit code | **RESOLVED** | `_judge` catches `BaseException` except `KeyboardInterrupt`; `exits.py` toy test; skip requires `absent_reason` or all-ABSENT rows. A different false-pass path remains (N5). |
| 11 MED, spend guard | **PARTLY** | **Fixed:** reserves `max_out` at 2.5 chars/token and settles in `finally`. **Remaining:** no whole-run pre-estimate; "one vendor after the other" is not enforced in code (N10). |
| 12 LOW | **RESOLVED** (caveats) | **Done:** `test_sentence_ids_match_pp_selectid_at_the_named_commit` runs code from git object d809a1f8; `getaddrinfo` and `sendto` are blocked. **Caveats:** the test skips if the object is missing. It `exec`s extracted functions only, so it will raise NameError if those functions use module helpers (uncertain). Partner-list membership is still unverifiable from this material. |

## 2. New defects

**N1. HIGH: must-pass `cb_target` (n17v727G7FI k82) fails the exam's own rules**

- **The case:**
  - Title: "Coin Bureau: 'Our 75K Target Never Broke', and Bitcoin Didn't Make a New Low Once the Results Were In".
  - Its why says "a dated fact", but the clip carries no date.
- **Unresolved referent:** "the results" (the election, per cb_nov3 in the same video) is outside the clip. That is exactly the unresolved_referent trap.
- **Stale time claim:** "never broke" is a state claim relative to the publish date (around Nov 4), shown on 2026-11-12. That is the stale_time class's logic.
- **Not baseline-tested:** the clip was added after baseline v1.
- **Why it matters:** a correct, fail-closed gate rejects it. Together with N3 and N4, three must-pass rejects are already 13.6%.
- **Fix:** replace it with a clip whose referents are all inside it, or retitle with the referent resolved ("…once the Nov 3 election results were in, per Coin Bureau on 2026-11-04").

**N2. HIGH: the clean POOL is both the must-pass set and the filler, so membership leaks the verdict**

- **Evidence:**
  - 19 of 22 must-pass moments also appear as adjacent clips in other CI cases.
  - The other 3 (swan_questioning, gold_etf, bm_reserve) appear as VO segments.
  - Only the three title_adds_thesis moments do the same among the 42 must-fails.
- **A content-blind gate that passes:**
  - Rule: "pass iff the moment text recurs as a segment elsewhere in the exam, and the title adds no number or claim absent from the clip".
  - It can build its lookup from the blinded corpus files alone.
  - It needs zero context judgement.
- **Overfitting risk:** the same 25 sentences recur everywhere, so the builder tuning on the corpus learns "these are clean".
- **Fix:**
  - Draw adjacents and VO segments from a pool disjoint from the CI must-pass moments.
  - Let some must-fail moment clips appear as VO B-segments too.
  - Add a test that the rate of "moment recurs elsewhere" is similar for both labels.

**N3. MEDIUM: must-pass `sb_fed` (l987bgGZjS0 k203) claims "single narrator", but the exam contradicts it**

- **Evidence from the same video:**
  - exclusions third_party_media 01 plays Darius Dale's audio at k39-40.
  - The author removed k130 and k133 as possible paraphrases of Lopp and Saylor.
  - k212 is a buy imperative, likely inside the 80 s after-window.
- **Why it matters:** whether k203 is the host's own assertion is not established. sb_fed is also adjacent in 6 must-fail cases (unresolved_referent 01, sarcasm 02, answer_without_question 03, title_adds_thesis 03, hypothetical 02, conditional_split 01).
- **Fix:** verify k203's speaker by timestamp listening and record it in the case, or replace the clip.
- **Same treatment for kaifu_apps:** record who says k191, or drop it.

**N4. MEDIUM (uncertain): "Bitcoin Mechanic" in the must-pass mechanic_freedom title and VO faithful_paraphrase 02**

- **Evidence:** "The Bitcoin Mechanic says…" uses an article, so it reads as a person. The pseudonym is a guest on several shows. Its channel is not in `SHOW_NAMES`.
- **If NM_WPezsI0I's `channel_name` is not "Bitcoin Mechanic":**
  - The must-pass package names an unverified person.
  - quoting_opponent 03 may then show one channel twice, if the channel is TFTC (its adjacent is tftc_sound).
- **If it is "Bitcoin Mechanic":** the author's own rule wants "Bitcoin Mechanic's show".
- **Fix:** print the meta `channel_name`, then credit the show.

**N5. MEDIUM: the real-gate test passes on exit status alone**

- **Evidence:**
  - `test_the_gate_sits_the_exam` ends with `assert status == 0`.
  - A gate that calls `os._exit(0)`, or patches `__main__.table`, ends the run at 0 with no report or a forged one.
  - The test does not check that rows cover the whole corpus.
  - `PP_MOMENTS_CORPORA` passes through the env filter, so the "real" exam can run on another directory.
- **Fix:**
  - Require `rep is not None`.
  - Recompute `table()` in the test process from `rep` rows.
  - Assert the row ids equal the salted ids of every case in the committed corpus (the salt is in the report).
  - Drop `PP_MOMENTS_CORPORA` from the passed env.

**N6. MEDIUM: must-fail cases still carry a second defect, so the per-class table credits the wrong detector**

- **conditional_split 01, 02, 03:** each moment also has an unresolved referent ("We will pass THAT", "stop IT at all", and 03's own why: "its 'IT' (the hearing) is outside the clip").
- **false_dialogue 01 (k382-384):** "No, you can't. They all go down." is an answer without its question, rejectable alone.
- **sarcasm 04 (jTuJ8PXhRV4 k179-181):** contains "Sell your Bitcoin, all of it" (exclusions imperative 03 uses k179-180), an L-u imperative in the clip.
- **steelman 02, quoting_opponent 01, conditional_split 02, false_dialogue 01:** titles credit "Scott Melker" as speaker from an unlabelled whisper record. This breaks the author's own person-named-channel rule.
- **hypothetical 01:** whether "Bitcoin Goes to a Million" is spoken in k473-474 (the why places it in k471) is still unshown.
- **Fix:** for each, either isolate the trap, or record `expected.also` (the secondary classes) and report per-class detection only on isolated cases.

**N7. MEDIUM: constructed exclusion cases are still recognisable past `blind()`**

- **Evidence, timing:** `_con_sents` produces 1-decimal times, a fixed 0.3 s gap, and duration `0.35*words+0.4`.
- **Evidence, shape:**
  - Descriptions are under 40 characters ("Weekly Bitcoin show.").
  - The context spans about 25 s against about 60 s for real cases.
  - All four cases share the same filler sentences.
- **Why it matters:** all four are exclude and make up two whole classes, so this is a free win. `_ex_fields` checks none of these.
- **Fix:**
  - Take the timing pattern and the description from a real record of the named channel.
  - Fill the context to 60 s.
  - Add precision, gap regularity and span to `_ex_fields`.

**N8. MEDIUM: the baseline is no longer blind, and its prompt is tuned to the cases**

- **Not blind:** v1's output drove label and case changes (k130, k133, the burnett title, the person-named channels).
- **Cue words beyond the law text:**
  - VO_RULES lists "(buy, sell, hold, stack, don't sell)", which are the exact must-fail lines.
  - EX_RULES adds "'reportedly'" and "(relaying allegations included)", which are the found_by cues.
- **Stale window text:** CI_RULES still says "60 s after", while every window is 80 s.
- **Fix:**
  - Run v2 with the laws' wording only, and the correct window text.
  - Label v0 and v1 as label-informing, not blind.
  - If credits allow, use a model that saw no earlier version.

**N9. LOW: must-pass VO wording drifts from the clips**

- **kaifu_apps:** "should **focus on** the application space" against the clip's "should look at"; "focus on" is stronger.
- **faithful_paraphrase 01:** drops "or want less risk".
- **Fix:** keep the clip's verb ("look at") and the full disjunction.

**N10. LOW: spend guard and key handling**

- **No run pre-estimate:** there is no guard before the run starts. At $15/$120 per 1M tokens, a full gpt run of 135 cases is plausibly $13-27 on its own, so it truncates into ERROR rows.
- **Per-process budget files:** `PP_BASELINE_SPEND` lets two processes use separate budget files.
- **Key fragments in reports:** SDK auth errors (masked key tails) land in report rows through `why` and `traceback`.
- **Fix:**
  - Refuse to start when (cases × expected cost + already spent) exceeds the budget.
  - Pin the SPEND path.
  - Redact `sk-…` and `AIza…` patterns in `_judge`.
  - Gitignore SPEND.jsonl and its .lock.

**Clean:** nothing writes to the main tree; the store and `.env` are only read; CUDA is hidden before the gate import; the default run reaches no network; toy controls cover reject-all, accept-all, uncertain, positional, crash, exit, peek, network, absent and partial gates.

## Verdict

**NOT READY.** N1, N3 and N4 together can push a correct gate past the 10% false-reject limit. N2 is a content-blind route to passing. N5 lets exit status 0 count as a pass without a verified report.
