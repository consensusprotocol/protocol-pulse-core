# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 44 s finish=stop usage in 8241 / out 144 usd~0.045 (upper-bound price)

**P0: None**  
**P1: None**  
**P2: None** (all four mandated checks are directly verifiable from the diff and pass: lineup_for is invoked unchanged on the extended list so every rule applies; own moments are placed first in their original relative order before any pool additions and the test asserts the selected segs respect that prefix; the fill block guards on `n_lineup == 0` and passes the supplied `dropped | doomed` set through; placement() reproduces exactly the two conditions that lineup_for itself uses for LAST-only and hook eligibility). No loops, no uncontrolled combinatorial growth (rest list is built once, lineup_for called at most twice).  

SHIP: yes