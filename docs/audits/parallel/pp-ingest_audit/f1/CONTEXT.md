### The finding (pp-ingest, fresh session, 07:31 ET Nov 14; STATE LIVE STATE "FINDING F1")
RULING 40 P1 (orchestrator 03:13 + 19:22 ET Nov 13): the miner's `imperative` and `single_source_breaking` labels stand
as hard flags (law L-u) only when a SECOND model agrees; the adapter releases such a flag only on the second model's
"no". The watcher lets a back-end answer that question only if it passed a CALIBRATION: the 16 quotes of those two
flags with a clear answer (flagcheck.PROBES, fictional names), every one answered right. service.py says the checker
is "re-calibrated on the known quotes once a day (and at every start)".
F1: flagcheck.calibrate() called router.run() with the default use_cache=True, and the watcher's router has a reply
cache. So every start and every daily calibration replayed stored answers. Measured: at the 06:46 ET start the
calibration read glm 16/16, muse 16/16, and the queue's calls since the start were 32 rows of kind 'cache' only; the
cached answers were written 20:10-20:12 ET Nov 13 (glm) and 20:11-23:05 ET Nov 13 (muse). The router's own comment
(providers.py run): a stored reply "calls nobody, proves nothing about health". A model changed behind the same
gateway name (the gateway routes one model name to several providers) would keep releasing hard flags on a stale
calibration. Law L-m: nothing measured is never a pass.

