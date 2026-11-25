#!/usr/bin/env python3
"""R1 (build 172, the owner's 15:25 ET Nov 24 order; lean-release only): the release's chargeable calls go through the
spend day's ONE ledger (pipeline/spend_ceiling.py, byte-identical to pp-lean's): reserved BEFORE the vendor is asked,
settled AFTER with the vendor's figure (the sign-off, xAI vision) or the metered one (Scribe by its audio, the voice by
its characters). Offline: every vendor is a stub, every ledger a temporary folder (conftest), no socket opens.
must-pass  each of the four call sites holds a reservation at the moment of its request and settles it after
must-fail  at the ceiling (or a stopped ledger) each call site is refused BEFORE its request (the stub never called)
must-fail  with the guard installed (scripts/lean/sitecustomize.py) a paid request with no reservation is refused,
           through urllib, requests and the ElevenLabs SDK (httpx), before any socket
must-fail  a paid client added to a module the render or the lock service imports, without the ledger, fails here
Run: cd <lean-release> && python3 -m pytest -q pipeline/test_lean_ceiling.py"""
import io
import json
import modulefinder
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import spend_ceiling as SC  # noqa: E402

PP_LEAN = "/home/ultron/worktrees/pp-lean/pipeline/spend_ceiling.py"
NOSOCK = '''
import socket as _socket
OPENED = []
def _blocked(*a, **k):
    OPENED.append(1)
    raise OSError("the network is blocked by this test")
_socket.socket.connect = _socket.socket.connect_ex = _socket.getaddrinfo = _socket.create_connection = _blocked
'''
_SAVED = {}


def setUpModule():
    import socket
    _SAVED.update(getaddrinfo=socket.getaddrinfo, create_connection=socket.create_connection,
                  connect=socket.socket.connect, connect_ex=socket.socket.connect_ex)

    def blocked(*a, **k):
        raise OSError("the network is blocked by this test")
    socket.getaddrinfo = socket.create_connection = blocked
    socket.socket.connect = socket.socket.connect_ex = blocked


def tearDownModule():
    import socket
    socket.getaddrinfo, socket.create_connection = _SAVED["getaddrinfo"], _SAVED["create_connection"]
    socket.socket.connect, socket.socket.connect_ex = _SAVED["connect"], _SAVED["connect_ex"]


