# pp-backtest — failure patterns for the Qwen bible (the integrator folds these in; the bible is not edited here)

### E-FAIL-candidate-B1: The audit tool writes into the main tree from any worktree
**Evidence:** utils/cross_llm_audit.py sets `BASE = Path.home() / "protocol_pulse"`, creates `BASE/docs/audits/<feature>/`
on import, writes every package / reply / consensus there and rewrites `BASE/docs/audits/AUDIT_REGISTRY.json`; it
also loads keys from `BASE/.env`. Run unmodified from a parallel worktree (pp-backtest, 2026-11-12) it would have
written into /home/ultron/protocol_pulse while a live run executed from it.
**Rule:** a parallel session runs the audit with HOME pointing at a scratch directory whose `protocol_pulse/` holds
only the gospel, the diff and a symlink to the main `.env` (read by name inside the tool); the results are copied
into the session's own docs. Request filed (pp-backtest_REQUESTS.md R1): an explicit output root.

### E-FAIL-candidate-B2: A stand-in LLM that inherits LocalLLM.stop() evicts the live run's model
**Evidence:** story_semantics.LocalLLM.stop() posts keep_alive 0 for gemma3:27b to the shared GPU0 Ollama;
editorial_select.select_story calls L.stop() at its end (and pipeline/backtest.py's main calls it again). Any
replay, backtest or test double that subclasses LocalLLM without overriding stop() unloads the model a live run is
using in the middle of its editorial stage.
**Rule:** every LocalLLM stand-in overrides stop() (pipeline/oracle/replay.py CacheOnlyLLM; test
test_oracle_llm_replay.py::test_stop_never_unloads_the_shared_gpu0_model).

### E-FAIL-candidate-B3: A cache miss raised as an ordinary exception becomes a selector verdict
**Evidence:** LocalLLM.chat_json turns every Exception from _post into a failed attempt, and after the attempts an
LLMParseError, which adjudicate / label_cluster / rate_passages record as INCONCLUSIVE / not counted / unrated. A
cache-only replay that raised RuntimeError on a miss would therefore have produced a complete-looking
TOPIC_SELECTION.json whose 'decisions' were invented by the missing cache (law L-m: nothing measured is never a
result).
**Rule:** a replay's miss is a BaseException (replay.NotRerun) that no `except Exception` can absorb; the replay
records NOT_RERUN and the phase, and the day is scored from the saved record instead.

### E-FAIL-candidate-B4: Saved runs hold no transcripts; the universe is a list of shas into a mutable store
**Evidence:** every runs/fresh_*/transcripts directory is empty (0 files in all 13 fresh runs on 2026-11-12); a
run's universe exists only as transcript_sha256 values pointing into data/editorial/transcripts. Embedding.chunk_vectors
also writes that store on a cache miss. A backtest is only as frozen as the store's write-once rule.
**Rule:** backtests read records by the recorded sha with the hash re-checked (a missing record is a counted gap,
never a substitute; an altered record stops the export, since that universe can no longer be reproduced:
pipeline/oracle/export.py), and never write the store (replay.CpuEmbedder).

### E-FAIL-candidate-B5: Pre-DEC-13 selection records keep no cluster membership
**Evidence:** TOPIC_SELECTION.json of fresh_20261106_213852 .. fresh_20261111_213954 keeps, per emergent cluster,
only its channels, n_chunks and the label's excerpt ids; member_chunk_ids exists from DEC-13 (5dde8179) on. On those
days a "lost at cluster formation" verdict can only be partial (label excerpts) unless the clustering is replayed.
**Rule:** the supply backtest traces old days through the HEAD replay's clusters as well as the saved record, and
says which (BACKTEST_SUPPLY_REPORT.md section 3).

### E-FAIL-candidate-B6: Caption speaker changes are not sentence ends for sentence_law.is_terminal
**Evidence:** CNBC / Bloomberg captions mark a new speaker with '&gt;&gt;' ('>>') and often leave the previous
speaker's sentence unpunctuated, so a text-level split joins two speakers into one 'sentence'. Unpunctuated
stretches are common in every record kind: over the ten exports, rows longer than the 20 s clip budget number 632
of 25,798 auto-caption rows (longest 136.8 s), 82 of 3,298 Whisper-segment rows (93.2 s), 171 of 5,715 verbatim
whisper_words rows (92.3 s) and 8 of 1,134 whisper_words_punct rows (35.7 s). The selector itself never cuts from
captions (windows need sentence_ready word records, law L-e), so this bounds text-level readers (the export, chunk
labels) and shows where L-e's restoration still leaves stretches.
**Rule:** the supply export ends a sentence at a speaker marker and hides any 'sentence' longer than the 20 s clip
budget from the oracle (counted per run).

### E-FAIL-candidate-B7: A cluster label names the video, not the excerpt, and the protected preview's story dies at LABEL
**Evidence:** Nov 10 (fresh_20261110_093150) through DEC-13 clustering (the 394ffe5a cold backtest and the HEAD
replay, same cached gemma reply): cluster 0 holds DataDash RXTVaDsN11M:0-1 and Yahoo Finance _cGepHL1Rf0:9-11, the
statements of the blind oracle's accepted line-up (= the PBX-approved preview's story). Its label quotes Yahoo's
sentence verbatim ("Bitcoin dropped pretty massively over the weekend alongside the tech selloff ...") but returns
current_development_chunk_id "_cGepHL1Rf0" (the video id) instead of an excerpt id, so label_cluster's quote check
fails closed and the cluster stops at "label: no verified current-development evidence". Frequency: 1-2 of 31-46
specific-event labels in each of the five DEC-13 records (two cold-backtest, three live runs).
**Rule:** a model never writes an identifier the code then matches back; it picks from numbered statements and the
code binds the chunk (orchestrator addendum '22:15' item 3, constrained selection). Detection: the supply backtest's
LABEL stage (docs/audits/BACKTEST_SUPPLY_REPORT.md).

