# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0230
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 112 s finish=stop usage in 5717 / out 3449 usd~0.069 (upper-bound price)

<medium> heimdall_health.py:26 — the claim stamps `last_probe_utc = now` at *claim* time, while `probe_result` (unchanged, line 31) later stamps `last_probe_utc` again when the probe *ends*. Between the two, the slot is already spent, so the effective probe period is `PROBE_EVERY_S + probe duration`, not `PROBE_EVERY_S`. Concrete scenario: probe takes 30 s (network timeout); a probe due at T=0 is claimed at T=0, ends at T=0:30; the next slot opens at T=120 (from the claim), not T=120 from the answer — the "every 2 minutes" cadence drifts by the probe duration each cycle. Not a regression (the old code had the same drift via `probe_result`'s stamp), and the docstring (lines 13–15) declares this ("A claimer that never reports leaves the slot spent: the next probe is due PROBE_EVERY_S later"), so it's a documented, accepted behaviour, not a defect. — but note the *streak* semantics: if the probe answers at T=0:30, the next due is T=120, so "3 in a row" = 3 slots ≈ 6+ minutes, consistent with the ruling's intent. No break found.

<medium> heimdall_health.py:26 — `_save(path, s)` is called even when the claim is a *repeat* claim by the same prober. Concrete scenario: the router's thread calls `probe_due` at T=0 (claims, saves), then the probe thread's next iteration at T=0.1 s (before `probe_result` runs) — wait, no: the second call at T=0.1 finds `lp = 0` and `(0.1 - 0) < 120`, returns False without saving. So no double-save. No break found; the lock covers read+stamp+save (lines 18–28, inside `with _Locked(path)`), so two concurrent callers cannot both see a stale `last_probe_utc`. One caveat I cannot verify from the diff: whether `_Locked` is re-entrant or whether `_save` itself takes the lock (if `_save` re-locks, a non-re-entrant flock would deadlock — but the unchanged `probe_result` presumably already calls `_save` under the lock, so this is pre-existing, not introduced).

<medium> heimdall_health.py:26 — `who` defaults to `""`, and the diff shows the router passes `who="pp-selectid probe"` (providers.py:41), but the diff does not show pp-ingest's watcher call site (external repo, loaded by path). If pp-ingest calls `probe_due(path)` without `who`, the state records `last_probe_by = ""` — cosmetic only (the slot is still claimed; the *stamp* is what enforces exclusivity), so no functional break, but the audit trail ("who claimed") is lost for that prober. Cannot verify pp-ingest's call site from this diff; flagging as unverifiable, not a defect.

<medium> heimdall_health.py:24–25 — the early-return-False path (slot taken) does not save, which is correct; but note the *mode* check at line 20 (`if s["mode"] != "plan_b" and not s.get("failing_since_utc"): return False`) also returns False without saving — correct, no claim is made when no probe is due, so a healthy-mode caller doesn't burn the slot. Good.

<medium> tests/providers/test_heimdall_health.py:60–72 — the test's `at(m)` lambda (line 59) shadows nothing, but note `k(m)` (line 56) vs `at(m)` (line 59) are *different* lambdas: `k(m)` = `T0 + timedelta(minutes=m)` passed as `**k(0)` → `now=T0+0m` into `HH.note`, while `at(m)` = same expression but passed positionally as `now`. Both produce the same timestamps, so the test is consistent; the duplication is stylistic. However, line 66–72: `rounds = 1` then the loop over `(18, 20)` increments to 3 — this hard-codes that the *first* answer at minute 16 (line 63) counts as answer #1 of the 3-in-a-row, and minutes 18 and 20 give answers #2 and #3, so `probe_result(True, **k(m))` at 18 and 20 → mode flips to `heimdall_first` at the third consecutive True. This matches BACK_AFTER=3. But the test asserts `mode == "heimdall_first"` only at the *end* (line 72) — it does not assert the mode is still `plan_b` after the *second* answer (minute 18), so a regression that flips after 2 answers would pass this test. Minor test-coverage gap, not a code defect.

<medium> tests/providers/test_heimdad_health.py:74 — (typo in my reading, file is `test_heimdall_health.py`) — the next test (line 74) calls `HH._SEEN.clear()` but the new test (lines 53–72) does not; if `HH._SEEN` is module-level and `note()`/`probe_result()` use it for dedup ("answers write once per heartbeat" per line 75's docstring), the new test's `probe_result(True, **k(16))` at line 63 and `probe_result(True, **tag m)` at line 71 could be deduped by `_SEEN` if they share a key. Cannot verify `_SEEN`'s keying from the diff (the diff doesn't show `note`/`probe_result` bodies), so: if `_SESEEN` dedups by (who, minute) or similar, the second `probe_result(True, **k(18))` might be a no-op and the mode would never flip — the test would fail, which the author presumably ran, so likely `_SEEN` keys on something the test varies. Unverifiable from the diff; flagging for the author to confirm. — Actually, since the test presumably passes (it's in the diff as

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 46 s finish=stop usage in 5848 / out 124 usd~0.032 (upper-bound price)

<critical>: None verifiable from diff.
<high>: None verifiable from diff.
<medium>: None verifiable from diff (read+claim under single _Locked at heimdall_health.py:18-28 preserves 15-min rule at:20, yields exactly one True per slot (test at test_heimdall_health.py:60 with at(16) for ("pp-selectid","pp-ingest")), never-reporter limited to one PROBE_EVERY_S slot via last_probe_utc set at:26 before return, 3-in-row logic and other state keys untouched in visible paths).
SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 22 s finish=stop usage in 6152 / out 1648 usd~0.043 (upper-bound price)

I have reviewed the diff against the stated defect, the governing laws, and the specific check criteria.

### Findings

**<medium> `pipeline/heimdall_health.py:26-27` — State mutation on read path**
The function `probe_due` is semantically a "check" (predicate), but the change makes it a "claim" (action) that mutates persistent state (`last_probe_utc`, `last_probe_by`) and writes to disk (`_save`).
*   **Scenario:** If a caller invokes `probe_due` to check eligibility but fails to subsequently call `probe_result` (e.g., due to an exception in the caller's logic before the probe executes, or a process crash between the claim and the execution), the slot is marked as "spent" (`last_probe_utc` is updated) but no probe result is recorded.
*   **Impact:** The next probe will not be due for another `PROBE_EVERY_S` (2 minutes). This effectively "eats" a probe cycle. While the prompt states "A claimer that never reports leaves the slot spent," this is a significant behavioral change for a function named `probe_due`. It reduces the frequency of health checks in failure scenarios. If the system is in `plan_b` and a prober crashes after claiming, the other prober cannot probe for 2 minutes. This is acceptable per the "one probe per slot" requirement but is a side-effect that should be documented more prominently or the function renamed to `claim_probe_slot` to reflect its imperative nature.

**<low> `pipeline/heimdall_health.py:11` — Default argument `who=""`**
The new parameter `who` defaults to an empty string.
*   **Scenario:** If a legacy caller or a new caller forgets to pass `who`, the state will record `last_probe_by: ""`.
*   **Impact:** This makes debugging "who claimed the slot" impossible for that instance. The test `test_two_probers_share_one_probe_per_slot` correctly passes `who`, but the production code in `providers.py:41` also passes it. However, `pp-ingest` (external repo) must be updated to pass `who`. If `pp-ingest` is not updated simultaneously, it will claim slots with `who=""`, potentially causing confusion in the state file. This is a coordination risk, not a code defect in this diff, but worth noting.

**<low> `tests/providers/test_heimdall_health.py:60` — Test relies on specific timing**
The test uses `T0 + timedelta(minutes=16)` for the first claim and `T0 + timedelta(minutes=17)` for the second check.
*   **Scenario:** `PROBE_EVERY_S` is 120 seconds (2 minutes).
    *   `note(False, **k(15))` sets `failing_since_utc` to T0+15m.
    *   `probe_due` at T0+16m: `now - lp` (where `lp` is likely None or old) >= 120s? Yes. Claims slot. `last_probe_utc` = T0+16m.
    *   `probe_due` at T0+17m: `now - lp` = 1 minute = 60s. 60s < 120s. Returns False. Correct.
    *   `probe_result` at T0+16m (simulating the probe finishing). Note: `probe_result` also updates `last_probe_utc`? The prompt says "probe_result (unchanged) still stamps last_probe_utc when the probe ends."
    *   Wait, if `probe_result` stamps `last_probe_utc` to T0+16m (or slightly later), and the next `probe_due` is at T0+18m:
        *   `now` = T0+18m. `lp` = T0+16m (from claim) or T0+16m+epsilon (from result).
        *   `now - lp` = 2 minutes = 120s.
        *   Condition: `if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S: return False`.
        *   120 < 120 is False. So it proceeds to claim.
    *   The test asserts `probe_due` at T0+18m returns True. This works if the timestamp is exactly T0+16m. If `probe_result` adds a small delay (e.g., T0+16m+1s), then at T0+18m, `now - lp` = 119s, which is < 120s, so it would return False.
    *   **Risk:** The test might be flaky if `probe_result` updates the timestamp to a value slightly later than the claim time, or if the system clock has any drift. The test uses `at(18)` which is exactly 2 minutes after `at(16)`. If `probe_result` sets `last_probe_utc` to the *current* time when it is called (which might be `at(16)` in the test's mocked time, or real time?), the test mocks `now` for `probe_due` but does it mock `now` for `probe_result`?
    *   Looking at the test: `HH.probe_result(True, **k(16))`. `k(16)` passes `now=T0+16m`. So `probe_result` sets `last_probe_utc` to T0+16m.
    *   Then `probe_due` at `at(18)` (T0+18m). `now - lp` = 120s. `120 < 120` is False. So it claims.
    *   This is correct but relies on exact equality. If `PROBE_EVERY_S` was 121s, it would fail. It is tight but correct for the defined constant.

**<info> Compliance with Governing Laws**
*   **LAW 20 / M2:** No gate thresholds changed. No reclassification.
*   **M12 FAIL CLOSED:** The change does not introduce a path where missing data leads to a pass. It leads to a "slot spent" (no probe), which is a conservative failure (less frequent probing) rather than a false positive (probing too often).
*   **Smallest diff:** The diff is minimal and focused.

### SHIP: yes with conditions

**Conditi

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0230 (pp-ingest R12: probe_due claims the slot), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes (no finding); qwen3.8-27b SHIP yes with conditions; glm-5.3-flash SHIP yes with
conditions. No critical, no high.

- Condition, qwen and glm: pp-ingest should pass a non-empty `who`. MET by pp-ingest's own message (02:3x ET):
  - its watcher loads the module once at start and passes who="pp-ingest probe" from the restart that takes this
    commit (a two-line change, audited on its side);
  - until then the claim works with who="" (the argument is optional).
- Condition, glm: say what anchors the next due time. IMPLEMENTED in probe_due's docstring:
  - the later stamp decides;
  - probe_result re-stamps last_probe_utc when the probe reports (answer-anchored);
  - a claimer that never reports leaves its claim's stamp (claim-anchored).
  The behaviour is unchanged.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0230/C2_STEP.diff (79 lines)
```
   1 | diff --git a/pipeline/heimdall_health.py b/pipeline/heimdall_health.py
   2 | index 510725f..f76a69e 100644
   3 | --- a/pipeline/heimdall_health.py
   4 | +++ b/pipeline/heimdall_health.py
   5 | @@ -184,15 +184,25 @@ def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
   6 |          return s["mode"]
   7 |  
   8 |  
   9 | -def probe_due(path=STATE, now=None):
  10 | -    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old."""
  11 | +def probe_due(path=STATE, now=None, who=""):
  12 | +    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old.
  13 | +    A True CLAIMS the slot (last_probe_utc and last_probe_by stamped under the lock), so with several probers (this
  14 | +    builder's router, pp-ingest's watcher) there is ONE probe per PROBE_EVERY_S slot, and "BACK_AFTER answers in a
  15 | +    row" means that many slots (pp-ingest REQUESTS R12, 02:3x ET Nov 14). The next probe is due PROBE_EVERY_S after the
  16 | +    later stamp: probe_result re-stamps last_probe_utc when the probe reports (answer-anchored), and a claimer that
  17 | +    never reports leaves the slot spent from its claim (claim-anchored) (audit 0230 C1, glm). who names the claimer
  18 | +    (pp-ingest's watcher passes it from its next restart; "" until then)."""
  19 |      now = _now(now)
  20 |      with _Locked(path):
  21 |          s = _load(path)
  22 |          if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
  23 |              return False
  24 |          lp = _t(s.get("last_probe_utc"))
  25 | -        return lp is None or (now - lp).total_seconds() >= PROBE_EVERY_S
  26 | +        if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S:
  27 | +            return False
  28 | +        s["last_probe_utc"], s["last_probe_by"] = _iso(now), who
  29 | +        _save(path, s)
  30 | +        return True
  31 |  
  32 |  
  33 |  def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
  34 | diff --git a/pipeline/providers.py b/pipeline/providers.py
  35 | index aa5474b..1161323 100644
  36 | --- a/pipeline/providers.py
  37 | +++ b/pipeline/providers.py
  38 | @@ -1036,7 +1036,7 @@ class Router:
  39 |          def loop():
  40 |              while True:
  41 |                  try:
  42 | -                    if HH.probe_due(self.health):
  43 | +                    if HH.probe_due(self.health, who="pp-selectid probe"):     # claims the slot (one prober each)
  44 |                          HH.probe_result(self.probe_once(fams), self.health, evidence=self.deadline_log,
  45 |                                          state_md=self.state_md, who="pp-selectid probe")
  46 |                  except Exception:                      # noqa: BLE001 (the probe never stops a build)
  47 | diff --git a/tests/providers/test_heimdall_health.py b/tests/providers/test_heimdall_health.py
  48 | index e47a60c..8cfeff4 100644
  49 | --- a/tests/providers/test_heimdall_health.py
  50 | +++ b/tests/providers/test_heimdall_health.py
  51 | @@ -73,6 +73,27 @@ class TestHealth(unittest.TestCase):
  52 |          self.assertIn("BACK TO HEIMDALL-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW)",
  53 |                        open(self.md).read().split("\n")[0])
  54 |  
  55 | +    def test_two_probers_share_one_probe_per_slot(self):
  56 | +        """pp-ingest REQUESTS R12 (02:3x ET Nov 14): this router's probe and pp-ingest's watcher probe the same state;
  57 | +        a due probe is CLAIMED, so one slot gives one probe and 3 in a row is 3 slots."""
  58 | +        k = lambda m: self.kw(T0 + timedelta(minutes=m))
  59 | +        HH.note(False, **k(0))
  60 | +        HH.note(False, **k(15))                                          # down: plan_b
  61 | +        at = lambda m: T0 + timedelta(minutes=m)
  62 | +        self.assertEqual([HH.probe_due(self.state, at(16), who=w) for w in ("pp-selectid", "pp-ingest")],
  63 | +                         [True, False])                                  # the second prober finds the slot taken
  64 | +        self.assertEqual(json.load(open(self.state))["last_probe_by"], "pp-selectid")
  65 | +        HH.probe_result(True, **k(16))
  66 | +        self.assertEqual([HH.probe_due(self.state, at(17), who=w) for w in ("pp-selectid", "pp-ingest")],
  67 | +                         [False, False])
  68 | +        rounds = 1
  69 | +        for m in (18, 20):
  70 | +            claims = [HH.probe_due(self.state, at(m), who=w) for w in ("pp-ingest", "pp-selectid")]
  71 | +            self.assertEqual(claims, [True, False])
  72 | +            rounds += 1
  73 | +            mode = HH.probe_result(True, **k(m))
  74 | +        self.assertEqual((rounds, mode), (3, "heimdall_first"))         # three slots, three answers
  75 | +
  76 |      def test_a_drill_is_recorded_never_counted_and_answers_write_once_per_heartbeat(self):
  77 |          HH._SEEN.clear()
  78 |          for m in range(0, 40, 5):                                        # 40 minutes of drill failures
  79 | 
```

---

You are auditing a SMALL change on branch pp-selectid (Protocol Pulse). Only state what you can verify from the diff;
if uncertain, say so; do not guess. Be specific: file:line and a concrete input that breaks it.

Background (static): RULING 87 (Plan B): Heimdall is "down" after 15 minutes with no Heimdall family answering;
while calls fail or the mode is plan_b, a cheap health probe runs every 2 minutes (PROBE_EVERY_S); "Return to
Heimdall-first when its probe has answered 3 times in a row" (BACK_AFTER). pipeline/heimdall_health.py keeps the
state in one JSON file under an flock; TWO processes now probe it: this builder's Router probe thread and pp-ingest's
watcher (another repo, loading this module by path).

The defect (pp-ingest's REQUESTS R12): probe_due() only READ the slot, so both probers could probe in one 2-minute
slot. Then "3 in a row" could come from fewer than 3 slots, and one prober's failure reset the other's streak.

The change: probe_due(path, now, who="") CLAIMS the slot when it returns True: under the same lock, last_probe_utc =
now and last_probe_by = who are saved, so a second prober in the same slot gets False. probe_result (unchanged) still
stamps last_probe_utc when the probe ends. The router's probe thread passes who="pp-selectid probe". A test has two
probers share one slot and needs three slots for three answers in a row.

Check: that one slot yields exactly one True across callers (the read and the stamp are under one lock); that the
existing 15-minute rule and the 3-in-a-row return are unchanged; that a claimer that never reports cannot block
probing for more than one slot; that nothing else in the state changes. Answer with findings tagged <critical>,
<high>, <medium> (file:line, a concrete scenario), then "SHIP: yes / no / yes with conditions".


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
