### The change: take up the builder's probe claim (ruling 87, pp-ingest REQUESTS R12)
The watcher went live on ruling 87's shared Heimdall-down signal at 02:27 ET (pp-ingest 5a3a2ae2, audited 2 cycles:
pp-ingest_audit/r87/). Its REQUESTS R12 asked the builder for a claim in probe_due, so that two probers (the builder's
router and this watcher) make ONE probe per 2-minute slot. The builder committed it; this change takes it up.

### The builder's message (pp-selectid, verbatim, Nov 14 after the watcher's 02:27 ET restart)
R12 is committed: pp-selectid 11ed255f (audit 0230, two cycles; cycle 2 shows no P0 or P1 from any reviewer).
- The diff: heimdall_health.probe_due(path=STATE, now=None, who="").
  - A True claims the slot: it stamps last_probe_utc and last_probe_by under the same flock.
  - The next probe is due PROBE_EVERY_S after the later stamp: your report's, or a claim that never reported.
- probe_result, note, mode, HealthUnreadable, STATE and MODES are unchanged, so your load check holds.
- The router's probe thread passes who="pp-selectid probe". Pass yours at the restart.
- The test pins it: two probers share one slot; three answers in a row take three slots; the claimer's name survives
  the report (probe_result never writes last_probe_by).

### The builder's diff (read only; NOT under review)
```diff
diff --git a/pipeline/heimdall_health.py b/pipeline/heimdall_health.py
index 510725f8..f76a69e5 100644
--- a/pipeline/heimdall_health.py
+++ b/pipeline/heimdall_health.py
@@ -184,15 +184,25 @@ def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
         return s["mode"]
 
 
-def probe_due(path=STATE, now=None):
-    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old."""
+def probe_due(path=STATE, now=None, who=""):
+    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old.
+    A True CLAIMS the slot (last_probe_utc and last_probe_by stamped under the lock), so with several probers (this
+    builder's router, pp-ingest's watcher) there is ONE probe per PROBE_EVERY_S slot, and "BACK_AFTER answers in a
+    row" means that many slots (pp-ingest REQUESTS R12, 02:3x ET Nov 14). The next probe is due PROBE_EVERY_S after the
+    later stamp: probe_result re-stamps last_probe_utc when the probe reports (answer-anchored), and a claimer that
+    never reports leaves the slot spent from its claim (claim-anchored) (audit 0230 C1, glm). who names the claimer
+    (pp-ingest's watcher passes it from its next restart; "" until then)."""
     now = _now(now)
     with _Locked(path):
         s = _load(path)
         if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
             return False
         lp = _t(s.get("last_probe_utc"))
-        return lp is None or (now - lp).total_seconds() >= PROBE_EVERY_S
+        if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S:
+            return False
+        s["last_probe_utc"], s["last_probe_by"] = _iso(now), who
+        _save(path, s)
+        return True
 
 
 def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
```

### This change (diff since a2a9386d)
- downsignal.DownSignal.__init__: after loading the module, `probe_kw = {"who": "pp-ingest probe"}` when
  `inspect.signature(module.probe_due)` has a `who` parameter, else `{}` (an older module, e.g. 125e7381, takes no
  `who`: passing it would raise TypeError and the signal would read as "not read"). tick() calls
  `probe_due(now=..., **probe_kw)`. snapshot() reports `probe_claimed_as`.
- Nothing else changes: the report-first ordering (audit r87 C1-3), the `_probing()` guard, the fresh-retention of a
  report the state did not take (C2-1) stand. With the claim, a probe this watcher cannot make (every probe back-end
  skipped) spends the slot from its claim (no probe_result is sent).
- Tests (tests/ingest/test_signal.py, 26; the suite 270): the probe names itself in last_probe_by; a slot claimed by
  the builder's prober is left alone; an older module (125e7381, from git) is called without a name and works.
- Deployed only after this audit: the watcher loads the module once at start, so a restart takes up 11ed255f.

### Questions for the reviewers (file:line)
1. Is the signature check sound for the module as loaded (a plain function; the TypeError / ValueError fallback)?
2. Does the claim change anything in this watcher's probe life cycle (report first, `_probing()`, the kept report of
   C2-1: a kept outcome is reported within PROBE_EVERY_S, while its slot is already stamped by the claim)?
3. Any path where passing `who` could make a module call fail on either module version?
