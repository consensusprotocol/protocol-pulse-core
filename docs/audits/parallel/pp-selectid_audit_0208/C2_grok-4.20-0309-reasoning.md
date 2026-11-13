# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 57 s finish=stop usage in 13174 / out 1144 usd~0.094 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In my (assumed) Cycle 1 I focused on the per-moment reanchor, time-overlap dedup in `kept`, and test coverage but missed the three divergent lookup copies (package.src_of vs speakers.py:274 .get() vs context_integrity) and their failure-mode mismatch (KeyError vs silent None). I also missed Qwen/GLM's callout on the report["window_records"] type change (scalar → per-video list) and the exact phrasing of the new source_for docstring referencing the audit. Those were visible in the original diff but I did not surface them.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- Agree with GLM & Qwen on the lookup P1: three copies with inconsistent failure modes was real; speakers could have produced an unmeasured speaker from None while gates crashed. The FIXED diff resolves it cleanly (one source_for that always raises; speakers catches and forces "unknown"/measured=False; tests at 340-347 explicitly verify).  
- Agree with the consensus K1 disposition and the "one rule, fail closed for gates, unknown for speakers" outcome.  
- Partially agree on report schema P2: the structure change is breaking in theory, but the diff updates every use inside ledger_build (lines 148, 206), the test (301), and the log; consensus confirms no other consumers, so impact is only P2.  
- Agree with Grok that full-video path (lines 86-111) is untouched and that tests now cover the new per-moment + dedup + source_key paths.  
- Disagree with any post-fix "SHIP: no"—the provided C2 diff implements the exact mitigations the consensus listed.

**3. NEW FINDINGS FROM THIS REVIEW**  
P2 — ledger_build.py:177 `key = f"{vid}@{wsrc.window['start_s']:.3f}-{wsrc.window['end_s']:.3f}"` + sources[key] = wsrc. Two windows that round to identical bounds at 3 decimals share a Source (and report entry). The docstring claims "ONE WINDOW PER MOMENT" and the test uses distinct times, but nothing in the diff enforces uniqueness of the formatted key. Uncertain whether the worker can produce colliding windows; if it does, the later moment silently reuses the earlier Source (benign for same window but masks a worker bug).  

P2 — speakers.py:275 `import context_integrity as CI` is now inside attribute_package(). Works, but is the only runtime import in the changed files and could be moved to top-level for consistency (style/maintainability).  

No P0/P1. The new make() wrapper (60-75), per-sha caption lookup (143-144), explicit KeyError test, and "unknown" speaker path all align with L-m / L-j. The overlap test `a < sp.end and sp.start < b` (154) matches the Cycle-1 GLM fragment and L-p; touching spans are not deduped (visible and intentional).

**4. REVISED SCORES**  
| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| Source lookup      | P2      | resolved| Missed the multi-copy + fail-mode divergence; now one canonical raising function + explicit catch + test coverage. |
| Report / schema    | not flagged | P2     | Acknowledged breaking list change but all in-diff uses updated; low downstream risk per consensus. |
| Deduplication & windows | no finding | P2 | New visibility into :.3f key and kept-list reset per video; edge cases visible but not P1. |
| Test coverage      | SHIP yes| SHIP yes| Expanded assertions (302, 329-347) now directly exercise the exact failure modes C1 flagged. |
| Full-video path    | unchanged | unchanged | Still identical (verified lines 86-111). |

**5. FINAL PRIORITY LIST**  
P2 MEDIUM (nothing higher):  
- pipeline/ledger_build.py:177 — document the exact key format contract or add a uniqueness guard (or switch to moment_id if guaranteed unique).  
- pipeline/speakers.py:275 — move the import to module level.  
No P0/P1 items. All Cycle-1 findings are implemented and tested in the diff.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Centralizing the lookup in context_integrity.source_for() (lines 9-13) with its audit-referencing docstring, forcing every caller (prescreen, exclusion_for, hook_onset_for, contexts_from_sources, speakers, tests) through one fail-closed rule.

**7. PRODUCTION READY?**  
Yes with conditions: (1) confirm no out-of-diff consumer assumes report["window_records"][vid] is a string (visible uses are updated); (2) the word-pass worker must guarantee that formatted window bounds are unique per video (or the key format must be strengthened); (3) full regression_test.sh must pass post-merge. All verifiable defects from combined Cycle-1 feedback are fixed and tested.

**Findings**  
No P0.  
P2 ledger_build.py:177 (key collision on :.3f bounds—uncertain worker guarantee).  
P2 speakers.py:275 (import location).  
All prior P1 lookup and failure-mode issues resolved.  

**Verdict**  
SHIP: yes with conditions