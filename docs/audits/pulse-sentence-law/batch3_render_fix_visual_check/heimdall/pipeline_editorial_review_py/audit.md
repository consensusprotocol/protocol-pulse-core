# Heimdall audit

**Question:** Protocol Pulse news-video pipeline. Changes: (1) pipeline/transitions.py renamed pulse_transitions.py because render16 puts a legacy folder with its own transitions.py first on sys.path (import shadowing); (2) a contact sheet of the finished video plus a 6-line visual checklist answered by two vision models, any no/missing/unparseable answer = HOLD, added on top of existing gates, never replacing one; (3) fade-out retry made transactional (a moved cut is kept only if the re-prepared clip passes the whole contract, else original cut and clip restored); (4) one function decides whether cuts are machine-placed; (5) Telegram delivery attaches the sheets. Find real bugs: wrong pass/fail decisions, a gate that can pass when it should hold, crashes, lost files, state left inconsistent after a failure. Only state what you can verify from the diff. (this chunk: pipeline/editorial_review.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0033
## Consensus findings (majority of panel agrees)
- **[high] pipeline/editorial_review.py:93** The new integer-index check uses isinstance(..., int), but bool is a subclass of int in Python. A clip judgment with index true or false therefore passes validation. Since True == 1 and False == 0, sorted boolean indices can compare equal to the expected CLIP numbers, so the validator can accept a malformed judgment and let the gate pass when it should hold.
  - evidence: `if not all(isinstance(j, dict) and isinstance(j.get("index"), int) for j in clips):`
  - fix: Reject booleans explicitly, e.g. use `type(j.get("index")) is int` or `isinstance(j.get("index"), int) and not isinstance(j.get("index"), bool)`.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[medium] pipeline/editorial_review.py:92** isinstance(j.get("index"), int) accepts Python booleans because bool is a subclass of int. A vision-model response containing {"index": true} or {"index": false} passes the guard, and because True==1 / False==0 in Python, the subsequent sorted(...) == want comparison can also succeed. This lets a malformed (non-integer) index slip through the validator, turning what should be a HOLD (unparseable answer) into a PASS.
  - evidence: `if not all(isinstance(j, dict) and isinstance(j.get("index"), int) for j in clips):`
  - fix: Exclude booleans explicitly: isinstance(j.get("index"), int) and not isinstance(j.get("index"), bool)
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
