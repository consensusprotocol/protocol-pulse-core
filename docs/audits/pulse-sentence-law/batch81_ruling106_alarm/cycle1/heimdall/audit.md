# Heimdall audit

**Question:** Batch 81 = RULING 106 (d) (orchestrator 2026-11-14 '20:21', verbatim): "THE ALARM. If something that needs me or PBX has waited 45 minutes (a ready video not launched, a cap reached, a real outage, every build refused), the INTEGRATOR sends ONE plain text message to PBX's Telegram review chat through the pipeline's own sender: 'PULSE CHECK NEEDS A DECISION: <one sentence>. Waiting since <time>.' At most one per issue and at most one an hour in total; nothing for routine progress." and "YOUR SIDE OF (d): the one-line Telegram text sender (reuse telegram.py's sender; a plain message, no media, no release authorisation; rate limits enforced in code; a test that a second alarm inside the hour is refused)".
The change: telegram.send_alarm(issue, sentence, waiting_since) builds exactly 'PULSE CHECK NEEDS A DECISION: <sentence>. Waiting since <time>.' and sends it through the existing _send_bot_api("message", ...) (the approval chat; credentials read by name, never printed). Under an exclusive fcntl lock on an append-only log (data/pulse_check/alarms.jsonl) it refuses (AlarmRefused, nothing sent): an issue already in the log; any alarm within ALARM_GAP_S (3600 s) of the last logged one; an empty or multi-line issue, sentence or time. An explicit Telegram refusal (SendRejected) is not logged (nothing was sent, it may be retried); any other failure is logged as outcome "unknown" and counts (never resent). Tests: test_alarm (5) with a fake sender and a temporary log; they fail on the old file.
FIND: a path that sends two alarms inside an hour, or two for one issue; a race between two processes; a key or token that can be printed or logged; anything that touches a run, the release ledger or media. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0008
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] A SendRejected after the send actually reached Telegram (e.g. response lost after Telegram accepted) is not logged, so a retry can send two alarms for one issue inside the hour, violating 'at most one per issue and at most one an hour'. (agree: 1)

## Added in cross-examination (not voted on)
- none
