# pp-selectid — PROOF on the saved universes (order 00:32 ET Nov 12, item 3)

The table, per run and per model, is generated from the proof files by tests/select_by_id/proof_table.py into
docs/audits/parallel/pp-selectid_PROOF_TABLE.md, and copied into STATE.

How it ran:
- Driver: tests/select_by_id/proof_saved_runs.py, which calls select_by_id.run_pools, the production entry, with
  ModelChecks.
- Inputs, all read-only: each run's TOPIC_SELECTION.json universe; the store records by the sha the run recorded,
  hash-checked; cached embeddings for runs older than DEC-13 (a CPU re-cluster).
- Every reply is recorded under tests/select_by_id/fixtures/replies, and tests replay them offline.
- No GPU. In this CPU replay, a story whose on-screen videos have no sentence-ready word record in the store cannot be
  given a line-up; production runs its word pass there. Those rows say so.

Models, recorded in every proof file:
- COLUMN OF RECORD (tests/select_by_id/proof_judge_t0/): generator claude-fable-5-2@medium (orchestrator 02:00 note);
  judge grok-4.20-0309-reasoning at temperature 0 with the attempt's seed. That is production parity: LocalLLM runs
  every check at temperature 0 (story_semantics.py:190-195).
- Every row carries the sha256 of select_by_id.py / eligibility.py that produced it. 188a35e3c047deee /
  6f7055bcfdfa3aa7 are the committed files.
- SENSITIVITY column (tests/select_by_id/proof_judge_default/): the same generator and recordings, with the judge at the
  API's default temperature.
  - Its per-sentence verdicts varied across the three attempts of one story; the preview's story was rejected there
    and accepted at temperature 0.
  - Rows written before 02:25 ET come from the pre-audit-C2 code and are superseded.
- Earlier columns (superseded, recordings kept): gpt-6.1-sol, then claude-opus-5-5.

## Summary (column of record)

- **Line-ups.** No universe produced an accepted line-up. Every reply that was asked for resolved to source sentences
  (ids are checked before anything else). The holds are named per group: declined by the model, rejected by the
  per-sentence check (TOPIC_ONLY), or rejected by a deterministic rule (Bitcoin screen, stand-alone claim).
- **Stories accepted:** the preview's (DataDash's claim), and on fresh_20261111_190259 "Bitcoin touched its 200 day
  moving average today."
  - 190259's on-screen videos have no sentence-ready word record in the store, so this CPU replay could not ask for a
    line-up. Production runs its word pass there.
  - The preview's line-up call DECLINED, although a line-up that passes our rules exists in the same offered rows:
    the must-pass test builds a four-segment one, about 62 s. That is a recall miss by the generator at the line-up
    step, the E-FAIL-043 class, and it is recorded as such.
- **What dominates the holds:** the per-sentence check, today's strict verify_support with the claim as the event.
  Channels describing one move with different reference points, or with a pronoun subject, are TOPIC_ONLY on their
  own. That is the same strictness that held today's selector (E-FAIL-043).
  - It is a model judgement, kept as the audit asked (C2-1), and not relaxed to make anything pass.
  - The product answer is law L-o's 01:55 amendment (same-development coverage is a packaging style, not integrity)
    and the moments-first packager (phase 2).

## Per defect: would the defect that held the run be possible under this contract?

**fresh_20261111_190259: E-FAIL-030.** `story_semantics.emergent_clusters` crashed on `sorted({None, ...})`. Four
hand-made whisper_words records carried no channel identity, and the chunker copied it into every chunk.
- The crash site is the clusterer, upstream of select_by_id and unchanged by R1. It was fixed at HEAD:
  transcript_store.chunks takes identity from meta.json and yields nothing without it.
- What the contract adds: a Source without channel_id and channel_name is refused by name (rule S2,
  `no_channel_identity`). It can never be a story sentence, a hook or a clip, and nothing ever sorts a missing name.
- In the replay, the run's universe identities come from the universe record, and the run was replayed end to end.
- **Not possible in selection.** The crash class is outside this contract and fixed upstream.

**fresh_20261111_213954: E-FAIL-033 and E-FAIL-034.**
- E-FAIL-033: a 35.28 s "sentence" came from an unpunctuated decode.
  - **Not possible on screen.** A span with a boundary inside an unpunctuated stretch fails T5 (`unpunctuated`).
  - A word record that needs restoration is not sentence-ready (S7, law L-e), so it is never offered to the line-up
    call.
  - As evidence, the story table offers only sentences eligible as evidence, and T5 applies there too.
- E-FAIL-034: headline-shaped candidates split the conversation.
  - **Not possible.** The contract reads the DEC-13 clusters themselves: the channels' own sentences, widest cluster
    first. A wire headline is evaluated only after every cluster tier, and then only as a hint, never as the claim.
