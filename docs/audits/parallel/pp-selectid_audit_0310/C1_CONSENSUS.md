# pp-selectid audit 0310 (the render's STAND_ALONE at the pin stage): cycle 1 consensus

Synthesis by the pp-selectid session, 03:13 ET Nov 13, written before cycle 2.

**Run.** C1_STEP.diff covers package.py, package_pin.py and test_medley.py. No P0. Verdicts:
- grok-4.20-0309-reasoning (xAI): no P0 and no P1, "SHIP: yes";
- qwen/qwen3.8-27b (Heimdall, effort none): "SHIP: yes with conditions";
- z-ai/glm-5.3-flash (Heimdall, effort none): "SHIP: yes with conditions".

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | Is stand_alone_check an exact copy of the render's call? Do the EDL shape and the fixed subject match (glm P1-1, qwen P1-1)? | VERIFIED, and stated in the docstring. pipeline/stand_alone.py is byte-identical to main's at 5be6f301 (`diff` exit 0). check_edl (stand_alone.py:99-123) passes `s.get("text")` to opener() and topical(). Channel and duration go only into the scorer's passages, which are unused with rate=None. The labels come from the order (`clip_{index:02d}`). The subject: main run_fresh.stand_alone_subject returns subject_terms("", "bitcoin") for a bound pinned moments EDL labelled 'bitcoin', and package_pin.to_pin sets "label": "bitcoin" for every moments pin (package_pin.py:179). The reproduction test pins the render's own verdicts on the held pin (run_log.txt lines 47-49). |
| K2 | No test drives the FAIL path through inventory()'s evidence rows (glm P1-3) | IMPLEMENTED: test_inventory_writes_a_FAIL_row_with_its_evidence. inventory(stand=<failing check>) writes a FAIL row with one evidence line per segment; with stand=None the row is absent, which refuses the pin. check_edl always gives every row an "opener" and a "topic" dict, each with "why" (stand_alone.py:116-121), so the evidence lines cannot raise. |
| K3 | Is `import stand_alone` GPU-free (glm P2-4)? | VERIFIED. stand_alone.py imports only `re` at module level, and canon lazily inside _words(). The GPU scorer lives in story_semantics.LocalLLM, which stand_alone never imports; only the render's rate() closure in run_fresh imports it. |
| K4 | out["usable"] changed meaning (glm P2-2) | IMPLEMENTED: out["usable"] is again the count after usable(). The moments left out are counted in out["no_role"] and on the log line ("N usable, M of them left out ..."). |

## Unique findings: answered or kept

- **qwen P1-2 and P1-3 (stricter than the render):** KEPT, as intended and stated in the docstrings. With no scorer, a conjunction or reply-fragment opener fails closed, so the pin stage never seals a line-up that the render's scorer would have to rescue. A pronoun opener stays in play, and test_a_moment_opening_on_a_conjunction_or_reply_fragment_has_no_role covers that.
- **qwen P2-4 (machine-parseable rows):** KEPT as text. The row's "status" is what is machine-checked (gate_problems); the rows are human evidence in the render's own wording.
- **qwen P2-5 (the comment is dense):** DONE. The MEDLEY_GATES comment is three lines, one per origin.
- **qwen P2-6 (the test is coupled to the run log):** KEPT. The test pins the render's verdicts as constants. The log is cited, not read.
- **qwen P2-7 (Rig is not in the diff):** ANSWERED. Rig is the existing build harness in test_medley.py (class Rig, line 414), unchanged here.
- **glm P2-1 (MEDLEY_GATES for other shapes):** ANSWERED. required_gates adds MEDLEY_GATES only when shape == "medley" (package_pin.py:37). The integrator's check_pin_only calls gate_problems with REQUIRED_GATES only, so older pins still recompute.
- **glm P2-3 and P2-5:** recorded as verified by the reviewer; no change.

## Verification

- test_medley 51 OK (44 existing, 6 new in cycle 1, 1 new for K2).
- The other 10 suites: OK (run before cycle 2).
