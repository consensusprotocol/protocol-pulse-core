# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-12 02:27 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
The automated Protocol Pulse "Pulse Check" medley (pipeline/run_fresh.py) cuts hooks and clips from
partner YouTube videos, renders 16:9 and 9:16, and runs QA gates. PBX watched the 2026-11-10 cut and
found editorial errors every gate had passed: the opening word sounded clipped (D1), clips started or
ended mid-sentence (D2/D3), credit avatars were warped (D4), the vertical was letterboxed (D5) and
channel changes were abrupt (D6). This work makes the gates catch what a human caught, proves it on
yesterday's files (tests/fixtures/pulse_20261110, pipeline/test_pulse_20261110_mustfail.py), fixes the
causes, then requires three clean fresh videos in a row with no code edits between them.

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
- SENTENCE LAW: a clip's first word is the first word of a sentence and its last word the last word of
  a sentence. Boundary = transcript punctuation at a place a listener hears as the break between the two
  words (DEC-10, 2026-11-11: no minimum pause; the 01:50 order's 80 ms is recalibrated to the approved v2f
  reference, whose edges measure 0-10 ms; pipeline/sentence_law.py states every constant with its
  measurement). An unpunctuated transcript stretch has NO boundary
  (fail closed). Punctuation is added at transcription time only from a second, prompted ASR decode of
  the same audio, onto aligned verbatim words; the words never change (pipeline/punctuation.py). No
  language model decides a boundary (the per-gap adjudicator called 19/19 gaps sentence ends; removed).
- SELECTION LOCK: the words a clip must contain are fixed at selection time (selection_lock in edl.json,
  sha256-sealed). No later stage may recompute expected first/last words from a moved cut.
- SNAP LIMIT: a cut may move only inside the heard gap between the chosen sentence and its neighbour
  (the previous word's offset .. the next word's onset, at speech - 6 dB); it may never add or drop a word.
  A short gap is cut at the envelope minimum between the two words, never rejected for its length (DEC-10 d);
  its fade sits inside the gap (L-b: 2 video frames = 83 ms when it fits, down to 10 ms).
- NEIGHBOUR (DEC-10 c-ii): NO audible part of the neighbouring word: every frame the cut keeps on the
  neighbour's side of that minimum stays below the valley threshold (local speech - 12 dB) after the fade.
  A window is rejected for its edges only if this, the 85 % edge-word rule or sentence-completeness fails.
