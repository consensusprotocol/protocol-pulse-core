# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 45 s finish=stop usage in 10186 / out 889 usd_reported=0.027111 usd~0.073 (upper-bound price)

**Audit Summary for pp-selectid-20261115_1436 (hook115 measurement driver)**

The diff adds a self-contained measurement tool (`tests/package/hook115.py`) + offline unit test to implement Ruling 115 (3) exactly as written. It constructs `prompt_v2` (original `HOOKS_PROMPT` first paragraph + PBX examples block + unchanged `HOOK_QUESTION` contract), runs the ten moments alone (cache=None, seed=7, isolated router with `coherence_verdict:hook` forced to a single model, own spend ledger), computes the exact pass rule required by the ruling ("all 5 approved own >= 4 AND all 5 negatives <= 3"), does the leave-one-out variant to surface copying, stays under the $0.50 cap, writes only to its own proof/ directory, and produces the mandated REPORT.md before any production use. No pipeline/ code is touched; the hook job continues to use ruling 115 (1)'s prompt and contract. All six explicit "PLEASE CHECK" items pass.

No violations of any Governing Law were found (L-a through L-l, M2, M12, LAW 20/22, SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-c dissent-is-right, L-d protected preview, L-e punctuated-before-read, L-f channels-first, L-g written forms, L-h text-read-as-spoken, L-i claim-is-the-event, L-j release-authorised-on-these-bytes, L-k one-canonical-form, L-l model-reply-counts-only-whole). The added code never touches EDLs, transcripts, cuts, renders, gates, selection locks, edge-word fidelity, sign-off voiceovers, canonicalisation, release attestation, or any production cache/ledger. All model calls are isolated, fail-closed where relevant, and the measurement itself is not part of any release gate.

**Findings**

[P2] `hook115.py:64` and `negatives()` – test depends on live proof files (`hook112.build_records(..., since="ledger_20261113_161500")` + `all_ratings`). While the ruling explicitly requires these exact negatives, the unit test (`test_hook115.py:254`) is therefore not hermetic. A missing or mutated proof package breaks CI. Mock the ledger read for the unit test (the integration run can stay).

[P2] `hook115.py:88` – `partition("\n\n")` to splice the examples block after the first paragraph is fragile. If `HOOKS_PROMPT` ever gains an earlier blank line or formatting change, the splice point moves silently. Use `split("\n\n", 1)` for an explicit "after first paragraph only" contract.

[P3] Hard-coded magic values (STOP_USD=0.25, LIMIT_USD=0.55, SEED=7, the exact NEGATIVES list and ledger timestamp, model strings, SPEND_H115.json path, OUT directory). These should be named constants at module level with comments tying them to the ruling cap and the "stop early" safety margin.

[P3] `hook115.py:184` – `print(open(...).read()[:3000])` is a quick-and-dirty console dump. If the report grows beyond 3000 chars the truncation hides part of the "every rating" section the ruling asks to see. Use `pathlib` + explicit `print(report)` or let the caller read the generated REPORT.md.

[P3] Minor style: `sys.path.insert(0, ...)` twice, duplicate `import unittest.mock` inside `if __name__`, and a 183-line test driver that mixes real LLM spend with offline verification. Could be split into a lightweight measurement script under `tools/audits/` rather than living next to unit tests, but this is cosmetic given the "report before use" mandate.

No P0 or P1 defects. The implementation is precise, auditable, fail-closed where required, smallest reasonable diff for the ruling, and ready for the parallel review by the other two models. The generated REPORT.md (once run) can be attached to the merge request as the required evidence before any production hook-model change.

P1_OR_WORSE: 0