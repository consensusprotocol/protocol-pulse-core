**CYCLE 2 REVIEW — pulse-sentence-law**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
- The D4 credits/avatar-warp defect (still present; only made visible via verify_pack contact sheets).  
- The value of structured logging on the `"uncertain"` path (vertical_layout.py:1818) so the gate report itself surfaces it.  
- Depth of the ffmpeg 4.x xfade offset fix (transitions.py:1570-1574) and its frame-lock guarantee.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- **MF-1 (uncertain label)**: Agree. Logging is the minimal, zero-risk improvement.  
- **MF-2 (D4 credits)**: Partially agree. The verify_pack workaround is intentional interim control; the underlying reframe path for credits is correctly left out of this diff.  
- Overall READY verdict: Full agreement across all four models.

**3. NEW FINDINGS FROM THIS REVIEW**  
None blocking. The combined view confirms that every new gate (G18, G4-per-shot, G4s) and the frozen v2f path are correctly fail-closed; the only open items are observability and a documented deferral.

**4. REVISED SCORES**

| Subsystem       | Cycle 1 | Cycle 2 | Why changed          |
|-----------------|---------|---------|----------------------|
| Correctness     | 9/10    | 9/10    | No change            |
| Law Compliance  | 9/10    | 9/10    | No change            |
| Test Quality    | 8/10    | 9/10    | Tests now cover must-fail fixtures end-to-end |
| Security        | 7/10    | 7/10    | No change            |
| Overall         | READY   | READY   | —                    |

**5. FINAL PRIORITY LIST**  
- **P1** vertical_layout.py:1818 — emit `logger.warning` (clip, frame, t) when label becomes `"uncertain"`.  
- **P2** render_vertical.py (credits path) + verify_pack.py:1691 — add one-line comment documenting that D4 fix is deferred and contact-sheet verification is the control.  
- No P0 items.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Add the one-line structured log on the `"uncertain"` path so a human reviewer sees the safe-frame decision in the gate report without opening contact sheets.

**7. PRODUCTION READY?**  
**Yes with conditions**: implement the P1 logging line and the P2 comment before the next drop. All laws (Sentence Law, Selection Lock, Snap Limit, M12 Fail-Closed, Law 22) are now enforced; no blocking defects remain.