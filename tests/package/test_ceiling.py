#!/usr/bin/env python3
"""R1 (build 172, the owner's 15:25 ET order): ONE enforceable cumulative $1.50 ceiling across the builder, the audio lock
service and the renderer: pipeline/spend_ceiling.py (byte-identical on lean-release) and providers.Router in ceiling
mode, on ONE ledger file. Offline: no vendor is asked; every paid call here is a stub, every ledger a temporary file.
  - three processes (the builder's router, the lock service's Scribe, the render's sign-off) race one ledger: the
    total never passes the cap, nothing is lost, no reservation is left;
  - a call at the cap is refused before any network use (the back-end never called, no socket opened);
  - a crash between reserve and settle stays counted (the old router released it: shown);
  - a cost unknown after the call, a bill above its reservation, a lock past its wait, an unreadable ledger: fail closed;
  - the guard: no paid endpoint is reachable without a reservation; free ones are;
  - the completion reserve (lean (5)) reads the same ledger; the launch's seed counts the day's other spend."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/package/lean"):
    sys.path.insert(0, os.path.join(REPO, _p))
import providers as P  # noqa: E402
import spend_ceiling as SC  # noqa: E402

GROK = "xai:grok-4.20-0309-reasoning"
NOW = datetime(2026, 11, 25, 15, 0, tzinfo=timezone.utc)          # a moment of build 172's spend day (Nov 24 21:10 ET)
LEAN_RELEASE = "/home/ultron/worktrees/pp-lean-release/pipeline/spend_ceiling.py"


NOSOCK = r'''
import socket as _socket
OPENED = []
def _blocked(*a, **k):
    OPENED.append(repr(a[1:])[:80])
    raise OSError("the network is blocked by this test")
_socket.socket.connect = _blocked
_socket.socket.connect_ex = _blocked
_socket.getaddrinfo = _blocked
_socket.create_connection = _blocked
'''                          # every subprocess these tests start runs this first: no socket, no DNS, ever
_SAVED = {}


PROD_ENV = ("PP_SPEND_PROD_BUILDER", "PP_SPEND_PROD_OUTSIDE", "PP_SPEND_PROD_RUNS", "PP_SPEND_ONE_WAIT_S")


def setUpModule():
    import socket
    for k in ("getaddrinfo", "create_connection"):
        _SAVED[k] = getattr(socket, k)
    _SAVED["connect"], _SAVED["connect_ex"] = socket.socket.connect, socket.socket.connect_ex

    def blocked(*a, **k):
        raise OSError("the network is blocked by this test")
    socket.getaddrinfo = socket.create_connection = blocked
    socket.socket.connect = socket.socket.connect_ex = blocked
    # B1 (b): every reservation re-reads PRODUCTION's day ledgers: here empty stand-ins (never the live ledgers), and no
    # running process matches (the tests that check those set their own); B2's wait for the one slot: short
    prod = tempfile.mkdtemp(prefix="ceiling_prod_")
    _SAVED["env"] = {k: os.environ.get(k) for k in PROD_ENV}
    os.environ.update(PP_SPEND_PROD_BUILDER=prod, PP_SPEND_PROD_OUTSIDE=os.path.join(prod, "outside.jsonl"),
                      PP_SPEND_PROD_RUNS="no-production-run-in-tests", PP_SPEND_ONE_WAIT_S="20")
    _SAVED["wait"], SC.ONE_WAIT_S = SC.ONE_WAIT_S, 20.0


def tearDownModule():
    import socket
    socket.getaddrinfo, socket.create_connection = _SAVED["getaddrinfo"], _SAVED["create_connection"]
    socket.socket.connect, socket.socket.connect_ex = _SAVED["connect"], _SAVED["connect_ex"]
    shutil.rmtree(os.environ["PP_SPEND_PROD_BUILDER"], True)
    for k, v in _SAVED["env"].items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    SC.ONE_WAIT_S = _SAVED["wait"]


class Tmp(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.path = SC.ledger_path(NOW, self.d)
        SC.init_day({}, by="test", path=self.path, now=NOW)       # B1 (a): initialized before anything charges

    def router(self, answer=None, ceiling=True, **kw):
        r = P.Router(spend_path=self.path, limit_usd=SC.CAP_USD, limit_basis="reported", uncapped=("heimdall",),
                     chains={"coherence_verdict": [GROK]}, ceiling=ceiling, **kw)
        self.asked = []

        def complete(prompt, max_tokens, seed, system=None):
            self.asked.append(prompt)
            if isinstance(answer, BaseException):
                raise answer
            return '{"ok": true}', dict({"in": 10, "out": 10, "usd_reported": 0.011}, **(answer or {})), 0.1
        r.backends[GROK].complete = complete
        return r


def run(code, env_extra=None, timeout=120):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([os.path.join(REPO, "pipeline"), os.path.join(REPO, "tests",
                                                                                                     "package")]),
               **(env_extra or {}))
    return subprocess.run([sys.executable, "-B", "-c", NOSOCK + textwrap.dedent(code)], capture_output=True,
                          text=True, timeout=timeout, env=env)


RACER = NOSOCK + r'''
import json, os, random, sys, time
import spend_ceiling as SC, providers as P
path, who, n = sys.argv[1], sys.argv[2], 0
refused = 0
if who == "builder":
    r = P.Router(spend_path=path, limit_usd=SC.CAP_USD, limit_basis="reported", uncapped=("heimdall",),
                 chains={"coherence_verdict": ["xai:grok-4.20-0309-reasoning"]}, ceiling=True)
    b = r.backends["xai:grok-4.20-0309-reasoning"]
    b.complete = lambda prompt, mt, seed, system=None: ('{"ok": 1}', {"in": 10, "out": 10, "usd_reported": 0.011}, 0.01)
for i in range(400):
    time.sleep(random.random() * 0.003)
    try:
        if who == "builder":
            r.call("coherence_verdict", "x" * 2000, 1200, 7 + i)
            n += 1
        elif who == "lock":
            with SC.charge("elevenlabs_stt:scribe_v1", 0.0078, role="lock_precheck", path=path) as c:
                c.cost(0.0078, reported=False)
            n += 1
        else:
            with SC.charge("xai:grok-3-mini", 0.05, role="render", path=path) as c:
                c.cost(0.0040, reported=True)
            n += 1
    except (SC.CeilingRefused, P.SpendLimit):
        refused += 1
print(json.dumps({"who": who, "n": n, "refused": refused}))
'''


class TestTheCeilingHoldsUnderARace(Tmp):
    def test_three_programs_race_one_ledger_and_the_total_never_passes_the_cap(self):
        """MUST-PASS: the builder's router (Grok verdicts, $0.011 each), the lock service (Scribe, $0.0078) and the render
        (sign-off, $0.004) spend against ONE ledger already carrying $1.00 from the day, in parallel, until refused: the
        ledger never passes $1.50, nothing is lost (its total = the day's $1.00 + what each process says it paid), and
        no reservation is left behind."""
        SC.seed({"builder:pp-selectid": 1.00}, path=self.path)
        script = os.path.join(self.d, "racer.py")
        with open(script, "w") as f:
            f.write(RACER)
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([os.path.join(REPO, "pipeline")]))
        ps = [subprocess.Popen([sys.executable, "-B", script, self.path, who], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, env=env) for who in ("builder", "lock", "render")]
        outs = [p.communicate(timeout=300) for p in ps]
        self.assertEqual([p.returncode for p in ps], [0, 0, 0], [e[-400:] for _, e in outs])
        res = {r["who"]: r for r in (json.loads(o.strip().splitlines()[-1]) for o, _ in outs)}
        d = SC.read(self.path)
        total = SC.spent(d) + SC.held(d)
        self.assertLessEqual(total, SC.CAP_USD + 1e-9)
        self.assertEqual(d["reserved"], {})
        paid = 1.00 + 0.011 * res["builder"]["n"] + 0.0078 * res["lock"]["n"] + 0.0040 * res["render"]["n"]
        self.assertAlmostEqual(SC.spent(d), paid, places=6)           # no update lost
        self.assertTrue(all(r["refused"] > 0 for r in res.values()), res)   # each one met the ceiling
        self.assertTrue(all(r["n"] > 0 for r in res.values()), res)


class TestRefusedBeforeTheVendor(Tmp):
    def test_at_the_cap_no_backend_is_called(self):
        """MUST-FAIL: the day at $1.48 of $1.50: the builder's Grok call ($0.08 reserved) and a render sign-off ($0.05)
        are refused before anything is sent."""
        SC.seed({"builder:pp-selectid": 1.48}, path=self.path)
        r = self.router()
        with self.assertRaises(P.SpendLimit):
            r.call("coherence_verdict", "x" * 3000, 1200, 7)
        self.assertEqual(self.asked, [])
        ran = []
        with self.assertRaises(SC.CeilingRefused):
            with SC.charge("xai:grok-3-mini", 0.05, path=self.path):
                ran.append(1)
        self.assertEqual(ran, [])
        self.assertEqual(SC.read(self.path)["reserved"], {})

    def test_the_guard_refuses_a_paid_request_without_a_reservation_before_any_socket(self):
        out = run(r'''
            import json, urllib.request, spend_ceiling as SC
            print(SC.install_guard())
            for url in ("https://api.x.ai/v1/chat/completions", "https://api.elevenlabs.io/v1/speech-to-text"):
                try:
                    urllib.request.urlopen(urllib.request.Request(url, data=b"{}"), timeout=2)
                    print("REACHED", url)
                except SC.CeilingRefused as e:
                    print("REFUSED", url)
            print("SOCKETS", len(OPENED))
        ''')
        self.assertEqual(out.returncode, 0, out.stderr[-500:])
        self.assertIn("REFUSED https://api.x.ai/v1/chat/completions", out.stdout)
        self.assertIn("REFUSED https://api.elevenlabs.io/v1/speech-to-text", out.stdout)
        self.assertIn("SOCKETS 0", out.stdout)

    def test_the_guard_lets_a_reserved_call_and_every_free_endpoint_through(self):
        """MUST-PASS: inside a reservation (charge(), or a router call bound to its key in its deadline thread) the
        paid request goes on to the transport; Heimdall, Telegram and the voice account's free reads need none."""
        out = run(r'''
            import tempfile, os, urllib.request, spend_ceiling as SC
            seen = []
            class T(urllib.request.HTTPSHandler):        # a subclass: build_opener leaves the real one out
                def https_open(self, req):
                    seen.append(req.full_url)
                    raise urllib.error.URLError("stub transport")
            urllib.request.install_opener(urllib.request.build_opener(T))
            SC.install_guard()
            d = tempfile.mkdtemp()
            p = os.path.join(d, "L.json")
            SC.init_day({}, by="test", path=p)
            def get(url):
                try:
                    urllib.request.urlopen(url, timeout=2)
                except urllib.error.URLError:
                    pass
            with SC.charge("xai:grok-3-mini", 0.05, path=p) as c:
                get("https://api.x.ai/v1/chat/completions")
                c.cost(0.004)
            k = SC.reserve("xai:grok-4.20-0309-reasoning", 0.08, path=p)
            import threading
            t = threading.Thread(target=SC.bound(k, lambda: get("https://api.x.ai/v1/chat/completions")))
            t.start(); t.join()
            for u in ("https://api-staging.heimdallm.com/api/v1/chat/completions", "https://api.telegram.org/bot1/getMe",
                      "https://api.elevenlabs.io/v1/user/subscription"):
                get(u)
            print("SEEN", len(seen), "SOCKETS", len(OPENED))
        ''')
        self.assertEqual(out.returncode, 0, out.stderr[-500:])
        self.assertIn("SEEN 5 SOCKETS 0", out.stdout)


CRASHER = NOSOCK + r'''
import os, sys, spend_ceiling as SC
SC.reserve("xai_vision:grok-4.7", 0.40, role="vision", path=sys.argv[1])
os._exit(3)                                          # dies between reserve and settle
'''


class TestACrashStaysCounted(Tmp):
    def test_a_reservation_of_a_dead_process_is_never_released(self):
        """MUST-PASS: a process reserves $0.40 and dies before it settles: the one ledger keeps the $0.40 counted, and
        the builder's router (ceiling mode) refuses a $0.08 call that would fit without it. MUST-FAIL before: the old
        router read the same file and released the dead process's reservation (the call went ahead)."""
        SC.seed({"builder:pp-selectid": 1.05}, path=self.path)
        script = os.path.join(self.d, "crasher.py")
        with open(script, "w") as f:
            f.write(CRASHER)
        p = subprocess.run([sys.executable, "-B", script, self.path], env=dict(os.environ, PYTHONPATH=os.path.join(
            REPO, "pipeline")), capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 3)
        self.assertAlmostEqual(SC.status(self.path)["held"], 0.40, places=6)
        r = self.router()
        with self.assertRaises(P.SpendLimit):
            r.call("coherence_verdict", "x" * 3000, 1200, 7)              # its cost is unknown: the ledger stops
        self.assertEqual(self.asked, [])
        st = SC.status(self.path)
        self.assertIn("ended before it settled", st["stop"]["why"])
        self.assertAlmostEqual(st["held"], 0.40, places=6)               # still counted
        with self.assertRaises(SC.CeilingRefused):                        # every program, not only the router
            SC.reserve("elevenlabs_stt:scribe_v1", 0.001, path=self.path)
        SC.clear_stop("the owner", "test", path=self.path)
        old = self.router(ceiling=False)
        old.call("coherence_verdict", "x" * 3000, 1200, 7)               # the old reading: released, went ahead
        self.assertEqual(len(self.asked), 1)


class TestFailClosed(Tmp):
    def test_a_cost_unknown_after_the_call_keeps_it_counted_and_stops_every_program(self):
        """MUST-FAIL: the render's call raises after it may have reached the vendor: its reservation stays, the ledger
        stops, and the next paid call of any program (the lock service's Scribe, the builder's Grok) is refused."""
        with self.assertRaises(RuntimeError):
            with SC.charge("xai:grok-3-mini", 0.05, role="render", path=self.path):
                raise RuntimeError("the connection dropped mid-reply")
        st = SC.status(self.path)
        self.assertTrue(st["stop"])
        self.assertAlmostEqual(st["held"], 0.05, places=6)
        with self.assertRaises(SC.CeilingRefused):
            SC.reserve("elevenlabs_stt:scribe_v1", 0.0078, path=self.path)
        r = self.router()
        with self.assertRaises(P.SpendLimit):
            r.call("coherence_verdict", "x" * 3000, 1200, 7)
        self.assertEqual(self.asked, [])
        SC.clear_stop("the owner", "test", path=self.path)               # only the owner's step clears it
        self.assertFalse(SC.status(self.path)["stop"])
        self.assertAlmostEqual(SC.status(self.path)["held"], 0.05, places=6)   # still counted

    def test_the_router_keeps_an_unavailable_or_abandoned_call_and_stops(self):
        r = self.router(answer=P.Unavailable("HTTP 503 after the request was sent"))
        with self.assertRaises(P.ProviderError):
            r.call("coherence_verdict", "x" * 3000, 1200, 7)
        st = SC.status(self.path)
        self.assertTrue(st["stop"])
        self.assertGreater(st["held"], 0.0)
        Tmp.setUp(self)                                                   # a fresh ledger: the deadline case
        r = self.router()
        late = []
        slow = r.backends[GROK].complete

        def complete(*a, **k):
            time.sleep(1.5)
            late.append(1)
            return slow(*a, **k)
        r.backends[GROK].complete = complete
        with self.assertRaises(P.ProviderError):
            r.call("coherence_verdict", "x" * 3000, 1200, 7, deadline_s=0.3)
        st = SC.status(self.path)
        self.assertTrue(st["stop"])
        self.assertGreater(st["held"], 0.0)                               # abandoned: its reservation stays
        time.sleep(2.0)
        st = SC.status(self.path)
        self.assertEqual((late, st["held"]), ([1], 0.0))                  # the late answer's own figure settles it
        self.assertTrue(st["stop"])                                       # the stop stays for the owner

    def test_a_refused_request_is_released_without_a_stop(self):
        r = self.router(answer=P._answered(P.RequestRejected("HTTP 400"), 400))
        with self.assertRaises(P.ProviderError):
            r.call("coherence_verdict", "x" * 3000, 1200, 7)
        st = SC.status(self.path)
        self.assertEqual((st["stop"], st["held"]), (None, 0.0))

    def test_the_real_transport_marks_what_the_vendor_answered(self):
        """The marks come from the router's own transport (_with_backoff) and key lookup, not from this test: a 4xx
        answer (429 after its retries, 400) and a key that is not configured release the reservation; a 5xx, a dropped
        connection and a 200 reply without an answer keep it and stop the ledger. The vendor is a stub; the key file
        is an empty temporary file (no real key is read)."""
        import io
        import urllib.error
        saved = P.BACKOFF_S, P._http_json
        P.BACKOFF_S = ()
        empty_env = os.path.join(self.d, "empty.env")
        open(empty_env, "w").close()

        def http_error(status):
            def f(url, body, headers, timeout):
                raise urllib.error.HTTPError(url, status, "stub", {}, io.BytesIO(b"{}"))
            return f

        def dropped(url, body, headers, timeout):
            raise urllib.error.URLError("connection reset by peer")

        def no_choices(url, body, headers, timeout):
            return {"usage": {"prompt_tokens": 900, "completion_tokens": 40}}
        cases = (("429", http_error(429), "k", False), ("400", http_error(400), "k", False),
                 ("key missing", http_error(500), None, False), ("503", http_error(503), "k", True),
                 ("dropped", dropped, "k", True), ("200 without an answer", no_choices, "k", True))
        try:
            for label, transport, key, stops in cases:
                Tmp.setUp(self)
                r = P.Router(spend_path=self.path, limit_usd=SC.CAP_USD, limit_basis="reported", uncapped=("heimdall",),
                             chains={"coherence_verdict": [GROK]}, ceiling=True, env_path=empty_env)
                if key:
                    r.backends[GROK].key = lambda name: "stub-key"
                P._http_json = transport
                with self.assertRaises(P.ProviderError, msg=label):
                    r.call("coherence_verdict", "x" * 3000, 1200, 7)
                st = SC.status(self.path)
                self.assertEqual((bool(st["stop"]), st["held"] > 0), (stops, stops), label)
        finally:
            P.BACKOFF_S, P._http_json = saved

    def test_a_bill_above_its_reservation_stops_the_ledger(self):
        r = self.router(answer={"usd_reported": 0.50})                   # far above a 25 %-of-list reservation
        r.call("coherence_verdict", "x" * 3000, 1200, 7)
        self.assertTrue(SC.status(self.path)["stop"])
        Tmp.setUp(self)
        k = SC.reserve("xai:grok-3-mini", 0.05, path=self.path)
        SC.settle(k, "xai:grok-3-mini", 0.07, path=self.path)
        st = SC.status(self.path)
        self.assertTrue(st["stop"])
        self.assertAlmostEqual(st["spent"], 0.07, places=6)               # counted as billed

    def test_an_unreadable_ledger_or_a_lock_past_its_wait_refuses(self):
        with open(self.path, "w") as f:
            f.write("{ not json")
        with self.assertRaises(SC.CeilingRefused):
            SC.reserve("xai:grok-3-mini", 0.05, path=self.path)
        r = self.router()
        with self.assertRaises(P.SpendLimit):
            r.call("coherence_verdict", "x" * 3000, 1200, 7)
        os.remove(self.path)
        holder = subprocess.Popen([sys.executable, "-c", textwrap.dedent(f'''
            import fcntl, time, sys
            f = open({self.path + ".lock"!r}, "w"); fcntl.flock(f, fcntl.LOCK_EX); print("HELD", flush=True)
            time.sleep(6)''')], stdout=subprocess.PIPE, text=True)
        self.assertEqual(holder.stdout.readline().strip(), "HELD")
        saved = SC.LOCK_WAIT_S
        SC.LOCK_WAIT_S = 0.5
        try:
            t0 = time.time()
            with self.assertRaises(SC.CeilingRefused):
                SC.reserve("xai:grok-3-mini", 0.05, path=self.path)
            with self.assertRaises(P.SpendLimit):
                self.router().call("coherence_verdict", "x" * 3000, 1200, 7)
            self.assertLess(time.time() - t0, 3.0)
        finally:
            SC.LOCK_WAIT_S = saved
            holder.kill()
            holder.wait()

    def test_a_vendor_s_4xx_refusal_or_a_refusal_before_sending_releases(self):
        class HTTP429(Exception):                     # the shape of requests' / httpx's HTTP errors
            response = type("R", (), {"status_code": 429})()
        for exc in (HTTP429("rate limited"), SC.CeilingRefused("refused before sending")):
            with self.assertRaises(type(exc)):
                with SC.charge("xai:grok-3-mini", 0.05, path=self.path):
                    raise exc
            st = SC.status(self.path)
            self.assertEqual((st["stop"], st["held"], st["spent"]), (None, 0.0, 0.0))

        class HTTP503(Exception):
            response = type("R", (), {"status_code": 503})()
        with self.assertRaises(HTTP503):                                  # a 5xx: not known to be free
            with SC.charge("xai:grok-3-mini", 0.05, path=self.path):
                raise HTTP503("bad gateway")
        self.assertTrue(SC.status(self.path)["stop"])

    def test_a_back_end_whose_bill_no_ledger_can_settle_is_never_called(self):
        """xai_search (the trend brief, not called by the build): its live-search fees are not in its reply: refused
        under the one ledger, the back-end never asked; without the ceiling, as before."""
        for ceiling, refused in ((True, True), (False, False)):
            Tmp.setUp(self)
            r = P.Router(spend_path=self.path, limit_usd=SC.CAP_USD, limit_basis="reported", uncapped=("heimdall",),
                         chains={"trend_brief": ["xai_search:grok-4.7"]}, ceiling=ceiling)
            asked = []
            r.backends["xai_search:grok-4.7"].complete = lambda *a, **k: (asked.append(1) or "{}", {"in": 1, "out": 1},
                                                                          0.1)
            if refused:
                with self.assertRaises(P.SpendLimit):
                    r.call("trend_brief", "x", 100, 7)
            else:
                r.call("trend_brief", "x", 100, 7)
            self.assertEqual(asked, [] if refused else [1])

    def test_an_unbounded_call_is_never_made(self):
        with self.assertRaises(SC.CeilingRefused):
            with SC.charge("xai:grok-3-mini", None, path=self.path):
                pass


class TestTheVoice(Tmp):
    def test_the_voice_is_held_to_its_characters_per_build_not_dollars(self):
        """No USD rate is established offline: the voice is outside the dollar ceiling and held to VOICE_CHAR_CAP
        characters PER BUILD (PP_SPEND_RUN); a line past it is refused before the call; another build has its own
        count; "usd" mode without the owner's rate refuses (no rate of ours)."""
        saved = os.environ.get("PP_SPEND_RUN")
        os.environ["PP_SPEND_RUN"] = "build172"
        try:
            with SC.charge("elevenlabs_tts:eleven_v4", SC.voice_usd(400), role="render", chars=400, path=self.path) as c:
                c.cost(0.0, reported=False, usage={"characters": 400})
            with self.assertRaises(SC.CeilingRefused):
                SC.reserve("elevenlabs_tts:eleven_v4", 0.0, chars=SC.VOICE_CHAR_CAP - 399, path=self.path)
            st = SC.status(self.path)
            self.assertEqual((st["voice"]["run"], st["voice"]["chars"], st["spent"]), ("build172", 400, 0.0))
            os.environ["PP_SPEND_RUN"] = "build173"
            k = SC.reserve("elevenlabs_tts:eleven_v4", 0.0, chars=SC.VOICE_CHAR_CAP - 399, path=self.path)
            SC._release(k, self.path)
        finally:
            if saved is None:
                os.environ.pop("PP_SPEND_RUN", None)
            else:
                os.environ["PP_SPEND_RUN"] = saved
        mode = SC.VOICE_MODE
        SC.VOICE_MODE = "usd"
        try:
            with self.assertRaises(SC.CeilingRefused):
                SC.voice_usd(400)
        finally:
            SC.VOICE_MODE = mode


class TestOneLedgerForTheCompletionReserve(Tmp):
    def test_a_hold_by_another_program_narrows_what_the_search_may_spend(self):
        """(e): the builder's completion reserve is checked against the SAME ledger the lock service and the render
        reserve in: their hold leaves the search less room."""
        SC.seed({"builder:pp-selectid": 0.50}, path=self.path)
        r = self.router()
        r.completion_reserve_usd = 0.82
        r.call("coherence_verdict", "x" * 3000, 1200, 7)                 # 0.50 + 0.08 + 0.82 <= 1.50
        k = SC.reserve("elevenlabs_stt:scribe_v1", 0.10, role="lock_precheck", path=self.path)
        with self.assertRaises(P.CompletionReserve):
            r.call("coherence_verdict", "x" * 3001, 1200, 8)            # the lock service's hold leaves no room
        SC.settle(k, "elevenlabs_stt:scribe_v1", 0.0078, reported=False, path=self.path)


class TestTheReserveHoldsTheRendersReservations(unittest.TestCase):
    def test_a_completion_that_spends_its_whole_reserve_leaves_the_render_its_sign_off(self):
        """(e) under the one ledger: the day spent up to the completion reserve (the speculative search stopped there),
        then every completion call bills its FULL reservation, the lock service's Scribe included: the render's
        sign-off reservation ($0.05) still fits. MUST-FAIL before: the reserve counted the sign-off at its $0.0045 bill
        and the lock's Scribe at $0.01, and the render was refused its sign-off for money."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        code = r'''
            import os, sys, tempfile, proof_ly as PL, providers as P, package as PK, spend_ceiling as SC
            r = P.Router(spend_path=SC.ledger_path(), limit_usd=SC.CAP_USD, limit_basis="reported",
                         uncapped=PL.UNCAPPED, chains=PL.chains("heimdall_first"), routing="heimdall_first", ceiling=True)
            cr = PK.completion_reserve(r)
            SC.seed({"the day so far": round(SC.CAP_USD - cr["usd"], 6)})
            for part in cr["parts"]:
                if part["what"].startswith("the render's sign-off"):
                    continue
                for _ in range(part["calls"]):
                    k = SC.reserve(part["backend"] or "elevenlabs_stt:scribe_v1", part["usd_each"])
                    SC.settle(k, part["backend"] or "elevenlabs_stt:scribe_v1", part["usd_each"])
            try:
                with SC.charge("xai:grok-3-mini", SC.SIGNOFF_RESERVE_USD, role="render") as c:
                    c.cost(0.004013)
                print("SIGN-OFF FITS", round(cr["usd"], 4))
            except SC.CeilingRefused as e:
                print("SIGN-OFF REFUSED", round(cr["usd"], 4))
        '''
        out = run(code, {"PP_SPEND_CEILING": "1", "PP_SPEND_LEDGER_DIR": d})
        self.assertEqual(out.returncode, 0, out.stderr[-600:])
        self.assertTrue(out.stdout.startswith("SIGN-OFF FITS"), out.stdout)


class TestTheDriverUsesTheOneLedger(unittest.TestCase):
    def test_under_the_launch_s_switch_the_day_ledger_is_the_one_ledger(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        out = run(r'''
            import proof_ly as PL, spend_ceiling as SC
            print(PL.CEILING, PL.SPEND == SC.ledger_path(), PL.SPEND)
        ''', {"PP_SPEND_CEILING": "1", "PP_SPEND_LEDGER_DIR": d})
        self.assertEqual(out.returncode, 0, out.stderr[-400:])
        self.assertTrue(out.stdout.startswith(f"True True {d}/SPEND_D"), out.stdout)
        out = run("import proof_ly as PL; print(PL.CEILING, '/tests/package/proof/' in PL.SPEND)")
        self.assertEqual(out.stdout.split(), ["False", "True"])            # unset: the worktree's ledger, as before

    def test_one_cap(self):
        import proof_ly as PL
        self.assertEqual((PL.DAY_CAP_USD, PL.LY_LIMIT_USD), (SC.CAP_USD, SC.CAP_USD))


class TestTheSeed(unittest.TestCase):
    def test_the_day_s_other_spend_is_carried_in_once_and_an_unknown_source_refuses(self):
        import ceiling_seed as CS
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        start = SC.day_start(NOW)
        rel = os.path.join("tests", "package", "proof", CS.day_file(start))
        prod, copy, other = (os.path.join(d, w, rel) for w in ("pp-selectid", "pp-lean", "stray"))
        for p in (prod, copy, other):
            os.makedirs(os.path.dirname(p))
        ledger = {"usd_estimate": 1.0, "usd_reported": 0.6, "usd_unreported_estimate": 0.05, "calls": 3,
                  "by_backend": {GROK: {"usd_reported": 0.6}, "heimdall:qwen/qwen3.8-27b": {"usd_reported": 0.3}},
                  "reserved": {}}
        for p in (prod, copy):
            with open(p, "w") as f:
                json.dump(ledger, f)
        out_led = os.path.join(d, "outside.jsonl")
        with open(out_led, "w") as f:
            for at, usd, vendor in (("2026-11-25T03:00:00Z", 0.0078, "elevenlabs:scribe_v1"),
                                    ("2026-11-25T03:01:00Z", None, "elevenlabs:tts:eleven_v4"),
                                    ("2026-11-24T01:00:00Z", 0.5, "xai:grok-3-mini")):    # the day before: not counted
                f.write(json.dumps({"at": at, "usd": usd, "vendor": vendor, "units": {"characters": 107}}) + "\n")
        parts, voice, notes, unknown = CS.parts_for(start, start.replace(day=start.day + 1), production=os.path.join(
            d, "pp-selectid"), worktrees=d, outside=out_led)
        self.assertEqual(parts["builder:pp-selectid"], 0.65)            # Heimdall never counted
        self.assertEqual((parts["integrator:outside"], voice, unknown), (0.0078, 107, []))
        self.assertTrue([n for n in notes if "copy" in n and "pp-lean" in n])    # a copy is never counted twice
        with open(other, "w") as f:
            json.dump(dict(ledger, usd_reported=0.9), f)
        _, _, _, unknown = CS.parts_for(start, start.replace(day=start.day + 1), production=os.path.join(
            d, "pp-selectid"), worktrees=d, outside=out_led)
        self.assertEqual(unknown, [other])                               # MUST-FAIL: an unknown source refuses
        led = SC.ledger_path(NOW, d)
        SC.seed(parts, path=led)
        r = P.Router(spend_path=led, limit_usd=SC.CAP_USD, limit_basis="reported", uncapped=("heimdall",), ceiling=True)
        self.assertAlmostEqual(r.spent(), 0.6578, places=6)              # the router counts the carried-in spend


class TestTheLedgerFirst(unittest.TestCase):
    def test_no_paid_call_before_the_ledger_is_initialized(self):
        """B1 (a), MUST-FAIL: a ledger that does not exist yet (or was never initialized) refuses every program's paid
        call before the vendor is asked: a service started before the launch's ledger-init charges nothing."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = SC.ledger_path(NOW, d)
        with self.assertRaisesRegex(SC.CeilingRefused, "not initialized"):
            SC.reserve("elevenlabs_stt:scribe_v1", 0.0078, path=path)
        r = P.Router(spend_path=path, limit_usd=SC.CAP_USD, limit_basis="reported", uncapped=("heimdall",),
                     chains={"coherence_verdict": [GROK]}, ceiling=True)
        asked = []
        r.backends[GROK].complete = lambda *a, **k: (asked.append(1) or '{"ok": 1}', {"in": 1, "out": 1}, 0.1)
        with self.assertRaises(P.SpendLimit) as cm:
            r.call("coherence_verdict", "x" * 3000, 1200, 7)
        self.assertIn("not initialized", str(cm.exception))
        self.assertEqual(asked, [])
        SC.init_day({}, by="test", path=path, now=NOW)
        r.call("coherence_verdict", "x" * 3000, 1200, 7)                  # initialized: it goes ahead
        self.assertEqual(asked, [1])


class Production(Tmp):
    """Production's day ledgers as stand-ins (PP_SPEND_PROD_BUILDER / _OUTSIDE, set by setUpModule)."""

    def prod_ledger(self, usd, held=0.0):
        d = os.path.join(os.environ["PP_SPEND_PROD_BUILDER"], "tests", "package", "proof")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, SC.prod_day_file(SC.day_start(NOW)))
        with open(p + ".tmp", "w") as f:
            json.dump({"usd_estimate": usd, "usd_reported": usd, "usd_unreported_estimate": 0.0, "calls": 1,
                       "by_backend": {GROK: {"usd_reported": usd}}, "reserved": {"1:x": held} if held else {}}, f)
        os.replace(p + ".tmp", p)
        self.addCleanup(lambda: os.path.exists(p) and os.remove(p))
        return p

    def outside(self, *lines):
        p = os.environ["PP_SPEND_PROD_OUTSIDE"]
        with open(p, "a") as f:
            for x in lines:
                f.write(json.dumps(x) + "\n")
        self.addCleanup(lambda: os.path.exists(p) and os.remove(p))


