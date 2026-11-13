# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1744
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 761 s finish=stop usage in 21318 / out 20945 usd~0.378 (upper-bound price)

# Audit: pp-selectid-1744 — rulings 68/72 lock pre-check

Scope: I verified only what the diff shows. `attest.diff/carry_class/quotes`, `package_pin.seal`, `package._package`, and the integrator's service are outside the diff; where the code depends on them I say so.

## P0

None found.

## P1

**P1-1 — `lock_precheck.answer` can adopt a ruling-72 entry written by a *different request* whose outcome is `error`, and `check` then never asks again — but worse: a stale `error` entry from an earlier request permanently shadows nothing, yet a *stale pass* from an older request is reused even when the integrator's advice ("send the candidate texts BEFORE the paid verdicts") implies freshness.** Actually, re-reading: reuse of an on-file pass is explicitly the documented behavior ("An answer already on file is used (never an error)"), and the test `test_answers_on_file_are_used_and_nothing_is_asked` pins it. The real issue is subtler:

**P1-1 (final) — `check()`'s reuse path can mix answers from different requests, and the mixed set is never re-validated as one line-up.** `lock_precheck.py:162-166`: `got = [answer(s, results_dir) for s in req]` — each segment answered independently, by whatever request produced the newest matching entry. If segment A was answered by request `r1` (yesterday, same window/text) and segment B by `r2`, the line-up is judged from two different locks. The contract says "Send the WHOLE line-up in one request" — the code does, but only when *any* segment lacks an answer; when all have answers it never sends, so the "whole line-up" coherence is only as good as the per-segment match. Concrete scenario: a line-up is re-lined (a clip dropped, others kept); the kept clips' answers come from the earlier request, the new clip's from the new request; the integrator's service answered each request as a *set* (its ruling-17 lock may depend on the line-up context — the diff cannot show it doesn't). If the service's answers are context-free per segment, this is fine; the diff cannot prove that. Mitigation: `check` filters by `request_id` only in the wait loop (`:170`), not in the reuse path. Severity: P1 because the contract's "answers each name and content once" plus per-segment result files suggests per-segment answers, but the whole-line-up request format argues the answers may be line-up-scoped. If they are, a reused answer from a different request_id could be wrong. Flag for the integrator to confirm.

**P1-2 — `decide()`'s `adopt_spoken` path: `AT.diff`/`AT.carry_class` exceptions are not caught, so a defect in attest (or an unexpected spoken_text shape) raises out of `decide` → out of `check` → out of `build`'s `lock_check(segs)` call, which is not wrapped.** `lock_precheck.py:143-146` (`r, p, ops = AT.diff(spoken, approved)`; `classes = [AT.carry_class(...)]`), called from `package.py:2540` (`pk = LP.apply(pk, nv_pre)` — no, that's apply; the `lock_check(order)` call at `:2497`-ish and `lock_check(segs)` at `:2682`-ish are bare). `build` wraps `LP.apply` in `try/except (ValueError, KeyError, TypeError)` (`package.py:288-293` of the diff, lines 2540/2938), but the `lock_check(...)` calls themselves are not wrapped. If `attest.diff` raises (say, a `TypeError` on an unexpected token), the whole build dies rather than fail-closing the line-up. Under M12 (fail closed) a build crash is arguably fail-closed, but the medley's documented behavior for "no verdict" is "nothing is written, the search stops" — an exception skips even that, leaving no `tried` record. Concrete scenario: the integrator's service returns `spoken_text` containing a token type attest's diff never anticipated (e.g. an int in a list-of-strings contract); `AT.diff` raises; the build crashes mid-angle with no ledger row. P1: the module's own docstring promises "A request is sent again rather than reusing an error" and "no verdict. Never a pass (law L-m)" — an exception is neither.

**P1-3 — `apply()`'s coverage check compares `r["approved_text"] != s["text"]` but `pin_problems()` does NOT compare approved_text at all.** `lock_precheck.py:208-211` (apply) vs `:233-237` (pin_problems). `pin_problems` checks video_id, start, end, verdict — but not that the sealed text is still the one the lock judged. Scenario: between `apply` and `write_pin`, some other code (outside the diff — e.g. a later ruling's caption fix, or `SP.attribute_package` at `proof_ledger.py:404` which runs *before* `pin_problems` at `:406`) mutates `s["text"]`. Then the pin seals a text the lock never judged, and `pin_problems` passes it. The driver's guard (change item 4) is therefore weaker than it reads. Note `attribute_package` runs before `pin_problems` in `proof_ledger.py:403-408` — if it edits segment text (the diff doesn't show; it "attributes" speakers, likely only setting `speaker`), the sealed text diverges. P1 because the whole point of ruling 68 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 32 s finish=stop usage in 20964 / out 259 usd~0.111 (upper-bound price)

