ORCHESTRATOR AMENDMENT D4 (PBX decision, 01:34 ET) — apply in STEP 2 before any commit. Also append this text verbatim to docs/audits/TRACK_A_FRESH_RUN.md under "PBX DECISIONS".

Evidence: live run runs/fresh_20261107_080503 (after 421f303c) held with 0 legal windows of 24 attempted; 22 failed "too short after expansion", 2 "start not a sentence boundary"; of ~40 adjacent sentences checked, 1 passed. The adjacency checker labels the host's follow-on sentence TOPIC_ONLY/UNRELATED because it reacts to the event instead of restating it. Hosts state the event in one 3-6 s sentence then react. Therefore D3's repair-by-expansion cannot produce windows under the current on-event definition. Record this pattern in docs/QWEN_CONTEXT_BIBLE.md now (title: "adjacent reaction/consequence sentence rejected as TOPIC_ONLY; 0/24 windows on fresh_20261107_080503").

D4 — SCOPED OPTION B (repairs the definition of "on-event"; lowers no gate):
- The hook/quote sentence remains the required anchor and must still pass full verification unchanged.
- An adjacent sentence may be admitted into the window ONLY if (a) it contains an explicit backward reference to the verified event (deictic/pronoun/definite reference: "this", "that", "it", "the hack", "the breach", "what just happened") OR shares a named entity or number from the anchor (e.g. Binance, $6.3B, North Korea); AND (b) it starts within 8 s of the anchor boundary it extends; AND (c) an independent verifier call returns SAME_EVENT_REACTION_OR_CONSEQUENCE for it. The verifier question is exactly "is this sentence a reaction to or consequence of the same verified event?" — NOT "does it restate the event" and NOT "is it related/on topic".
- Hard reject if the sentence introduces a new primary subject or a different news item (verifier returns NEW_SUBJECT or OTHER_EVENT).
- Cap: at most two admitted adjacent sentences per direction.
- Off-topic rejections remain rejections. The 3.0 quality floor is untouched. No other threshold moves (Law 20).
- Tests: add (1) a positive fixture from fresh_20261107_080503 — a Binance anchor + the host's actual reaction sentence — that must now assemble a legal 8-25 s window; (2) a negative fixture where the neighbour switches to market commentary with no backward reference or shared entity and must still fail; (3) a negative where the neighbour is a different news item and must fail as NEW_SUBJECT. The verifier prompt text is checked by a test so it cannot drift into a general similarity gate.
- D1 and D2 unchanged. D3 stays but now operates on windows D4 can actually extend.

Audit target for cross_llm_audit: implementation matches this wording exactly; no threshold moved; verifier prompt matches; the three fixtures exist and behave as stated.

---

D4a (PBX, 2026-11-09 01:59 ET): "Content-free interjections and fillers are transparent to rule (a): skipped for the deictic/entity/number check, not counted toward the two-sentence cap, and they do not close the direction. The 8 s bound and the independent SAME_EVENT reaction/consequence verifier still apply to whatever window results. No threshold lowered."

Implementation (02:15 ET, session pp_vert resumed):
- editorial_select.py expanded_window(): interjection-only sentences (set(lc_words) <= INTERJECTIONS) are included in the window without calling on_event(), without incrementing admitted[d], and without closing the direction. The 8 s gate still applies.
- editorial_select.py repair_window(): same transparency rule.
- Tests added to test_window_review.py TestD4aInterjectionTransparency:
  (1) test_positive_080503_btc_sessions_interjection_then_reaction_assembles_hook — the real BTC Sessions 9La50F_lmd0 fixture; "Oh." is transparent, "That's like a pittance..." provides the reaction, legal 8-12 s hook.
  (2) test_interjection_does_not_count_toward_cap_and_does_not_close_direction — cap=2 with an interjection in the stream; both real reactions admitted, interjection not sent to checker.
  (3) test_interjection_alone_does_not_make_a_window_legal — an interjection next to a short anchor does not extend it enough on its own.