class TestProductionAtEveryReservation(Production):
    def test_production_s_live_spend_lowers_the_room_at_once(self):
        """B1 (b), MUST-FAIL: production's builder ledger grows from $0.50 to $1.45 AFTER the launch's init: the next
        reservation of every program re-reads it under the one ledger's lock and is refused (the room is gone); the
        one ledger shows production's figure. MUST-FAIL before: the seed counted production once, at launch (shown with
        the re-read switched off: the call goes ahead on the stale $0.50)."""
        self.prod_ledger(0.50)
        SC.init_day({"builder:pp-selectid": 0.50}, by="test", path=self.path, now=NOW)
        r = self.router()
        r.call("coherence_verdict", "x" * 3000, 1200, 7)                  # room: $1.00 - its own reservation
        self.prod_ledger(1.45)
        with self.assertRaises(P.SpendLimit):
            r.call("coherence_verdict", "x" * 3001, 1200, 8)
        with self.assertRaises(SC.CeilingRefused):
            SC.reserve("xai:grok-3-mini", 0.05, path=self.path)
        self.assertEqual(len(self.asked), 1)
        self.assertAlmostEqual(SC.status(self.path)["carried_in"]["carried_in:builder:pp-selectid"], 1.45, places=6)
        with mock.patch.object(SC, "refresh_production", lambda d, now=None: False):   # the old reading: once
            Tmp.setUp(self)
            SC.init_day({"builder:pp-selectid": 0.50}, by="test", path=self.path, now=NOW)
            r = self.router()
            r.call("coherence_verdict", "x" * 3002, 1200, 9)
            r.call("coherence_verdict", "x" * 3003, 1200, 10)
            self.assertEqual(len(self.asked), 2)                          # went ahead on $0.50

    def test_the_outside_ledger_and_a_production_reservation_count_too(self):
        self.prod_ledger(1.00, held=0.30)                                 # production's own call in flight: counted
        SC.init_day({}, by="test", path=self.path, now=NOW)
        with self.assertRaises(SC.CeilingRefused):
            SC.reserve("xai:grok-3-mini", 0.25, path=self.path)          # 1.30 + 0.25 > 1.50
        k = SC.reserve("xai:grok-3-mini", 0.15, path=self.path)
        SC.settle(k, "xai:grok-3-mini", 0.004, path=self.path)
        self.outside({"at": NOW.isoformat().replace("+00:00", "Z"), "usd": 0.19, "vendor": "elevenlabs:scribe_v1"})
        with self.assertRaises(SC.CeilingRefused):                        # production's lock check, after the fact
            SC.reserve("elevenlabs_stt:scribe_v1", 0.01, path=self.path)
        self.assertAlmostEqual(SC.status(self.path)["spent"], 1.30 + 0.19 + 0.004, places=6)

    def test_an_unreadable_or_unknown_production_ledger_refuses(self):
        SC.init_day({}, by="test", path=self.path, now=NOW)
        p = self.prod_ledger(0.10)
        with open(p, "w") as f:
            f.write("{ torn")
        with self.assertRaisesRegex(SC.CeilingRefused, "unreadable"):
            SC.reserve("xai:grok-3-mini", 0.05, path=self.path)
        os.remove(p)
        self.outside({"at": NOW.isoformat().replace("+00:00", "Z"), "usd": None, "vendor": "openai:gpt"})
        with self.assertRaisesRegex(SC.CeilingRefused, "unknown kind"):
            SC.reserve("xai:grok-3-mini", 0.05, path=self.path)