### The change (0abeb304, diff against 159c6709 below)
- flagcheck.calibrate(..., fresh=False, rounds=1): fresh puts every quote to the model now (router.run use_cache=False;
  a successful live reply still refreshes the cache file); a quote a back-end did not answer (AllBackendsFailed after
  the router's own attempts / transport retries) is asked of it again, only that quote, up to `rounds` rounds.
  Defaults keep the measurement CLI exactly as it was (stored replies: a report is reproduced from them; it releases
  nothing). watcher_checkers() calibrates with fresh=True, rounds=CALIBRATION_ROUNDS (3).
- service.check_once: after a calibration, the next one comes after CHECK_RECALIBRATE_S (a day) when a back-end passed
  or when no back-end could pass (every one answered some quote wrong: at temperature 0 the same again); when none
  passed and one still could (a quote unanswered, none answered wrong: an outage at calibration time) it comes after
  CHECK_RETRY_S (600 s), the wait doubling while it keeps failing (600, 1200, 2400 ... capped at a day; after the cap
  it starts again at 600). The stored calibration (queue kv 'check_calibration', shown in live.json) gains asked_at
  per back-end; the log line says "asked live" with right / answered / unanswered and the next wait.
- Bundled (the handoff's open item 7, cosmetic): the start-up WARNING no longer says "never a paid frontier fallback"
  without qualification; it names ruling 98's capped paid route as a separate role.
- Design: docs/audits/INGEST_DESIGN.md section 16 (in the package above).

### The readings (to be STATE assumptions A33-A35)
- A33 "calibrated" (ruling 40 P1) means measured on the model as it answers now: a replayed reply is not a measurement.
  Cost: 16 short questions per back-end per calibration (2 back-ends), at start and daily: about $0.003 a day.
- A34 an outage must not bar the checkers for a day (yield), and a checker that keeps failing must not be asked every
  10 minutes forever (spend): 3 rounds inside a calibration for unanswered quotes; a calibration with none passing and
  one that could is retried after 600 s, doubling; a back-end that answered a quote wrong waits for the daily one.
  When one back-end passed and the other was left unanswered, the other waits for the daily calibration (the passing
  one answers; a real question it cannot answer is asked again after 600 s, the flag standing meanwhile).
- A35 the measurement CLI (tools/ingest_watch.py flagcheck, flagcheck.main / remeasure) keeps its stored replies.

### Questions for the reviewers
1. Can any path now let a back-end answer (and so release a flag) without a live, fully answered, all-right
   calibration? Can an unanswered quote count as right anywhere?
2. The rounds loop in calibrate(): are the results aggregated correctly per back-end and quote (order, duplicates,
   a back-end with no effective entry)? Is a re-asked quote's answer the only one counted?
3. The schedule in check_once: is the doubling bounded and correct on every path (first calibration, consecutive
   failures, a pass after failures, the cap)? Can the check loop calibrate in a tight loop?
4. Interplay: the router's breaker (5 consecutive failures, open 300 s), transport retries, the shared Heimdall-down
   signal (live calibration calls are now real calls and are noted; cached ones never were), the spend meter, the
   reply cache being overwritten by a live answer. Anything wrong or surprising?
5. Tests: do the four new tests prove the behaviour, and would they fail on the old code (the core one does: 16 calls
   instead of 32)? Missing must-fail cases?

### The new tests (tests/ingest/test_flagcheck.py)
```python
def _gold():
    """{calibration prompt: (gold answer, quote)} and a checker function that answers every quote right."""
    gold = {FC.prompt({"channel_name": "Calibration", "title": "Bitcoin news", "published_at": "2026-11-12",
                       "text": t}, f): (g, t) for f, g, t in FC.PROBES}

    def right(prompt):
        g, t = gold[prompt]
        return _reply("yes", t.split()[0]) if g == "yes" else _reply("no")
    return gold, right


def test_f1_the_watchers_calibration_asks_the_model_live_never_a_stored_reply(tmp_path):
    """F1 (Nov 14): the watcher's calibration was answered from the reply cache, so its daily re-calibration replayed
    the first answers and never re-measured the model it releases hard flags on. MUST FAIL the old code: a model that
    answered every quote right before and answers one wrong now is barred, though its stored replies are all right
    (the measurement CLI, which reproduces a report from its stored replies, still reads 16 / 16 without a call)."""
    gold, right = _gold()
    probes = tuple(p for p in FC.PROBES if p[0] in ("imperative", "single_source_breaking"))
    first = probes[0][2]
    b = H.FakeBackend("ca", fn=right)
    r = _router([b], cache_dir=str(tmp_path))
    allowed, cal = FC.watcher_checkers(r)
    assert allowed == ["ca"] and cal["ca"]["right"] == cal["ca"]["of"] == 16 and len(b.calls) == 16
    b.fn = lambda p: _reply("no") if gold[p][1] == first else right(p)      # the model behind the name changes
    replay = FC.calibrate(r, 2, probes)                                      # stored replies: the change is hidden
    assert replay["ca"]["right"] == 16 and len(b.calls) == 16
    allowed, cal = FC.watcher_checkers(r)                                    # live: every quote asked again
    assert len(b.calls) == 32 and allowed == [] and cal["ca"]["right"] == 15
    assert cal["ca"]["wrong"] == [{"flag": "imperative", "gold": "yes", "answer": "no", "text": first}]


def test_f1_a_quote_not_answered_is_asked_again_up_to_the_rounds(tmp_path):
    """A passing gateway error does not bar a checker: a quote it did not answer (the router's retries spent) is asked
    again in the next round, and only that quote; with no round left it stays unanswered and the checker is not
    allowed (nothing measured is never a pass)."""
    gold, right = _gold()
    first = FC.PROBES[0][2]
    for rounds, ok in ((1, False), (3, True)):
        failed = []

        def fn(p):
            if gold[p][1] == first and len(failed) < 3:          # the router's call and its 2 transport retries
                failed.append(p)
                return providers.BackendError("network", "down")
            return right(p)
        b = H.FakeBackend("ca", fn=fn)
        allowed, cal = FC.watcher_checkers(_router([b], cache_dir=str(tmp_path / f"r{rounds}")), rounds=rounds)
        asked_first = sum(1 for p in b.calls if gold[p][1] == first)
        if ok:
            assert allowed == ["ca"] and cal["ca"]["right"] == cal["ca"]["of"] == 16 and cal["ca"]["unmeasured"] == 0
            assert asked_first == 4 and len(b.calls) == 15 + 4               # the others were asked once
        else:
            assert allowed == [] and cal["ca"]["of"] == 15 and cal["ca"]["unmeasured"] == 1
            assert asked_first == 3 and len(b.calls) == 15 + 3


```

### The new tests (tests/ingest/test_service.py; svc, _checker, _flagging_miner and run_once are the file's existing fixtures)
```python
def test_f1_a_calibration_an_outage_left_unanswered_is_tried_again_soon_and_the_wait_doubles(svc):
    """F1 (Nov 14): the calibration is asked live, so an outage can leave it unanswered. Then no checker may answer
    (nothing measured is never a pass), but the next calibration comes after CHECK_RETRY_S, not a day later, the wait
    doubling while it keeps failing; once one passes, the daily calibration again, and the flags are checked."""
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1)
    run_once(s)
    good = b["fallback"].fn
    b["fallback"].fn = lambda p: providers.BackendError("network", "down")
    assert s.check_once(wait=True) == 0 and s.check_allowed == []
    assert s.check_recal_s == service.CHECK_RETRY_S
    n = len(b["fallback"].calls)
    s.check_once(wait=True)                                          # not due yet: nothing asked
    assert len(b["fallback"].calls) == n and s.check_recal_s == service.CHECK_RETRY_S

    def due():
        s.check_calibrated -= s.check_recal_s
        for h in s.router.health.values():
            h.open_until = 0.0
    due()
    assert s.check_once(wait=True) == 0 and s.check_allowed == []   # still down: asked again, the wait doubles
    assert len(b["fallback"].calls) > n and s.check_recal_s == 2 * service.CHECK_RETRY_S
    b["fallback"].fn = good                                          # back
    due()
    while s.check_once(wait=True):
        pass
    assert s.check_allowed == ["fallback"] and s.check_recal_s == service.CHECK_RECALIBRATE_S
    cal = json.loads(s.q.kv_get("check_calibration"))
    assert cal["fallback"]["right"] == cal["fallback"]["of"] == 16 and cal["fallback"]["asked_at"]
    since = datetime.fromtimestamp(s.clock() - 3600, timezone.utc)
    out, rep = ledger.best_unused_moments(s.p["ledger"], since, registry=[H.CHAN], optout=(), store_root=s.p["root"])
    assert out and rep["released_by_the_second_model"] == len(out)


def test_f1_a_checker_that_answers_a_quote_wrong_waits_for_the_daily_calibration(svc):
    """A calibration every back-end answered in full, with a quote answered wrong, bars them until the daily one (at
    temperature 0 a model answers a known quote the same way again: no quick retry)."""
    s, vids, b = svc(_checker("no", probes_right=False), _checker("no", probes_right=False), n_videos=1)
    run_once(s)
    assert s.check_once(wait=True) == 0 and s.check_allowed == []
    assert s.check_recal_s == service.CHECK_RECALIBRATE_S


```
