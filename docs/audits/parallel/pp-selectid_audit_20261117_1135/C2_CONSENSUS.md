# Cycle 2 consensus (pp-selectid_audit_20261117_1135, rulings 136 / 137 stage 1)

SEATS ANSWERED: 3 of 3 (qwen3.8-27b, gpt-oss-20b, gemma-4-31b-it). gemma: P0/P1 none. qwen: P0/P1 none, two P2.
gpt-oss: one claimed P1, REFUTED below.

## Findings
- gpt-oss [P1] "build() passes never_empty and flagged_today to _build(), which does not accept them: TypeError":
  REFUTED. They are the wrapper's keyword-only parameters (inspect.signature(build) = (*args, never_empty=False,
  flagged_today=0, **kw)), bound there and never part of **kw; _build has no never_empty parameter. NEW test
  test_the_wrapper_forwards_only_what_the_search_takes mocks _build with its REAL signature (autospec, which raises
  TypeError on any unknown keyword) and records the forwarded keywords: ["lineups", "log"], then
  ["lineups", "log", "soft"]. 7 tests in test_ruling_137 pass.
- qwen [P2] flag_sentence raises KeyError on a code not in STEP_A_SOFT: DECLINED. It is called only when soft_a holds,
  i.e. every code of the package is in STEP_A_SOFT; a KeyError there would surface a real bug, where a raw code would
  break ruling 138 (3) ("no codes").
- qwen [P2] the wrapper's never-empty log line reads kw.get("log") and would miss a positional log: DECLINED. Every
  caller passes log by keyword (the driver: log=say); the line would go to stdout, never a gate.

## Result
CLEARED to land. Suites 41 files / 880 tests by exit code; mutations 15 of 16 killed (P2 an equivalent mutant).
