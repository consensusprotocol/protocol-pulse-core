### The order (orchestrator 08:15 ET Nov 14, to pp-ingest, ruling 2, verbatim)
"(2) THE HOOK PASS: BOTH. (B) up to 5 candidates a window in conversation episodes, and (C) the 12-35 s spotlight
question for them ('one speaker's complete claim, number or question that a stranger understands cold and would stop
scrolling for'). Last night's pools had exactly one opener rated 4 in each window; this is where the supply is. Audit
as one change; run it over the current window and every new upload. Report rows per video and cost."

### Background
- Ruling 80: the HOOK PASS, a second mining question over the same windows (mine.HOOK_PROMPT, role `hook`), 1-3
  openers of 4-14 s a window, rows = moments with role_hint "hook". Ruling 92 (mine-hook/2): the builder's OPENER rule
  stated and applied in code (bad_opener), the episode's caption turn measure (episode_measure: '>>' markers per
  minute) on every row; its options (b) more hook candidates and (c) a spotlight question were left to the
  orchestrator, who has now ruled BOTH.
- Ruling 90 (the builder's spotlight): ONE moment, one speaker, one channel, 12 to 35 s of clip, played alone; it must
  rate >= 4 on the hook's own job (scroll / alone) AND >= 4 as a clip standing alone; ruling 92: from a conversation
  (caption turns >= 1.0 a minute, the builder's spotlight.CONVERSATION_TPM) or a first-hand statement, never a solo
  recap or reaction.
- The builder (pp-selectid) reads every row through this adapter (ledger.best_unused_moments) and re-judges it with
  its own gates; it does not read role_hint; its spotlight pool takes rows up to 35 s and snaps shorter ones outward.

### The change (ef431ff5; diff against 197b35ec below)
- mine.py: CONVERSATION_TPM 1.0 and is_conversation(episode) (unmarked / unmeasured / non-numeric -> False);
  HOOK_MAX_CONVERSATION 5: mine_video measures the episode FIRST and asks the hook question with max_n 5 in a
  conversation (prompt "1 to 5", the validator holds the reply to 5), else 3 (prompt byte-identical to mine-hook/2's:
  verified by sha256, so solo re-runs replay from the reply cache); SPOT_PROMPT (mine-spot/1): the orchestrator's
  words, 12-35 s, 1-8 sentences, one speaker, the judge's hook question verbatim (only scroll / alone count: nothing
  follows), the whole-clip stand-alone test, the hook NOT list plus 'a host reading news aloud, or a speaker reacting to
  a clip played inside the video'; at most 2 a window; KINDS["spotlight"] (role spotlight, key "spotlights",
  role_hint "spotlight", eligibility role "clip", seconds 12-35: rows outside, or opening on a pronoun / conjunction /
  reply word, are not written); mine_window takes max_n and picks the prompt by kind.
- service.py hook_video: the hook question, then (conversation only) the spotlight question over the same windows; the
  failures of both decide a retry; cost over both roles; spot_rows (NULL when not a conversation); the event and the log
  line say both; check_roles(): a provider config without a role for every mining question stops the start.
- providers.json: role `spotlight` (the hook role's chain: heimdall_qwen27b, local_gemma). queue.py: column
  spot_rows. stats.py: hooks_12h.conversations and spotlight_rows. ledger.carry_forward: any role_hint travels to a
  later line of the same moment, a later line's own hint winning (was: only "hook").

### The readings (to be STATE assumptions A36-A39)
- A36 "conversation episodes" = ruling 92's caption measure: >= 1.0 speaker changes a minute (the builder's own
  threshold for spotlights). Captions without any '>>' (professional captions, often news networks) are unknown, never
  a conversation here; the builder's ruling 92 also admits first-hand statements, which this pass does not try to
  detect (the orchestrator may widen it).
