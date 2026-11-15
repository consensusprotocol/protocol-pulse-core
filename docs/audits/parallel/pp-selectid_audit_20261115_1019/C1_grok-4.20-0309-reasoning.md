# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 33 s finish=stop usage in 7013 / out 729 usd_reported=0.018562 usd~0.053 (upper-bound price)

**CODE AUDIT REPORT — pp-selectid-20261115_1019 (proof_ledger + test_ruling_107_guard)**

**Summary of change**: The patch renames the word-pass refused list to `wp_refused` to eliminate a rebinding collision with `start_refused()` later in `main()`. It moves the `next_attempt` (Ruling 95) calculation immediately after `build_inputs()` (still before any spend-check rebinding or router decision), stores the result in `inputs.json` even on “nothing new” paths, and updates the driver test harness plus adds an explicit test that the refused count is taken from the inputs alone. The patch is explicitly labeled “Reporting only: no gate, verdict or selection changes.”

**Compliance with governing laws**:
- All core media laws (SENTENCE LAW, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, L-a through L-l, CREDITS, L-b EDGE WORDS WHOLE, L-c DISSENT IS RIGHT UNTIL DISPROVED, L-d PROTECTED PREVIEW, L-e PUNCTUATED BEFORE READ, L-f CHANNELS FIRST, L-g WRITTEN FORMS, L-h TEXT READ AS SPOKEN, L-i THE CLAIM IS THE EVENT, L-j RELEASE IS AUTHORISED ON THESE BYTES, L-k ONE CANONICAL FORM, L-l A MODEL REPLY COUNTS ONLY WHOLE, LAW 20/M2, M12 FAIL CLOSED, LAW 22) are untouched. No selection logic, gate thresholds, EDL bytes, render paths, punctuation restoration, cluster ordering, canon.py usage, or v2f reference rendering is altered.
- The change lives entirely inside test/proof ledger reporting. No new renderer, compositor or selector (M1). No DB schema changes, therefore the index requirement is irrelevant. Smallest diff principle satisfied.
- No violations found.

**Findings**:
- **[P2]** Surviving mutation (the one that forces `res["next_attempt"] = {}` late in the build record on the router path) is not killed. The new test only exercises the early “nothing-new” path; the harness short-circuits before a full router build populates the final `res` dict. This leaves a coverage gap for the exact bytes that would be written to a real proof ledger JSON when a build proceeds. The original defect was also a test-surviving scoping bug; repeating that pattern is undesirable. Must be fixed before merge.
- **[P3]** The added multi-line comment in `proof_ledger.py:12-13` and the test docstring are excessively long and contain build-specific timestamps (“10:10 ET Nov 15”, “Build 6”). While they document the history correctly, they reduce readability and will age poorly. Move detailed narrative to the commit message or a ruling appendix; keep source comments concise.
- **[P3]** `except Exception as e: # noqa: BLE001` is used twice for the reporting path. Acceptable here because the contract is “a report, never the build”, but a narrower exception list would be preferable for future maintainability.

No P0 or P1 defects. The name-collision fix is correct, `next_try` is computed from the intended inputs, no downstream variable is mutated before the build record is populated, the test harness extension is sound, and all new code passes the existing 685-test suite plus the added ruling-95 case. The single P2 item blocks clean merge under the quality gate.

P1_OR_WORSE: 1