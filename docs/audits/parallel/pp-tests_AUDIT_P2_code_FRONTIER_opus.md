# Frontier review (claude-opus-5-5, effort high) - pp-tests_moments_A

stop_reason: end_turn; model: claude-opus-5-5; usage: in 54937 / out 29723

# Audit: pp-tests phase 2, moments-first exam (tests and fixtures only)

## Findings

**1. CRITICAL: the CI answer leaks through a constant bridge string**

- **File:** `build_corpora.py`, `_PASS` loop.
- **Evidence:** `ci(cls, "pass", POOL[key], ..., bridge="Also on the record:", ...)`. Every one of the 21 must-pass cases gets this bridge. None of the 43 must-fail cases uses it: theirs are "And from Swan Bitcoin:", "Meanwhile, Coin Bureau:", and so on.
- **Why it matters:** this one-line gate meets every CI threshold with 0% false rejects:
  `return {"verdict": "pass" if case["package"]["vo"]["bridges"] == ["Also on the record:"] else "fail"}`
  `blind()` does not touch package text.
- **Fix:**
  - Give must-pass cases the same mix of channel bridges the must-fail cases use.
  - Add a corpus test that fails when any single scalar field, or a normalised template of it, perfectly separates the verdicts. Check bridge, intro, signoff, caption shape, order, `before_s`/`after_s`, and `dated`.

**2. HIGH: other shortcuts let a gate pass without judging content**

- **Order leak.**
  - Cases run in INDEX order, and INDEX order is the spec order. All fails come first and all passes last, in all three corpora: CI fails, then the `_PASS` loop; VO fails, then passes; exclusions exclude, then keep.
  - `run_corpus` runs them in that order.
  - A stateful gate that answers "fail" for the first 43 calls and "pass" after that wins.
  - The same order means `--limit N` only ever samples must-fail cases.
- **Unsalted opaque id.**
  - The opaque id is `"case-" + sha256(id)[:12]`, with no salt. `moments_toy_gates/oracle.py` shows the inversion works.
  - `_write` adds `"origin", "verdict", "class"` to every INDEX.json row. Format v1 published only `{"id","file","sha256"}`, so this is an unannounced change.
  - The builder is pointed at this exact directory ("Code your adapter against it; do not read the expected verdicts"). The answer key sits beside the cases in plain text.
- **No held-out set.** The builder can tune to all 135 inputs.
- **Fix:**
  - Shuffle cases per run with a seeded random order, and record the seed in the report.
  - Salt the opaque id per run.
  - Move verdict, class and origin out of INDEX.json into a separate answer file.
  - Keep a sealed held-out subset outside the builder's readable tree, with only its hash committed.

**3. HIGH: must-pass speaker attribution cannot be verified from the material (saif_growth, saif_gold, saif_mining, kaifu_apps)**

- **The Saifedean debate clips.**
  - `vgsSZ4mAHfQ` is a two-sided debate in a `whisper_words_punct` record. It has no speaker markers (`speaker` None, `turn` None).
  - The exam itself marks other sentences in that video as the opponent's: `hypothetical` k481-482, "voiced by the MMT side of a debate, not by the channel's host".
  - Yet three must-pass titles assert "Saifedean Ammous: ...". saif_growth is two sentences (k1080-1081) and might span a turn change (L-v).
  - A gate that fails closed (L-j; "any 'uncertain' is a FAIL") cannot confirm the speaker, so it should answer uncertain. That is 3/21 = 14.3% false rejects, already over the 10% limit, for a gate that is right.
- **kaifu_apps (`4cfjpf_IDwU` k191).**
  - It opens "So ..." in an unlabelled interview.
  - The same video's `wrong_speaker` case (k173-174) is failed precisely because "So you're telling me ..." is interviewer framing.
- **Fix:** either record verified speaker evidence in each case (diarization, or a hand-checked timestamp noted in the case), or replace these with single-speaker monologue clips.

**4. HIGH: must-pass titles use names that are unverified or not shown to be audible**

- **The exam contradicts itself.**
  - VO pass case on moss_derail: "On CoinTelegraph, a guest says ... ", with the note "Condition and hedge kept; **no unverified name**".
  - The CI must-pass on the same clip is titled "Mark Moss Doesn't See Anything Derailing Bitcoin ...".
  - Same pattern for kaifu_apps: VO says "A Bloomberg Television guest", while the CI title says "Kai-Fu Lee Thinks ...".
  - VO segments carry `"speaker": None`.
