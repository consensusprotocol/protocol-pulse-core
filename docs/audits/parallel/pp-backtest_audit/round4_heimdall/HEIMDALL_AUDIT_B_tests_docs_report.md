# Heimdall-only audit, package B_tests_docs_report (spend freeze 05:30 ET; reviewers: heimdall-deepseek-v4.1-flash, heimdall-glm-5.3-flash, heimdall-qwen3.8-27b)

| cycle | back-end | measured | findings / rulings | verdict | s | USD |
|---|---|---|---|---|---|---|
| 1 | heimdall-deepseek-v4.1-flash | NOT MEASURED: JSONDecodeError: Expecting value: line 1 column 1 (char 0) | - | - | - | - |
| 1 | heimdall-glm-5.3-flash | NOT MEASURED: InternalServerError: Error code: 503 - {'error': {'code': 503, 'message': 'The marketplace is restarting before this res | - | - | - | - |
| 1 | heimdall-qwen3.8-27b | NOT MEASURED: JSONDecodeError: Expecting value: line 1 column 1 (char 0) | - | - | - | - |
| 2 | heimdall-deepseek-v4.1-flash | NOT MEASURED: SpendStop: spend guard: 0.05 spent + 1.65 in flight + worst case 0.32 for heimdall-deepseek-v4.1-flash > cap 2.00 USD | - | - | - | - |
| 2 | heimdall-glm-5.3-flash | NOT MEASURED: JSONDecodeError: Expecting value: line 1 column 1 (char 0) | - | - | - | - |
| 2 | heimdall-qwen3.8-27b | yes | 0 | MEDIUM | 90.1 | 0.004215 |

Consensus (CONFIRMED by >= 2 of the 3 in cycle 2): 0 of 0 cycle-1 findings.

## Every cycle-1 finding and its cycle-2 votes


## Added in cycle 2 (one reviewer each; not consensus)

- heimdall-qwen3.8-27b: MEDIUM docs/audits/BACKTEST_SUPPLY_REPORT.md:497 vs docs/audits/parallel/pp-backtest_ANALYSIS.md:206: The hand-written analysis (stated as section 5 of the report) contradicts the report's own generated table on the local witness back-end: 19/15 vs 23/18 items, and 6/15 vs 8/18 agreement.
- heimdall-qwen3.8-27b: MEDIUM docs/audits/BACKTEST_SUPPLY_REPORT.md:539 vs docs/audits/BACKTEST_SUPPLY_REPORT.md:583: Section 0 claims 25 items were not run, but the report's own section 9 table states 23/48 items were run (implying 25 not sent). However, the table also states 18 measured, 0 not sent (spend guard), 5 failed. 23 - 18 - 5
- heimdall-qwen3.8-27b: LOW docs/audits/BACKTEST_SUPPLY_REPORT.md:539 vs docs/audits/BACKTEST_SUPPLY_REPORT.md:497: The 'median s per call' for the local judge is not explicitly listed in the table row provided in the evidence (it is '88.1' in the analysis but the table cell is empty or missing in the diff? No, the table has '88.1' in