### E-FAIL-candidate-B8: A verbatim quote check fails when the model corrects the transcript's own ASR error
**Evidence:** Nov 7 (fresh_20261107_080503): Yahoo Finance's caption reads "... as Wall Street telloff triggers over $1
billion in crypto liquidations"; the adjudicator quoted it as "selloff", quote_verified False, so the statement that
carries the accepted line-up's development was not counted and coverage fell to one channel (Swan Bitcoin). Same class
as the open Claude-select T1 finding (zero tolerance for the model's own clean-up).
**Rule:** as B7: the evidence is a sentence id, the quote is the stored sentence; a model's paraphrase is never the
evidence.

### E-FAIL-candidate-B9: A duration told to a model as a "target" is mostly not met
**Evidence:** the supply backtest's L-o runs (2026-11-12): told the 8-12 s / 12-20 s windows are targets ("prefer
segments inside these targets; go outside them only when a statement needs it"), gpt-6.1-sol returned accepted line-ups
outside at least one window in 36 of 41 (story-first) and 43 of 48 (moments-first) cases.
**Rule:** a taste bend needs a ranking pressure the code applies (distance from the target as a penalty), or it
silently stops existing; the backtest measures windows-hard supply in its own run instead of filtering target runs.

### E-FAIL-candidate-B10: A context check on captions cannot always tell who is speaking
**Evidence:** the witness pass (2026-11-12) read 166 moments segments in their original caption context: 3 came back
"uncertain" (the speaker of a reply could not be identified: captions carry '>>' turn marks at best, no names), and
uncertain is a fail by the reviewers' rule. Diarised transcripts are an input the check needs, not a refinement.

### E-FAIL-candidate-B11: A local model's context window cuts a long prompt and still answers
**Evidence:** the writer's prompt for a saved universe is 115,595-219,172 tokens (the writer's own token counts,
2026-11-12, all 10 universes); the local back-end (Ollama, num_ctx 131,072) has to keep its 16,000-token reply budget
inside that window. Ollama shortens an input longer than num_ctx and returns a normal reply (only its server log says
the prompt was truncated), so a local writer would have answered about part of the universe as if it were all of it.
A first estimate of 3 characters per token was not conservative here: on this instrument's own stored prompts the
writer's tokenizer counted 2.93-3.06 and the judge's 1.84-2.07 characters per token (ids and numbers tokenize densely),
so the Nov 10 writer prompt "fitted" by the estimate and not by its real count (115,595 + 16,000 > 131,072).
**Rule:** a prompt whose estimate (1.75 characters per token: below every tokenizer measured) plus the reply budget
exceeds the back-end's context is never sent (pipeline/oracle/providers.py ContextTooLong; the role moves to the next
back-end and the skip is recorded); a local reply whose prompt + output tokens reach num_ctx is a failure, not an
answer.

