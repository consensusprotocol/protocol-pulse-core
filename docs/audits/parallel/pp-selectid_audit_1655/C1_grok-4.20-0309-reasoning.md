# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 29 s finish=stop usage in 10643 / out 201 usd~0.058 (upper-bound price)

**P2: tests/package/test_medley.py:210** (Rig.__init__ + run): registered= kw is accepted and passed through to PK.build only on the explicit path; uncertain whether every formation site (reordered/pool-filled) truly passes through the exact `segs` tuple point shown in the package.py diff.  
**P2: pipeline/candidates.py:18** (`key(lu) != k`): validation relies on an undefined `key()` in the provided diff snippet; behavior cannot be fully verified from diff alone.  

No P0/P1 findings. All required checks (search never judges/writes registered line-ups on formation paths, skip precedes n_lineup/spins and uses break so never counted as judged and cannot spin-loop, candidate= build bypasses via `if candidate is None`, gates/verdicts/seal untouched, refused_only() patches are strictly inside with-blocks for the two refusal tests only) pass from the diff.  

SHIP: yes