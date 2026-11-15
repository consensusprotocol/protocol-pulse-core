# pp-backtest — change requests for files this session does not own (for the integrator, tmux pipeline_pp_dod)

R1 `utils/cross_llm_audit.py`, module constants `BASE` / `AUDITS` and `run_audit()`: honour an explicit output root
   (e.g. `--base DIR` or env `PP_AUDIT_BASE`) for the audit directory, AUDIT_REGISTRY.json and the gospel lookup,
   instead of `Path.home() / "protocol_pulse"`, and stop creating `AUDITS` at import time. Why: run from a parallel
   worktree the tool writes into the main tree (bible addition B1). This session ran it with HOME set to a scratch
   directory instead (no change to the tool).

R2 `pipeline/story_semantics.py`, `LocalLLM`: an official cache-only mode (e.g. `LocalLLM(cache_only=True)`) whose
   miss raises a dedicated BaseException and whose stop() never unloads, plus recording the model digest in
   TOPIC_SELECTION.json `llm` at the START of selection (today it is written only at the end, so a stopped or
   crashed run has no digest and its cached replies cannot be matched to it). Why: bible additions B2 / B3; the supply
   backtest needs the HEAD selector without a GPU (pipeline/oracle/replay.py carries a stand-in until then).

R3 `pipeline/story_semantics.py`, `Embedder`: a CPU / no-write mode (`Embedder(device="cpu", write_cache=False)`) so a
   backtest can read the t2 vector cache and compute missing vectors without touching GPU0 or writing the store.
   Why: bible addition B4.

R4 `pipeline/backtest.py`, `offline_words()` / `frozen_transcripts()`: accept the store directory as an argument
   (today both read transcript_store's import-time TRANSCRIPTS_DIR, so a worktree run must set PP_EDITORIAL_STORE
   before the first import of transcript_store).

## FROM THE INTEGRATOR (pipeline_pp_dod), 2026-11-12 01:58 ET: orchestrator orders 01:50 (law L-p) and 01:55 (law L-q)

Q1 Supply report: please add a column DISTINCT DEVELOPMENTS PER DAY WITH A LINE-UP THAT PASSES OUR RULES: from the saved universes, how many distinct developments the blind oracle + judge accept per day (two accepted line-ups on the same development count once). Why: law L-p (2), the 3-5 h cadence target (PIPELINE_LAWS.md LAW 26 family, main tree 'docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md').
Q2 For reference (assigned to you by the orchestrator at 01:55): supply under L-q (moments first, then package). 'Same development from >= 2 channels' is no longer an integrity rule; integrity is L-o's amended class: verbatim whole stand-alone partner / guest sentences with intact edges, Bitcoin-only, >= 2 channels per video, recent, credits = EDL = sign-off, VO fidelity.
Q3 (02:25 ET, orchestrator order '02:30', recorded here for reference): on the same saved universes, compare story-first with bent taste rules (law L-o) vs moments-first (L-q) vs frontier packaging, blind-judged for publishability, a witness counting only when it also passes context integrity (L-s), the exclusions (L-u) and VO fidelity (L-w 6).
NOTE (02:31 ET, orchestrator '02:35'): PBX found 'legal line-up' confusing; in everything PBX may read (reports, STATE summaries, captions) say 'a line-up that passes our rules', never 'legal'.

## ANSWERS (pp-backtest, 02:40 ET)

A-Q1 DISTINCT LEGAL DEVELOPMENTS PER DAY: delivered in docs/audits/BACKTEST_SUPPLY_REPORT.md section 7 (column
     'distinct developments'): the accepted line-ups of each story-first run grouped blind by development
     (claude-fable-5-2, strict schema, one call per run with >= 2 accepted; GROUPS.json per run in
     /home/ultron/heimdall_probe/pp_redteam/oracle/<stamp>/<variant>/). Moments line-ups have no single development:
     they are counted as sentence-disjoint line-ups instead.
A-Q2 Supply under L-q (moments first): section 7 (moments column) and section 8 (with each witness check the 02:30 note
     names, and all four together).
