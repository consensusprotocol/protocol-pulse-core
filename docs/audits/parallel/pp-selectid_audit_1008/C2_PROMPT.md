# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1008
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 7 s finish=stop usage in 12480 / out 27 usd~0.038 (upper-bound price)

<critical> — none found. <high> — none found. <medium> — none found. SHIP: yes.

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 68 s finish=stop usage in 12568 / out 411 usd~0.073 (upper-bound price)

<critical> heimdall_health.py:112 (probe_due `if families is not None and s["mode"] != "plan_b" and failed and not failed & set(families)`): pp-ingest current calls (background: loads module by path, calls probe_due without families= kwarg, only note/mode/probe_due/probe_result) bypass the skip; builder note(False, family="deepseek") at :62 populates failing_families=["deepseek"]; pp-ingest probe_due(families=None) claims slot (returns True), runs probe_once on its families (no deepseek per background), probe_result(True) at :137 clears clock/families. Violates ruling "probe must be a real model call on the family that failed (and one other)"; enables false reset after single failed call. (Test at :253-254 assumes both sides pass families=; older state without failing_families key returns [] per :92, same bypass.)
<medium> heimdall_health.py:136 (`if answered and (fs is None or now >= fs)`): matches test at :221 (now=9 < fs=10 does not reset) and :136 comment but ruling says "timed before"; equal times (now == fs) would reset (no test for == case verifiable in diff). _t on unparsable failing_since_utc uncertain (facts only cover no-zone case returns None).
<medium> heimdall_health.py:59 and :61 (note else branch): if failure with family=None (pp-ingest current calls per (f)) and clock already running, does not clear/replace failing_families list (only appends on :62 if family truthy); verifiable as unchanged from pre-change path but interacts with cross-process probe claim above.

SHIP: yes with conditions (pp-ingest must update its note(False, family=...) and probe_due(families=...) calls simultaneously before merge/deploy; all 20 tests + mutations pass on single-process paths).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 75 s finish=stop usage in 13665 / out 4903 usd~0.115 (upper-bound price)

I have audited the diff against the governing laws, the orchestrator's ruling, and the specific attack vectors.

### Findings

