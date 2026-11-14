### The order (orchestrator 22:52 Nov 13, ruling 92, verbatim as relayed by the builder)
"92. SPOTLIGHT SOURCES: CONVERSATION, NOT REACTION. A spotlight moment must come from a conversation or original
reporting: an episode whose caption turn structure shows two or more speakers (interview, podcast, panel), or a
first-hand statement (a keynote, an interview on a news network). NOT from a solo host-to-camera news recap or
reaction segment, on any channel. Measured, not listed by name: the turn markers across the episode (one speaker
throughout = solo), plus the visual check's layout ... This rule is for SPOTLIGHTS; medleys keep the existing rule."
And to pp-ingest: "the hook pass should favour conversations for this purpose (role_hint stays 'hook')."

### The evidence that shaped the change
The 12 h pool already held 22 hook rows from conversation episodes. The builder's 22:13 build: Bitcoin Magazine's 16
stopped at a channel-level layout rule (burned-in chyron) the miner cannot change; BTC Sessions' 6 stopped at step A's
REFERENT_OUTSIDE (most), the render's STAND_ALONE (openers on 'and' / 'but' / 'so'), a second recognition, and a
first onset with no quiet before it. The builder: "the useful change is DIFFERENT rows rather than more:
self-contained openers that name their referents, don't start on a connective, and start after a pause".

### The change (mine-hook/2; diff since 116fbd5c)
- The hook prompt states the builder's deterministic OPENER rule with its own word sets (pp-selectid stand_alone.py
  PRONOUNS / CONJUNCTIONS / REPLY_FRAGMENTS, verbatim; a test compares them with the builder's source), "names who or
  what it is about", "starts a new thought, never the middle of an argument", and "in a conversation the best opener
  is ONE speaker's complete claim, number or question a stranger understands at once".
- A hook whose first word (canon.canon_tokens with contraction heads, the builder's tokenizer) breaks that rule is
  not written (counted in the report), as a hook outside 4-14 s is not.
- Every new row (moment and hook) carries `episode` = the caption turn structure measured (speaker markers '>>' and
  their escaped form, minutes, turns per minute, unmarked when there is none): the measure ruling 92 names, so the
  builder need not recompute it.
- `tools/ingest_watch.py hooks --rerun`: queues the 12 h window's mined videos for the current hook question once
  (the watcher's loop does the work, newest first).
- Not built (the orchestrator's choice): more candidates per window, or a spotlight-length question.

### Questions for the reviewers (file:line)
1. Can the OPENER filter drop a hook the builder would accept, or keep one it rejects (tokenization, contractions,
   quotes, '>>' markers before the first word)?
2. Is the episode measure correct (both marker forms, minutes from the record, unmarked) and impossible to break a
   line (a field added to pp.moment/1 lines)?
3. Does anything change the moment pass, the flags, the adapter, or any gate?