- A37 (B) changes only how many openers the hook question may return in a conversation (5, was 3); nothing else.
- A38 (C): at most 2 spotlights a window; 1-8 whole sentences, 12-35 s; the OPENER rule; its own role `spotlight` for
  clean cost accounting (same chain as `hook`; Heimdall-only under the freeze; never on ruling 98's paid route);
  role_hint "spotlight"; eligibility judged as "clip" (informational: the adapter leaves eligibility to the packager).
- A39 "run it over the current window and every new upload": once live, `tools/ingest_watch.py hooks --rerun`
  re-queues every mined video of the 12 h window whose pass is older; every new upload gets mine-hook/3.

### Questions for the reviewers
1. Can a non-conversation episode ever get the 5-hook question or the spotlight question? Can a conversation miss it?
2. The validator, the schema, the prompt and max_n: always the same number for one call? Anything that lets a reply of
   6 hooks or 3 spotlights through?
3. The spotlight rows: can one be written outside 12-35 s, with a bad opener, without the integrity fields every
   moment carries (risk flags, eligibility, expiry, miner_route, the episode)? Does anything downstream (the adapter,
   the second-model check, the purge, stats, carry_forward) treat a "spotlight" row wrongly?
4. hook_video: retries, failures of either question, cost, the queue columns, the log line, crash paths; the rerun.
5. The prompt: does SPOT_PROMPT ask for what ruling 90 / 92 and the order describe? Anything that would make the model
   return weak or unsafe spans (e.g. a price prediction, an accusation, a reaction)?
6. Tests: do they prove (B) and (C)? Missing must-fail cases?

### The new tests (tests/ingest/test_mine.py)
```python
def test_the_spotlight_prompt_states_the_ruling_and_the_judges_hook_question_verbatim():
    """The 08:15 ruling 2 (c): the spotlight question in the orchestrator's words, ruling 90's 12-35 s, one speaker,
    the builder's judge question verbatim (its scroll and alone parts count) and the OPENER rule's own words."""
    win = [{"k": 3, "start": 0.0, "text": "Bitcoin is a bet against every central bank."},
           {"k": 4, "start": 4.0, "text": "Here is why."}]
    p = mine.spot_prompt({"exact_title": "t"}, {"display_name": "c"}, win)
    flat = " ".join(p.split())
    for s in ("one speaker's complete claim, number or question that a stranger understands cold and would stop "
              "scrolling for", "12 to 35 seconds", "One speaker throughout", "it NAMES who or what",
              "only \"scroll\" and \"alone\" count", "must stand alone", "a price prediction", "an accusation",
              "an ad read", '"this week"', "reacting to a clip", "1 to 2 passages", "1 to 8 consecutive"):
        assert s in flat, s
    assert mine.JUDGE_HOOK_QUESTION in p and mine._AXES_TEXT in p
    assert mine._FLAGS_TEXT.format(reason_max=mine.REASON_MAX) in p
    for w in mine.OPENER_PRONOUNS | mine.OPENER_CONJUNCTIONS | mine.OPENER_REPLY_FRAGMENTS:
        assert w in p
    assert '{"spotlights": [' in p and "S3" in p and p != mine.hook_prompt({"exact_title": "t"}, {"display_name": "c"},
                                                                             win)


@pytest.mark.parametrize("reply,why", [
    ('{"hooks": []}', "exactly the key 'spotlights'"),
    ('{"spotlights": [M, M, M]}', "3 spotlights > 2"),
    ('{"spotlights": [C9]}', "count 9 is not 1-8"),
])
def test_the_spotlight_reply_is_strict(reply, why):
    m = json.dumps(H.moment(0, 1))
    reply = reply.replace("M", m).replace("C9", json.dumps(H.moment(0, 8)))
    k = mine.KINDS["spotlight"]
    with pytest.raises(providers.Invalid, match=why):
        mine.validator(range(20), k["key"], k["max_n"], k["max_count"])(reply)


def test_the_spotlight_question_writes_rows_of_12_to_35_seconds_judged_as_clips():
    """(c): rows with role_hint "spotlight", the spotlight's own version and pass, 12-35 s; a span outside it or one
    opening on a pronoun is not written (4 s sentences: 4 sentences = 16 s kept; 2 = 8 s dropped; 6-7 opens 'I')."""
    rec, meta = H.caption_record(H.vid(), n_rep=3)
    r = H.make_router([H.FakeBackend("primary", fn=lambda p: H.spots_reply(p, ((0, 3), (5, 8))))])
    with ThreadPoolExecutor(4) as ex:
        lines, rep = mine.mine_video(r, ex, rec, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c1",
                                     use_cache=False, kind="spotlight")
    assert len(lines) == 1 and rep["kind"] == "spotlight" and rep["max_n"] == mine.SPOT_MAX and not rep["failed"]
    for l in lines:
        assert l["role_hint"] == "spotlight" and l["eligibility"]["role"] == "clip" and l["mined"]["pass"] == "spotlight"
        assert l["mined"]["prompt_version"] == mine.SPOT_PROMPT_VERSION and l["miner_route"] == "spotlight"
        assert 12.0 <= l["duration_estimate_s"] <= 35.0 and mine.bad_opener(l["text"]) is None
        assert not ledger.line_problems(l)
    assert rep["dropped"] == {"opens on a pronoun (the builder's OPENER rule)": 1}
    r = H.make_router([H.FakeBackend("primary", fn=lambda p: H.spots_reply(p, ((0, 1),)))])
    with ThreadPoolExecutor(4) as ex:
        none, rep = mine.mine_video(r, ex, rec, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c1",
                                    use_cache=False, kind="spotlight")
    assert none == [] and rep["dropped"] == {"outside 12-35 s": 1} and rep["dropped_s"] == [8.0]
    r = H.make_router([H.FakeBackend("primary", fn=lambda p: H.spots_reply(p, ((0, 3), (4, 7), (8, 11))))])
    with ThreadPoolExecutor(4) as ex:
        none, rep = mine.mine_video(r, ex, rec, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c1",
                                    use_cache=False, kind="spotlight")
    assert none == [] and "3 spotlights > 2" in json.dumps(rep["failed"])     # never more than SPOT_MAX a window


def test_a_conversation_is_asked_for_up_to_5_hooks_a_window_and_a_solo_episode_for_3():
    """(b): the same hook question, 5 in a conversation (>= 1 caption speaker change a minute), 3 elsewhere: the prompt
    says it and the validator holds the reply to it; a solo episode's prompt is the one asked before (cached replies
    still answer it)."""
    asked = []

    def fn(p):
        asked.append(p)
        return H.hooks_reply(p, ((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)))
    solo, meta = H.caption_record(H.vid(), n_rep=3)
    conv = H.conversation(H.caption_record(H.vid(), n_rep=3)[0], every=4)
    assert mine.is_conversation(mine.episode_measure(conv)) and not mine.is_conversation(mine.episode_measure(solo))
    r = H.make_router([H.FakeBackend("primary", fn=fn)])
    with ThreadPoolExecutor(4) as ex:
        lines, rep = mine.mine_video(r, ex, conv, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c1",
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


@pytest.mark.parametrize("ep,conv", [
    ({"turns_per_min": 1.0}, True), ({"turns_per_min": 2.5}, True), ({"turns_per_min": 0.99}, False),
    ({"turns_per_min": None, "unmarked": True}, False), ({}, False), (None, False), ({"turns_per_min": True}, False),
    ({"turns_per_min": "2"}, False),
])
def test_a_conversation_is_measured_never_assumed(ep, conv):
    assert mine.is_conversation(ep) is conv


```

### The new tests (tests/ingest/test_service.py; svc / run_once are the file's fixtures; helpers.is_spot / spots_reply / conversation are new)
```python
def _every_question(prompt):
    """The miner answering every question: the moment pass its first two ids; the hook question as many hooks as it
    allows (5 in a conversation, else 3); the spotlight question two 4-sentence spans (16 s at 4 s a sentence)."""
    flat = " ".join(prompt.split())
    if H.is_spot(prompt):
        return H.spots_reply(prompt, ((0, 3), (10, 13)))
    if H.is_hook(prompt):
        n = 5 if "1 to 5 lines" in flat else 3
        return H.hooks_reply(prompt, tuple((i, i) for i in range(n)))
    return H.first_two(prompt)


def test_the_hook_pass_of_a_conversation_asks_5_hooks_and_the_spotlight_question_a_solo_one_neither(svc,
                                                                                                    monkeypatch):
    """The orchestrator's 08:15 ruling 2 (ruling 92 (b) + (c)): a conversation (caption turns >= 1 a minute) is asked
    for up to 5 hooks a window and the spotlight question (its rows: role_hint "spotlight", 12-35 s); a solo episode
    keeps 3 hooks and is never asked the spotlight question. The pass's version, its spotlight rows and its cost (both
    roles) are recorded; live.json counts them."""
    s, vids, b = svc(_every_question, _every_question, n_videos=2)
    conv = vids[0]
    ts = config.ts()
    solo_captions = ts.fetch_captions

    def captions(meta, work):
        if meta["video_id"] != conv:
            return solo_captions(meta, work)
        lead = [(">> " if i % 4 == 3 else "") + f"Bitcoin show {conv} opens with {i} new facts." for i in range(30)]
        rec, _ = H.caption_record(conv, n_rep=8, lead=lead)
        return "ok", ts._make_record(meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)", rec["segments"])
    monkeypatch.setattr(ts, "fetch_captions", captions)
    run_once(s)
    while s.hook_once(wait=True):
        pass
    rows = [l for l in ledger.read(s.p["ledger"])[0]]
    c, o = s.q.video(conv), s.q.video(vids[1])
    assert c["episode_tpm"] >= mine.CONVERSATION_TPM > (o["episode_tpm"] or 0)
    assert c["hook_version"] == o["hook_version"] == mine.HOOK_PROMPT_VERSION == "mine-hook/3"
    spots = [l for l in rows if l.get("role_hint") == "spotlight"]
    assert spots and {l["video_id"] for l in spots} == {conv} and c["spot_rows"] == len(spots) and o["spot_rows"] is None
    assert all(12.0 <= l["duration_estimate_s"] <= 35.0 and l["mined"]["pass"] == "spotlight" for l in spots)
    per_window = {}
    for l in rows:
        if l.get("role_hint") == "hook" and l["mined"]["pass"] == "hook":
            per_window.setdefault((l["video_id"], tuple(l["mined"]["window"])), set()).add(tuple(l["sentences"]))
    assert max(len(v) for (vid, _), v in per_window.items() if vid == conv) == 5
    assert max(len(v) for (vid, _), v in per_window.items() if vid != conv) == 3
    calls = s.q.rows("SELECT video_id, role, COUNT(*) AS n, SUM(cost_usd) AS usd FROM calls WHERE role IN ('hook', "
                     "'spotlight') GROUP BY video_id, role")
    assert {(r["video_id"], r["role"]) for r in calls} == {(conv, "hook"), (conv, "spotlight"), (vids[1], "hook")}
    assert c["hook_cost_usd"] == pytest.approx(sum(r["usd"] for r in calls if r["video_id"] == conv))
    hk = s.health_once()["hooks_12h"]
    assert hk["conversations"] == 1 and hk["spotlight_rows"] == len(spots)


def test_every_mining_question_needs_its_role_to_start():
    """The 08:15 ruling 2: the spotlight question has its own role; a provider config without it stops the start
    (asked without it, every conversation's hook pass would crash)."""
    service.check_roles(providers.load_config())                        # the real providers.json: every role there
    cfg = H.router_cfg(["primary", "fallback"])
    service.check_roles(cfg)
    del cfg["roles"]["spotlight"]
    with pytest.raises(ValueError, match=r"no role \['spotlight'\]"):
        service.check_roles(cfg)


```
