### The order (orchestrator 09:02 ET Nov 14, to pp-ingest, verbatim)
"ORCHESTRATOR RULING 09:02 to PP-INGEST, A36: WIDEN. The hook pass (B) + (C) runs on every episode with >= 0.3
caption turns a minute AND on every episode with NO speaker markers at all (auto captions carry none, e.g. Stephan
Livera's interviews; at $0.006 a video the cost of asking is nothing and the cost of missing an interview is the whole
point). Only an episode that IS marked and sits under 0.3 is skipped. Your numbers show the 1.0 line was drawn from one
solo recap (0.48) and cuts off Bitcoin Magazine's and CoinDesk's interviews and Pompliano at 0.97. I am giving the
builder the matching ruling for its source test."

### Background
The hook pass mine-hook/3 (af298eb9, audited 2 cycles as pp-ingest_audit/hk3/, live 08:53 ET) asks, in a
"conversation", (b) up to 5 hooks a window and (c) the spotlight question. mine.is_conversation(episode) decided it:
turns_per_min >= 1.0 (ruling 92's caption measure); unmarked or unmeasured: never. The episode dict comes from
mine.episode_measure(rec): {speaker_markers: int count of '>>' / '&gt;&gt;' in the record's segments, minutes,
turns_per_min: markers / minutes (None when minutes is 0), unmarked: markers == 0, measured_from}. Measured on the 67
videos mined with moments in 72 h: >= 1.0: 26; 0.3-1.0: 19; (0, 0.3): 9; no markers: 13 (6 professional captions, 7
auto captions).

### The change (c1141fff; diff against af298eb9 below)
- mine.CONVERSATION_TPM 1.0 -> 0.3; mine.is_conversation(episode): True unless the episode has speaker_markers > 0
  (an int, not a bool) AND a numeric (not bool) turns_per_min < 0.3. So: no markers -> asked; marked with an
  unmeasurable rate -> asked; None / {} -> asked. HOOK_PROMPT_VERSION mine-hook/4 (the pass's question set changed for
  the episodes now asked; `hooks --rerun` re-queues the 12 h window; unchanged prompts replay free from the cache).
- service.py: the log text for a skipped episode says "a marked solo episode: N markers, T turns / min".
- stats.py: hooks_12h counts spotlight_asked_videos = videos whose pass recorded spot_rows (was: a threshold count
  "conversations").
- tests: the predicate's cases (marked under / over 0.3, unmarked, unmeasurable, malformed); the 5-vs-3 test with a
  marked solo record (1 marker in 4.7 min) and an unmarked record (now 5); the service test's solo video is a marked
  solo episode; test fakes answer the spotlight question (unmarked test captions are now asked).

### The readings (to be STATE assumptions)
- A40 "every episode with NO speaker markers at all": speaker_markers == 0 (or not an int count), including a record
  with no segments (it has no windows, so nothing is asked anyway).
- A41 a marked episode whose rate cannot be measured (minutes 0, so turns_per_min None) is asked: the ruling skips
  only an episode that "IS marked and sits under 0.3", and an unmeasured rate is not shown to sit under it.
- A42 ruling 98's paid route keeps its own ordering threshold (providers.json paid_route.conversation_tpm 1.0: which
  new uploads it mines first during an outage); the 09:02 ruling is about the hook pass. One config value if the
  orchestrator wants them aligned.

### Questions for the reviewers
1. Does is_conversation now implement exactly "skip only a marked episode under 0.3"? Any input that is skipped but
   should be asked, or asked but should be skipped?
2. Anything else that read the old threshold or the old meaning (stats, the paid route, the builder's contract, the
   log, the tests)?
3. The version bump and the re-run: correct and free where the prompts did not change?