class Sites(unittest.TestCase):
    """The four call sites, each driven to its vendor request with a stub transport that notes whether a reservation
    was held at that moment."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lean_ceiling_")
        self.held = []                                   # one entry per request: the reservation keys held then
        import outside_spend as OS
        for p in (mock.patch.object(OS, "LEDGER", os.path.join(self.tmp, "outside.jsonl")),):
            p.start()
            self.addCleanup(p.stop)

    def note(self):
        self.held.append(tuple(getattr(SC._tl, "keys", ())))

    def ledger(self):
        return SC.read(SC.ledger_path())

    # the four sites
    def scribe(self):
        import second_recogniser as SR
        src = os.path.join(self.tmp, "w.mp4")
        open(src, "wb").close()

        def run(cmd, *a, **k):
            if cmd[0] == "ffprobe":
                return types.SimpleNamespace(stdout="40.0\n", returncode=0)
            open(cmd[cmd.index("-ar") + 2], "wb").close()
            return types.SimpleNamespace(stdout="", returncode=0)

        def urlopen(req, *a, **k):
            self.note()
            return io.BytesIO(json.dumps({"text": "hi", "words": [{"text": "hi", "start": 0.1, "end": 0.3}]}).encode())
        relay = types.ModuleType("relay")
        relay.get_key = lambda name: "k"
        with mock.patch.object(SR.subprocess, "run", run), mock.patch.object(SR.urllib.request, "urlopen", urlopen), \
                mock.patch.dict(sys.modules, {"relay": relay}):
            return SR.scribe_words(src)

    def signoff(self):
        import signoff

        def post(url, **k):
            self.note()
            reply = {"choices": [{"message": {"content": "1. too short"}}], "usage": {"cost_in_usd_ticks": 40_130_000}}
            return mock.Mock(**{"json.return_value": reply, "raise_for_status.return_value": None})
        with mock.patch("requests.post", post), mock.patch.object(signoff, "get_key", lambda n: "k"), \
                mock.patch.object(signoff, "_load_history", lambda: []), \
                mock.patch.object(signoff, "_load_reference", lambda: "ref"):
            return signoff.generate_signoff("topic", ["A", "B"], "seg", max_rounds=1)

    def vision(self):
        import visual_check as VC
        img = os.path.join(self.tmp, "sheet.jpg")
        with open(img, "wb") as f:
            f.write(b"\xff\xd8\xff\xd9")

        def urlopen(req, *a, **k):
            self.note()
            return io.BytesIO(json.dumps({"choices": [{"message": {"content": "{}"}}],
                                          "usage": {"cost_in_usd_ticks": 300_000_000}}).encode())
        with mock.patch.object(VC, "_xai_key", lambda: "k"), mock.patch("urllib.request.urlopen", urlopen):
            return VC._call_xai(img, "the checklist", "xai:grok-4.7", 60)

    def voice(self, text="Bitcoin held its ground today."):
        import credit_rings  # noqa: F401  (cv2 before sys.modules is patched)
        import vo
        seg = os.path.join(self.tmp, "seg")
        os.makedirs(seg, exist_ok=True)
        with open(os.path.join(seg, "edl.json"), "w") as f:
            json.dump({"vo": {"intro": text}, "clips": []}, f)
        test = self

        class Client:
            def __init__(self, api_key):
                self.text_to_speech = self

            def convert(self, **k):
                def stream():                            # the request is made as the stream is read
                    test.note()
                    yield b"\0\0" * 22050
                return stream()
        el = types.ModuleType("elevenlabs")
        el.ElevenLabs = Client
        paths = {"vo_dir": os.path.join(seg, "vo_audio"), "edl_json": os.path.join(seg, "edl.json")}
        with mock.patch.object(vo, "resolve_paths", lambda d: paths), mock.patch.object(vo, "get_key", lambda n: "v"), \
                mock.patch.dict(sys.modules, {"elevenlabs": el}):
            vo.generate_vo(seg)

    def test_each_site_holds_a_reservation_at_its_request_and_settles_after(self):
        """MUST-PASS: Scribe (metered: 40 s at $0.012/min = $0.008), the sign-off (xAI's 40,130,000 ticks = $0.004013),
        xAI vision ($0.03), the voice (its characters, $0 in "chars" mode): each request ran with a reservation held,
        and the ledger holds the settled figure and no reservation after."""
        self.scribe()
        with self.assertRaises(RuntimeError):                # "1. too short": no valid line after its one round
            self.signoff()
        self.vision()
        self.voice()
        self.assertEqual(len(self.held), 4)
        self.assertTrue(all(len(k) == 1 for k in self.held), self.held)
        d = self.ledger()
        self.assertEqual(d["reserved"], {})
        bb = d["by_backend"]
        self.assertAlmostEqual(bb["elevenlabs_stt:scribe_v1"]["usd_estimate"], 0.008, places=4)
        self.assertNotIn("usd_reported", bb["elevenlabs_stt:scribe_v1"])          # metered, not vendor-reported
        self.assertAlmostEqual(bb["xai:grok-3-mini"]["usd_reported"], 0.004013, places=6)
        self.assertAlmostEqual(bb["xai_vision:grok-4.7"]["usd_reported"], 0.03, places=6)
        self.assertEqual(bb["elevenlabs_tts:eleven_v4"]["usd_estimate"], 0.0)
        self.assertEqual(SC.status()["voice"]["chars"], len("Bitcoin held its ground today."))
        self.assertIsNone(d.get("stop"))

    def test_at_the_ceiling_each_site_is_refused_before_its_request(self):
        """MUST-FAIL: the day at $1.50: Scribe, the sign-off and vision are refused before their request; a stopped
        ledger refuses the voice too (its dollars are $0, its stop is not)."""
        SC.seed({"builder:pp-selectid": 1.50})
        for site in (self.scribe, self.signoff, self.vision):
            with self.assertRaises(SC.CeilingRefused, msg=site.__name__):
                site()
        d = self.ledger()
        d["stop"] = {"why": "test: the ledger is stopped"}
        SC.write(SC.ledger_path(), d)
        with self.assertRaises(SC.CeilingRefused):
            self.voice()
        self.assertEqual(self.held, [])                     # no transport was reached
        self.assertEqual(self.ledger()["reserved"], {})

    def test_before_the_ledger_is_initialized_each_site_is_refused_before_its_request(self):
        """B1 (a) (08:38 ET Nov 25), MUST-FAIL: the spend day's ledger not yet created by the launch's ledger-init (the
        lock service or the render started first): Scribe, the sign-off, vision and the voice are each refused before
        their request."""
        os.remove(SC.ledger_path())                          # conftest initialized it: gone, as before the ledger-init
        for site in (self.scribe, self.signoff, self.vision, self.voice):
            with self.assertRaisesRegex(SC.CeilingRefused, "not initialized", msg=site.__name__):
                site()
        self.assertEqual(self.held, [])

    def test_a_reply_without_xai_s_figure_stops_the_ledger(self):
        """The sign-off's reply with no cost_in_usd_ticks: its cost is unknown: the reservation stays, the ledger stops."""
        import signoff

        def post(url, **k):
            reply = {"choices": [{"message": {"content": "1. too short"}}], "usage": {"total_tokens": 900}}
            return mock.Mock(**{"json.return_value": reply, "raise_for_status.return_value": None})
        with mock.patch("requests.post", post), mock.patch.object(signoff, "get_key", lambda n: "k"), \
                mock.patch.object(signoff, "_load_history", lambda: []), \
                mock.patch.object(signoff, "_load_reference", lambda: "ref"):
            with self.assertRaises(RuntimeError):
                signoff.generate_signoff("topic", ["A", "B"], "seg", max_rounds=1)
        st = SC.status()
        self.assertTrue(st["stop"])
        self.assertAlmostEqual(st["held"], SC.SIGNOFF_RESERVE_USD, places=6)


class TheGuard(unittest.TestCase):
    def test_no_paid_client_reaches_a_paid_endpoint_without_a_reservation(self):
        """MUST-FAIL: a process started as the launch starts the render and the lock service (PYTHONPATH=scripts/lean,
        PP_SPEND_CEILING=1): urllib, requests and the ElevenLabs SDK (httpx) are each refused before any socket."""
        code = NOSOCK + textwrap.dedent('''
            import spend_ceiling as SC, urllib.request, requests
            out = []
            def tryit(name, fn):
                try:
                    fn()
                    out.append(name + " REACHED")
                except SC.CeilingRefused:
                    out.append(name + " REFUSED")
                except Exception as e:
                    out.append(name + " OTHER " + type(e).__name__)
            tryit("urllib", lambda: urllib.request.urlopen(urllib.request.Request(
                "https://api.elevenlabs.io/v1/speech-to-text", data=b"x"), timeout=2))
            tryit("requests", lambda: requests.post("https://api.x.ai/v1/chat/completions", json={}, timeout=2))
            from elevenlabs import ElevenLabs
            tryit("elevenlabs-sdk", lambda: b"".join(ElevenLabs(api_key="test").text_to_speech.convert(
                voice_id="v", text="hi", model_id="eleven_v4", output_format="pcm_22050")))
            print(" | ".join(out), "| SOCKETS", len(OPENED))
        ''')
        env = dict(os.environ, PP_SPEND_CEILING="1", PYTHONPATH=os.pathsep.join(
            [os.path.join(REPO, "scripts", "lean"), PIPELINE]))
        p = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(p.returncode, 0, p.stderr[-800:])
        self.assertEqual(p.stdout.strip(), "urllib REFUSED | requests REFUSED | elevenlabs-sdk REFUSED | SOCKETS 0")

    def test_without_the_launch_s_switch_the_guard_is_not_installed(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "scripts", "lean"))
        env.pop("PP_SPEND_CEILING", None)
        p = subprocess.run([sys.executable, "-B", "-c", "import sys; print('spend_ceiling' in sys.modules)"],
                           capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(p.stdout.strip(), "False")


PAID_CLIENT = re.compile(r"api\.x\.ai|api\.openai\.com|api\.anthropic\.com|generativelanguage|api\.elevenlabs\.io|"
                         r"^\s*(?:from|import)\s+(?:elevenlabs|openai|anthropic)\b", re.M)
GUARDED = {"pipeline/second_recogniser.py", "pipeline/signoff.py", "pipeline/visual_check.py", "pipeline/vo.py"}
FREE_ONLY = {"pipeline/preflight.py": "https://api.elevenlabs.io/v1/user/subscription"}   # the plan's quota: a free read
LISTS_ONLY = {"pipeline/spend_ceiling.py"}               # names the paid hosts in its table (the guard's): no client
UNCALLED = {"video_pipeline_v3/relay.py"}                # call_llm (Anthropic, xAI, Gemini): a paid client nothing the
#   render or the lock service imports calls (asserted below); the guard refuses it at run time if anything ever does
CALLS_UNCALLED = re.compile(r"\bcall_llm\(")
ENTRIES = {"render": ["pipeline/preflight.py", "pipeline/run_fresh.py", "pipeline/telegram.py", "pipeline/story_ledger.py",
                      "scripts/integrator/check_pin_only.py"],
           "lock service": ["pipeline/lock_precheck.py"]}


class _Finder(modulefinder.ModuleFinder):
    """modulefinder that takes a module it cannot resolve (a namespace package outside the repo) as not found."""
    def find_module(self, name, path, parent=None):
        try:
            return super().find_module(name, path, parent)
        except AttributeError:
            raise ImportError(name) from None


class EveryPaidClientIsKnown(unittest.TestCase):
    def test_every_module_the_render_and_the_lock_service_import_that_reaches_a_vendor_is_charged(self):
        """MUST-FAIL: the static import closure (modulefinder: it reads, never runs) of the render's and the lock
        service's entry points; every module in it that names a paid endpoint or a vendor SDK is either one of the four
        charged call sites (each with spend_ceiling.charge at its request) or reads only a free endpoint. A paid client
        added anywhere they import, without the ledger, fails here (and the guard refuses it at run time)."""
        import sysconfig                                 # the repo's folders and the standard library only: a
        std = sysconfig.get_paths()                      # third-party package is "not found" (only the repo's own
        path = [PIPELINE, os.path.join(REPO, "scripts", "integrator"), os.path.join(REPO, "scripts"),   # modules count)
                os.path.join(REPO, "video_pipeline_v3"), REPO, std["stdlib"], std["platstdlib"],
                os.path.join(std["platstdlib"], "lib-dynload")]
        reached = set()
        for prog, entries in ENTRIES.items():
            for e in entries:
                mf = _Finder(path=path)
                mf.run_script(os.path.join(REPO, e))
                for m in mf.modules.values():
                    f = os.path.abspath(m.__file__ or "")
                    if f.startswith(REPO + os.sep) and f.endswith(".py"):
                        reached.add(os.path.relpath(f, REPO))
        paid = {f for f in reached if PAID_CLIENT.search(open(os.path.join(REPO, f)).read())}
        self.assertEqual(paid, GUARDED | set(FREE_ONLY) | LISTS_ONLY | UNCALLED, sorted(paid))
        callers = {f for f in reached - UNCALLED if CALLS_UNCALLED.search(open(os.path.join(REPO, f)).read())}
        self.assertEqual(callers, set(), "a module the render or the lock service imports calls relay.call_llm")
        for f in GUARDED:
            self.assertIn("spend_ceiling.charge(", open(os.path.join(REPO, f)).read(), f)
        for f, url in FREE_ONLY.items():
            urls = {u for u in re.findall(r"https://[a-z.]+/[\w/.-]*", open(os.path.join(REPO, f)).read())
                    if PAID_CLIENT.search(u)}                      # its URLs on a vendor's host
            self.assertEqual(urls, {url})
            self.assertFalse(SC.is_paid(url))


class OneModule(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(PP_LEAN), "pp-lean not checked out here")
    def test_pp_lean_carries_the_same_bytes(self):
        with open(os.path.join(PIPELINE, "spend_ceiling.py"), "rb") as a, open(PP_LEAN, "rb") as b:
            self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()
