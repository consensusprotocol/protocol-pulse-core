# Heimdall-only audit, package A_code (spend freeze 05:30 ET; reviewers: heimdall-deepseek-v4.1-flash, heimdall-glm-5.3-flash, heimdall-qwen3.8-27b)

| cycle | back-end | measured | findings / rulings | verdict | s | USD |
|---|---|---|---|---|---|---|
| 1 | heimdall-deepseek-v4.1-flash | yes | 7 | No path was found where a failed/empty/malformed model reply is recorded as NONE, pass, accepted, available or agreement (run.py/lineup.py/witness.py all raise  | 544.7 | 0.008385 |
| 1 | heimdall-glm-5.3-flash | NOT MEASURED: InternalServerError: Error code: 503 - {'error': {'code': 503, 'message': 'The marketplace is restarting before this res | - | - | - | - |
| 1 | heimdall-qwen3.8-27b | NOT MEASURED: APIConnectionError: Connection error. | - | - | - | - |
| 2 | heimdall-deepseek-v4.1-flash | yes | 0 | x | 1139.0 | 0.003938 |
| 2 | heimdall-glm-5.3-flash | NOT MEASURED: InternalServerError: Error code: 503 - {'error': {'code': 503, 'message': 'The marketplace is restarting before this res | - | - | - | - |
| 2 | heimdall-qwen3.8-27b | yes | 7 | Only deepseek#3 and deepseek#5 are confirmed defects. The others are either refuted due to misunderstandings of the control flow (lease gate, score stages, ledg | 95.9 | 0.004261 |

Consensus (CONFIRMED by >= 2 of the 3 in cycle 2): 0 of 7 cycle-1 findings.

## Every cycle-1 finding and its cycle-2 votes

- [deepseek#1] LOW L-x: no vendor/model name outside the provider config: Vendor / model names hard-coded outside providers.py -- confirmed 0, refuted 1, unsure 0
- [deepseek#2] MEDIUM GPU use outside the lease gate: GPU0 lease gate lives only in available(); call_backend, the function that actually sends to the local model, does not re-check it. -- confirmed 0, refuted 1, unsure 0
- [deepseek#3] LOW silently truncated prompt: The 'cut prompt is never accepted' check under-counts the characters actually sent for no_tools back-ends. -- confirmed 1, refuted 0, unsure 0
- [deepseek#4] MEDIUM a stage blamed in score.py the record never reached: score.py can blame LAYOUT_ELIGIBILITY / WINDOWS for a candidate the record never decided. -- confirmed 0, refuted 1, unsure 0
- [deepseek#5] LOW failed reply not counted: A failed A/B sample is dropped when the same item was also measured OK, so a failure is counted neither as failed nor as measured. -- confirmed 1, refuted 0, unsure 0
- [deepseek#6] LOW L-l deciding field not enforced: parse_oracle does not enforce that LINEUPS carries an empty none_reason, so a self-contradicting reply passes as LINEUPS. -- confirmed 0, refuted 1, unsure 0
- [deepseek#7] LOW spend-guard hole: The spend ledger aborts on a corrupt line instead of failing closed / skipping. -- confirmed 0, refuted 1, unsure 0

## Added in cycle 2 (one reviewer each; not consensus)

- heimdall-deepseek-v4.1-flash: LOW n/a: run.py --no-judge runs are reported as JUDGE_FAILED, a stage that never ran