SLEEPER = "#!/bin/bash\nsleep 30\n"            # no exec: bash keeps the script as its argument


class TestAProductionRunStopsPaidCalls(Production):
    def test_a_production_render_appearing_stops_every_program(self):
        """B1 (b), MUST-FAIL: a render (pulse_check_run.sh) not started by our launcher appears: the next reservation
        STOPS the ledger (production does not reserve here); started under our launcher (lean_ops.py), it is ours."""
        script = os.path.join(self.d, "pulse_check_run.sh")
        with open(script, "w") as f:
            f.write(SLEEPER)
        saved = os.environ.get("PP_SPEND_PROD_RUNS")
        os.environ["PP_SPEND_PROD_RUNS"] = "pulse_check_run.sh"
        try:
            parent = os.path.join(self.d, "lean_ops.py")                  # a stand-in for our launcher
            with open(parent, "w") as f:
                f.write(f"import subprocess; subprocess.run(['bash', {script!r}])\n")
            ours = subprocess.Popen([sys.executable, parent])
            self.addCleanup(lambda: (ours.kill(), ours.wait()))
            time.sleep(0.5)
            self.assertEqual(SC.production_running(fresh=True), [])       # ours: not production
            k = SC.reserve("xai:grok-3-mini", 0.05, path=self.path)
            SC.settle(k, "xai:grok-3-mini", 0.004, path=self.path)
            prod = subprocess.Popen(["bash", script])
            self.addCleanup(lambda: (prod.kill(), prod.wait()))
            time.sleep(0.3)
            SC._SCAN["at"] = 0.0
            with self.assertRaisesRegex(SC.CeilingRefused, "STOPPED"):
                SC.reserve("xai:grok-3-mini", 0.05, path=self.path)
            st = SC.status(self.path)
            self.assertIn(f"pid {prod.pid}", st["stop"]["why"])
            r = self.router()
            with self.assertRaises(P.SpendLimit):
                r.call("coherence_verdict", "x" * 3000, 1200, 7)
            self.assertEqual(self.asked, [])
        finally:
            SC._SCAN["at"] = 0.0
            if saved is None:
                os.environ.pop("PP_SPEND_PROD_RUNS", None)
            else:
                os.environ["PP_SPEND_PROD_RUNS"] = saved

    def test_what_counts_as_running_a_build_or_render(self):
        yes = (["bash", "scripts/pulse_check_run.sh", "--pinned", "x"], ["python3", "-B", "tests/package/proof_ledger.py"],
               ["/home/ultron/protocol_pulse/scripts/pulse_check_run.sh"], ["python3.10", "pipeline/run_fresh.py"])
        no = (["grep", "-rn", "pulse_check_run.sh"], ["python3", "-m", "pytest", "tests/package/proof_ledger.py"],
              ["python3", "-c", "import proof_ledger"], ["less", "scripts/pulse_check_run.sh"], ["timeout", "9",
                                                                                                  "proof_ledger.py"])
        self.assertTrue(all(SC.runs_production(a) for a in yes))
        self.assertFalse(any(SC.runs_production(a) for a in no))


