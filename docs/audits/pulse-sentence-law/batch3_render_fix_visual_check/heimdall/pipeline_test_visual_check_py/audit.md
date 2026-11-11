# Heimdall audit

**Question:** Protocol Pulse news-video pipeline. Changes: (1) pipeline/transitions.py renamed pulse_transitions.py because render16 puts a legacy folder with its own transitions.py first on sys.path (import shadowing); (2) a contact sheet of the finished video plus a 6-line visual checklist answered by two vision models, any no/missing/unparseable answer = HOLD, added on top of existing gates, never replacing one; (3) fade-out retry made transactional (a moved cut is kept only if the re-prepared clip passes the whole contract, else original cut and clip restored); (4) one function decides whether cuts are machine-placed; (5) Telegram delivery attaches the sheets. Find real bugs: wrong pass/fail decisions, a gate that can pass when it should hold, crashes, lost files, state left inconsistent after a failure. Only state what you can verify from the diff. (this chunk: pipeline/test_visual_check.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0122
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/test_visual_check.py:82** The skipUnless condition only checks for .env and HEIMDALL_API_KEY, but not for the existence of the required fixture SHEET_NOV10. If the fixture is missing, the test will run and crash with FileNotFoundError instead of skipping.
  - evidence: `@unittest.skipUnless(os.path.exists(os.path.join(REPO, ".env")) and
                     any(l.startswith("HEIMDALL_API_KEY") for l in open(os.path.join(REPO, ".env"))),
                     "Heimdall`
  - fix: Add os.path.exists(SHEET_NOV10) to the skipUnless condition.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[low] pipeline/test_visual_check.py:83** The .env file is opened without being closed, leaking a file handle.
  - evidence: `any(l.startswith("HEIMDALL_API_KEY") for l in open(os.path.join(REPO, ".env")))`
  - fix: Use a context manager: with open(os.path.join(REPO, ".env")) as f: any(l.startswith("HEIMDALL_API_KEY") for l in f).
  - raised by deepseek:F3; agree: deepseek, qwen27b
- **[low] pipeline/test_visual_check.py:82** File handle opened in the @unittest.skipUnless decorator is never closed; the descriptor leaks for the lifetime of the process (or until GC collects the generator).
  - evidence: `any(l.startswith("HEIMDALL_API_KEY") for l in open(os.path.join(REPO, ".env")))`
  - fix: Use a context manager or close explicitly, e.g.:
with open(os.path.join(REPO, ".env")) as f:
    has_key = any(l.startswith("HEIMDALL_API_KEY") for l in f)
and pass has_key to skipUnless.
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[low] pipeline/test_visual_check.py:88** TestVisionMustFail is skipped only when the API key is absent, but it does not verify that the fixture file SHEET_NOV10 exists. If the key is present but the fixture was removed or the path is wrong, V.ask_panel will raise FileNotFoundError (or an I/O error) and the test will ERROR rather than skip, masking the real cause.
  - evidence: `ok, per = V.ask_panel(SHEET_NOV10, "9x16")`
  - fix: Add os.path.exists(SHEET_NOV10) to the skipUnless condition, or add a self.skipIf at the top of the test method.
  - raised by qwen27b:F2; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F1 [medium] The test passes a non-existent work directory to contact_sheet without creating it, which can cause a FileNotFoundError crash if contact_sheet expects the directory to exist. (agree: 0)

## Added in cross-examination (not voted on)
- deepseek: [low] Image file handle is not closed after reading its size.
