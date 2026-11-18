# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261118_0711
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 318 s finish=stop usage in 9489 / out 6052 usd_reported=0.001045 usd~0.119 (upper-bound price)

The code implements RULING 144 to allow a one-time window exception for a specific package. While the logic for window extension and flag counting is correct, there is a critical synchronization error in the build driver.

### Findings

**[P1] Review Flags Mismatch in Build Driver**
In `tests/package/proof_ledger.py` (lines 106-110), the driver injects the `EXCEPTION_GATE` into `res["package"]["gates"]`. However, it does not update the `res["package"]["review_flags"]` summary field. 
Immediately after, it calls `LP.pin_problems(res["package"])` (line 111). This function calls `package_pin.review_problems`, which performs a strict equality check:
`want, got = review_flags_of(mp.get("gates")), mp.get("review_flags") or []`
`out = [] if got == want else [f"review_flags {got} are not the sealed gates' flags {want}"]`
Because `want` now includes the exception flag (via `review_flags_of`) but `got` (the summary field) does not, `review_problems` will return a mismatch error. This will cause `lock` to be non-empty, and the build will be refused, making the `--pbx-exception` flag functionally unusable.

**[P3] Redundant `isinstance` check in `content_flags`**
In `pipeline/package_pin.py` (line 46), the check `if isinstance(gates, dict)` is performed twice in the same line (once for the `exc` assignment and once implicitly via the `review_flags_of(gates)` call which also handles the type check). This is a minor nit.

### Verification of Governing Laws
- **L-j (Release Auth):** The exception is correctly logged as a `FLAGGED` row in the gates, ensuring the evidence is present in the final bytes.
- **RULING 144 (Review Flags):** The sorting logic in `review_flags_of` (`key=lambda kv: kv[0] != EXCEPTION_GATE`) correctly ensures the exception flag appears first.
- **RULING 144 (Cap):** `content_flags` correctly excludes the exception flags from the `REVIEW_FLAGS_MAX` count.
- **Process Isolation:** The modification of `package_pin.WINDOW_H` is local to the `proof_ledger.py` process, ensuring the exception does not leak to other builds.

P1_OR_WORSE: 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 326 s finish=stop usage in 9032 / out 10277 usd_reported=0.007747 usd~0.181 (upper-bound price)



# Code Audit — RULING 144 (PBX Exception, pp-selectid)

## Scope Reviewed
Three files: `pipeline/package_pin.py`, `tests/package/proof_ledger.py`, `tests/package/test_ruling_137.py`. The change introduces a named, logged, one-process exception that extends the 12-hour window to at most 30 hours for a single build, places the exception's plain words as the first review flag, and excludes them from the 3-flag content cap.

---

## Findings

### [P2] Global mutation of `package_pin.WINDOW_H` is a process-wide side effect

```python
if a.pbx_exception:
    package_pin.WINDOW_H = float(a.hours)
```

This rewrites a module-level constant that `package.expired`, `window_problems`, and the candidate registry all read. The design contract is "one build = one process," and the test confirms the value is restored in the test's `finally`. However, if this driver is ever invoked more than once in a long-lived process (a test harness, a supervisor that re-enters `main`), the second invocation inherits the first's widened window with no exception flag. A parameter-passing approach (threading `window_h` into the checks that need it) would eliminate the class of bug entirely.

*Why not P1:* The stated architecture is strictly one-process-per-build, the refusal path (exit 2) occurs before the mutation, and the test pins the invariant. It is a latent fragility, not a live defect.

---

### [P2] Exception gate is injected after `SP.attribute_package` (the seal)

```python
SP.attribute_package(router, res["package"], sources, log=say)   # seal
try:
    if a.pbx_exception:
        res["package"]["gates"][package_pin.EXCEPTION_GATE] = {…}
    lock = LP.pin_problems(res["package"]) + \
        package_pin.window_problems(res["package"]["segments"])
```

The ruling's narrative says "after the package seals and before its pin is written," which matches the code. But if `pin_problems` (or any downstream validator) re-hashes the gate set against the seal produced by `attribute_package`, the added row would break that hash and the pin would be refused. The diff does not show `pin_problems`'s body, so I cannot confirm it is seal-agnostic with respect to gates.

*Action:* Verify that `LP.pin_problems` does not compare the gate inventory to the seal. If it does, the exception row must be added *before* `attribute_package`, or the seal must be recomputed after insertion.

---

