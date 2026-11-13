# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0831
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 60 s finish=stop usage in 7707 / out 1644 usd~0.048 (upper-bound price)

# Audit: item 55 deadline evidence log (C1_STEP.diff)

## Verified from the diff

**Fields the order names.** The order asks for (model, prompt size, seconds). `missed_deadline` (providers.py:50-52) writes `model`, `prompt_chars`, `seconds` (== `deadline_s`, correct: the call is abandoned *at* the deadline), plus `role`, `vendor`, `deadline_s`, `max_tokens`. `answered_slowly` (providers.py:60-64) adds `threshold_s` and token counts. Both kinds carry everything the order names. ✔

**Exactly once.** Each log point sits on a mutually exclusive path: `missed_deadline` inside the `DeadlineExceeded` handler before `continue`; `answered_slowly` after a successful `_settle`, before the empty-reply check. No loop, no retry of the log call itself. ✔

**Cannot change the call's outcome or the ledger.** `_log_slow` (providers.py:28-41) runs after `_settle`/`tried.append` on the success path and after the settle+append on the deadline path; it returns early when `deadline_log` is falsy; the only caught exception is `OSError`, which becomes a notice. It never touches the ledger, `tried`, or the return value. One caveat below (P2-1) on the notice path. ✔ (with caveat)

**Concurrency.** The append is inside `self._log_lock` (providers.py:36-39), and each line is a single `f.write(line + "\n")` — one write call, so even without the lock, POSIX appends of <PIPE_BUF are effectively line-atomic; with the lock, interleaving within one Router instance is excluded. ✔ (caveat: see P2-2)

**Nothing secret.** Both records contain only: kind, role, model, vendor, deadline_s/threshold_s, seconds, prompt_chars, max_tokens, in, out, utc. No prompt text, no keys. ✔

**Tests.** The existing deadline test now asserts the missed line's kind/model/prompt_chars/max_tokens/deadline_s (test:115-117); the new test covers slow-logged (with tokens), fast-not-logged, and no-log-writes-nothing (test:125-145). ✔

## Findings

**P1-1 — `answered_slowly` is silently skipped when the reply is empty.** providers.py:60-65: the slow-answer log sits *before* the `if not (isinstance(text, str) and text.strip())` check, so that ordering is fine — but note the slow log fires even for an *empty* reply that the chain then moves on from. Conversely, if a back-end answers slowly *and* the reply is empty, you get the slow line but the "refused this request: an empty reply" outcome only in `tried`. That's arguably correct (both facts are evidence), but it means the Heimdall team's "answered slowly" count includes calls that produced no usable answer. If the order's "one 8-excerpt screen took 8 min" refers to a call that *did* answer, fine; if it refers to one that timed out at the *router* level, note that a `DeadlineExceeded` raised by the *caller* (not a back-end) — i.e., the whole chain exhausting — is never logged. Only per-back-end misses are. If the intent was "every missed deadline," a chain-level exhaustion (all back-ends miss) still produces one line per back-end, so coverage holds; but a caller-side deadline that aborts the chain before a back-end misses (if such a path exists — I cannot see the full `call()` body, only the excerpt) would go unlogged. **Uncertain: the diff shows only the excerpt; I cannot verify there is no other deadline path.**

**P2-1 — notice list grows unbounded on a persistent write failure.** providers.py:41: every failed write appends to `self.notices` with no cap. A read-only mount or full disk over a long build = one notice per call. Cosmetic; the call still succeeds. Also, `self.notices` is appended without holding `self._lock()` — if `notices` is read concurrently elsewhere, this is a benign-list race I cannot rule out from the diff (the Router's other lock usage isn't shown).