### The tests (tests/ingest/test_mine.py)
```python
def test_a_conversation_is_asked_for_up_to_5_hooks_a_window_and_a_solo_episode_for_3():
    """(b): the same hook question, 5 in a conversation and (the 09:02 ruling A36) in an episode with no speaker
    markers at all; 3 only in a MARKED episode under 0.3 turns a minute: the prompt says it and the validator holds the
    reply to it; a solo episode's prompt is the one asked before (cached replies still answer it)."""
    asked = []

    def fn(p):
        asked.append(p)
        return H.hooks_reply(p, ((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)))
    solo, meta = H.caption_record(H.vid(), n_rep=10)                    # 70 segments of 4 s, 4.7 min
    solo = H.marked_solo(solo)                                          # 1 marker: 0.21 turns a minute
    conv = H.conversation(H.caption_record(H.vid(), n_rep=3)[0], every=4)
    unmarked = H.caption_record(H.vid(), n_rep=3)[0]
    assert mine.episode_measure(solo)["turns_per_min"] < mine.CONVERSATION_TPM
    assert mine.is_conversation(mine.episode_measure(conv)) and not mine.is_conversation(mine.episode_measure(solo))
    assert mine.episode_measure(unmarked)["unmarked"] and mine.is_conversation(mine.episode_measure(unmarked))
    r = H.make_router([H.FakeBackend("primary", fn=fn)])
    for rec in (conv, unmarked):
        with ThreadPoolExecutor(4) as ex:
            lines, rep = mine.mine_video(r, ex, rec, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c1",
                                         use_cache=False, kind="hook")
        assert rep["max_n"] == 5 and not rep["failed"] and asked and all("1 to\n5 lines" in p or "1 to 5" in
                                                                         p.replace("\n", " ") for p in asked)
        asked.clear()
    with ThreadPoolExecutor(4) as ex:
        _, rep = mine.mine_video(r, ex, solo, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c1",
                                 use_cache=False, kind="hook")
    assert rep["max_n"] == 3 and rep["failed"]                          # 5 hooks to a solo question: rejected
    assert all("1 to 3" in p.replace("\n", " ") for p in asked)
    win = mine.windows(contract.sentences(solo)[2])[0]
    assert mine.hook_prompt(meta, H.CHAN, win) == mine.HOOK_PROMPT.format(
        max_s=3, reason_max=mine.REASON_MAX, max_h=3, channel=H.CHAN["display_name"], title=meta["exact_title"],
        rows="\n".join(f"[S{s['k']} {mine._mmss(s['start'])}] {mine._untrusted(s['text'])}" for s in win),
        lo=win[0]["k"], hi=win[-1]["k"])


@pytest.mark.parametrize("ep,asked", [
    ({"speaker_markers": 5, "turns_per_min": 0.3}, True), ({"speaker_markers": 5, "turns_per_min": 2.5}, True),
    ({"speaker_markers": 5, "turns_per_min": 0.97}, True),                  # Pompliano: was cut off by the 1.0 line
    ({"speaker_markers": 5, "turns_per_min": 0.29}, False),                 # a marked solo recap: the only skip
    ({"speaker_markers": 1, "turns_per_min": 0.0}, False),
    ({"speaker_markers": 0, "turns_per_min": 0.0, "unmarked": True}, True),  # no markers (Stephan Livera): asked
    ({"speaker_markers": 0, "turns_per_min": None, "unmarked": True}, True),
    ({"speaker_markers": 5, "turns_per_min": None}, True),                  # marked, rate unmeasurable: not shown solo
    ({"speaker_markers": 5, "turns_per_min": True}, True), ({"speaker_markers": 5, "turns_per_min": "0.1"}, True),
    ({"speaker_markers": True, "turns_per_min": 0.1}, True), ({}, True), (None, True),
])
def test_the_hook_pass_skips_b_and_c_only_for_a_marked_episode_under_0_3_turns_a_minute(ep, asked):
    """The orchestrator's 09:02 ruling (A36: WIDEN): (b) + (c) on every episode with >= 0.3 caption turns a minute AND
    every episode with no speaker markers; only an episode that IS marked and sits under 0.3 is skipped."""
    assert mine.CONVERSATION_TPM == 0.3
    assert mine.is_conversation(ep) is asked


```