- In the column of record, this run's 8 story calls ended 6 declined and 2 rejected. The "$73,000 / 200-day moving
  average" cluster was rejected by the per-sentence check (two sentences TOPIC_ONLY against the claim). The same
  development was accepted on fresh_20261111_190259 ("Bitcoin touched its 200 day moving average today."), and the
  blind oracle found it on tonight's universe.

**fresh_20261112_001448: E-FAIL-036, E-FAIL-037, E-FAIL-038, and coverage after rewrites.**
- E-FAIL-036 / 037 (caption entities; split Whisper tokens): **not possible.** Nothing the model writes is ever
  matched back to a transcript. The text the model sees and the text that leaves the module are
  transcript_store.read_text (law L-h), so entities are decoded and split tokens read whole.
- E-FAIL-038 (the claim re-read as another event): **not possible.** There is no query derivation. The claim is a
  source sentence (law L-i: the claim is the event, verbatim). ModelChecks' event is that sentence, with its own
  names as the key entities.
- Coverage after rewrites: **not possible as it happened.** Every channel's sentence is now judged against the claim
  sentence itself (verify_support per story sentence, audit C2-1), never against a model rewrite. The judgement is
  still a model's, and strict; see the preview row below.

**fresh_20261112_013452** (the order's `_014204`, assumption A1): coverage / currentness, and only one layout-eligible
channel.
- The layout rule is deterministic: a story whose sentences come from fewer than two layout-eligible channels is
  refused by name (G3, `story_layout_channels`). Today this was found only after the model work.
- Currentness is the source's own upload age (S5) plus `presented_as == current` (ModelChecks).
- **The hold reason cannot recur as a hidden defect.** A one-layout-channel story is refused at once and says so.

**fresh_20261110_093150 (Nov 10): E-FAIL-043.** The selector missed the day's known line-up. The preview's story
reached today's selector only as a wire headline and stopped at "currentness missing"; the best cluster stopped at
"only 1 layout-eligible channel".
- Under the contract, the cluster pool runs first, and the preview's own four sources are tested directly in the
  preview row.
- In the column of record, the preview's story is ACCEPTED (DataDash's claim, every member SUPPORTS at temperature 0),
  and the line-up call DECLINED. A line-up that passes our rules exists in those rows, so the miss is the generator's,
  at the line-up step.
- In the sensitivity column, with the judge at its default temperature, the same story was rejected: the judge rated
  other channels' sentences TOPIC_ONLY on all three attempts, with different ids each time. For example, Natalie
  Brunell's "It went from above $81,000 after the election to below $75,000 by the weekend.", which has an unstated
  actor and other reference prices.
- The judge's setting therefore decides this story. Production runs at temperature 0. Nov 10's own universe: 8 story
  calls, 6 declined, 2 rejected.
- Law L-o's 01:55 amendment moved "same development from >= 2 channels" out of integrity into a packaging style, and
  L-w 3 keeps story-first as a package type for when >= 2 channels DO cover one development. The moments-first
  packager (phase 2) is the route for the preview's kind of video.

**fresh_20261112_050611 (tonight, live): HOLD at editorial ("no candidate is producible").** The blind oracle's
line-up 1 passes our rules (ORACLE.json sha256 e923e91f...).
- Its story: "Bitcoin dropped to around $73,000 and found support at its 200-day moving average", with an Altcoin
  Daily hook, two Coin Bureau clips and a The Bitcoin Layer clip, on caption-line timing.
- In the column of record, the replay's 8 story calls ended 5 declined and 3 rejected, and one cluster needed no model
  call. Cluster 0 (Altcoin Daily, Bitcoin Magazine, ...: the oracle's development) was rejected by the per-sentence
  check (ids 37 and 45 TOPIC_ONLY). Two clusters were rejected because the claim did not stand alone. No story was
  accepted, so no line-up was asked: the same hold as the live run, now with a named reason per cluster.
- Note for phase 2: the oracle's line-up takes two clips from one channel, which law L-u (02:30) now refuses.

## The preview (pinned_20261111_172202): overlap with its four approved passages

Generated into the table. Reported honestly:
- The approved hook (DataDash) and the two approved clips (Natalie Brunell, Yahoo Finance) are word records that pass
  every on-screen rule with the right story statements (TestRealPreview).
- The approved Bitcoin Magazine clip is never on screen: has_chyron (DEC-12d), and its window transcript is not
  sentence-ready (NOTE-PS5).
- The approved trio estimates ~54.4 s, below L-o's 60 s; the four approved passages ran 71.08 s on the final, above
  70 s. The tolerance is PBX's call.
- In the column of record, the story is accepted and the line-up call declined. With the model's own story:
  - DataDash's hook and Yahoo Finance's clip are eligible on screen;
  - Natalie Brunell's approved clip holds no sentence the model marked as a story statement (`no_story_statement`);
  - Bitcoin Magazine's clip is layout-ineligible and not sentence-ready.