**P2-2 — lock is per-Router, not per-file.** providers.py:20: `threading.Lock` guards only this instance. If two Router instances (e.g., proof_ly.py:96-98 and proof_ledger.py:75-77, or a build + a proof script) point at the same `DEADLINE_LOG` path, their lines can interleave *between* processes/instances. Each line is still a single small `write()` under `open(..., "a")`, so O_APPEND keeps it line-atomic in practice on Linux; risk is theoretical. Also `os.makedirs` runs on every log call inside the lock — trivial cost, but it's per-write.

**P2-3 — `import threading` inside `__init__`.** providers.py:18: works, but module-level import is the file's convention elsewhere (json/os/time are used bare at :34). Style only.

**P2-4 — test asserts `seconds >= 0.2` but the record's `seconds` comes from the back-end's self-reported third return value.** test:128-131, 139: `Took.complete` returns a *constant* 0.25, and the production code logs whatever the back-end reports (`secs`), not a measured wall time. If the production `secs` is measured around the call (not shown in the diff), fine; if it's the back-end's self-report, the "8 min" evidence's accurac

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 37 s finish=stop usage in 7771 / out 352 usd~0.048 (upper-bound price)

**P0 findings:** None verifiable from diff.

**P1 findings:** None verifiable from diff.

**P2 findings:**
- pipeline/providers.py:18 (concrete scenario): `import threading` is inside `Router.__init__` (visible diff places it after `self.limit_basis = ...`); this is legal but non-standard and not at module top.
- pipeline/providers.py:34,37 (concrete scenario): `_log_slow` calls `json.dumps`, `os.makedirs`, `time.strftime` and `open`; diff does not show these imports, so uncertain whether they are already present in the file (if absent, NameError on first log).
- pipeline/providers.py:36 (concrete scenario): `self._log_lock = threading.Lock()` is per-Router instance; diff does not show whether production code (thread pool) uses a single shared Router instance, so uncertain whether concurrent writes to same `deadline_log` are guaranteed non-interleaved.
- pipeline/providers.py:50 vs 61 (concrete scenario): missed_deadline log hard-codes `"seconds": deadline_s`; slow log uses `round(secs, 2)`; matches order's "seconds" requirement but diff does not show exact timing source for DeadlineExceeded path.

All other claims in the order (exactly-once logging per event, no effect on call outcome/spend ledger/return values, no secrets written, failed write becomes notice only, new test coverage of slow/no-log paths, lock usage for append) are directly verifiable in the diff and hold. No violations of any listed governing LAWS are detectable in this isolated change.

SHIP: yes with conditions (module-level imports for json/os/time must be confirmed present; single Router instance must be confirmed for lock correctness).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 39 s finish=stop usage in 8451 / out 1280 usd~0.045 (upper-bound price)

# Audit: C1_STEP.diff (pp-selectid)

## P0 Findings
None.

## P1 Findings

**1. `pipeline/providers.py:34` — `time` module not imported in the diff**
The new method `_log_slow` calls `time.strftime(...)` and `time.gmtime()`. The diff does not show an `import time` statement being added to `pipeline/providers.py`. If `time` is not already imported at the top of the module (which is plausible given the file is ~750+ lines and may use `time` elsewhere, but not verifiable from this diff alone), this will raise `NameError` at runtime.
*Scenario:* First slow call or missed deadline triggers `_log_slow` → `NameError: name 'time' is not defined` → caught by the `except OSError` block? **No** — `NameError` is not an `OSError`, so it propagates up and **crashes the call**, violating the stated invariant that "a write that fails becomes a notice and the call goes on." This would turn an evidence-logging failure into a hard failure of the model call.
*Verification needed:* Confirm `import time` exists in `pipeline/providers.py` outside this diff. If it does, downgrade to P2.

**2. `pipeline/providers.py:37` — `os.makedirs` on every log write**
`os.makedirs(os.path.dirname(...), exist_ok=True)` is called on every single log line. While `exist_ok=True` makes it idempotent, this is a filesystem syscall on the hot path of every slow/missed call. Under concurrent load (thread pool), this is a minor contention point on the directory inode. Not a correctness bug, but unnecessary I/O.
*Scenario:* 50 concurrent slow calls → 50 redundant `makedirs` syscalls. Low risk, but worth noting.