- ONSET/TAIL: edge words keep >= 85 % of their duration in the render (a floor for timestamp noise, never
  permission to trim: L-b below). The START OF PLAYBACK keeps the D1
  rule unchanged: a source that starts speaking at its file head, and the hook, need >= 80 ms of genuine
  sub-speech audio before the first onset or a declared room-tone lead-in pad; codec zero/padding is not
  room tone. Inside the video there is no lead / tail minimum (DEC-10: v2f's approved edges: 0 ms).
- CREDITS: round avatars of the channels actually used; the avatar is the channel's real square avatar,
  never a video thumbnail, never a generated placeholder; G12 / G15 measure the brand-red rings the renderer
  draws and G15 checks each disc is the credited channel's registered avatar (DEC-11).
- L-a SIGN-OFF NAMES ALL (PBX, 2026-11-11): the sign-off voiceover names every channel on the credits card, and the spoken set, the card set and the clips used are identical.
  Check: run_fresh.stage_voice HOLDs before render unless the script names exactly credit_rings.credit_channels(edl) (hook first, then clips); G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off and requires spoken == credited (registry names + aliases); VO stems are keyed by hash(text, voice, model). Must-fail: the 2026-11-11 preview (DataDash missing). Must-pass: v2f.
- L-b EDGE WORDS WHOLE (PBX, 2026-11-11): a fade never overlaps an edge word: the first and last word of every clip are heard whole, at full level, with their natural decay.
  Check: sentence_law.edge_fades places each machine-cut fade (2 frames, shortened down to 10 ms) inside the gap next to the cut, measured from the cut point's level; G17c (sentence_law.gate_g17_edges) requires every frame of both edge words within 1 dB of the unfaded source. Must-fail: the preview's Natalie Brunell tail ('...participated in the Monday rally.'). Must-pass: the L-b re-cut of it; v2f's edges except its two recorded legacy edges.
- L-c DISSENT IS RIGHT UNTIL DISPROVED (PBX, 2026-11-11): a check that disagrees with the others on an edge word is treated as right until an acoustic comparison against the source proves otherwise.
  Check: run_fresh.stage_gates: a dissenting G3b reading (DEC-12f) or a G3c head / tail failure on an edge stands (HOLD / FAIL) unless G16's neighbour_clear passes and G17c, MEASURED ON THE FINAL FILE OF THAT FORMAT (sentence_law.edges_on_final: the bytes being approved, their constant gain removed, every frame of the edge word compared), passes for that edge; a proof from the prepared clip is never accepted (amended by the orchestrator addendum 2026-11-11 '22:00', GPT-cut F03). Test: test_release_auth / test_word_diff TestSpanMatches; sentence_law.edge_word_fidelity refuses an alignment that leaves a word frame uncompared (GPT-cut F07).
- L-d PROTECTED PREVIEW (PBX, 2026-11-11): the PBX-approved preview of 2026-11-11 is a protected reference.
  Check: pipeline/regression.sh step 6 (pipeline/check_preview_reference.py): its selection locks, cut points and 9:16 layout must reproduce with the current code; tag ref-pulse-preview-2026-11-11; references/pulse_preview_2026-11-11 (read-only, SHA256SUMS).
- L-e PUNCTUATED BEFORE READ (2026-11-11): Every word transcript the sentence law reads, the editorial word pass included, has its sentence punctuation restored from a prompted second decode of the same audio before any sentence is read.
  Check: transcript_store.acquire(prefer_words) returns only a sentence_ready record: the verbatim decode where no stretch reads unpunctuated, else a whisper_words_punct record (marks from a large-v3 batched reference decode with punctuation.PROMPT, onto aligned words only, plus a sentence-initial capital where both decodes end a sentence right before the word, so editorial start_is_boundary reads the reference's own evidence; word keys and timings unchanged; the verbatim record kept; one Whisper model on GPU0 at a time); editorial_select's word pass treats any other record as failed. Must-fail: Altcoin Daily Ov5jg52HqIY's verbatim record (its quote read as one 35.28 s sentence). Must-pass: its restored record (the quote's sentence 161.14-170.08, "Even thinking about the seasonality, ... the midterms.", a valid 8.94 s hook window). Test: pipeline/test_punct_word_pass.py.
- L-f CHANNELS FIRST (DEC-13, orchestrator 2026-11-11 18:00): Story candidates come from the channels' own conversation first: clusters of statements by at least two independent channels, screened for Bitcoin before any model call, with the claim written from their shared statements and their quotes attached; wire headlines are evaluated only after every cluster is exhausted.
  Check: editorial_select pools channel_clusters_48h -> channel_clusters_72h -> wire_headlines (a pool runs only when every earlier one produced nothing); cluster_entry (>= 2 channels with a Bitcoin statement, 48 h tier then 72 h max, else stopped with no model call; one statement per channel); a cluster's coverage adjudicates its own statements; every cluster's ledger entry names its channels, claim, statements, counted quotes and the gate that stopped it; a validated model reply is cached by sha256(model, its Ollama digest, context, max_tokens, prompt). MIN_COVERAGE_CHANNELS 2, hook >= 4.0, stand-alone, topic and sentence laws unchanged. Must-produce: today's $74K-pullback statements (4 channels) and ETF-outflow statements (2 channels) reach the model (under the old rule they were in no cluster). Must-not: Bloomberg's Fed-hike and Natalie Brunell's ETF-outflow statements never share a cluster. Test: pipeline/test_dec13_clusters.py.
- L-g WRITTEN FORMS (2026-11-11): A check that reads speech counts a word the ASR wrote as a symbol as the spoken word ('$40 trillion' = '40 trillion dollars', '50%' = '50 percent'), and reads the expected word the same way.
  Check: segment_v1/qa_gates._g3b_words: G3b's readings, the EDL's last word and its next word are read with the same rules (symbols spelled out in spoken order, abbreviated scales too ('$40M' = '40 million dollars'), a 'dollars' the ASR also wrote never doubled; thousands separators and trailing full stops dropped, other commas split words, decimals kept; a leak is any word of the next source word heard after the last word); vote rule and thresholds unchanged; G17c still compares every edge word with the source. Must-pass: the approved v2f's 9:16 clip_02 '... above 40 trillion dollars.' (read 'above $40 trillion' twice). Must-fail unchanged: Nov 10's Natalie tail against 'week.'; a cut 250 ms into 'rally'. Test: pipeline/test_g3b_majority.py.
- L-h TEXT READ AS SPOKEN (2026-11-12): Transcript text is read as the words it stands for before any chunk, quote check or model sees it: caption HTML entities are decoded ('S&amp;P' = 'S&P') and a Whisper word split into tokens is read whole ('$81 ,000' = '$81,000'); the stored record is never rewritten.
  Check: transcript_store.read_text builds every chunk's text; story_semantics._norm decodes entities and joins split tokens for quote checks; the embedding cache is versioned (t2) so vectors match the read text. Must-fail / must-pass: Altcoin Daily's 'S&P 500' quote and Natalie Brunell's '$81,000' quote against their real excerpts (pipeline/test_caption_entities.py).
- L-i THE CLAIM IS THE EVENT (DEC-13 a) (2026-11-12): A channel cluster's claim is the event its coverage is judged against: its query is derived from the claim alone and the model never re-reads it as another event.
  Check: story_semantics.derive_story_query: a transcript_cluster item is derived from the claim with CLUSTER_NOTE (no label summary) and its underlying_event is the claim verbatim (the model's reading kept as underlying_event_derived); wire items byte-identical. Test: test_caption_entities TestClusterClaimIsTheEvent; real model (DoD 20:13): Natalie Brunell and Coin Bureau then both count for the election sell-off / ETF-outflow claim.
- L-j RELEASE IS AUTHORISED ON THESE BYTES (red-team order 2026-11-11 '21:55', A): 'all release gates passed' means every REQUIRED gate ran, on samples, unwaived, on exactly the bytes that are sent.
  Check: pipeline/release_auth.py is the one authorisation every send path uses: exact gate inventory v1 (REQUIRED rows exactly 'PASS' with evidence executed and samples >= 1; MONITORING rows present with an exact verdict, reported, not deciding: addendum '22:15' item 4; any other or missing row = blocker); run_fresh writes ATTESTATION.json last (holds anywhere = HOLD; executed code at the launch revision; the finals and manifests must be the bytes the gates measured); authorise() re-hashes both finals, EDL, manifests, gate report, verification pack and sheets before the first send; telegram.deliver_run checks each file's digest again before its send, checkpoints every message, never resends an unknown outcome; the legacy send_telegram_preview is removed; replays are never deliverable. Tests: test_release_auth.py (the fail-closed mutation family), test_telegram_delivery.py, test_failure_blocks.py.
- L-k ONE CANONICAL FORM (orchestrator 2026-11-11 '21:10'): every text comparison in the pipeline uses pipeline/canon.py; two strings a listener hears as the same words compare equal, and a different number, unit, sign, name, negation or dropped word never does.
  Check: canon.canon_tokens / canon_aligned / same (entities, unicode, split tokens, numbers as values, currency and percent spoken order, signs, apostrophes kept); routed into quote verification, selection anchors, edge words, G3 / G3b, G18 (word_diff keeps units and signs; a repeat-only difference is decided by the audio, sentence_law.span_matches: GPT-cut F04 / F05), G20, G1 / G13 (token runs, never substrings), PIN approved text. Tests: test_canon.py (200 real sentences x mutations equal; real differences unequal; TestSites fails any ad-hoc normaliser outside canon.py).
- L-n DELIVERY IS THE MEASURE (orchestrator 2026-11-12 '01:50'; PBX 01:43: "pls lock these changes into law"): the pipeline exists to deliver publishable videos, and the one number reported to PBX is videos delivered per day. A HOLD on a day when a legal line-up existed in the sources is a DEFECT of the selector (a miss), not a safe outcome.
  Check: every HOLD at editorial (or, under L-q, at mining / packaging) runs the blind oracle + judge on that run's universe (pipeline/oracle, branch pp-backtest, once merged); when it finds an accepted line-up the miss is logged with the first stage that lost it (MISS record in the run dir) and goes to the bible. Not yet wired. Tonight's instance: fresh_20261112_050611 HELD at editorial while the oracle's line-up 1 was judged LEGAL (ORACLE.json sha256 e923e91fa3d05621844449244100ded681c916bf8d06d0aa4a7ec3f9e64bc77a): a miss (E-FAIL-043 family).
- L-o INTEGRITY IS HARD, TASTE BENDS (orchestrator 2026-11-12 '01:50', amended '01:55' with L-q): two classes of rule, never mixed. INTEGRITY (hard, fail closed, never relaxed to ship): (1) every clip is verbatim whole sentences, what is spoken matching the locked sentences word for word (G16 / G18); (2) intact edges: no clipped or faded edge word (G17, L-b); (3) each clip stands alone, or is made to stand by the VO line before it WITHOUT changing its meaning; (4) Bitcoin-only; (5) >= 2 channels per video; (6) recent content (currentness); (7) credits card = EDL set = spoken sign-off set (G12 / G15 / G20, L-a); (8) release authorisation bound to the exact bytes (L-j); (9) nothing measured is never a pass (L-m, branch hardening-redteam); (10) the partner / guest source rule; (11) VO FIDELITY (new, '01:55'): the VO never puts words in a speaker's mouth: it may not attribute to a speaker a claim, stance or number that is not in that speaker's clip, may not imply two speakers were answering each other when they were not, and every fact the VO itself asserts is supported by a clip in the video or a verified source in PROVENANCE; a VO-fidelity check with must-fail fixtures must exist before any moments-first video is labelled a pass. REMOVED from integrity by the '01:55' amendment: 'same development from >= 2 channels' (now one packaging style among several, L-q). TASTE (targets that RANK candidates, never reject one when nothing better exists): the 8-12 s hook and 12-20 s clip duration windows; the hook / clip score floors; a sentence opening on a conjunction ('And', 'So', 'But') when it still stands alone in context. A whole sentence always beats a duration window: selection prefers passages inside the targets, and when no line-up fits inside them it takes the best legal line-up outside them and records each deviation and its size in PROVENANCE and in the Telegram caption. The only hard duration rule is the format: total runtime 60-70 s (PBX's format).
  Check: EVIDENCE asked by the '01:50' order (no number invented): CLOCK: the windows are measured on SENTENCE-LOCKED WHISPER WORD timing, never caption timing (editorial_select.py:49-50 define them, :1180 applies them; the words come from transcript_store.acquire(prefer_words=True), editorial_select.py:880, and only a sentence_ready record, whisper_words / whisper_words_punct, transcript_store.py:404-410, counts); the blind oracle's durations are caption-line timing, another clock, which a pinned run re-measures on locked words. APPROVED PASSAGES (locked word span): Nov 11 preview hook 9.08 s, clips 12.34 / 18.70 / 16.66 s; v2f hook 9.02 s, clips 10.70 / 11.54 / 14.44 s: PBX approved every length from 9.02 to 18.70 s, two clips under today's 12 s minimum among them; tonight's near-misses missed a window by 0.10-1.86 s (hooks 12.12, 12.74, 7.88, 7.0, 6.14 s; clips 11.9, 11.14, 11.02, 8.74 s). FORMAT: the approved preview's finals run 71.08 s (both formats), 1.08 s over 70; its four passages fill 58.17 s of the final, leaving 12.91 s of VO, cards and transitions. PROPOSAL: no fixed per-passage outer bound (no evidence supports one: nothing was ever rejected for a passage's length, and the approved range already spans 9.02-18.70 s); the one hard bound is the line-up total, checked BEFORE render where the line-up is chosen (selector / packager): passages + VO + fixed cards inside the 60-70 s format, i.e. at the preview's measured 12.91 s of non-passage time, passages totalling about 47-57 s; any per-passage limit is then arithmetic (70 s minus the fixed time minus the other passages), never a constant. For PBX: the approved preview itself ran 71.08 s; whether the format is checked on the final's runtime with a tolerance is PBX's call. WIRING (code change; two audit cycles; must-fail tests proving every INTEGRITY rule still rejects): into the moments-first miner / packager (L-q) and the shared validation (sentence lock, pinned validation); the story-first selector is retired ('01:58'). Until wired, the existing code still applies the windows and floors as hard filters.
- L-p CADENCE (orchestrator 2026-11-12 '01:50'; PBX 01:43: "i need one new video every few hrs once this thing is live and operational. ideally every 3-5 hrs"): once operational the target is one NEW video every 3-5 hours; it supersedes the daily target as the goal, and the daily rate remains the first milestone. No schedule is installed without PBX.
  Check: design consequences, requests and notes, no code yet: (1) NOVELTY: a video is NEW when its development differs from every video delivered in the previous 24 h, or it carries a materially new fact on the same development; the story ledger enforces it (integrity class). Under L-q the proposed reading is: none of its sentence ids was delivered in the previous 24 h and its angle differs from every delivered video's, or it carries a materially new fact (open for the orchestrator). (2) SUPPLY: the 72 h universe barely moves in 3-5 h, so each cycle ingests what was published since the last one and the channel universe must be wide enough; pipeline_pp_backtest is asked (its REQUESTS file) for the DISTINCT legal developments per day the oracle finds in the saved universes. (3) RUN TIME: a full cycle must fit comfortably inside 3 h on GPU0 alone. Measured: tonight's editorial stage took 70.2 min (fresh_20261112_050611, 4213 s): about 50 min of gemma3:27b calls (397 calls, 230 cache hits; reply-cache writes from +1.4 to +70.2 min), about 19 min in three Whisper word passes, each a GPU0 swap (48 h pool +20 to +29 min, 72 h pool +33 to +39, wire pool +64 to +67), under 1 min universe + embeddings (cached). The last complete render path (pinned_20261111_172202) took 51.3 min after selection: render 17.9, gates 15.6, verify 13.4, prepare 1.6, layout 1.2, cut + sentence law + voice 1.1, review 0.6 min. A cycle is about 2 h: inside 3 h, not comfortably (no room for a second candidate after a HOLD). The time goes to model calls (~50 min), render + gates + verify (~47 min) and Whisper swaps (~19 min).
- L-q MOMENTS FIRST, THEN PACKAGE (orchestrator 2026-11-12 '01:55'; PBX 01:48: "i want you to start looking for the stuff that is most social media and engagement friendly. not all segments you clip need to be 100% same exact topic so long as any PBX MAX VO can stitch the two in a logical clever way that actually allows for points to be made etc. perhaps we analyze best of moments across every few hrs new content first.. then decide how to package it and how to optimzie for views etc. now THIS is the strategy"; '01:58': "pls drop the old video and start this new process"): moments-first selection is the product; story-first selection is retired, and the DEC-13 clusters (L-f) become one input, not the gate. STEP 1 MINE: each cycle, over the content published since the last cycle (plus the recent window), find the best MOMENTS: whole stand-alone sentences from partner / guest sources, scored for social engagement (a strong opinion, a surprising number, a quotable line, a named figure, stakes, emotion, a clean hook in the first 2 s), by sentence id, never rewritten. STEP 2 PACKAGE: choose the set of moments that makes the best video and the angle that ties them; the moments need not be the same development: the PBX MAX voiceover stitches them with bridges that make a point, logically and cleverly. STEP 3 OPTIMISE: hook choice, order, title / caption for views. Integrity is L-o's amended class, VO fidelity included.
  Check: a moments-first run replaces the gates that assumed one development (any same-event / topic check on the line-up) with the VO-fidelity gate, ONLY for moments-first runs and only once that gate exists with its must-fail corpus passing; every other integrity gate is unchanged ('01:58'). Build: pipeline_pp_selectid builds the miner and packager (pipeline/moments.py, package.py, trend_brief.py, the VO-fidelity checker) on its ids-only contract (pipeline/select_by_id.py, eligibility.py); pipeline_pp_backtest measures supply under this rule; the integrator wires and audits them when they report DONE. The first delivery goes to Telegram as REVIEW ONLY ('first moments-first package; selection + VO by the new path, not yet merged/audited') with its duration deviations listed per L-o. Not yet built.
- L-r GPU0 NEVER SURPRISES A RUN (orchestrator 2026-11-12 '01:55' B; PBX on the pinned run's out-of-memory: "let's make sure that never happens again. what can we do rn to fix this??"): (1) ONE OWNER: every code path that loads anything on GPU0 (gemma via Ollama, Whisper, the face detector / vision gates, NVENC, the preflight's own model checks, GPU test sessions, the backtest) takes the gpu0.py lease first: no lease, no load; (2) ONE MODEL AT A TIME by construction: one function swap_to(model) unloads whatever is resident (Ollama keep_alive=0 confirmed via the GPU0 listener, torch empty_cache, the Whisper object deleted), then VERIFIES by nvidia-smi that GPU0's free memory is at least the incoming model's known requirement plus margin before loading; every stage calls it, nothing calls a loader directly; the preflight leaves GPU0 as empty as it found it and asserts that; (3) BOUNDED SELF-HEAL, not a silent retry: on CUDA out-of-memory, release everything this run owns, wait until nvidia-smi shows the memory free (timeout), retry the SAME step ONCE, both attempts in PROVENANCE; a second failure is a HOLD naming every process on GPU0 (pid, name, MiB); an out-of-memory never surfaces as a different error: the HOLD reason carries the real cause; (4) FOREIGN PROCESSES: at run start and before every swap, a process using GPU0 memory without the lease HOLDs the run at once, named; nothing is killed that the run did not start; GPU1 stays quarantined and untouched; (5) TESTS: a must-fail that loads a dummy allocation on GPU0 before each stage and proves the stage refuses or recovers as specified, and a test that runs env -> pinned -> render -> gates back to back twice and shows peak GPU0 memory per stage in a table, which every REPORT.md carries from now on.
  Check: in progress; it outranks hardening batches 18 / 19 and must be in place before the first moments-first render ('01:58'). Done so far: stage_pinned releases GPU0 before Whisper (456a440f, E-FAIL-052). The GPU0 paths are enumerated in the DoD (file:line, wired or not). It supersedes branch hardening-redteam's uncommitted GPU0 lease draft (batch 20), which is rebuilt to this law.
- L-s CONTEXT INTEGRITY (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md; a new HARD gate, separate from VO fidelity; the reviewers' unanimous #1 blind spot): a verbatim whole sentence can still misrepresent its speaker once lifted. For every selected moment the inputs are the source's speaker-turn-aware transcript from at least 90 s before (back to the start of the question / turn) to 60 s after, the video's title and description, the selected sentence ids, and the finished package (order, adjacent clips, VO, title, caption). STEP A (context only, the package hidden): a model from a different vendor than the writer states who is speaking; whose view it is (own sincere / attributed to someone else / hypothetical / conditional / sarcastic / question / reading aloud / ad read); the referent of every pronoun and of 'this / that / today'; any governing condition or time frame; any retraction or qualification in the window. STEP B (the package only): what an ordinary viewer concludes the speaker asserts. PASS only if: the speaker's own sincere assertion; every referent inside the clip; no unmet condition and no reversal; the in-context proposition entails the viewer takeaway with the same polarity and no stronger certainty; no implied relation (agreeing / answering / rebutting) between speakers who were not in the same source video, whether by sequence, bridge or title, not only by banned words. Any 'uncertain' is a FAIL. Repair is ONLY extending the clip by whole locked sentences and re-checking, or dropping the MOMENT and repacking; never writing the missing context into the VO.
  Check: must-fail corpus >= 40 (steelman, quoting an opponent, sarcasm, a conditional split across sentences, an unresolved pronoun, 'some people say', a stale 'today / just', an answer without its question, a later retraction, false dialogue by sequence, the wrong speaker) AND a must-pass corpus >= 20 with the false-reject rate reported (a checker that rejects everything is a broken selector). Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-t ALL AUDIENCE-FACING TEXT IS UNDER THE GATES (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): the title, the caption and any on-screen text are free text exactly like the VO: every number, name and claim is audible in a clip of this video; quotes are verbatim; no stronger certainty; the framing verbs destroys / slams / exposes / admits / confirms / caught are banned unless they are the source's own word; no name of a person who does not appear; no second-person financial imperative. ONE title and ONE caption go through VO fidelity and context integrity (L-s) with the video, and are bound into the release authorisation (L-j) with BOTH files: one manifest holds both renders, the title, the caption, the source intervals, the credits and the gate results; any change after the gates re-runs them.
  Check: release_auth's attested set grows by the title, caption and manifest; telegram.deliver_run sends that one title and caption. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-u HARD EXCLUSIONS AND SCORING (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md; engagement scoring otherwise selects exactly what burns partners): never auto-selected: accusations of crime / fraud / insolvency / dishonesty against a named person or company; one partner attacking another; buy / sell / leverage imperatives and guaranteed-return claims; single-source 'breaking' factual claims; ad reads and sponsor segments; third-party media played inside a partner's video. Down-weighted and capped: price predictions (at most one per video, always framed as that speaker's prediction, never as fact in the title), doom, politics not about Bitcoin policy. 'Named figure' stops being a positive axis on its own; contempt / outrage is a penalty, not a boost. Per-channel fairness: at most ONE clip per channel per video, at most 20 s per source video, per-channel daily and weekly appearance caps (numbers proposed from the saved universes), topic and speaker cooldowns beyond the 24 h moment rule.
  Check: exclusions in code, before any score (a rank weight is not an exclusion); the cap numbers come from the saved universes (pp-backtest). Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-v SPEAKER AND TRANSCRIPT TRUTH (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): (1) WHO IS SPEAKING: a moment may not span a speaker change; a person is NAMED in VO / title only when verified (title / description metadata, or diarisation above a stated confidence), otherwise the show is credited. (2) every gate today trusts one Whisper transcript: for the selected sentences only, a second independent recognition pass (a different model / settings) runs against the SOURCE audio; any disagreement on a number, a name or a negation makes that token unusable in VO / title or drops the moment. (3) time-sensitive language ('just', 'today', price levels) requires the source's original publish time inside the window; re-uploads are excluded.
  Check: the second pass is a GPU0 load (law L-r: through gpu0.swap_to); diarisation confidence threshold stated with its evidence. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-w OPERATING RULES (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): (1) DIVISION OF LABOUR: the local gemma mines and scores by id; CODE does the duration packing (VO length and the credits absorb the slack, so 60-70 s is met by arithmetic, not by the model); a FRONTIER model picks the angle and writes VO / title / caption; a different vendor rules fidelity and context; measured dollars per video are reported. (2) NO ZERO-VIDEO NIGHTS FROM THE CHECKER: on a VO reject, regenerate once, then fall back to a plain factual VO ('Next, <show> on <topic>.') rather than dropping the package; a package is dropped only for a context-integrity or exclusion failure, and then repacked from the next moments. (3) STORY-FIRST IS KEPT as a preferred package TYPE when >= 2 channels cover one development (the safest format); the packager chooses the type. (4) the trend brief runs in SHADOW first (logged, zero weight) next to a free baseline signal from our own corpus (topic frequency across partner channels, last 24 h); when enabled its weight is capped at ~10-15% of the score, its output forced into a closed Bitcoin topic taxonomy, raw post text never enters any prompt, and a person-trend may boost only moments where that person is the speaker. (5) the Telegram approval message carries, per clip, a link to the source video ~30 s before the clip, the flagged risks, both file hashes, the one title and caption. (6) REPORTED NUMBERS: generated, delivered, approved-without-edit, published, rejected with reason, corrected / challenged; not delivered alone. A hold is a selector defect only when the blind oracle's witness package ALSO passes context integrity, exclusions and fidelity; the oracle runs on selector holds only (not ingestion / GPU holds). No integrity rule is ever demoted to ranking without PBX in writing.
  Check: amends L-n (the reported numbers; the oracle on selector holds only, its witness under L-s / L-u / VO fidelity) and L-q (story-first kept as a package type). The backtest session is asked separately to compare, on the same saved universes, story-first with bent taste rules vs moments-first vs frontier packaging, blind-judged for publishability. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- AMENDMENTS 2026-11-12 '02:30': L-n by L-w (6) (reported numbers: generated / delivered / approved-without-edit / published / rejected with reason / corrected or challenged; the blind oracle runs on selector holds only, and a hold is a selector defect only when its witness package also passes L-s, L-u and VO fidelity); L-o by L-s and L-t (context integrity and all audience-facing text join the integrity class; an integrity rule is never demoted to ranking without PBX in writing, L-w (6)); L-q by L-w (3) (story-first is kept as a preferred package type when >= 2 channels cover one development; the packager chooses the type).
- LAW 20 / M2: gate thresholds are constants; a failed gate is a hard stop; never change what a check
  accepts to make a render pass; never reclassify a failing gate as a false positive.
- M12 FAIL CLOSED: missing data, model failure or an exception rejects; it never produces a pass.
- LAW 22: the frozen v2f reference (references/v2f_2026-11-06) must keep re-rendering byte-identically.
- Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing.



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (2122 lines)
```
   1 | diff --git a/pipeline/backtest.py b/pipeline/backtest.py
   2 | index 5ba6215b..547a8465 100644
   3 | --- a/pipeline/backtest.py
   4 | +++ b/pipeline/backtest.py
   5 | @@ -212,6 +212,9 @@ def main(argv=None):
   6 |          days = [d for d in days if os.path.basename(d) in set(a.runs)]
   7 |      os.makedirs(a.out, exist_ok=True)
   8 |      registry = json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))
   9 | +    import gpu0
  10 | +    lease = gpu0.lease(f"backtest {os.path.basename(a.out)} (pid {os.getpid()})")   # L-r: a GPU0 job holds the lease
  11 | +    lease.__enter__()
  12 |      E, L = sm.Embedder(), sm.LocalLLM().start()
  13 |      rows, t0 = [], time.time()
  14 |      try:
  15 | @@ -227,6 +230,7 @@ def main(argv=None):
  16 |      finally:
  17 |          L.stop()
  18 |          E.close()
  19 | +        lease.__exit__(None, None, None)
  20 |      print(table(rows))
  21 |      print(f"total {round(time.time() - t0)} s -> {a.out}")
  22 |      return 0
  23 | diff --git a/pipeline/config.py b/pipeline/config.py
  24 | index e87c7dc6..4f9e6482 100644
  25 | --- a/pipeline/config.py
  26 | +++ b/pipeline/config.py
  27 | @@ -135,6 +135,8 @@ def conform_outro(aspect="16x9"):
  28 |      Content-keyed cache: only re-conforms if master hash changes.
  29 |      Returns path to conformed file, or raises FileNotFoundError.
  30 |      """
  31 | +    import gpu0
  32 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
  33 |      if aspect == "16x9":
  34 |          master = OUTRO_MASTER_16x9
  35 |          w, h = WIDTH, HEIGHT
  36 | diff --git a/pipeline/cut_accept.py b/pipeline/cut_accept.py
  37 | index 1a6e31c8..6fd8015a 100644
  38 | --- a/pipeline/cut_accept.py
  39 | +++ b/pipeline/cut_accept.py
  40 | @@ -152,15 +152,10 @@ def spoken_tokens(words):
  41 |      return canon.canon_tokens(" ".join(words))
  42 |  
  43 |  
  44 | -_MODEL = None
  45 | -
  46 | -
  47 |  def _model():
  48 | -    global _MODEL
  49 | -    if _MODEL is None:
  50 | -        from faster_whisper import WhisperModel
  51 | -        _MODEL = WhisperModel("large-v3", device="cuda", compute_type="float16")
  52 | -    return _MODEL
  53 | +    """The process's one large-v3 (L-r: gpu0.whisper loads it through swap_to; any later swap deletes it)."""
  54 | +    import gpu0
  55 | +    return gpu0.whisper("large-v3")
  56 |  
  57 |  
  58 |  def _whisper_words(wav_path):
  59 | diff --git a/pipeline/preflight.py b/pipeline/preflight.py
  60 | index 1009b9ee..980ce21a 100644
  61 | --- a/pipeline/preflight.py
  62 | +++ b/pipeline/preflight.py
  63 | @@ -20,12 +20,14 @@ import os
  64 |  import shutil
  65 |  import subprocess
  66 |  import sys
  67 | +import time
  68 |  import urllib.request
  69 |  
  70 |  PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
  71 |  REPO = os.path.dirname(PIPELINE_DIR)
  72 |  sys.path.insert(0, PIPELINE_DIR)
  73 |  sys.path.insert(1, os.path.join(REPO, "video_pipeline_v3"))     # relay.get_key (the pipeline's key loader)
  74 | +import gpu0  # noqa: E402  (law L-r)
  75 |  
  76 |  GPU0_FREE_MIB = 20000             # editorial model ~19 GB + Whisper; counted with our own Ollama model released
  77 |  DISK_FREE_GB = 25
  78 | @@ -43,21 +45,18 @@ def _get_json(url, headers=None, timeout=15, data=None):
  79 |  
  80 |  
  81 |  def check_gpu0():
  82 | -    import story_semantics as sm
  83 | -    gpus = dict(l.split(", ") for l in _run(["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader"])
  84 | -                .stdout.strip().splitlines())
  85 | -    apps = [l.split(", ") for l in _run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory",
  86 | -                                         "--format=csv,noheader,nounits"]).stdout.strip().splitlines() if l]
  87 | -    serve = sm.LocalLLM()._listener_pid()
  88 | -    ours = set(_run(["pgrep", "-P", str(serve)]).stdout.split()) | {str(serve)} if serve else set()
  89 | -    others = [(p, m) for p, u, m in apps if u == gpus.get("0") and p not in ours]
  90 | -    if others:
  91 | -        return False, "other job(s) on GPU0: " + ", ".join(
  92 | -            f"pid {p} ({m} MiB) {_run(['ps', '-o', 'args=', '-p', p]).stdout.strip()[:60]}" for p, m in others)
  93 | -    used, total = sm.gpu0_memory()
  94 | -    held = sum(int(m) for p, u, m in apps if u == gpus.get("0") and p in ours)
  95 | +    """L-r: no foreign process on GPU0 (gpu0.foreign: anything but this run's processes and the GPU0 Ollama's), and
  96 | +    room for the largest single model swap_to will load (its measured need + margin) once the Ollama's models, ours
  97 | +    to unload, are released."""
  98 | +    foreign = gpu0.foreign()
  99 | +    if foreign:
 100 | +        return False, f"GPU0 memory is held by a process that is not this run's: {gpu0.describe(foreign)}"
 101 | +    used, total = gpu0.memory()
 102 | +    ollama = gpu0._ollama_pids()
 103 | +    held = sum(m or 0 for p, n, m in gpu0.processes() if p in ollama)
 104 | +    need = max(GPU0_FREE_MIB, max(gpu0.REQUIREMENT_MIB.values()) + gpu0.MARGIN_MIB)
 105 |      free = total - used + held
 106 | -    return free >= GPU0_FREE_MIB, f"{free} MiB available with our model released (need {GPU0_FREE_MIB})"
 107 | +    return free >= need, f"{free} MiB available with the GPU0 Ollama's models released (need {need})"
 108 |  
 109 |  
 110 |  def check_ollama():
 111 | @@ -65,8 +64,9 @@ def check_ollama():
 112 |      digest = sm.model_digest(sm.LLM_HOST, sm.LLM_MODEL)
 113 |      if not digest:
 114 |          return False, f"{sm.LLM_MODEL} not installed on {sm.LLM_HOST}"
 115 | -    body = json.dumps({"model": sm.LLM_MODEL, "prompt": "ok", "stream": False,
 116 | -                       "options": {"num_predict": 1}}).encode()
 117 | +    gpu0.swap_to(f"ollama:{sm.LLM_MODEL}")           # L-r: the model reaches GPU0 only through swap_to
 118 | +    body = json.dumps({"model": sm.LLM_MODEL, "prompt": "ok", "stream": False, "keep_alive": 0,   # unloaded after
 119 | +                       "options": {"num_predict": 1}}).encode()                                  # its answer (L-r)
 120 |      r = _get_json(f"http://{sm.LLM_HOST}/api/generate", {"Content-Type": "application/json"}, timeout=180, data=body)
 121 |      return "response" in r, f"{sm.LLM_MODEL} {digest[:12]} answered"
 122 |  
 123 | @@ -149,6 +149,8 @@ def run_checks(checks=None):
 124 |      for name, fn in (CHECKS if checks is None else checks):
 125 |          try:
 126 |              ok, detail = fn()
 127 | +        except gpu0.Gpu0Stop as e:                    # a GPU0 refusal names its cause (pids, MiB; never a secret)
 128 | +            ok, detail = False, f"GPU0 {type(e).__name__}: {e}"
 129 |          except Exception as e:                        # an exception is a failed check, never a pass; reported by
 130 |              ok, detail = False, f"{type(e).__name__} (raised)"   # TYPE only: a network error's text can carry a
 131 |                                                                    # key or token in its URL (claude-fable audit #6)
 132 | @@ -156,8 +158,33 @@ def run_checks(checks=None):
 133 |      return out
 134 |  
 135 |  
 136 | +def left_as_found(found_used, found_models, wait_s=60, slack_mib=256):
 137 | +    """L-r item 2: (ok, detail): GPU0 holds no more than the preflight found (memory within slack_mib of it, no Ollama
 138 | +    model that was not resident before), waiting up to wait_s for an unload to land."""
 139 | +    t0 = time.time()
 140 | +    while True:
 141 | +        used, _ = gpu0.memory()
 142 | +        extra = sorted(set(gpu0.ollama_loaded()) - set(found_models))
 143 | +        if used <= found_used + slack_mib and not extra:
 144 | +            return True, f"GPU0 at {used} MiB, found at {found_used} MiB, no model left resident"
 145 | +        if time.time() - t0 > wait_s:
 146 | +            return False, f"the preflight left GPU0 at {used} MiB (found at {found_used} MiB), resident {extra}"
 147 | +        time.sleep(1)
 148 | +
 149 | +
 150 |  def main():
 151 | -    res = run_checks()
 152 | +    try:
 153 | +        with gpu0.lease(f"preflight (pid {os.getpid()})"):   # L-r: custody of the wrapper's fd 8, else its own
 154 | +            found_used, found_models = gpu0.memory()[0], gpu0.ollama_loaded()
 155 | +            res = run_checks()
 156 | +            try:
 157 | +                ok, detail = left_as_found(found_used, found_models)
 158 | +            except gpu0.Gpu0Stop as e:
 159 | +                ok, detail = False, f"GPU0 {type(e).__name__}: {e}"
 160 | +            res.append({"check": "gpu0_left", "ok": ok, "detail": detail})
 161 | +    except gpu0.Gpu0Stop as e:
 162 | +        print(f"HOLD (preflight): GPU0 {type(e).__name__}: {e}", flush=True)
 163 | +        return 3
 164 |      for r in res:
 165 |          print(f"  preflight {r['check']:13s} [{'PASS' if r['ok'] else 'FAIL'}] {r['detail']}", flush=True)
 166 |      bad = [r for r in res if not r["ok"]]
 167 | diff --git a/pipeline/pulse_transitions.py b/pipeline/pulse_transitions.py
 168 | index ea2c8141..2d4bbcf2 100644
 169 | --- a/pipeline/pulse_transitions.py
 170 | +++ b/pipeline/pulse_transitions.py
 171 | @@ -151,6 +151,8 @@ def wipe_frames(w, h, n=WIPE_FRAMES):
 172 |  
 173 |  
 174 |  def render_wipe(path, w, h, qp):
 175 | +    import gpu0
 176 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 177 |      import tempfile
 178 |      tmp = tempfile.mkdtemp(prefix="wipe_")
 179 |      for k, f in enumerate(wipe_frames(w, h)):
 180 | @@ -181,6 +183,8 @@ def concat(segments, junctions, out_path, qp, w, h, work_dir):
 181 |      """Concatenate (label, path, type) segments with the planned junctions. Every input is normalised
 182 |      to its exact video frame count (audio padded/trimmed to it) so picture and sound stay locked.
 183 |      Returns the timeline [{"label","type","start","end"}] (overlapping entries at dissolves)."""
 184 | +    import gpu0
 185 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 186 |      style_c = [j for j in junctions if j["kind"] == "insert"]
 187 |      segs = list(segments)
 188 |      if style_c:
 189 | diff --git a/pipeline/render16.py b/pipeline/render16.py
 190 | index 18962aa2..8c810217 100644
 191 | --- a/pipeline/render16.py
 192 | +++ b/pipeline/render16.py
 193 | @@ -54,6 +54,8 @@ def ease_in_out(t):
 194 |  def render_vo_visual(vo_wav, preceding_src, preceding_cut_out, output_mp4, label, qa_dir):
 195 |      """R5 VO visual: freeze last frame, blur sigma 6, 1.0x->1.08x zoom, waveform bottom 22%, pre-roll.
 196 |      Returns the path to the assembled VO WAV (silence + stem) for G6 measurement."""
 197 | +    import gpu0
 198 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 199 |      print(f"  Rendering R5 VO visual: {os.path.basename(output_mp4)}")
 200 |  
 201 |      vo_dur = get_duration(vo_wav)
 202 | @@ -193,6 +195,8 @@ def render_vo_visual(vo_wav, preceding_src, preceding_cut_out, output_mp4, label
 203 |  def apply_watermark_alpha(input_mp4, output_mp4, mark_path, mark_px, margin,
 204 |                            opacity, fade_in_dur, shoutout_start):
 205 |      """Overlay alpha watermark on final concat. No black box -- alpha PNG."""
 206 | +    import gpu0
 207 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 208 |      overlay_expr = (
 209 |          f"[1:v]scale={mark_px}:-1,format=rgba,"
 210 |          f"colorchannelmixer=aa={opacity},"
 211 | @@ -223,6 +227,8 @@ def apply_watermark_alpha(input_mp4, output_mp4, mark_path, mark_px, margin,
 212 |  def render_16x9(segment_dir, qa_version=None, output_name="segment.mp4",
 213 |                  alimiter_dbfs=-3.0):
 214 |      """Full 16:9 render pipeline. Returns (final_path, manifest_path, vo_assembled_tracks) or raises."""
 215 | +    import gpu0
 216 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 217 |      t0 = time.time()
 218 |      print("=== RENDER 16:9 ===\n")
 219 |  
 220 | @@ -611,6 +617,9 @@ def _find_outro(qa_dir, segment_dir=None):
 221 |      try:
 222 |          return conform_outro("16x9")
 223 |      except (FileNotFoundError, subprocess.CalledProcessError) as e:
 224 | +        import gpu0
 225 | +        if gpu0.is_oom(e):           # L-r: an NVENC out-of-memory is never a fallback (E-FAIL-052)
 226 | +            raise gpu0.GpuOOM(f"outro conform: CUDA/NVENC out of memory ({e})") from e
 227 |          print(f"  PBX outro conform failed ({e}), falling back to qa_dir")
 228 |      for name in ["final_outro.mp4", "outro.mp4"]:
 229 |          candidate = os.path.join(qa_dir, name)
 230 | diff --git a/pipeline/render_vertical.py b/pipeline/render_vertical.py
 231 | index 418fd124..bb59cf98 100644
 232 | --- a/pipeline/render_vertical.py
 233 | +++ b/pipeline/render_vertical.py
 234 | @@ -64,6 +64,8 @@ def reframe_fixed_crop(seg_path, output_path, seg_label):
 235 |      """Fixed 9:16 crop per clip. Detect faces via mediapipe, use median centre X.
 236 |      Falls back to centre crop if no faces detected.
 237 |      Returns (success: bool, crop_rect: str)."""
 238 | +    import gpu0
 239 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 240 |      import cv2
 241 |      import mediapipe as mp_lib
 242 |      from mediapipe.tasks.python import vision
 243 | @@ -135,6 +137,8 @@ def reframe_stack2(seg_path, output_path, seg_label, layout_cfg):
 244 |      """Stack2: speaker rect on TOP, other person rect on BOTTOM.
 245 |      Each rect cropped from source, scaled to 1080 wide, placed in 1080x960 slot.
 246 |      layout_cfg keys: speaker_rect (x,y,w,h), other_rect (x,y,w,h)."""
 247 | +    import gpu0
 248 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 249 |      import cv2
 250 |      print(f"    Reframe stack2: {seg_label}")
 251 |  
 252 | @@ -203,6 +207,8 @@ def reframe_grid(seg_path, output_path, seg_label, layout_cfg):
 253 |      """Grid: face rect on TOP slot, chart rect on BOTTOM slot.
 254 |      layout_cfg keys: face_rect (x,y,w,h), chart_rect (x,y,w,h),
 255 |                       top_slot_h (default 810), bottom_slot_h (default 1110)."""
 256 | +    import gpu0
 257 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 258 |      import cv2
 259 |      print(f"    Reframe grid: {seg_label}")
 260 |  
 261 | @@ -270,6 +276,8 @@ def reframe_grid(seg_path, output_path, seg_label, layout_cfg):
 262 |  
 263 |  def reframe_single(seg_path, output_path, seg_label, layout_cfg):
 264 |      """Single: crop one rect from source, scale to 1080 wide, pad to 1920 tall (centred)."""
 265 | +    import gpu0
 266 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 267 |      print(f"    Reframe single: {seg_label}")
 268 |  
 269 |      rect = layout_cfg["rect"]  # [x, y, w, h]
 270 | @@ -310,6 +318,8 @@ def reframe_letterbox(seg_path, output_path, seg_label, layout_cfg=None):
 271 |      darkened (-35%), 1.25x zoomed copy of the same frame. No crop.
 272 |  
 273 |      Returns (success: bool, layout_name: str)."""
 274 | +    import gpu0
 275 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 276 |      print(f"    Reframe letterbox: {seg_label}")
 277 |  
 278 |      # Full 16:9 frame scaled to 1080 wide = 1080x608 (at 16:9 ratio)
 279 | @@ -395,6 +405,8 @@ def _shot_vf(shot, src_w, src_h):
 280 |  def reframe_auto(seg_path, output_path, seg_label, plan):
 281 |      """Per-shot 9:16 from the PREPARED clip (lead-in pad and fades identical to 16:9). Video only is
 282 |      re-composed; the clip's audio is copied unchanged. Returns (ok, layout_summary)."""
 283 | +    import gpu0
 284 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 285 |      fps = plan["fps"]
 286 |      graph, labels = [], []
 287 |      matrix = _input_matrix(seg_path)
 288 | @@ -428,6 +440,8 @@ def reframe_auto(seg_path, output_path, seg_label, plan):
 289 |  def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4, label, qa_dir):
 290 |      """R5 native 9:16 VO visual: face-crop BG, blur, 1.0x->1.08x zoom, waveform.
 291 |      Returns the path to the assembled VO WAV (silence + stem) for G6 measurement."""
 292 | +    import gpu0
 293 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 294 |      import cv2
 295 |      import mediapipe as mp_lib
 296 |      from mediapipe.tasks.python import vision
 297 | @@ -623,6 +637,8 @@ def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4,
 298 |  def apply_watermark_alpha_vert(input_mp4, output_mp4, mark_path, mark_px, margin,
 299 |                                 opacity, fade_in_dur, shoutout_start):
 300 |      """Overlay alpha watermark on vertical concat. Bottom-right, smaller for 9:16."""
 301 | +    import gpu0
 302 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 303 |      overlay_expr = (
 304 |          f"[1:v]scale={mark_px}:-1,format=rgba,"
 305 |          f"colorchannelmixer=aa={opacity},"
 306 | @@ -658,6 +674,8 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 307 |                  alimiter_dbfs=-3.0):
 308 |      """Full 9:16 vertical render pipeline.
 309 |      Returns (final_path, manifest_path, vo_assembled_tracks) or raises."""
 310 | +    import gpu0
 311 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 312 |      t0 = time.time()
 313 |      print("=== RENDER 9:16 ===\n")
 314 |  
 315 | @@ -1160,6 +1178,9 @@ def _find_outro_vert(qa_dir, segment_dir=None):
 316 |      try:
 317 |          return conform_outro("9x16")
 318 |      except (FileNotFoundError, subprocess.CalledProcessError) as e:
 319 | +        import gpu0
 320 | +        if gpu0.is_oom(e):           # L-r: an NVENC out-of-memory is never a fallback (E-FAIL-052)
 321 | +            raise gpu0.GpuOOM(f"outro conform: CUDA/NVENC out of memory ({e})") from e
 322 |          print(f"  PBX 9:16 outro conform failed ({e}), falling back to qa_dir")
 323 |  
 324 |      # Fallback: pre-rendered vertical outro in qa_dir
 325 | diff --git a/pipeline/replay.py b/pipeline/replay.py
 326 | index b7522fab..fc871e29 100644
 327 | --- a/pipeline/replay.py
 328 | +++ b/pipeline/replay.py
 329 | @@ -75,7 +75,13 @@ def replay(run_dir, start="prepare", vision=True, stamp=None):
 330 |          cuts = json.load(f)
 331 |      t0 = time.time()
 332 |      try:
 333 | +        # L-r: a replay is a GPU0 job like a run: the lease to its end (custody when a wrapper holds it), the sampler
 334 | +        run.gpu0_stack.enter_context(rf.gpu0.lease(f"replay {os.path.basename(dst)} (pid {os.getpid()})"))
 335 | +        run.sampler = rf.gpu0.PeakSampler().start()
 336 |          rf.run_tail(run, cuts, start=start, vision=vision)
 337 | +    except rf.gpu0.Gpu0Stop as e:                       # the lease is busy: a HOLD carrying the real cause
 338 | +        run.status["verdict"] = rf.VERDICT_HOLD
 339 | +        run.status["holds"].append(f"replay: infrastructure: GPU0 {type(e).__name__}: {e}")
 340 |      except rf.Hold:
 341 |          run.status["verdict"] = rf.VERDICT_HOLD
 342 |      except Exception as e:                              # as run_fresh.main: anything unexpected is a HOLD
 343 | @@ -86,6 +92,9 @@ def replay(run_dir, start="prepare", vision=True, stamp=None):
 344 |      finally:
 345 |          run.status["elapsed_s"] = round(time.time() - t0, 1)
 346 |          run.status["ended"] = rf.now_iso()
 347 | +        if run.sampler:
 348 | +            run.prov.setdefault("gpu0", {})["peaks_mib"] = run.sampler.stop()
 349 | +        run.prov.setdefault("gpu0", {})["swaps"] = rf.gpu0.events()
 350 |          try:                                            # attested for its verdict, never deliverable
 351 |              rf.attest_run(run, deliverable=False, why_not="replay: diagnostic, deliver only a full run",
 352 |                            code_checked=False)
 353 | @@ -96,6 +105,7 @@ def replay(run_dir, start="prepare", vision=True, stamp=None):
 354 |          rf.write_report(run)
 355 |          with open(os.path.join(dst, "VERDICT.txt"), "w") as f:
 356 |              f.write(str(run.status["verdict"]) + "\n")
 357 | +        run.gpu0_stack.close()                          # the GPU0 lease is held to here
 358 |      print(f"\n=== REPLAY {dst} (from {start}, vision {'on' if vision else 'OFF'}): {run.status['verdict']} ===")
 359 |      for h in run.status["holds"]:
 360 |          print(f"  HOLD: {h}")
 361 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
 362 | index 4b93da2c..c57d517a 100644
 363 | --- a/pipeline/run_fresh.py
 364 | +++ b/pipeline/run_fresh.py
 365 | @@ -39,6 +39,7 @@ Usage:
 366 |    cd ~/protocol_pulse/pipeline && CUDA_VISIBLE_DEVICES=0 python3 run_fresh.py --pinned PIN.json
 367 |  """
 368 |  import argparse
 369 | +import contextlib
 370 |  import datetime
 371 |  import hashlib
 372 |  import io
 373 | @@ -87,6 +88,9 @@ class Hold(Exception):
 374 |      """Fail-closed stop. The run ends in HOLD with the reason recorded."""
 375 |  
 376 |  
 377 | +import gpu0  # noqa: E402  (law L-r: the one owner of GPU0; pipeline/ is this file's directory)
 378 | +
 379 | +
 380 |  # ── utilities ──
 381 |  
 382 |  def sha256(path):
 383 | @@ -168,6 +172,46 @@ class Run:
 384 |          self.mode = "auto"                  # "auto" | "pinned"
 385 |          self.machine_cuts = False          # True only for machine-built PINs (enables snap)
 386 |          self.allow_v2f_material = False     # True only for a pin declaring reuses_v2f_material
 387 | +        self.sampler = None                 # L-r: gpu0.PeakSampler, started in stage_env
 388 | +        self.gpu0_stack = contextlib.ExitStack()   # L-r: holds the GPU0 lease from stage_env to the end of main
 389 | +
 390 | +    def _attempts(self, name, fn):
 391 | +        """Law L-r item 3. A CUDA out-of-memory gets ONE retry of the same step, after everything this run owns is
 392 | +        released and nvidia-smi shows GPU0 free; both attempts go to PROVENANCE (gpu0_oom); a second one is a HOLD
 393 | +        naming every GPU0 process. Every other GPU0 stop is a HOLD carrying its real cause, never another error."""
 394 | +        for attempt in (1, 2):
 395 | +            if self.sampler:
 396 | +                self.sampler.set(name)
 397 | +            try:
 398 | +                return fn()
 399 | +            except Hold:
 400 | +                raise
 401 | +            except gpu0.Gpu0Stop as e:
 402 | +                if not isinstance(e, gpu0.GpuOOM):
 403 | +                    raise Hold(f"infrastructure: {name}: GPU0 {type(e).__name__}: {e}") from None
 404 | +                err = e
 405 | +            except Exception as e:
 406 | +                if not gpu0.is_oom(e):
 407 | +                    raise
 408 | +                err = e
 409 | +            entry = {"attempt": attempt, "at": now_iso(), "error": f"{type(err).__name__}: {str(err)[:400]}"}
 410 | +            try:
 411 | +                entry["gpu0_memory"], entry["gpu0_processes"] = gpu0.memory(), gpu0.processes()
 412 | +            except gpu0.Gpu0Stop as e2:
 413 | +                entry["gpu0_unreadable"] = str(e2)
 414 | +            self.prov.setdefault("gpu0_oom", {}).setdefault(name, []).append(entry)
 415 | +            self.save()
 416 | +            if attempt == 2:
 417 | +                raise Hold(f"infrastructure: {name}: CUDA out of memory twice ({entry['error'][:240]}); on GPU0: "
 418 | +                           f"{gpu0.describe(entry.get('gpu0_processes') or [])}") from None
 419 | +            print(f"  GPU0 OUT OF MEMORY in stage {name}: {entry['error'][:200]}; releasing everything this run "
 420 | +                  f"owns, retrying once", flush=True)
 421 | +            try:
 422 | +                entry["release"] = gpu0.release_all()
 423 | +            except gpu0.Gpu0Stop as e2:
 424 | +                raise Hold(f"infrastructure: {name}: CUDA out of memory ({entry['error'][:200]}) and GPU0 did not "
 425 | +                           f"come free: {e2}") from None
 426 | +            self.save()
 427 |  
 428 |      def stage(self, name, fn):
 429 |          rec = {"name": name, "started": now_iso(), "status": "running"}
 430 | @@ -176,7 +220,7 @@ class Run:
 431 |          print(f"\n######## STAGE {name} ########", flush=True)
 432 |          t0 = time.time()
 433 |          try:
 434 | -            out = fn()
 435 | +            out = self._attempts(name, fn)
 436 |              rec["status"] = "passed"
 437 |              return out
 438 |          except Hold as h:
 439 | @@ -198,6 +242,9 @@ class Run:
 440 |          finally:
 441 |              rec["ended"] = now_iso()
 442 |              rec["seconds"] = round(time.time() - t0, 1)
 443 | +            if self.sampler:
 444 | +                self.sampler.set(None)
 445 | +                rec["gpu0_peak_mib"] = self.sampler.peaks.get(name)
 446 |              self.save()
 447 |  
 448 |      def save(self):
 449 | @@ -235,6 +282,16 @@ def stage_env(run):
 450 |                         "ffmpeg": ffv, "yt_dlp": ytv, "nvidia_smi": gpu.split("\n")}
 451 |      if "telegram" in sys.modules or "telegram_drop" in sys.modules:
 452 |          raise Hold("telegram module loaded — publishing path must not be importable here")
 453 | +    # L-r: the run holds the GPU0 lease to the end of main (custody of scripts/pulse_check_run.sh's fd 8, else its
 454 | +    # own), nothing foreign may hold GPU0 memory at its start, and GPU0 memory is sampled per stage from here on
 455 | +    run.gpu0_stack.enter_context(gpu0.lease(f"run_fresh {os.path.basename(run.dir)} (pid {os.getpid()})"))
 456 | +    foreign = gpu0.foreign()
 457 | +    if foreign:
 458 | +        raise Hold(f"infrastructure: env: GPU0 memory is held by a process that is not this run's: "
 459 | +                   f"{gpu0.describe(foreign)}")
 460 | +    run.prov["gpu0"] = {"at_start": {"memory_mib": gpu0.memory(), "processes": gpu0.processes(),
 461 | +                                     "ollama_resident": gpu0.ollama_loaded(), "holder": gpu0.holder()}}
 462 | +    run.sampler = gpu0.PeakSampler().start()
 463 |  
 464 |  
 465 |  # ── stage 1: topic ──
 466 | @@ -508,7 +565,9 @@ def free_gpu0_for_whisper(run, stage, need_free_mib=6000):
 467 |      """GPU0 is shared (other sessions load Ollama models on :11434, e.g. a 22 GB qwen3-coder at 06:02 on
 468 |      Nov 11, which OOM'd the recut's prepare). Before a Whisper stage, unload the GPU0 Ollama models and
 469 |      wait for room, exactly as the editorial stage does (story_semantics.release_gpu0_for_whisper); a
 470 | -    release that cannot be proven is an infrastructure HOLD, never an OOM mid-stage."""
 471 | +    release that cannot be proven is an infrastructure HOLD, never an OOM mid-stage. L-r: through
 472 | +    gpu0.swap_to (every other GPU0 model unloaded, a foreign process refused, the measured need proven free);
 473 | +    a refusal is a Gpu0Stop that Run.stage turns into a HOLD carrying the real cause."""
 474 |      import story_semantics as sm
 475 |      try:
 476 |          ev = sm.release_gpu0_for_whisper(sm.LocalLLM(), need_free_mib=need_free_mib, wait_s=180)
 477 | @@ -1231,6 +1290,12 @@ def write_report(run):
 478 |      L += ["## Stages", "| stage | status | s | reason |", "|---|---|---|---|"]
 479 |      L += [f"| {r['name']} | {r['status']} | {r.get('seconds')} | {r.get('reason', '')[:200]} |"
 480 |            for r in s["stages"]]
 481 | +    g0 = p.get("gpu0") or {}
 482 | +    total = ((g0.get("at_start") or {}).get("memory_mib") or [None, None])[1]
 483 | +    L += ["", f"## GPU0 peak memory per stage (law L-r; nvidia-smi memory.used every 1 s; GPU0 total {total} MiB)",
 484 | +          "| stage | peak MiB | out-of-memory retries |", "|---|---|---|"]
 485 | +    L += [f"| {r['name']} | {r.get('gpu0_peak_mib', 'not sampled')} | {len((p.get('gpu0_oom') or {}).get(r['name'], []))} |"
 486 | +          for r in s["stages"]]
 487 |      vc = p.get("visual_checklist") or {}
 488 |      if vc:
 489 |          L += ["", "## Visual checklist (answered FROM the contact sheets qa/contact_sheet_<fmt>.jpg; any no = HOLD)"]
 490 | @@ -1370,6 +1435,10 @@ def main():
 491 |              run.status["holds"].append(f"provenance: {type(e).__name__}: {e}")
 492 |          run.status["ended"] = now_iso()
 493 |          run.status["elapsed_s"] = round(time.time() - t0, 1)
 494 | +        if run.sampler:                        # L-r item 5: peak GPU0 memory per stage, in PROVENANCE and REPORT.md
 495 | +            run.prov.setdefault("gpu0", {})["peaks_mib"] = run.sampler.stop()
 496 | +            run.prov["gpu0"]["sampler_errors"] = run.sampler.errors
 497 | +        run.prov.setdefault("gpu0", {})["swaps"] = gpu0.events()
 498 |          try:                                   # LAST: the terminal state, any hold included (release_auth)
 499 |              attest_run(run)
 500 |          except Exception as e:
 501 | @@ -1383,6 +1452,7 @@ def main():
 502 |          for h in run.status["holds"]:
 503 |              print(f"  HOLD: {h}")
 504 |          print(f"  report: {os.path.join(run_dir, 'REPORT.md')}  (no publishing)")
 505 | +        run.gpu0_stack.close()                 # the GPU0 lease (law L-r) is held to here
 506 |      sys.exit(0 if run.status["verdict"] == VERDICT_CANDIDATE else 3)
 507 |  
 508 |  
 509 | diff --git a/pipeline/run_isolated.py b/pipeline/run_isolated.py
 510 | index 5ac15517..595fd2c5 100644
 511 | --- a/pipeline/run_isolated.py
 512 | +++ b/pipeline/run_isolated.py
 513 | @@ -321,6 +321,8 @@ def prerender_clips(run_dir, cuts_table):
 514 |      (cut["fade_in_ms"], cut["fade_out_ms"]; absent = 20 in / 30 out, the M19 defaults). DEC-10: a cut at an
 515 |      envelope minimum declares 83 ms (2 video frames); v2f's table declares 20 / 30, so its render is unchanged.
 516 |      """
 517 | +    import gpu0
 518 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 519 |      qa_dir = os.path.join(run_dir, "qa")
 520 |      sources_dir = os.path.join(run_dir, "sources")
 521 |  
 522 | diff --git a/pipeline/select_passages.py b/pipeline/select_passages.py
 523 | index e1dcb327..82a54fc1 100644
 524 | --- a/pipeline/select_passages.py
 525 | +++ b/pipeline/select_passages.py
 526 | @@ -87,8 +87,8 @@ def _whisper_transcribe(source_path, video_id, run_dir):
 527 |              if result.get("punctuation") or not punctuation.needs_restoration(result.get("words", [])):
 528 |                  return result
 529 |  
 530 | -        from faster_whisper import WhisperModel
 531 | -        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
 532 | +        import gpu0
 533 | +        model = gpu0.whisper("large-v3")      # L-r: loaded through swap_to; a GPU0 stop passes the except below
 534 |          if result is None:
 535 |              segments, info = model.transcribe(
 536 |                  source_path, language="en", beam_size=5,
 537 | @@ -112,6 +112,9 @@ def _whisper_transcribe(source_path, video_id, run_dir):
 538 |          return result
 539 |  
 540 |      except Exception as e:
 541 | +        import gpu0
 542 | +        if gpu0.is_oom(e):           # L-r: an out-of-memory is never 'transcription failed' (E-FAIL-052)
 543 | +            raise gpu0.GpuOOM(f"{video_id}: Whisper: CUDA out of memory ({type(e).__name__}: {str(e)[:200]})") from e
 544 |          print(f"    WARN: whisper failed for {video_id}: {e}")
 545 |          return None
 546 |  
 547 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
 548 | index b283500d..b0c9d836 100644
 549 | --- a/pipeline/sentence_law.py
 550 | +++ b/pipeline/sentence_law.py
 551 | @@ -813,6 +813,8 @@ def room_tone(src_path, t0, t1, seconds, sr=48000):
 552 |  def apply_lead_in_pad(run_dir, cut, fps, qp):
 553 |      """Prepend cut['lead_in_pad_s'] of room tone + the held first frame to qa/final_<clip>.mp4
 554 |      (atomic replace). The pad is declared in cuts_final.json, so every gate knows it is there."""
 555 | +    import gpu0
 556 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 557 |      import wave
 558 |      pad = float(cut["lead_in_pad_s"])
 559 |      clip = os.path.join(run_dir, "qa", f"final_{cut['clip_id']}.mp4")
 560 | diff --git a/pipeline/shot_snap.py b/pipeline/shot_snap.py
 561 | index 8898b9b4..161c40b1 100644
 562 | --- a/pipeline/shot_snap.py
 563 | +++ b/pipeline/shot_snap.py
 564 | @@ -48,6 +48,8 @@ def plan(changes, n_frames, fps, speech_on_s, speech_off_s):
 565 |  def apply(clip, cut, fps, qp):
 566 |      """Snap qa/final_<clip>.mp4 in place when a neighbouring shot shows outside the speech. Returns a record
 567 |      (always), {"snapped": False, ...} when nothing changed."""
 568 | +    import gpu0
 569 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 570 |      pad = float(cut.get("lead_in_pad_s") or 0.0)
 571 |      pin, pout = cut.get("pause_in") or {}, cut.get("pause_out") or {}
 572 |      on = (pin["end"] - cut["cut_in"] + pad) if "end" in pin else None
 573 | diff --git a/pipeline/story_semantics.py b/pipeline/story_semantics.py
 574 | index f6cbdc63..a1aeaf78 100644
 575 | --- a/pipeline/story_semantics.py
 576 | +++ b/pipeline/story_semantics.py
 577 | @@ -27,6 +27,7 @@ import os
 578 |  import re
 579 |  import subprocess
 580 |  import time
 581 | +import urllib.error
 582 |  import urllib.request
 583 |  from datetime import datetime, timedelta, timezone
 584 |  
 585 | @@ -70,11 +71,14 @@ class Embedder:
 586 |      def __init__(self):
 587 |          _gpu_guard()
 588 |          import torch
 589 | +        import gpu0
 590 |          from transformers import AutoModel, AutoTokenizer
 591 |          from huggingface_hub import snapshot_download
 592 |          path = snapshot_download(EMBED_MODEL, revision=EMBED_REVISION, local_files_only=True)
 593 |          self.tok = AutoTokenizer.from_pretrained(path)
 594 | -        self.model = AutoModel.from_pretrained(path, dtype=torch.float16).to("cuda:0").eval()
 595 | +        # L-r: the weights reach GPU0 only through gpu0.swap_to("embedder") (Model.get), and any later swap deletes them
 596 | +        self.model = gpu0.model("embedder", lambda: AutoModel.from_pretrained(path, dtype=torch.float16).to("cuda:0").eval())
 597 | +        self.gpu0 = gpu0
 598 |          self.torch = torch
 599 |          self.model_id = f"{EMBED_MODEL}@{EMBED_REVISION[:12]}"
 600 |  
 601 | @@ -83,10 +87,12 @@ class Embedder:
 602 |          with self.torch.no_grad():
 603 |              for i in range(0, len(texts), batch):
 604 |                  bt = [(EMBED_QUERY_PREFIX + t) if query else t for t in texts[i:i + batch]]
 605 | -                enc = self.tok(bt, padding=True, truncation=True, max_length=512,
 606 | -                               return_tensors="pt").to("cuda:0")
 607 | -                cls = self.model(**enc).last_hidden_state[:, 0].float()
 608 | -                out.append(self.torch.nn.functional.normalize(cls, dim=-1).cpu().numpy())
 609 | +                self.model.get()                                  # resident before any tensor goes to GPU0
 610 | +                with self.gpu0.guard("embedder: encode"):
 611 | +                    enc = self.tok(bt, padding=True, truncation=True, max_length=512,
 612 | +                                   return_tensors="pt").to("cuda:0")
 613 | +                    cls = self.model(**enc).last_hidden_state[:, 0].float()
 614 | +                    out.append(self.torch.nn.functional.normalize(cls, dim=-1).cpu().numpy())
 615 |          return np.vstack(out) if out else np.zeros((0, 768), np.float32)
 616 |  
 617 |      def chunk_vectors(self, rec, chunks):
 618 | @@ -104,7 +110,7 @@ class Embedder:
 619 |          return ids, vecs
 620 |  
 621 |      def close(self):
 622 | -        del self.model
 623 | +        self.model.unload()
 624 |          self.torch.cuda.empty_cache()
 625 |  
 626 |  
 627 | @@ -187,13 +193,23 @@ class LocalLLM:
 628 |          return sorted(gpus.get(u, u) for u in mine)
 629 |  
 630 |      def _post(self, prompt, max_tokens, seed):
 631 | +        import gpu0
 632 | +        if getattr(self, "_gpu0_gen", None) != gpu0.generation() or self.model not in gpu0.ollama_loaded():
 633 | +            gpu0.swap_to(f"ollama:{self.model}")        # L-r: nothing else resident, the memory proven free
 634 | +            self._gpu0_gen = gpu0.generation()
 635 |          body = json.dumps({"model": self.model, "stream": False, "format": "json",
 636 |                             "messages": [{"role": "user", "content": prompt}],
 637 |                             "options": {"temperature": 0, "seed": seed, "num_ctx": LLM_CTX,
 638 |                                         "num_predict": max_tokens}}).encode()
 639 |          req = urllib.request.Request(f"http://{self.host}/api/chat", data=body,
 640 |                                       headers={"Content-Type": "application/json"})
 641 | -        resp = json.loads(urllib.request.urlopen(req, timeout=600).read())
 642 | +        try:
 643 | +            resp = json.loads(urllib.request.urlopen(req, timeout=600).read())
 644 | +        except urllib.error.HTTPError as e:
 645 | +            text = e.read().decode(errors="replace")[:400]
 646 | +            if gpu0.is_oom(RuntimeError(text)):
 647 | +                raise gpu0.GpuOOM(f"ollama {self.model}: CUDA out of memory (HTTP {e.code}: {text})") from None
 648 | +            raise RuntimeError(f"Ollama HTTP {e.code}: {text}") from None
 649 |          self.calls += 1
 650 |          if not self.placement_checked:
 651 |              placement = self.gpu_placement()
 652 | @@ -297,7 +313,11 @@ def loaded_models(host=LLM_HOST):
 653 |  
 654 |  def release_gpu0_for_whisper(llm, need_free_mib=7000, wait_s=180, log=print):
 655 |      """Unload every model on the GPU0 Ollama, wait until GPU0 has need_free_mib free.
 656 | -    Returns an evidence dict; raises RuntimeError (infrastructure) if release can't be proven."""
 657 | +    Returns an evidence dict; raises RuntimeError (infrastructure) if release can't be proven.
 658 | +    L-r: first gpu0.swap_to (every other GPU0 model unloaded, a foreign process refused, the batched word-pass model's
 659 | +    measured need proven free; a refusal is a Gpu0Stop that no caller can rename), then this function's own proof."""
 660 | +    import gpu0
 661 | +    gpu0.swap_to("whisper:large-v3:batched", wait_s=wait_s)
 662 |      ev = {"before": gpu0_memory(), "unloaded": []}
 663 |      deadline = time.time() + wait_s
 664 |      while True:
 665 | diff --git a/pipeline/test_acoustic.py b/pipeline/test_acoustic.py
 666 | index bdda05e4..76fe0eb7 100644
 667 | --- a/pipeline/test_acoustic.py
 668 | +++ b/pipeline/test_acoustic.py
 669 | @@ -82,7 +82,8 @@ def test_magnitude_whisper():
 670 |              "ffmpeg", "-y", "-ss", str(cut_out - 1.0), "-t", "1.0",
 671 |              "-i", source, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp_wav,
 672 |          ], capture_output=True, timeout=10, check=True)
 673 | -        model = WhisperModel("medium", device="cuda", compute_type="float16")
 674 | +        import gpu0
 675 | +        model = gpu0.whisper("medium")          # L-r: through swap_to, under the session's GPU0 lease
 676 |          segments, _ = model.transcribe(tmp_wav, language="en", beam_size=5)
 677 |          text = " ".join(seg.text.strip() for seg in segments).lower()
 678 |          os.unlink(tmp_wav)
 679 | diff --git a/pipeline/test_pinned.py b/pipeline/test_pinned.py
 680 | index ff16fc2f..8c962ed0 100644
 681 | --- a/pipeline/test_pinned.py
 682 | +++ b/pipeline/test_pinned.py
 683 | @@ -289,8 +289,9 @@ class TestPinnedStageFreesGpu0First(Fixture):
 684 |              self.assertEqual(events, [("release", "pinned"), "prepare"])
 685 |              events.clear()
 686 |              rf.free_gpu0_for_whisper = refuse
 687 | -            with self.assertRaisesRegex(rf.Hold, "infrastructure: pinned"):
 688 | +            with self.assertRaisesRegex(rf.Hold, "^infrastructure: pinned") as cm:    # anchored (fable audit of 456a440f)
 689 |                  rf.stage_pinned(run, self.write(self.pin()))
 690 | +            self.assertNotIn("pinned decision rejected", str(cm.exception))
 691 |              self.assertEqual(events, [("release", "pinned")])        # nothing downloaded or transcribed after it
 692 |          finally:
 693 |              rf.free_gpu0_for_whisper, pinned.prepare = orig_free, orig_prep
 694 | diff --git a/pipeline/test_pulse_20261110_mustfail.py b/pipeline/test_pulse_20261110_mustfail.py
 695 | index 61d5335a..90e3c888 100644
 696 | --- a/pipeline/test_pulse_20261110_mustfail.py
 697 | +++ b/pipeline/test_pulse_20261110_mustfail.py
 698 | @@ -294,8 +294,9 @@ class TestPunctuationLayer(unittest.TestCase):
 699 |          from faster_whisper import WhisperModel
 700 |          raw = json.load(open(os.path.join(FIX, "run", "transcripts", "36HPi9UZPOc.json")))
 701 |          want = json.load(open(os.path.join(FIX, "selection", "transcripts_punctuated", "36HPi9UZPOc.json")))
 702 | +        import gpu0
 703 |          got = P.ensure(raw, os.path.join(FIX, "audio", "src_36HPi9UZPOc.flac"),
 704 | -                       WhisperModel("large-v3", device="cuda", compute_type="float16"))
 705 | +                       gpu0.whisper("large-v3"))         # L-r: through swap_to, under the session's GPU0 lease
 706 |          self.assertEqual([w["word"] for w in got["words"]], [w["word"] for w in want["words"]])
 707 |  
 708 |  
 709 | diff --git a/pipeline/test_punct_word_pass.py b/pipeline/test_punct_word_pass.py
 710 | index 33ecee49..58b34169 100644
 711 | --- a/pipeline/test_punct_word_pass.py
 712 | +++ b/pipeline/test_punct_word_pass.py
 713 | @@ -157,34 +157,67 @@ class TestAcquireUpgrade(unittest.TestCase):
 714 |  
 715 |      def test_a_failed_restoration_is_not_sentence_ready(self):
 716 |          def boom():
 717 | -            raise RuntimeError("CUDA out of memory (simulated)")
 718 | +            raise RuntimeError("reference decode failed (simulated)")
 719 |          ts._reference = boom
 720 |          r, st = ts.acquire(self.vid, prefer_words=True)
 721 |          self.assertEqual((st, r["transcript_method"]), ("punctuation_failed", "whisper_words"))
 722 |          self.assertFalse(ts.sentence_ready(r))                 # editorial_select treats it as a failure
 723 | -        self.assertIn("out of memory", ts.LAST_ERROR[self.vid])
 724 | +        self.assertIn("reference decode failed", ts.LAST_ERROR[self.vid])
 725 | +
 726 | +    def test_an_out_of_memory_is_never_a_failure_status(self):
 727 | +        """Law L-r (E-FAIL-052): until Nov 12 a simulated out-of-memory here became 'punctuation_failed' (a video's
 728 | +        failure). It now leaves acquire as gpu0.GpuOOM for the stage's one bounded retry."""
 729 | +        import gpu0
 730 | +        def boom():
 731 | +            raise RuntimeError("CUDA out of memory (simulated)")
 732 | +        ts._reference = boom
 733 | +        saved = ts.release_whisper
 734 | +        ts.release_whisper = lambda: None
 735 | +        try:
 736 | +            with self.assertRaisesRegex(gpu0.GpuOOM, "punctuation: CUDA out of memory"):
 737 | +                ts.acquire(self.vid, prefer_words=True)
 738 | +        finally:
 739 | +            ts.release_whisper = saved
 740 |  
 741 |  
 742 |  class TestOneWhisperModelAtATime(unittest.TestCase):
 743 |      """Heimdall batch13: the word pass's GPU0 arbitration proves 7 GB free, so distil-large-v3 and the large-v3
 744 | -    reference are never resident together (stubbed models, no GPU)."""
 745 | +    reference are never resident together (stubbed models, no GPU). Law L-r makes it so by construction: both are
 746 | +    gpu0 Models, and loading one through swap_to deletes the other."""
 747 |      def test_loading_one_drops_the_other(self):
 748 |          import types
 749 | +        import tempfile
 750 | +        from unittest import mock
 751 | +        import gpu0
 752 |          fw = types.ModuleType("faster_whisper")
 753 |          fw.WhisperModel = type("WM", (), {"__init__": lambda self, name, **kw: setattr(self, "name", name)})
 754 |          fw.BatchedInferencePipeline = type("BP", (), {"__init__": lambda self, model: setattr(self, "model", model)})
 755 |          saved = (sys.modules.get("faster_whisper"), os.environ.get("CUDA_VISIBLE_DEVICES"), ts._WHISPER, ts._REFERENCE)
 756 |          sys.modules["faster_whisper"], os.environ["CUDA_VISIBLE_DEVICES"] = fw, "0"
 757 |          ts._WHISPER = ts._REFERENCE = None
 758 | +        fake = [mock.patch.object(gpu0, "memory", return_value=(100, 24564)),
 759 | +                mock.patch.object(gpu0, "processes", return_value=[]),
 760 | +                mock.patch.object(gpu0, "ollama_loaded", return_value=[]),
 761 | +                mock.patch.object(gpu0, "_ollama_unload", return_value=[]),
 762 | +                mock.patch.dict(os.environ, {"PP_GPU0_LEASE": os.path.join(tempfile.mkdtemp(), "lease")})]
 763 | +        for f in fake:
 764 | +            f.start()
 765 |          try:
 766 | -            a = ts._whisper()
 767 | -            self.assertEqual((a.model.name, ts._REFERENCE), (ts.WHISPER_MODEL, None))
 768 | -            self.assertIs(ts._whisper(), a)
 769 | -            b = ts._reference()
 770 | -            self.assertEqual((b.model.name, ts._WHISPER), (ts.REFERENCE_MODEL, None))
 771 | -            ts._whisper()
 772 | -            self.assertIsNone(ts._REFERENCE)
 773 | +            with gpu0.lease("test"):
 774 | +                a = ts._whisper()
 775 | +                self.assertEqual((a.model.name, ts._REFERENCE), (ts.WHISPER_MODEL, None))
 776 | +                self.assertIs(ts._whisper(), a)
 777 | +                b = ts._reference()
 778 | +                self.assertEqual((b.model.name, ts._WHISPER), (ts.REFERENCE_MODEL, None))
 779 | +                self.assertFalse(a.loaded)                            # deleted by the swap to the reference
 780 | +                ts._whisper().model                                    # loads on first use (lazy)
 781 | +                self.assertIsNone(ts._REFERENCE)
 782 | +                self.assertFalse(b.loaded)
 783 |          finally:
 784 | +            for f in reversed(fake):
 785 | +                f.stop()
 786 | +            for m in (gpu0.whisper(ts.WHISPER_MODEL, batched=True), gpu0.whisper(ts.REFERENCE_MODEL, batched=True)):
 787 | +                m.unload()
 788 |              mod, cvd, ts._WHISPER, ts._REFERENCE = saved
 789 |              if mod is None:
 790 |                  sys.modules.pop("faster_whisper", None)
 791 | diff --git a/pipeline/transcript_store.py b/pipeline/transcript_store.py
 792 | index 4a9ac39c..c45b8667 100644
 793 | --- a/pipeline/transcript_store.py
 794 | +++ b/pipeline/transcript_store.py
 795 | @@ -292,6 +292,9 @@ def release_whisper():
 796 |      """Drop the Whisper models and free their GPU memory (E5). Returns GPU0 used MiB after."""
 797 |      global _WHISPER, _REFERENCE
 798 |      _WHISPER = _REFERENCE = None
 799 | +    import gpu0
 800 | +    for name in (WHISPER_MODEL, REFERENCE_MODEL):
 801 | +        gpu0.whisper(name, batched=True).unload()
 802 |      import gc
 803 |      gc.collect()
 804 |      try:
 805 | @@ -304,21 +307,18 @@ def release_whisper():
 806 |  
 807 |  def _load(name):
 808 |      """One Whisper model on GPU0 at a time (the word pass's arbitration proves 7 GB free, not two models' worth;
 809 | -    Heimdall batch13): loading one drops the other first."""
 810 | +    Heimdall batch13): L-r makes it so by construction: gpu0.whisper loads through swap_to, which deletes every
 811 | +    other GPU0 model first, and the model reloads through swap_to after any later swap."""
 812 |      global _WHISPER, _REFERENCE
 813 |      if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
 814 |          raise AcquisitionError("Whisper requires CUDA_VISIBLE_DEVICES=0 (GPU1 quarantined)")
 815 | -    if (_WHISPER if name == WHISPER_MODEL else _REFERENCE) is None:
 816 | -        import gc
 817 | -        _WHISPER = _REFERENCE = None
 818 | -        gc.collect()
 819 | -        from faster_whisper import WhisperModel, BatchedInferencePipeline
 820 | -        m = BatchedInferencePipeline(model=WhisperModel(name, device="cuda", compute_type="float16"))
 821 | -        if name == WHISPER_MODEL:
 822 | -            _WHISPER = m
 823 | -        else:
 824 | -            _REFERENCE = m
 825 | -    return _WHISPER if name == WHISPER_MODEL else _REFERENCE
 826 | +    import gpu0
 827 | +    m = gpu0.whisper(name, batched=True)
 828 | +    if name == WHISPER_MODEL:
 829 | +        _WHISPER, _REFERENCE = m, None
 830 | +    else:
 831 | +        _WHISPER, _REFERENCE = None, m
 832 | +    return m
 833 |  
 834 |  
 835 |  def _whisper():
 836 | @@ -480,8 +480,10 @@ def acquire(video_id, rss=None, channel=None, allow_whisper=True, prefer_words=F
 837 |      except Exception as e:
 838 |          LAST_ERROR[video_id] = f"{type(e).__name__}: {e}"[-400:]
 839 |          _log_attempt(video_id, step=step, status="error", error=str(e)[-300:])
 840 | -        if "out of memory" in str(e).lower():
 841 | -            release_whisper()          # never keep a half-initialised model around
 842 | +        import gpu0
 843 | +        if gpu0.is_oom(e):             # L-r: an out-of-memory is never a video's failure status; it leaves as GpuOOM
 844 | +            release_whisper()          # (never keep a half-initialised model around), for the stage's one retry
 845 | +            raise gpu0.GpuOOM(f"{video_id}: {step}: CUDA out of memory ({type(e).__name__}: {str(e)[:200]})") from e
 846 |          return canonical_transcript(video_id), f"{step}_failed"
 847 |      return canonical_transcript(video_id), status
 848 |  
 849 | diff --git a/pipeline/word_diff.py b/pipeline/word_diff.py
 850 | index 386cb7a0..8c25e650 100644
 851 | --- a/pipeline/word_diff.py
 852 | +++ b/pipeline/word_diff.py
 853 | @@ -70,8 +70,8 @@ def edges(lock_text, heard, n=EDGE_WORDS):
 854 |  
 855 |  class Transcriber:
 856 |      def __init__(self):
 857 | -        from faster_whisper import WhisperModel
 858 | -        self.model = WhisperModel(ASR["model"], device="cuda", compute_type="float16")
 859 | +        import gpu0
 860 | +        self.model = gpu0.whisper(ASR["model"])      # L-r: loaded through swap_to on first use
 861 |  
 862 |      def span(self, media, t0, t1):
 863 |          if t1 - t0 < 0.05:
 864 | diff --git a/scripts/pulse_check_run.sh b/scripts/pulse_check_run.sh
 865 | index 34183a0f..9a1449fd 100755
 866 | --- a/scripts/pulse_check_run.sh
 867 | +++ b/scripts/pulse_check_run.sh
 868 | @@ -72,6 +72,16 @@ if ! flock -n 9; then
 869 |    echo "pulse_check_run: another run holds /tmp/pulse_check_run.lock" | tee -a "$LOG" >&2
 870 |    exit 75
 871 |  fi
 872 | +# law L-r ONE OWNER: the GPU0 lease (pipeline/gpu0.py) on fd 8 for the whole run; preflight and run_fresh inherit
 873 | +# the descriptor (custody), nothing else may load onto GPU0 meanwhile; released when this script exits
 874 | +GPU0_LEASE="${PP_GPU0_LEASE:-/tmp/pulse_gpu0.lease}"
 875 | +exec 8>>"$GPU0_LEASE"
 876 | +if ! flock -n 8; then
 877 | +  echo "pulse_check_run: the GPU0 lease is held: $(cat "$GPU0_LEASE" 2>/dev/null)" | tee -a "$LOG" >&2
 878 | +  exit 75
 879 | +fi
 880 | +printf '{"pid": %s, "owner": "pulse_check_run %s (%s)", "since": %s}' $$ "$STAMP" "${ARGS[*]:-auto}" "$(date +%s)" \
 881 | +  > "$GPU0_LEASE"
 882 |  
 883 |  export CUDA_VISIBLE_DEVICES=0
 884 |  cd "$REPO/pipeline" || exit 1
 885 | diff --git a/segment_v1/qa_gates.py b/segment_v1/qa_gates.py
 886 | index 19ba78dd..6f4b7f82 100644
 887 | --- a/segment_v1/qa_gates.py
 888 | +++ b/segment_v1/qa_gates.py
 889 | @@ -47,16 +47,21 @@ G9_REENCODE_SPREAD = {"16x9": 0.05, "9x16": 0.04}      # DEC-12a: MEASURED sprea
 890 |      # made a correct render pass or fail by encoder state (OD-4).
 891 |  G9_LUMA_FLOOR = {k: round(G9_V2F_LUMA[k] - G9_REENCODE_SPREAD[k], 4) for k in G9_V2F_LUMA}   # 14.2857 / 14.7315
 892 |  
 893 | -# ── Faster-Whisper singleton (medium, float16, cuda, vad OFF, word timestamps) ──
 894 | -_FW_MODEL = None
 895 | +# ── Faster-Whisper medium (float16, GPU0, vad OFF, word timestamps): law L-r, through pipeline/gpu0.py ──
 896 | +
 897 | +def _gpu0():
 898 | +    """pipeline/gpu0.py (law L-r), importable when this file runs on its own too."""
 899 | +    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline")
 900 | +    if p not in sys.path:
 901 | +        sys.path.insert(0, p)
 902 | +    import gpu0
 903 | +    return gpu0
 904 | +
 905 |  
 906 |  def _get_fw_model():
 907 | -    """Load faster-whisper medium model once per gate run."""
 908 | -    global _FW_MODEL
 909 | -    if _FW_MODEL is None:
 910 | -        from faster_whisper import WhisperModel
 911 | -        _FW_MODEL = WhisperModel("medium", device="cuda", compute_type="float16")
 912 | -    return _FW_MODEL
 913 | +    """The process's one faster-whisper medium: gpu0.whisper loads it through swap_to on first use (every other
 914 | +    GPU0 model unloaded, the memory proven free), any later swap deletes it, and it reloads when used again."""
 915 | +    return _gpu0().whisper("medium")
 916 |  
 917 |  
 918 |  def fw_transcribe(wav_path, word_timestamps=True):
 919 | @@ -146,7 +151,7 @@ def gate_g1(final_mp4, manifest, vo_regions, qa_dir, vo_assembled_tracks=None):
 920 |      from resemblyzer import VoiceEncoder, preprocess_wav
 921 |  
 922 |      print("\n=== G1: VOICE IDENTITY ===")
 923 | -    encoder = VoiceEncoder()
 924 | +    encoder = _gpu0().model("resemblyzer", VoiceEncoder)     # L-r: loaded through swap_to; calls inside guard()
 925 |  
 926 |      if vo_assembled_tracks is None:
 927 |          vo_assembled_tracks = {}
 928 | diff --git a/pipeline/gpu0.py b/pipeline/gpu0.py
 929 | new file mode 100644
 930 | index 00000000..f4cb840f
 931 | --- /dev/null
 932 | +++ b/pipeline/gpu0.py
 933 | @@ -0,0 +1,583 @@
 934 | +#!/usr/bin/env python3
 935 | +"""pipeline/gpu0.py — law L-r GPU0 NEVER SURPRISES A RUN (orchestrator 2026-11-12 '01:55' B; PBX on the pinned run's
 936 | +out-of-memory: "let's make sure that never happens again").
 937 | +
 938 | +ONE OWNER. GPU0 belongs to whoever holds the lease: an exclusive flock on the lease file (/tmp/pulse_gpu0.lease; the
 939 | +environment variable PP_GPU0_LEASE overrides it), the holder recorded in the file. Entry points take it:
 940 | +scripts/pulse_check_run.sh on fd 8 for the whole run (preflight and run_fresh inherit that descriptor), and run_fresh,
 941 | +preflight, backtest and GPU test sessions with lease() when started on their own. held() is true in a process that
 942 | +took it with lease(), or that inherited a descriptor whose open file description holds the flock (a second flock on
 943 | +that description succeeds; on any other description it fails while the lock is held). Every load onto GPU0 goes
 944 | +through swap_to(), which calls require(): no lease, no load.
 945 | +
 946 | +ONE MODEL AT A TIME. swap_to(key) is the one way anything gets onto GPU0. It refuses a foreign GPU0 process, unloads
 947 | +everything else that is resident (this process's Model objects, every model on the GPU0 Ollama via keep_alive=0,
 948 | +confirmed on /api/ps), collects garbage and empties torch's cache, then waits until nvidia-smi shows GPU0 free >=
 949 | +REQUIREMENT_MIB[key] + MARGIN_MIB. A Model (whisper(), model()) loads through swap_to on first use, is deleted
 950 | +by any later swap, and loads again through swap_to when it is used again; its calls run inside guard().
 951 | +
 952 | +STOPS. Every refusal is a Gpu0Stop, a BaseException, so no `except Exception` between a load and the stage runner can
 953 | +turn it into another error ('transcription failed' hid an out-of-memory on Nov 12, E-FAIL-052): GpuOOM (a CUDA
 954 | +out-of-memory inside guard()), Gpu0Foreign (GPU0 memory held by a process that is not this run's), LeaseMissing (a
 955 | +load without the lease), LeaseBusy (another owner holds the lease), Gpu0NotFree (the memory did not come free in
 956 | +time), Gpu0Unreadable (nvidia-smi or the Ollama listener cannot be read: never read as 'nothing there'). run_fresh's
 957 | +stage runner owns the one retry of an out-of-memory and turns every other stop into a HOLD carrying the real cause."""
 958 | +import contextlib
 959 | +import fcntl
 960 | +import gc
 961 | +import json
 962 | +import os
 963 | +import re
 964 | +import subprocess
 965 | +import sys
 966 | +import threading
 967 | +import time
 968 | +import urllib.error
 969 | +import urllib.request
 970 | +
 971 | +DEFAULT_LEASE = "/tmp/pulse_gpu0.lease"
 972 | +OLLAMA_HOST = "127.0.0.1:11434"            # the GPU0 Ollama listener (story_semantics.LLM_HOST)
 973 | +MARGIN_MIB = 1024
 974 | +# Peak GPU0 memory one load needs (MiB, its process's CUDA context included): the peak measured on this host's 24564 MiB
 975 | +# GPU0 by pipeline/measure_gpu0.py on 2026-11-12 (600 s of speech; DoD 'L-r GPU0 requirements'), rounded up by ~5%;
 976 | +# swap_to adds MARGIN_MIB. A key missing here can never be loaded.
 977 | +REQUIREMENT_MIB = {
 978 | +    "ollama:gemma3:27b": 20600,            # resident 20548-20559 (nvidia-smi 01:43 / 01:55 ET); measured peak 19241
 979 | +    "whisper:large-v3": 6000,              # measured 5657 (beam 5, word timestamps, 600 s)
 980 | +    "whisper:large-v3:batched": 9600,      # measured 9145 (batch 16 full: 600 s)
 981 | +    "whisper:distil-large-v3:batched": 5700,   # measured 5401 (batch 16 full: 600 s)
 982 | +    "whisper:medium": 2800,                # measured 2649
 983 | +    "embedder": 1500,                      # measured 1379 (bge-base fp16, 64 x 512 tokens)
 984 | +    "resemblyzer": 850,                    # measured 775
 985 | +    "nvenc": 600,                          # measured 536 (one 1080x1920 h264_nvenc encode at a time)
 986 | +}
 987 | +WAIT_S = 180
 988 | +
 989 | +
 990 | +class Gpu0Stop(BaseException):
 991 | +    """A GPU0 refusal. A BaseException on purpose: it passes every `except Exception` up to the stage runner."""
 992 | +
 993 | +
 994 | +class GpuOOM(Gpu0Stop):
 995 | +    """A CUDA out-of-memory raised inside guard() (the original exception is its __cause__)."""
 996 | +
 997 | +
 998 | +class Gpu0Foreign(Gpu0Stop):
 999 | +    """GPU0 memory is held by a process that is not this run's."""
1000 | +
1001 | +
1002 | +class LeaseMissing(Gpu0Stop):
1003 | +    """A GPU0 load in a process that does not hold the lease."""
1004 | +
1005 | +
1006 | +class LeaseBusy(Gpu0Stop):
1007 | +    """Another owner holds the lease."""
1008 | +
1009 | +
1010 | +class Gpu0NotFree(Gpu0Stop):
1011 | +    """The memory a load needs did not come free in time."""
1012 | +
1013 | +
1014 | +class Gpu0Unreadable(Gpu0Stop):
1015 | +    """nvidia-smi or the GPU0 Ollama listener cannot be read."""
1016 | +
1017 | +
1018 | +_lock = threading.RLock()
1019 | +_own = {}           # lease path -> {"file", "pid", "depth"}: this process's own lease() holdings
1020 | +_resident = []      # Model objects loaded on GPU0 by this process
1021 | +_events = []        # every swap's evidence (run_fresh copies it into PROVENANCE)
1022 | +_gen = [0]          # bumped whenever the resident set changes (LocalLLM re-swaps only when it moved)
1023 | +
1024 | +
1025 | +# ── the lease ──
1026 | +
1027 | +def lease_path():
1028 | +    return os.path.realpath(os.environ.get("PP_GPU0_LEASE", DEFAULT_LEASE))
1029 | +
1030 | +
1031 | +def _fds_on(target):
1032 | +    out = []
1033 | +    for name in os.listdir("/proc/self/fd"):
1034 | +        try:
1035 | +            if os.path.realpath(os.readlink(f"/proc/self/fd/{name}")) == target:
1036 | +                out.append(int(name))
1037 | +        except (OSError, ValueError):
1038 | +            continue
1039 | +    return out
1040 | +
1041 | +
1042 | +def held():
1043 | +    """True when this process holds the lease (see the module docstring)."""
1044 | +    target = lease_path()
1045 | +    h = _own.get(target)
1046 | +    if h and h["pid"] == os.getpid():
1047 | +        return True
1048 | +    for fd in _fds_on(target):
1049 | +        try:
1050 | +            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
1051 | +            return True
1052 | +        except OSError:
1053 | +            continue
1054 | +    return False
1055 | +
1056 | +
1057 | +def holder():
1058 | +    """The recorded holder {"pid", "owner", "since"} while the lease is held, None when it is free."""
1059 | +    try:
1060 | +        f = open(lease_path(), "a+")
1061 | +    except OSError as e:
1062 | +        return {"pid": None, "owner": f"lease file unreadable ({type(e).__name__})"}
1063 | +    with f:
1064 | +        try:
1065 | +            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
1066 | +        except OSError:
1067 | +            return _record(f)
1068 | +        fcntl.flock(f, fcntl.LOCK_UN)              # this probe's own private description only
1069 | +        return None
1070 | +
1071 | +
1072 | +def _record(f):
1073 | +    try:
1074 | +        rec = json.loads(os.pread(f.fileno(), 4096, 0).decode(errors="replace") or "{}")
1075 | +    except (OSError, ValueError):
1076 | +        rec = {}
1077 | +    return rec if isinstance(rec, dict) else {}
1078 | +
1079 | +
1080 | +@contextlib.contextmanager
1081 | +def lease(owner, wait_s=0.0, poll_s=0.2):
1082 | +    """Hold the lease for the block. Re-entrant where this process already holds it (its own lease() or an inherited
1083 | +    descriptor); otherwise acquired within wait_s, or LeaseBusy naming the holder. Released by closing the
1084 | +    descriptor (never LOCK_UN): a child that was handed it keeps GPU0 until it closes it too."""
1085 | +    target = lease_path()
1086 | +    if held():
1087 | +        h = _own.get(target)
1088 | +        if h and h["pid"] == os.getpid():
1089 | +            h["depth"] += 1
1090 | +            try:
1091 | +                yield
1092 | +            finally:
1093 | +                h["depth"] -= 1
1094 | +        else:
1095 | +            yield
1096 | +        return
1097 | +    f = open(target, "a+")
1098 | +    t0 = time.time()
1099 | +    while True:
1100 | +        try:
1101 | +            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
1102 | +            break
1103 | +        except OSError:
1104 | +            if time.time() - t0 >= wait_s:
1105 | +                rec = _record(f)
1106 | +                f.close()
1107 | +                raise LeaseBusy(f"the GPU0 lease is held by {rec.get('owner', 'an unrecorded owner')} "
1108 | +                                f"(pid {rec.get('pid')})") from None
1109 | +            time.sleep(poll_s)
1110 | +    f.seek(0)
1111 | +    f.truncate()
1112 | +    json.dump({"pid": os.getpid(), "owner": owner, "since": time.time()}, f)
1113 | +    f.flush()
1114 | +    _own[target] = {"file": f, "pid": os.getpid(), "depth": 1}
1115 | +    try:
1116 | +        yield
1117 | +    finally:
1118 | +        _own.pop(target, None)
1119 | +        f.close()
1120 | +
1121 | +
1122 | +def require(what):
1123 | +    """No lease, no load; and GPU0 only (GPU1 is quarantined)."""
1124 | +    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
1125 | +        raise LeaseMissing(f"{what}: GPU0 loads need CUDA_VISIBLE_DEVICES=0 (it is "
1126 | +                           f"{os.environ.get('CUDA_VISIBLE_DEVICES')!r}; GPU1 is quarantined)")
1127 | +    if not held():
1128 | +        raise LeaseMissing(f"{what}: a GPU0 load without the GPU0 lease (law L-r: no lease, no load); "
1129 | +                           f"holder: {holder()}")
1130 | +
1131 | +
1132 | +# ── what is on GPU0 ──
1133 | +
1134 | +def _smi(args, timeout=15):
1135 | +    try:
1136 | +        r = subprocess.run(["nvidia-smi", *args], capture_output=True, text=True, timeout=timeout)
1137 | +    except (OSError, subprocess.TimeoutExpired) as e:
1138 | +        raise Gpu0Unreadable(f"nvidia-smi: {type(e).__name__}") from None
1139 | +    if r.returncode != 0:
1140 | +        raise Gpu0Unreadable(f"nvidia-smi exit {r.returncode}: {r.stderr.strip()[:200]}")
1141 | +    return r.stdout
1142 | +
1143 | +
1144 | +def memory():
1145 | +    """(used_mib, total_mib) of GPU index 0."""
1146 | +    out = _smi(["-i", "0", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"])
1147 | +    try:
1148 | +        used, total = (int(x) for x in out.strip().split(","))
1149 | +    except ValueError:
1150 | +        raise Gpu0Unreadable(f"nvidia-smi memory line unreadable: {out.strip()[:80]!r}") from None
1151 | +    return used, total
1152 | +
1153 | +
1154 | +def processes():
1155 | +    """[(pid, name, MiB)] of every compute process on GPU index 0."""
1156 | +    uuid = _smi(["-i", "0", "--query-gpu=uuid", "--format=csv,noheader"]).strip()
1157 | +    if not uuid:
1158 | +        raise Gpu0Unreadable("nvidia-smi names no GPU 0")
1159 | +    out = []
1160 | +    for line in _smi(["--query-compute-apps=pid,gpu_uuid,used_memory,process_name",
1161 | +                      "--format=csv,noheader,nounits"]).strip().splitlines():
1162 | +        p = [x.strip() for x in line.split(",", 3)]
1163 | +        if len(p) == 4 and p[1] == uuid and p[0].isdigit():
1164 | +            out.append((int(p[0]), os.path.basename(p[3]), int(p[2]) if p[2].isdigit() else None))
1165 | +    return out
1166 | +
1167 | +
1168 | +def describe(procs):
1169 | +    return ", ".join(f"pid {p} {n} {m} MiB" for p, n, m in procs) or "nothing"
1170 | +
1171 | +
1172 | +def _parent(pid):
1173 | +    with open(f"/proc/{pid}/stat") as f:
1174 | +        return int(f.read().rsplit(")", 1)[1].split()[1])
1175 | +
1176 | +
1177 | +def _ancestors():
1178 | +    out, pid = set(), os.getpid()
1179 | +    while pid > 1:
1180 | +        try:
1181 | +            pid = _parent(pid)
1182 | +        except (OSError, ValueError, IndexError):
1183 | +            break
1184 | +        out.add(pid)
1185 | +    return out
1186 | +
1187 | +
1188 | +def _descendants():
1189 | +    out, todo = set(), [os.getpid()]
1190 | +    while todo:
1191 | +        p = todo.pop()
1192 | +        try:
1193 | +            tids = os.listdir(f"/proc/{p}/task")
1194 | +        except OSError:
1195 | +            continue
1196 | +        for tid in tids:
1197 | +            try:
1198 | +                with open(f"/proc/{p}/task/{tid}/children") as f:
1199 | +                    kids = [int(x) for x in f.read().split()]
1200 | +            except (OSError, ValueError):
1201 | +                continue
1202 | +            for k in kids:
1203 | +                if k not in out:
1204 | +                    out.add(k)
1205 | +                    todo.append(k)
1206 | +    return out
1207 | +
1208 | +
1209 | +def _ollama_pids():
1210 | +    port = OLLAMA_HOST.rsplit(":", 1)[1]
1211 | +    try:
1212 | +        r = subprocess.run(["ss", "-ltnpH", f"sport = :{port}"], capture_output=True, text=True, timeout=10)
1213 | +        serve = {int(p) for p in re.findall(r"pid=(\d+)", r.stdout)}
1214 | +        kids = set()
1215 | +        for p in serve:
1216 | +            k = subprocess.run(["pgrep", "-P", str(p)], capture_output=True, text=True, timeout=10)
1217 | +            kids |= {int(x) for x in k.stdout.split()}
1218 | +    except (OSError, subprocess.TimeoutExpired) as e:
1219 | +        raise Gpu0Unreadable(f"cannot read the GPU0 Ollama listener: {type(e).__name__}") from None
1220 | +    return serve | kids
1221 | +
1222 | +
1223 | +def foreign():
1224 | +    """GPU0 compute processes that are not this run's: anything but this process, its ancestors (the wrapper that
1225 | +    holds the lease) and descendants, and the GPU0 Ollama listener with its runners (whose models every swap
1226 | +    unloads)."""
1227 | +    ours = {os.getpid()} | _ancestors() | _descendants() | _ollama_pids()
1228 | +    return [p for p in processes() if p[0] not in ours]
1229 | +
1230 | +
1231 | +# ── the GPU0 Ollama ──
1232 | +
1233 | +def _ollama(path, body=None, timeout=30):
1234 | +    req = urllib.request.Request(f"http://{OLLAMA_HOST}{path}",
1235 | +                                 data=None if body is None else json.dumps(body).encode(),
1236 | +                                 headers={"Content-Type": "application/json"})
1237 | +    return json.loads(urllib.request.urlopen(req, timeout=timeout).read() or b"{}")
1238 | +
1239 | +
1240 | +def ollama_loaded():
1241 | +    """Names of the models resident on the GPU0 Ollama ([] when nothing listens there)."""
1242 | +    try:
1243 | +        return [m["name"] for m in _ollama("/api/ps").get("models", [])]
1244 | +    except urllib.error.URLError as e:
1245 | +        if isinstance(getattr(e, "reason", None), ConnectionRefusedError):
1246 | +            return []
1247 | +        raise Gpu0Unreadable(f"Ollama {OLLAMA_HOST} /api/ps: {e}") from None
1248 | +    except (OSError, ValueError, KeyError, TypeError) as e:
1249 | +        raise Gpu0Unreadable(f"Ollama {OLLAMA_HOST} /api/ps: {type(e).__name__}: {e}") from None
1250 | +
1251 | +
1252 | +def _ollama_unload(keep=None, wait_s=60):
1253 | +    names = [n for n in ollama_loaded() if n != keep]
1254 | +    for n in names:
1255 | +        try:
1256 | +            _ollama("/api/generate", {"model": n, "keep_alive": 0}, timeout=120)
1257 | +        except (OSError, ValueError) as e:
1258 | +            raise Gpu0NotFree(f"Ollama would not unload {n}: {type(e).__name__}: {e}") from None
1259 | +    t0 = time.time()
1260 | +    while True:
1261 | +        left = [n for n in ollama_loaded() if n != keep]
1262 | +        if not left:
1263 | +            return names
1264 | +        if time.time() - t0 > wait_s:
1265 | +            raise Gpu0NotFree(f"Ollama still holds {left} {wait_s}s after keep_alive=0")
1266 | +        time.sleep(1)
1267 | +
1268 | +
1269 | +# ── swaps ──
1270 | +
1271 | +def generation():
1272 | +    return _gen[0]
1273 | +
1274 | +
1275 | +def events():
1276 | +    return list(_events)
1277 | +
1278 | +
1279 | +def _empty_caches():
1280 | +    gc.collect()
1281 | +    torch = sys.modules.get("torch")
1282 | +    if torch is not None:
1283 | +        try:
1284 | +            if torch.cuda.is_initialized():
1285 | +                torch.cuda.empty_cache()
1286 | +        except Exception:
1287 | +            pass
1288 | +
1289 | +
1290 | +def _ollama_key(key):
1291 | +    return key[len("ollama:"):] if key.startswith("ollama:") else None
1292 | +
1293 | +
1294 | +def swap_to(key, wait_s=WAIT_S, poll_s=2.0):
1295 | +    """Make GPU0 ready for `key` and nothing else this run can unload (see the module docstring). Returns the
1296 | +    evidence it recorded. Raises a Gpu0Stop."""
1297 | +    require(f"swap_to({key})")
1298 | +    if key not in REQUIREMENT_MIB:
1299 | +        raise Gpu0NotFree(f"{key}: no measured GPU0 requirement (gpu0.REQUIREMENT_MIB): never loaded")
1300 | +    with _lock:
1301 | +        f = foreign()
1302 | +        if f:
1303 | +            raise Gpu0Foreign(f"GPU0 memory is held by a process that is not this run's: {describe(f)}")
1304 | +        ev = {"key": key, "at": time.time(), "before": memory(), "unloaded": []}
1305 | +        for m in [m for m in _resident if m.key != key]:
1306 | +            m.unload()
1307 | +            ev["unloaded"].append(m.key)
1308 | +        name = _ollama_key(key)
1309 | +        ev["unloaded"] += [f"ollama:{n}" for n in _ollama_unload(keep=name)]
1310 | +        already = name in ollama_loaded() if name else any(m.key == key for m in _resident)
1311 | +        _empty_caches()
1312 | +        need = REQUIREMENT_MIB[key] + MARGIN_MIB
1313 | +        t0 = time.time()
1314 | +        while True:
1315 | +            used, total = memory()
1316 | +            if already or total - used >= need:
1317 | +                break
1318 | +            if time.time() - t0 > wait_s:
1319 | +                raise Gpu0NotFree(f"{key}: GPU0 has {total - used} MiB free {wait_s}s after the swap, needs {need} "
1320 | +                                  f"({REQUIREMENT_MIB[key]} + margin {MARGIN_MIB}); on GPU0: {describe(processes())}")
1321 | +            time.sleep(poll_s)
1322 | +        if not already:
1323 | +            _gen[0] += 1
1324 | +        ev.update(after=[used, total], free_mib=total - used, already_resident=already,
1325 | +                  waited_s=round(time.time() - t0, 1))
1326 | +        _events.append(ev)
1327 | +        return ev
1328 | +
1329 | +
1330 | +def release_all(wait_s=WAIT_S, idle_mib=None, poll_s=2.0):
1331 | +    """Unload everything this process put on GPU0 (its Models, every GPU0 Ollama model), then wait until nvidia-smi
1332 | +    shows GPU0 at most idle_mib used (default: the smallest requirement, i.e. nothing loaded but CUDA contexts).
1333 | +    Returns evidence; raises Gpu0NotFree naming every GPU0 process when it does not come free."""
1334 | +    idle_mib = min(REQUIREMENT_MIB.values()) if idle_mib is None else idle_mib
1335 | +    with _lock:
1336 | +        ev = {"at": time.time(), "before": memory(), "unloaded": []}
1337 | +        for m in list(_resident):
1338 | +            m.unload()
1339 | +            ev["unloaded"].append(m.key)
1340 | +        ev["unloaded"] += [f"ollama:{n}" for n in _ollama_unload()]
1341 | +        _empty_caches()
1342 | +        _gen[0] += 1
1343 | +        t0 = time.time()
1344 | +        while True:
1345 | +            used, total = memory()
1346 | +            if used <= idle_mib:
1347 | +                ev.update(after=[used, total], waited_s=round(time.time() - t0, 1))
1348 | +                return ev
1349 | +            if time.time() - t0 > wait_s:
1350 | +                raise Gpu0NotFree(f"GPU0 still has {used} MiB used {wait_s}s after releasing everything this run "
1351 | +                                  f"owns (idle is <= {idle_mib}); on GPU0: {describe(processes())}")
1352 | +            time.sleep(poll_s)
1353 | +
1354 | +
1355 | +# ── out of memory ──
1356 | +
1357 | +_OOM = re.compile(r"out of memory|CUDA_ERROR_OUT_OF_MEMORY|cudaErrorMemoryAllocation|CUBLAS_STATUS_ALLOC_FAILED|"
1358 | +                  r"OutOfMemoryError", re.I)
1359 | +
1360 | +
1361 | +def is_oom(e):
1362 | +    """True for a CUDA / NVENC out-of-memory, read from the exception, its type and any captured stderr/output."""
1363 | +    if isinstance(e, GpuOOM):
1364 | +        return True
1365 | +    parts = [type(e).__name__, str(e)]
1366 | +    for attr in ("stderr", "output"):
1367 | +        v = getattr(e, attr, None)
1368 | +        if isinstance(v, bytes):
1369 | +            v = v.decode(errors="replace")
1370 | +        if isinstance(v, str):
1371 | +            parts.append(v[-4000:])
1372 | +    return bool(_OOM.search(" ".join(parts)))
1373 | +
1374 | +
1375 | +@contextlib.contextmanager
1376 | +def guard(what):
1377 | +    """A CUDA out-of-memory raised inside the block leaves it as GpuOOM (nothing can rename it on the way up)."""
1378 | +    try:
1379 | +        yield
1380 | +    except Gpu0Stop:
1381 | +        raise
1382 | +    except Exception as e:
1383 | +        if is_oom(e):
1384 | +            raise GpuOOM(f"{what}: CUDA out of memory ({type(e).__name__}: {str(e)[:300]})") from e
1385 | +        raise
1386 | +
1387 | +
1388 | +def guard_iter(it, what):
1389 | +    """Iterate a lazily decoding iterator (faster-whisper segments) with every step inside guard()."""
1390 | +    while True:
1391 | +        with guard(what):
1392 | +            try:
1393 | +                x = next(it)
1394 | +            except StopIteration:
1395 | +                return
1396 | +        yield x
1397 | +
1398 | +
1399 | +# ── the only GPU0 models ──
1400 | +
1401 | +class Model:
1402 | +    """A GPU0 object loaded only through swap_to (see the module docstring). get() returns the loaded object;
1403 | +    any attribute of it is reachable through the Model, a call running inside guard()."""
1404 | +
1405 | +    def __init__(self, key, build):
1406 | +        self.key, self._build, self._obj = key, build, None
1407 | +
1408 | +    def get(self):
1409 | +        with _lock:
1410 | +            if self._obj is None:
1411 | +                swap_to(self.key)
1412 | +                with guard(f"{self.key}: load"):
1413 | +                    self._obj = self._build()
1414 | +                _resident.append(self)
1415 | +            return self._obj
1416 | +
1417 | +    def unload(self):
1418 | +        with _lock:
1419 | +            self._obj = None
1420 | +            if self in _resident:
1421 | +                _resident.remove(self)
1422 | +
1423 | +    @property
1424 | +    def loaded(self):
1425 | +        return self._obj is not None
1426 | +
1427 | +    def __getattr__(self, name):
1428 | +        if name.startswith("_"):
1429 | +            raise AttributeError(name)
1430 | +        attr = getattr(self.get(), name)
1431 | +        if not callable(attr):
1432 | +            return attr
1433 | +        what = f"{self.key}: {name}"
1434 | +
1435 | +        def call(*a, **k):
1436 | +            with guard(what):
1437 | +                return attr(*a, **k)
1438 | +        return call
1439 | +
1440 | +    def __call__(self, *a, **k):
1441 | +        obj = self.get()
1442 | +        with guard(f"{self.key}: call"):
1443 | +            return obj(*a, **k)
1444 | +
1445 | +
1446 | +class Whisper(Model):
1447 | +    def transcribe(self, *a, **k):
1448 | +        obj = self.get()
1449 | +        with guard(f"{self.key}: transcribe"):
1450 | +            segments, info = obj.transcribe(*a, **k)
1451 | +        return guard_iter(iter(segments), f"{self.key}: decode"), info
1452 | +
1453 | +
1454 | +_models = {}
1455 | +
1456 | +
1457 | +def whisper(name, batched=False):
1458 | +    """The process's one faster-whisper model `name` (float16 on GPU0; batched = a BatchedInferencePipeline)."""
1459 | +    key = f"whisper:{name}" + (":batched" if batched else "")
1460 | +    with _lock:
1461 | +        if key not in _models:
1462 | +            def build():
1463 | +                from faster_whisper import WhisperModel
1464 | +                m = WhisperModel(name, device="cuda", compute_type="float16")
1465 | +                if batched:
1466 | +                    from faster_whisper import BatchedInferencePipeline
1467 | +                    m = BatchedInferencePipeline(model=m)
1468 | +                return m
1469 | +            _models[key] = Whisper(key, build)
1470 | +        return _models[key]
1471 | +
1472 | +
1473 | +def model(key, build):
1474 | +    """The process's one Model for `key` (a torch module, an encoder...): `build` makes the loaded object."""
1475 | +    with _lock:
1476 | +        if key not in _models:
1477 | +            _models[key] = Model(key, build)
1478 | +        return _models[key]
1479 | +
1480 | +
1481 | +# ── evidence ──
1482 | +
1483 | +class PeakSampler:
1484 | +    """GPU0 memory.used sampled every interval_s on a daemon thread; the peak per label (run_fresh: the stage)."""
1485 | +
1486 | +    def __init__(self, interval_s=1.0):
1487 | +        self.interval_s, self.label, self.peaks, self.errors = interval_s, None, {}, 0
1488 | +        self._stop = threading.Event()
1489 | +        self._thread = threading.Thread(target=self._run, daemon=True)
1490 | +
1491 | +    def start(self):
1492 | +        self._thread.start()
1493 | +        return self
1494 | +
1495 | +    def set(self, label):
1496 | +        self.label = label
1497 | +        self._sample()
1498 | +
1499 | +    def _sample(self):
1500 | +        try:
1501 | +            used, _ = memory()
1502 | +        except Gpu0Stop:
1503 | +            self.errors += 1
1504 | +            return
1505 | +        if self.label is not None:
1506 | +            self.peaks[self.label] = max(self.peaks.get(self.label, 0), used)
1507 | +
1508 | +    def _run(self):
1509 | +        while not self._stop.wait(self.interval_s):
1510 | +            self._sample()
1511 | +
1512 | +    def stop(self):
1513 | +        self._stop.set()
1514 | +        self._thread.join(timeout=5)
1515 | +        self._sample()
1516 | +        return dict(self.peaks)
1517 | diff --git a/pipeline/test_gpu0.py b/pipeline/test_gpu0.py
1518 | new file mode 100644
1519 | index 00000000..ee139407
1520 | --- /dev/null
1521 | +++ b/pipeline/test_gpu0.py
1522 | @@ -0,0 +1,283 @@
1523 | +#!/usr/bin/env python3
1524 | +"""Law L-r GPU0 NEVER SURPRISES A RUN (pipeline/gpu0.py): CPU tests with a private lease file and stubbed nvidia-smi /
1525 | +Ollama readings, so they never touch GPU0. The GPU must-fails (a real allocation on GPU0 before a stage) and the
1526 | +back-to-back runs with the per-stage peak table are pipeline/test_gpu0_live.py (GPU0, under the lease)."""
1527 | +import json
1528 | +import os
1529 | +import subprocess
1530 | +import sys
1531 | +import tempfile
1532 | +import textwrap
1533 | +import unittest
1534 | +from unittest import mock
1535 | +
1536 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
1537 | +sys.path.insert(0, PIPELINE)
1538 | +import gpu0  # noqa: E402
1539 | +
1540 | +
1541 | +class Box(unittest.TestCase):
1542 | +    """A private lease file, CUDA_VISIBLE_DEVICES=0, and a fake GPU0: memory / processes / Ollama are stubs."""
1543 | +
1544 | +    def setUp(self):
1545 | +        self.tmp = tempfile.mkdtemp(prefix="gpu0t_")
1546 | +        self.env = mock.patch.dict(os.environ, {"PP_GPU0_LEASE": os.path.join(self.tmp, "lease"),
1547 | +                                                "CUDA_VISIBLE_DEVICES": "0"})
1548 | +        self.env.start()
1549 | +        self.addCleanup(self.env.stop)
1550 | +        self.used = [100]                 # MiB used on the fake GPU0 (a list: tests change it)
1551 | +        self.procs = []                   # fake GPU0 compute processes
1552 | +        self.ollama = []                  # fake resident Ollama models
1553 | +        self.unloaded = []
1554 | +        for name, fn in (("memory", lambda: (self.used[0], 24564)), ("processes", lambda: list(self.procs)),
1555 | +                         ("ollama_loaded", lambda: list(self.ollama)), ("_ollama_pids", lambda: {999999}),
1556 | +                         ("_ollama_unload", self._unload)):
1557 | +            p = mock.patch.object(gpu0, name, side_effect=fn)
1558 | +            p.start()
1559 | +            self.addCleanup(p.stop)
1560 | +        saved = (list(gpu0._resident), dict(gpu0._models), list(gpu0._events))
1561 | +        gpu0._resident.clear()
1562 | +        gpu0._models.clear()
1563 | +
1564 | +        def restore():
1565 | +            gpu0._resident[:] = saved[0]
1566 | +            gpu0._models.clear()
1567 | +            gpu0._models.update(saved[1])
1568 | +            gpu0._events[:] = saved[2]
1569 | +        self.addCleanup(restore)
1570 | +
1571 | +    def _unload(self, keep=None, wait_s=60):
1572 | +        gone = [n for n in self.ollama if n != keep]
1573 | +        self.ollama[:] = [n for n in self.ollama if n == keep]
1574 | +        self.unloaded += gone
1575 | +        return gone
1576 | +
1577 | +
1578 | +class TestLease(Box):
1579 | +    def test_no_lease_no_load_and_gpu0_only(self):
1580 | +        with self.assertRaises(gpu0.LeaseMissing):
1581 | +            gpu0.require("a load")
1582 | +        with gpu0.lease("test"):
1583 | +            gpu0.require("a load")
1584 | +            with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0,1"}):
1585 | +                with self.assertRaisesRegex(gpu0.LeaseMissing, "GPU1 is quarantined"):
1586 | +                    gpu0.require("a load")
1587 | +        self.assertFalse(gpu0.held())
1588 | +
1589 | +    def test_reentrant_and_busy_names_the_holder(self):
1590 | +        with gpu0.lease("outer"):
1591 | +            with gpu0.lease("inner"):
1592 | +                self.assertTrue(gpu0.held())
1593 | +            self.assertTrue(gpu0.held())
1594 | +            code = textwrap.dedent(f"""
1595 | +                import sys; sys.path.insert(0, {PIPELINE!r}); import gpu0
1596 | +                try:
1597 | +                    with gpu0.lease("second"): print("GOT")
1598 | +                except gpu0.LeaseBusy as e: print("BUSY", e)""")
1599 | +            out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60).stdout
1600 | +            self.assertIn("BUSY", out)
1601 | +            self.assertIn("outer", out)                               # the holder is named
1602 | +        self.assertIsNone(gpu0.holder())
1603 | +
1604 | +    def test_an_inherited_descriptor_is_custody_a_reopened_one_is_not(self):
1605 | +        with gpu0.lease("parent"):
1606 | +            fd = gpu0._own[gpu0.lease_path()]["file"].fileno()
1607 | +            os.set_inheritable(fd, True)
1608 | +            code = f"import sys; sys.path.insert(0, {PIPELINE!r}); import gpu0; print(gpu0.held())"
1609 | +            inherited = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
1610 | +                                       pass_fds=(fd,)).stdout.strip()
1611 | +            reopened = subprocess.run([sys.executable, "-c", code + f"; f = open({gpu0.lease_path()!r}, 'a+'); "
1612 | +                                       "print(gpu0.held())"], capture_output=True, text=True, timeout=60).stdout.split()
1613 | +        self.assertEqual(inherited, "True")
1614 | +        self.assertEqual(reopened, ["False", "False"])
1615 | +
1616 | +
1617 | +class TestSwap(Box):
1618 | +    def test_a_foreign_process_is_refused_and_named(self):
1619 | +        self.procs[:] = [(424242, "python3", 4000)]
1620 | +        with gpu0.lease("t"):
1621 | +            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "pid 424242 python3 4000 MiB"):
1622 | +                gpu0.swap_to("whisper:large-v3")
1623 | +
1624 | +    def test_everything_else_is_unloaded_and_the_memory_proven_free(self):
1625 | +        built = []
1626 | +        a = gpu0.model("embedder", lambda: built.append("embedder") or object())
1627 | +        b = gpu0.whisper("medium")
1628 | +        self.ollama[:] = ["gemma3:27b"]
1629 | +        with gpu0.lease("t"):
1630 | +            with mock.patch.object(b, "_build", lambda: built.append("medium") or object()):
1631 | +                a.get()
1632 | +                self.assertEqual(self.unloaded, ["gemma3:27b"])        # the Ollama model went first
1633 | +                b.get()
1634 | +            self.assertEqual(built, ["embedder", "medium"])
1635 | +            self.assertFalse(a.loaded)                                 # one model at a time
1636 | +            self.assertTrue(b.loaded)
1637 | +            ev = gpu0.events()[-1]
1638 | +            self.assertEqual((ev["key"], ev["unloaded"]), ("whisper:medium", ["embedder"]))
1639 | +
1640 | +    def test_memory_that_never_comes_free_is_a_stop_naming_every_process(self):
1641 | +        self.used[0] = 22000
1642 | +        self.procs[:] = [(999999, "ollama", 21000)]                  # the Ollama runner: ours, but not free
1643 | +        need = gpu0.REQUIREMENT_MIB["whisper:large-v3"] + gpu0.MARGIN_MIB
1644 | +        with gpu0.lease("t"):
1645 | +            with self.assertRaisesRegex(gpu0.Gpu0NotFree, rf"needs {need} .*pid 999999 ollama 21000 MiB"):
1646 | +                gpu0.swap_to("whisper:large-v3", wait_s=0, poll_s=0)
1647 | +
1648 | +    def test_an_unknown_model_is_never_loaded(self):
1649 | +        with gpu0.lease("t"):
1650 | +            with self.assertRaisesRegex(gpu0.Gpu0NotFree, "no measured GPU0 requirement"):
1651 | +                gpu0.swap_to("whisper:tiny")
1652 | +
1653 | +    def test_the_model_already_resident_is_kept(self):
1654 | +        self.ollama[:] = ["gemma3:27b"]
1655 | +        self.used[0] = 20600                                           # its own memory: not 'not free'
1656 | +        with gpu0.lease("t"):
1657 | +            ev = gpu0.swap_to("ollama:gemma3:27b", wait_s=0)
1658 | +        self.assertEqual((ev["already_resident"], self.unloaded), (True, []))
1659 | +
1660 | +
1661 | +class TestOutOfMemory(Box):
1662 | +    def test_every_spelling_is_recognised_and_nothing_else(self):
1663 | +        cpe = subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"OpenEncodeSessionEx failed: out of memory (10)")
1664 | +        for e in (RuntimeError("CUDA failed with error out of memory"), cpe,
1665 | +                  type("OutOfMemoryError", (RuntimeError,), {})("CUDA"), RuntimeError("CUBLAS_STATUS_ALLOC_FAILED")):
1666 | +            self.assertTrue(gpu0.is_oom(e), e)
1667 | +        for e in (MemoryError(), OSError(12, "Cannot allocate memory"), RuntimeError("decoder failed"),
1668 | +                  subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"Invalid data found")):
1669 | +            self.assertFalse(gpu0.is_oom(e), e)
1670 | +
1671 | +    def test_a_stop_passes_every_except_exception(self):
1672 | +        def helper():                                    # the shape of select_passages._whisper_transcribe
1673 | +            try:
1674 | +                with gpu0.guard("whisper: transcribe"):
1675 | +                    raise RuntimeError("CUDA failed with error out of memory")
1676 | +            except Exception:
1677 | +                return None                              # 'transcription failed' (E-FAIL-052)
1678 | +        with self.assertRaisesRegex(gpu0.GpuOOM, "whisper: transcribe: CUDA out of memory"):
1679 | +            helper()
1680 | +
1681 | +    def test_a_lazily_decoded_out_of_memory_is_converted_too(self):
1682 | +        def segs():
1683 | +            yield 1
1684 | +            raise RuntimeError("CUDA failed with error out of memory")
1685 | +        it = gpu0.guard_iter(segs(), "decode")
1686 | +        self.assertEqual(next(it), 1)
1687 | +        with self.assertRaises(gpu0.GpuOOM):
1688 | +            next(it)
1689 | +
1690 | +    def test_a_model_call_is_guarded_and_a_non_oom_error_is_unchanged(self):
1691 | +        class Enc:
1692 | +            def embed(self, x):
1693 | +                if x == "oom":
1694 | +                    raise RuntimeError("CUDA error: out of memory")
1695 | +                raise ValueError("bad input")
1696 | +        m = gpu0.model("resemblyzer", Enc)
1697 | +        with gpu0.lease("t"):
1698 | +            with self.assertRaises(gpu0.GpuOOM):
1699 | +                m.embed("oom")
1700 | +            with self.assertRaises(ValueError):
1701 | +                m.embed("x")
1702 | +
1703 | +
1704 | +class TestPeaks(Box):
1705 | +    def test_the_peak_per_label(self):
1706 | +        s = gpu0.PeakSampler(interval_s=3600)
1707 | +        s.set("pinned")
1708 | +        self.used[0] = 5000
1709 | +        s._sample()
1710 | +        self.used[0] = 300
1711 | +        s.set("render")
1712 | +        s.set(None)
1713 | +        self.used[0] = 9999                              # outside any stage: attributed to none
1714 | +        s._sample()
1715 | +        self.assertEqual(s.peaks, {"pinned": 5000, "render": 300})
1716 | +
1717 | +
1718 | +class TestStageRunner(Box):
1719 | +    """run_fresh.Run._attempts: one bounded retry of an out-of-memory, both attempts in PROVENANCE, a second one a
1720 | +    HOLD naming every GPU0 process; every other GPU0 stop a HOLD with its real cause."""
1721 | +
1722 | +    def run_(self):
1723 | +        import run_fresh as rf
1724 | +        d = tempfile.mkdtemp(dir=self.tmp)
1725 | +        return rf, rf.Run(d)
1726 | +
1727 | +    def test_one_retry_then_success(self):
1728 | +        rf, run = self.run_()
1729 | +        calls = []
1730 | +
1731 | +        def stage():
1732 | +            calls.append(1)
1733 | +            if len(calls) == 1:
1734 | +                raise gpu0.GpuOOM("whisper:large-v3: transcribe: CUDA out of memory")
1735 | +            return "ok"
1736 | +        with mock.patch.object(gpu0, "release_all", return_value={"after": [18, 24564]}) as rel:
1737 | +            self.assertEqual(run.stage("pinned", stage), "ok")
1738 | +        self.assertEqual((len(calls), rel.call_count), (2, 1))
1739 | +        log = run.prov["gpu0_oom"]["pinned"]
1740 | +        self.assertEqual((len(log), log[0]["attempt"], log[0]["release"]), (1, 1, {"after": [18, 24564]}))
1741 | +
1742 | +    def test_a_second_out_of_memory_is_a_hold_naming_every_process(self):
1743 | +        rf, run = self.run_()
1744 | +        self.procs[:] = [(31337, "python3", 23000)]
1745 | +
1746 | +        def stage():
1747 | +            raise RuntimeError("CUDA failed with error out of memory")   # raw: recognised by the runner too
1748 | +        with mock.patch.object(gpu0, "release_all", return_value={}):
1749 | +            with self.assertRaises(rf.Hold) as cm:
1750 | +                run.stage("gates", stage)
1751 | +        msg = str(cm.exception)
1752 | +        self.assertTrue(msg.startswith("infrastructure: gates: CUDA out of memory twice"), msg)
1753 | +        self.assertIn("pid 31337 python3 23000 MiB", msg)
1754 | +        self.assertEqual(len(run.prov["gpu0_oom"]["gates"]), 2)
1755 | +
1756 | +    def test_other_stops_hold_with_the_real_cause_and_ordinary_errors_are_not_retried(self):
1757 | +        rf, run = self.run_()
1758 | +        with self.assertRaisesRegex(rf.Hold, r"^infrastructure: render: GPU0 Gpu0Foreign: .*pid 7"):
1759 | +            run.stage("render", lambda: (_ for _ in ()).throw(gpu0.Gpu0Foreign("held by pid 7 x 1 MiB")))
1760 | +        n = []
1761 | +        with self.assertRaisesRegex(rf.Hold, "ValueError: no"):
1762 | +            run.stage("cut", lambda: n.append(1) or (_ for _ in ()).throw(ValueError("no")))
1763 | +        self.assertEqual(n, [1])
1764 | +
1765 | +    def test_e_fail_052_the_pinned_out_of_memory_is_reported_as_one(self):
1766 | +        """Nov 12: Whisper's out-of-memory in the pinned stage read 'pinned decision rejected: R-iKNbc7-zk:
1767 | +        transcription failed'. Now it reaches the HOLD as the out-of-memory it is (after one retry)."""
1768 | +        rf, run = self.run_()
1769 | +        import pinned
1770 | +        import select_passages as sp
1771 | +
1772 | +        class OOMWhisper:                                # what gpu0.whisper's guard makes of a CTranslate2 OOM
1773 | +            def transcribe(self, *a, **k):
1774 | +                with gpu0.guard("whisper:large-v3: transcribe"):
1775 | +                    raise RuntimeError("CUDA failed with error out of memory")
1776 | +        src = os.path.join(self.tmp, "src.mp4")
1777 | +        open(src, "wb").write(b"x")
1778 | +        seg = {"role": "hook", "video_id": "R-iKNbc7-zk", "start": 18.16, "end": 26.4, "source": {"kind": "youtube"}}
1779 | +        with mock.patch.object(sp, "_download_window", return_value=(src, 0.0)), \
1780 | +                mock.patch.object(gpu0, "whisper", return_value=OOMWhisper()), \
1781 | +                mock.patch.object(gpu0, "release_all", return_value={}):
1782 | +            with self.assertRaises(rf.Hold) as cm:
1783 | +                run.stage("pinned", lambda: pinned.acquire({"segments": [seg]}, run.dir, log=lambda s: None))
1784 | +        msg = str(cm.exception)
1785 | +        self.assertTrue(msg.startswith("infrastructure: pinned: CUDA out of memory twice"), msg)
1786 | +        self.assertNotIn("transcription failed", msg)
1787 | +        self.assertNotIn("pinned decision rejected", msg)
1788 | +
1789 | +
1790 | +class TestPreflightLeavesGpu0AsFound(Box):
1791 | +    def test_a_model_left_resident_or_memory_left_used_fails(self):
1792 | +        import preflight
1793 | +        self.assertTrue(preflight.left_as_found(100, [], wait_s=0)[0])
1794 | +        self.ollama[:] = ["gemma3:27b"]
1795 | +        ok, why = preflight.left_as_found(100, [], wait_s=0)
1796 | +        self.assertFalse(ok)
1797 | +        self.assertIn("gemma3:27b", why)
1798 | +        self.ollama[:] = []
1799 | +        self.used[0] = 20659
1800 | +        ok, why = preflight.left_as_found(100, [], wait_s=0)
1801 | +        self.assertEqual((ok, "left GPU0 at 20659 MiB (found at 100 MiB)" in why), (False, True))
1802 | +
1803 | +
1804 | +if __name__ == "__main__":
1805 | +    unittest.main()
1806 | diff --git a/pipeline/test_gpu0_live.py b/pipeline/test_gpu0_live.py
1807 | new file mode 100644
1808 | index 00000000..c8ea282e
1809 | --- /dev/null
1810 | +++ b/pipeline/test_gpu0_live.py
1811 | @@ -0,0 +1,153 @@
1812 | +#!/usr/bin/env python3
1813 | +"""Law L-r item 5 on the real GPU0 (a GPU session: CUDA_VISIBLE_DEVICES=0; pipeline/conftest.py holds the GPU0 lease
1814 | +for the session). Before each stage a real allocation sits on GPU0, and the stage refuses or recovers as the law says:
1815 | +  - a FOREIGN allocation (a process that is not this run's) -> every stage kind HOLDs at once, naming its pid and MiB;
1816 | +  - this run's OWN resident model -> the next stage's swap deletes it and the stage passes;
1817 | +  - a real CUDA out-of-memory -> released, retried ONCE, both attempts in PROVENANCE; a second one HOLDs naming every
1818 | +    GPU0 process.
1819 | +TestBackToBack (PP_GPU0_LIVE=1, ~2 x 50 min, a committed clean tree): run_fresh env -> pinned -> ... -> render ->
1820 | +gates twice back to back on a frozen-reference pin, printing both runs' per-stage GPU0 peak tables."""
1821 | +import json
1822 | +import os
1823 | +import re
1824 | +import signal
1825 | +import subprocess
1826 | +import sys
1827 | +import tempfile
1828 | +import time
1829 | +import unittest
1830 | +
1831 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
1832 | +REPO = os.path.dirname(PIPELINE)
1833 | +sys.path.insert(0, PIPELINE)
1834 | +import gpu0  # noqa: E402
1835 | +
1836 | +GPU = os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
1837 | +SOURCE = os.path.join(REPO, "references", "pulse_preview_2026-11-11", "sources", "RXTVaDsN11M.mp4")
1838 | +
1839 | +
1840 | +def _wav(tmp, seconds=20):
1841 | +    wav = os.path.join(tmp, "a.wav")
1842 | +    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "30", "-t", str(seconds), "-i", SOURCE, "-vn", "-ac", "1",
1843 | +                    "-ar", "16000", wav], check=True, timeout=120)
1844 | +    return wav
1845 | +
1846 | +
1847 | +@unittest.skipUnless(GPU, "GPU0 session only (CUDA_VISIBLE_DEVICES=0)")
1848 | +class Live(unittest.TestCase):
1849 | +    def setUp(self):
1850 | +        self.assertTrue(gpu0.held(), "the session must hold the GPU0 lease (pipeline/conftest.py)")
1851 | +        gpu0.release_all()
1852 | +        self.tmp = tempfile.mkdtemp(prefix="gpu0live_")
1853 | +        self.wav = _wav(self.tmp)
1854 | +        import run_fresh as rf
1855 | +        self.rf = rf
1856 | +        self.run_ = rf.Run(self.tmp)
1857 | +        self.run_.sampler = gpu0.PeakSampler(interval_s=0.25).start()
1858 | +        self.addCleanup(self.run_.sampler.stop)
1859 | +        self.addCleanup(gpu0.release_all)
1860 | +
1861 | +    def transcribe(self, name):
1862 | +        segs, _ = gpu0.whisper(name).transcribe(self.wav, language="en", beam_size=5, word_timestamps=True,
1863 | +                                                vad_filter=False)
1864 | +        return sum(len(s.words or []) for s in segs)
1865 | +
1866 | +
1867 | +class TestForeignAllocationIsRefused(Live):
1868 | +    def test_every_stage_kind_holds_naming_the_foreign_process(self):
1869 | +        flag = os.path.join(self.tmp, "allocated")
1870 | +        code = ("import torch, time; x = torch.empty(int(2e9), dtype=torch.uint8, device='cuda:0'); "
1871 | +                f"open({flag!r}, 'w').write('ok'); time.sleep(900)")
1872 | +        # double fork: the allocator is NOT this process's descendant (a foreign job), and holds no lease descriptor
1873 | +        out = subprocess.run(["setsid", "bash", "-c", f"{sys.executable} -c \"{code}\" >/dev/null 2>&1 & echo $!"],
1874 | +                             capture_output=True, text=True, timeout=30, env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"})
1875 | +        pid = int(out.stdout.strip())
1876 | +        self.addCleanup(lambda: os.kill(pid, signal.SIGTERM) if os.path.exists(f"/proc/{pid}") else None)
1877 | +        for _ in range(120):
1878 | +            if os.path.exists(flag) and any(p == pid for p, n, m in gpu0.processes()):
1879 | +                break
1880 | +            time.sleep(0.5)
1881 | +        else:
1882 | +            self.fail("the foreign allocation never appeared on GPU0")
1883 | +        stages = {"pinned": lambda: self.transcribe("large-v3"),
1884 | +                  "review": lambda: gpu0.swap_to("ollama:gemma3:27b"),
1885 | +                  "render": lambda: gpu0.swap_to("nvenc"),
1886 | +                  "gates": lambda: self.transcribe("medium")}
1887 | +        for name, fn in stages.items():
1888 | +            with self.assertRaises(self.rf.Hold, msg=name) as cm:
1889 | +                self.run_.stage(name, fn)
1890 | +            msg = str(cm.exception)
1891 | +            self.assertTrue(msg.startswith(f"infrastructure: {name}: GPU0 Gpu0Foreign"), msg)
1892 | +            self.assertIn(f"pid {pid} ", msg)
1893 | +        self.assertFalse(gpu0.whisper("large-v3").loaded)              # nothing was loaded next to it
1894 | +
1895 | +
1896 | +class TestOwnResidentModelIsSwappedOut(Live):
1897 | +    def test_the_next_stage_deletes_it_and_passes(self):
1898 | +        import story_semantics as sm
1899 | +        E = sm.Embedder()
1900 | +        E.encode(["bitcoin " * 200] * 16)                              # resident on GPU0 before the stage
1901 | +        self.assertTrue(E.model.loaded)
1902 | +        n = self.run_.stage("pinned", lambda: self.transcribe("large-v3"))
1903 | +        self.assertGreater(n, 10)
1904 | +        self.assertFalse(E.model.loaded)                               # deleted by the swap
1905 | +        ev = [e for e in gpu0.events() if e["key"] == "whisper:large-v3"][-1]
1906 | +        self.assertIn("embedder", ev["unloaded"])
1907 | +        print(f"\n  peaks MiB: {self.run_.sampler.peaks}")
1908 | +
1909 | +
1910 | +class TestRealOutOfMemory(Live):
1911 | +    def test_retried_once_and_recovered_then_twice_is_a_hold_naming_every_process(self):
1912 | +        import torch
1913 | +        attempts = []
1914 | +
1915 | +        def stage():
1916 | +            attempts.append(1)
1917 | +            if len(attempts) == 1:                                     # a REAL CUDA out-of-memory on GPU0
1918 | +                with gpu0.guard("dummy allocation"):
1919 | +                    torch.empty(int(40e9), dtype=torch.uint8, device="cuda:0")
1920 | +            return self.transcribe("medium")
1921 | +        self.assertGreater(self.run_.stage("gates", stage), 10)
1922 | +        log = self.run_.prov["gpu0_oom"]["gates"]
1923 | +        self.assertEqual((len(attempts), len(log)), (2, 1))
1924 | +        self.assertIn("out of memory", log[0]["error"].lower())
1925 | +        self.assertIn("after", log[0]["release"])
1926 | +
1927 | +        def always():
1928 | +            with gpu0.guard("dummy allocation"):
1929 | +                torch.empty(int(40e9), dtype=torch.uint8, device="cuda:0")
1930 | +        with self.assertRaises(self.rf.Hold) as cm:
1931 | +            self.run_.stage("render", always)
1932 | +        msg = str(cm.exception)
1933 | +        self.assertTrue(msg.startswith("infrastructure: render: CUDA out of memory twice"), msg)
1934 | +        self.assertIn(f"pid {os.getpid()} ", msg)                     # every GPU0 process named (here: this one)
1935 | +        self.assertEqual(len(self.run_.prov["gpu0_oom"]["render"]), 2)
1936 | +
1937 | +
1938 | +PIN = os.path.join(REPO, "references", "pinned", "v2f_integration_proof.pin.json")
1939 | +
1940 | +
1941 | +@unittest.skipUnless(GPU and os.environ.get("PP_GPU0_LIVE") == "1", "PP_GPU0_LIVE=1: two full runs (~2 x 50 min)")
1942 | +class TestBackToBack(unittest.TestCase):
1943 | +    def test_two_runs_back_to_back_with_the_peak_table(self):
1944 | +        fd = gpu0._own[gpu0.lease_path()]["file"].fileno()        # the session's lease: run_fresh inherits custody
1945 | +        os.set_inheritable(fd, True)
1946 | +        tables = []
1947 | +        for i in (1, 2):
1948 | +            gpu0.release_all()
1949 | +            r = subprocess.run([sys.executable, os.path.join(PIPELINE, "run_fresh.py"), "--pinned", PIN],
1950 | +                               capture_output=True, text=True, timeout=4 * 3600, pass_fds=(fd,), cwd=PIPELINE)
1951 | +            run_dir = re.search(r"=== FRESH-TOPIC RUN (\S+) ===", r.stdout).group(1)
1952 | +            report = open(os.path.join(run_dir, "REPORT.md")).read()
1953 | +            table = report[report.index("## GPU0 peak memory per stage"):].split("\n\n")[0]
1954 | +            tables.append((run_dir, r.returncode, table))
1955 | +            status = json.load(open(os.path.join(run_dir, "status.json")))
1956 | +            for st in status["stages"]:
1957 | +                self.assertNotIn("out of memory", (st.get("reason") or "").lower(), (run_dir, st))
1958 | +                self.assertNotIn("Gpu0", st.get("reason") or "", (run_dir, st))
1959 | +        for run_dir, rc, table in tables:
1960 | +            print(f"\n{run_dir} (exit {rc})\n{table}")
1961 | +
1962 | +
1963 | +if __name__ == "__main__":
1964 | +    unittest.main()
1965 | diff --git a/pipeline/conftest.py b/pipeline/conftest.py
1966 | new file mode 100644
1967 | index 00000000..67cebb03
1968 | --- /dev/null
1969 | +++ b/pipeline/conftest.py
1970 | @@ -0,0 +1,34 @@
1971 | +"""pytest and GPU0 (law L-r ONE OWNER, pipeline/gpu0.py). Decided once, before collection:
1972 | +  CUDA_VISIBLE_DEVICES '' or '-1'  a CPU session: takes nothing; a GPU0 load in it is refused (gpu0.require)
1973 | +  unset or '0'                     a GPU session, GPU0 only: holds the GPU0 lease for the whole session, or stops at
1974 | +                                   once with exit 75 naming the holder (a run or another session has GPU0)
1975 | +  anything else ('0,1', '1', ...)  refused (exit 2): GPU1 is quarantined"""
1976 | +import os
1977 | +import sys
1978 | +
1979 | +import pytest
1980 | +
1981 | +sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # gpu0 lives next to this file
1982 | +
1983 | +_CVD = os.environ.get("CUDA_VISIBLE_DEVICES")
1984 | +_LEASE = []
1985 | +
1986 | +
1987 | +def pytest_configure(config):
1988 | +    if _CVD in ("", "-1"):
1989 | +        return
1990 | +    if _CVD not in (None, "0"):
1991 | +        pytest.exit(f"CUDA_VISIBLE_DEVICES={_CVD!r}: test sessions run on GPU0 only ('0', or '' for CPU)", returncode=2)
1992 | +    os.environ["CUDA_VISIBLE_DEVICES"] = "0"          # unset = every GPU visible: a GPU session is GPU0 only
1993 | +    import gpu0
1994 | +    cm = gpu0.lease(f"pytest session (pid {os.getpid()})")
1995 | +    try:
1996 | +        cm.__enter__()
1997 | +    except gpu0.LeaseBusy as e:
1998 | +        pytest.exit(f"GPU0 is busy, no GPU test session now: {e}", returncode=75)
1999 | +    _LEASE.append(cm)
2000 | +
2001 | +
2002 | +def pytest_unconfigure(config):
2003 | +    while _LEASE:
2004 | +        _LEASE.pop().__exit__(None, None, None)
2005 | diff --git a/pipeline/measure_gpu0.py b/pipeline/measure_gpu0.py
2006 | new file mode 100644
2007 | index 00000000..2b04ae18
2008 | --- /dev/null
2009 | +++ b/pipeline/measure_gpu0.py
2010 | @@ -0,0 +1,111 @@
2011 | +#!/usr/bin/env python3
2012 | +"""pipeline/measure_gpu0.py — measure the peak GPU0 memory each gpu0.REQUIREMENT_MIB key needs (law L-r item 2:
2013 | +'the incoming model's known requirement'). Holds the GPU0 lease for the whole measurement; runs one child process per
2014 | +key (it inherits the lease descriptor and loads through gpu0, as the pipeline does) on a representative workload while
2015 | +this process samples nvidia-smi every 0.1 s. Prints the peak above the idle baseline per key; changes nothing.
2016 | +Usage: CUDA_VISIBLE_DEVICES=0 [MEASURE_SECONDS=600] python3 pipeline/measure_gpu0.py [key ...]"""
2017 | +import json
2018 | +import os
2019 | +import subprocess
2020 | +import sys
2021 | +import tempfile
2022 | +import threading
2023 | +import time
2024 | +
2025 | +PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
2026 | +REPO = os.path.dirname(PIPELINE_DIR)
2027 | +sys.path.insert(0, PIPELINE_DIR)
2028 | +import gpu0  # noqa: E402
2029 | +
2030 | +SOURCE = os.environ.get("MEASURE_SOURCE") or os.path.join(REPO, "references", "pulse_preview_2026-11-11", "sources",
2031 | +                                                       "jbDqdLytkNM.mp4")     # 733 s of speech (protected, read-only)
2032 | +
2033 | +CHILD = r'''
2034 | +import os, sys, json, urllib.request
2035 | +sys.path.insert(0, sys.argv[1])
2036 | +import gpu0
2037 | +key, wav = sys.argv[2], sys.argv[3]
2038 | +if key.startswith("whisper:"):
2039 | +    parts = key.split(":")
2040 | +    m = gpu0.whisper(parts[1], batched=len(parts) > 2)
2041 | +    kw = {"language": "en", "word_timestamps": True}
2042 | +    kw.update({"batch_size": 16} if len(parts) > 2 else {"beam_size": 5, "vad_filter": False})
2043 | +    segs, _ = m.transcribe(wav, **kw)
2044 | +    n = sum(len(s.words or []) for s in segs)
2045 | +    print(json.dumps({"words": n}))
2046 | +elif key == "embedder":
2047 | +    import story_semantics as sm
2048 | +    gpu0.swap_to("embedder")
2049 | +    e = sm.Embedder()
2050 | +    v = e.encode([("bitcoin price support moving average " * 60)] * 64)
2051 | +    print(json.dumps({"vectors": len(v)}))
2052 | +elif key == "resemblyzer":
2053 | +    gpu0.swap_to("resemblyzer")
2054 | +    from resemblyzer import VoiceEncoder, preprocess_wav
2055 | +    enc = VoiceEncoder()
2056 | +    print(json.dumps({"dims": len(enc.embed_utterance(preprocess_wav(wav)))}))
2057 | +elif key == "nvenc":
2058 | +    gpu0.swap_to("nvenc")
2059 | +    import subprocess
2060 | +    for size in ("1920x1080", "1080x1920"):
2061 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30", "-t", "8",
2062 | +                        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18", "-f", "null", "-"],
2063 | +                       check=True, timeout=300)
2064 | +    print(json.dumps({"encoded": 2}))
2065 | +elif key.startswith("ollama:"):
2066 | +    import story_semantics as sm
2067 | +    gpu0.swap_to(key)
2068 | +    body = json.dumps({"model": key.split(":", 1)[1], "stream": False, "keep_alive": 0,
2069 | +                       "messages": [{"role": "user", "content": "Write 150 words about Bitcoin's 200-day average."}],
2070 | +                       "options": {"temperature": 0, "seed": 7, "num_ctx": sm.LLM_CTX, "num_predict": 200}}).encode()
2071 | +    r = json.loads(urllib.request.urlopen(urllib.request.Request(
2072 | +        f"http://{gpu0.OLLAMA_HOST}/api/chat", data=body, headers={"Content-Type": "application/json"}),
2073 | +        timeout=600).read())
2074 | +    print(json.dumps({"chars": len(r["message"]["content"])}))
2075 | +'''
2076 | +
2077 | +
2078 | +def main():
2079 | +    keys = sys.argv[1:] or list(gpu0.REQUIREMENT_MIB)
2080 | +    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
2081 | +        sys.exit("CUDA_VISIBLE_DEVICES must be 0")
2082 | +    with gpu0.lease("measure_gpu0 (L-r requirements)"), tempfile.TemporaryDirectory(prefix="gpu0m_") as tmp:
2083 | +        lease_fd = gpu0._own[gpu0.lease_path()]["file"].fileno()
2084 | +        os.set_inheritable(lease_fd, True)
2085 | +        wav = os.path.join(tmp, "a.wav")
2086 | +        secs = os.environ.get("MEASURE_SECONDS", "60")     # batched keys: >= 480 s fills a 16 x 30 s batch
2087 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "60", "-t", secs, "-i", SOURCE, "-vn", "-ac", "1",
2088 | +                        "-ar", "16000", wav], check=True, timeout=120)
2089 | +        rows = []
2090 | +        for key in keys:
2091 | +            gpu0.release_all()
2092 | +            base, total = gpu0.memory()
2093 | +            peak = [base]
2094 | +            stop = threading.Event()
2095 | +
2096 | +            def sample():
2097 | +                while not stop.wait(0.1):
2098 | +                    try:
2099 | +                        peak[0] = max(peak[0], gpu0.memory()[0])
2100 | +                    except gpu0.Gpu0Stop:
2101 | +                        pass
2102 | +            t = threading.Thread(target=sample, daemon=True)
2103 | +            t.start()
2104 | +            t0 = time.time()
2105 | +            r = subprocess.run([sys.executable, "-c", CHILD, PIPELINE_DIR, key, wav], capture_output=True, text=True,
2106 | +                               timeout=1800, pass_fds=(lease_fd,))
2107 | +            stop.set()
2108 | +            t.join()
2109 | +            rows.append({"key": key, "baseline_mib": base, "peak_mib": peak[0], "need_mib": peak[0] - base,
2110 | +                         "seconds": round(time.time() - t0, 1), "rc": r.returncode,
2111 | +                         "out": (r.stdout.strip().splitlines() or [""])[-1][:120],
2112 | +                         "err": "" if r.returncode == 0 else r.stderr.strip()[-300:]})
2113 | +            print(json.dumps(rows[-1]), flush=True)
2114 | +        gpu0.release_all()
2115 | +        print("\n| key | baseline MiB | peak MiB | need MiB | s | rc |\n|---|---|---|---|---|---|")
2116 | +        for x in rows:
2117 | +            print(f"| {x['key']} | {x['baseline_mib']} | {x['peak_mib']} | {x['need_mib']} | {x['seconds']} | {x['rc']} |")
2118 | +
2119 | +
2120 | +if __name__ == "__main__":
2121 | +    main()
2122 | 
```

---

## YOUR REVIEW TASK: PULSE CHECK SENTENCE LAW / ONSET / CREDITS (Python pipeline, no UI, no DB)

The only file is the exact staged diff of ONE commit. Review that diff, nothing else.
Only state what you can verify from the diff shown. If uncertain, say so. Do not guess. Cite diff lines.

### Q1: CORRECTNESS
Does each changed function do what its docstring and the laws above say? Off-by-one in time/index
handling, wrong units (seconds vs ms), wrong comparisons, silent exceptions, state that leaks between
clips. Can any path produce a PASS (or a cut, a lock, a window) when data is missing or a model failed?

### Q2: LAW COMPLIANCE
For each law above: COMPLIANT / VIOLATION / PARTIAL with the diff line. In particular: can a cut move
outside the locked sentence's silence, can expected words be recomputed after selection, can a gate
threshold have been loosened, can the v2f reference path behave differently?

### Q3: TESTS
Do the tests prove the claim (must-fail fixtures FAIL for the right reason; controls PASS for the right
reason)? Any assertion that could pass vacuously?

### Q4: VERDICT
List every defect as: SEVERITY | diff line | issue | fix. End with READY or NOT READY.