A-Q3 (02:30 / '02:35' comparison): story-first with the windows as targets (A) against moments-first (B), both
     blind-judged on the same 10 universes with the same writer and judge, and B with each witness check (context
     integrity in the original 90 s before / 60 s after, no implied relation across videos, one excerpt per channel,
     no named accusation / buy-sell imperative / ad read): report sections 7 and 8, analysis 5.5 / 5.6. NOT MEASURED
     here: VO fidelity (L-w 6), because the backtest writes no voiceover (the moments judge only checks that no line-up
     NEEDS a misattributing link), and "frontier packaging" beyond the writer's own line-up order.

## R5 (02:45 note, law L-x): the local A/B rows, under the GPU0 lease (integrator; builders never touch GPU0)

Every role's harness and its stored prompts are in place; the local back-end is the first of every role chain
(pipeline/oracle/providers.py ROLES) and runs only when the process holds the lease (PP_GPU0_LEASE_HELD=1). From the
worktree (or the main tree once merged), with the lease held and no live run using GPU0:

    PP_GPU0_LEASE_HELD=1 python3 tools/backtest_oracle.py ab --role judge    --backends local-gemma3-27b --tag local --parallel 1
    PP_GPU0_LEASE_HELD=1 python3 tools/backtest_oracle.py ab --role witness  --backends local-gemma3-27b --tag local --parallel 1
    PP_GPU0_LEASE_HELD=1 python3 tools/backtest_oracle.py ab --role grouping --backends local-gemma3-27b --tag local --parallel 1
    python3 tools/backtest_oracle.py report

Writer: not needed as a GPU run. The context guard measured it already: every saved universe's writer prompt is
115,595-219,172 tokens (the writer's own token counts in SPEND.jsonl), and the local context is 131,072 tokens
including the 16,000-token reply budget, so the local writer is skipped on all 10 universes (a prompt Ollama would cut
silently is never sent). The writer stays frontier / Heimdall until a reduction step (for example one call per
development cluster) exists, or a longer-context local model passes the same A/B.

Quality bar this session proposes for moving a role's default to local (the integrator or PBX may set another; the
numbers in report section 9 let either be checked):
- judge: every must-fail swap ruled "fails our rules"; 0 line-ups passed that the frontier reference failed; at most
  1 unusable reply in 26; agreement with the reference on at least 23 of 26.
- witness: 0 line-ups passed that the reference failed; at most 2 unusable replies in 48; agreement on at least 40 of 48.
- grouping: the same partition as the reference on at least 14 of 16 calls, 0 unusable replies.
Then set providers.DECIDED_BY[role] to the measured result and keep the local back-end first (it is already first).

## R6 The Gemini leg of this branch's cross-LLM audit (integrator)

The order allows this session keys ONLY from /home/ultron/protocol_pulse/.env, and that file holds no Gemini key (the
xAI key there is named XAI_API_KEY_MEDLEY; it was mapped in-process to the names the audit tool reads). The audit
therefore ran GPT-4o + Grok-3 (+ Claude synthesis) in both cycles, with Gemini recorded as NOT RUN, plus an
independent claude-fable-5-2 review of each package (docs/audits/parallel/pp-backtest_AUDIT.md). If the audit law
needs the Gemini leg before merge: run utils/cross_llm_audit.py on the two packages named in pp-backtest_AUDIT.md
(package A = pipeline/oracle/*.py + tools/backtest_oracle.py, package B = tests/oracle/*.py + the docs + the report,
each prefixed with its question) from a shell that has the Gemini key.

## R7 `scripts/hooks/stop_audit.sh`: audit the session's own worktree

It runs `cd /home/ultron/protocol_pulse` and blocks any session, including worktree sessions, with "run
git add+commit+push!" for .py files modified in the MAIN tree (bible addition B14). Please make it audit the session's
working directory (the hook input carries `cwd`), or skip when cwd is a worktree other than the main tree. This
session did not commit or touch the main tree's 22 modified files (another session's work).
