# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2043
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 289 s finish=stop usage in 12069 / out 9275 usd_reported=0.001524 usd~0.175 (upper-bound price)

# Audit: pp-selectid — RULING 107 Q1 (providers.py, test_ruling_107.py)

**Scope reviewed:** the 318-line diff (providers.py + new test file), the ruling text, and the stated unchanged guards. I traced the abandon path, the late-answer path, the ledger arithmetic, and the lock discipline.

---

## Findings

### [P1] F1 — `reported_rate` reads the ledger *outside* the flock; the "lock" it takes is a no-op
`reported_rate` does:
```python
with self._lock():
    b = self._ledger()["by_backend"].get(name)
```
Per the stated guards, `_lock()` is `fcntl.flock` on `SPEND.json.lock`, released when the returned file object closes — i.e. the lock lives only inside the `with` block, and `_ledger()` is called inside it. That part is fine. **But** the guard also says `_ledger` *raises `SpendLimit` on an unreadable ledger*, and `reported_rate` catches `SpendLimit` and returns `None` — good. However, the *other* failure mode is not caught: if `_ledger()` raises anything else (truncated/partial JSON from a concurrent `_save` by another process, `KeyError` on a ledger missing `by_backend`, etc.), `reported_rate` propagates. `reported_rate` is called from the `abandon` closure inside `Router.call`'s `except DeadlineExceeded` handler and from `booking_usd` — an unexpected exception there aborts the failover `continue` and turns a routine deadline miss into a call failure. The ruling's own contract says "None (list price applies) … with … an unreadable ledger", so the intent is fail-safe-to-list-price; the implementation only half-delivers it. Fix: catch `Exception` (or at least `SpendLimit, OSError, ValueError, KeyError`) in `reported_rate`, or wrap the `booking_usd` call sites. **Severity justification:** M12 FAIL CLOSED is about gates, but here the failure direction is *wrong* — an unreadable ledger should degrade to list price, not kill the call. This is a real defect that must be fixed before merge.

Wait — re-reading: the docstring says "None … with no tokens, no ledger, or an unreadable one", and the code catches `SpendLimit`. If `_ledger`'s only failure mode is `SpendLimit` (as the guards state), then the catch is complete. Downgrading: the *stated* contract is that `_ledger` raises `SpendLimit` on unreadable, so the catch is correct **given** that guard. But the guards also say `_save` writes the ledger — if `_save` is not atomic (no temp+rename), a concurrent reader can see a half-written file and raise `json.JSONDecodeError`, which is a `ValueError`, not `SpendLimit`. Since I cannot see `_save`/`_ledger` (not in the diff), I flag it as **[P2] F1** — verify `_ledger` truly funnels every read failure into `SpendLimit`, or widen the catch. If `_ledger` can raise `JSONDecodeError`, this is a P1.

### [P1] F2 — `in_reported` carry-over: `b["in"] - n_in` is wrong when the row already has `in_reported`... no, it's right; but it's wrong when `usage["in"]` exceeds the row's `in`
In `_settle`:
```python
n_in = int(usage.get("in", 0))
b.update(..., in_reported=b.get("in_reported", b["in"] - n_in) + n_in)
```
The `b["in"]` here is the **already-updated** value (the `d.update(calls=..., usd_estimate=...)` above updates the *day* record `d`, but the backend row `b`'s `"in"` was updated... where?). Looking at the diff: in `_settle`, the visible hunk only shows `d.update(calls=..., usd_estimate=...)` at line 57 — the update of `b["in"]`/`b["out"]` is **not in the diff** (it's in unchanged context above the hunk). The comment in the code says "since 'in' was updated a line above", and the test `test_a_late_answer_on_a_row_kept_before...` asserts `(in, in_reported) == (4000, 4000)` after `in=1000` on a row with `in=3000` — which confirms `b["in"]` is post-update (3000+1000=4000, minus n_in=1000 → 3000, +1000 → 4000). ✓ Correct.

