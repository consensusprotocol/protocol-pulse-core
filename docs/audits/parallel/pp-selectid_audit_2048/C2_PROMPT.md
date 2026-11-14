# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2048
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 109 s finish=stop usage in 17513 / out 418 usd~0.098 (upper-bound price)

**P0: none verifiable from diff**  
**P1: none verifiable from diff**  
**P2: pipeline/providers.py:296** (concrete: if on_abandon() raises e.g. SpendLimit before the `raise DeadlineExceeded`, the `except DeadlineExceeded` block is skipped, `_log_slow` for "missed_deadline" never runs, and Router.call sees the on_abandon exception instead of triggering the documented failover path; the ordering test only exercises successful on_abandon).  
**P2: pipeline/attest.py:56** (the `one` counter makes >1 function-word substitution return None on the second occurrence, matching ruling 84(b) and integrator rules 3-4 exactly; the wider "all function words" integrator variant mentioned in background is not implemented here).  

All other checked items match the diff:  
- class_84 implements the five integrator rules (fillers spoken-only, critical=None, at-most-one "one function word", other subs=None, pure insert/drop uses unchanged carry_class); tests in test_attest.py:340 and test_lock_precheck.py:396 cover the 20:12 held span (now adopts) and all must-hold cases.  
- Ledger arithmetic in Router._late (subtract booked, add delta/estimate/reported) produces exact on-time numbers with no double-count (verifiable in test_providers.py:490 and :522).  
- _within lock guarantees booking precedes on_late (test:550 shows order ["booked", "answered", "booked done", ("late", ...)]); on_late exceptions are dropped (line 202); ledger writes from daemon thread are under self._lock().  
- LY limits updated exactly per ruling 83(b); RULES string matches integrator; nothing integrator held can adopt here (any None class => hold).  
- No violation of L-j (release auth), L-k (canon), M12 (fail-closed), LAW 20/22, or smallest-diff constraints visible in diff.  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 38 s finish=stop usage in 19629 / out 2158 usd~0.091 (upper-bound price)

# Code Audit: pp-selectid-2048

## P0 Findings

**1. `pipeline/providers.py` (lines 207-210): Race condition in `_within` allows double-booking or missed booking**
The check `if not done.is_set()` inside the lock is racy. If the worker thread sets `done` *just before* the main thread acquires the lock, the main thread sees `done.is_set() == True` and skips the `abandon()` call. However, the worker thread has already finished and will check `late = "abandoned" in box`. Since `box["abandoned"]` was never set (because the main thread skipped it), `late` is `False`, and `on_late` is never called.
*   **Scenario:** A call times out. The worker thread finishes at `T+0.001s`. The main thread wakes from `done.wait()` at `T+0.002s`. It acquires the lock. `done.is_set()` is `True`. It does **not** raise `DeadlineExceeded` and does **not** call `abandon()`. It proceeds to `if "error" in box` or `return box["value"]`.
*   **Result:** The call is treated as successful (or failed with its own exception), but **no spend is booked** for the prompt tokens, and **no late answer logic** runs. This violates Ruling 83(a) ("booked at its prompt tokens") and Law M12 (fail closed/accurate accounting). The ledger will be under-reported.
*   **Fix:** The `abandon` logic must be triggered by the *timeout* event, not by the state of the worker thread at the moment the main thread wakes. The current structure conflates "worker finished" with "deadline passed".