- **Affected must-pass cases:** booth_free_market ("Jeff Booth"), moss_derail, kaifu_apps, burnett_s2f and burnett_gold ("Joe Burnett"). That is 5/21 ≈ 24%.
- **Why it matters:** L-t requires every name to be audible in a clip. Nothing shown proves these names are in the clips, so a correct gate may reject them all.
- **Fix:** either show the name in the window or the source metadata, and state in the format that source title or description counts as evidence, or re-attribute to the channel or "a guest".

**5. MEDIUM: must-pass titles drop hedges, and BTC Sessions attribution is inconsistent**

- **valek_macro.**
  - The why says "a complete framed view ('I think')".
  - The title, "BTC Sessions: Bitcoin Trading 'More and More' as a Macro Sound-Money Asset", drops "I think". That is stronger certainty than the source.
- **Inconsistent attribution within one video (`jTuJ8PXhRV4`).**
  - k730 is titled "BTC Sessions Guest:".
  - k530 is titled "BTC Sessions Guest:".
  - But k796 (gold_etf) and k802 (valek_macro; the key name suggests a guest) are titled "BTC Sessions:".
  - Either the speaker is unverified or one set of titles is a wrong-speaker attribution.
- **btcs_dollar.** The why says "('kind of', 'in my opinion') and kept so", but the title keeps only "kind of".
- **Uncertain:** sb_bottom, "I Still Think the Bottom's In", is a time-sensitive market-state claim. I cannot see its publish date relative to the Nov 5 drop.
- **Fix:** keep the hedges in the titles, and attribute each speaker consistently.

**6. MEDIUM: the bm_bear relabel has the wrong class, contaminates the baseline, and is used inconsistently**

- **Weak label.**
  - The case is `later_retraction` on POOL["bm_bear"]. Its why cites "But maybe there's a more nuanced view owed".
  - That is a hedged qualification, not a retraction.
  - The title "Every Bear Market Shallower Than the Last" matches the clip's own numbers, as quoted in the VO pass case: "minus 85%, then minus 84%, then minus 77%, and now minus 53%". The must-fail label is not clearly defensible.
- **Baseline contamination.** `found_by` reads "frontier baseline v0 (both vendors) flagged the must-pass label". The label was flipped on the baseline's own output, so that case is no longer blind for the baseline.
- **Inconsistent use.** bm_bear is still a "real selected sentence" in 6 VO cases, 2 of them must-pass. It still sits in POOL, which is commented "clean real clips".
- **Fix:**
  - Drop the case, or reclassify it with a package whose defect is unambiguous.
  - Disclose the baseline's influence on labels and exclude this case from baseline scoring.
  - Replace bm_bear in VO.

**7. MEDIUM: must-fail CI packages carry confounds, so the per-class table credits detection that may not have happened**

- **hypothetical 01 (`L9tzgg6PXi8` k473-474).** The title quotes 'Bitcoin Goes to a Million'. Per the why, that phrase is in k471, outside the moment, so any title-quote-audible check rejects it. Uncertain: k473-474 may repeat the phrase; I cannot see it.
- **answer_without_question 02 (k92).** The title and intro introduce "$1 Million by 2030", which is not in the clip. A number check rejects it.
- **sarcasm 04 (`jTuJ8PXhRV4`).** The title "'Sell Your Bitcoin, All of It'" is itself a second-person financial imperative (L-t).
- **quoting_opponent 01.** The title names Saylor with "Insolvent ... Bankrupt", which is a named insolvency accusation (L-u).
- **false_dialogue 03.**
  - Its two clips share a channel ("Both clips are CoinTelegraph uploads"); this is acknowledged but not fixed.
  - Its moment, k351, is the same moment as answer_without_question 01.
- **false_dialogue 01.** The moment "No, you can't. They all go down." is on its own an answer without its question.
- **Fix:** rewrite each package so that the class is its only defect.

**8. MEDIUM: VO banned_framing cases do not isolate the framing verb**

