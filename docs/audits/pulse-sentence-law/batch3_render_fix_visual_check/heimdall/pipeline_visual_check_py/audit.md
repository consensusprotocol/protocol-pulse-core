# Heimdall audit

**Question:** Protocol Pulse news-video pipeline. Changes: (1) pipeline/transitions.py renamed pulse_transitions.py because render16 puts a legacy folder with its own transitions.py first on sys.path (import shadowing); (2) a contact sheet of the finished video plus a 6-line visual checklist answered by two vision models, any no/missing/unparseable answer = HOLD, added on top of existing gates, never replacing one; (3) fade-out retry made transactional (a moved cut is kept only if the re-prepared clip passes the whole contract, else original cut and clip restored); (4) one function decides whether cuts are machine-placed; (5) Telegram delivery attaches the sheets. Find real bugs: wrong pass/fail decisions, a gate that can pass when it should hold, crashes, lost files, state left inconsistent after a failure. Only state what you can verify from the diff. (this chunk: pipeline/visual_check.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0156
## Consensus findings (majority of panel agrees)
- **[high] pipeline/visual_check.py:149** ask_vision crashes on any network or HTTP error instead of returning empty answers (HOLD). The urlopen call is not wrapped in try/except, so a URLError, HTTPError (4xx/5xx), or socket.timeout propagates and kills the pipeline. The function's own docstring promises 'never a crash' and the pipeline design requires any failure to HOLD, not abort.
  - evidence: `    for _ in range(attempts):
        raw = json.loads(urllib.request.urlopen(req, timeout=timeout).read())`
  - fix: Wrap the urlopen call in try/except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, OSError). On exception, append the error to `tries` and continue the retry loop; after all attempts, return ({}, {"model": model, "unparseable": tries}) so the caller sees empty answers and HOLDs.
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[high] pipeline/visual_check.py:183** verdict crashes with AttributeError if the vision model returns a non-dict value for a checklist key (e.g. {"answers":{"credits_round_and_match":"yes"}} instead of the expected nested object). The expression (answers.get(k) or {}) evaluates to the string 'yes' (truthy), and calling .get('answer','') on a str raises AttributeError, crashing the gate instead of HOLDing.
  - evidence: `        a = str((answers.get(k) or {}).get("answer", "")).strip().lower()`
  - fix: Guard the value before calling .get: val = answers.get(k); if not isinstance(val, dict): val = {}; a = str(val.get('answer','')).strip().lower(). This treats any malformed entry as 'missing' (HOLD) rather than crashing.
  - raised by qwen27b:F2; agree: deepseek, qwen27b
- **[medium] pipeline/visual_check.py:122** _key() raises FileNotFoundError if the .env file is absent, or StopIteration if no line starts with HEIMDALL_API_KEY. Neither is caught, so a misconfigured environment crashes the pipeline with an opaque traceback instead of a clear error or a HOLD.
  - evidence: `    return next(l.split("=", 1)[1].strip().strip('"\'') for l in open(env) if l.startswith("HEIMDALL_API_KEY"))`
  - fix: Wrap in try/except (FileNotFoundError, StopIteration) and raise a clear RuntimeError('HEIMDALL_API_KEY not found in .env') or return a sentinel that causes ask_vision to HOLD. Also close the file handle (use a with-block).
  - raised by qwen27b:F3; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- deepseek: [high] _probe_duration uses check=True and no try/except, so ffprobe failure (missing/corrupt video, timeout) raises CalledProcessError/TimeoutExpired and aborts the pipeline instead of HOLDing.
- deepseek: [high] ask_vision does not catch JSONDecodeError when the HTTP response body is not valid JSON (e.g., an HTML error page), so it crashes instead of retrying and eventually HOLDing.
- deepseek: [medium] ask_vision assumes the decoded HTTP response is a dict; if the API returns a JSON list or string, raw.get raises AttributeError and crashes instead of HOLDing.
- deepseek: [medium] The full-resolution first-frame timestamp for a talking-head segment can exceed the segment's end when the previous segment overlaps and the current segment is short, so the grabbed still is from the wrong segment and can cause a wrong visual-check decision.
- deepseek: [medium] _key() raises IndexError if a line starts with HEIMDALL_API_KEY but has no '=' character, crashing instead of a clear error or HOLD.
