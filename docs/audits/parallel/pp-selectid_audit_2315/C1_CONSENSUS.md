# pp-selectid audit of the ledger build path (ruling 2, 22:40): cycle 1 consensus (synthesis by the pp-selectid session, 23:22 ET Nov 12)

**Run.** C1_STEP.diff is 21,663 bytes; the prompt is 42,836 bytes. Reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions.
- qwen/qwen3.8-27b (Heimdall, effort none): two P0s, both refuted below.
- z-ai/glm-5.3-flash (Heimdall, effort none): "P0: none provable".

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | the punctuated record is not read first; a broken punctuated record falls through to the verbatim one (qwen P0-1, glm P0-2) | REFUTED on the sort, and now tested. `key=lambda p: "punct" not in p` gives the punctuated file False, which sorts BEFORE True: the punctuated record is read first. The fall-through to a verbatim record that is itself sentence-ready is law L-e's own rule (E.sentence_ready: punctuation restored OR no stretch that needs restoring), as in the selector. Test: test_the_punctuated_record_is_read_first |
| K2 | the snap can change the meaning (up to 3 words per edge) while the ledger's scores and risks are kept (grok P1, glm P1-1) | IMPLEMENTED: a word the snap would ADD may not be a negation (not, no, never, nobody, ... n't) or carry a digit (SNAP_GUARD); such a row is dropped with why. Those are the words that flip or add a claim the ledger's judgment never saw. The rest of the snap (at most 3 words of the record's own sentence) stays: the ledger row is discovery, and the word record's whole sentences are what every gate judges (step A, exclusion, fidelity, context) and what the pin locks. Tests: test_a_snap_never_adds_a_negation_or_a_number ("can stop Bitcoin" would gain "Nobody"; "Bitcoin started ..." would gain "In 2009"), and the exact 3-word boundary (3 snaps, 4 refused) |
| K3 | the delivered pins are hard-coded in the driver (qwen P1-3, glm P1-4 / P2-8) | IMPLEMENTED: --delivered PIN ... (default: tonight's two delivered pins); a missing or broken pin file stops the run (fail closed) |

## Unique findings, evaluated

| finding | disposition |
|---|---|
| grok P0: an empty successful read is "quiet" | REFRAMED, docstring corrected. A FAILURE or a REFUSAL raises (tested). An empty successful read is a real result: no row passes the ledger's own exclusions, the report's counts say why, and no pin can come of it. Test: the empty-read case returns ([], report) |
| glm P0-1: a record with no transcript_sha256 passes vacuously | REFUTED: None != segments_sha256(...), so it is skipped. A segment edited after its sha was taken is caught too (new test) |
| qwen P0-2: the snapped span may not be sentence-ready | REFUTED: sentence readiness is a property of the RECORD (E.sentence_ready), and the Span is whole sentences k0..k1 of that record by construction |
| glm P1-2: the report cannot tell "no record" from "sha-broken / not sentence-ready" | IMPLEMENTED: word_source returns why, and the report counts no_word_record_why by reason |
| glm P1-8 / P1-9: a malformed row or a non-numeric time crashes instead of being counted | IMPLEMENTED: a malformed row is a counted drop (report.malformed, tested); an unreadable time only widens the anchor's search |
| glm P1-6: --hours is truncated to an int for the horizon | IMPLEMENTED: the float is passed |
| glm P2-6 / P2-7 / P2-10: provenance not asserted, the clock-skew message, a circular sha test | IMPLEMENTED: the scores provenance is asserted; the "does not anchor" message names the searched window; the sha test now edits a segment after the sha |
| qwen P1-1: the Source takes rs[0]'s channel identity | KEPT: rows are grouped by video, and a video has one uploader channel |
| qwen P1-2: SEARCH_PAD_S = 30 s may be small for caption drift | KEPT: captions and word records share the full-video clock; a miss is a counted, named drop |
| glm P1-10: overlapping spans of one video are both kept | KEPT: one line-up never holds two moments of one channel (the supply exception needs two different videos) |
| glm P1-3 / P2-1 / P2-2 / P2-4 / P2-5 / P2-9 | KEPT: cosmetic or unreachable as written (the child's keys fail closed by KeyError; anchor returns a 3-tuple or None) |
