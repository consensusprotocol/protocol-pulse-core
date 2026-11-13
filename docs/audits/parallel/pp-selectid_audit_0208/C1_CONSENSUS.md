# pp-selectid audit of one window per moment: cycle 1 consensus (synthesis by the pp-selectid session, 02:17 ET Nov 13)

**Run.** C1_STEP.diff covers ledger_build.py, package.py, context_integrity.py, speakers.py and test_ledger_build.py.
No P0.
- grok-4.20-0309-reasoning (xAI): no findings, "SHIP: yes".
- qwen/qwen3.8-27b (Heimdall, effort none): two P1s on the lookups; "SHIP: no".
- z-ai/glm-5.3-flash (Heimdall, effort none): P1s on the lookups, the report schema, and consumers outside the diff.
  SHIP yes with conditions.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | the Source lookup existed in three copies with different failure modes: package.src_of raised KeyError on a missing key, while speakers.attribute_package used .get() and passed None (qwen P1 x2, glm P1) | IMPLEMENTED: ONE rule, context_integrity.source_for(x, sources) = sources[x.get("source_key") or x["video_id"]], which raises KeyError (fail closed). package.src_of and contexts_from_sources use it. speakers.attribute_package catches the KeyError, so the speaker is "unknown", not measured, with no call made; it never claims a name and never takes another Source. Test: a segment whose source_key is not in sources makes the gate's context check raise, and gives an unknown, unmeasured speaker |

## Unique findings: answered or kept (each verified)

- **glm P1 (coverage: consumers outside the diff may still look up by video id):** ANSWERED. A grep of every
  `sources[` / `sources.get(` in pipeline/ and the drivers finds the medley path's lookups only in source_for (via
  package.src_of, contexts_from_sources) and speakers. The other hits belong to other dictionaries that never see
  these Sources:
  - select_by_id.py: the older selector's own universe sources;
  - rank.py: a list named sources;
  - select_passages.py: the render's acquisition file paths.
  package_pin and the pin never read Sources. The render (the integrator's) uses each pin segment's video_id and
  times, and decodes its own window.
- **glm P1 (the report schema: window_records becomes a list, plus new counts):** KEPT. The report is read only by the
  driver's log line and saved in inputs.json as proof; no code consumes it.
- **qwen ("unmeasured speaker attribution violates L-m"):** KEPT, as disposed in audit 0007 K2. "unknown" with
  measured false claims no name; L-m governs gates, and this record is not one.

## Verification

- 11 offline suites, 234 tests OK; regression_test.sh 26 PASS | 0 FAIL | 5 WARN (run before this fix).
- test_ledger_build, test_medley, test_speakers and test_gates are re-run after the fix: OK.
