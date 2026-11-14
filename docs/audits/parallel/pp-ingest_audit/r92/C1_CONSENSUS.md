# Ruling 92 (hook v2), cycle 1: consensus and dispositions

Reviewers (Heimdall-served): qwen3.8-27b (219 s, $0.009), glm-5.3-flash (315 s, $0.005), muse-spark-open-816b
(455 s, $0.026). No P0 from any (muse: "No data-loss, security, or correctness blocker in this diff").

## REFUTED BY MEASUREMENT
| finding | reviewers | evidence |
|---|---|---|
| P1 "if the text starts with '>>', opener_word returns '>>' and the conjunction check is bypassed" | qwen, muse (consensus) | measured: canon.canon_tokens(heads=True) drops the marker in both forms (and leading dashes and quotes): ">> And then" -> ['and', 'then']; "&gt;&gt; And then" -> ['and', 'then']; 229 ledger texts begin with '>>' (">> Yeah, I ..." -> 'yeah': a reply word, dropped). Pinned: test_mine `test_a_leading_speaker_marker_never_hides_the_first_word` |
| P1 "add a test that the OPENER sets match the builder's" | muse | present: test_mine `test_the_opener_words_are_the_builders_verbatim` (ast of pp-selectid stand_alone.py) |

## IMPLEMENTED
| finding | reviewer | fix |
|---|---|---|
| no way to see whether ruling 92 changed anything | glm P1 | live.json `hooks_12h.rows_by_episode`: hook rows by the episode's turn measure (>= 1 turn / min, < 1, unmarked captions, not measured); the measure is kept per video (queue episode_markers / episode_tpm) |
| `--rerun` left no event; its "once per version" help was wrong for failed videos | glm P2 | an event `hooks_rerun` (version, videos); the help says a failed re-run is queued again by a second --rerun and that it is run while no hook pass is in flight (muse P2) |
| an empty record measured like a solo episode | muse P3 | `measured_from: "no segments"`, minutes None |

## BY DESIGN
| finding | reviewer | evidence |
|---|---|---|
| P1 "an episode term in rank_score" | glm | rank_score orders every read, medleys included; ruling 92 is for SPOTLIGHTS ("medleys keep the existing rule"), and the builder applies it with the measure each row now carries |
| canon import failure | muse | the hook pass then raises: hook_video records the crash, retries in 10 min, writes nothing (fail closed, visible in the log) |
| cache the episode measure per video | qwen | already: computed once per video in mine_video and passed to build_line |
| an "empty" opener reason | glm | bad_opener returns its own reason ("empty") before the duration rule; it is its own key in the report |
Tests: tests/ingest 242 passed.
