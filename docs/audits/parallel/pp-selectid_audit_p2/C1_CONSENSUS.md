# pp-selectid PHASE 2 audit: cycle 1 consensus (synthesis by the pp-selectid session, 2026-11-12, ET)

The package is the repo's utils/cross_llm_audit.py build_audit_package, run on two chunks of the phase-2 diff (each
chunk under the 220,000-byte limit):

- A_core: pipeline/*.py and model_providers.json.
- B_tests_docs_wiring: tests, design doc, REQUESTS R7/R8.

The question is QUESTION.txt Q1-Q5.

Reviewers, each named in its file:

- claude-fable-5-2, claude-opus-5-5 and claude-sonnet-5-5 (effort high);
- grok-4.20-0309-reasoning (temperature 0, no tools);
- the tool's own gpt-4o leg, which FAILED with HTTP 429 (no credit) on both chunks.

Four reviewers per chunk.

Scores (Q1 / Q2 / Q3 / Q4 / Q5):

| chunk | fable | opus | sonnet | grok |
|---|---|---|---|---|
| A | 35/70/75/40/15 | (no table) | 38/66/58/40/30 | 72/88/93/55/45 |
| B | 35/45/40/30/50 | 35/45/30/40/50 | 35/45/45/40/50 | 82/93/88/75/78 |

Every finding below was checked against the code before its disposition. "Verified" means the defect is reproduced
from the code as written. "Refuted" gives the evidence.

The rule is consensus only. A finding raised by at least two reviewers (in either chunk) is implemented. A unique
finding is evaluated on its own evidence and either implemented or recorded with a reason.

## Unanimous or 3-4 of 4: implemented

### C1. The pin asserts the gates passed with literals
Raised by: A fable P0-1, opus P1-8, sonnet P1-4, grok P1; B fable P0-1, opus P0-1, sonnet P1-1.

**Verified:**
- package_pin.to_pin writes `"checks": {"vo_fidelity_ok": True, "context_integrity_ok": True}` and never reads
  `pk["checks"]`.
- R7's pinned.py patch tests these flags for truthiness only.
- The patch copies `package_sha256` and never recomputes it.

**Fix: a sealed GATE INVENTORY (the L-j pattern).** package.build writes `pk["gates"]` with a fixed set of rows:
- `vo_fidelity_deterministic`, `vo_fidelity_verdict`, `duplicate`, `price_now`, `runtime`;
- `context_a`, `context_b`, `context_c`;
- `exclusion`, `second_pass`, `coherence`.

Each row is exactly `"PASS"` with evidence: the back-end, n judged, and replayed false.

`package_sha256` is computed by one function, `package.seal()`, over a canonical serialisation of the gated bytes:
- segments (video_id, start, end, text, transcript_sha256);
- the VO intro, bridges and after_clip;
- the title and caption;
- the inventory.

Both package_pin.to_pin and the R7 patch recompute it:
- package_pin.to_pin refuses a package whose inventory is missing, not exactly PASS on every row, or replayed.
- R7 refuses any mismatch between the recomputed sha and the pin, and any pin VO, title or caption that differs from
  the sealed bytes.
- R7 also refuses a non-dict `moments_package`, `checks: null`, and a non-int or duplicate `after_clip`.

### C2. The blind fidelity verdict passes on `{"claims": []}` or partial coverage
Raised by: A fable P0-2, opus P0-1, sonnet P0-1; B fable P1-4, opus P1-11, sonnet P1-4.

**Verified:** vo_fidelity.check_verdict returns ok on an empty or partial claim list.

**Fix:**
- Every line slot must carry at least one claim; a slot with none is VERDICT_INCOMPLETE.
- The prompt says so ("every line, including a connective one, gets at least one claim; a connective line's claim is
  what it tells the viewer, supported by the manifest").
- A support run must be at least 3 canonical tokens, or the whole segment when it is shorter.
- A line's support may cite only its own cited segments or the manifest.

### C3. The exclusion verdict (L-u) never runs in production
Raised by: A fable P0-3, opus P1-3, sonnet P1-2.

**Verified:** `exclusion_verdict` is called only from the exam adapter. `usable()` trusts the miner's own `risk`.

**Fix:**
- package.build runs moments.exclusion_verdict on every segment of a line-up before any paid writing.
- It is cached per moment and run with `avoid_model` = the moment's miner.
- The window's text is the before/after context.
- An "exclude", or an unreadable verdict, drops the moment.
- A moment right after an ad-read marker sentence is excluded deterministically.

### C4. Law L-v 2 is optional, partial, one-directional, and passes "not measured"
Raised by: A fable P0-4, opus P1-2, sonnet P0-2; B fable P0-2, opus P1-3, sonnet P1-2.

**Verified on every point:**
- `if truth_dir:` with default None;
- the plain path skips it;
- the trigger covers numbers and negations only;
- `compare` is a one-way set membership over the padded window;
- `turn_change_inside: None` counts as clean;
- the offset is wrong when the clip starts within 1.5 s of the video head.

**Fix:**
- The second pass runs on EVERY segment of every package, written and plain alike.
- Without a work directory it is NOT RUN. That row is not PASS and the pin refuses.
- The comparison is bidirectional with counts (a critical token of either side missing or miscounted on the other).
- It is restricted to the second pass's segments overlapping the selection.
- Names are included.
- `turn_change_inside` must be exactly False.
- The offset is computed from the real window start.

The transcription goes through the Router (C9).

### C5. Step B need not rate every pair
Raised by: A fable P1-1, opus P1-1, sonnet (context section).

**Verified.**

**Fix:** step B must return exactly one relation for every unordered pair of labels (C(n,2)). A missing, duplicate or
extra pair is CONTEXT_UNAVAILABLE.

### C6. Attribution
Raised by: A fable P1-3, opus P1-5 and Q4, sonnet Q4; B fable Q4.

**Verified:**
- the colon form "X: ..." is unbound;
- the verbs are case-sensitive, so "Says" in a Title Case title is missed;
- `att_pool` is overwritten, so every number is checked against the LAST attribution;
- "according to" is searched inside the verb loop (29 duplicate violations);
- pronoun subjects ("she says") are unbound.

**Fix:**
- Attributions are found case-insensitively with their positions, the colon form included.
- Each number is checked against the pool of the attribution that governs it: the nearest preceding one in the same
  sentence, else the cited pool when none precedes.
- "according to" is searched once.
- A pronoun or lowercase-noun subject of a speech verb is ATTRIBUTION ("name the show").

### C7. NAME
Raised by: A fable, opus, sonnet, grok; B opus P1-10, sonnet, fable.

**Verified:**
- a Title Case line skips the rule;
- a sentence-initial single word is skipped;
- `_run_in(a, nt)` lets "Bitcoin Jesus" pass through the allowed term "Bitcoin".

**Fix: a lexicon test replaces the case heuristics.**
- A capitalised token that is not a lowercase English word (/usr/share/dict/words, with production words added) is a
  name candidate wherever it stands, in Title Case lines and at a sentence start alike.
- Each candidate token must occur in the cited sentences or the manifest terms, possessive and plural folded.
- Allowed terms no longer exempt a longer name that contains them.

### C8. RELATION
Raised by: A fable, opus, sonnet, grok.

**Verified:** false rejects ("how Bitcoin responded to the rate hike" with one cite; grok: "both agree" inside ONE
video) and misses ("goes further", "sees it the same way", "similarly", "concurs", "backs up", "while X says").

**Fix:**
- RELATION applies to a line that involves two or more parties: two or more cited segments, two or more credited
  channel names, or a plural party word ("both", "all three", "they all", "each other", "everyone").
- It fails only when those parties are from different source videos.
- The phrase list is extended.

### C9. L-x violations
Raised by: A fable P1-4, opus P1-9, sonnet P2.

**Verified:**
- transcript_truth hard-codes OpenAI's URL and model outside the Router (no failover, no ledger, no replay);
- `_writer_vendor` falls back to the literal "openai", and `prescreen` defaults to it;
- Heimdall's base URL is a class constant.

**Fix:**
- A role "transcribe" with two back-ends in model_providers.json: OpenAI diarised transcription, then ElevenLabs
  Scribe with diarisation (ELEVENLABS_API_KEY).
- Router.transcribe() walks that chain with the same down / record / replay / spend semantics.
- `_writer_vendor` reads the config and has no literal.
- `writer_vendor` is a required argument of prescreen.
- The Heimdall base URL lives in the config.

### C10. PRICE_NOW and current_levels
Raised by: A fable, opus P1-6, sonnet; B fable, opus P1-9, sonnet.

**Verified:**
- HISTORY exempts the whole line on "all-time", "since", "once" or any year;
- PRESENT counts "is", "are" and "just", so predictions and past levels become "current";
- `price_levels` treats any value of 1000 or more as a price ("640,000 bitcoin", "21 million");
- bridges are exempt.

**Fix:**
- PRICE_NOW runs on every VO line, title and caption.
- A price is a value with a money word next to it ($ / dollars / K or thousand in a Bitcoin price phrase), or a value
  of 10,000-500,000 after a price verb or preposition ("at", "to", "hit", "trading").
- A count of coins ("bitcoin", "BTC", "coins") is never a price.
- History must govern THAT number: a year or history phrase within the same clause, before it.
- "all-time" is no history marker.
- A current level comes only from a present-tense level sentence ("is trading at", "is at", "sits at", "right now
  at", "today at") with no modal, future or conditional word ("will", "could", "going to", "if", "by <year>",
  "target").

### C11. Context window, quoting and the precomputed step A
Raised by: A fable, opus, sonnet.

**Verified:**
- `window()` includes only sentences that start inside [t0 − 90 s, t1 + 60 s], so the window is AT MOST that, where the
  docstring and law say at least;
- `_q()` (quote_data) turns the window's own `<selected>` markers into ‹selected›, and silently truncates at 6000
  characters;
- `a.get("time_ok", "yes")` defaults a missing field to pass;
- the precomputed step A loses the back-end name.

**Fix:**
- The window extends to the first sentence starting at or before t0 − 90 s and the first ending at or after t1 + 60 s
  (capped at 180 s before).
- The transcript is escaped per sentence and the markers are added after escaping.
- A window over the excerpt limit is CONTEXT_TOO_LONG (fail closed, never truncated).
- `time_ok` has no default.
- The precomputed step A keeps its back-end per label.

### C12. A provider outage drops an innocent moment
Raised by: A fable P2, opus P2, sonnet P2.

**Verified:** `dropped |= bad or {order[-1]}`.

**Fix:** a violation with no segment (CONTEXT_UNAVAILABLE, RELATION_UNREADABLE) drops nothing. The angle's attempt
ends, recorded as unavailable.

### C13. Dead v1 code, and the L-u price-prediction cap lost
Raised by: A fable P2, opus P2, sonnet P2; B fable P1-7, opus P2-2, sonnet P2.

**Verified:**
- candidate_sets, WRITE_PROMPT, write, check_written and gates() are unused by build, and gates() lacks DUPLICATE and
  PRICE_NOW;
- the angle-first `lineup_for` LOST the L-u cap of at most one price prediction per video, which only the dead code
  had. Found through the reviewers' vacuous-test note.

**Fix:**
- The dead code is removed.
- `lineup_for` enforces the cap.
- The test has a positive case and a negative case.

### C14. FRAMING, IMPERATIVE and TIME lists
Raised by: A fable, opus, sonnet; B fable.

**Verified false rejects:**
- "exposure", "confirmations";
- "Short-term holders", "Sell-off fears", "Sell pressure";
- "breaking down", "record-breaking".

**Verified misses:**
- "torches", "debunks", "bombshell";
- "It's time to buy", "Don't sell", "you should probably buy", "You've got to buy";
- "just set / passed / hit" (partly listed), "overnight", "last night", "this month", "currently", "recently".

**Fix:** the lists are rewritten with word boundaries and the misses added. "breaking" counts only as "breaking news"
or "breaking:".

### C15. NUMBER exemptions
Raised by: A fable, opus, sonnet; B fable, sonnet.

**Verified:** a spelled number of 10 or less, and any unitless number equal to a package count, day or year, are
exempt ("seven countries", "four rate cuts").

**Fix:**
- A manifest number is exempt only beside a production noun (clips, channels, voices, shows, videos) or inside the
  show date.
- "one" is exempt only as a determiner or pronoun ("one thing", "one of", "one voice").
- Every other number word is checked like a digit.

### C16. DUPLICATE
Raised by: A fable, opus, sonnet, grok; B fable, opus P2-1, sonnet.

**Verified:**
- only the adjacent line and the title are compared (the real R8-2 incident was the intro against clip_03);
- the caption is never compared;
- the 60 % share counts function words.

**Fix:**
- Every VO line, the title and the caption are compared with EVERY clip.
- A run of 5 or more canonical tokens with at least 3 content words, or 60 % or more of a short clip's CONTENT tokens,
  is a duplicate.

### C17. Harness and proof tooling
Raised by: B fable, opus, sonnet.

- **yield_table.py.**
  - The "gates" column is a literal (verified) and now renders the sealed inventory.
  - A missing oracle directory reads as "no defect" (verified) and now reads as ORACLE MISSING.
  - The v1 "tried" keys are fixed.
- **proof_packages.py.** `--want 2` overwrote the top pin (verified: write_pin always writes MOMENTS_PIN.json).
  write_pin now takes the file name.
- **ab_roles.py.**
  - The verdict A/B was not blinded the way the exam is (verified). It now uses the recorder's blind().
  - The judge saw only one order (n = 1). It now judges both orders, and a split counts as a tie.
  - `next()` raised StopIteration. It now gives a clear error.
  - `--judge` was not checked against the compared vendors. It now is.
  - "local:gemma3:27b" was hard-coded. It now comes from the config by vendor.
- **run_exam_record.blind()** stripped nested origin / expected where the harness strips only the top level, plus
  provenance at any depth (moments_exam.py:117-129). It now mirrors the harness exactly.
- **The config test** checked only chain[0] of three verdict roles (verified). It now checks every verdict role
  (coherence and exclusion included): for EVERY possible writer back-end, the chain keeps at least one back-end of
  another vendor and another model family.
- **Vacuous or conditional tests are fixed:**
  - the punchline test, which was conditional;
  - the price-prediction test, which could never produce a set;
  - the `({"angles": []}, "angles")` substring;
  - content_range used as its own oracle (now literal 60-70 arithmetic).

### C18. Vendor separation is a single string
Raised by: B fable P1-6, opus P1-4, sonnet P1-3.

**Verified:** the angle and the VO may come from different vendors after a failover. The verdicts avoid only the last
writer's vendor.

**Fix:**
- `avoid_vendor` accepts a set.
- Every verdict avoids the vendors AND model families of every reply whose text it judges (angle writer, every writer
  attempt).
- Step A's prescreen avoids the vendors of the whole angle_write chain head, and is re-run when the final writer
  shares a vendor with it (as before).

### C19. Docs contradict code
Raised by: B fable, opus, sonnet.

- **§4b "4-8 moments".** The code accepts 3-8, which matches the orchestrator's "at least 3"; the prompt asks for 5-8.
- **§4 "regenerate once".** The code does up to 3 rewrites (orchestrator 03:40).
- **"No rule loosened" (§9).** It now names each narrowing and what covers it.
- **The REPAIR docstring.** It promises "extend backwards", which is not implemented (A fable, opus). The law permits
  dropping. The docstrings now say drop-only, and the unused `repairable()` is removed.

### C20. R7 item 4 has no patch
Raised by: B fable, opus, sonnet.

An exact release_auth.py patch is written beside the pinned.py patch. The moments seal is re-verified on the EDL, with
the title and caption in the attested set, and smoke-tested the same way.

## Two of four: implemented

### M1. The speaker is always the channel
Raised by: A fable P1-2, opus P1-4; B fable Q4.

**Verified:** `"speaker": s["channel"]`.

**Fix (L-v 1, "a person named only when verified"):**
- Step A answers "speaker_is": "host" / "guest" / "uncertain", with "host_evidence": exact words from the excerpt
  showing that the speaker is the channel's own host, or "".
- Code checks the evidence is a verbatim run of the excerpt.
- Only a segment whose speaker is "host" with verified evidence may be attributed to the channel by a speech verb
  ("X says").
- Every other segment is credited to the SHOW ("on X", "from X's show", "X's guest").
- ATTRIBUTION enforces this.
- The writer is told so.

### M2. The Router marks a back-end down for the whole run on a per-request error
Raised by: A fable P1-5, sonnet P1-3.

**Verified:** a local over-context prompt, or any other 4xx, takes the back-end down for every later role.

**Fix:**
- A new `RequestRejected` (per-request: 400 / 413 / 422, over-context, empty choices) skips that back-end for THIS call
  only.
- `Unavailable` (account, auth, rate-limit after backoff, 5xx, transport) still marks it down.

### M3. The spend guard fails open and blocks the free model
Raised by: A fable P1-6, opus P2; B fable P2, opus P2-4.

**Verified:**
- an unreadable ledger reads as $0 and is then overwritten;
- the guard checks after the fact, so two $10 calls pass a $15 limit;
- it stops the free local back-end too.

**Fix:**
- An unreadable ledger raises SpendLimit (fail closed); a missing one is $0.
- The check reserves the call's upper bound (prompt tokens estimated at 4 characters each, plus max_tokens, at the
  back-end's price) under the ledger lock before calling.
- A zero-price back-end is never stopped.

### M4. Runtime arithmetic
Raised by: A opus P1-7, sonnet P1-1; fable P2 (budgets).

**Verified:**
- `vo_s` subtracts the standard sign-off a second time (FIXED_S already excludes it), so the estimate is about 6.9 s
  short;
- `content_range` and `budgets` omit the sign-off;
- `budgets` gives 40 % + 30 % per bridge, so a 1-bridge VO under-fills.

**Fix:**
- runtime = segments + FIXED_S + (intro + bridges + sign-off words) / WPS.
- content_range and budgets subtract the standard sign-off.
- Bridges share 60 % of the VO budget.
- The runtime is checked before any paid verdict, and a plain VO that cannot land 60-70 s is not gated.

### M5. The exam adapter makes must-fail cases pass vacuously
Raised by: A fable P1-7, sonnet P1-5.

**Verified:** a ReplayMiss or an outage answers "fail" / "exclude". The pp-tests harness counts a crash as ERROR
(test_moments_gates.py:367-378) and "uncertain" as a reject.

**Fix:**
- An unmeasured gate (ReplayMiss, every back-end unavailable, an unreadable verdict) RAISES GateNotMeasured, which the
  harness counts as ERROR.
- A deterministic failure is still a measured "fail".
- The adapter passes `current_levels` when the case carries them.

### M6. Malformed replies crash with TypeError
Raised by: A fable P2, sonnet P2.

**Verified:** an unhashable `line` or `segment`, and relation labels.

**Fix:** every model-supplied field is type-checked before use. A malformed reply is a contract violation (fail
closed), never a crash.

### M7. Coherence "None."
Raised by: A fable P2, sonnet P2.

**Verified:** "None." and "none - unrelated" count as a through-line.

**Fix:** any through-line that, once normalised, is empty, starts with "none", "no through", "n/a" or "unclear", or is
under 4 words, is no through-line.

### M8. QUOTE
Raised by: A fable Q4, opus Q4/P2.

**Verified:** single-quoted text is unchecked, a one-word quote is skipped, and a quote may come from any cited segment.

**Fix:**
- Curly and straight single quotes are recognised (an apostrophe inside a word is not).
- Every quoted run of 1 or more tokens must be verbatim.
- When attributed, it must come from the attributed speaker's segment.

### M9. Angle text in the writer prompt
Raised by: A fable P2, sonnet P2.

**Verified:** the angle enters WRITE_V2 unescaped with its newlines.

**Fix:** the angle passes through quote_data, is collapsed to one line and capped at 300 characters. It is never
audience-facing, and the pin's label is the constant "bitcoin" (see R1 below).

### M10. The split key-file literal
Raised by: A fable P1-4, B fable P2, opus P2-8.

The literal was written so that file text could pass the shell gate (pre_bash_gate.sh), which blocks commands naming
that path. It hid nothing: the path is the one the order names, and phase 1 writes it plainly
(proof_saved_runs.py:44). It is now ONE plain constant, `providers.ENV_PATH`, imported everywhere. The Router's default
is that path, not the worktree's.

### M11. A missing speaker measurement counts as usable
Raised by: B fable P1-5, opus P1-2.

`turn_change_inside` is None at mining time, because the measurement is L-v 2's at packaging time. `usable()` keeps
None as a CANDIDATE only. The package's `second_pass` row requires a measured False for every segment, so the pin
refuses an unmeasured one. The test now says so.

### M12. The smoke test
Raised by: B opus P2-6, sonnet.

`patch -p1` (fuzz allowed) is replaced by `git apply --check` + `git apply`.

The copy-equals-copy sha assertion is replaced by a recomputation. New refusal cases:
- a tampered VO with a stale sha;
- a truthy-string flag;
- a non-dict package;
- `checks: null`;
- a duplicate or boolean `after_clip`;
- a replayed verdict.

## Unique: evaluated one by one

| # | finding | disposition |
|---|---|---|
| U1 | the Router caches an invalid reply and serves it again for the same seed (fable P2) | IMPLEMENTED: `Router.reject(reply)` deletes the recording of a reply the caller found out of contract (every strict parser calls it); the angle call re-asks once with a new seed. A served recording in a live run is marked `cached`, distinct from offline `replayed` |
| U2 | novelty by exact moment_id: a re-punctuated record defeats it (fable P2) | IMPLEMENTED: delivered = (video_id, start, end) intervals; a moment overlapping a delivered interval of the same video is unusable |
| U3 | AD_MARKERS false-rejects "sponsored the bill"; the sentence after an ad marker is offered (fable P2) | PARTIAL: the false reject is fail-closed and kept; the after-marker sentence is excluded in production (C3, deterministic) |
| U4 | FRAMING compares raw text outside canon (fable P2) | KEPT: the same regex runs on line and source, so the comparison is symmetric; canon would fold inflections the lemma list already covers |
| U5 | "M1 says no new selector" (fable) | SUPERSEDED: the orchestrator's phase-2 order (01:55) commissions moments.py / package.py |
| U6 | trend_brief has one back-end (fable P1-4) | KEPT as documented: its second back-end is the free local baseline (code), which the run uses when the search back-end is down; SHADOW weight 0 (L-w 4). The config test asserts the fallback exists |
| U7 | in replay, a missing recording for back-end 1 serves back-end 2's (opus) | KEPT: that is the live run's own failover; `Reply.tried` names the skipped back-end, and the pin refuses replayed verdicts (C1) |
| U8 | vendor is not model family (opus) | IMPLEMENTED: each back-end has a `family` in the config; verdicts avoid the writer's families (C18) |
| U9 | `window_sources` crashes on age None (opus) | IMPLEMENTED |
| U10 | `audio_window` startswith collision (opus) | IMPLEMENTED: exact base name + extension |
| U11 | plain title `[:70]` cuts a name (opus) | IMPLEMENTED: whole names only; channels beyond 70 characters become "and others" |
| U12 | replay key omits the model digest; R7 ignores replay (opus B) | PARTIAL: the pin refuses replayed verdicts (C1); recordings are keyed by back-end name and kept as evidence of what was asked |
| U13 | a failed trend brief is cached for the cycle (sonnet) | IMPLEMENTED: only an "ok" brief is cached |
| U14 | PRICE_NOW tolerance 5 % passes 74,000 against 74,210 (grok A) | REFUTED: 0.3 % is rounding, which the tolerance exists for; a stale level is tens of percent away (16K / 126K against 73K) |
| U15 | yield_table counts the same files twice (grok B) | REFUTED: `passed` reads `<day>/moments/JUDGE_L*.json`, `story` reads `<day>/JUDGE_L*.json` (yield_table.py:24-33), two directories |
| U16 | a whitespace-only bridge passes R7 (grok B) | REFUTED: `not str(...).strip()` rejects it; tightened anyway to need a word character |
| U17 | the plain VO is not re-gated (grok B) | REFUTED: package.py:634-641 runs integrity() on the plain package before keeping it; it now also runs exclusion and L-v 2 (C3 / C4) |
| U18 | pin label / headline put model text on screen (fable B Q3) | REFUTED: package_pin.py `"label": "bitcoin"` (a constant), `"headline": pk["title"]` (the gated title) |
| U19 | angle ids: unknown ids silently dropped? (fable B, opus B) | REFUTED: check_angles raises on any id not offered (package.py:419); the message now names the unknown id, and a test covers ["a","b","c","zz"] |
| U20 | R7 runs `_generate_vo_script` before overriding it (sonnet B) | IMPLEMENTED in the patch |
| U21 | `approved_text_similarity` is mocked; transcript sha not checked (fable B) | KEPT: the sentence law (unchanged, shared) locates the words by text at render time; the pin carries `transcript_sha256` per segment for the record |
| U22 | `quotable=3.0` rejected though L-l calls an integral float harmless (fable B, sonnet B) | KEPT (fail closed): the miner contract asks for integers, and a re-ask costs one call. Recorded |
