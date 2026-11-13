# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 60 s finish=stop usage in 18603 / out 1350 usd~0.127 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0155 (G17a at pin stage)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
GLM's P0-2 (cache keyed only on moment_id while depending on work_dir/audio_window state) and the ledger_build caption_source poisoning that produced "0 moments cleared" on the first live run. Qwen's pad double-counting scenario (file-head hook with synthetic LEAD_PAD_S). The exact 85 ms boundary test and the CONTEXT_UNAVAILABLE isolation fix were not in my Cycle 1 mental model. The kept items (CUTTABLE vs edge_plan "not cuttable", no-voice added clip never becoming the hook) were also outside my initial scan.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P0-1/P1-1 (slice vs render decode divergence): Partially agree — the original diff risked a 75-85 ms flip; the fixed version adds MARGIN_MS + explicit test (85 ms fails, 120 ms passes) and docstring clarification that fade-in only makes the pin check stricter. The concrete failure scenario is now prevented.  
- GLM P0-2 (cache): Agree it is a real coupling; consensus that audio_window is disk-cached makes it deterministic and fail-closed, so downgrade to P2 is correct.  
- Qwen pad P1: Agree it was a legitimate reading of the original diff; the new test_a_file_head_hook_counts_the_pad_the_render_adds_once plus updated docstring (pad added *before* source) refutes double-counting.  
- Qwen lineup "opens with clip" P1: Disagree — the diff + new test explicitly shows lineup_for(need_onset=True) returns None (no paid medley call) when no hook passes; proposer's hook correctly yields to next valid one.  
- Consensus kept items (GLM P1-3 CUTTABLE, P1-4 no-voice clip, angle["hook"] usage): Fully agree; verified in the fixed diff and test_medley updates.  
- Grok's "no findings / SHIP yes": Agree on the final fixed diff; Cycle 1 version would have warranted the margin addition.

**3. NEW FINDINGS FROM THIS REVIEW**  
**P2 — pipeline/package.py:254 (ThreadPoolExecutor) + hook_onset_for:235**  
Cache `hk = {}` is built once per `build()` and shared across all angles. A transient exception on first measurement of a moment_id permanently records `{"pass": False, "measured": False}` for the entire run (fail-closed, L-m compliant). The new ledger test isolates CONTEXT_UNAVAILABLE but does not exercise a transient audio_window failure after first success. Verifiable from diff; uncertain whether disk cache can ever flip after first write.

**P2 — pipeline/hook_onset.py:58-61 (word index filtering)**  
`idx = [i for i, t in enumerate(toks) if ... float(t["start"]) >= a and float(t["end"]) <= a + sa.dur]` then `if w0 not in idx or w1 not in idx: return measured=False`. With synthetic test audio=(env, 0.0) this passes; with real TT.audio_window() floating-point start offsets or token timestamps that land exactly on slice boundaries could silently produce "words not inside its audio window" (measured=False, never a pass). Test covers the no-audio case but not boundary float equality. Uncertain without SL.SourceAudio internals.

No new P0 or P1 verifiable from diff alone.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Measurement divergence (slice vs render) | P0     | P2     | Margin + test_a_lead_within_one_frame_of_80_ms_does_not_pass directly closes the flip window I previously rated P0 |
| Cache / determinism    | P1     | P2     | Consensus + ledger_store changes confirm disk caching; still a coupling but now tested |
| Lineup hook filtering  | 0      | 0      | New test_a_hook_without_80_ms... proves fallback and "no line-up → no paid call" |
| Ledger context poisoning | N/A   | P2     | Fixed in this diff; new test verifies isolation |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL:** None verifiable.  
**P1 HIGH:** None.  
**P2 MEDIUM:**  
- pipeline/package.py:235-242 (hook_onset_for cache lifetime) — document reliance on audio_window disk cache; add explicit cache-bust comment.  
- pipeline/hook_onset.py:58-61 (word filtering) — add test case with exact boundary timestamp to prove measured=True.  
- pipeline/ledger_build.py:115-152 (caption_source dual-store) — already tested, but the "different words" ambiguous path logs only one why; minor.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The addition of MARGIN_MS plus the concrete 85 ms failure test in test_hook_onset.py that pins the slice-vs-render quantization window to exactly what the render will see.

**7. PRODUCTION READY?**  
Yes with conditions: (a) add explicit comment at package.py:235 documenting that the per-build cache is safe *only* because audio_window is disk-cached and deterministic; (b) extend test_hook_onset with one boundary-float case for the idx filter. These are documentation/test gaps, not behavioral defects.

**Findings (verifiable from diff only)**  
**P2-1 — pipeline/package.py:254 + hook_onset_for:235**  
Shared `hk={}` cache + ThreadPoolExecutor; first transient audio_window exception for a moment_id freezes measured=False for whole build (e.g. momentary NFS glitch on L-v 2 window). Leads to permanent "NOT MEASURED" in prescreen and no lineup for that moment even if later calls would succeed. Fail-closed but silent. (Consensus kept item.)

**P2-2 — pipeline/hook_onset.py:58**  
Word-index collection can return empty idx for floating-point edge timestamps inside the requested [start, end] window, producing measured=False (never pass) even though edge_plan would have succeeded. Test only exercises clear no-audio and words-outside cases.

**Verdict**  
SHIP: yes with conditions