- **Evidence:**
  - `bm_reserve`: "admits he **never believed in** the strategic reserve", against the clip's "never thought ... was going to happen". This changes the stance.
  - `rv_overblown`: "destroys **the case against** the AI buildout", against "reactions ... very overblown".
  - "Simply Bitcoin slams the Fed", against a neutral factual clip.
- **Why it matters:** a stance-only checker gets 3/3 without knowing the verb list.
- **Fix:** add verb-only variants, for example "Real Vision slams the reactions to the AI buildout as very overblown."

**9. MEDIUM: format fields leak class or origin past `blind()`**

- **Stale-time captions.** `dated=False` is used only by the 3 stale_time_reference cases, so an undated caption perfectly identifies that class.
- **Constructed exclusions.**
  - The CONSTRUCTED exclusions carry `"title": "CONSTRUCTED (no store record)"`, with video_id, url, `k` and `start` all None.
  - This exposes the origin that `blind()` claims to hide, and both such cases are "exclude".
  - `test_blinding_hides_the_answer` checks only keys, not values.
- **Unique window.** after_s=80 appears only in later_retraction 01.
- **Fix:**
  - Add undated must-pass cases.
  - Give constructed cases realistic, same-shaped metadata.
  - Extend the blinding test to values.

**10. MEDIUM: skip-with-reason is decided by exit code alone**

- **Evidence:**
  - `test_the_gate_sits_the_exam` uses `if status == 3: pytest.skip(...)`.
  - `_judge` catches only `(Exception, NetworkRefused)`, so a gate's `SystemExit(3)` propagates.
  - The process then exits 3 with no report, and the test skips with the message "function not defined".
- **Why it matters:** a crashing gate can be reported as absent.
- **Fix:**
  - Skip only if `rep` is not None and the corpus rows are 100% ABSENT, or `absent_reason` is set.
  - Catch `BaseException` other than KeyboardInterrupt in `_judge` and record it as ERROR.

**11. MEDIUM: the baseline spend guard under-reserves**

- **Evidence:**
  - `EST_OUT_TOKENS = 2500`, but `max_out` is 8000 (anthropic) and 6000 (openai). The input estimate is `len/3.5`, which is not conservative.
  - Each in-flight openai call can overrun its reservation by up to (6000−2500)×$120/1M ≈ $0.42.
  - With `--jobs 6` that is about $2.5 over the $15 guard.
- **Run truncation.** At the declared price the output reservation alone is ≥$0.30 per openai call. The run may exhaust the budget mid-way, and because cases run in INDEX order, the must-pass rows become ERROR first, which loses exactly the false-reject number.
- **Already correct:** the cross-process flock and the reserve-then-settle logic.
- **Fix:**
  - Reserve at `max_out`.
  - Pre-estimate the whole run and refuse to start if it exceeds the budget.
  - Shuffle the case order.
  - Gitignore SPEND.jsonl and its .lock.

**12. LOW: verbatim binding is circular, and the network block is partial**

- **Circular binding.**
  - `test_every_case_rebuilds_verbatim_from_the_store` compares the files against the same `store_extract`/`build_corpora` code.
  - The claim "computed exactly as pp-selectid d809a1f8" (`tokens_from_record`, `split_sentences`) is never tested against pp-selectid's code.
  - The record sha binding itself is sound.
- **Partial network block.** `refuse_network` blocks only TCP `connect`/`connect_ex`. DNS lookups (`getaddrinfo`), UDP `sendto` and subprocesses are not blocked.
- **Exclusion label issues (also low):**
  - exclusions/single_source_breaking 01 (`9La50F_lmd0` k368) says "presented as news". The CI case on the same sentence says the hosts dismiss it ("Spoiler alert, it's neither"). The class is wrong.
  - Whether "What Bitcoin Did", "Coin Bureau" and the speaking channels in the constructed partner_attack cases are in `config/partner_channels.json` cannot be verified from this material.
- **Fix:**
  - When `PP_MOMENTS_PATH` reaches pp-selectid, cross-check sentence `k` and text for every referenced record against its functions.
  - Also block `getaddrinfo` and `sendto` in the harness.

## Clean on review

- Nothing writes to the main tree; the store is only read, and `.env` is read by name without printing the key.
- `CUDA_VISIBLE_DEVICES` is set to empty.
- The default test run makes no network calls.

## Verdict

**NOT READY**