## P2 Findings

**3. `pipeline/providers.py:34` — UTC stamp uses second-resolution `time.strftime`**
The timestamp is `%Y-%m-%dT%H:%M:%SZ` (no sub-second). If two calls miss their deadline in the same second, their log lines are indistinguishable by timestamp alone. The `model` and `role` fields disambiguate, but for forensic ordering of near-simultaneous events, millisecond resolution would be preferable.
*Scenario:* Two backends time out in the same second; the Heimdall team cannot determine which was first from the log alone.

**4. `pipeline/providers.py:50-52` — `seconds` field in `missed_deadline` is always equal to `deadline_s`**
The logged `"seconds": deadline_s` is the deadline value, not the actual elapsed time at abandonment. The order asks for "seconds" as evidence of how long the call took. Since the call was abandoned *at* the deadline, the actual elapsed time is approximately `deadline_s`, but if the timer has drift or the check is slightly late, the true elapsed time could differ. This is a minor semantic inaccuracy: the field name implies measured duration, but it's the configured limit.
*Scenario:* Heimdall team reads `"seconds": 300.0` and assumes the call ran exactly 300 s; in reality it may have been 300.02 s or 299.98 s. Low impact.

**5. `tests/providers/test_providers.py:115-117` — Test reads log file without closing it**
`open(os.path.join(d, "DEADLINES.jsonl"))` is not closed (no `with` statement). In CPython this is harmless due to reference counting, but it's a resource leak in principle and inconsistent with the `with` usage elsewhere in the test.
*Scenario:* No practical impact in the test suite, but poor hygiene.

