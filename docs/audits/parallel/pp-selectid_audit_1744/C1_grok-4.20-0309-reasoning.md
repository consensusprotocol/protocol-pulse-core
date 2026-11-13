# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 32 s finish=stop usage in 20964 / out 259 usd~0.111 (upper-bound price)

**P0 findings:** none verifiable from diff.  
**P1 findings:** none verifiable from diff.  
**P2 findings:** none verifiable from diff (all four requested checks hold exactly: build+apply+pin_problems gate every non-(pass/adopt) text before any seal (package.py:277,312,338; proof_ledger.py:406; lock_precheck.py:206,229); adopt_spoken only reaches apply when this side's AT.carry_class returns non-None for every op and is sealed with attested record (lock_precheck.py:149,187,218; package_pin.py:374; test confirms seal hash changes); error/None outcome always produces verdict=error, ok=False, lock_stop+budget, never a package (lock_precheck.py:131,164,181; package.py:321,351); matching uses only ruling-72 entries, newest by (at,k), 3-decimal window+role+approved_text+TRIM fields exactly per contract (lock_precheck.py:47,85,91,74); send is atomic .tmp-then-rename, rejects existing or bad ID_RE chars (lock_precheck.py:115,120); seal() and all other gates untouched per diff).  

SHIP: yes