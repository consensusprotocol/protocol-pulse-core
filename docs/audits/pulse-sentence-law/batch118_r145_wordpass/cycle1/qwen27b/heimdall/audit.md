# Heimdall audit

**Question:** TASK: audit batch 118 of the Protocol Pulse video pipeline (Python). You are reviewing a diff. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

THE ORDER (orchestrator 18:18 ET Nov 23, ruling 145): land the small-tenant GPU lease allowance "so a stray program never kills the word pass again". On Nov 17 a foreign program (DaVinci Resolve, 678 MiB on GPU1) made gpu0.swap_to raise gpu0.Gpu0Foreign out of the word-pass worker's cycle(); main() caught only RuntimeError, and Gpu0Stop and its subclasses derive from BaseException (pipeline/gpu0.py:94-118: Gpu0Stop(BaseException); GpuOOM, Gpu0Foreign, LeaseMissing, LeaseBusy, Gpu0NotFree, Gpu0Unreadable subclass it), so the worker died and stayed down. The allowance itself (tolerating a foreign process under 2 GiB and 10 % utilisation) changes gpu0.py, which is hashed into the lock pre-check's decoder sha, so it lands later in a lockstep. THIS batch is the worker's half and touches no hashed file.

WHAT THE DIFF DOES (pipeline/word_pass_worker.py main()):
- main() imports gpu0 and catches gpu0.Gpu0Foreign, gpu0.GpuOOM and gpu0.Gpu0NotFree from cycle(): it logs "cycle stopped, GPU1 not ours to use now: <type>: <message>" and sets rep = {"picked": 0, "blocked": <type>}, so the loop's existing rule (`if not rep.get("picked") or rep.get("blocked"): time.sleep(a.sleep)`) sleeps before the next cycle, where the moments are picked again (no row was written for them).
- Unchanged on purpose: gpu0.LeaseMissing (no GPU1 lease file / host misconfiguration), gpu0.Gpu0Unreadable and a LeaseBusy raised inside a held batch (cycle() re-raises it: a bug of this process, not another owner's turn) still leave main(), as before; the busy lease at the door is already handled inside cycle() (batch 90).
- cycle()'s own cleanup runs before main() sees the exception: its `finally` empties the temp dir, and gpu_batch's `finally` releases Whisper (ts.release_whisper) before the lease context exits.

CHECK, AND ANSWER EACH:
Q1. Can the new except clause catch anything it should not (KeyboardInterrupt, SystemExit, a LeaseMissing), or miss one of the three it names?
Q2. After a caught exception, is the next cycle safe: no lease still held, no Whisper left loaded by this process, no partial row written?
Q3. Do the tests prove the behaviour (each subtest fails if the except clause is removed; the LeaseMissing test fails if LeaseMissing were also caught)?
Q4. Any other defect.

OUTPUT: for each finding, severity (critical|high|medium|low), file:line, the concrete failure (inputs -> wrong result), and the fix. If none, say NONE for that question.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** qwen27b  |  **Cost:** $0.0033
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
