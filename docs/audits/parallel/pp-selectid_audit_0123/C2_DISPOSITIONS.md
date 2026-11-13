# pp-selectid audit of the window-record wiring: cycle 2 dispositions (synthesis by the pp-selectid session, 01:36 ET Nov 13)

**Run.** Cycle 2 cross-reviews the fixed diff with the cycle-1 reviews and C1_CONSENSUS.md. Every reviewer: SHIP yes
with conditions; no P0.
- grok-4.20-0309-reasoning (xAI): two P2s; one is shared with glm.
- qwen/qwen3.8-27b (Heimdall, effort none): "P1"s about the start edge (the media starts at 0 s) and the duration
  field; it calls both P2 itself.
- z-ai/glm-5.3-flash (Heimdall, effort none): N1 (P1, conditional) and N2-N5 (P2).

Both cycles together cost about $0.81 at upper-bound prices.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K3 | the coverage check measures the caption record's extent, not whether its WORDS reach the marks. A wordless stretch inside [t0 - 90 s, t0] passes with less context judged (grok P2-1, glm N1) | IMPLEMENTED, the same rule as window() for a full-video record. The context goes back to the last caption word starting at or before the 90 s mark, never past CONTEXT_MAX_BEFORE_S (180 s; beyond that, window()'s own stop applies). It goes forward to the first caption word ending at or past the 60 s mark. The covered window reflects the words. Test: test_a_wordless_stretch_inside_the_window_is_bridged_to_reach_the_marks (nothing said 515-585 s; the context reaches 514.1 s, past the 516.1 s mark) |

## Unique findings, implemented (each verified first)

- **glm N2:** a matching record that cannot be read was reported as "no record in the store matches". Now the why
  says how many transcript files could not be read. Tested.
- **qwen P1-1 / P1-2** (it calls them P2): the start edge assumes the media starts at 0 s. That is the YouTube clock,
  now stated in the docstring.

## Answered or kept, with the reason

- **qwen's condition** (do caption records carry duration?): all 743 caption-type records in the store do (252
  yt_auto, 461 yt_manual, 30 whisper). Where one did not, the end-edge rule fails closed.
- **glm N3** (file_head on w0 == 0.0 exactly): KEPT. The worker writes round(max(0.0, start - 45 s), 3), which is
  exactly 0.0 when clipped.
- **glm N4** (window_records lists a record even when no moment came of it): KEPT, the same as word_records ("read");
  moments and videos count what was used.
- **glm N5** (covered falls back to the selection's bounds when no words are on a side): KEPT. That happens only at a
  media edge, which the edge checks have already allowed.
- **grok P2-2** (each window video's transcripts are read once per build): KEPT. That is at most a handful of files
  per video, read-only.

## Verification

- 10 offline suites, 226 tests OK; test_ledger_build.py has 29 tests.
- The two new tests fail on the cycle-2 code, rebuilt by applying C2_STEP.diff to HEAD: 2 FAIL.
- regression_test.sh: 26 PASS | 0 FAIL | 5 WARN. py_compile: 5 files OK.
