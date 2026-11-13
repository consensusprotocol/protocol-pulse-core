### The orders this change answers (verbatim)
PBX 18:01 ET Nov 13: "do we have a system in place to stop our coping system from reusing old clips? We need to delete
all the contents after like 6 to 12 hours so that we never reuse any of it"
ORCHESTRATOR RULING 77, 18:09 ET (with the builder's ruling 76: a moment is usable only within 12 h of its video's
publish time, then never again):
1. EXPIRY IN THE LEDGER: a moment whose video published_at is more than 12 h old is marked expired (a field, with the
   time), and the adapter never returns it. Expired rows are not deleted from the ledger file: they are the record that
   a moment was seen (the 'first said' receipt, the dedupe against re-posts) and they cost nothing.
2. DELETE THE CONTENT: cached source media and audio of videos older than 12 h (downloads, windows' WAVs, acquired mp4
   sections) are deleted on a rolling basis, EXCEPT the sources of DELIVERED videos, whose provenance records
   (PROVENANCE.json, transcript hashes, the pin) are kept per the attribution law. Transcripts (text) are kept; media is
   not. Report the disk freed and what is kept.
3. This needs a recurring purge. Do NOT install a cron: the watcher process you already run does the purge in its own
   loop. Say how often.
4. The mining order: newest uploads first, always; the word-pass worker's tiers become 'last 6 h, then 6-12 h',
   nothing older (tell the integrator; it owns the worker).

### The builder's readings (STATE assumptions A17-A21)
- A17 the purge deletes outside this worktree only in the three targets of purge.json (runs/*/sources,
  data/lock_precheck/work/*/sources, /tmp/word_pass_*); load_spec refuses a target naming a protected path.
- A18 "marked expired (a field, with the time)": the ledger is append-only, so every new row carries `expires_at`
  (publish + 12 h) written at mining; the adapter uses min(expires_at, published_at + 12 h).
- A19 "EXCEPT the sources of DELIVERED videos": every cached copy of a delivered video's media is kept (literal).
- A20 only the three listed kinds are deleted; renders' intermediates, out/, other pipelines' caches are measured and
  reported, never deleted.
- A21 newest-first orders the mining; videos older than 12 h are still mined last (receipts).

### Live evidence
Dry run on the real tree: would free 6 files 0.09 GB (never-delivered runs, videos 25-105 h old); kept 154 files 7.27 GB
(copies of the 15 delivered videos), 51 symlinks, 1 unnamed, 1 in use, 1 not yet expired. The watcher's first real pass
(18:23 ET) deleted exactly those 6 files. The adapter on the live ledger: 172 expired refused, 304 returned.

### Questions for the reviewers (answer each with file:line)
1. Can the purge delete anything the ruling says to keep: a delivered video's source, a provenance record, a
   transcript, a pin, a render? Can it delete media of a video published under 12 h ago?
2. Can a malformed purge.json, a symlink, a race with a render, a rename, or an unreadable file make it delete outside
   its targets or delete something it should keep? Is every uncertainty fail-closed (keep)?
3. Can the adapter return a moment 12 h or more after its video's publish time, by any path (since, horizon, a row
   without expires_at, a later expires_at, a re-mined row)?
4. Does anything in the change weaken an earlier check (L-u flags, delivered, opt-out, contract drift, the spend freeze)?
