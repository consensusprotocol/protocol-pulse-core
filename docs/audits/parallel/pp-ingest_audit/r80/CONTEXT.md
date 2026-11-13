### Two changes in this diff
A. RULING 77's cycle-1 fixes (cross-validate them): see C1_CONSENSUS.md of ruling 77 (the corrupt-record fail-open
   path closed, the STATE notice, the /proc count, unreadable paths, spec types, boundary and bare-date tests).
B. RULING 80, NEW (review it in full).

### Ruling 80 (orchestrator 18:42 ET Nov 13, verbatim)
"The 12 h pool has 201 moments, 19 cuttable, and ZERO that rate 4 as a HOOK (best three are 3: 'lacks punch to stop
scrolling', 'a mild opener', 'time-specific'). The builder dies at the hook stage. The miner finds good statements; it
is not looking for openers.
RULING 80: A HOOK PASS IN THE MINER. For every video inside the 12 h window (newest first, and every new upload from now
on), a second mining question over the same transcript windows, Heimdall, cheap: 'the 1 to 3 lines in this window that
would stop a scroll as the FIRST words of a short video'. A hook is: 4 to 14 seconds; starts at a sentence start and
ends at a sentence end; one speaker; understandable with nothing before it; a concrete, surprising or sharply put claim,
contrast, number or question about Bitcoin or money; NOT a greeting, a show intro, a date or 'this week' reference, an
ad read, a price prediction, an accusation. Give the judge's three-part hook definition the builder uses (stops the
scroll, stands alone, sets up what follows) in the prompt verbatim: get it from the builder's code (pp-selectid, ruling
52 / 59) so the miner aims at the same target the judge scores.
Rows go into the ledger as moments with role_hint 'hook' and the same exclusion flags and provenance as any moment;
the adapter returns them like any row (the builder's gates decide, nothing is waived). Run it now over the current 12 h
window, then keep it in the watcher loop. Report: hook rows mined per video, cost, and tell the builder the moment the
first batch is in the ledger so it rebuilds. Audit as usual; the backfill over the current window may run on the
audited code only."

### How it is built (mine.py HOOK_PROMPT / KINDS, service.hook_video / hook_once, queue hook columns, ledger.carry_forward)
- The hook question is a second prompt (mine-hook/1) over the SAME windows (mine.windows, the same Bitcoin screen),
  role "hook" in providers.json (the mine role's chain: Heimdall then local). It carries the builder's HOOK_QUESTION
  verbatim (a test compares it with pp-selectid's package.py source) and the moment prompt's own score axes and flag
  list (copied from mine.PROMPT at import, so the definitions are identical). Reply: {"hooks": [...]}, at most 3, each
  1-3 sentences (first + count), the moment schema otherwise; the same strict validator (parameterised).
- Rows: build_line with kind "hook": role_hint "hook", eligibility judged with the builder's role "hook" (its own
  hook rules), mined.prompt_version mine-hook/1, mined.pass "hook"; the same moment_id as a moment of the same span
  (the contract's identity: the builder's dedupe and delivered checks keep working). A row whose duration (word timing,
  else the caption estimate) is outside 4-14 s, or unmeasured, is not written (counted in the report).
- Every ledger append of the service (moment and hook passes) goes through one lock that reads the video's earlier
  lines and carries their flags (ledger.carry_forward: risk union, names_person / altcoin either, about_bitcoin both,
  the hook hint): the adapter returns a moment's LATEST line, so a hook line for a span the moment pass flagged keeps
  the flag (and a re-mine keeps the hook hint).
- The loop: every 5 s, mined videos published in the last 12 h whose hook pass has not run, newest first, 2 at once
  (their windows share the router's bounds: Heimdall <= 20 in flight). A pass with failed windows is retried in 10 min
  (stored replies make the good windows free); an outage uses no try; after 3 passes with rejected windows the good
  windows' hooks are written. Videos older than 12 h are never hook-mined (their moments are expired).

### Questions for the reviewers (file:line)
1. Can a hook row reach the adapter WITHOUT a flag an earlier line of the same span had, or with a flag it should
   carry missing (any order of passes, concurrency, a crash between the read and the append)?
2. Does the hook pass ask exactly the ruling's question (the 1-3 lines, 4-14 s, the NOT list) and the builder's judge
   question verbatim? Can a row outside 4-14 s, or spanning a speaker change, be written as a hook?
3. Does anything here change what the adapter excludes or waive any gate (L-u, delivered, opt-out, expiry, drift)?
4. Ruling 77's fixes: is the fail-open path closed, and is every new failure mode fail-closed?