class TestOnePaidCallInFlight(Tmp):
    def test_a_second_paid_call_waits_for_the_first_to_settle(self):
        """B2, MUST-PASS: while the render's sign-off is in flight, the lock service's Scribe waits (it is reserved only
        after the sign-off settles); the builder's router refuses at once without its wait, and with a wait goes ahead
        after; the voice (characters, no dollars) is never held up. MUST-FAIL: past its wait, refused."""
        import threading
        marks = {}

        def signoff():
            with SC.charge("xai:grok-3-mini", 0.05, role="render", path=self.path) as c:
                marks["in"] = time.time()
                time.sleep(1.0)
                c.cost(0.004)
            marks["settled"] = time.time()
        t = threading.Thread(target=signoff)
        t.start()
        while "in" not in marks:
            time.sleep(0.01)
        k = SC.reserve("elevenlabs_tts:eleven_v4", 0.0, chars=100, path=self.path)   # the voice: not held up
        SC._release(k, self.path)
        r = self.router()
        with self.assertRaises(P.SpendLimit):
            r.call("coherence_verdict", "x" * 3000, 1200, 7)              # no wait (the default): refused at once
        k = SC.reserve("elevenlabs_stt:scribe_v1", 0.0078, path=self.path)
        reserved_at = time.time()
        t.join()
        self.assertGreaterEqual(reserved_at, marks["settled"] - 0.05)
        SC.settle(k, "elevenlabs_stt:scribe_v1", 0.0078, reported=False, path=self.path)
        self.assertEqual(self.asked, [])
        t = threading.Thread(target=signoff)
        marks.clear()
        t.start()
        while "in" not in marks:
            time.sleep(0.01)
        r = self.router(reserve_wait_s=10)
        r.reserve_poll_s = 0.05
        r.call("coherence_verdict", "x" * 3001, 1200, 8)                  # waits, then goes ahead
        self.assertGreaterEqual(time.time(), marks["settled"] - 0.05)
        self.assertEqual(len(self.asked), 1)
        t.join()
        marks.clear()
        t = threading.Thread(target=signoff)
        t.start()
        while "in" not in marks:
            time.sleep(0.01)
        with self.assertRaisesRegex(SC.CeilingRefused, "in flight"):
            SC.reserve("elevenlabs_stt:scribe_v1", 0.0078, path=self.path, wait_s=0.3)
        t.join()