**2. `pipeline/providers.py` (lines 254-259): Ledger arithmetic error in `_late` for unreported estimates**
In `_late`, when a late answer arrives without a vendor figure (`rep` is None):
```python
d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
# ...
else:
    d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
```
The code subtracts the initial `booked` amount (prompt tokens) and adds the new `usd` (full estimate). This is correct *if* `booked` was the only thing added to `usd_unreported_estimate` for this call. However, `abandon()` calls `self._settle(key, b, {"in": 0, "out": 0}, booked, role)`. We must verify `_settle` adds to `usd_unreported_estimate`. Assuming it does, the math holds.
*   **BUT:** Look at line 259: `d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)`. If `booked` is larger than the current `usd_unreported_estimate` (e.g., due to floating point or previous errors), this can go negative. More critically, if the vendor *does* report a figure, the code does:
    ```python
    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
    # ...
    if _num(rep):
        # ... adds to usd_reported
    else:
        d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
    ```
    This logic is sound *only* if `abandon()` correctly added `booked` to `usd_unreported_estimate`. If `abandon()` failed or was skipped (see P0 #1), this subtraction will corrupt the ledger.

**3. `pipeline/attest.py` (lines 44-46): `class_84` filler detection is position-dependent and fragile**
```python
drop = {i for _tag, a, b, _c, _d in ops for i in range(a, b) if r[i] in FILLERS}
```
This drops fillers from the *spoken* side (`r`) based on the *original* diff opcodes. However, `r` is the canonicalized spoken text. If a filler is part of a larger substitution block (e.g., spoken: "um the", approved: "the"), the opcode might be `replace` or `insert`. If it's `insert`, `r[i]` is the filler. If it's `replace`, `r[i]` might be "um" and `p[j]` might be "the". The code drops `r[i]` if it's a filler. This seems correct for "filler on spoken side only".
*   **Issue:** What if the filler is *not* in a separate opcode but part of a `replace` where the other side is also a filler? E.g., spoken: "um", approved: "uh". Both are fillers. `drop` will contain the index of "um". `r2` will be empty. The diff of `r2` vs `p` will show "uh" as an insert. `carry_class` will be called. Is "uh" a function word? No. Is it a repetition? No. It will likely return `None` (hold). This is correct per Ruling 84 (fillers on approved side alone hold).
*   **However:** The logic `one += k is not None` (line 58) is buggy. `k` is a string or `None`. `k is not None` is a boolean. `one` is an integer. `one += True` works in Python, but it's confusing. More importantly, if `k` is `None`, `one` is not incremented. If `k` is "one function word", `one` is incremented. This tracks the count of "one function word" classes. The check `one == 0` ensures only the *first* such difference is allowed. This logic is correct but obscure.

## P1 Findings

**4. `pipeline/providers.py` (lines 196-203): `on_late` exception handling swallows errors**
```python
if late and on_late is not None:
    try:
        on_late(box["abandoned"], box.get("value"), box.get("error"))
    except Except

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 2048 (ruling 83 (a)+(b): abandoned calls booked at their prompt tokens, a late figure replacing it, cap $20 / stop $16; ruling 84: this side's class): cycle 1 consensus

- **grok:** "SHIP: yes". No P0 or P1. Two P2s.
- **qwen:** "SHIP: NO", on three P0s and one P1. The P0s are refuted below from the code. The P1 is implemented.
- **glm-5.3-flash:** NO ANSWER. The call was still open after 13 min (21:01 ET), against 76 s for the same reviewer
  in audit 1810. This is the Heimdall glm outage of tonight: 5 of 5 glm step-A calls missed 120 s in the 20:12
  build. Cycle 1 rests on grok and qwen. If glm answers later, its file is read before the final consensus.

## Implemented

- **grok P2 (providers.py, abandon):** when the booking raises (SpendLimit on an unreadable ledger), the call still
  stops as before (fail closed: no paid call on a total nobody can read). The `missed_deadline` line is now written
  BEFORE the booking, so the miss is on record either way. New test: the ledger breaks while the call is out. The
  call raises SpendLimit, the next back-end is never asked, the log holds exactly one `missed_deadline`, the
  abandoned thread's late answer changes nothing, and the corrupt ledger is never overwritten.
- **qwen P1-4 (on_late swallows errors):** the late ledger write is now its own method, Router._replace_booking (one
  write under the ledger lock: tmp file + os.replace, so all or nothing). _late catches its failure and records it
  on the late answer's log line (`replaced: false`, `ledger_error`). The prompt-token booking then stands. New
  test: the ledger breaks before the late answer, and the line carries `replaced: false` and the SpendLimit.
  `_within` still drops an exception from on_late: nobody is left to catch it there. _late itself no longer raises
  for a ledger failure.

## Refuted (with the code)

- **qwen P0-1 ("race in _within: no booking when the worker finishes just before the lock"):**
  - If the worker ends between `done.wait` timing out and the main thread taking the lock, then `done.is_set()` is
    True and nothing is abandoned.
  - `_within` then returns the worker's value (set BEFORE `done`), or raises its error.
  - Router.call treats that as an on-time answer: `_settle(key, b, usage, usd, role)` books its full cost, with the
    vendor's figure when there is one. An error books what any error books (the reservation is released).
  - So nothing is under-booked. That is the intended behaviour: an answer at the deadline is used, not abandoned.
  - The booking cannot be skipped for an abandoned call either. `box["abandoned"]` is set only by the on_abandon
    call, under the lock, before the raise, and the worker reads it under the same lock.
  - The ordering test drives the race with events: ["booked", "answered", "booked done", late].
- **qwen P0-2 (the _late arithmetic depends on abandon):** it does, by construction.
  - `_late` runs only when `box` holds on_abandon's value.
  - That value ex

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_2048/C2_STEP.diff (617 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index 78a4fde..f45e4d5 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -10,7 +10,10 @@ refused). The takeaway, title and caption are re-gated only if they quote the ch
   6 |  The diff is the render's own (pipeline/pinned.adjudicate_lock): canon.canon_tokens of the run's decode against the
   7 |  approved text, difflib.SequenceMatcher(autojunk=False) opcodes. canon.py here is byte-identical to the render's, and
   8 |  critical() is the render's _lv2_critical with its lists. CPU only, no model call. Imports nothing from package.py
   9 | -(package_pin, which the integrator's check imports, must never pull it in)."""
  10 | +(package_pin, which the integrator's check imports, must never pull it in).
  11 | +
  12 | +RULING 84 (orchestrator 20:41 Nov 13) has its own class, class_84, for the render's lock pre-check only (the
  13 | +second recogniser against the lock): fillers, and ONE function word. carry_class (ruling 67's re-seal) is unchanged."""
  14 |  import re
  15 |  from difflib import SequenceMatcher
  16 |  
  17 | @@ -38,6 +41,10 @@ what which who whom whose why how where
  18 |  """.split())
  19 |  
  20 |  
  21 | +# RULING 84 (a): the fillers the second recogniser hears and Whisper drops, exactly the ruling's list (canon tokens)
  22 | +FILLERS = frozenset(("um", "uh", "er", "ah", "mm", "hmm"))
  23 | +
  24 | +
  25 |  def critical(tok, texts):
  26 |      """Law L-v 2 as the render tests it (pinned._lv2_critical): a number, a negation, or a name (in either text, a
  27 |      capitalised word that does not open a sentence; 'I' excepted). A doubtful token is critical."""
  28 | @@ -78,6 +85,39 @@ def carry_class(r, p, op, texts):
  29 |      return "immediate repetition" if any(repeats(*s) for s in sides) else "function word"
  30 |  
  31 |  
  32 | +def class_84(spoken, approved):
  33 | +    """RULING 84 (orchestrator 20:41 Nov 13): the render's lock pre-check class, as the integrator's pre-check applies
  34 | +    it (its message of 20:4x Nov 13), on this side's comparison: the spoken text (the second recogniser's reading)
  35 | +    against the approved text. -> [{"spoken", "approved", "class"}], one per difference; a class None holds.
  36 | +    1. A filler (FILLERS) inside a difference is dropped from the SPOKEN side only: class "filler". A filler on the
  37 | +       approved side alone is not in the class.
  38 | +    2. The fillers dropped, the texts are compared again. A number, a negation or a name on either side holds.
  39 | +    3. One token against one token, both function words: "one function word". At most ONE per span; another holds.
  40 | +    4. Any other substitution (both sides non-empty) holds, a 2-for-2 or 1-for-2 of function words included.
  41 | +    5. An insert or a drop: ruling 67's class (carry_class), unchanged, on the filler-free spoken text."""
  42 | +    texts = (spoken, approved)
  43 | +    r, p, ops = diff(spoken, approved)
  44 | +    drop = {i for _tag, a, b, _c, _d in ops for i in range(a, b) if r[i] in FILLERS}
  45 | +    out = [{"spoken": r[i], "approved": "", "class": "filler"} for i in sorted(drop)]
  46 | +    r2 = [t for i, t in enumerate(r) if i not in drop]
  47 | +    one = 0
  48 | +    for op in SequenceMatcher(None, r2, p, autojunk=False).get_opcodes():
  49 | +        tag, a, b, c, d = op
  50 | +        if tag == "equal":
  51 | +            continue
  52 | +        rs, ps = r2[a:b], p[c:d]
  53 | +        if any(critical(t, texts) for t in rs + ps):
  54 | +            k = None
  55 | +        elif rs and ps:
  56 | +            k = "one function word" if (len(rs) == len(ps) == 1 and rs[0] in FUNCTION_WORDS and
  57 | +                                        ps[0] in FUNCTION_WORDS and one == 0) else None
  58 | +            one += k is not None
  59 | +        else:
  60 | +            k = carry_class(r2, p, op, texts)
  61 | +        out.append({"spoken": " ".join(rs), "approved": " ".join(ps), "class": k})
  62 | +    return out
  63 | +
  64 | +
  65 |  def reads(x, s, lo, hi):
  66 |      """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
  67 |      they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
  68 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
  69 | index 0cc5e96..4ca0726 100644
  70 | --- a/pipeline/lock_precheck.py
  71 | +++ b/pipeline/lock_precheck.py
  72 | @@ -12,7 +12,7 @@ and answers each name and content once.
  73 |  Results: read only, in /home/ultron/protocol_pulse/data/lock_precheck/results/
  74 |  <video_id>.<start %.3f>-<end %.3f>.<decoder[:12]>.json. Each file is a list. The answer is the newest entry (by "at")
  75 |  that meets all of these:
  76 | -- rules == RULES ("ruling 17 + ruling 72 + ruling 73" since 18:43 Nov 13; an answer under any other rules string,
  77 | +- rules == RULES ("ruling 17 + ruling 72 + ruling 73 + ruling 84" since ruling 84; an answer under any other rules string,
  78 |    or in a file named for another decoder, is not valid for the render's code and is never read);
  79 |  - its window is the segment's [start, end];
  80 |  - its role, approved_text, trimmed_leading and untrimmed_start equal the request's.
  81 | @@ -21,9 +21,11 @@ Entries without "rules" are ruling 68's, from before, and are never read.
  82 |  Outcomes:
  83 |  - no_difference, adopted, two_readings: pass. The approved text stands.
  84 |  - adopt_spoken: the text to seal is "spoken_text", already through the render's validate_range + segment_lock. It is
  85 | -  adopted only when this side's own check agrees that every difference is in ruling 67's carry-over class
  86 | -  (attest.carry_class: a function word, or the speaker's own immediate repetition; never a number, a name or a
  87 | -  negation). Otherwise it is a hold (fail closed).
  88 | +  adopted only when this side's own check agrees that every difference is in ruling 84's class (attest.class_84,
  89 | +  the integrator's class: a filler the second recogniser heard, ONE 1-for-1 function word, else ruling 67's
  90 | +  carry-over class for an insert or a drop; never a number, a name or a negation). Otherwise it is a hold (fail
  91 | +  closed). Under ruling 84 (b) the spoken text holds the second recogniser's reading of the one function word; the
  92 | +  render's lock keeps its decode's word and records the other reading (the entry's "alternatives").
  93 |  - hold: the clip may not be used with that text. The reason says why.
  94 |  - error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
  95 |    is sent again rather than reusing an error.
  96 | @@ -38,7 +40,8 @@ from datetime import datetime, timezone
  97 |  
  98 |  import attest as AT
  99 |  
 100 | -RULES = "ruling 17 + ruling 72 + ruling 73"   # RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
 101 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84"   # RULING 84 (orchestrator 20:41 Nov 13): the integrator's
 102 | +#   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
 103 |  DECODER = "8a101f222598"                      # side): the render's own cut placement joins the pre-check, so its
 104 |  #   decoder_sha changed (8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7); a passing entry carries
 105 |  #   "cut", and a span the render cannot cut holds ("ruling 73: the render cannot cut this span: ...")
 106 | @@ -137,15 +140,12 @@ def decide(seg, e):
 107 |      spoken, approved = e.get("spoken_text"), seg["approved_text"]
 108 |      if not isinstance(spoken, str) or not spoken.strip():
 109 |          return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
 110 | -    r, p, ops = AT.diff(spoken, approved)
 111 | -    if not ops:                                       # the same canonical words: the approved text stands
 112 | +    diffs = AT.class_84(spoken, approved)
 113 | +    if not diffs:                                     # the same canonical words: the approved text stands
 114 |          return {"verdict": "pass", "outcome": out, "why": "adopt_spoken with no canonical difference"}
 115 | -    classes = [AT.carry_class(r, p, o, (spoken, approved)) for o in ops]
 116 | -    diffs = [{"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "class": k}
 117 | -             for (_, a, b, c, d), k in zip(ops, classes)]
 118 | -    if None in classes:                               # this side's ruling-67 check disagrees: fail closed
 119 | +    if any(x["class"] is None for x in diffs):        # this side's ruling-84 check disagrees: fail closed
 120 |          return {"verdict": "hold", "outcome": out, "differences": diffs,
 121 | -                "why": "adopt_spoken, but by this side's attest.carry_class a difference is outside ruling 67's "
 122 | +                "why": "adopt_spoken, but by this side's attest.class_84 a difference is outside ruling 84's "
 123 |                         "class: " + str([[x["spoken"], x["approved"]] for x in diffs if x["class"] is None])[:300]}
 124 |      return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs}
 125 |  
 126 | @@ -180,11 +180,12 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
 127 |              "error": "; ".join(errs)[:600] or None}
 128 |  
 129 |  
 130 | -def attested(row, run_rule="ruling 72 (live 17:17 Nov 13): adopt_spoken, in ruling 67's carry-over class"):
 131 | +def attested(row, run_rule="ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"):
 132 |      """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
 133 |      return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
 134 |              "carried": "every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
 135 | -                       "ruling 67's carry-over class (checked on this side too), and no line quotes the changed words",
 136 | +                       "ruling 84's class (a filler, one function word, or ruling 67's carry-over class for an insert "
 137 | +                       "or a drop; checked on this side too), and no line quotes the changed words",
 138 |              "render": {"precheck": row["entry"], "spoken_text": row["spoken_text"]}}
 139 |  
 140 |  
 141 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 142 | index aa6c175..55b66b3 100644
 143 | --- a/pipeline/providers.py
 144 | +++ b/pipeline/providers.py
 145 | @@ -178,12 +178,22 @@ class Backend:
 146 |          """The most output tokens this back-end may bill for one call (its own floor applied)."""
 147 |          return max(int(self.spec.get("min_out", 0)), max_tokens)
 148 |  
 149 | -    def upper_usd(self, prompt, max_tokens, system=None):
 150 | -        """The call's spend upper bound: every prompt character a token (a safe over-estimate), IMAGE_TOKENS_UPPER per
 151 | -        image of a vision prompt, + the output cap."""
 152 | +    @staticmethod
 153 | +    def prompt_tokens_upper(prompt, system=None):
 154 | +        """A prompt's input tokens, counted from above: every character a token (a safe over-estimate), + 200 for the
 155 | +        message frame, IMAGE_TOKENS_UPPER per image of a vision prompt."""
 156 |          n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
 157 | -        return self.usd({"in": len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img,
 158 | -                         "out": self.max_out(max_tokens)})
 159 | +        return len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img
 160 | +
 161 | +    def upper_usd(self, prompt, max_tokens, system=None):
 162 | +        """The call's spend upper bound: its prompt tokens (prompt_tokens_upper) + the output cap."""
 163 | +        return self.usd({"in": self.prompt_tokens_upper(prompt, system), "out": self.max_out(max_tokens)})
 164 | +
 165 | +    def prompt_usd(self, prompt, system=None):
 166 | +        """RULING 83 (a) (orchestrator 20:33 Nov 13): what a call abandoned at its deadline is booked at: its PROMPT
 167 | +        tokens at the listed input rate, no output. A call that never answered has no vendor token count, so the
 168 | +        prompt is counted from above (prompt_tokens_upper): never an under-booking."""
 169 | +        return self.usd({"in": self.prompt_tokens_upper(prompt, system), "out": 0})
 170 |  
 171 |      def key(self, name):
 172 |          k = env_value(self.env_path, name)
 173 | @@ -249,22 +259,35 @@ class DeadlineExceeded(Exception):
 174 |      more than 5 min). The call is abandoned, not killed: Python cannot stop the thread."""
 175 |  
 176 |  
 177 | -def _within(seconds, fn):
 178 | +def _within(seconds, fn, on_abandon=None, on_late=None):
 179 |      """fn() in a daemon thread, waited for at most `seconds`. -> its value, or its own exception re-raised, or
 180 | -    DeadlineExceeded. An abandoned thread finishes (or times out) on its own; its result is dropped unrecorded."""
 181 | +    DeadlineExceeded. At the deadline on_abandon() runs (it books the abandoned call) BEFORE DeadlineExceeded is
 182 | +    raised, under a lock the thread takes when it ends, so the booking always comes first. An abandoned thread finishes
 183 | +    (or times out) on its own; then on_late(on_abandon's value, fn's value or None, fn's exception or None) runs in
 184 | +    it (ruling 83 (a): a late answer's own figure replaces the booking). Its text is dropped unrecorded. An exception
 185 | +    from on_late is dropped (it runs where nobody can catch it); the booking then stands."""
 186 |      import threading
 187 | -    box, done = {}, threading.Event()
 188 | +    box, done, lock = {}, threading.Event(), threading.Lock()
 189 |  
 190 |      def run():
 191 |          try:
 192 |              box["value"] = fn()
 193 |          except BaseException as e:            # handed back to the caller below
 194 |              box["error"] = e
 195 | -        finally:
 196 | +        with lock:
 197 |              done.set()
 198 | +            late = "abandoned" in box
 199 | +        if late and on_late is not None:
 200 | +            try:
 201 | +                on_late(box["abandoned"], box.get("value"), box.get("error"))
 202 | +            except Exception:                 # noqa: BLE001 (no caller is left; the booking stands)
 203 | +                pass
 204 |      threading.Thread(target=run, daemon=True, name="pp-deadline").start()
 205 |      if not done.wait(seconds):
 206 | -        raise DeadlineExceeded(f"no answer within {seconds:.0f} s")
 207 | +        with lock:
 208 | +            if not done.is_set():             # still running: abandoned (an answer at the deadline is used below)
 209 | +                box["abandoned"] = on_abandon() if on_abandon is not None else None
 210 | +                raise DeadlineExceeded(f"no answer within {seconds:.0f} s")
 211 |      if "error" in box:
 212 |          raise box["error"]
 213 |      return box["value"]
 214 | @@ -670,7 +693,7 @@ class Router:
 215 |          """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
 216 |          bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
 217 |          estimate for each call whose vendor reports none (usd_unreported_estimate: those calls, and a call abandoned at
 218 | -        its deadline, booked at its upper bound)."""
 219 | +        its deadline, booked at its prompt tokens (ruling 83 (a), 20:33 Nov 13) until a late answer replaces it)."""
 220 |          if self.limit_basis == "reported":
 221 |              if d.get("calls", 0) and "usd_reported" not in d and "usd_unreported_estimate" not in d:
 222 |                  raise SpendLimit("the ledger has calls but keeps no vendor-reported figures: the reported basis "
 223 | @@ -735,6 +758,62 @@ class Router:
 224 |                      d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
 225 |              self._save(d)
 226 |  
 227 | +    def _late(self, ab, value, error):
 228 | +        """RULING 83 (a): an abandoned call that ended after its deadline (in its own thread). An answer is accounted
 229 | +        as an on-time one would have been, in place of its prompt-token booking: the vendor's reported figure, or,
 230 | +        with none, the estimate from its own token counts. No answer (an error): the booking stands. Either way one
 231 | +        line goes to the deadline log (item 55). The answer's text is never used or recorded."""
 232 | +        b, role, booked = ab["backend"], ab["role"], float(ab["usd"])
 233 | +        rec = {"kind": "late_answer" if error is None else "late_error", "role": role, "model": b.name,
 234 | +               "vendor": b.vendor, "deadline_s": ab.get("deadline_s"),
 235 | +               "seconds": round(time.time() - ab["t0"] + float(ab.get("deadline_s") or 0), 2), "booked_usd": booked}
 236 | +        if error is None:
 237 | +            try:
 238 | +                _text, usage, _secs = value
 239 | +                usage = dict(usage or {})
 240 | +            except (TypeError, ValueError):
 241 | +                usage = None
 242 | +            if usage is None:
 243 | +                rec.update(kind="late_error", error="no (text, usage, seconds) from the back-end")
 244 | +            else:
 245 | +                usd, rep = b.usd(usage), usage.get("usd_reported")
 246 | +                rec.update({"in": usage.get("in"), "out": usage.get("out"), "usd_estimate": usd,
 247 | +                            "usd_reported": float(rep) if _num(rep) else None})
 248 | +                if self.spend_path:
 249 | +                    try:
 250 | +                        self._replace_booking(b, role, booked, usage, usd, rep)
 251 | +                        rec["replaced"] = True
 252 | +                    except Exception as e:             # noqa: BLE001 (audit 2048 C1: on record; the prompt-token
 253 | +                        rec.update(replaced=False,     # booking stands, the ledger written whole or not at all)
 254 | +                                   ledger_error=f"{type(e).__name__}: {str(e)[:200]}")
 255 | +        else:
 256 | +            rec["error"] = f"{type(error).__name__}: {str(error)[:200]}"
 257 | +        self._log_slow(rec)
 258 | +
 259 | +    def _replace_booking(self, b, role, booked, usage, usd, rep):
 260 | +        """RULING 83 (a): a late answer's accounting in place of its prompt-token booking, in one ledger write: its
 261 | +        own token counts, its estimate (usd) for the estimate basis, and on the reported basis the vendor's figure
 262 | +        (rep) or, with none, the estimate. The call was counted when it was booked; it is not counted again."""
 263 | +        with self._lock():
 264 | +            d = self._ledger()
 265 | +            bb = d["by_backend"].setdefault(b.name, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0,
 266 | +                                                     "price_usd_per_1m": list(b.price)})
 267 | +            r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
 268 | +            delta = usd - booked
 269 | +            bb.update(usd_estimate=round(bb["usd_estimate"] + delta, 6),
 270 | +                      **{"in": bb["in"] + int(usage.get("in", 0)), "out": bb["out"] + int(usage.get("out", 0))})
 271 | +            r["usd_estimate"] = round(r["usd_estimate"] + delta, 6)
 272 | +            d["usd_estimate"] = round(d["usd_estimate"] + delta, 6)
 273 | +            d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
 274 | +            if _num(rep):
 275 | +                bb.update(usd_reported=round(bb.get("usd_reported", 0.0) + float(rep), 8),
 276 | +                          reported_calls=bb.get("reported_calls", 0) + 1)
 277 | +                d["usd_reported"] = round(d.get("usd_reported", 0.0) + float(rep), 8)
 278 | +            else:
 279 | +                d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
 280 | +            d["late_answers"] = d.get("late_answers", 0) + 1
 281 | +            self._save(d)
 282 | +
 283 |      def reject(self, reply, why=""):
 284 |          """The caller found this reply out of its contract: drop its recording, so the exchange is asked again next
 285 |          time instead of served again (fable C1 U1). Offline replay keeps its recordings. -> True if one was dropped."""
 286 | @@ -810,18 +889,25 @@ class Router:
 287 |                  n = self.heimdall_tripwire()
 288 |                  if n:
 289 |                      notices.append(n)
 290 | +
 291 | +            def abandon(b=b, key=key, name=name):      # RULING 83 (a): booked at its PROMPT tokens (input rate), an
 292 | +                booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
 293 | +                self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 294 | +                                "deadline_s": deadline_s, "seconds": deadline_s,
 295 | +                                "prompt_chars": len(prompt_text(prompt)),
 296 | +                                "max_tokens": max_tokens, "booked_usd": booked})   # evidence first (audit 2048 C1)
 297 | +                self._settle(key, b, {"in": 0, "out": 0}, booked, role)          # an unreadable ledger raises here
 298 | +                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time()}
 299 |              try:
 300 |                  if deadline_s:                         # ruling 5 (22:40): fail over instead of waiting
 301 | -                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system))
 302 | +                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system),
 303 | +                                                on_abandon=abandon, on_late=self._late)
 304 |                  else:
 305 |                      text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 306 | -            except DeadlineExceeded as e:              # abandoned; the vendor may still bill it, so its UPPER bound is
 307 | -                self._settle(key, b, {"in": 0, "out": 0}, upper, role)     # booked as spent (estimate, unreported)
 308 | -                tried.append((name, f"{e} (abandoned at the deadline; its upper bound ${upper:.2f} booked as spent)"))
 309 | -                self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 310 | -                                "deadline_s": deadline_s, "seconds": deadline_s,
 311 | -                                "prompt_chars": len(prompt_text(prompt)),
 312 | -                                "max_tokens": max_tokens})
 313 | +            except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
 314 | +                booked = b.prompt_usd(prompt, system)  # abandon()
 315 | +                tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
 316 | +                                    "ruling 83 (a))"))
 317 |                  continue
 318 |              except RequestRejected as e:
 319 |                  self._settle(key)
 320 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 321 | index 24e4276..dc5fe4a 100644
 322 | --- a/tests/package/proof_ly.py
 323 | +++ b/tests/package/proof_ly.py
 324 | @@ -47,9 +47,9 @@ import speakers as SP  # noqa: E402
 325 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
 326 |  OUT = os.path.join(HERE, "proof")
 327 |  SPEND = os.path.join(OUT, "SPEND_LY.json")
 328 | -LY_LIMIT_USD = 12.0                # ruling 48 (07:02 Nov 13): $12.00 VENDOR-REPORTED in total for this order (the
 329 | -LY_LIMIT_BASIS = "reported"        # old $40 cap by the price-table estimate read ~12x high: $39.49 = $3.46 reported);
 330 | -LY_STOP_USD = 10.0                 # the estimate counts only where a vendor reports none. At $10 no build starts.
 331 | +LY_LIMIT_USD = 20.0                # RULING 83 (b) (20:33 Nov 13): $20.00 VENDOR-REPORTED for this order (ruling 48's
 332 | +LY_LIMIT_BASIS = "reported"        # $12 before; the old $40 cap by the price-table estimate read ~12x high);
 333 | +LY_STOP_USD = 16.0                 # the estimate counts only where a vendor reports none. At $16 no build starts.
 334 |                                     # Each paid call still RESERVES its price-table upper bound while in flight.
 335 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
 336 |  DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
 337 | diff --git a/tests/package/test_attest.py b/tests/package/test_attest.py
 338 | index 5263b7a..522a7b9 100644
 339 | --- a/tests/package/test_attest.py
 340 | +++ b/tests/package/test_attest.py
 341 | @@ -72,6 +72,41 @@ class TestAttest(unittest.TestCase):
 342 |          self.assertEqual(AT.quotes(["No single owner controls the bitcoin network"], r, p, ops), [])
 343 |  
 344 |  
 345 | +
 346 | +class TestClass84(unittest.TestCase):
 347 | +    """RULING 84 (orchestrator 20:41 Nov 13): the pre-check's class, as the integrator applies it, on this side's
 348 | +    comparison (the spoken text against the approved text)."""
 349 | +
 350 | +    def k(self, spoken, approved):
 351 | +        return [(x["spoken"], x["approved"], x["class"]) for x in AT.class_84(spoken, approved)]
 352 | +
 353 | +    def test_fillers_on_the_spoken_side_and_one_function_word(self):
 354 | +        self.assertEqual(self.k("So over time, um, I came to think, uh, or the", "So over time, I came to think, so the"),
 355 | +                         [("um", "", "filler"), ("uh", "", "filler"), ("or", "so", "one function word")])
 356 | +        self.assertEqual(self.k("hmm mm er ah uh um yes", "yes"),
 357 | +                         [(f, "", "filler") for f in ("hmm", "mm", "er", "ah", "uh", "um")])
 358 | +        self.assertEqual(self.k("Um, the", "the"), [("um", "", "filler")])         # capitalised, still not a name
 359 | +        self.assertEqual(self.k("came um came to", "came to"),                      # the repetition, filler-free
 360 | +                         [("um", "", "filler"), ("came", "", "immediate repetition")])
 361 | +        self.assertEqual(self.k("I think the Bitcoin", "I think Bitcoin"), [("the", "", "function word")])
 362 | +        self.assertEqual(self.k("the same", "the same"), [])
 363 | +
 364 | +    def test_what_holds(self):
 365 | +        self.assertEqual(self.k("in the house on it", "on the house in it"),        # a second 1-for-1 holds
 366 | +                         [("in", "on", "one function word"), ("on", "in", None)])
 367 | +        self.assertEqual(self.k("we went to the store", "we went to a shop"), [("the store", "a shop", None)])
 368 | +        self.assertEqual(self.k("went in a store", "went to the store"), [("in a", "to the", None)])   # 2-for-2
 369 | +        self.assertEqual(self.k("the", "the um"), [("", "um", None)])              # a filler on the approved side
 370 | +        self.assertEqual(self.k("I paid 5 dollars", "I paid 6 dollars"), [("5", "6", None)])
 371 | +        self.assertEqual(self.k("it is not", "it is"), [("not", "", None)])
 372 | +        self.assertEqual(self.k("um I asked Mike", "I asked mike"), [("um", "", "filler")])   # canon: the same name
 373 | +
 374 | +    def test_ruling_67s_class_is_unchanged(self):
 375 | +        r, p, ops = AT.diff("so um I came", "so I came")
 376 | +        self.assertEqual([AT.carry_class(r, p, o, ("so um I came", "so I came")) for o in ops], [None])
 377 | +        self.assertEqual(AT.FILLERS, frozenset({"um", "uh", "er", "ah", "mm", "hmm"}))
 378 | +
 379 | +
 380 |  class TestReseal(unittest.TestCase):
 381 |      """reseal() on the pin the render held, with its run's records rebuilt in a temporary directory."""
 382 |  
 383 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 384 | index b65d9d9..229792d 100644
 385 | --- a/tests/package/test_lock_precheck.py
 386 | +++ b/tests/package/test_lock_precheck.py
 387 | @@ -118,11 +118,48 @@ class TestDecide(unittest.TestCase):
 388 |                         "I think Bitcoin never dropped like 5, 6%."):                      # a number, a name, a negation
 389 |              d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
 390 |              self.assertEqual(d["verdict"], "hold", spoken)
 391 | -            self.assertIn("outside ruling 67's class", d["why"])
 392 | +            self.assertIn("outside ruling 84's class", d["why"])
 393 |          same = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="i think bitcoin only dropped like 5 6%"))
 394 |          self.assertEqual(same["verdict"], "pass")                                          # no canonical difference
 395 |  
 396 |  
 397 | +
 398 | +class TestRuling84(unittest.TestCase):
 399 | +    """RULING 84 (orchestrator 20:41 Nov 13): fillers the second recogniser hears adopt; ONE 1-for-1 function word
 400 | +    adopts (the render's lock keeps its decode's word and records the other reading); two hold; any other
 401 | +    substitution holds. The 20:12 build's held span: [['', 'um'], ['', 'uh'], ['so', 'or']]."""
 402 | +    BREEDLOVE = {"moment_id": "b", "video_id": "uaHNzi-Kgr8", "start": 100.0, "end": 112.6,
 403 | +                 "text": "So over time, I came to think so the money itself was broken."}
 404 | +    s = LP.segments_of([BREEDLOVE])[0]
 405 | +
 406 | +    def test_the_rules_string_is_the_integrators(self):
 407 | +        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84")
 408 | +
 409 | +    def test_the_held_span_of_the_20_12_build_now_adopts(self):
 410 | +        spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 411 | +        d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
 412 | +        self.assertEqual(d["verdict"], "adopt")
 413 | +        self.assertEqual([(x["spoken"], x["approved"], x["class"]) for x in d["differences"]],
 414 | +                         [("um", "", "filler"), ("uh", "", "filler"), ("or", "so", "one function word")])
 415 | +        row = dict(self.s, **d, entry={"request_id": "r1"})
 416 | +        self.assertIn("ruling 84", LP.attested(row)["rule"])
 417 | +        self.assertIn("ruling 84's class", LP.attested(row)["carried"])
 418 | +
 419 | +    def test_what_still_holds(self):
 420 | +        for spoken in ("So over time, I came to think or the money itself is broken.",    # two 1-for-1 function words
 421 | +                       "So over time, I came to think in a the money itself was broken.", # a 1-for-2 substitution
 422 | +                       "So over time, I came to believe so the money itself was broken.", # a content word
 423 | +                       "So over time, I came to think so the money itself was not broken.",   # a negation
 424 | +                       "So over time, I came to think so the money itself was broken 2."):    # a number
 425 | +            d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
 426 | +            self.assertEqual(d["verdict"], "hold", spoken)
 427 | +            self.assertIn("outside ruling 84's class", d["why"])
 428 | +        e = entry(self.s, "adopt_spoken", spoken_text="So over time, I came to think so the money itself was broken.")
 429 | +        e["approved_text"] = "So over time, um, I came to think so the money itself was broken."
 430 | +        s2 = dict(self.s, approved_text=e["approved_text"])               # a filler on the approved side alone
 431 | +        self.assertEqual(LP.decide(s2, e)["verdict"], "hold")
 432 | +
 433 | +
 434 |  class TestCheck(Dirs):
 435 |      def run_check(self, segs, appear=None, timeout=60.0):
 436 |          t = [0.0]
 437 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
 438 | index ffb9037..b7498ef 100644
 439 | --- a/tests/providers/test_providers.py
 440 | +++ b/tests/providers/test_providers.py
 441 | @@ -78,15 +78,40 @@ class Slow(Fake):
 442 |          return super().complete(prompt, max_tokens, seed, system)
 443 |  
 444 |  
 445 | +class SlowFail(Slow):
 446 | +    """A back-end that fails only after `delay` seconds (a call abandoned at its deadline that never answers)."""
 447 | +
 448 | +    def complete(self, prompt, max_tokens, seed, system=None):
 449 | +        import time as _t
 450 | +        _t.sleep(self.delay)
 451 | +        raise P.Unavailable("HTTP 504 after the deadline")
 452 | +
 453 | +
 454 | +def wait_for(path, kind, timeout=5.0):
 455 | +    """The deadline log's lines once one of `kind` is in it (an abandoned thread ends on its own clock)."""
 456 | +    import time as _t
 457 | +    t0 = _t.time()
 458 | +    while _t.time() - t0 < timeout:
 459 | +        if os.path.exists(path):
 460 | +            with open(path) as f:
 461 | +                log = [json.loads(x) for x in f]
 462 | +            if any(x["kind"] == kind for x in log):
 463 | +                return log
 464 | +        _t.sleep(0.05)
 465 | +    raise AssertionError(f"no {kind} line in {timeout} s")
 466 | +
 467 | +
 468 |  class TestDeadline(unittest.TestCase):
 469 |      """Orchestrator 22:40 ruling 5: one writer call never waits more than its deadline; it fails over to the next
 470 | -    back-end, the failover is recorded, and the abandoned call's upper bound is booked as spent."""
 471 | +    back-end, and the failover is recorded. RULING 83 (a) (20:33 Nov 13): the abandoned call is booked at its PROMPT
 472 | +    tokens at the listed input rate (not the upper bound of a full answer); a late answer's own figure replaces it."""
 473 |  
 474 |      def test_a_call_that_passes_its_deadline_fails_over_and_is_recorded(self):
 475 |          import tempfile
 476 |          import time as _t
 477 |          with tempfile.TemporaryDirectory() as d:
 478 | -            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=2.0, family="deepseek")
 479 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.8, family="deepseek",
 480 | +                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
 481 |              next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
 482 |              r = router(d, [slow, next_], {"angle_write": ["heimdall:deepseek", "heimdall:qwen"]},
 483 |                         spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0,
 484 | @@ -100,12 +125,128 @@ class TestDeadline(unittest.TestCase):
 485 |              self.assertLess(_t.time() - t0, 1.5)                       # never waited for the slow one
 486 |              self.assertEqual((rep.backend, rep.text), ("heimdall:qwen", '{"ok": 2}'))
 487 |              self.assertIn("no answer within 0 s", rep.tried[0][1])   # the failover is recorded on the reply
 488 | -            self.assertIn("abandoned at the deadline", rep.tried[0][1])
 489 | +            self.assertIn("abandoned at the deadline; booked at its prompt tokens", rep.tried[0][1])
 490 |              led = json.load(open(os.path.join(d, "SPEND.json")))
 491 | -            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)       # booked, at its upper bound
 492 | -            self.assertAlmostEqual(led["by_backend"]["heimdall:deepseek"]["usd_estimate"],
 493 | -                                   slow.upper_usd("p", 100), places=6)
 494 | +            booked = slow.prompt_usd("p")                              # ruling 83 (a): 201 tokens at $10 / 1M
 495 | +            self.assertAlmostEqual(booked, 201 * 10 / 1e6, places=9)
 496 | +            self.assertLess(booked, slow.upper_usd("p", 100) / 5)     # not the upper bound of a full answer
 497 | +            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)
 498 | +            self.assertAlmostEqual(led["by_backend"]["heimdall:deepseek"]["usd_estimate"], booked, places=6)
 499 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], booked + next_.usd({"in": 1000, "out": 100}),
 500 | +                                   places=6)                           # the answer that was used: no vendor figure
 501 | +            self.assertAlmostEqual(log[0]["booked_usd"], booked, places=9)
 502 |              self.assertEqual(led["reserved"], {})                      # no reservation left behind
 503 | +            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")   # then the vendor's figure arrives
 504 | +            late = [x for x in log if x["kind"] == "late_answer"]
 505 | +            self.assertEqual([(x["model"], x["usd_reported"], x["replaced"], x["booked_usd"]) for x in late],
 506 | +                             [("heimdall:deepseek", 0.0123, True, booked)])
 507 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
 508 | +            b = led["by_backend"]["heimdall:deepseek"]
 509 | +            self.assertEqual((b["calls"], b["in"], b["out"], b["reported_calls"], led["late_answers"]),
 510 | +                             (1, 1000, 100, 1, 1))                     # still one call, now with its own counts
 511 | +            self.assertAlmostEqual(b["usd_reported"], 0.0123, places=9)
 512 | +            self.assertAlmostEqual(b["usd_estimate"], slow.usd({"in": 1000, "out": 100}), places=6)
 513 | +            self.assertAlmostEqual(led["usd_reported"], 0.0123, places=9)        # the booking is replaced, not added
 514 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], next_.usd({"in": 1000, "out": 100}), places=6)
 515 | +            self.assertAlmostEqual(led["usd_estimate"], slow.usd({"in": 1000, "out": 100}) +
 516 | +                                   next_.usd({"in": 1000, "out": 100}), places=6)
 517 | +            self.assertEqual(led["reserved"], {})
 518 | +
 519 | +    def test_ruling_83_a_a_late_error_leaves_the_booking_and_a_late_answer_without_a_figure_is_its_estimate(self):
 520 | +        import tempfile
 521 | +        for cls, usage, kind in ((SlowFail, None, "late_error"), (Slow, {"in": 3000, "out": 500}, "late_answer")):
 522 | +            with tempfile.TemporaryDirectory() as d:
 523 | +                slow = cls("heimdall:glm", "heimdall", '{"ok": 1}', delay=0.5, family="glm", usage=usage)
 524 | +                next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
 525 | +                             usage={"in": 10, "out": 10, "usd_reported": 0.001})
 526 | +                path = os.path.join(d, "DEADLINES.jsonl")
 527 | +                r = router(d, [slow, next_], {"check": ["heimdall:glm", "heimdall:qwen"]},
 528 | +                           spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0, limit_basis="reported",
 529 | +                           deadline_log=path)
 530 | +                self.assertEqual(r.call("check", "pp", 100, 7, deadline_s=0.1).backend, "heimdall:qwen")
 531 | +                booked = slow.prompt_usd("pp")
 532 | +                self.assertAlmostEqual(r.spent(), booked + 0.001, places=6)   # the reported basis: booking + figure
 533 | +                log = wait_for(path, kind)
 534 | +                led = json.load(open(os.path.join(d, "SPEND.json")))
 535 | +                if kind == "late_error":                               # no answer: the booking stands
 536 | +                    self.assertIn("HTTP 504", [x for x in log if x["kind"] == kind][0]["error"])
 537 | +                    self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=6)
 538 | +                    self.assertNotIn("late_answers", led)
 539 | +                else:                                                  # an answer, no vendor figure: its estimate
 540 | +                    est = slow.usd(usage)
 541 | +                    self.assertAlmostEqual(led["usd_unreported_estimate"], est, places=6)
 542 | +                    self.assertAlmostEqual(r.spent(), est + 0.001, places=6)
 543 | +                    self.assertIsNone([x for x in log if x["kind"] == kind][0]["usd_reported"])
 544 | +
 545 | +    def test_ruling_83_a_an_unreadable_ledger_at_the_deadline_stops_the_call_and_the_miss_is_logged(self):
 546 | +        import tempfile
 547 | +        with tempfile.TemporaryDirectory() as d:
 548 | +            spend, path = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
 549 | +
 550 | +            class Corrupts(Slow):                                       # the ledger breaks while the call is out
 551 | +                def complete(self, prompt, max_tokens, seed, system=None):
 552 | +                    with open(spend, "w") as f:
 553 | +                        f.write("{ corrupt")
 554 | +                    return super().complete(prompt, max_tokens, seed, system)
 555 | +            slow = Corrupts("heimdall:glm", "heimdall", '{"ok": 1}', delay=0.4, family="glm")
 556 | +            next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
 557 | +            r = router(d, [slow, next_], {"check": ["heimdall:glm", "heimdall:qwen"]}, spend_path=spend,
 558 | +                       limit_usd=50.0, deadline_log=path)
 559 | +            with self.assertRaises(P.SpendLimit):                       # fail closed: no paid call on an unreadable
 560 | +                r.call("check", "pp", 100, 7, deadline_s=0.1)          # total, as before
 561 | +            self.assertEqual(next_.calls, 0)
 562 | +            with open(path) as f:                                       # the miss is on record all the same
 563 | +                self.assertEqual([json.loads(x)["kind"] for x in f], ["missed_deadline"])
 564 | +            import time as _t
 565 | +            _t.sleep(0.6)                                               # the abandoned thread ends: nothing to do
 566 | +            with open(path) as f:
 567 | +                self.assertEqual([json.loads(x)["kind"] for x in f], ["missed_deadline"])
 568 | +            self.assertEqual(open(spend).read(), "{ corrupt")          # never overwritten
 569 | +
 570 | +    def test_ruling_83_a_a_late_answer_that_cannot_be_booked_is_on_record_and_the_booking_stands(self):
 571 | +        import tempfile
 572 | +        with tempfile.TemporaryDirectory() as d:
 573 | +            spend, path = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
 574 | +            slow = Slow("heimdall:glm", "heimdall", '{"ok": 1}', delay=0.5, family="glm",
 575 | +                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
 576 | +            next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
 577 | +            r = router(d, [slow, next_], {"check": ["heimdall:glm", "heimdall:qwen"]}, spend_path=spend,
 578 | +                       limit_usd=50.0, deadline_log=path)
 579 | +            r.call("check", "pp", 100, 7, deadline_s=0.1)
 580 | +            with open(spend, "w") as f:                                  # the ledger breaks before the late answer
 581 | +                f.write("{ corrupt")
 582 | +            late = [x for x in wait_for(path, "late_answer") if x["kind"] == "late_answer"]
 583 | +            self.assertEqual((late[0]["replaced"], late[0]["usd_reported"]), (False, 0.0123))
 584 | +            self.assertIn("SpendLimit", late[0]["ledger_error"])
 585 | +            self.assertEqual(open(spend).read(), "{ corrupt")
 586 | +
 587 | +    def test_ruling_83_a_the_booking_always_comes_before_the_late_answer(self):
 588 | +        import threading
 589 | +        go, order = threading.Event(), []
 590 | +
 591 | +        def fn():                                                       # answers only once the test lets it
 592 | +            go.wait(5)
 593 | +            order.append("answered")
 594 | +            return "late"
 595 | +
 596 | +        def abandon():
 597 | +            order.append("booked")
 598 | +            go.set()                                                    # the answer races the booking
 599 | +            import time as _t
 600 | +            _t.sleep(0.3)
 601 | +            order.append("booked done")
 602 | +            return {"k": 1}
 603 | +        done = threading.Event()
 604 | +
 605 | +        def late(ab, value, error):
 606 | +            order.append(("late", ab, value, error))
 607 | +            done.set()
 608 | +        with self.assertRaises(P.DeadlineExceeded):
 609 | +            P._within(0.05, fn, on_abandon=abandon, on_late=late)
 610 | +        self.assertTrue(done.wait(5))
 611 | +        self.assertEqual(order, ["booked", "answered", "booked done", ("late", {"k": 1}, "late", None)])
 612 | +        self.assertEqual(P._within(1.0, lambda: 7, on_abandon=abandon, on_late=late), 7)   # in time: neither runs
 613 | +        self.assertEqual(len(order), 4)
 614 |  
 615 |      @staticmethod
 616 |      def lines(path):
 617 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins). Only state what
you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- providers.Router.call tries a role's chain of back-ends in order. Each paid call RESERVES its price-table upper
  bound on the spend ledger (a JSON file under an flock) before it runs, and settles after. Ruling 48: the cap is
  checked on the vendors' own reported dollars (usd_reported), plus an estimate for each call whose vendor reports
  none (usd_unreported_estimate). A call with deadline_s runs in a daemon thread (_within). At the deadline it is
  abandoned (Python cannot stop the thread), and the router moves on to the next back-end.
- BEFORE this change, an abandoned call was booked at its UPPER bound as an unreported estimate: every prompt
  character a token, plus the back-end's 16,000-token output floor at $15/1M. That is about $0.26 for a Heimdall call.
  On 20:12 Nov 13, 11 calls abandoned at 120 s booked $2.90 of a build's $2.99. Real answers were $0.09.
- The render's lock pre-check is the integrator's service (ruling 72). It compares the render's lock (its Whisper
  decode) with a second recogniser. Its outcome "adopt_spoken" hands over spoken_text, the second recogniser's text,
  to seal. This side (pipeline/lock_precheck.decide) adopts it only when its OWN check agrees that every difference
  (spoken_text against the approved text) is in the class. Otherwise it holds (fail closed). The integrator's verdict
  comes first: this side never sees adopt_spoken for a span the integrator held.
- pipeline/attest.carry_class is ruling 67's class (an immediate repetition, or all function words; never a number,
  a name or a negation). Ruling 67's re-seal tool (tests/package/reseal_attested.py) uses it too.

The orders:
- RULING 83 (orchestrator 20:33 Nov 13): "(a) A call abandoned at the deadline is booked at its PROMPT tokens at the
  model's listed input rate, not at the upper bound of a full answer; if the vendor later reports a cost for it, the
  reported figure replaces it. (b) The cap for this order becomes $20.00 vendor-reported, stop-and-tell at $16."
  "Outages must not be what spends the budget."
- RULING 84 (orchestrator 20:41 Nov 13): "(a) FILLERS the second recogniser hears and Whisper drops (um, uh, er, ah, mm,
  hmm) are in the adopt class with the speaker's own repetitions: the lock takes the spoken text, verdicts carry over,
  G18 compares against it. (b) ONE function-word disagreement between the two recognisers in a span (so / or, a / the,
  in / on) is the 'one ambiguous token' already ruled acceptable with acoustic identity (numbers, names, negations and
  content words always hold); the lock keeps the render decode's word and records the other reading. Two or more such
  disagreements in one span still hold."
- The integrator's class for ruling 84 (its message, 20:4x Nov 13), difference by difference:
  1. FILLERS = {um, uh, er, ah, mm, hmm} as canon tokens, dropped from the SECOND RECOGNISER's side only. A difference
     that is only fillers is "filler" and adopts. A filler on the lock side alone is not in the class.
  2. A number, negation or name on either side holds.
  3. One token against one token after fillers, both function words and different: "one function word". At most ONE
     per span; two or more hold.
  4. Any other substitution (both sides non-empty after fillers) holds, 2-for-2 and 1-for-2 included.
  5. A pure insert or drop: ruling 67's class unchanged, on the filler-free sequence.
  Its RULES string is "ruling 17 + ruling 72 + ruling 73 + ruling 84". Its spoken_text carries the second
  recogniser's reading of the one function word; the render's lock keeps the decode's word and records the other.
  Its decoder sha also changes. That value arrives only when the integrator's change is live. It is the ONE line of
  this change not in the diff: DECODER in pipeline/lock_precheck.py, a 12-hex constant naming the result files.

The change:
1. pipeline/providers.py:
   - Backend.prompt_tokens_upper (shared with upper_usd) and Backend.prompt_usd (input tokens only).
   - _within(seconds, fn, on_abandon, on_late). At the deadline, on_abandon runs under a lock BEFORE
     DeadlineExceeded is raised. The worker thread takes the same lock when it ends, so the booking always comes
     before on_late.
   - Router.call: abandon() books prompt_usd as an unreported estimate and releases the reservation.
   - Router._late: a late ANSWER is accounted as an on-time answer would have been, in place of the booking: the
     vendor's figure, or with none, the estimate from its own tokens. A late ERROR leaves the booking. One line goes
     to the deadline log either way. The late text is never used or recorded.
2. tests/package/proof_ly.py: LY_LIMIT_USD 12 -> 20, LY_STOP_USD 10 -> 16.
3. pipeline/attest.py: FILLERS and class_84 (new). carry_class is unchanged.
4. pipeline/lock_precheck.py:
   - RULES is the integrator's string;
   - decide() classifies with class_84;
   - attested()'s rule and carried texts name ruling 84.
5. Tests:
   - providers: the prompt-token booking, then the late vendor figure replacing it (no double count); a late error
     leaves the booking; a late answer without a figure books its estimate; the ordering of _within with a racing
     answer.
   - attest: class_84 case by case; carry_class unchanged.
   - lock_precheck: the 20:12 held span (um, uh, so/or) now adopts; two 1-for-1 function words, a 1-for-2, a content
     word, a negation, a number, and a filler on the approved side alone all hold; RULES is the integrator's string.

Design choices to check (each is a decision, say if you think it is wrong):
- A late answer WITHOUT a vendor figure is booked at the estimate from its own tokens (more than the prompt booking).
  The ruling names only the reported figure. This keeps a call that measurably used output tokens from being booked
  below them.
- The reservation is released at the deadline: the guard no longer holds the in-flight remainder of an abandoned
  call.
- Prompt tokens are counted one per character (+200): an abandoned call has no vendor token count.
- This side's class matches the integrator's exactly. The integrator also allowed a wider one ("every token a
  function word or a filler").

Check, against the diff:
- the ledger arithmetic of _late: no double count; usd_unreported_estimate ends exactly as if the call had answered on
  time; usd_reported moves only on a vendor figure;
- the ordering: the booking always precedes the late replacement; no deadlock; what happens when on_abandon raises
  (SpendLimit on an unreadable ledger) and when on_late raises;
- thread safety of ledger writes from the abandoned thread;
- class_84 against the integrator's five rules;
- that nothing the integrator held can be sealed on this side; the cap / stop change.

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
