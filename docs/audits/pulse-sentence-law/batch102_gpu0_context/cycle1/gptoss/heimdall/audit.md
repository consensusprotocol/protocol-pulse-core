# Heimdall audit

**Question:** Review this diff (batch 102). The problem it fixes: the cron transcript ingest's Whisper pass (transcript_ingest.ingest) gave GPU0 back at a file boundary when a build service wanted the card (gpu0_want) and then WAITED and went on. Once Whisper has loaded in a process, that process keeps a CUDA context (394 MiB) until it exits, and gpu0's L-r check counts any other process on GPU0 as a foreign user: the stand-alone scorer's swap_to / release_all waited 600 s and raised gpu0.Gpu0Foreign, which the scorer's serve_once did not catch, so the scorer service died (15:26 ET Nov 16, down 18 h). The fix: (1) the Whisper pass ENDS at that boundary (the rest of its videos wait for the next cron run), so the process and its context are gone; (2) the scorer catches every gpu0.Gpu0Stop and lives on.

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.

FACTS (unchanged code, not in the diff):
- gpu0 exceptions: class Gpu0Stop(BaseException); LeaseBusy, Gpu0Foreign, GpuOOM, LeaseMissing, Gpu0NotFree, Gpu0Unreadable all subclass Gpu0Stop.
- hold is a contextlib.ExitStack holding the GPU0 lease, with ts.release_whisper registered to run first on close (Whisper unloaded while the lease is still held).
- gpu0_turn(hold, waited, log) waits (polling, holding nothing) for the lease BEFORE a load; Whisper loads only inside ts.acquire(..., allow_whisper=True) after a turn is held.
- After the loop, ingest() writes the run's summary (ingest_runs.jsonl) and returns; main() then exits. The pass runs from cron every 30 min, one instance at a time.
- In stand_alone_scorer.serve_once, `llm = sm.LocalLLM().start()` precedes `try: ... finally: gpu0.release_all()`, all inside `with gpu0.lease(OWNER, wait_s=0):`; the requests are files that stay pending until answered.
- local_judge already catches gpu0.Gpu0Stop the same way.

CHECKS:
G1. After a mid-pass yield, can the pass load Whisper again in this run, or wait for GPU0 while this process holds a CUDA context? Is the lease released and Whisper unloaded before the pass ends?
G2. Are exactly the videos not yet transcribed (the one in hand onward) given a deferred status, with a render's flag keeping deferred_render_wants_gpu0? Is any video lost or marked done without a transcript?
G3. Is waiting before the first load unchanged (gpu0_turn, LEASE_WAIT_S)?
G4. stand_alone_scorer: is every Gpu0Stop that leaves the lease block caught (including one from release_all inside the finally)? Is LeaseBusy still logged as before? Can a request be lost or answered twice?
G5. Does anything else change behaviour?

**Panel:** gptoss  |  **Cost:** $0.0004
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