**<critical> `pipeline/heimdall_health.py`: Race condition in `probe_due` allows slot starvation and double-claiming**
The `probe_due` function (lines 95-116 in the diff context) performs a read-modify-write cycle on the state file to claim a probe slot.
1.  **The Logic:** It checks `if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S: return False`. If this passes, it stamps `last_probe_utc` and `last_probe_by` and saves.
2.  **The Flaw:** The check for `families` (lines 111-113) happens *before* the time check. However, the critical failure is that `probe_due` is not atomic with respect to the *decision* to probe. Two processes (Builder and pp-ingest) can both call `probe_due` at nearly the same time.
    *   Process A (Builder) reads state: `last_probe_utc` is old. `failing_families` contains "deepseek". Builder's families include "deepseek". It proceeds to claim the slot.
    *   Process B (pp-ingest) reads state *concurrently* (before A saves): `last_probe_utc` is still old. `failing_families` contains "deepseek". pp-ingest's families do *not* include "deepseek" (they have qwen, glm, muse).
    *   Wait, the logic says: `if families is not None and s["mode"] != "plan_b" and failed and not failed & set(families): return False`.
    *   So Process B returns `False` correctly.
    *   **However**, consider the case where *both* can ask the failed family, or the case where the "failed" family is ambiguous.
    *   **Real Critical Issue:** The `probe_due` function claims the slot by writing to the file. If Process A claims the slot, it writes `last_probe_utc = now`. Process B, if it reads *after* A writes, sees the new time and returns `False`. This is safe *if* the flock is held during the entire read-check-write.
    *   **Let's look closer at the flock usage.** The docstring says "under an flock". The code uses `with _Locked(path):`. This serializes access.
    *   **So where is the critical bug?**
    *   Look at `probe_result` (lines 120-144). It resets `failing_since_utc` and `failing_families` if `answered` is True.
    *   Look at `note` (lines 41-65). If `answered` is False, it sets `failing_since_utc` if not already set, and adds to `failing_families`.
    *   **The Bug:** In `probe_due`, the check `if families is not None and s["mode"] != "plan_b" and failed and not failed & set(families): return False` relies on `failing_families` being accurate.
    *   **Scenario:**
        1.  Builder fails a call to `deepseek`. `note(False, family="deepseek")` is called. `failing_families = ["deepseek"]`. Clock starts.
        2.  Builder's probe thread wakes up. It calls `probe_due(families=["deepseek", "glm", "qwen"])`.
        3.  `failed = {"deepseek"}`. `failed & set(families)` is `{"deepseek"}`. It is not empty. So it does *not* return False early.
        4.  It checks time. It claims the slot. It writes `last_probe_utc`.
        5.  Builder executes the probe. It asks `deepseek`, `glm`, `qwen`.
        6.  **Simultaneously**, pp-ingest's watcher wakes up. It calls `probe_due(families=["qwen", "glm", "muse"])`.
        7.  If pp-ingest reads the state *before* Builder writes the claim, it sees `last_probe_utc` is old.
        8.  It checks `failed & set(families)`. `failed` is `{"deepseek"}`. `families` is `{"qwen", "glm", "muse"}`. Intersection is empty.
        9.  So pp-ingest returns `False`. It does *not* claim the slot.
        10. Builder claims the slot.
        11. This seems correct. The "failed family" steering works.

    *   **Wait, look at the "False Outage" scenario in the Ruling.**
        "One 502 on a calibration call, then silence, and the clock ran while every probe was answering."
        The fix is: `probe_result(True)` resets the clock.
        
    *   **Let's re-read the `probe_result` logic carefully.**
        ```python
        fs = _t(s.get("failing_since_utc"))
        if answered and (fs is None or now >= fs):     # not a late report from before the clock started
            s["last_answer_utc"], s["failing_since_utc"], s["failing_families"] = _iso(now), None, []
        ```
        If `answered` is True, and `now >= fs`, it resets the clock.
        
    *   **Is there a case where a probe answers, but the clock is NOT reset?**
        If `now < fs`. This is the "late report" guard.
        If a probe finishes at time T, but is reported at time T+2min (due to tick delay), and the failure started at T+1min.
        `fs` = T+1min. `now` (report time) = T+2min.
        `now >= fs` is True. Clock is reset.
        
        What if the probe *started* before the failure, but *finished* after?
        The ruling says: "A probe answer timed BEFORE the failure that started the clock... does not reset that clock."
        The code uses `

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 1008 (the orchestrator's 10:06 ruling 87 amended: an answered probe resets the clock; the probe asks the family that failed), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes with conditions (pp-ingest updates its calls). One <critical>, two <medium>.
- qwen3.8-27b: SHIP yes. Every <critical> and <high> in its text resolves inside its own text ("This seems correct",
  "This is CORRECT"); its summary: none found.
- glm-5.3-flash: "none found ... SHIP: yes" in 27 tokens and 7 s. That is too thin to count as a review: it is recorded
  here, not counted as evidence either way.

Upper-bound cost: about $0.23 ($0.073 + $0.115 + $0.038), outside SPEND_LY.json.

## Implemented

- grok <medium> 1, the equal-time case. A probe answered AT the second its clock started (now == failing_since) is not
  "before" the failure, so it resets the clock. That is what the code does (`now >= fs`). It is now pinned by a test
  (test_a_late_probe_report_does_not_reset_a_newer_clock): an answer at the failure's own second resets. Mutation H2b
  (`now > fs`) is killed by it. The mutation check: 15 of 15 killed. 20 health tests pass.

## Recorded as a condition, not a defect

- grok <critical>: "pp-ingest's current calls pass no families, so its probe can claim a slot opened by the builder's
  deepseek failure, ask only qwen, and its answer resets the clock".
  - The reset is right under the ruling's first sentence: "'Down' means NO SUCCESSFUL ANSWER of any kind for 15
    minutes: any answered call OR answered probe resets the clock". A qwen answer is an answer of some kind. One model
    down is ruling 82's chain, not 'down'.
  - What is missing until pp-ingest updates is only that ITS probe does not ask the builder's failed family. The
    ruling asks for that; pp-ingest has adopted the API (its message, 10:2x ET): note(False, family=...) for each
    family that failed, probe_due(families=["glm", "muse", "qwen"]), and a probe that asks those three in parallel.
    Each new keyword is passed only when the loaded module's signature takes it. The watcher restarts on this commit's
    sha.
  - Making families required would be worse. A prober with the old API could then never claim while a family is
    recorded, so with the builder idle no one would probe, and the clock would run to plan_b on silence: the false
    outage again. families=None claims as before, by design (and tested).

## Refuted, with evidence from the code

- grok <medium> 1, its second half: "an unparseable failing_since_utc". _t returns None for a time it cannot parse or
  without a zone. An answer then clears the field (fs is None), and _down_rule never switches on it (fs is None). A bad
  field can only be cleared, never read as 'down'.
- grok <medium> 2: "a failure with family=None while the clock runs neither clears nor replaces failing_families". By
  design. The list is the families that failed on THIS clock; a failure that names no family adds none. A new clock
  starts the list afres

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1008/C2_STEP.diff (310 lines)
```
   1 | diff --git a/pipeline/heimdall_health.py b/pipeline/heimdall_health.py
   2 | index f76a69e..7509287 100644
   3 | --- a/pipeline/heimdall_health.py
   4 | +++ b/pipeline/heimdall_health.py
   5 | @@ -1,11 +1,17 @@
   6 |  """RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE. One shared 'Heimdall down' signal for the builder
   7 |  (verdicts and writes) and pp-ingest's watcher (the miner), kept in ONE JSON state file under an flock.
   8 |  
   9 | -- Heimdall is DOWN when NO Heimdall family answers a verdict or writer call inside its deadline for DOWN_AFTER_S (15
  10 | -  minutes) running: note(False) starts the clock (failing_since), any note(True) stops it. One model down is not
  11 | -  'down': that is ruling 82's chain, and any family's answer stops the clock.
  12 | -- While calls are failing, and while in Plan B, a cheap probe (probe_due / probe_result) runs every PROBE_EVERY_S
  13 | -  (2 minutes).
  14 | +- RULING 87 AMENDED (orchestrator 10:06 Nov 14, after the false outage of 09:16-09:22: one 502 on a calibration call,
  15 | +  then silence, and the clock ran while every probe was answering): Heimdall is DOWN when there is NO SUCCESSFUL
  16 | +  ANSWER OF ANY KIND for DOWN_AFTER_S (15 minutes) running. note(False) starts the clock (failing_since); an answered
  17 | +  call (note(True)) OR an answered probe (probe_result(True) while heimdall_first) resets it to zero. One model down is
  18 | +  not 'down': that is ruling 82's chain, and any family's answer resets the clock.
  19 | +- While the clock runs, and while in Plan B, the probe (probe_due / probe_result) goes every PROBE_EVERY_S (2
  20 | +  minutes), so one failed call followed by one good probe is never 'down'. A probe is a REAL model call on the family
  21 | +  that failed and one other, never a ping (the caller makes it: providers.Router.probe_once asks each of its Heimdall
  22 | +  families). note(False, family=...) records the failed family (failing_families, cleared by any answer); while the
  23 | +  clock runs, a prober that names its families (probe_due(families=...)) and can ask none of the failed ones leaves
  24 | +  the slot to the prober that can (the builder and pp-ingest call different families). In plan_b any prober claims.
  25 |  - Down: the mode is "plan_b" at once (the whole pin stage: Grok mainly, then any other outside key that answers).
  26 |    BACK: "heimdall_first" when the probe has answered BACK_AFTER (3) times in a row.
  27 |  - Every switch is recorded three times: in the state's "switches"; as a line {"kind": "switch", ...} in the
  28 | @@ -13,7 +19,7 @@
  29 |    physical line).
  30 |  
  31 |  The state file: {"mode": "heimdall_first" | "plan_b", "last_answer_utc", "failing_since_utc", "last_probe_utc",
  32 | -"probe_streak", "switches": [{"utc", "to", "why"}], "notes": n}. Times are ISO UTC. An unreadable state file is never
  33 | +"probe_streak", "failing_families": [...], "switches": [{"utc", "to", "why"}], "notes": n}. Times are ISO UTC. An unreadable state file is never
  34 |  'up' or 'down' by guess: note() / mode() raise HealthUnreadable (fail closed: the caller decides, and says so).
  35 |  CPU only; no model call here (the caller makes the probe call and reports it)."""
  36 |  import fcntl
  37 | @@ -132,10 +138,11 @@ def _prepend(state_md, head):
  38 |          pass
  39 |  
  40 |  
  41 | -def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", drill=False):
  42 | +def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", drill=False, family=None):
  43 |      """One Heimdall verdict or writer call's outcome: answered inside its deadline (True), or not (False: down,
  44 |      refused, empty, past the deadline). -> the mode after it. 15 minutes of failures with no answer: plan_b.
  45 |      drill=True (pp-ingest's outage drill, 21:4x Nov 13): recorded (drills, last_drill_utc), never counted.
  46 | +    family: the Heimdall family the call went to; a failure records it in failing_families (ruling 87 amended).
  47 |      An answer while all is well is written at most once per HEARTBEAT_S per process (a failure is always written)."""
  48 |      import time as _time
  49 |      now, mono = _now(now), _time.monotonic()
  50 | @@ -150,9 +157,12 @@ def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", d
  51 |              return s["mode"]
  52 |          s["notes"] = int(s.get("notes") or 0) + 1
  53 |          if answered:
  54 | -            s["last_answer_utc"], s["failing_since_utc"] = _iso(now), None
  55 | -        elif not s.get("failing_since_utc"):
  56 | -            s["failing_since_utc"] = _iso(now)
  57 | +            s["last_answer_utc"], s["failing_since_utc"], s["failing_families"] = _iso(now), None, []
  58 | +        else:
  59 | +            if not s.get("failing_since_utc"):
  60 | +                s["failing_since_utc"], s["failing_families"] = _iso(now), []
  61 | +            if family:
  62 | +                s["failing_families"] = sorted(set(_families(s)) | {str(family)})
  63 |          _down_rule(s, now, evidence, state_md, who)
  64 |          _save(path, s)
  65 |          with _SEEN_LOCK:
  66 | @@ -166,14 +176,15 @@ def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", d
  67 |  def _down_rule(s, now, evidence, state_md, who):
  68 |      fs = _t(s.get("failing_since_utc"))
  69 |      if s["mode"] == "heimdall_first" and fs is not None and (now - fs).total_seconds() >= DOWN_AFTER_S:
  70 | -        _switch(s, "plan_b", f"no Heimdall family answered inside its deadline for "
  71 | +        _switch(s, "plan_b", f"no answer of any kind (no call and no probe answered) for "
  72 |                               f"{int((now - fs).total_seconds() // 60)} minutes (since {_iso(fs)})", now, evidence,
  73 |                  state_md, who)
  74 |          s["probe_streak"] = 0
  75 |  
  76 |  
  77 |  def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
  78 | -    """The mode now (the 15-minute rule applied on the clock too, so an idle build still switches). -> mode."""
  79 | +    """The mode now (the 15-minute rule applied on the clock too, so an idle build still switches: no call and no
  80 | +    probe answered for 15 minutes; the probe goes every 2 minutes while the clock runs). -> mode."""
  81 |      now = _now(now)
  82 |      with _Locked(path):
  83 |          s = _load(path)
  84 | @@ -184,19 +195,30 @@ def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
  85 |          return s["mode"]
  86 |  
  87 |  
  88 | -def probe_due(path=STATE, now=None, who=""):
  89 | +def _families(s):
  90 | +    """The failed families on the running clock (a malformed field reads as none: no prober is kept out by it)."""
  91 | +    f = s.get("failing_families")
  92 | +    return [x for x in f if isinstance(x, str)] if isinstance(f, list) else []
  93 | +
  94 | +
  95 | +def probe_due(path=STATE, now=None, who="", families=None):
  96 |      """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old.
  97 |      A True CLAIMS the slot (last_probe_utc and last_probe_by stamped under the lock), so with several probers (this
  98 |      builder's router, pp-ingest's watcher) there is ONE probe per PROBE_EVERY_S slot, and "BACK_AFTER answers in a
  99 |      row" means that many slots (pp-ingest REQUESTS R12, 02:3x ET Nov 14). The next probe is due PROBE_EVERY_S after the
 100 |      later stamp: probe_result re-stamps last_probe_utc when the probe reports (answer-anchored), and a claimer that
 101 |      never reports leaves the slot spent from its claim (claim-anchored) (audit 0230 C1, glm). who names the claimer
 102 | -    (pp-ingest's watcher passes it from its next restart; "" until then)."""
 103 | +    (pp-ingest's watcher passes it from its next restart; "" until then). RULING 87 AMENDED (10:06 Nov 14): a probe is a
 104 | +    real model call on the family that failed: while the clock runs in heimdall_first, a prober whose `families` include
 105 | +    none of failing_families does not claim (the prober that can ask them does); families=None claims as before."""
 106 |      now = _now(now)
 107 |      with _Locked(path):
 108 |          s = _load(path)
 109 |          if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
 110 |              return False
 111 | +        failed = set(_families(s))
 112 | +        if families is not None and s["mode"] != "plan_b" and failed and not failed & set(families):
 113 | +            return False
 114 |          lp = _t(s.get("last_probe_utc"))
 115 |          if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S:
 116 |              return False
 117 | @@ -206,17 +228,23 @@ def probe_due(path=STATE, now=None, who=""):
 118 |  
 119 |  
 120 |  def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
 121 | -    """A probe's outcome (any Heimdall family answering it counts). BACK_AFTER answers in a row while in plan_b:
 122 | -    back to heimdall_first (the failure clock cleared). While not yet down, a probe answer is no verdict answer: the
 123 | -    15-minute clock runs on (the ruling counts verdict and writer calls). -> the mode after it."""
 124 | +    """A probe's outcome (any Heimdall family answering it counts). RULING 87 AMENDED (10:06 Nov 14): an answered probe
 125 | +    is an answer like an answered call, in both modes: it resets the clock (failing_since_utc, failing_families) and
 126 | +    stamps last_answer_utc (pp-ingest's ruling-98 route reads the clock as "no answer of any kind"). A probe answer
 127 | +    timed before the failure that started the clock (a report that arrives late) does not reset that clock. A failed
 128 | +    probe never starts the clock (note(False) does). plan_b closes on BACK_AFTER answers in a row, as before.
 129 | +    -> the mode after it."""
 130 |      now = _now(now)
 131 |      with _Locked(path):
 132 |          s = _load(path)
 133 |          s["last_probe_utc"] = _iso(now)
 134 |          s["probe_streak"] = int(s.get("probe_streak") or 0) + 1 if answered else 0
 135 | +        fs = _t(s.get("failing_since_utc"))
 136 | +        if answered and (fs is None or now >= fs):     # not a late report from before the clock started
 137 | +            s["last_answer_utc"], s["failing_since_utc"], s["failing_families"] = _iso(now), None, []
 138 |          if s["mode"] == "plan_b" and s["probe_streak"] >= BACK_AFTER:
 139 |              _switch(s, "heimdall_first", f"the probe answered {s['probe_streak']} times in a row", now, evidence,
 140 |                      state_md, who)
 141 | -            s["failing_since_utc"], s["probe_streak"] = None, 0
 142 | +            s["failing_since_utc"], s["failing_families"], s["probe_streak"] = None, [], 0
 143 |          _save(path, s)
 144 |          return s["mode"]
 145 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 146 | index 1161323..6dc0aee 100644
 147 | --- a/pipeline/providers.py
 148 | +++ b/pipeline/providers.py
 149 | @@ -1015,7 +1015,8 @@ class Router:
 150 |              return
 151 |          import heimdall_health as HH
 152 |          try:
 153 | -            HH.note(answered, self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid")
 154 | +            HH.note(answered, self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid",
 155 | +                    family=b.family)              # ruling 87 amended: the family a probe must ask
 156 |          except (HH.HealthUnreadable, OSError) as e:
 157 |              n = f"RULING 87: the Heimdall health state cannot be read or written: {e}"
 158 |              if n not in self.notices:
 159 | @@ -1036,7 +1037,8 @@ class Router:
 160 |          def loop():
 161 |              while True:
 162 |                  try:
 163 | -                    if HH.probe_due(self.health, who="pp-selectid probe"):     # claims the slot (one prober each)
 164 | +                    if HH.probe_due(self.health, who="pp-selectid probe",      # claims the slot (one prober each),
 165 | +                                    families=sorted({self.backends[n].family for n in fams})):   # 87 amended
 166 |                          HH.probe_result(self.probe_once(fams), self.health, evidence=self.deadline_log,
 167 |                                          state_md=self.state_md, who="pp-selectid probe")
 168 |                  except Exception:                      # noqa: BLE001 (the probe never stops a build)
 169 | diff --git a/tests/providers/test_heimdall_health.py b/tests/providers/test_heimdall_health.py
 170 | index de1ce34..410fba7 100644
 171 | --- a/tests/providers/test_heimdall_health.py
 172 | +++ b/tests/providers/test_heimdall_health.py
 173 | @@ -45,7 +45,8 @@ class TestHealth(unittest.TestCase):
 174 |              self.assertEqual([json.loads(x)["kind"] for x in f], ["switch"])
 175 |          first = open(self.md).read().split("\n")[0]
 176 |          self.assertTrue(first.endswith("| 21:00 ET: line one as it was."), first)     # one physical line, prepended
 177 | -        self.assertIn("ET: SWITCHED TO PLAN B (NO HEIMDALL FAMILY ANSWERED", first)
 178 | +        self.assertIn("ET: SWITCHED TO PLAN B (NO ANSWER OF ANY KIND (NO CALL AND NO PROBE ANSWERED) FOR 15 MINUTES",
 179 | +                      first)
 180 |  
 181 |      def test_one_answer_stops_the_clock(self):
 182 |          HH.note(False, **self.kw(T0))
 183 | @@ -54,6 +55,94 @@ class TestHealth(unittest.TestCase):
 184 |          self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=34))), "heimdall_first")
 185 |          self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=35))), "plan_b")   # idle: the clock still runs
 186 |  
 187 | +    def test_ruling_87_amended_an_answered_probe_resets_the_clock(self):
 188 | +        """RULING 87 AMENDED (10:06 Nov 14), the false outage of 09:16-09:22 replayed: one 502 at 14:01:08Z, then probes
 189 | +        answering every 2 minutes and no real call. 'Down' is no answer of ANY kind for 15 minutes."""
 190 | +        k = lambda m: self.kw(T0 + timedelta(minutes=m))
 191 | +        HH.note(False, **k(0))                                           # one failed call starts the clock
 192 | +        for m in range(2, 22, 2):
 193 | +            self.assertTrue(HH.probe_due(self.state, T0 + timedelta(minutes=m)) or m > 2)
 194 | +            self.assertEqual(HH.probe_result(True, **k(m)), "heimdall_first")
 195 | +            self.assertEqual(HH.mode(**k(m + 1)), "heimdall_first")
 196 | +        st = json.load(open(self.state))
 197 | +        self.assertIsNone(st["failing_since_utc"])                       # reset by the first good probe
 198 | +        self.assertEqual(st["last_answer_utc"], "2026-11-14T02:20:00Z")   # an answer of any kind
 199 | +        self.assertEqual(st["switches"], [])
 200 | +        self.assertFalse(HH.probe_due(self.state, T0 + timedelta(minutes=30)))     # no clock: no probe
 201 | +        self.assertEqual(open(self.md).read().split("\n")[0], "21:00 ET: line one as it was.")   # no switch line
 202 | +
 203 | +    def test_one_failed_call_then_one_good_probe_then_silence_is_never_down(self):
 204 | +        HH.note(False, **self.kw(T0))
 205 | +        self.assertEqual(HH.probe_result(True, **self.kw(T0 + timedelta(minutes=2))), "heimdall_first")
 206 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(hours=3))), "heimdall_first")
 207 | +
 208 | +    def test_failing_probes_leave_the_clock_running_and_a_failed_probe_never_starts_it(self):
 209 | +        self.assertEqual(HH.probe_result(False, **self.kw(T0)), "heimdall_first")
 210 | +        self.assertIsNone(json.load(open(self.state))["failing_since_utc"])   # only note(False) starts the clock
 211 | +        HH.note(False, **self.kw(T0))
 212 | +        for m in range(2, 16, 2):
 213 | +            self.assertEqual(HH.probe_result(False, **self.kw(T0 + timedelta(minutes=m))), "heimdall_first")
 214 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=15))), "plan_b")   # zero answers for 15 minutes
 215 | +        self.assertIn("NO ANSWER OF ANY KIND", open(self.md).read().split("\n")[0])
 216 | +
 217 | +    def test_a_late_probe_report_does_not_reset_a_newer_clock(self):
 218 | +        """pp-ingest reports a probe at its next tick with the probe's own time (up to PROBE_EVERY_S late): an answer
 219 | +        timed before the failure that started the clock proves nothing about after it."""
 220 | +        HH.note(False, **self.kw(T0 + timedelta(minutes=10)))
 221 | +        HH.probe_result(True, **self.kw(T0 + timedelta(minutes=9)))       # answered at 9, reported after the 10 failure
 222 | +        self.assertEqual(json.load(open(self.state))["failing_since_utc"], "2026-11-14T02:10:00Z")
 223 | +        HH.probe_result(True, **self.kw(T0 + timedelta(minutes=10)))      # answered AT the failure's second: not
 224 | +        self.assertIsNone(json.load(open(self.state))["failing_since_utc"])   # before it, so it resets (audit 1008 C1)
 225 | +        HH.note(False, **self.kw(T0 + timedelta(minutes=10)))
 226 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=25))), "plan_b")
 227 | +        HH.note(False, **self.kw(T0 + timedelta(minutes=40)))
 228 | +        HH.probe_result(True, **self.kw(T0 + timedelta(minutes=41)))      # in plan_b: one answer is a streak of 1,
 229 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=42))), "plan_b")   # back only after 3 (as before)
 230 | +
 231 | +    def test_in_plan_b_an_answered_probe_resets_the_clock_and_plan_b_still_needs_3_in_a_row(self):
 232 | +        """pp-ingest's ruling-98 route opens on plan_b AND failing_since_utc 20 minutes old (read as 'no answer of any
 233 | +        kind'): a probe answer at minute 17 of plan_b restarts that clock; closing plan_b stays at 3 answers in a row."""
 234 | +        k = lambda m: self.kw(T0 + timedelta(minutes=m))
 235 | +        HH.note(False, **k(0))
 236 | +        self.assertEqual(HH.mode(**k(15)), "plan_b")
 237 | +        HH.note(False, **k(16))                                          # still failing inside plan_b
 238 | +        self.assertEqual(HH.probe_result(True, **k(17)), "plan_b")
 239 | +        st = json.load(open(self.state))
 240 | +        self.assertEqual((st["failing_since_utc"], st["last_answer_utc"], st["probe_streak"]),
 241 | +                         (None, "2026-11-14T02:17:00Z", 1))
 242 | +        self.assertEqual(HH.probe_result(False, **k(19)), "plan_b")      # a miss: the streak is 0, the clock stays off
 243 | +        self.assertIsNone(json.load(open(self.state))["failing_since_utc"])   # (a failed probe never starts it)
 244 | +        HH.note(False, **k(20))                                           # a failed call starts it again
 245 | +        self.assertEqual(json.load(open(self.state))["failing_since_utc"], "2026-11-14T02:20:00Z")
 246 | +        self.assertEqual([HH.probe_result(True, **k(m)) for m in (21, 23, 25)], ["plan_b", "plan_b", "heimdall_first"])
 247 | +
 248 | +    def test_the_probe_asks_the_family_that_failed(self):
 249 | +        """RULING 87 AMENDED: a probe is a real model call on the family that failed. The builder's probe asks deepseek,
 250 | +        glm and qwen; pp-ingest's asks qwen, glm and muse. While the clock runs, a prober that can ask none of the
 251 | +        failed families leaves the slot to the one that can; in plan_b any prober claims (plan_b can always close)."""
 252 | +        at = lambda m: T0 + timedelta(minutes=m)
 253 | +        mine, theirs = ["deepseek", "glm", "qwen"], ["glm", "muse", "qwen"]
 254 | +        HH.note(False, family="muse", **self.kw(at(0)))                  # pp-ingest's muse 502
 255 | +        self.assertEqual(json.load(open(self.state))["failing_families"], ["muse"])
 256 | +        self.assertFalse(HH.probe_due(self.state, at(2), who="pp-selectid", families=mine))   # cannot ask muse
 257 | +        self.assertTrue(HH.probe_due(self.state, at(2), who="pp-ingest", families=theirs))
 258 | +        HH.note(False, family="deepseek", **self.kw(at(3)))              # then the builder's deepseek fails too
 259 | +        self.assertEqual(json.load(open(self.state))["failing_families"], ["deepseek", "muse"])
 260 | +        self.assertTrue(HH.probe_due(self.state, at(4), who="pp-selectid", families=mine))    # it can ask one
 261 | +        HH.probe_result(True, **self.kw(at(4)))                          # any answer: the clock and the families reset
 262 | +        st = json.load(open(self.state))
 263 | +        self.assertEqual((st["failing_since_utc"], st["failing_families"]), (None, []))
 264 | +        self.assertFalse(HH.probe_due(self.state, at(8), families=mine))  # no clock: no probe
 265 | +        HH.note(False, family="muse", **self.kw(at(10)))
 266 | +        self.assertTrue(HH.probe_due(self.state, at(12)))                # families not named: claims as before
 267 | +        HH.note(False, family="muse", **self.kw(at(25)))                 # nobody answered for 15 minutes: plan_b
 268 | +        self.assertEqual(HH.mode(**self.kw(at(25))), "plan_b")
 269 | +        self.assertTrue(HH.probe_due(self.state, at(26), who="pp-selectid", families=mine))   # plan_b: any prober
 270 | +        st = json.load(open(self.state))
 271 | +        st["mode"], st["failing_families"], st["failing_since_utc"] = "heimdall_first", "muse", "2026-11-14T02:30:00Z"
 272 | +        json.dump(st, open(self.state, "w"))                             # a malformed field keeps no prober out
 273 | +        self.assertTrue(HH.probe_due(self.state, at(31), families=mine))
 274 | +
 275 |      def test_the_probe_every_2_minutes_and_back_after_3_answers_in_a_row(self):
 276 |          k = lambda m: self.kw(T0 + timedelta(minutes=m))
 277 |          self.assertFalse(HH.probe_due(self.state, T0))                  # healthy: no probe
 278 | @@ -181,6 +270,23 @@ class TestRouterPlanB(unittest.TestCase):
 279 |          self.assertIn("heimdall:deepseek", r.down)                       # still down: marked as before
 280 |          self.assertFalse(os.path.exists(os.path.join(self.d.name, "rec")))   # a probe is never recorded
 281 |  
 282 | +    def test_the_probe_thread_names_its_families_to_the_slot_claim(self):
 283 | +        """RULING 87 AMENDED: the builder's probe asks its own Heimdall families, and says which to probe_due."""
 284 | +        import time as _t
 285 | +        from unittest import mock
 286 | +        r, seen = self.router(), []
 287 | +
 288 | +        def due(path, now=None, who="", families=None):
 289 | +            seen.append((who, families))
 290 | +            return False
 291 | +        with mock.patch.object(HH, "probe_due", due):
 292 | +            P.Router.start_probe(r, every_s=3600.0)       # one look, then an hour asleep (a daemon thread)
 293 | +            for _ in range(200):
 294 | +                if seen:
 295 | +                    break
 296 | +                _t.sleep(0.01)
 297 | +        self.assertEqual(seen, [("pp-selectid probe", ["deepseek"])])
 298 | +
 299 |      def test_a_failing_heimdall_call_is_noted_as_not_answered(self):
 300 |          r = self.router()
 301 |  
 302 | @@ -191,6 +297,7 @@ class TestRouterPlanB(unittest.TestCase):
 303 |          st = json.load(open(self.state))
 304 |          self.assertIsNotNone(st["failing_since_utc"])
 305 |          self.assertIsNone(st["last_answer_utc"])
 306 | +        self.assertEqual(st["failing_families"], ["deepseek"])          # ruling 87 amended: the family to probe
 307 |  
 308 |  
 309 |  
 310 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence of calls that breaks it.

BACKGROUND (static):
- pipeline/heimdall_health.py keeps ONE shared "Heimdall down" signal in a JSON state file under an flock, for two
  processes: this builder's model router (providers.Router) and another team's miner (pp-ingest's watcher, which loads
  this module BY PATH from this worktree and calls only note, mode, probe_due, probe_result). Heimdall is a model gateway
  with several model families (deepseek, glm, qwen, ...). "plan_b" sends the builder's verdict calls to outside vendors
  (Grok first); "heimdall_first" uses Heimdall's families first.
- The clock: note(False) (a call that failed) starts it (failing_since_utc); note(True) (an answered call) clears it.
  mode() and note() apply _down_rule: when the clock has run DOWN_AFTER_S (15 min), the mode switches to plan_b and the
  switch is written to the state, an evidence file, and STATE line 1. In plan_b, probe_result counts answers in a row;
  BACK_AFTER (3) in a row switches back to heimdall_first. probe_due() returns True (and claims the 2-minute slot) only
  while the clock runs or the mode is plan_b.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- heimdall_health._Locked (class at :82) serialises every read-modify-write of the state with fcntl.flock; _load (:61)
  raises HealthUnreadable on an unreadable state (:72), never a guess.
- heimdall_health._t parses an ISO time and returns None for a time without a zone; _iso writes "%Y-%m-%dT%H:%M:%SZ".
- providers.Router._note (providers.py:1009) notes ONLY HeimdallBackend calls of the verdict roles and "angle_write";
  their chains use only the families deepseek, glm and qwen (nemotron appears only in visual_check, not a noted role).
  On a failure it starts the probe thread (start_probe, :1026).
- providers.Router.start_probe / probe_once (:1026-:1066): while HH.probe_due(...) (:1039) claims a slot, it asks EACH
  of its Heimdall families deepseek, glm and qwen (:1033) a real one-word model call ("Reply with the single word OK.",
  60 s each, never served from a recording) and reports HH.probe_result(any answered) (:1040) at the current time.
- pp-ingest's watcher (pipeline/ingest/downsignal.py in its own worktree) reports a finished probe at its next tick
  with the probe's OWN time: probe_result(answered, now=<probe finish time>, ...) (downsignal.py:338), up to
  PROBE_EVERY_S late; its notes too carry their own times (:297).

THE ORCHESTRATOR'S RULING (10:06 ET Nov 14), verbatim:
"RULING 87 AMENDED (the false outage of 09:16-09:22: one 502 on a calibration call, then silence, and the clock ran while
every probe was answering). 'Down' means NO SUCCESSFUL ANSWER of any kind for 15 minutes: any answered call OR answered
probe resets the clock to zero. While the clock is running the probe goes every 2 minutes, so a single failed call
followed by one good probe is never 'down'. A probe must be a real model call on the family that failed (and one
other), not a ping. Plan B opens only when the clock reaches 15 minutes with zero answers; it closes on 3 good probes as
now. Every switch still goes on line 1 in capitals; a switch later found false is marked so, as pp-ingest did (well
reported). The clock lives in your module: fix it there (audited, small), tell pp-ingest when it is live."

THE CHANGE (the diff follows):
1. probe_result: an ANSWERED probe is an answer like an answered call, IN BOTH MODES: it resets the clock
   (failing_since_utc None, failing_families []) and stamps last_answer_utc. pp-ingest's watcher opens its paid route
   (its ruling 98) on mode == plan_b AND failing_since_utc 20 minutes old, reading that field as "no answer of any kind",
   so a probe answer inside plan_b must restart it. A probe answer timed BEFORE the failure that started the clock (a
   late report) does not reset that clock. A failed probe never starts the clock (only note(False) does), as before.
   plan_b still closes only on 3 answers in a row. Before this change, a probe answer did not count while heimdall_first
   (the clock ran on: the false outages of 09:16 and 10:12 ET).
2. "A probe must be a real model call on the family that failed (and one other)": note(False, family=...) records the
   failed family in the state (failing_families: the families whose failures are on the running clock; a new clock
   starts the list afresh; any answer clears it). probe_due(families=[...]): while the clock runs in heimdall_first, a
   prober that can ask NONE of the failed families does not claim the slot, so the prober that can (the other process)
   does; families=None claims as before; in plan_b any prober claims (plan_b can always close). A malformed
   failing_families field reads as none (no prober is kept out by it). The builder calls deepseek, glm and qwen; pp-ingest
   calls qwen, glm and muse: each side's probe asks every family it calls.
3. providers.Router passes family=b.family to note() and families=<its probe's families> to probe_due().
4. The switch reason now reads "no answer of any kind (no call and no probe answered) for N minutes (since T)".
5. Tests: the 09:16 outage replayed (probes answering every 2 minutes); one failed call then one good probe then 3 hours
   of silence; failing probes leave the clock running; a late report does not reset a newer clock; inside plan_b an
   answered probe resets the clock and plan_b still needs 3 in a row; the failed family steers the slot claim (and plan_b
   lets any prober claim; a malformed field keeps no prober out); the Router passes its family and its probe's families.
   20 tests pass; 14 mutations, each killed.

ATTACK:
(a) Can a single failed call followed by one good probe still end in plan_b? Can 15 minutes of failed calls AND failed
    probes fail to open plan_b?
(b) The late-report guard (now >= failing_since): can it drop a genuine answer, or let a stale one reset a newer clock?
    Equal times? A state whose failing_since_utc cannot be parsed?
(c) Any interaction with plan_b's 3-in-a-row rule, the probe slot claim (probe_due), the heartbeat cache in note()
    (_SEEN), or the two processes writing the same file?
(d) Does anything here let the builder or pp-ingest read 'up' or 'down' by guess, or change what pp-ingest's calls do?
(e) "A probe must be a real model call on the family that failed (and one other)": can a slot be spent on a probe that
    asks none of the failed families while a prober that can ask them is alive? Can the families rule leave plan_b, or
    a running clock, with no prober at all? What must pp-ingest's side do?
(f) An older state file (no failing_families key) or pp-ingest's current calls (no family, no families): unchanged?

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".


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
