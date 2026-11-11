# Heimdall audit

**Question:** Protocol Pulse news-video pipeline. Changes: (1) pipeline/transitions.py renamed pulse_transitions.py because render16 puts a legacy folder with its own transitions.py first on sys.path (import shadowing); (2) a contact sheet of the finished video plus a 6-line visual checklist answered by two vision models, any no/missing/unparseable answer = HOLD, added on top of existing gates, never replacing one; (3) fade-out retry made transactional (a moved cut is kept only if the re-prepared clip passes the whole contract, else original cut and clip restored); (4) one function decides whether cuts are machine-placed; (5) Telegram delivery attaches the sheets. Find real bugs: wrong pass/fail decisions, a gate that can pass when it should hold, crashes, lost files, state left inconsistent after a failure. Only state what you can verify from the diff. (this chunk: pipeline/run_fresh.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0230
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/run_fresh.py:519** Transactional retry can unnecessarily modify a cut point that was already clean. When sides contains both 'in' and 'out', and the first side's fix resolves BOTH fade errors, the code still enters the inner loop for the second side. The acceptance condition `not any(e.startswith(f"fade-{side}") for e in d.get("errors") or [])` is vacuously true (no such error exists), so the first candidate for the second side is accepted, changing cut_out (or cut_in) to a different position than the sentence-law-placed value. The final contract check may still pass, so the function returns True with a modified cut that was never in error. This leaves the EDL in a state inconsistent with the sentence-law placement and can alter the G16 re-check input.
  - evidence: `if not any(e.startswith(f"fade-{side}") for e in d.get("errors") or []):
    trial, fixed = t2, True
    break`
  - fix: Before the inner candidate loop for each side, check whether that side's fade error is still present in the current `d`. If it is already absent, skip the side entirely (set fixed=True and continue to the next side) without trying any candidates. Example: add at the top of the `for side in sorted(sides):` body: `if not any(e.startswith(f"fade-{side}") for e in d.get("errors") or []): continue`
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F2 [low] write_report crashes with TypeError if a per-model answer row `r` is not a dict (e.g. a bare string from a vision-model response). `r['answer']` raises `TypeError: string indices must be integers` (or `TypeError: 'NoneType' object is not subscriptable` if r is None). This prevents REPORT.md from being written, which may block downstream consumers that expect the report file to exist. (agree: 1)

## Added in cross-examination (not voted on)
- none