### E-FAIL-candidate-B12: A shared credit counter is not the price of a call
**Evidence:** the A/B harness first priced Heimdall back-ends as the change in the gateway's account-wide credit
counter around a batch; three batches ran on the same key at once (and other sessions use it), so each back-end would
have been charged for the others' calls. The gateway reports each call's own cost (usage.cost).
**Rule:** dollars are recorded per call: the price table for frontier back-ends, the gateway-reported cost for a
gateway that bills per call, 0 for local; a remote back-end with neither is recorded as 'unpriced', never as free.

### E-FAIL-candidate-B13: .gitignore drops new tests and reports from a commit without a word
**Evidence:** .gitignore line 16 `test_*` and line 39 `docs/audits/*.md` ignore every new test module and every new
audit report; `git status` does not list them, so `git add <dir>` commits the code without its tests or its report.
The 62 test modules tracked today (pipeline/test_*.py, ...) were force-added. On pp-backtest (2026-11-12) the nine
tests/oracle/test_oracle_*.py and docs/audits/BACKTEST_SUPPLY_REPORT.md were invisible to `git status`.
**Rule:** add tests and reports with `git add -f <path>` and prove the commit holds them (`git ls-files <path>` after
the commit, count matches the files on disk); a DONE that cites tests names the tracked files.

### E-FAIL-candidate-B14: The stop hook audits the main tree from every worktree and orders a commit there
**Evidence:** scripts/hooks/stop_audit.sh starts with `cd /home/ultron/protocol_pulse` and blocks the session with
"UNCOMMITTED: ... run git add+commit+push!" for any modified .py file in the MAIN tree. On 2026-11-12 03:25 ET it
blocked the pp-backtest worktree session over 22 .py files (+450 / -146) modified by another session on the main
tree's branch combo-letterbox-quoteonly-v2 (pipeline/backtest.py, config.py, cut_accept.py, preflight.py,
pulse_transitions.py, ...), while a live run executed from that tree. Obeying it would commit another session's
unfinished work from the wrong session.
**Rule:** a session commits only its own worktree's branch; a hook that names files outside the session's worktree is
reported, never obeyed. The hook should audit the session's own working directory (request R7).

### E-FAIL-candidate-B15: The tool's two-model consensus said READY while an independent review found 28 defects
**Evidence:** utils/cross_llm_audit.py on pp-backtest's code package (2026-11-12, Gemini not run: no key in the main
.env): GPT-4o and Grok-3 answered the tool's generic Q1-Q4 sentence-law checklist with "no defects, READY" in round 1,
and found no code defect in round 2 (they asked only for tests). An independent claude-fable-5-2 review of the same
package, asked the package's own FIND list with a schema for findings, returned 12 defects in round 1 (spend guard
not shared across processes, stale derived files read as results, must-fail swaps that could pass for the wrong
reason, ...) and 16 in round 2 (recall counting unmeasured records as misses, CLUSTER_FORMATION blamed where the run
stopped, ...), most of them confirmed and fixed with tests; three changed reported results (the recall
denominator, the loss stage of 11 traces, the must-fail swaps of the judge A/B).
**Rule:** for a diff the tool's feature header does not describe, the audit carries the package's own question and
laws, and at least one independent reviewer answers that question with findings in a schema; a READY from the generic
checklist is not evidence of correctness. An empty or cut review is NOT MEASURED, never READY (it happened once here:
a 32k-token reply cap).