**P0 findings:** none verifiable from diff.  
**P1 findings:** none verifiable from diff.  
**P2 findings:** none verifiable from diff (all four requested checks hold exactly: build+apply+pin_problems gate every non-(pass/adopt) text before any seal (package.py:277,312,338; proof_ledger.py:406; lock_precheck.py:206,229); adopt_spoken only reaches apply when this side's AT.carry_class returns non-None for every op and is sealed with attested record (lock_precheck.py:149,187,218; package_pin.py:374; test confirms seal hash changes); error/None outcome always produces verdict=error, ok=False, lock_stop+budget, never a package (lock_precheck.py:131,164,181; package.py:321,351); matching uses only ruling-72 entries, newest by (at,k), 3-decimal window+role+approved_text+TRIM fields exactly per contract (lock_precheck.py:47,85,91,74); send is atomic .tmp-then-rename, rejects existing or bad ID_RE chars (lock_precheck.py:115,120); seal() and all other gates untouched per diff).  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 76 s finish=stop usage in 23588 / out 1594 usd~0.095 (upper-bound price)

# Audit: pp-selectid-1744 (Lock Pre-check / Rulings 68 & 72)

## P0 Findings (Blockers)

**None found.** The implementation correctly implements the "fail-closed" requirements for the lock pre-check.

## P1 Findings (Major)

**None found.**

## P2 Findings (Minor / Observations)

### 1. `lock_precheck.py`: Potential `KeyError` in `decide()` for `adopt_spoken`
**File:** `pipeline/lock_precheck.py` (lines 140-143 in diff, approx line 140 in file)
**Scenario:** If the integrator returns `outcome: "adopt_spoken"` but the `spoken_text` field is missing or `None`, the code correctly returns an error. However, if `spoken_text` is present but `seg["approved_text"]` is missing (which shouldn't happen as `segments_of` always sets it, but defensive coding is good), `AT.diff` might behave unexpectedly.
**Verification:** The code checks `if not isinstance(spoken, str) or not spoken.strip(): return {"verdict": "error"...}`. This is safe. `seg["approved_text"]` is guaranteed by `segments_of`. No action needed.

### 2. `package.py`: `lock_check` invocation in No-Voice path
**File:** `pipeline/package.py` (lines 277-280 in diff)
**Scenario:** In the no-voice fallback path, `lock_check(order)` is called. If `lock_check` returns `ok: False` due to a `hold`, the code returns `None` (no package). This is correct. If it returns `ok: False` due to an `error` (no verdict), the code also returns `None`.
**Observation:** The comment says "no verdict is never a pass". The code `if nv_pre is not None and not nv_pre.get("ok"): return None` handles both `hold` and `error` by refusing the package. This aligns with Law L-m (Fail Closed).

### 3. `package.py`: `lock_stop` logic
**File:** `pipeline/package.py` (lines 321-324 in diff)
**Scenario:** When `pre.get("error")` is true (no verdict), `out["lock_stop"]` is set to `True`. This stops the search for *this angle*. The outer loop condition `not out.get("lock_stop")` ensures the angle loop breaks.
**Verification:** This prevents the system from trying other line-ups for the same angle if the lock service is down or timing out, which is a reasonable "fail fast" behavior to avoid wasting budget on a broken dependency. It does *not* stop the entire build, just the current angle's search. This seems correct.

### 4. `lock_precheck.py`: `answer()` matching logic
**File:** `pipeline/lock_precheck.py` (lines 85-92 in diff)
**Scenario:** The `_matches` function checks `e.get("rules") == RULES`. `RULES` is `"ruling 17 + ruling 72"`.
**Verification:** The contract states: "Take the newest entry with rules == 'ruling 17 + ruling 72'". The code does exactly this. It also checks `win == [seg["start"], seg["end"]]`. `seg["start"]` and `seg["end"]` are rounded to 3 decimal places in `segments_of`. The result file name uses `%.3f`. The JSON entry's `window` is expected to be a list of two floats. The code rounds the window values to 3 decimal places before comparison: `win = [round(float(w[0]), 3), round(float(w[1]), 3)]`. This ensures floating point precision issues don't cause mismatches. This is robust.

### 5. `lock_precheck.py`: `send()` atomicity
**File:** `pipeline/lock_precheck.py` (lines 112-125 in diff)
**Scenario:** The code writes to a `.tmp` file and then renames it to `.json`.
**Verification:** `os.rename` is atomic on POSIX systems (Linux). This ensures the integrator never sees a partially written request file. The code also checks `if os.path.exists(final) or os.path.exists(tmp): raise FileExistsError`. This prevents overwriting an existing request, which aligns with the contract "answers each name and content once".

### 6. `package_pin.py`: `attested` field in seal
**File:** `pipeline/package_pin.py` (lines 373-376 in diff)
**Scenario:** The `attested` field is added to the pin segment.
**Verification:** The `seal()` function is not modified. The `attested` field is part of the segment dictionary, so it will be included in the SHA256 hash calculation for the pin. This is correct: the "attested" record is part of the sealed state. If the text changes, the `attested` record changes, and the pin hash changes.

### 7. `test_medley.py`: `lock_stub`
**File:** `tests/package/test_medley.py` (lines 676-696 in diff)
**Scenario:** The test stub `lock_stub` simulates the `lock_check` function.
**Verification:** The stub correctly returns a dictionary with `ok`, `request_id`, `segments`, and `error`. The `segments` list contains dictionaries with `verdict`, `outcome`, `why`, and `entry`. This matches the expected return type of `lock_precheck.check`.

## SHIP: Yes

The code correctly implements the Rulings 68 and 72 requirements:
1.  **No pin sealed with unpassed text:** `lock_precheck.apply` refuses to apply if the pre-check didn't pass or if the segments don't match. `package.build` only calls `apply` if `lock_check` returned `ok: True`. The driver's `pin_problems` check adds a final layer 

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1744 (rulings 68 / 72: the render's lock pre-check, wired before the writes and at the pin stage): cycle 1 consensus

- **grok:** "SHIP: yes". No P0, P1 or P2. It verifies the four required checks line by line.
- **qwen:** "SHIP: Yes". No P0 or P1. Its P2s are verifications.
- **glm:** "SHIP: yes with conditions". No P0; four P1s. Two are verified real and implemented; two are refuted below.

## Implemented

**C1-a (glm P1-2, verified): a pre-check that RAISES crashed the build instead of failing closed.**
- `lock_check(segs)` was called bare in build(), both for the voiced line-up and for the no-voice one.
- Unwrapped exceptions included:
  - an OSError from writing the request (send);
  - an exception inside decide() (attest on an unexpected spoken_text).
- On the driver's normal search, that loses the build record (package.json) and the registry update.
- Fixed:
  - both calls are wrapped; an exception becomes `lock_precheck.failed(e)`, the same no-verdict shape as an error
    answer. No write, and the search stops (`lock_stop`);
  - the no-voice path now also sets `lock_stop` on no verdict (glm P2-1: before, it would wait up to 1200 s again on
    every later line-up);
  - the two `LP.apply` guards catch any exception (glm P2-6), never crashing and never making a pin.
- Test: test_a_pre_check_that_raises_is_no_verdict_never_a_crash (voiced and no-voice). It fails with the wrap
  removed, and with the no-voice stop removed (mutation runs).

**C1-b (glm P1-3, verified): the pin stage's own check did not compare the sealed TEXT.**
- `pin_problems` compared video, start, end and verdict only.
- Fixed:
  - `apply` records, per segment, the text the lock passed (the approved text, or the adopted spoken text) in
    pk["precheck"];
  - `pin_problems` refuses when the package's segment text is not that text ("as they now stand").
- Test: test_the_pin_stage_compares_the_text_the_lock_passed. It fails with the comparison removed.

## Refuted (evidence)

- **glm P1-1** (a resent request id collides, FileExistsError): the ids are "pp-selectid.<build dir>.<n>". The build
  dir is created by `os.makedirs(out_dir)` without exist_ok, and the driver REFUSES an existing one. n increments
  within the process. Two requests can never share an id. (And with C1-a, even a collision would be no verdict,
  not a crash.)
- **glm P1-4** (reused answers may come from different requests): the contract's results are per segment window
  ("<video_id>.<start>-<end>" files; "Take the newest entry whose window equals [start, end] (a one-segment video)").
  The integrator says a repeat "is answered from cache", per segment content.
  - A medley has one clip per channel (L-y 4), so one segment per video.
  - A video with two segments in one line-up would carry a wider window and never match. That is no answer, so an
    error: fail closed.
- **glm P2-3** (the driver's id must fit ID_RE): the build dir's basename is "ledger_YYYYMMDD_HHMMSS", all within
  [A-

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1744/C2_STEP.diff (820 lines)
```
   1 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
   2 | new file mode 100644
   3 | index 0000000..a389742
   4 | --- /dev/null
   5 | +++ b/pipeline/lock_precheck.py
   6 | @@ -0,0 +1,240 @@
   7 | +"""RULING 68 (orchestrator 14:02 Nov 13) and RULING 72 (live 17:17 Nov 13 on the integrator's side): the render's own
   8 | +ruling-17 lock, asked BEFORE any write is paid for a line-up and before its pin is sealed. Ruling 68: "When it exists,
   9 | +your approved text comes from it."
  10 | +
  11 | +The integrator's service runs the render's acquisition, decode and lock (pinned.acquire, validate_range,
  12 | +pinned.segment_lock) on the segments of a request. Under ruling 72 it compares the second recogniser with the lock on
  13 | +every span.
  14 | +
  15 | +Requests: this worktree's tests/package/proof/lock_requests/ (<name>.tmp, then rename). The service only reads there,
  16 | +and answers each name and content once.
  17 | +
  18 | +Results: read only, in /home/ultron/protocol_pulse/data/lock_precheck/results/
  19 | +<video_id>.<start %.3f>-<end %.3f>.<decoder[:12]>.json. Each file is a list. The answer is the newest entry (by "at")
  20 | +that meets all of these:
  21 | +- rules == "ruling 17 + ruling 72";
  22 | +- its window is the segment's [start, end];
  23 | +- its role, approved_text, trimmed_leading and untrimmed_start equal the request's.
  24 | +Entries without "rules" are ruling 68's, from before, and are never read.
  25 | +
  26 | +Outcomes:
  27 | +- no_difference, adopted, two_readings: pass. The approved text stands.
  28 | +- adopt_spoken: the text to seal is "spoken_text", already through the render's validate_range + segment_lock. It is
  29 | +  adopted only when this side's own check agrees that every difference is in ruling 67's carry-over class
  30 | +  (attest.carry_class: a function word, or the speaker's own immediate repetition; never a number, a name or a
  31 | +  negation). Otherwise it is a hold (fail closed).
  32 | +- hold: the clip may not be used with that text. The reason says why.
  33 | +- error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
  34 | +  is sent again rather than reusing an error.
  35 | +
  36 | +The text a pin seals is the approved text, or the adopted spoken text with an "attested" record
  37 | +(package_pin.SEALED_LATER), as ruling 67's re-seal records it."""
  38 | +import json
  39 | +import os
  40 | +import re
  41 | +import time
  42 | +from datetime import datetime, timezone
  43 | +
  44 | +import attest as AT
  45 | +
  46 | +RULES = "ruling 17 + ruling 72"
  47 | +DECODER = "25cd6f15e6c9"                      # the integrator's decoder_sha[:12] (unchanged by ruling 72)
  48 | +RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  49 | +REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  50 | +                        "lock_requests")      # this worktree's; the service only reads it
  51 | +PASS = frozenset(("no_difference", "adopted", "two_readings"))
  52 | +TRIM = ("trimmed_leading", "untrimmed_start")
  53 | +ID_RE = re.compile(r"[A-Za-z0-9_.:~-]{1,120}")
  54 | +TIMEOUT_S = 1200.0                            # a fresh line-up takes about 2-2.5 min; the service yields to renders
  55 | +POLL_S = 10.0
  56 | +OLDEST = datetime.min.replace(tzinfo=timezone.utc)
  57 | +
  58 | +
  59 | +def segments_of(segs):
  60 | +    """The request's segments, exactly as package_pin.to_pin will carry them from this line-up: role (the hook first),
  61 | +    start and end rounded to the millisecond, the moment's text as approved_text, and both trim fields when the
  62 | +    moment is trimmed (package._package copies them then)."""
  63 | +    out = []
  64 | +    for i, m in enumerate(segs):
  65 | +        s = {"video_id": str(m["video_id"]), "start": round(float(m["start"]), 3), "end": round(float(m["end"]), 3),
  66 | +             "role": "hook" if i == 0 else "clip", "approved_text": m["text"]}
  67 | +        if m.get("trimmed_leading"):
  68 | +            s.update({k: m[k] for k in TRIM})
  69 | +        out.append(s)
  70 | +    return out
  71 | +
  72 | +
  73 | +def result_file(seg, results_dir=RESULTS, decoder=DECODER):
  74 | +    return os.path.join(results_dir, f"{seg['video_id']}.{seg['start']:.3f}-{seg['end']:.3f}.{decoder[:12]}.json")
  75 | +
  76 | +
  77 | +def _at(s):
  78 | +    try:
  79 | +        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  80 | +    except (TypeError, ValueError):
  81 | +        return OLDEST
  82 | +    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)
  83 | +
  84 | +
  85 | +def _matches(e, seg):
  86 | +    w = e.get("window")
  87 | +    try:
  88 | +        win = [round(float(w[0]), 3), round(float(w[1]), 3)] if isinstance(w, list) and len(w) == 2 else None
  89 | +    except (TypeError, ValueError):
  90 | +        win = None
  91 | +    return (e.get("rules") == RULES and win == [seg["start"], seg["end"]] and e.get("role") == seg["role"] and
  92 | +            e.get("approved_text") == seg["approved_text"] and all(e.get(k) == seg.get(k) for k in TRIM))
  93 | +
  94 | +
  95 | +def answer(seg, results_dir=RESULTS, request_id=None):
  96 | +    """The newest matching entry (by "at", then file order), only `request_id`'s when given; None when there is none
  97 | +    or the file cannot be read (no answer is never a pass)."""
  98 | +    try:
  99 | +        with open(result_file(seg, results_dir)) as f:
 100 | +            entries = json.load(f)
 101 | +    except (OSError, ValueError):
 102 | +        return None
 103 | +    best = None
 104 | +    for k, e in enumerate(entries if isinstance(entries, list) else []):
 105 | +        if isinstance(e, dict) and _matches(e, seg) and (request_id is None or e.get("request_id") == request_id):
 106 | +            key = (_at(e.get("at")), k)
 107 | +            if best is None or key >= best[0]:
 108 | +                best = (key, e)
 109 | +    return best[1] if best else None
 110 | +
 111 | +
 112 | +def send(segments, request_id, requests_dir=REQUESTS):
 113 | +    """Write the WHOLE line-up as one request: <request_id>.tmp, then renamed to <request_id>.json. Never over an
 114 | +    existing request (the service answers each name and content once)."""
 115 | +    if not isinstance(request_id, str) or not ID_RE.fullmatch(request_id):
 116 | +        raise ValueError(f"a request_id is 1-120 of [A-Za-z0-9_.:~-]: {request_id!r}")
 117 | +    os.makedirs(requests_dir, exist_ok=True)
 118 | +    final = os.path.join(requests_dir, request_id + ".json")
 119 | +    tmp = os.path.join(requests_dir, request_id + ".tmp")
 120 | +    if os.path.exists(final) or os.path.exists(tmp):
 121 | +        raise FileExistsError(f"{final} (or its .tmp) exists: a request is never written over")
 122 | +    with open(tmp, "x") as f:
 123 | +        json.dump({"request_id": request_id, "segments": segments}, f, indent=1)
 124 | +    os.rename(tmp, final)
 125 | +    return final
 126 | +
 127 | +
 128 | +def decide(seg, e):
 129 | +    """One segment's verdict from its answer -> {"verdict": "pass" | "adopt" | "hold" | "error", "outcome", "why",
 130 | +    and for an adoption "spoken_text" and "differences"}."""
 131 | +    if e is None:
 132 | +        return {"verdict": "error", "outcome": None, "why": "no answer from the render's lock in time (law L-m)"}
 133 | +    out, why = e.get("outcome"), str(e.get("reason") or "")[:400]
 134 | +    if out in PASS:
 135 | +        return {"verdict": "pass", "outcome": out, "why": why}
 136 | +    if out == "hold":
 137 | +        return {"verdict": "hold", "outcome": out, "why": why or "held (no reason given)"}
 138 | +    if out != "adopt_spoken":
 139 | +        return {"verdict": "error", "outcome": out, "why": f"no verdict: outcome {out!r} {why}".strip()}
 140 | +    spoken, approved = e.get("spoken_text"), seg["approved_text"]
 141 | +    if not isinstance(spoken, str) or not spoken.strip():
 142 | +        return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
 143 | +    r, p, ops = AT.diff(spoken, approved)
 144 | +    if not ops:                                       # the same canonical words: the approved text stands
 145 | +        return {"verdict": "pass", "outcome": out, "why": "adopt_spoken with no canonical difference"}
 146 | +    classes = [AT.carry_class(r, p, o, (spoken, approved)) for o in ops]
 147 | +    diffs = [{"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "class": k}
 148 | +             for (_, a, b, c, d), k in zip(ops, classes)]
 149 | +    if None in classes:                               # this side's ruling-67 check disagrees: fail closed
 150 | +        return {"verdict": "hold", "outcome": out, "differences": diffs,
 151 | +                "why": "adopt_spoken, but by this side's attest.carry_class a difference is outside ruling 67's "
 152 | +                       "class: " + str([[x["spoken"], x["approved"]] for x in diffs if x["class"] is None])[:300]}
 153 | +    return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs}
 154 | +
 155 | +
 156 | +def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_s=TIMEOUT_S, poll_s=POLL_S,
 157 | +          clock=time.time, sleep=time.sleep, log=print):
 158 | +    """The render's lock for this line-up. An answer already on file is used (never an error), else the whole line-up
 159 | +    is sent and its answers awaited. -> {"ok": every segment passes or is adopted, "request_id": the one sent or None,
 160 | +    "segments": [request segment + decide() + the answer's "entry" ref], "error": why no verdict, or None}."""
 161 | +    req = segments_of(segs)
 162 | +    got = [answer(s, results_dir) for s in req]
 163 | +    sent = None
 164 | +    if any(e is None or e.get("outcome") not in PASS | {"adopt_spoken", "hold"} for e in got):
 165 | +        sent = request_id
 166 | +        send(req, request_id, requests_dir)
 167 | +        log(f"    ruling 72: the lock pre-check asked ({request_id}, {len(req)} segment(s))")
 168 | +        deadline = clock() + timeout_s
 169 | +        while True:
 170 | +            got = [answer(s, results_dir, request_id) for s in req]
 171 | +            if all(e is not None for e in got) or clock() >= deadline:
 172 | +                break
 173 | +            sleep(poll_s)
 174 | +    rows = []
 175 | +    for s, e in zip(req, got):
 176 | +        d = decide(s, e)
 177 | +        rows.append(dict(s, **d, entry=None if e is None else {
 178 | +            "request_id": e.get("request_id"), "at": e.get("at"), "outcome": e.get("outcome"),
 179 | +            "lock_sha256": (e.get("lock") or {}).get("sha256") if isinstance(e.get("lock"), dict) else None,
 180 | +            "file": os.path.basename(result_file(s, results_dir))}))
 181 | +    errs = [f"{x['video_id']} {x['start']}-{x['end']}: {x['why']}" for x in rows if x["verdict"] == "error"]
 182 | +    return {"ok": all(x["verdict"] in ("pass", "adopt") for x in rows), "request_id": sent, "segments": rows,
 183 | +            "error": "; ".join(errs)[:600] or None}
 184 | +
 185 | +
 186 | +def attested(row, run_rule="ruling 72 (live 17:17 Nov 13): adopt_spoken, in ruling 67's carry-over class"):
 187 | +    """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
 188 | +    return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
 189 | +            "carried": "every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
 190 | +                       "ruling 67's carry-over class (checked on this side too), and no line quotes the changed words",
 191 | +            "render": {"precheck": row["entry"], "spoken_text": row["spoken_text"]}}
 192 | +
 193 | +
 194 | +def quoting_lines(lines, row):
 195 | +    """The lines that quote an adopted segment's changed words (ruling 67: such a line is re-gated first)."""
 196 | +    r, p, ops = AT.diff(row["spoken_text"], row["approved_text"])
 197 | +    return AT.quotes(lines, r, p, ops)
 198 | +
 199 | +
 200 | +def apply(pk, pre):
 201 | +    """The package as it will be sealed, from this line-up's pre-check: each adopted segment's text is the spoken text
 202 | +    with its "attested" record, and the hook's first words follow its text. Refuses (ValueError) unless the pre-check
 203 | +    passed and covers exactly the package's segments (video, start, end, approved text, in order), and when a line
 204 | +    quotes an adopted segment's changed words (ruling 67: re-gated first). -> pk (its segments are its own)."""
 205 | +    rows, segs = pre.get("segments") or [], pk["segments"]
 206 | +    if pre.get("ok") is not True:
 207 | +        raise ValueError(f"the render's lock pre-check did not pass: {pre.get('error') or 'a segment holds'}")
 208 | +    if len(rows) != len(segs) or any(
 209 | +            r["video_id"] != s["video_id"] or r["start"] != round(float(s["start"]), 3) or
 210 | +            r["end"] != round(float(s["end"]), 3) or r["approved_text"] != s["text"] for r, s in zip(rows, segs)):
 211 | +        raise ValueError("the lock pre-check does not cover exactly this package's segments")
 212 | +    lines = [x["text"] for x in pk.get("lines") or []]
 213 | +    for r, s in zip(rows, segs):
 214 | +        if r["verdict"] == "adopt":
 215 | +            q = quoting_lines(lines, r)
 216 | +            if q:
 217 | +                raise ValueError(f"ruling 67: these lines quote the changed words of {s['video_id']}: {q}")
 218 | +            s["text"], s["attested"] = r["spoken_text"], attested(r)
 219 | +    pk["hook_first_words"] = " ".join(segs[0]["text"].split()[:8])      # as package._package derives it
 220 | +    pk["precheck"] = {"ok": True, "request_id": pre.get("request_id"),
 221 | +                      "segments": [dict({k: r.get(k) for k in ("video_id", "start", "end", "role", "verdict", "outcome",
 222 | +                                                               "entry")}, text=s["text"])   # the text the lock passed
 223 | +                                   for r, s in zip(rows, segs)]}
 224 | +    return pk
 225 | +
 226 | +
 227 | +def failed(e):
 228 | +    """A pre-check that raised (a request that could not be written, an answer that could not be decided): no
 229 | +    verdict, never a pass (law L-m). -> the shape check() returns (audit 1744 C1)."""
 230 | +    return {"ok": False, "request_id": None, "segments": [], "error": f"{type(e).__name__}: {str(e)[:300]}"}
 231 | +
 232 | +
 233 | +def pin_problems(pk):
 234 | +    """The pin stage's own check (ruling 68): a package is sealed only with a passing pre-check that covers exactly its
 235 | +    segments as they now stand (an adopted text included). -> [why]."""
 236 | +    pre = pk.get("precheck") or {}
 237 | +    rows, segs = pre.get("segments") or [], pk.get("segments") or []
 238 | +    if pre.get("ok") is not True:
 239 | +        return ["ruling 68: no passing lock pre-check on this package"]
 240 | +    if len(rows) != len(segs) or any(r.get("video_id") != s.get("video_id") or
 241 | +                                     r.get("start") != round(float(s.get("start")), 3) or
 242 | +                                     r.get("end") != round(float(s.get("end")), 3) or
 243 | +                                     r.get("verdict") not in ("pass", "adopt") or
 244 | +                                     r.get("text") != s.get("text") for r, s in zip(rows, segs)):   # audit 1744 C1
 245 | +        return ["ruling 68: the lock pre-check does not cover this package's segments as they now stand"]
 246 | +    return []
 247 | diff --git a/pipeline/package.py b/pipeline/package.py
 248 | index a0c1526..ad6dd60 100644
 249 | --- a/pipeline/package.py
 250 | +++ b/pipeline/package.py
 251 | @@ -2119,7 +2119,7 @@ def candidate_lineup(router, candidate, cleared, now):
 252 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 253 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
 254 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
 255 | -          visual_cache=None, registered=None):
 256 | +          visual_cache=None, registered=None, lock_check=None):
 257 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 258 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 259 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 260 | @@ -2151,11 +2151,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 261 |      line-up the search forms that is registered is recorded ("registered") and neither judged nor written, and the angle
 262 |      ends there, as it ends after a passing line-up whose line fails; ruling 3's no-voice fallback never adds the clip
 263 |      that would form one (audit 1655). A build from a candidate ignores it.
 264 | +    RULING 68 / 72 (lock_check, lock_precheck.check through the driver): "your approved text comes from" the render's own
 265 | +    ruling-17 lock. A line-up whose clips pass is asked BEFORE any write is paid:
 266 | +      - a clip the render would hold is out (doomed), and the line-up is re-lined;
 267 | +      - no verdict (an error, or no answer in time) is never a pass: nothing is written, the search stops, and the
 268 | +        line-up stays a candidate (its class is "budget");
 269 | +      - a package keeps the approved texts, or seals an adopted spoken text with its "attested" record
 270 | +        (lock_precheck.apply, checked again at the pin stage).
 271 | +    The no-voice line-up is asked too. lock_check None: no pre-check (the tests' rigs); the driver always passes it.
 272 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 273 |      t0 = time.time()
 274 |      usd0 = _spent(spend)
 275 |      held_map = dict(registered or {}) if candidate is None else {}   # ruling 66: the registry's line-ups, by moment ids
 276 |      import visual_pin as VP                            # ruling 70
 277 | +    import lock_precheck as LP                         # rulings 68 / 72
 278 |      vcache = VP.load_cache(visual_cache) if visual_cache else {}
 279 |      out_visual = {"calls": 0, "cached": 0, "usd_reported": 0.0, "usd_estimate": 0.0, "estimated_calls": 0,
 280 |                    "unmeasured": 0, "flags": 0}   # ruling 70: the vendor's figure and the estimate never mixed
 281 | @@ -2488,6 +2497,17 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 282 |          if vbad:
 283 |              note["why_not"] = f"ruling 70: the visual check is not measured for {vbad}"
 284 |              return None
 285 | +        nv_pre = None
 286 | +        if lock_check is not None:                         # RULINGS 68 / 72: its own line-up
 287 | +            try:
 288 | +                nv_pre = lock_check(order)
 289 | +            except Exception as e:                        # noqa: BLE001  audit 1744 C1: no verdict, never a pass
 290 | +                nv_pre = LP.failed(e)
 291 | +        if nv_pre is not None and not nv_pre.get("ok"):
 292 | +            note["why_not"] = f"ruling 68 / 72: the render's lock: {nv_pre.get('error') or 'a clip holds'}"[:400]
 293 | +            if nv_pre.get("error") or not nv_pre.get("segments"):
 294 | +                out["lock_stop"] = note["why_not"]        # no verdict: the search stops, as for a voiced line-up
 295 | +            return None
 296 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 297 |          pk["medley"] = nv_med
 298 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 299 | @@ -2527,6 +2547,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 300 |          pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": nv_med}
 301 |          pk["seconds"] = round(time.time() - t0, 1)
 302 |          pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 303 | +        if nv_pre is not None:                            # rulings 68 / 72: the texts it seals
 304 | +            try:
 305 | +                pk = LP.apply(pk, nv_pre)
 306 | +            except Exception as e:                        # noqa: BLE001  audit 1744 C1: never a crash, never a pin
 307 | +                note["why_not"] = f"ruling 68 / 72: {e}"[:400]
 308 | +                return None
 309 |          note["result"] = "PACKAGE"
 310 |          log(f"  angle {ai + 1} line-up {n_lineup}: NO-VOICE package ({len(order)} clips, "
 311 |              f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 312 | @@ -2540,7 +2566,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 313 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
 314 |              if candidate is not None:                     # RULING 66: its own seeds, so its recorded calls are served
 315 |                  n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs
 316 | -            while total < lineups and not out["packages"] and not out.get("budget_stop"):
 317 | +            while total < lineups and not out["packages"] and not out.get("budget_stop") and \
 318 | +                    not out.get("lock_stop"):
 319 |                  if candidate is not None and n_lineup >= candidate["n_lineup"]:
 320 |                      break                                 # RULING 66: the candidate alone, never re-lined or swapped
 321 |                  if over_budget(ai):
 322 | @@ -2662,6 +2689,29 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 323 |                      doomed |= set(vbad)
 324 |                      rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
 325 |                      relined, w_used = True, writes      # no write is paid
 326 | +                pre = None
 327 | +                if not relined and lock_check is not None:  # RULINGS 68 / 72: the render's own lock, before any write
 328 | +                    try:
 329 | +                        pre = lock_check(segs)
 330 | +                    except Exception as e:                # noqa: BLE001  audit 1744 C1: no verdict, never a pass
 331 | +                        pre = LP.failed(e)
 332 | +                    rec["precheck"] = {"request_id": pre.get("request_id"), "ok": pre.get("ok"),
 333 | +                                       "segments": [{k: x.get(k) for k in ("video_id", "start", "end", "verdict",
 334 | +                                                                          "outcome", "why")} for x in pre["segments"]]}
 335 | +                    log(f"    ruling 72: the render's lock: " + ", ".join(
 336 | +                        f"{x['video_id']} {x['verdict']}" for x in pre["segments"]) + f" ({time.time() - t0:.0f} s)")
 337 | +                    held = {segs[i]["moment_id"]: x["why"] for i, x in enumerate(pre["segments"])
 338 | +                            if x["verdict"] == "hold"}
 339 | +                    if pre.get("error") or not pre["segments"]:      # no verdict is never a pass (law L-m): nothing
 340 | +                        rec["why"] = f"ruling 68 / 72: no lock verdict: {pre.get('error')}"[:500]   # is written, the
 341 | +                        rec["budget"], out["lock_stop"] = True, rec["why"]   # search stops, the line-up stays a
 342 | +                        w_used = writes                                     # candidate (class "budget")
 343 | +                    elif held:                             # the render would hold these clips: out, re-lined
 344 | +                        dropped |= set(held)
 345 | +                        doomed |= set(held)
 346 | +                        rec["why"] = ("ruling 72: the render's lock holds " +
 347 | +                                      "; ".join(f"{k}: {v}" for k, v in held.items()))[:500] + ": re-lined"
 348 | +                        relined, w_used = True, writes
 349 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 350 |                  alone_n, alone_by, t_refused, t_alone, last_fid, last_rw65 = 0, None, [], False, None, False
 351 |                  while True:                                # RULING 66 amended (17:02): the writes; then, when the
 352 | @@ -2889,12 +2939,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 353 |                      pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 354 |                      pk["seconds"] = round(time.time() - t0, 1)
 355 |                      pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 356 | +                    if lock_check is not None:            # rulings 68 / 72: the texts it seals come from the lock
 357 | +                        try:
 358 | +                            pk = LP.apply(pk, pre)
 359 | +                        except Exception as e:            # noqa: BLE001  audit 1744 C1: never a crash, never a pin
 360 | +                            rec["why"] = f"ruling 68 / 72: {e}"[:400]
 361 | +                            w_used = writes
 362 | +                            break
 363 |                      out["packages"].append(pk)
 364 |                      rec["result"] = "PACKAGE"
 365 |                      break
 366 |                  rec["relined"] = relined                    # ruling 66: a clip was dropped (or a line-up rule)
 367 |                  if not out["packages"] and not relined and ok_m and not med["flagged"] and \
 368 | -                        take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop"):
 369 | +                        take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop") \
 370 | +                        and not out.get("lock_stop"):
 371 |                      nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup)
 372 |                      if nv is not None:
 373 |                          out["packages"].append(nv)
 374 | @@ -2907,7 +2965,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 375 |                                    (f" ({', '.join(rules)})" if rules else ""))
 376 |                  if out["packages"] or not relined:
 377 |                      break
 378 | -            if out["packages"] or out.get("budget_stop") or over_budget(ai):
 379 | +            if out["packages"] or out.get("budget_stop") or out.get("lock_stop") or over_budget(ai):
 380 |                  break
 381 |      out["package"] = out["packages"][0] if out["packages"] else None
 382 |      if candidate is not None:                             # RULING 66: what became of the candidate
 383 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 384 | index 19330af..a846a1c 100644
 385 | --- a/pipeline/package_pin.py
 386 | +++ b/pipeline/package_pin.py
 387 | @@ -281,7 +281,8 @@ def to_pin(pk, run_name):
 388 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 389 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 390 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 391 | -                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual")
 392 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual",
 393 | +                                          "attested")      # rulings 68 / 72: an adopted spoken text, sealed
 394 |                          if k in s},
 395 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 396 |      edl_vo = {"intro": pk["vo"]["intro"],
 397 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 398 | index 02585be..38e802b 100644
 399 | --- a/tests/package/proof_ledger.py
 400 | +++ b/tests/package/proof_ledger.py
 401 | @@ -58,6 +58,7 @@ import proof_ly as PL  # noqa: E402
 402 |  import proof_saved_runs as PS  # noqa: E402
 403 |  import providers as P  # noqa: E402
 404 |  import speakers as SP  # noqa: E402
 405 | +import lock_precheck as LP  # noqa: E402
 406 |  
 407 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 408 |  
 409 | @@ -175,7 +176,9 @@ def main(argv=None):
 410 |                hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 411 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 412 |                scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 413 | -              visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"))       # ruling 70
 414 | +              visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
 415 | +              lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
 416 | +                  segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
 417 |      name, at = os.path.relpath(out_dir, REPO), now.isoformat()
 418 |      if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
 419 |          res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
 420 | @@ -220,6 +223,9 @@ def main(argv=None):
 421 |      if res["package"]:
 422 |          SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 423 |          try:
 424 | +            lock = LP.pin_problems(res["package"])       # ruling 68: sealed only with a passing lock pre-check
 425 | +            if lock:
 426 | +                raise package_pin.PinRefused("; ".join(lock))
 427 |              path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 428 |                                                name="MOMENTS_PIN_LEDGER.json")
 429 |              res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 430 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 431 | new file mode 100644
 432 | index 0000000..b7c4f3b
 433 | --- /dev/null
 434 | +++ b/tests/package/test_lock_precheck.py
 435 | @@ -0,0 +1,224 @@
 436 | +#!/usr/bin/env python3
 437 | +"""RULINGS 68 / 72 (orchestrator 14:02 Nov 13; live on the integrator's side 17:17 Nov 13): the render's own ruling-17
 438 | +lock, asked before a line-up is written and before its pin is sealed (pipeline/lock_precheck.py). Offline: the
 439 | +requests and results directories are temporary, the clock and the sleep are the test's."""
 440 | +import json
 441 | +import os
 442 | +import sys
 443 | +import tempfile
 444 | +import unittest
 445 | +
 446 | +HERE = os.path.dirname(os.path.abspath(__file__))
 447 | +REPO = os.path.dirname(os.path.dirname(HERE))
 448 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 449 | +import lock_precheck as LP  # noqa: E402
 450 | +
 451 | +HOOK = {"moment_id": "h", "video_id": "DcUbBkyeh9M", "start": 216.0541, "end": 228.6739,
 452 | +        "text": "Bitcoin launched in January of 2009. It's never been renamed."}
 453 | +CLIP = {"moment_id": "x", "video_id": "MqVqfEDXgLo", "start": 937.971, "end": 957.291,
 454 | +        "text": "I think Bitcoin only dropped like 5, 6%."}
 455 | +TRIM = dict(CLIP, moment_id="t", video_id="HWuMai_mAug", start=1691.139, end=1698.069, trimmed_leading="And",
 456 | +            untrimmed_start=1690.9, text="treasury companies will also bleed to Bitcoin.")
 457 | +
 458 | +
 459 | +def entry(seg, outcome="no_difference", at="2026-11-13T22:30:00Z", rid="r1", **kw):
 460 | +    e = {"rules": LP.RULES, "request_id": rid, "video_id": seg["video_id"], "start": seg["start"], "end": seg["end"],
 461 | +         "window": [seg["start"], seg["end"]], "role": seg["role"], "approved_text": seg["approved_text"],
 462 | +         "trimmed_leading": seg.get("trimmed_leading"), "untrimmed_start": seg.get("untrimmed_start"),
 463 | +         "outcome": outcome, "reason": None, "lock": {"sha256": "ab" * 32}, "at": at}
 464 | +    e.update(kw)
 465 | +    return e
 466 | +
 467 | +
 468 | +class Dirs(unittest.TestCase):
 469 | +    def setUp(self):
 470 | +        self.tmp = tempfile.TemporaryDirectory()
 471 | +        self.req, self.res = os.path.join(self.tmp.name, "req"), os.path.join(self.tmp.name, "res")
 472 | +        os.makedirs(self.res)
 473 | +
 474 | +    def tearDown(self):
 475 | +        self.tmp.cleanup()
 476 | +
 477 | +    def put(self, seg, *entries):
 478 | +        p = LP.result_file(seg, self.res)
 479 | +        old = []
 480 | +        if os.path.exists(p):
 481 | +            with open(p) as f:
 482 | +                old = json.load(f)
 483 | +        with open(p, "w") as f:
 484 | +            json.dump(old + list(entries), f)
 485 | +
 486 | +
 487 | +class TestRequest(Dirs):
 488 | +    def test_the_segments_are_the_pins_own(self):
 489 | +        s = LP.segments_of([HOOK, CLIP, TRIM])
 490 | +        self.assertEqual([x["role"] for x in s], ["hook", "clip", "clip"])
 491 | +        self.assertEqual((s[0]["start"], s[0]["end"]), (216.054, 228.674))              # to the millisecond
 492 | +        self.assertEqual(s[0]["approved_text"], HOOK["text"])
 493 | +        self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 494 | +        self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 495 | +        self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 496 | +                         "DcUbBkyeh9M.216.054-228.674.25cd6f15e6c9.json")
 497 | +
 498 | +    def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 499 | +        segs = LP.segments_of([HOOK, CLIP])
 500 | +        p = LP.send(segs, "pp-selectid.ledger_x.1", self.req)
 501 | +        self.assertEqual(os.listdir(self.req), ["pp-selectid.ledger_x.1.json"])           # no .tmp left
 502 | +        with open(p) as f:
 503 | +            self.assertEqual(json.load(f), {"request_id": "pp-selectid.ledger_x.1", "segments": segs})
 504 | +        with self.assertRaises(FileExistsError):
 505 | +            LP.send(segs, "pp-selectid.ledger_x.1", self.req)
 506 | +        for bad in ("", "a b", "x" * 121, "../x"):
 507 | +            with self.assertRaises(ValueError):
 508 | +                LP.send(segs, bad, self.req)
 509 | +
 510 | +
 511 | +class TestAnswer(Dirs):
 512 | +    def test_the_newest_matching_entry_of_ruling_72_and_only_it(self):
 513 | +        s = LP.segments_of([HOOK])[0]
 514 | +        self.put(s, entry(s, "hold", at="2026-11-13T22:00:00Z"), entry(s, "no_difference", at="2026-11-13T22:05:00Z"),
 515 | +                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), rules=None),        # ruling 68's: never read
 516 | +                 entry(dict(s, approved_text="other words"), "adopted", at="2026-11-13T23:00:00Z"),
 517 | +                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), window=[216.0, 228.674]),
 518 | +                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), role="clip"))
 519 | +        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")
 520 | +        self.put(s, entry(s, "hold", at="2026-11-13T22:05:00Z", rid="r2"))                 # same time: the later one
 521 | +        self.assertEqual(LP.answer(s, self.res)["outcome"], "hold")
 522 | +        self.assertEqual(LP.answer(s, self.res, request_id="r1")["outcome"], "no_difference")
 523 | +        self.assertIsNone(LP.answer(s, self.res, request_id="r9"))
 524 | +        t = LP.segments_of([TRIM])[0]
 525 | +        self.put(t, dict(entry(t), untrimmed_start=1690.0))                               # the trim must match
 526 | +        self.assertIsNone(LP.answer(t, self.res))
 527 | +        with open(LP.result_file(LP.segments_of([CLIP])[0], self.res), "w") as f:
 528 | +            f.write("{not json")
 529 | +        self.assertIsNone(LP.answer(LP.segments_of([CLIP])[0], self.res))                  # unreadable: no answer
 530 | +
 531 | +
 532 | +class TestDecide(unittest.TestCase):
 533 | +    s = LP.segments_of([CLIP])[0]
 534 | +
 535 | +    def test_the_outcomes(self):
 536 | +        for out in ("no_difference", "adopted", "two_readings"):
 537 | +            self.assertEqual(LP.decide(self.s, entry(self.s, out))["verdict"], "pass")
 538 | +        self.assertEqual(LP.decide(self.s, entry(self.s, "hold", reason="ruling 72: at ['x']"))["why"],
 539 | +                         "ruling 72: at ['x']")
 540 | +        for e in (None, entry(self.s, "error"), entry(self.s, "decoded"), entry(self.s, "adopt_spoken"),
 541 | +                  entry(self.s, "adopt_spoken", spoken_text="  ")):
 542 | +            self.assertEqual(LP.decide(self.s, e)["verdict"], "error", e and e.get("outcome"))
 543 | +
 544 | +    def test_adopt_spoken_only_inside_ruling_67s_class_by_this_sides_check(self):
 545 | +        rep = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="I think I think Bitcoin only dropped like "
 546 | +                                                                          "5, 6%."))
 547 | +        self.assertEqual((rep["verdict"], rep["differences"][0]["class"]), ("adopt", "immediate repetition"))
 548 | +        fw = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="I think the Bitcoin only dropped like 5, 6%."))
 549 | +        self.assertEqual(fw["verdict"], "adopt")
 550 | +        for spoken in ("I think Bitcoin only dropped like 7, 6%.", "I think Ethereum only dropped like 5, 6%.",
 551 | +                       "I think Bitcoin never dropped like 5, 6%."):                      # a number, a name, a negation
 552 | +            d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
 553 | +            self.assertEqual(d["verdict"], "hold", spoken)
 554 | +            self.assertIn("outside ruling 67's class", d["why"])
 555 | +        same = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="i think bitcoin only dropped like 5 6%"))
 556 | +        self.assertEqual(same["verdict"], "pass")                                          # no canonical difference
 557 | +
 558 | +
 559 | +class TestCheck(Dirs):
 560 | +    def run_check(self, segs, appear=None, timeout=60.0):
 561 | +        t = [0.0]
 562 | +        sleeps = []
 563 | +
 564 | +        def sleep(s):
 565 | +            sleeps.append(s)
 566 | +            t[0] += s
 567 | +            if appear and len(sleeps) == 1:
 568 | +                appear()
 569 | +        rep = LP.check(segs, "pp-selectid.ledger_x.1", self.req, self.res, timeout_s=timeout, poll_s=10.0,
 570 | +                       clock=lambda: t[0], sleep=sleep, log=lambda m: None)
 571 | +        return rep, sleeps
 572 | +
 573 | +    def test_answers_on_file_are_used_and_nothing_is_asked(self):
 574 | +        segs = LP.segments_of([HOOK, CLIP])
 575 | +        for s in segs:
 576 | +            self.put(s, entry(s))
 577 | +        rep, sleeps = self.run_check([HOOK, CLIP])
 578 | +        self.assertEqual((rep["ok"], rep["request_id"], sleeps, os.path.exists(self.req)), (True, None, [], False))
 579 | +        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.25cd6f15e6c9.json")
 580 | +
 581 | +    def test_a_missing_answer_asks_the_whole_line_up_and_waits_for_its_own(self):
 582 | +        segs = LP.segments_of([HOOK, CLIP])
 583 | +        self.put(segs[0], entry(segs[0]))                                                  # one answered before
 584 | +        self.put(segs[1], entry(segs[1], "error"))                                         # an error: asked again
 585 | +
 586 | +        def appear():
 587 | +            for s in segs:
 588 | +                self.put(s, entry(s, rid="pp-selectid.ledger_x.1", at="2026-11-13T23:00:00Z"))
 589 | +        rep, sleeps = self.run_check([HOOK, CLIP], appear)
 590 | +        self.assertEqual((rep["ok"], rep["request_id"], len(sleeps)), (True, "pp-selectid.ledger_x.1", 1))
 591 | +        with open(os.path.join(self.req, "pp-selectid.ledger_x.1.json")) as f:
 592 | +            req = json.load(f)
 593 | +        self.assertEqual(len(req["segments"]), 2)                                          # the WHOLE line-up
 594 | +
 595 | +    def test_no_answer_in_time_is_no_verdict_never_a_pass(self):
 596 | +        rep, sleeps = self.run_check([HOOK, CLIP], timeout=30.0)
 597 | +        self.assertFalse(rep["ok"])
 598 | +        self.assertIn("no answer from the render's lock in time", rep["error"])
 599 | +        self.assertEqual(sleeps, [10.0, 10.0, 10.0])
 600 | +
 601 | +    def test_a_hold_is_not_ok_and_is_not_an_error(self):
 602 | +        segs = LP.segments_of([HOOK, CLIP])
 603 | +        self.put(segs[0], entry(segs[0], "hold", reason="PinError: edge"))
 604 | +        self.put(segs[1], entry(segs[1]))
 605 | +        rep, _ = self.run_check([HOOK, CLIP])
 606 | +        self.assertEqual((rep["ok"], rep["error"], rep["segments"][0]["verdict"]), (False, None, "hold"))
 607 | +
 608 | +
 609 | +class TestApply(Dirs):
 610 | +    def pk(self):
 611 | +        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
 612 | +                             for m in (HOOK, CLIP)],
 613 | +                "lines": [{"slot": "takeaway", "text": "Durability matters more than speed."}],
 614 | +                "hook_first_words": " ".join(HOOK["text"].split()[:8])}
 615 | +
 616 | +    def pre(self, hook_spoken=None):
 617 | +        segs = LP.segments_of([HOOK, CLIP])
 618 | +        self.put(segs[0], entry(segs[0], "adopt_spoken", spoken_text=hook_spoken) if hook_spoken else entry(segs[0]))
 619 | +        self.put(segs[1], entry(segs[1]))
 620 | +        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)
 621 | +
 622 | +    def test_an_adopted_text_is_sealed_with_its_record_and_the_hook_words_follow(self):
 623 | +        spoken = "Bitcoin launched in in January of 2009. It's never been renamed."      # 'in' said twice
 624 | +        pk = LP.apply(self.pk(), self.pre(spoken))
 625 | +        s = pk["segments"][0]
 626 | +        self.assertEqual(s["text"], spoken)
 627 | +        self.assertEqual(s["attested"]["was"], HOOK["text"])
 628 | +        self.assertIn(s["attested"]["differences"][0]["class"], ("immediate repetition", "function word"))
 629 | +        self.assertEqual(pk["hook_first_words"], "Bitcoin launched in in January of 2009. It's")
 630 | +        named = "Bitcoin Bitcoin launched in January of 2009. It's never been renamed."   # a name is critical
 631 | +        with self.assertRaises(ValueError):                                                # (L-v 2): held
 632 | +            LP.apply(self.pk(), self.pre(named))
 633 | +        self.assertEqual(LP.pin_problems(pk), [])
 634 | +        self.assertNotIn("attested", pk["segments"][1])
 635 | +
 636 | +    def test_apply_refuses_what_does_not_cover_or_pass_or_is_quoted(self):
 637 | +        pre = self.pre()
 638 | +        other = self.pk()
 639 | +        other["segments"][1]["end"] = 958.0
 640 | +        with self.assertRaises(ValueError):
 641 | +            LP.apply(other, pre)                                                          # not these segments
 642 | +        with self.assertRaises(ValueError):
 643 | +            LP.apply(self.pk(), dict(pre, ok=False))
 644 | +        spoken = "Bitcoin launched in January of 2009. It's it's never been renamed."
 645 | +        quoting = self.pk()
 646 | +        quoting["lines"] = [{"slot": "takeaway", "text": "It's it's never been renamed, and that matters."}]
 647 | +        with self.assertRaises(ValueError):
 648 | +            LP.apply(quoting, self.pre(spoken))
 649 | +
 650 | +    def test_the_pin_stage_needs_a_passing_pre_check_on_these_segments(self):
 651 | +        self.assertIn("no passing lock pre-check", LP.pin_problems(self.pk())[0])
 652 | +        pk = LP.apply(self.pk(), self.pre())
 653 | +        self.assertEqual(LP.pin_problems(pk), [])
 654 | +        pk["segments"][0]["start"] = 216.2
 655 | +        self.assertIn("does not cover", LP.pin_problems(pk)[0])
 656 | +
 657 | +
 658 | +if __name__ == "__main__":
 659 | +    unittest.main()
 660 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 661 | index d084147..b395b01 100644
 662 | --- a/tests/package/test_medley.py
 663 | +++ b/tests/package/test_medley.py
 664 | @@ -524,7 +524,7 @@ class Rig:
 665 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 666 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 667 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 668 | -                 cached=False, candidate=None, visuals=None, registered=None):
 669 | +                 cached=False, candidate=None, visuals=None, registered=None, lock_check=None):
 670 |          import providers as P
 671 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 672 |          self.takeaways, self.spend = list(takeaways or []), spend
 673 | @@ -535,6 +535,7 @@ class Rig:
 674 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 675 |          self.candidate, self.seeds = candidate, []          # ruling 66: build from a candidate; the seeds asked with
 676 |          self.registered = registered                        # ruling 66: the registry's line-ups (candidates.registered)
 677 | +        self.lock_check = lock_check                        # rulings 68 / 72: the render's lock (lock_precheck.check)
 678 |          self.visuals, self.visual_calls = dict(visuals or {}), []   # ruling 70: {moment id: record} (default: clean)
 679 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 680 |          self.screens, self.events, self.a_seen = [], [], []
 681 | @@ -667,6 +668,8 @@ class Rig:
 682 |          kw, path = ({"candidate": self.candidate} if self.candidate is not None else {}), None
 683 |          if self.registered is not None:
 684 |              kw["registered"] = self.registered
 685 | +        if self.lock_check is not None:
 686 | +            kw["lock_check"] = self.lock_check
 687 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 688 |              import tempfile
 689 |              fd, path = tempfile.mkstemp(suffix=".json")
 690 | @@ -2040,6 +2043,129 @@ class TestRuling66Amended(unittest.TestCase):
 691 |                                               cx("the real productivity story"))[1], False)        # a clip's own
 692 |  
 693 |  
 694 | +def lock_stub(verdicts=None, error=False, calls=None):
 695 | +    """lock_precheck.check as the build calls it: each moment's outcome from `verdicts` ({moment id: (outcome,
 696 | +    spoken_text)}, default no_difference), decided by the real lock_precheck.decide; error: no answer at all."""
 697 | +    import lock_precheck as LP
 698 | +
 699 | +    def check(segs):
 700 | +        req = LP.segments_of(segs)
 701 | +        if calls is not None:
 702 | +            calls.append([m["moment_id"] for m in segs])
 703 | +        if error:
 704 | +            return {"ok": False, "request_id": "r", "error": "no answer from the render's lock in time",
 705 | +                    "segments": [dict(s, verdict="error", outcome=None, why="no answer", entry=None) for s in req]}
 706 | +        rows = []
 707 | +        for m, s in zip(segs, req):
 708 | +            out, spoken = (verdicts or {}).get(m["moment_id"], ("no_difference", None))
 709 | +            e = {"outcome": out, "reason": "PinError: the edge word" if out == "hold" else None,
 710 | +                 "spoken_text": spoken, "request_id": "r", "at": "2026-11-13T23:00:00Z", "lock": {"sha256": "ab" * 32}}
 711 | +            rows.append(dict(s, **LP.decide(s, e), entry={"request_id": "r", "outcome": out}))
 712 | +        return {"ok": all(r["verdict"] in ("pass", "adopt") for r in rows), "request_id": "r", "segments": rows,
 713 | +                "error": None}
 714 | +    return check
 715 | +
 716 | +
 717 | +class TestRuling72Lock(unittest.TestCase):
 718 | +    """RULINGS 68 / 72 (14:02; live 17:17 Nov 13): the render's own lock, asked for a line-up whose clips pass, BEFORE
 719 | +    any write: a held clip is out and the line-up re-lined; no verdict stops the search with nothing written; a package
 720 | +    seals the approved texts, or an adopted spoken text with its "attested" record; the pin stage checks it again."""
 721 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 14.0)]   # every line-up >= 39 s
 722 | +
 723 | +    def test_a_held_clip_is_out_and_the_line_up_is_re_lined_before_any_write(self):
 724 | +        calls = []
 725 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 726 | +                  lock_check=lock_stub({"x": ("hold", None)}, calls=calls))
 727 | +        out = rig.run()
 728 | +        self.assertEqual(calls, [["h", "x", "y"], ["h", "y", "z"]])
 729 | +        self.assertEqual(rig.write_calls, [(["h", "y", "z"], None)])               # nothing written for the held one
 730 | +        self.assertIn("ruling 72: the render's lock holds x: PinError: the edge word", out["tried"][0]["why"])
 731 | +        self.assertEqual(out["tried"][0]["precheck"]["segments"][1]["verdict"], "hold")
 732 | +        self.assertIsNotNone(out["package"])
 733 | +        import lock_precheck as LP
 734 | +        self.assertEqual(LP.pin_problems(out["package"]), [])                       # the pin stage's own check
 735 | +
 736 | +    def test_no_verdict_writes_nothing_and_stops_the_search(self):
 737 | +        rig = Rig(self.MS, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)] * 2, [None],
 738 | +                  lock_check=lock_stub(error=True))
 739 | +        out = rig.run()
 740 | +        self.assertIsNone(out["package"])
 741 | +        self.assertEqual((rig.write_calls, len(rig.medley_calls)), ([], 1))       # no write, no second angle
 742 | +        self.assertTrue(out["tried"][0]["budget"])
 743 | +        self.assertIn("no lock verdict", out["lock_stop"])
 744 | +        c = PK.load_candidate(TestRuling66Candidate().record(), source="proof/ledger_x")
 745 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c,
 746 | +                  lock_check=lock_stub(error=True)).run()
 747 | +        self.assertEqual(out["candidate"]["class"], "budget")                      # it stays as it was
 748 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c,
 749 | +                  lock_check=lock_stub({"y": ("hold", None)})).run()
 750 | +        self.assertEqual(out["candidate"]["class"], "clip")                        # a clip fails a gate: closed
 751 | +
 752 | +    def test_an_adopted_spoken_text_is_sealed_with_its_record(self):
 753 | +        import lock_precheck as LP
 754 | +        spoken = self.MS[0]["text"].replace(" ", " the ", 1)                      # one function word more
 755 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 756 | +                  lock_check=lock_stub({"h": ("adopt_spoken", spoken)}))
 757 | +        pk = rig.run()["package"]
 758 | +        self.assertEqual(pk["segments"][0]["text"], spoken)
 759 | +        self.assertEqual(pk["segments"][0]["attested"]["was"], self.MS[0]["text"])
 760 | +        self.assertEqual(pk["hook_first_words"], " ".join(spoken.split()[:8]))
 761 | +        self.assertEqual(LP.pin_problems(pk), [])
 762 | +        pin = package_pin.to_pin(spk(pk), "test")
 763 | +        self.assertEqual(pin["segments"][0]["approved_text"], spoken)
 764 | +        self.assertEqual(pin["segments"][0]["attested"]["was"], self.MS[0]["text"])   # sealed (SEALED_LATER)
 765 | +        mp = pin["moments_package"]
 766 | +        self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"],
 767 | +                                          mp["caption"], mp["gates"], mp.get("btc_screen")), mp["package_sha256"])
 768 | +        bare = dict(pin["segments"][0])
 769 | +        bare.pop("attested")
 770 | +        self.assertNotEqual(package_pin.seal([bare] + pin["segments"][1:], mp["edl_vo"], mp["signoff_expected"],
 771 | +                                             mp["title"], mp["caption"], mp["gates"], mp.get("btc_screen")),
 772 | +                            mp["package_sha256"])                                 # the record is in the seal
 773 | +
 774 | +    def test_a_pre_check_that_raises_is_no_verdict_never_a_crash(self):
 775 | +        """Audit 1744 C1 (glm P1-2): a request that cannot be written, or an answer that cannot be decided, raises
 776 | +        inside lock_check: the line-up gets no write, the search stops, and the build still returns its record."""
 777 | +        def boom(segs):
 778 | +            raise OSError("the lock_requests directory is not writable")
 779 | +        rig = Rig(self.MS, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)] * 2, [None],
 780 | +                  lock_check=boom)
 781 | +        out = rig.run()
 782 | +        self.assertIsNone(out["package"])
 783 | +        self.assertEqual((rig.write_calls, len(rig.medley_calls)), ([], 1))
 784 | +        self.assertIn("OSError: the lock_requests directory is not writable", out["lock_stop"])
 785 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 786 | +        calls = []
 787 | +
 788 | +        def second_raises(segs):                        # the voiced line-up passes; the no-voice one raises
 789 | +            calls.append(len(segs))
 790 | +            if len(calls) > 1:
 791 | +                raise ValueError("an answer that cannot be decided")
 792 | +            return lock_stub()(segs)
 793 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
 794 | +                  [None, None], takeaways=bad, lock_check=second_raises).run()
 795 | +        self.assertIsNone(out["package"])
 796 | +        self.assertIn("ValueError: an answer that cannot be decided", out["lock_stop"])   # stops, as voiced
 797 | +
 798 | +    def test_the_pin_stage_compares_the_text_the_lock_passed(self):
 799 | +        import lock_precheck as LP
 800 | +        pk = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], lock_check=lock_stub()).run()[
 801 | +            "package"]
 802 | +        self.assertEqual(LP.pin_problems(pk), [])
 803 | +        pk["segments"][1]["text"] += " And more."                                 # changed after the lock passed
 804 | +        self.assertIn("as they now stand", LP.pin_problems(pk)[0])
 805 | +
 806 | +    def test_the_no_voice_line_up_asks_the_lock_too(self):
 807 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 808 | +        calls = []
 809 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
 810 | +                  [None, None], takeaways=bad, lock_check=lock_stub({"z": ("hold", None)}, calls=calls))
 811 | +        out = rig.run()
 812 | +        self.assertEqual(calls, [["h", "x", "y"], ["h", "x", "y", "z"]])          # its own line-up, the added clip
 813 | +        self.assertIsNone(out["package"])
 814 | +        self.assertIn("ruling 68 / 72: the render's lock", out["tried"][0]["no_voice"]["why_not"])
 815 | +
 816 | +
 817 |  class TestRuling65Caption(unittest.TestCase):
 818 |      """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 819 |      alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 820 | 
```

---

You are auditing a change to the medley pin builder on branch pp-selectid (Protocol Pulse: the builder of sealed medley
pins that an integrator renders). Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- A pin seals each clip's approved_text. At the render, ruling 17 locks the approved text to the render's own decode
  of the audio; a difference HOLDS the render.
- RULING 67: when the texts differ only by function words or the speaker's own immediate repetitions (attest.carry_class;
  never a number, a name or a negation: critical tokens), the pin may be re-sealed with the attested text and the
  verdicts carry over, recorded as "attested" (a sealed field: package_pin.SEALED_LATER). Lines that quote the changed
  words are re-gated first.
- RULING 68 (orchestrator 14:02): the integrator's pin-stage ruling-17 pre-check: "When it exists, your approved text
  comes from it."
- RULING 72 (now live on the integrator's side, 17:17), the contract they gave:
  - requests go to tests/package/proof/lock_requests/*.json (<name>.tmp, then rename). The service only reads there
    and answers each name + content once. Send the WHOLE line-up in one request, start/end exactly as the pin carries
    them.
  - results (read only): /home/ultron/protocol_pulse/data/lock_precheck/results/<video_id>.<start %.3f>-<end %.3f>.
    25cd6f15e6c9.json, a list. Take the newest entry with rules == "ruling 17 + ruling 72" whose window and role /
    approved_text / trimmed fields match yours; entries without "rules" are ruling 68's, ignore them.
  - outcomes: no_difference / adopted / two_readings = pass. adopt_spoken: "spoken_text" is the text to seal (already
    through the render's validate_range + segment_lock), every difference being in ruling 67's class. hold: the reason.
    error: no verdict, never a pass, never reused.
  - their advice: send the candidate texts BEFORE the paid verdicts.

The change:
1. pipeline/lock_precheck.py (new):
   - segments_of mirrors package_pin.to_pin: role, ms-rounded start/end, the moment's text, the trim fields only
     when trimmed;
   - answer(): the newest matching entry, optionally only a given request_id's;
   - send(): .tmp, then rename; never over an existing request;
   - decide(): adopt_spoken is adopted only when THIS side's attest.carry_class agrees; otherwise a hold;
   - check(): answers already on file are reused (never an error); else the whole line-up is sent and its own
     answers awaited (timeout 1200 s, poll 10 s); no answer = error;
   - apply(): the package's adopted texts plus the "attested" record and hook_first_words. It refuses unless the
     check passed and covers exactly the package's segments, and when a line quotes changed words;
   - pin_problems(): the pin stage's own check.
2. package.build(lock_check=) asks it for a line-up whose clips pass, BEFORE any write:
   - a held clip is dropped and doomed, and the line-up re-lined;
   - an error writes nothing and stops the search (out["lock_stop"], rec["budget"], so a candidate's class is
     "budget" and it stays as it was). Two guards stop it, the inner loop's condition and the angle loop's; either
     alone suffices;
   - a package goes through LP.apply before it is appended;
   - the no-voice line-up (its added clip) asks too.
   lock_check None (the test rigs): unchanged.
3. package_pin.to_pin copies "attested" into the pin segment (already sealed when present: SEALED_LATER). seal() is
   not changed. The integrator imports this file live for its seal recompute.
4. The driver passes lock_check to every build (request ids "pp-selectid.<build dir>.<n>"), and before write_pin
   refuses a package whose pin_problems() is non-empty.
5. Tests:
   - test_lock_precheck (12): the request's segments, matching and newest, request-id filtering, unreadable files,
     every outcome, this side's carry-class veto (a number, a name, a negation), reuse vs asking, the timeout,
     apply's refusals, the pin-stage check;
   - test_medley TestRuling72Lock (4): hold, then re-line; no verdict, then no write and the search stops (a
     candidate's class: budget; a held clip: clip); adoption sealed with its record and the seal recomputes; the
     no-voice line-up asks.
   Mutation runs: each wiring point removed fails a test. The two stop guards fail only together, by design.

Check, against the diff:
- that no pin can be sealed with a text the render's lock did not pass or adopt (the build gate, apply, and the
  driver's pin_problems);
- that an adopted text is only ever within ruling 67's class by THIS side's check, and is recorded and sealed;
- that "no verdict" is never a pass, and never closes a line-up as if it failed;
- the matching rules (newest, the ruling-72 entries only, window rounding, trim fields) against the contract above;
- request writing: atomic, never over an existing request, ids within the allowed characters;
- that nothing here changes what any other gate accepts, or seal().

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