**6. `pipeline/providers.py:18` — `import threading` inside `__init__`**
The import is inside the method body rather than at module level. This works but is unconventional and slightly slower on first instantiation (though negligible). More importantly, if `threading` were somehow unavailable (it's stdlib, so this is theoretical), the failure mode would be a `ModuleNotFoundError` at construction time rather than import time.
*Scenario:* No practical impact.

## Verification of Stated Invariants

| Invariant | Verdict |
|---|---|
| Every missed deadline logged exactly once | **Yes** — the `except DeadlineExceeded` block is the sole path for abandonment, and `_log_slow` is called once there. |
| Log never changes call outcome or spend ledger | **Yes** — `_log_slow` is called *after* `_settle` in both paths; a write failure appends to `self.notices` and does not re-raise (assuming `time` is imported, see P1-1). |
| Concurrent calls cannot interleave lines | **Yes** — `self._log_lock` (a `threading.Lock`) guards the entire `open`/`write`/`close` sequence. Each line is written atomically under the lock. |
| No secrets written (no keys, no prompt text) | **Yes** — only `prompt_chars` (integer length) is logged, never the prompt string. No API keys, no response text. |
| Without `deadline_log`, nothing is written | **Yes** — `_log_slow` returns immediately if `self.deadline_log` is falsy. |

## SHIP: yes with conditions

**Condition:** Verify that `import time` is present in `pipeline/providers.py` (module-level or earlier in the file). If it is not, this is a **P0** — the evidence logger will crash the model 

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0831 (order 08:06 item 55: the missed-deadline evidence log): cycle 1 consensus

**Run.** No P0 or P1 that holds. Verdicts:
- grok: "yes with conditions";
- qwen: "yes with conditions";
- glm: "SHIP: yes".

## The conditions, answered from the code (no change)

| # | condition | the code |
|---|---|---|
| A1 | grok / qwen: are json, os and time imported at module level? (If time were missing, the logger would raise inside call()) | pipeline/providers.py lines 33-35: `import json`, `import os`, `import time`. time.strftime is already used by _record (line 709). |
| A2 | grok: one Router per process for the lock | _log_lock is per Router. A build constructs ONE Router (proof_ledger / proof_ly). Its thread pool shares that instance, so the lock serialises every line in the build. Each line goes out in one small append (well under a page), so two builds' lines cannot interleave inside a line either. |
| A3 | glm P1-1: the slow log fires even for an empty reply | Intended: a call that took >= slow_log_s is evidence whatever it returned, and the line carries its in / out tokens. |

## Verification

- test_providers 16 OK; every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0831/C2_STEP.diff (150 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 49bfc9f..1eaba43 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -501,7 +501,7 @@ class Router:
   6 |      spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""
   7 |  
   8 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
   9 | -                 local_llm=None, chains=None, limit_basis="estimate"):
  10 | +                 local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0):
  11 |          with open(config) as f:
  12 |              self.config = json.load(f)
  13 |          self.env_path = env_path or ENV_PATH
  14 | @@ -509,6 +509,9 @@ class Router:
  15 |          if limit_basis not in ("estimate", "reported"):
  16 |              raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
  17 |          self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
  18 | +        import threading
  19 | +        self.deadline_log, self.slow_log_s = deadline_log, slow_log_s     # order 08:06 item 55: the evidence file
  20 | +        self._log_lock = threading.Lock()
  21 |          self.down, self.notices = {}, []
  22 |          self.backends = {}
  23 |          for name, spec in self.config["backends"].items():
  24 | @@ -578,6 +581,21 @@ class Router:
  25 |          with self._lock():
  26 |              return float(self._ledger()["usd_estimate"])
  27 |  
  28 | +    def _log_slow(self, rec):
  29 | +        """Order 08:06 item 55: one JSON line per call that missed its deadline or answered in >= slow_log_s, appended
  30 | +        to deadline_log (the evidence the Heimdall team gets). Evidence, never a gate: a write that fails becomes a
  31 | +        notice and the call goes on."""
  32 | +        if not self.deadline_log:
  33 | +            return
  34 | +        line = json.dumps(dict(rec, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
  35 | +        try:
  36 | +            with self._log_lock:
  37 | +                os.makedirs(os.path.dirname(os.path.abspath(self.deadline_log)), exist_ok=True)
  38 | +                with open(self.deadline_log, "a") as f:
  39 | +                    f.write(line + "\n")
  40 | +        except OSError as e:
  41 | +            self.notices.append(f"the deadline log could not be written: {type(e).__name__}: {e}")
  42 | +
  43 |      def _basis_total(self, d):
  44 |          """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
  45 |          bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
  46 | @@ -726,6 +744,9 @@ class Router:
  47 |              except DeadlineExceeded as e:              # abandoned; the vendor may still bill it, so its UPPER bound is
  48 |                  self._settle(key, b, {"in": 0, "out": 0}, upper, role)     # booked as spent (estimate, unreported)
  49 |                  tried.append((name, f"{e} (abandoned at the deadline; its upper bound ${upper:.2f} booked as spent)"))
  50 | +                self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
  51 | +                                "deadline_s": deadline_s, "seconds": deadline_s, "prompt_chars": len(prompt),
  52 | +                                "max_tokens": max_tokens})
  53 |                  continue
  54 |              except RequestRejected as e:
  55 |                  self._settle(key)
  56 | @@ -741,6 +762,11 @@ class Router:
  57 |                  raise
  58 |              usd = b.usd(usage)
  59 |              self._settle(key, b, usage, usd, role)
  60 | +            if secs >= self.slow_log_s:                # item 55: an answer this slow is evidence too
  61 | +                self._log_slow({"kind": "answered_slowly", "threshold_s": self.slow_log_s, "role": role, "model": name,
  62 | +                                "vendor": b.vendor, "deadline_s": deadline_s, "seconds": round(secs, 2),
  63 | +                                "prompt_chars": len(prompt), "max_tokens": max_tokens, "in": (usage or {}).get("in"),
  64 | +                                "out": (usage or {}).get("out")})
  65 |              if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
  66 |                  tried.append((name, "refused this request: an empty reply"))
  67 |                  continue
  68 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  69 | index 637e675..1ea63a0 100644
  70 | --- a/tests/package/proof_ledger.py
  71 | +++ b/tests/package/proof_ledger.py
  72 | @@ -121,7 +121,7 @@ def main(argv=None):
  73 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
  74 |                    f, indent=1, default=str)
  75 |      router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
  76 | -                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains())
  77 | +                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(), deadline_log=PL.DEADLINE_LOG)
  78 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
  79 |      if spent0 >= PL.LY_STOP_USD:
  80 |          say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
  81 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
  82 | index c958eab..24e4276 100644
  83 | --- a/tests/package/proof_ly.py
  84 | +++ b/tests/package/proof_ly.py
  85 | @@ -52,6 +52,7 @@ LY_LIMIT_BASIS = "reported"        # old $40 cap by the price-table estimate rea
  86 |  LY_STOP_USD = 10.0                 # the estimate counts only where a vendor reports none. At $10 no build starts.
  87 |                                     # Each paid call still RESERVES its price-table upper bound while in flight.
  88 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
  89 | +DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
  90 |  RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
  91 |          "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
  92 |          "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
  93 | @@ -276,7 +277,7 @@ def main(argv=None):
  94 |          print(table())
  95 |          return 0
  96 |      router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD,
  97 | -                      limit_basis=LY_LIMIT_BASIS, chains=chains())
  98 | +                      limit_basis=LY_LIMIT_BASIS, chains=chains(), deadline_log=DEADLINE_LOG)
  99 |      own = meter(router)
 100 |      used = reply_meter(router)
 101 |      os.makedirs(a.work_dir, exist_ok=True)
 102 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
 103 | index fb94590..0641fe9 100644
 104 | --- a/tests/providers/test_providers.py
 105 | +++ b/tests/providers/test_providers.py
 106 | @@ -89,9 +89,13 @@ class TestDeadline(unittest.TestCase):
 107 |              slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=2.0, family="deepseek")
 108 |              next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
 109 |              r = router(d, [slow, next_], {"angle_write": ["heimdall:deepseek", "heimdall:qwen"]},
 110 | -                       spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0)
 111 | +                       spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0,
 112 | +                       deadline_log=os.path.join(d, "DEADLINES.jsonl"))
 113 |              t0 = _t.time()
 114 |              rep = r.call("angle_write", "p", 100, 7, deadline_s=0.3)
 115 | +            log = [json.loads(x) for x in open(os.path.join(d, "DEADLINES.jsonl"))]       # item 55: the evidence
 116 | +            self.assertEqual([(x["kind"], x["model"], x["prompt_chars"], x["max_tokens"], x["deadline_s"]) for x in log],
 117 | +                             [("missed_deadline", "heimdall:deepseek", 1, 100, 0.3)])
 118 |              self.assertLess(_t.time() - t0, 1.5)                       # never waited for the slow one
 119 |              self.assertEqual((rep.backend, rep.text), ("heimdall:qwen", '{"ok": 2}'))
 120 |              self.assertIn("no answer within 0 s", rep.tried[0][1])   # the failover is recorded on the reply
 121 | @@ -102,6 +106,28 @@ class TestDeadline(unittest.TestCase):
 122 |                                     slow.upper_usd("p", 100), places=6)
 123 |              self.assertEqual(led["reserved"], {})                      # no reservation left behind
 124 |  
 125 | +    def test_item_55_a_slow_answer_is_logged_and_no_log_writes_nothing(self):
 126 | +        import tempfile
 127 | +        with tempfile.TemporaryDirectory() as d:
 128 | +            class Took(Fake):                                           # a back-end reports its own seconds
 129 | +                def complete(self, prompt, max_tokens, seed, system=None):
 130 | +                    text, usage, _ = super().complete(prompt, max_tokens, seed, system)
 131 | +                    return text, usage, 0.25
 132 | +            slow = Took("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek")
 133 | +            path = os.path.join(d, "DEADLINES.jsonl")
 134 | +            r = router(d, [slow], {"check": ["heimdall:deepseek"]}, deadline_log=path, slow_log_s=0.2)
 135 | +            r.call("check", "pp", 50, 7)                                # no deadline, answered in 0.25 s >= 0.2 s
 136 | +            log = [json.loads(x) for x in open(path)]
 137 | +            self.assertEqual([(x["kind"], x["prompt_chars"], x["in"], x["out"]) for x in log],
 138 | +                             [("answered_slowly", 2, 1000, 100)])
 139 | +            self.assertGreaterEqual(log[0]["seconds"], 0.2)
 140 | +            fast = Fake("heimdall:qwen", "heimdall", answer="{}")
 141 | +            router(d, [fast], {"check": ["heimdall:qwen"]}, deadline_log=path, slow_log_s=0.2).call("check", "p")
 142 | +            self.assertEqual(len(open(path).read().splitlines()), 1)   # a fast answer is not evidence
 143 | +            router(d, [Took("heimdall:x", "heimdall", answer="{}")], {"check": ["heimdall:x"]},
 144 | +                   slow_log_s=0.2).call("check", "p")                   # no deadline_log: nothing written
 145 | +            self.assertEqual(len(open(path).read().splitlines()), 1)
 146 | +
 147 |      def test_an_answer_inside_the_deadline_and_an_error_keep_their_meaning(self):
 148 |          import tempfile
 149 |          with tempfile.TemporaryDirectory() as d:
 150 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse). providers.Router calls paid model vendors in a
fail-over chain. A writer call has a deadline (300 s): a back-end that misses it is abandoned (DeadlineExceeded) and
the chain moves on. Your role: a strict reviewer of a new evidence log.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

The order this diff implements (ORCHESTRATOR 08:06 item 55, verbatim): "Heimdall deepseek and qwen both missed 300 s on
the angle step at 07:14, and one 8-excerpt screen took 8 min. Record every missed deadline (model, prompt size,
seconds) in one file for the Heimdall team; I owe PBX that evidence."
- Already done (data, not in this diff): docs/audits/parallel/pp-selectid_HEIMDALL_DEADLINES.md + .jsonl, backfilled
  from the build records and the reply cache.

The change:
1. pipeline/providers.py:
   - Router(..., deadline_log=None, slow_log_s=240.0) and _log_slow(rec), which appends one JSON line (with a UTC
     stamp) to deadline_log under a threading.Lock;
   - when the call abandons a back-end at its deadline it logs {"kind": "missed_deadline", role, model, vendor,
     deadline_s, seconds, prompt_chars, max_tokens};
   - when a back-end answers in >= slow_log_s it logs {"kind": "answered_slowly", threshold_s, role, model, vendor,
     deadline_s, seconds, prompt_chars, max_tokens, in, out};
   - without deadline_log nothing is written. A failed write becomes a router notice and never fails the call: this
     is evidence, not a gate.
2. tests/package/proof_ly.py + proof_ledger.py: the order's Routers log to the evidence file's .jsonl (DEADLINE_LOG).
3. tests/providers/test_providers.py:
   - the existing deadline test also asserts the one missed_deadline line;
   - a new test: an answer of 0.25 s against a 0.2 s threshold is logged with its tokens; a fast answer is not; a
     Router with no deadline_log writes nothing.
- test_providers 16 OK; every other suite OK.

Check: every missed deadline is logged exactly once with the fields the order names; the log can never change a
call's outcome or the spend ledger; concurrent calls (the build calls the router from a thread pool) cannot interleave
lines; nothing secret (a key, a prompt's text) is written: only sizes.

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
