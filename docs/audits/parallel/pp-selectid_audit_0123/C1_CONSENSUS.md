# pp-selectid audit of the window-record wiring (ruling 2): cycle 1 consensus (synthesis by the pp-selectid session, 01:32 ET Nov 13)

**Run.** C1_STEP.diff is 35,703 bytes; the prompt is 58,992 bytes.
- grok-4.20-0309-reasoning (xAI): no findings. "SHIP: yes".
- qwen/qwen3.8-27b (Heimdall, effort none): the context length is not enforced (P1 -> P2); some P2s. SHIP yes with
  conditions.
- z-ai/glm-5.3-flash (Heimdall, effort none): three "P0"s, of which one is conditional and two do not hold; five P1s;
  eleven P2s. SHIP yes with conditions.

The integrator answered the open question out of band: their render path never looks a pin segment's record up by
sha. It decodes its own window and checks approved_text by token ratio, failing closed before any render. So a window
clip needs nothing more in the pin.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | a window clip's L-s context can be SHORTER than 90 s / 60 s with nothing to show it: the code takes whatever caption words exist, so a caption record that stops early (an incomplete ingest) passes silently (qwen P1, glm P0-2 / P1-2) | IMPLEMENTED: the coverage is MEASURED. The caption must reach 90 s before the selection or begin within EDGE_TOL_S (30 s) of the media's start. It must reach 60 s after or end within 30 s of the video's duration (the caption record's own "duration" field, from meta.json). Otherwise caption_parts gives (None, None) and L-s fails closed. "Or to the media's edge" is the existing law's own form (window(): "or to the transcript's edge"). The window returned is the coverage achieved, no longer the bound asked for (glm P2-1). Test: test_the_caption_coverage_is_measured_never_assumed (stops at 650 s: unavailable; the same with duration 660 s: available; starts at 560 s: unavailable) |
| K2 | the caption record might not be the one the ledger mined: segments-sha matches are not proven unique, and the first one sorted wins (glm P0-1, conditional; qwen P2) | IMPLEMENTED: two or more records matching the row's transcript_sha256 is ambiguous, so there is no context (fail closed, with why). Only the full-video slots transcripts/<vid>/transcript.*.json are scanned, never a window. Test: test_two_records_matching_the_rows_sha_are_ambiguous_and_give_no_context |

## Unique findings, implemented (each verified first)

- **glm P2-10:** a caption word starting exactly at the selection's end was dropped. post now takes words with start
  >= t1.
- **glm P2-2:** context_around no longer raises StopIteration on an empty selection; it gives (None, None).
- **glm P2-3 / P2-6:** branches that were never tested now have tamper cases: the segments sha, the method, a channel
  contradiction, and segment edges off their words.
- **glm P2-7:** the exclusion verdict's normal path is tested: a canned verdict, measured, whose prompt carries the
  caption's words.
- **glm P1-4 wording:** "one window per video: the best-ranked row whose window record passes every check". A row
  whose own record fails is passed over, with why.
- **The integrator's suggestion:** a window moment's mined record carries its provenance: window {start_s, end_s,
  record, words_sha256, record_sha256, context_record}.

## Refuted or kept, with the reason

- **glm P0-3** (word_pass_index buckets): KEPT. The worker writes either a good row (record, no error) or a failed
  row (error, no record). The last row of a moment wins, and anything else is counted, not used. Fail closed.
- **glm P1-1** (caption clock vs YouTube clock): KEPT. The worker cut the window from the row's own start / end (w0 =
  start - 45 s, w1 = end + 45 s, 3 decimals), so the containment holds by construction; it ties the row to its
  record. The re-anchor by TEXT is what places the clip, and a skew would be a counted drop.
- **glm P1-3** (exclude when there is no context): KEPT. It is a drop, counted (no_caption_context), never a pass;
  glm calls it compliant.
- **glm P1-5** (file_head on 0.0): KEPT. The worker writes max(0.0, start - 45) rounded, so exactly 0.0 when clipped.
- **glm P2-4 / P2-5 / P2-8 / P2-9 / P2-11:** report arithmetic, relpath form, crash -> exclude on the legacy path (a
  narrowing), encoding, fixture shape. Noted, no defect.
- **qwen P2** (word_pass_index does not check path shape): window_source is the gate, and it checks the path.
- **qwen condition 2** (sentence_ready): E.sentence_ready requires word timing and punctuation (eligibility.py:292).

## Verification

- 10 offline suites, 225 tests OK. test_ledger_build.py has 28 tests.
- The K1 / K2 / provenance tests fail on the cycle-1 code: 2 FAIL, 1 ERROR, rebuilt by applying C1_STEP.diff to HEAD.
- Full-video records are unchanged. On 162 real ledger moments (11 records), context_around's exclusion context is
  byte-identical to the old code's.
- regression_test.sh: 26 PASS | 0 FAIL | 5 WARN.