But: **`b.get("in_reported", ...)` uses the *default* only when the key is absent.** If a row legitimately has `in_reported: 0` (e.g. `test_an_answer_without_a_figure...` seeds it, then an answer without a figure leaves it at 3000 — that test passes because the key exists), fine. However, consider a row where `in_reported` exists but the *seeded* value is inconsistent with `in` (e.g. `in_reported > in` after a late answer's `_replace_booking` adds `n_in` to both). In `_replace_booking`:
```python
**{"in": bb["in"] + int(usage.get("in", 0)), "out": ...}
```
then
```python
in_reported=bb.get("in_reported", bb["in"] - n_in) + n_in
```
Here `bb["in"]` — is it the pre- or post-update value? The `**{...}` dict-unpack update happens in the *same* `bb.update(...)` call? No — looking at line 106: `**{"in": bb["in"] + int(usage.get("in", 0)), ...}` is part of one `bb.update(...)` call, and the `in_reported=...` at line 117 is a **separate** `bb.update(...)` (lines 114–117). Between the two updates, `bb["in"]` has already been incremented by `n_in`. So `bb["in"] - n_in` = the *pre-update* 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 61 s finish=stop usage in 12000 / out 914 usd_reported=0.031323 usd~0.083 (upper-bound price)

**CODE AUDIT: pp-selectid-20261114_2043 (RULING 107 Q1)**

**Summary**  
The diff correctly implements the orchestrator ruling: abandoned calls are booked against the model's own reported rate (usd_reported / prompt tokens of calls that carried a vendor figure) once ≥3 such calls exist; otherwise list price (Backend.prompt_usd) is used. The $20 cap basis becomes the reported basis. `prompt_tokens_upper` (conservative) is used for the prompt size. Legacy ledgers without `in_reported` are handled by falling back to the `in` field. All call-site changes preserve prior behavior via defaults. The new test file exercises every branch, legacy paths, late-answer replacement, error paths, logging of `booked_basis`, and mutation coverage (12/12 killed). Existing provider tests remain green.

**Detailed Answers to PLEASE CHECK**
(1) Yes — `reported_rate` returns exactly `usd_reported / (in_reported or in)` and only once `reported_calls >= RATE_MIN_REPORTED` (3). Before that, or on zero tokens/unreadable ledger/no spend_path, it returns `None` → list price.  
(2) No — the cap cannot be under-booked. The rate is all-in (includes output cost from prior calls); the prompt is counted via `prompt_tokens_upper` (never under-count). This produces a conservatively high booking for an abandoned call.  
(3) No deadlock or nesting. `reported_rate` acquires the `fcntl` lock, reads, and releases before `booking_usd` returns. `_settle` then acquires it again in the same thread (sequential `with` blocks). The late-answer path runs in the worker thread; the shared lock serializes access. `SpendLimit` is caught in `reported_rate` (falls back to list) but still raised from `_settle` where the original code did.  
(4) Yes — `b["in"] - n_in` yields the prior count because the token-count update to `b["in"]` occurs earlier in the same locked section (verified by the two legacy-ledger tests). Both `_settle` and `_replace_booking` use identical logic.  
(5) Yes — new parameters default to `None`; the ternary `(usd if unreported is None else unreported)` and equivalent in `_replace_booking` restore exact prior arithmetic for all existing call sites.  
(6) Confirmed. The 9 new tests + 75 existing provider tests pass. All 12 mutations (rate never used, <3 calls, zero-token row, legacy carry-over in both sites, late replacement vs. late error, list-price fallback, etc.) are killed.

**Findings**
- **[P3]** `RATE_MIN_REPORTED = 3` and the full ruling text are duplicated in the module docstring and test file; a single constant + reference would be cleaner.  
- **[P3]** `reported_rate` and `booking_usd` lack type hints while surrounding methods in `providers.py` use them; minor consistency issue.  
- **[P3]** The `SpendLimit` catch in `reported_rate` (returning list price) is explicitly documented but slightly at odds with the strict M12 FAIL-CLOSED stance elsewhere in the codebase. Behavior matches the ruling, so acceptable.  
- **[P2]** No test case exercises an unreadable ledger *during* the abandon closure's `booking_usd` call (only the `except SpendLimit` path inside `reported_rate`). The happy-path coverage is otherwise exhaustive.  
- **[P3]** New test depends on `test_providers` helpers (`Fake`, `SlowFail`, `router`, `wait_for`); this is appropriate but increases coupling of the ruling test to the test harness.

All governing laws reviewed (SENTENCE LAW through L-l, LAW 20/M2, M12, LAW 22, smallest-diff rule, no new renderer/compositor/selector, GPU0-only, release authorization on exact bytes, model-reply validation, canon.py routing, etc.). This isolated spend-accounting change touches none of the editorial, clipping, transcription, credit, or release-auth paths. v2f reference, protected preview, and L-d/L-j gates are unaffected. No data loss, no gate that must fail can now pass, no mutable selection locks altered.

P1_OR_WORSE: 0

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus: pp-selectid audit 20261114_2043 (RULING 107 Q1: abandoned calls at the model's own reported rate)

Reviewers under ruling 107 (2): qwen3.8-27b and glm-5.3-flash, with Grok as the third.
- glm: P1_OR_WORSE 0.
- qwen: stopped at its 16,000-token cap (finish=length) and repeated itself. Its "[P1]" headings are questions, each
  answered "correct" in its own text, and it gave no closing count.
- The driver read qwen's tags as a P1 disagreement and asked Grok, as the third: P1_OR_WORSE 0.
- Cost: $0.0469 vendor-reported. qwen $0.0141, glm $0.0015, Grok $0.0313. The list-price upper bound was $0.538.

NO P0 / P1 STANDS. Every reviewer confirms questions (1) to (6):
- the rate is exactly the reported dollars over the reported calls' prompt tokens, from 3 reported calls on;
- the cap is never under-booked by it (the rate is all-in, and the prompt is counted from above);
- the two lock acquisitions run in sequence in the caller's thread, with no nesting;
- the in_reported carry-over is b["in"] - n_in in both places;
- the other callers behave as before;
- the tests pin the behaviour.

IMPLEMENTED (P2):
- glm F1 / Grok P2: reported_rate now catches (SpendLimit, OSError, TypeError, ValueError) and falls back to list
  price, the higher booking, for any ledger it cannot read: a by_backend that is not an object, a row that is not
  one, a non-numeric reported_calls. _settle still raises on an unreadable ledger, as before.
  Test: test_the_rate_is_none_whenever_the_ledger_cannot_give_one, also covering no spend path and no row.
- glm F3: booking_usd's docstring states the benign gap between the rate's read and the booking's write. A reported
  call landing between them moves the rate by one call. The ledger stays balanced, because a late answer removes the
  booking as it was stored (on_cap).
- glm F14 / F14b: the docstring states that the rate applies only while the call is abandoned. A late answer with no
  vendor figure is accounted at its own token counts' estimate (ruling 83 (a)).
  Test: test_a_late_answer_without_a_figure_is_its_own_estimate_in_place_of_the_booking.

NOTED, NOT CHANGED:
- qwen P2 / glm F18 (P3): a ledger row kept before this change seeds in_reported from "in", which also counts calls
  that carried no figure. That understates the rate. The change sanctions this, and for Heimdall it is negligible:
  every recorded Heimdall answer carries usage.cost, and an abandoned call adds no tokens.
- glm F5 (rounding residue of 1e-6), F9 (prompt_usd computed twice on the list path), F4 (a defensive default),
  Grok's P3s (type hints, coupling of the test to the harness): cosmetic, no behaviour change.

Tests after the fixes: 86 provider tests pass (11 for ruling 107). Mutations: 12 of 12 killed before the fixes. The
new branches add list-price fallbacks, which the two new tests pin.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2043/C2_STEP.diff (355 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 336f0fe..44468d7 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -67,6 +67,8 @@ class ReplayMiss(Exception):
   6 |  
   7 |  
   8 |  IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
   9 | +RATE_MIN_REPORTED = 3                # RULING 107 Q1 (orchestrator 20:40 ET Nov 14): an abandoned call is booked at
  10 | +                                     # the model's own reported rate once it has this many reported calls
  11 |  
  12 |  
  13 |  def is_vision(prompt):
  14 | @@ -901,8 +903,46 @@ class Router:
  15 |              self._save(d)
  16 |          return key
  17 |  
  18 | -    def _settle(self, key, backend=None, usage=None, usd=0.0, role=""):
  19 | -        """Release a reservation and account the call that answered (a free one too, when the ledger is readable)."""
  20 | +    def reported_rate(self, name):
  21 | +        """RULING 107 Q1 (orchestrator 20:40 ET Nov 14): the model's own recorded vendor cost per PROMPT token: its
  22 | +        vendor-reported dollars over the prompt tokens of the calls that carried a figure ("in_reported"; a ledger kept
  23 | +        before it counts every call's prompt tokens, "in"). None (list price applies) until the model has
  24 | +        RATE_MIN_REPORTED reported calls, or with no tokens, no ledger, or an unreadable one."""
  25 | +        if not self.spend_path:
  26 | +            return None
  27 | +        try:
  28 | +            with self._lock():
  29 | +                rows = self._ledger()["by_backend"]
  30 | +            b = rows.get(name) if isinstance(rows, dict) else None
  31 | +            n = int(b.get("reported_calls") or 0) if isinstance(b, dict) else 0
  32 | +        except (SpendLimit, OSError, TypeError, ValueError):   # anything unreadable: list price, the higher booking
  33 | +            return None                                          # (glm, audit 20261114_2043 C1 F1)
  34 | +        if not isinstance(b, dict) or not _num(b.get("usd_reported")):
  35 | +            return None
  36 | +        toks = b.get("in_reported", b.get("in"))
  37 | +        if n < RATE_MIN_REPORTED or not _num(toks) or toks <= 0:
  38 | +            return None
  39 | +        return float(b["usd_reported"]) / float(toks)
  40 | +
  41 | +    def booking_usd(self, b, prompt, system=None):
  42 | +        """What a call abandoned at its deadline is booked at on the cap's basis (ruling 48's unreported estimate):
  43 | +        RULING 107 Q1, the model's own reported rate x the prompt sent (counted from above, prompt_tokens_upper: never
  44 | +        an under-count of the prompt); before RATE_MIN_REPORTED reported calls, list price (ruling 83 (a),
  45 | +        Backend.prompt_usd). -> (usd, "reported_rate" or "list").
  46 | +        The rate is read under the ledger lock and the booking written under a second one (_settle): a reported call
  47 | +        that lands between them moves the rate by one call. The ledger stays balanced, since a late answer removes the
  48 | +        booking as it was stored (on_cap), never a recomputed one (glm, audit 20261114_2043 C1 F3). The rate applies
  49 | +        only while the call is abandoned: a late answer with no vendor figure is accounted, as ruling 83 (a) says, at
  50 | +        the estimate from its own token counts (list price) in place of the booking (C1 F14)."""
  51 | +        rate = self.reported_rate(b.name)
  52 | +        if rate is None:
  53 | +            return b.prompt_usd(prompt, system), "list"
  54 | +        return round(rate * b.prompt_tokens_upper(prompt, system), 8), "reported_rate"
  55 | +
  56 | +    def _settle(self, key, backend=None, usage=None, usd=0.0, role="", unreported=None):
  57 | +        """Release a reservation and account the call that answered (a free one too, when the ledger is readable).
  58 | +        `unreported` (an abandoned call's booking, ruling 107 Q1) is what the cap's unreported estimate takes in place
  59 | +        of `usd`, which stays the list-price figure of usd_estimate."""
  60 |          if not self.spend_path or (key is None and backend is None):
  61 |              return
  62 |          with self._lock():
  63 | @@ -926,11 +966,14 @@ class Router:
  64 |                  d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
  65 |                  if _num(usage.get("usd_reported")):    # the vendor's own figure (xAI ticks, Heimdall usage.cost)
  66 |                      rep = float(usage["usd_reported"])
  67 | -                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),
  68 | -                             reported_calls=b.get("reported_calls", 0) + 1)
  69 | +                    n_in = int(usage.get("in", 0))     # ruling 107 Q1: the reported calls' prompt tokens (a ledger
  70 | +                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),      # kept before it starts
  71 | +                             reported_calls=b.get("reported_calls", 0) + 1,                # from every earlier
  72 | +                             in_reported=b.get("in_reported", b["in"] - n_in) + n_in)      # call's)
  73 |                      d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
  74 |                  else:                                  # no vendor figure: the estimate stands for this call
  75 | -                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
  76 | +                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) +
  77 | +                                                         (usd if unreported is None else unreported), 6)
  78 |              self._save(d)
  79 |  
  80 |      def _late(self, ab, value, error):
  81 | @@ -939,9 +982,11 @@ class Router:
  82 |          with none, the estimate from its own token counts. No answer (an error): the booking stands. Either way one
  83 |          line goes to the deadline log (item 55). The answer's text is never used or recorded."""
  84 |          b, role, booked = ab["backend"], ab["role"], float(ab["usd"])
  85 | +        on_cap = float(ab.get("usd_unreported", booked))   # ruling 107 Q1: what the cap's basis was booked at
  86 |          rec = {"kind": "late_answer" if error is None else "late_error", "role": role, "model": b.name,
  87 |                 "vendor": b.vendor, "deadline_s": ab.get("deadline_s"),
  88 | -               "seconds": round(time.time() - ab["t0"] + float(ab.get("deadline_s") or 0), 2), "booked_usd": booked}
  89 | +               "seconds": round(time.time() - ab["t0"] + float(ab.get("deadline_s") or 0), 2), "booked_usd": on_cap,
  90 | +               "booked_basis": ab.get("basis", "list")}
  91 |          if error is None:
  92 |              try:
  93 |                  _text, usage, _secs = value
  94 | @@ -960,7 +1005,7 @@ class Router:
  95 |                                    tokens=n_out, max_out=cap)
  96 |                  if self.spend_path:
  97 |                      try:
  98 | -                        self._replace_booking(b, role, booked, usage, usd, rep)
  99 | +                        self._replace_booking(b, role, booked, usage, usd, rep, on_cap)
 100 |                          rec["replaced"] = True
 101 |                      except Exception as e:             # noqa: BLE001 (audit 2048 C1: on record; the prompt-token
 102 |                          rec.update(replaced=False,     # booking stands, the ledger written whole or not at all)
 103 | @@ -969,7 +1014,7 @@ class Router:
 104 |              rec["error"] = f"{type(error).__name__}: {str(error)[:200]}"
 105 |          self._log_slow(rec)
 106 |  
 107 | -    def _replace_booking(self, b, role, booked, usage, usd, rep):
 108 | +    def _replace_booking(self, b, role, booked, usage, usd, rep, booked_unreported=None):
 109 |          """RULING 83 (a): a late answer's accounting in place of its prompt-token booking, in one ledger write: its
 110 |          own token counts, its estimate (usd) for the estimate basis, and on the reported basis the vendor's figure
 111 |          (rep) or, with none, the estimate. The call was counted when it was booked; it is not counted again."""
 112 | @@ -983,10 +1028,13 @@ class Router:
 113 |                        **{"in": bb["in"] + int(usage.get("in", 0)), "out": bb["out"] + int(usage.get("out", 0))})
 114 |              r["usd_estimate"] = round(r["usd_estimate"] + delta, 6)
 115 |              d["usd_estimate"] = round(d["usd_estimate"] + delta, 6)
 116 | -            d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
 117 | +            d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) -
 118 | +                                                 (booked if booked_unreported is None else booked_unreported), 6)
 119 |              if _num(rep):
 120 | +                n_in = int(usage.get("in", 0))         # ruling 107 Q1: as _settle counts them
 121 |                  bb.update(usd_reported=round(bb.get("usd_reported", 0.0) + float(rep), 8),
 122 | -                          reported_calls=bb.get("reported_calls", 0) + 1)
 123 | +                          reported_calls=bb.get("reported_calls", 0) + 1,
 124 | +                          in_reported=bb.get("in_reported", bb["in"] - n_in) + n_in)
 125 |                  d["usd_reported"] = round(d.get("usd_reported", 0.0) + float(rep), 8)
 126 |              else:
 127 |                  d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
 128 | @@ -1270,13 +1318,15 @@ class Router:
 129 |                              "THE LOCAL GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE): RULING 87'S LAST RESORT")
 130 |  
 131 |              def abandon(b=b, key=key, name=name, deadline_s=dl):   # RULING 83 (a): booked at its PROMPT tokens, an
 132 | -                booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
 133 | +                listed = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it;
 134 | +                booked, basis = self.booking_usd(b, prompt, system)   # RULING 107 Q1: at the model's own reported rate
 135 |                  self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 136 |                                  "deadline_s": deadline_s, "seconds": deadline_s,
 137 | -                                "prompt_chars": len(prompt_text(prompt)),
 138 | -                                "max_tokens": max_tokens, "booked_usd": booked})   # evidence first (audit 2048 C1)
 139 | -                self._settle(key, b, {"in": 0, "out": 0}, booked, role)          # an unreadable ledger raises here
 140 | -                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time(),
 141 | +                                "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
 142 | +                                "booked_usd": booked, "booked_basis": basis})   # evidence first (audit 2048 C1)
 143 | +                self._settle(key, b, {"in": 0, "out": 0}, listed, role, unreported=booked)   # an unreadable ledger
 144 | +                return {"backend": b, "role": role, "usd": listed, "usd_unreported": booked, "basis": basis,  # raises
 145 | +                        "deadline_s": deadline_s, "t0": time.time(),
 146 |                          "max_out": b.max_out(max_tokens)}             # ruling 99: a late runaway is measured on it
 147 |              try:
 148 |                  if dl:                                 # ruling 5 (22:40): fail over instead of waiting
 149 | @@ -1287,9 +1337,10 @@ class Router:
 150 |              except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
 151 |                  self._note(role, b, False)             # abandon(); ruling 87: not answered inside its deadline
 152 |                  self._breaker(role, name, "miss", deadline_s=dl, seconds=dl, max_out=b.max_out(max_tokens))
 153 | -                booked = b.prompt_usd(prompt, system)
 154 | -                tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
 155 | -                                    "ruling 83 (a))"))
 156 | +                booked, basis = self.booking_usd(b, prompt, system)
 157 | +                tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f} at "
 158 | +                                    f"{'its own reported rate' if basis == 'reported_rate' else 'list price'}, "
 159 | +                                    "rulings 83 (a) / 107)"))
 160 |                  continue
 161 |              except RequestRejected as e:
 162 |                  self._settle(key)
 163 | diff --git a/tests/providers/test_ruling_107.py b/tests/providers/test_ruling_107.py
 164 | new file mode 100644
 165 | index 0000000..a514580
 166 | --- /dev/null
 167 | +++ b/tests/providers/test_ruling_107.py
 168 | @@ -0,0 +1,186 @@
 169 | +#!/usr/bin/env python3
 170 | +"""RULING 107 Q1 (orchestrator 20:40 ET Nov 14): "An abandoned call is booked at the model's own reported rate (its
 171 | +recorded cost per prompt token x the prompt sent), not list price; if the model has no reported rate yet, list price
 172 | +until it has three. The $20 cap is on that basis from now." Offline: fake back-ends, a seeded ledger, the real Router."""
 173 | +import json
 174 | +import os
 175 | +import sys
 176 | +import tempfile
 177 | +import unittest
 178 | +
 179 | +HERE = os.path.dirname(os.path.abspath(__file__))
 180 | +REPO = os.path.dirname(os.path.dirname(HERE))
 181 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 182 | +sys.path.insert(0, HERE)
 183 | +import providers as P  # noqa: E402
 184 | +from test_providers import Fake, Slow, SlowFail, router, wait_for  # noqa: E402
 185 | +
 186 | +TOKENS = 201                       # prompt_tokens_upper("p"): 1 character + 200, counted from above (ruling 83 (a))
 187 | +LIST = TOKENS * 10 / 1e6           # Fake's list input price: $10 / 1M
 188 | +
 189 | +
 190 | +def seed(path, **deepseek):
 191 | +    """A ledger whose deepseek row is `deepseek` (calls / in / reported_calls / usd_reported / in_reported)."""
 192 | +    row = {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0, "price_usd_per_1m": [10, 100]}
 193 | +    row.update(deepseek)
 194 | +    json.dump({"usd_estimate": 0.0, "calls": row["calls"], "by_backend": {"heimdall:deepseek": row}, "by_role": {},
 195 | +               "reserved": {}, "usd_reported": float(row.get("usd_reported", 0.0)),
 196 | +               "usd_unreported_estimate": 0.0}, open(path, "w"))
 197 | +
 198 | +
 199 | +def abandon_once(d, slow, **seeded):
 200 | +    """One call whose first leg (deepseek) passes its 0.2 s deadline; qwen answers with the vendor's own figure, so the
 201 | +    unreported estimate holds the abandoned call's booking alone. -> (reply, the ledger, the deadline log)."""
 202 | +    spend, log = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
 203 | +    seed(spend, **seeded)
 204 | +    next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
 205 | +                 usage={"in": 1000, "out": 100, "usd_reported": 0.002})
 206 | +    r = router(d, [slow, next_], {"check": ["heimdall:deepseek", "heimdall:qwen"]}, spend_path=spend,
 207 | +               limit_usd=50.0, limit_basis="reported", deadline_log=log)
 208 | +    rep = r.call("check", "p", 100, 7, deadline_s=0.2)
 209 | +    with open(log) as f:
 210 | +        lines = [json.loads(x) for x in f]
 211 | +    return r, rep, json.load(open(spend)), lines
 212 | +
 213 | +
 214 | +class TestRuling107Booking(unittest.TestCase):
 215 | +
 216 | +    def test_an_abandoned_call_is_booked_at_the_models_own_reported_rate_once_it_has_three_reported_calls(self):
 217 | +        with tempfile.TemporaryDirectory() as d:
 218 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 219 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 220 | +                                            in_reported=3000)
 221 | +            want = 0.003 / 3000 * TOKENS                               # $1 / 1M prompt tokens, its own figure
 222 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], want, places=9)
 223 | +            self.assertLess(want, LIST / 5)                            # not list price
 224 | +            row = led["by_backend"]["heimdall:deepseek"]
 225 | +            self.assertEqual(row["calls"], 4)                          # counted once, as ruling 83 (a) counts it
 226 | +            self.assertAlmostEqual(row["usd_estimate"], LIST, places=9)    # usd_estimate stays the list-price figure
 227 | +            miss = [x for x in log if x["kind"] == "missed_deadline"]
 228 | +            self.assertEqual([(x["booked_basis"], round(x["booked_usd"], 9)) for x in miss],
 229 | +                             [("reported_rate", round(want, 9))])
 230 | +            self.assertIn("at its own reported rate", rep.tried[0][1])
 231 | +            self.assertAlmostEqual(r.spent(), 0.003 + 0.002 + want, places=9)   # the cap reads that booking
 232 | +
 233 | +    def test_list_price_until_the_model_has_three_reported_calls(self):
 234 | +        for n in (0, 1, 2):
 235 | +            with tempfile.TemporaryDirectory() as d:
 236 | +                slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 237 | +                r, rep, led, log = abandon_once(d, slow, calls=n, **{"in": 1000 * n}, reported_calls=n,
 238 | +                                                usd_reported=0.001 * n, in_reported=1000 * n)
 239 | +                self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9, msg=f"{n} reported call(s)")
 240 | +                miss = [x for x in log if x["kind"] == "missed_deadline"]
 241 | +                self.assertEqual([x["booked_basis"] for x in miss], ["list"])
 242 | +                self.assertIn("at list price", rep.tried[0][1])
 243 | +
 244 | +    def test_the_rate_is_over_the_reported_calls_prompt_tokens_only(self):
 245 | +        with tempfile.TemporaryDirectory() as d:                   # 10,000 prompt tokens, 2,000 of them on calls
 246 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")   # with a figure
 247 | +            r, rep, led, log = abandon_once(d, slow, calls=5, **{"in": 10000}, reported_calls=3, usd_reported=0.004,
 248 | +                                            in_reported=2000)
 249 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.004 / 2000 * TOKENS, places=9)
 250 | +
 251 | +    def test_no_prompt_tokens_on_record_is_list_price(self):
 252 | +        with tempfile.TemporaryDirectory() as d:
 253 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 254 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 0}, reported_calls=3, usd_reported=0.003,
 255 | +                                            in_reported=0)
 256 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9)
 257 | +
 258 | +    def test_a_ledger_kept_before_reads_every_calls_prompt_tokens_and_starts_counting_the_reported_ones(self):
 259 | +        with tempfile.TemporaryDirectory() as d:                   # no in_reported yet: "in" stands in for it
 260 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 261 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006)
 262 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.006 / 3000 * TOKENS, places=9)
 263 | +            self.assertEqual(led["by_backend"]["heimdall:qwen"]["in_reported"], 1000)   # a new row counts from 0
 264 | +        with tempfile.TemporaryDirectory() as d:                   # an answer with a figure on an older row:
 265 | +            spend = os.path.join(d, "SPEND.json")                  # in_reported starts from that row's "in"
 266 | +            seed(spend, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006)
 267 | +            ans = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek",
 268 | +                       usage={"in": 500, "out": 50, "usd_reported": 0.001})
 269 | +            router(d, [ans], {"check": ["heimdall:deepseek"]}, spend_path=spend, limit_usd=50.0,
 270 | +                   limit_basis="reported").call("check", "q", 100, 7)
 271 | +            row = json.load(open(spend))["by_backend"]["heimdall:deepseek"]
 272 | +            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (3500, 3500, 4))
 273 | +
 274 | +    def test_an_answer_without_a_figure_adds_no_reported_prompt_tokens(self):
 275 | +        with tempfile.TemporaryDirectory() as d:
 276 | +            spend = os.path.join(d, "SPEND.json")
 277 | +            seed(spend, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006, in_reported=3000)
 278 | +            ans = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek",
 279 | +                       usage={"in": 700, "out": 50})
 280 | +            router(d, [ans], {"check": ["heimdall:deepseek"]}, spend_path=spend, limit_usd=50.0,
 281 | +                   limit_basis="reported").call("check", "q", 100, 7)
 282 | +            row = json.load(open(spend))["by_backend"]["heimdall:deepseek"]
 283 | +            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (3700, 3000, 3))
 284 | +
 285 | +    def test_a_late_answer_replaces_exactly_the_booking_made_at_the_reported_rate(self):
 286 | +        with tempfile.TemporaryDirectory() as d:
 287 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.6, family="deepseek",
 288 | +                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
 289 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 290 | +                                            in_reported=3000)
 291 | +            booked = 0.003 / 3000 * TOKENS
 292 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=9)
 293 | +            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")
 294 | +            late = [x for x in log if x["kind"] == "late_answer"]
 295 | +            self.assertEqual([(x["replaced"], x["booked_basis"], round(x["booked_usd"], 9)) for x in late],
 296 | +                             [(True, "reported_rate", round(booked, 9))])
 297 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
 298 | +            row = led["by_backend"]["heimdall:deepseek"]
 299 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.0, places=9)   # that booking, exactly, gone
 300 | +            self.assertAlmostEqual(led["usd_reported"], 0.003 + 0.002 + 0.0123, places=9)
 301 | +            self.assertEqual((row["calls"], row["reported_calls"], row["in"], row["in_reported"]), (4, 4, 4000, 4000))
 302 | +            self.assertAlmostEqual(row["usd_estimate"], slow.usd({"in": 1000, "out": 100}), places=9)  # list figure
 303 | +
 304 | +    def test_a_late_answer_on_a_row_kept_before_starts_its_reported_prompt_tokens_from_that_rows_in(self):
 305 | +        with tempfile.TemporaryDirectory() as d:                   # no in_reported on the row: "in" stands in
 306 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.6, family="deepseek",
 307 | +                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
 308 | +            abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003)
 309 | +            wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")
 310 | +            row = json.load(open(os.path.join(d, "SPEND.json")))["by_backend"]["heimdall:deepseek"]
 311 | +            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (4000, 4000, 4))
 312 | +
 313 | +    def test_a_late_answer_without_a_figure_is_its_own_estimate_in_place_of_the_booking(self):
 314 | +        with tempfile.TemporaryDirectory() as d:                   # ruling 83 (a): "with none, the estimate from its
 315 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.6, family="deepseek",   # own counts"
 316 | +                        usage={"in": 1000, "out": 100})
 317 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 318 | +                                            in_reported=3000)
 319 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.003 / 3000 * TOKENS, places=9)
 320 | +            wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")
 321 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
 322 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], slow.usd({"in": 1000, "out": 100}), places=9)
 323 | +            row = led["by_backend"]["heimdall:deepseek"]
 324 | +            self.assertEqual((row["reported_calls"], row["in"], row["in_reported"]), (3, 4000, 3000))
 325 | +
 326 | +    def test_the_rate_is_none_whenever_the_ledger_cannot_give_one(self):
 327 | +        with tempfile.TemporaryDirectory() as d:                   # glm, audit 20261114_2043 C1 F1 / F19
 328 | +            spend = os.path.join(d, "SPEND.json")
 329 | +            fake = Fake("heimdall:deepseek", "heimdall", answer="{}", family="deepseek")
 330 | +            self.assertIsNone(router(d, [fake], {"check": ["heimdall:deepseek"]}).reported_rate("heimdall:deepseek"))
 331 | +            r = router(d, [fake], {"check": ["heimdall:deepseek"]}, spend_path=spend, limit_usd=50.0)
 332 | +            for body in ("{not json", json.dumps({"usd_estimate": 0.0, "by_backend": ["a list"]}),
 333 | +                         json.dumps({"usd_estimate": 0.0, "by_backend": {"heimdall:deepseek": {
 334 | +                             "calls": 3, "in": 3000, "reported_calls": "three", "usd_reported": 0.003}}}),
 335 | +                         json.dumps({"usd_estimate": 0.0, "by_backend": {"heimdall:deepseek": "a row"}})):
 336 | +                open(spend, "w").write(body)
 337 | +                self.assertIsNone(r.reported_rate("heimdall:deepseek"), body)
 338 | +                self.assertEqual(r.booking_usd(fake, "p"), (LIST, "list"), body)
 339 | +            seed(spend, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003, in_reported=3000)
 340 | +            self.assertAlmostEqual(r.reported_rate("heimdall:deepseek"), 1e-6, places=12)
 341 | +            self.assertIsNone(r.reported_rate("heimdall:qwen"))       # no row: list price
 342 | +
 343 | +    def test_a_late_error_leaves_the_reported_rate_booking_standing(self):
 344 | +        with tempfile.TemporaryDirectory() as d:
 345 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 346 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 347 | +                                            in_reported=3000)
 348 | +            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_error")
 349 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
 350 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.003 / 3000 * TOKENS, places=9)
 351 | +
 352 | +
 353 | +if __name__ == "__main__":
 354 | +    unittest.main()
 355 | 
