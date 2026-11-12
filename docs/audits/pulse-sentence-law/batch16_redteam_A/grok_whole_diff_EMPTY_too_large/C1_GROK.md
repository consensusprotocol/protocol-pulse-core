**Q1: CORRECTNESS**  
No diff is present in the package. Nothing can be verified about function behavior, time/index handling, units, comparisons, exceptions, or state leakage.

**Q2: LAW COMPLIANCE**  
No diff lines exist, so every law (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-i, LAW 20/M2, M12, LAW 22) is marked UNCERTAIN. No evidence that cuts stay inside locked silence, that expected words are never recomputed, or that thresholds are unchanged.

**Q3: TESTS**  
No test files or diff lines are shown. Cannot confirm must-fail fixtures fail for the stated reason or that controls pass for the right reason. No assertions can be inspected for vacuous passes.

**Q4: VERDICT**  
- SEVERITY: BLOCKER | diff line: (none) | issue: no staged diff supplied | fix: provide the exact commit diff  
- SEVERITY: BLOCKER | diff line: (none) | issue: all laws and checks unverifiable | fix: supply the diff before review  

**NOT READY**