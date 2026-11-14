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