### [P2] `content_flags` will raise `AttributeError` if the exception gate's value is a non-dict truthy

```python
exc = ((gates or {}).get(EXCEPTION_GATE) or {}).get("flags") or [] if isinstance(gates, dict) else []
```

If `gates["pbx_exception"]` were ever a string, number, or list (data corruption, a hand-edited JSON), `(value or {})` evaluates to `value` (truthy non-dict), and `.get("flags")` raises. `review_flags_of` guards with `isinstance(row, dict)`, but `content_flags` does not.

*Fix:*
```python
row = (gates or {}).get(EXCEPTION_GATE) if isinstance(gates, dict) else None
exc = (row.get("flags") or []) if isinstance(row, dict) else []
```

---

### [P3] `--pbx-exception` accepts the bare prefix with no description

The validation is:
```python
a.pbx_exception.startswith("PBX exception") and a.pbx_exception.strip()
```

The string `"PBX exception"` (14 characters, no trailing text) passes. The ruling requires the exception to be "named and logged"; a bare prefix is technically a name but carries no context for the reviewer reading the flag. Consider requiring a minimum length or a non-empty remainder after the prefix:
```python
a.pbx_exception[len("PBX exception"):].strip()
```

---

### [P3] `content_flags` called twice in `to_pin`

```python
problems += [f"{content_flags(pk.get('gates'))} review flags, over …"] \
    if content_flags(pk.get("gates")) > REVIEW_FLAGS_MAX else []
```

The function is evaluated once for the f-string and once for the condition. Harmless (pure function, small input) but a local variable would read cleaner and guard against a future refactor that makes it impure.

---

### [P3] Redundant `isinstance` check on an argparse string

```python
isinstance(a.pbx_exception, str) and a.pbx_exception.startswith("PBX exception")
```

`argparse` with `metavar="TEXT"` (no `type=`) always yields a `str` or `None`. The `isinstance` guard is dead code. Not wrong, just noise.

---

## Answers to the Reviewer's Four Questions

1. **Can the exception leak to a later build or another pin?**
   No. The mutation is process-local (one build = one process, exit after). The gate row and `res["pbx_exception"]` are embedded in this package's JSON only. A later process starts with `WINDOW_H = 12` and must pass `--pbx-exception` again to widen it. The never-reused check reads delivered pins and is unaffected.

2. **Can it carry more than one flag past the cap, or hide a doubt?**
   The exception gate is always populated with exa

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261118_0711, ruling 144's one exception)

SEATS ANSWERED: 2 of 3. qwen3.8-27b: P0/P1 none. gemma-4-31b-it: one P1 claimed, REFUTED below. gpt-oss-20b: no answer.

