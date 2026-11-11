# Heimdall audit

**Question:** Protocol Pulse news-video pipeline, auto mode story selection and verification. Changes: (1) candidates whose COUNTED evidence includes the same statement (same video, shared supporting chunk, >=5 consecutive shared words in the evidence quotes) are merged into one event: one derived query, verdicts pooled one per video, not-counted verdicts re-judged against the merged query within a budget, same coverage decision; (2) a story ledger: an auto run delivered HOLD FOR APPROVAL in both formats records its counted evidence; later runs exclude any candidate resting on the same statement; (3) the 9:16 letterbox check asks two vision models about ONE frame per shot of every talking-head segment; a non-screen shot called letterboxed or unanswered fails. Find real bugs: false merges of different events, a delivered story selected again, a story wrongly excluded, a letterbox that can pass, crashes, state left inconsistent. Only state what you can verify from the diff. (this chunk: scripts/pulse_check_run.sh)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0071
## Consensus findings (majority of panel agrees)
- **[high] scripts/pulse_check_run.sh:77** A failure in story_ledger.record_if_approved (e.g. I/O error writing the JSONL, a KeyError, or any exception) after telegram.deliver_run has already succeeded causes the python process to exit non-zero. The shell then reports 'Telegram delivery FAILED' and exits 70, even though the messages were already sent. This misreports the failure, can trigger a duplicate delivery on retry, and leaves the operator believing the run was not delivered.
  - evidence: `python3 -c "import sys, telegram, story_ledger; r = telegram.deliver_run(sys.argv[1]); print('delivered:', [m.get('message_id') for m in r['messages']]); e = story_ledger.record_if_approved(sys.argv[1`
  - fix: Wrap the story_ledger call in a try/except so its failure does not change the process exit code. For example: `try: e = story_ledger.record_if_approved(...); print(...) except Exception as ex: print('story ledger: FAILED -', ex, file=sys.stderr)` and ensure the script's exit code reflects only the deliver_run result. Alternatively, split into two separate python invocations so a ledger failure cannot mask a successful delivery.
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[medium] scripts/pulse_check_run.sh:77** If the story_ledger module is missing or has an import-time error, the combined `import sys, telegram, story_ledger` statement fails before deliver_run is ever called. The script then reports 'Telegram delivery FAILED' and exits 70, but the real cause is a missing/broken ledger module, not a Telegram problem. This makes diagnosis harder and couples the delivery path to the ledger module's availability.
  - evidence: `import sys, telegram, story_ledger; r = telegram.deliver_run(sys.argv[1]);`
  - fix: Import story_ledger separately (or inside a try/except) so that a ledger import failure does not prevent delivery. E.g. `import sys, telegram; r = telegram.deliver_run(...); ...; try: import story_ledger; e = story_ledger.record_if_approved(...) except Exception as ex: print('story ledger: skipped -', ex, file=sys.stderr)`.
  - raised by qwen27b:F2; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