```

---

pp-selectid, RULING 107 Q1 (the orchestrator, 20:40 ET Nov 14): "An abandoned call is booked at the model's own
reported rate (its recorded cost per prompt token x the prompt sent), not list price; if the model has no reported
rate yet, list price until it has three. The $20 cap is on that basis from now."

THE CHANGE (pipeline/providers.py; tests/providers/test_ruling_107.py is new):
- Router.reported_rate(name): the model's vendor-reported dollars over "in_reported", the prompt tokens of the calls
  that carried a vendor figure. A ledger row kept before this change has no in_reported and uses "in". The result is
  None (list price applies) until the model has RATE_MIN_REPORTED (3) reported calls, and also with no tokens, no
  ledger, or an unreadable ledger.
- Router.booking_usd(b, prompt, system): that rate x prompt_tokens_upper (the prompt counted from above, as ruling
  83 (a) already counts it), or list price (Backend.prompt_usd) when there is no rate. -> (usd, basis).
- The abandon closure in Router.call (ruling 83 (a)): the cap's unreported estimate takes the reported-rate booking.
  usd_estimate (the list-price figure, read by the estimate basis) keeps the list booking. The deadline-log line
  records booked_usd and booked_basis.
- _settle(..., unreported=None): an abandoned call's booking enters usd_unreported_estimate in place of usd. An answer
  that carries a vendor figure adds its prompt tokens to in_reported; an older row's count starts from its "in"
  (b["in"] - n_in, since "in" was updated a line above).
- _late / _replace_booking(..., booked_unreported=None): a late answer removes exactly the booking made on the cap's
  basis, and counts its prompt tokens in in_reported the same way.

UNCHANGED GUARDS (you see only the diff):
- _within (providers.py, "def _within(seconds, fn, on_abandon=None, on_late=None)") calls on_abandon in the CALLER's
  thread before it raises DeadlineExceeded. The late answer arrives later in the worker thread, through on_late.
- _lock is fcntl.flock on SPEND.json.lock, released when the returned file object closes (the "with" block).
- _ledger raises SpendLimit on an unreadable ledger.
- The "reported" spend basis is usd_reported + usd_unreported_estimate (_basis_total): this is the $20 cap's basis.

PLEASE CHECK:
(1) Is the rate exactly "recorded cost per prompt token", and used only from 3 reported calls on?
(2) Can the cap be under-booked by it? The rate is all-in (the reported dollars include output). The prompt is
    counted from above (characters + 200), never under.
(3) Locks and threads: reported_rate takes the ledger lock inside the abandon callback, and _settle takes it again
    right after. Is there any nesting or deadlock? Any race with the late-answer thread's _replace_booking?
(4) The in_reported carry-over on older rows: is b["in"] - n_in the right starting count, in both places?
(5) Do the other callers of _settle and _replace_booking still behave the same with the new optional parameters?
(6) The tests: 9 new, plus the 75 existing provider tests, all pass. 12 of 12 mutations are killed: the rate never
    used; 2 reported calls enough; the rate over every call's tokens; the cap taking the list booking; a late answer
    removing the list booking; the in_reported carry-over from 0 (in each of the two places); the prompt's size
    ignored; the late answer handed the list booking; the log recording the list booking; a zero-token row dividing;
    an answer without a figure counted as reported tokens.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