gemma [P1] "the driver adds the exception row to the package's gates but not to a review_flags field, and
LP.pin_problems -> review_problems then refuses the pin": REFUTED. lock_precheck.pin_problems(pk) checks ONLY the lock
pre-check's coverage of the package's segments (ruling 68: ok, the same spans, pass / adopt, the same texts); it never
reads review flags. The PACKAGE carries no "review_flags" field at all: package_pin.to_pin derives them from the sealed
gates (rf = review_flags_of(pk["gates"])) and writes them into the pin's moments_package, so the exception row added
before write_pin is in them by construction, first. review_problems(mp) is the integrator's check of a written PIN,
where got == want by that construction.
gemma [P3] the double isinstance in content_flags: cosmetic, declined.

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261118_0711/C2_STEP.diff (171 lines)
```
   1 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
   2 | index e2403da..34d7bce 100644
   3 | --- a/pipeline/package_pin.py
   4 | +++ b/pipeline/package_pin.py
   5 | @@ -42,9 +42,13 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
   6 |                          "coherence", "ly_shape",           # RULING 141 (3), the line-up chain phase A: clip
   7 |                          #   ratings and unbridged joins of a kept candidate (the through-line and every other L-y check
   8 |                          #   stay HARD; the takeaway's value rows are not soft)
   9 | -                        "stand_alone"})                    # RULING 141 (2): a clip's STAND_ALONE opener (the topic
  10 | +                        "stand_alone",                     # RULING 141 (2): a clip's STAND_ALONE opener (the topic
  11 | +                        "pbx_exception"})                  # RULING 144: EXCEPTION_GATE, only on the one excepted pin
  12 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
  13 |  REVIEW_FLAGS_MAX = 3
  14 | +EXCEPTION_GATE = "pbx_exception"   # RULING 144 (PBX 07:05 ET Nov 18): a named, logged exception to a HARD rule for ONE
  15 | +#   package. Its row is FLAGGED with the exception in plain words; its sentence opens the review flags (the note's top
  16 | +#   line) and is not a doubt about the content, so it never counts toward REVIEW_FLAGS_MAX.
  17 |  
  18 |  
  19 |  # RULING 90 (orchestrator 22:40 ET Nov 13; LAW since 22:52, amended by 91 and 92): the SPOTLIGHT, a second pin kind.
  20 | @@ -397,9 +401,11 @@ def flagged_ok(g, row):
  21 |  
  22 |  
  23 |  def review_flags_of(gates):
  24 | -    """RULING 137: the plain-word flags of the inventory's FLAGGED rows, in gate order, each once."""
  25 | +    """RULING 137: the plain-word flags of the inventory's FLAGGED rows, in gate order, each once; RULING 144: an
  26 | +    exception's row first (the note's top line)."""
  27 |      out = []
  28 | -    for _g, row in (gates.items() if isinstance(gates, dict) else ()):
  29 | +    items = list(gates.items()) if isinstance(gates, dict) else []
  30 | +    for _g, row in sorted(items, key=lambda kv: kv[0] != EXCEPTION_GATE):
  31 |          if isinstance(row, dict) and row.get("status") == "FLAGGED":
  32 |              out += [f for f in row.get("flags") or [] if isinstance(f, str) and f not in out]
  33 |      return out
  34 | @@ -410,8 +416,14 @@ def review_problems(mp):
  35 |      over REVIEW_FLAGS_MAX (empty = it holds)."""
  36 |      want, got = review_flags_of(mp.get("gates")), mp.get("review_flags") or []
  37 |      out = [] if got == want else [f"review_flags {got} are not the sealed gates' flags {want}"]
  38 | -    return out + ([f"{len(want)} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"]
  39 | -                  if len(want) > REVIEW_FLAGS_MAX else [])
  40 | +    n = content_flags(mp.get("gates"))
  41 | +    return out + ([f"{n} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] if n > REVIEW_FLAGS_MAX else [])
  42 | +
  43 | +
  44 | +def content_flags(gates):
  45 | +    """RULING 136 (2) / 144: the flags that count toward REVIEW_FLAGS_MAX: every review flag except an exception's."""
  46 | +    exc = ((gates or {}).get(EXCEPTION_GATE) or {}).get("flags") or [] if isinstance(gates, dict) else []
  47 | +    return len([f for f in review_flags_of(gates) if f not in exc])
  48 |  
  49 |  
  50 |  def gate_problems(gates, required=REQUIRED_GATES):
  51 | @@ -502,8 +514,8 @@ def to_pin(pk, run_name):
  52 |          screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
  53 |          spotlight_problems(pk) + takeaway_problems(pk)
  54 |      rf = review_flags_of(pk.get("gates"))                 # RULING 137: derived from the sealed gates, at most 3
  55 | -    problems += [f"{len(rf)} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] if len(rf) > REVIEW_FLAGS_MAX \
  56 | -        else []
  57 | +    problems += [f"{content_flags(pk.get('gates'))} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] \
  58 | +        if content_flags(pk.get("gates")) > REVIEW_FLAGS_MAX else []
  59 |      if problems:
  60 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
  61 |      segs = []
  62 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  63 | index 3359471..55b6b06 100644
  64 | --- a/tests/package/proof_ledger.py
  65 | +++ b/tests/package/proof_ledger.py
  66 | @@ -249,6 +249,7 @@ def delivered_pins(paths):
  67 |      return spans, newest, pins
  68 |  
  69 |  
  70 | +PBX_EXCEPTION_MAX_H = 30.0     # RULING 144 (PBX 07:05 ET Nov 18): yesterday's batch, for one package only
  71 |  STOP_CEILING_USD = 1.50          # RULING 137 (3) (orchestrator 11:05 ET Nov 17): the day cap is $1.50 all-in from the
  72 |  #   21:10 ET day of Nov 17 (today's stop $1.40, given as --stop-usd); --stop-usd at most this. Was 1.25 (ORDER 17:50 ET
  73 |  #   Nov 16, 'ADD 25 CENTS').
  74 | @@ -443,14 +444,25 @@ def main(argv=None):
  75 |                      "build takes only those moments of the pool, every gate as before (one line-up at a time)")
  76 |      ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
  77 |                      f"limit (no build starts at it; the router stops outside calls at it), in (0, {STOP_CEILING_USD}]")
  78 | +    ap.add_argument("--pbx-exception", metavar="TEXT", default=None,
  79 | +                    help="RULING 144 (PBX 07:05 ET Nov 18): this ONE build's 12 h window is waived, named and logged "
  80 | +                         "(TEXT starts 'PBX exception'): --hours may reach PBX_EXCEPTION_MAX_H, every 12 h check of "
  81 | +                         "this process reads it, and the package carries TEXT as its first review flag")
  82 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
  83 |                      help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
  84 |                           "record (its tried[N]; default the first that passed), as it was judged")
  85 |      a = ap.parse_args(argv)
  86 |      now = datetime.now(timezone.utc)
  87 | -    if not 0 < a.hours <= package_pin.WINDOW_H:          # ruling 76: "rather than widen the window"
  88 | -        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {package_pin.WINDOW_H:g}]", file=sys.stderr)
  89 | +    if a.pbx_exception is not None and not (isinstance(a.pbx_exception, str) and
  90 | +                                            a.pbx_exception.startswith("PBX exception") and a.pbx_exception.strip()):
  91 | +        print("REFUSED (ruling 144): --pbx-exception must name the exception ('PBX exception ...')", file=sys.stderr)
  92 |          return 2
  93 | +    cap = PBX_EXCEPTION_MAX_H if a.pbx_exception else package_pin.WINDOW_H
  94 | +    if not 0 < a.hours <= cap:                           # ruling 76: "rather than widen the window" (144: one exception)
  95 | +        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {cap:g}]", file=sys.stderr)
  96 | +        return 2
  97 | +    if a.pbx_exception:                                  # RULING 144: this process only; every later build is 12 h
  98 | +        package_pin.WINDOW_H = float(a.hours)            # (package.expired, window_problems and the registry read it)
  99 |      try:                                                 # read before anything is written (glm C2 N-4)
 100 |          delivered, last, pins = delivered_pins(a.delivered)
 101 |          since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
 102 | @@ -641,6 +653,11 @@ def main(argv=None):
 103 |      if res["package"]:
 104 |          SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 105 |          try:
 106 | +            if a.pbx_exception:                          # RULING 144: the exception's row, its plain words first
 107 | +                res["package"]["gates"][package_pin.EXCEPTION_GATE] = {
 108 | +                    "status": "FLAGGED", "flags": [a.pbx_exception], "by": "ruling 144 (PBX 07:05 ET Nov 18)",
 109 | +                    "replayed": False, "n": len(res["package"]["segments"]), "window_h": a.hours}
 110 | +                res["pbx_exception"] = {"text": a.pbx_exception, "window_h": a.hours}
 111 |              lock = LP.pin_problems(res["package"]) + \
 112 |                  package_pin.window_problems(res["package"]["segments"])   # ruling 68; ruling 76 (c), render clock
 113 |              if lock:
 114 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 115 | index b0e276d..a679178 100644
 116 | --- a/tests/package/test_ruling_137.py
 117 | +++ b/tests/package/test_ruling_137.py
 118 | @@ -548,6 +548,52 @@ class TestRuling141LineUpChain(unittest.TestCase):
 119 |          self.assertFalse([t for t in out["never_empty"]["soft_record"]["tried"] if t.get("kept")])
 120 |  
 121 |  
 122 | +class TestRuling144TheOneException(unittest.TestCase):
 123 | +    """RULING 144 (PBX 07:05 ET Nov 18): ONE build's 12 h window waived, named and logged. Its row is FLAGGED with the
 124 | +    plain words, they open the review flags (the note's top line), and they never count toward the cap of 3."""
 125 | +    EXC = "PBX exception Nov 18: these clips are older than 12 hours (allowed for this one video only)"
 126 | +
 127 | +    def gates(self, n_content):
 128 | +        g = {f"g{i}": {"status": "FLAGGED", "flags": [f"doubt {i}"], "by": "x", "replayed": False, "n": 1}
 129 | +             for i in range(n_content)}
 130 | +        g[PP.EXCEPTION_GATE] = {"status": "FLAGGED", "flags": [self.EXC], "by": "ruling 144", "replayed": False, "n": 3}
 131 | +        return g
 132 | +
 133 | +    def test_the_exception_reads_first_and_is_not_a_doubt(self):
 134 | +        g = self.gates(3)
 135 | +        self.assertEqual(PP.review_flags_of(g), [self.EXC, "doubt 0", "doubt 1", "doubt 2"])
 136 | +        self.assertEqual(PP.content_flags(g), 3)
 137 | +        self.assertEqual(PP.review_problems({"gates": g, "review_flags": PP.review_flags_of(g)}), [])
 138 | +        self.assertEqual(len(PP.review_problems({"gates": self.gates(4), "review_flags": PP.review_flags_of(
 139 | +            self.gates(4))})), 1)                                           # a 4th DOUBT still refuses
 140 | +        self.assertIn(PP.EXCEPTION_GATE, PP.SOFT_GATES)
 141 | +
 142 | +    def test_the_driver_takes_it_only_named_and_only_in_this_process(self):
 143 | +        import proof_ledger as PLG
 144 | +        pins = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof", "fresh_20261112_050611", n)
 145 | +                for n in ("MOMENTS_PIN.json", "MOMENTS_PIN_LY.json")]
 146 | +
 147 | +        class Past(Exception):
 148 | +            pass
 149 | +
 150 | +        def stop(*a, **k):
 151 | +            raise Past()
 152 | +        saved = PP.WINDOW_H
 153 | +        try:
 154 | +            with mock.patch("sys.stderr"):
 155 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "26"]), 2)            # 12 h as ever
 156 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "26", "--pbx-exception", "please"]), 2)
 157 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "31", "--pbx-exception",
 158 | +                                           "PBX exception x"]), 2)                                  # 30 h at most
 159 | +            self.assertEqual(PP.WINDOW_H, saved)                               # nothing changed by a refusal
 160 | +            with mock.patch.object(PLG, "delivered_pins", stop):
 161 | +                with self.assertRaises(Past):
 162 | +                    PLG.main(["--delivered", *pins, "--hours", "26", "--pbx-exception", "PBX exception x"])
 163 | +            self.assertEqual(PP.WINDOW_H, 26.0)                                # this process: every 12 h check reads it
 164 | +        finally:
 165 | +            PP.WINDOW_H = saved
 166 | +
 167 | +
 168 |  class TestTheDayCount(unittest.TestCase):
 169 |      def test_counted_per_day_ledger(self):
 170 |          with tempfile.TemporaryDirectory() as d:
 171 | 
```

