# pp-selectid audit of the batch + speakers diff: cycle 2 dispositions (synthesis by the pp-selectid session, 00:18 ET Nov 13)

**Run.** Cycle 2 cross-reviews the fixed diff (C2_STEP.diff) with the cycle-1 reviews and C1_CONSENSUS.md. Every
reviewer: SHIP yes with conditions; no P0, no P1.
- grok-4.20-0309-reasoning (xAI): three P2s.
- qwen/qwen3.8-27b (Heimdall, effort none): confirms K1, K2 and K3. Its conditions are E.spoken consistency, the
  SEALED_LATER test, and the unknown rate.
- z-ai/glm-5.3-flash (Heimdall, effort none): "P1 HIGH: none". Six P2s; its conditions are N1, N4 and N7.

Both cycles together cost about $0.80 at upper-bound prices.

## Implemented (each verified first; each has a test that fails without it)

| finding (reviewers) | disposition |
|---|---|
| grok P2-2: matching normalised text can be fooled | REFUTED as written: its example is not a contiguous substring ("when i wrote the price" is not inside "when i wrote technology the price ..."). One real gap in the same place is FIXED: a normalised substring could start or end inside a word ("i wrote" inside "hi wrote"; a name inside a longer name). Quotes, names and lines now match whole words only (_within). Test: test_a_quote_or_a_name_matches_whole_words_only |
| grok P2-1 / glm N2: a reply with prose or a fence around its JSON is lost to "unknown" | FIXED: _json reads the reply's outermost {...}. Test: a fenced reply, and a fenced reply wrapped in prose |
| glm N1 (its first condition): the pin trusts a named record's measured flag | FIXED: speaker_problems refuses a named speaker whose record is not measured. Test: dict(named, measured=False) is refused |

## Answered (no code)

- **glm N4** (does Router.call's reply carry backend?): yes. Router.call returns Reply(text, name, ...) with the
  back-end name, and medley() already reads r.backend the same way.
- **glm N7** (is the seal computed from the records speaker_problems checked?): yes. to_pin checks pk["segments"]
  and builds the sealed segments from those same dicts.
- **qwen conditions:**
  - E.spoken gives the same text in the prompt and in the check, by construction.
  - The SEALED_LATER test passes: 6 of 6 earlier pins recompute.
  - The unknown rate of the live seal is reported in STATE.

## Kept, with the reason

- **grok P2-3** (the package file is written before the speakers): build and seal are separate steps, and the pin
  is the authority. qwen calls it the same: a harness detail.
- **glm N3** (a dead chain retries once): bounded. The retry is one call per segment, and the router skips back-ends
  it has marked down.
- **glm N8** (the earlier-pins test needs tests/package/proof): those pins are committed with the repo, and the test
  says what it reads.
- **K3** (people and roles): as documented in cycle 1.

## Verification

- 10 offline suites, 216 tests OK (test_speakers.py has 16).
- regression_test.sh in the worktree: 26 PASS | 0 FAIL | 5 WARN.
