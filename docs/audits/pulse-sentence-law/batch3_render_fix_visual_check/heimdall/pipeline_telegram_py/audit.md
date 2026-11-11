# Heimdall audit

**Question:** Protocol Pulse news-video pipeline. Changes: (1) pipeline/transitions.py renamed pulse_transitions.py because render16 puts a legacy folder with its own transitions.py first on sys.path (import shadowing); (2) a contact sheet of the finished video plus a 6-line visual checklist answered by two vision models, any no/missing/unparseable answer = HOLD, added on top of existing gates, never replacing one; (3) fade-out retry made transactional (a moved cut is kept only if the re-prepared clip passes the whole contract, else original cut and clip restored); (4) one function decides whether cuts are machine-placed; (5) Telegram delivery attaches the sheets. Find real bugs: wrong pass/fail decisions, a gate that can pass when it should hold, crashes, lost files, state left inconsistent after a failure. Only state what you can verify from the diff. (this chunk: pipeline/telegram.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0128
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [medium] _photo_ok can raise an unhandled exception (PIL.UnidentifiedImageError, OSError, etc.) if the contact-sheet file exists on disk but is not a valid image (e.g. 0-byte file left by a crashed render, truncated JPEG). This is a new crash vector: the old code simply called send("photo", p, …) without inspecting the file. Because the exception propagates out of the for-loop, the delivery-record JSON is never written, yet the video has already been sent to Telegram. The run is left with a delivered video but no TELEGRAM_DELIVERY*.json, so a retry would re-send the video and the operator has no audit trail of the first send. (agree: 1)

## Added in cross-examination (not voted on)
- none