---

pp-selectid: RULING 144 (orchestrator 07:15 ET Nov 18, PBX's words 07:05: "disregard the 12 hour rule for this one
exception and get this video done"). ONE package, from yesterday's batch, with the 12 h window waived: a NAMED, LOGGED
exception ('PBX exception Nov 18: clips older than 12 hours'); never-reused still holds; the rule is back for every
later build. The integrator's render needs nothing (its only age gate is L-v 3's 24 h for time_sensitive segments) and
asked that the exception's plain words be the FIRST review flag (its note prints review flags first). Files:
tests/package/proof_ledger.py (the build driver), pipeline/package_pin.py, tests/package/test_ruling_137.py.

THE CHANGE:
(a) proof_ledger: --pbx-exception TEXT. Refused (exit 2, before anything is written) unless TEXT starts "PBX exception".
    With it, --hours may reach PBX_EXCEPTION_MAX_H (30) instead of package_pin.WINDOW_H (12); without it, 12 as ever.
    package_pin.WINDOW_H = hours FOR THIS PROCESS ONLY (one build = one process; every 12 h check reads that constant:
    package.expired, package_pin.window_problems at the seal, the candidate registry's expiry). After the package seals
    and before its pin is written, the driver adds the exception's gate row (FLAGGED, flags [TEXT], replayed False) and
    records res["pbx_exception"].
(b) package_pin: EXCEPTION_GATE "pbx_exception" in SOFT_GATES (FLAGGED accepted by gate_problems as any soft row);
    review_flags_of lists its flags FIRST; content_flags = the review flags except the exception's: the cap of 3
    (to_pin and review_problems) counts only doubts about the content.

TESTS (test_ruling_137, 2 new): the exception first and not counted (3 doubts + it seal; a 4th doubt still refuses);
the driver: --hours 26 without the exception refused, an unnamed exception refused, 31 h refused, nothing changed by a
refusal, and with a named exception the window becomes 26 for the process. Mutations: 7 of 7 killed.

PLEASE CHECK: (1) can the exception leak to a later build or another pin? (2) can it carry more than ONE flag past the
cap, or hide a doubt? (3) anything else the 12 h rule guards that this bypasses (never-reused must hold)? (4) the tests.


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