class TestTheInputBound(Tmp):
    def test_a_paid_call_above_its_input_bound_is_never_sent(self):
        """B2, MUST-FAIL: under the one ledger a paid call's prompt is measured in bytes BEFORE it is sent: above
        INPUT_BOUND_BYTES it is not sent and nothing is reserved (no answer: never a pass); a free back-end of the same
        chain still answers it; at the bound it is sent."""
        r = self.router()
        with self.assertRaises(P.ProviderError) as cm:
            r.call("coherence_verdict", "é" * (P.INPUT_BOUND_BYTES // 2 + 1), 1200, 7)   # 2 bytes a character
        self.assertIn("input bound", str(cm.exception))
        self.assertEqual((self.asked, SC.status(self.path)["held"], SC.status(self.path)["spent"]), ([], 0.0, 0.0))
        r.call("coherence_verdict", "x" * (P.INPUT_BOUND_BYTES - 100), 1200, 7)
        self.assertEqual(len(self.asked), 1)
        big = {"text": "x", "images": ["y" * (P.IMAGE_BOUND[1] + 1)]}
        self.assertIn("image bound", P.input_over_bound(big))
        self.assertIsNone(P.input_over_bound({"text": "x", "images": ["y"] * P.IMAGE_BOUND[0]}))


class TestOneModuleBothBranches(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(LEAN_RELEASE), "lean-release not checked out here")
    def test_lean_release_carries_the_same_bytes(self):
        with open(os.path.join(REPO, "pipeline", "spend_ceiling.py"), "rb") as a, open(LEAN_RELEASE, "rb") as b:
            self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()
