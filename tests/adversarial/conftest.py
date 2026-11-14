"""tests/adversarial: the adversarial test wall (red-team 2026-11-11; session pipeline_pp_tests).

CPU ONLY, NO NETWORK. GPU0 is leased to the live run and GPU1 is quarantined, and nothing may reach Telegram, the
vision gateway, a model server or YouTube. The guards below make every such path impossible for the code of THIS
directory, and only for it (integrator merge audit 2026-11-12: they used to stay installed for the whole process, so
`pytest tests/` imposed them on every other suite):
  - CUDA_VISIBLE_DEVICES is emptied (segment_v1/qa_gates.py sets it to "0" at import: it is imported here first and
    the variable emptied again; the function fixture empties it before and after every test), so no CUDA library sees
    a device; test_f0 checks that no module this suite imported initialised CUDA or sets the variable unexpectedly;
  - no Whisper model can load: the pipeline loads Whisper only through law L-r's GPU0 lease (pipeline/gpu0.py:
    gpu0.whisper -> Model.get -> require), which refuses this process (CUDA_VISIBLE_DEVICES is '' and it holds no
    lease) with a Gpu0Stop, a BaseException; and faster_whisper is replaced by a stub whose WhisperModel raises (and
    records the attempt) for any load outside gpu0; a test that needs a transcript injects it
    (qa_gates.whisper_segment, gate_g18's transcriber, select_passages._whisper_transcribe);
  - no socket can connect, connect_ex, sendto or sendmsg over AF_INET / AF_INET6 (loopback included: a real Ollama
    listens on 127.0.0.1) and no name can be resolved (getaddrinfo, gethostbyname[_ex], gethostbyaddr): a missing
    fake or a regressed send path raises NetworkBlocked (a BaseException, so no `except Exception` in the code under
    test and no pytest.raises(RuntimeError) in a test can absorb it);
  - a child process may only be one of ALLOWED_PROGRAMS (local tools: ffmpeg / ffprobe on local files, git on this
    repository, read-only nvidia-smi queries) or a Python interpreter, which always starts with child_guard/ first on
    its PYTHONPATH so that its sitecustomize refuses the network exactly like this process (the one way around it is
    the moments exam's documented opt-in PP_MOMENTS_ALLOW_NETWORK=1 for a model-backed gate); anything else (yt-dlp,
    curl, ...) and a Python child started with -I / -S / -E raise NetworkBlocked before they start.
Model / vision replies are injected at their one HTTP seam (LocalLLM._post, visual_check._call), the Telegram sender at
deliver_run's `send`, yt-dlp by adv_helpers.FakeYtDlp.

Scope: the guards are installed when this file is imported (the test modules import pipeline code at collection),
removed when collection finishes (pytest_collection_finish), and re-installed by a MODULE-scoped autouse fixture
around every module of this directory (autouse fixtures of a scope run before that scope's other fixtures, so the
module fixtures that build media run guarded too); each removal restores exactly what was there before. What cannot
be undone in-process: a module imported during collection keeps what it bound at import (none of the modules this
suite imports binds faster_whisper or a socket function at import; test_f0 checks the CUDA side).

At session end a read-only nvidia-smi query fails the session if this process is a CUDA compute app. It is an extra
probe, not the guarantee (the guarantee is that no device is visible): it cannot see memory held and released
earlier, and it is skipped when nvidia-smi is unavailable.

Run: cd <worktree> && python3 -m pytest tests/adversarial -q
"""
import os
import socket
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PATHS = (os.path.join(REPO, "segment_v1"), os.path.join(REPO, "pipeline"), HERE)
ALLOWED_PROGRAMS = {"ffmpeg", "ffprobe", "git", "nvidia-smi"}    # local tools; Python children: guarded, below
PYTHONS = {os.path.basename(sys.executable), "python3", "python"}
CHILD_GUARD = os.path.join(HERE, "child_guard")                     # its sitecustomize.py guards a Python child

class _NoWhisper:
    """faster_whisper.WhisperModel stand-in: any attempt to load a model is recorded and refused."""
    attempts = []

    def __init__(self, *a, **k):
        _NoWhisper.attempts.append((a, k))
        raise RuntimeError("tests/adversarial: Whisper (GPU) is forbidden in this suite")


_FW = types.ModuleType("faster_whisper")
_FW.WhisperModel = _NoWhisper
_INET = (socket.AF_INET, socket.AF_INET6)
_REAL = {"connect": socket.socket.connect, "connect_ex": socket.socket.connect_ex,
         "sendto": socket.socket.sendto, "sendmsg": socket.socket.sendmsg,
         "getaddrinfo": socket.getaddrinfo, "gethostbyname": socket.gethostbyname,
         "gethostbyname_ex": socket.gethostbyname_ex, "gethostbyaddr": socket.gethostbyaddr,
         "popen_init": subprocess.Popen.__init__}


def _blocked(what):
    raise NetworkBlocked(f"tests/adversarial: network is disabled in this suite ({what})")


def _guard_inet(name):
    real = _REAL[name]

    def guarded(self, *a, **k):
        if self.family in _INET:
            target = a[-1] if (name in ("sendto", "sendmsg") and a) else (a[0] if a else "?")
            _blocked(f"{name} to {target!r}")
        return real(self, *a, **k)
    guarded.__name__ = f"_no_{name}"
    return guarded


def _guard_lookup(name):
    def guarded(host, *a, **k):
        _blocked(f"{name}({host!r})")
    guarded.__name__ = f"_no_{name}"
    return guarded


def _program(args):
    a = args[0] if isinstance(args, (list, tuple)) and args else args
    a = os.fsdecode(os.fspath(a))
    return os.path.basename(a.split()[0] if a.strip() else a)


def _guarded_popen_init(self, args, *a, **k):
    prog = _program(args)
    if prog in PYTHONS:
        # a child interpreter does not inherit this process's socket patches (integrator audit cycle 2, P0): it
        # starts with child_guard/ first on its PYTHONPATH, so its sitecustomize refuses the network too; a flag that
        # would skip that (-I isolated, -S no site, -E no environment) is refused, as is an env passed positionally
        argv = list(args) if isinstance(args, (list, tuple)) else str(args).split()
        opts = []
        for x in (os.fsdecode(os.fspath(v)) for v in argv[1:]):
            if not x.startswith("-") or x.startswith("--") or x in ("-c", "-m"):
                break
            opts.append(x)
        if any(set(o[1:]) & set("ISE") for o in opts) or len(a) > 9:
            raise NetworkBlocked(f"tests/adversarial: a Python child without the network guard is not allowed "
                                 f"({argv[:3]!r})")
        env = dict(os.environ if k.get("env") is None else k["env"])
        env["PYTHONPATH"] = CHILD_GUARD + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        k["env"] = env
    elif prog not in ALLOWED_PROGRAMS:
        raise NetworkBlocked(f"tests/adversarial: child process {prog!r} is not allowed in this suite "
                             f"(allowed: {sorted(ALLOWED_PROGRAMS)}, and Python children with the network guard)")
    return _REAL["popen_init"](self, args, *a, **k)


_GUARDED = {"connect": _guard_inet("connect"), "connect_ex": _guard_inet("connect_ex"),
            "sendto": _guard_inet("sendto"), "sendmsg": _guard_inet("sendmsg")}
_LOOKUPS = {n: _guard_lookup(n) for n in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr")}
_SAVED = {}


def install():
    """The guards on (idempotent). Saves what it replaces, once, so remove() restores exactly that."""
    if _SAVED:
        return
    _SAVED["fw"] = sys.modules.get("faster_whisper")
    _SAVED["cuda"] = os.environ.get("CUDA_VISIBLE_DEVICES")
    _SAVED["paths"] = [p for p in PATHS if p not in sys.path]
    sys.path[:0] = _SAVED["paths"]
    sys.modules["faster_whisper"] = _FW
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for name, fn in _GUARDED.items():
        setattr(socket.socket, name, fn)
    for name, fn in _LOOKUPS.items():
        setattr(socket, name, fn)
    subprocess.Popen.__init__ = _guarded_popen_init


def remove():
    """The guards off: everything install() replaced is put back as it was."""
    if not _SAVED:
        return
    for name in _GUARDED:
        setattr(socket.socket, name, _REAL[name])
    for name in _LOOKUPS:
        setattr(socket, name, _REAL[name])
    subprocess.Popen.__init__ = _REAL["popen_init"]
    if sys.modules.get("faster_whisper") is _FW:
        if _SAVED["fw"] is None:
            del sys.modules["faster_whisper"]
        else:
            sys.modules["faster_whisper"] = _SAVED["fw"]
    if _SAVED["cuda"] is None:
        os.environ.pop("CUDA_VISIBLE_DEVICES", None)
    else:
        os.environ["CUDA_VISIBLE_DEVICES"] = _SAVED["cuda"]
    for p in _SAVED["paths"]:                 # the one entry install() put in front (another module's own
        if p in sys.path:                     # insertion of the same directory stays)
            sys.path.remove(p)
    _SAVED.clear()


install()                                     # collection imports pipeline code: it is imported under the guards
from adv_helpers import NetworkBlocked  # noqa: E402  (a BaseException: see adv_helpers; the guards raise it)
import qa_gates  # noqa: E402,F401  (it sets CUDA_VISIBLE_DEVICES='0' at import: load it first, then undo that
os.environ["CUDA_VISIBLE_DEVICES"] = ""          # before any test module is collected; modules are cached)

import pytest  # noqa: E402


def pytest_collection_finish(session):
    """Collection is over: the other suites of this session run without this directory's guards."""
    remove()


@pytest.fixture(autouse=True, scope="module")
def _adversarial_guards():
    """Every module of this directory runs guarded (its module fixtures included), and leaves nothing behind."""
    install()
    yield
    remove()


@pytest.fixture(autouse=True)
def _cpu_only():
    """Before and after every test: no CUDA device visible (qa_gates re-sets it to '0' when it is imported)."""
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    yield
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


@pytest.fixture
def whisper_attempts():
    """The faster_whisper loads attempted during one test (each one was refused by the stub). A pipeline load stops
    at the GPU0 lease before the stub (law L-r), so it is not listed here: it raises gpu0.LeaseMissing."""
    start = len(_NoWhisper.attempts)
    yield lambda: _NoWhisper.attempts[start:]


def pytest_sessionfinish(session, exitstatus):
    """Read-only extra probe: this process must not be listed as a CUDA compute app (only this process's own pid
    is compared, so another job's GPU use on a shared host can never fail this suite)."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return
    if str(os.getpid()) in {line.strip() for line in out.splitlines()}:
        session.exitstatus = 1
        print(f"\nGPU USED by the adversarial suite (pid {os.getpid()} listed by nvidia-smi): FAIL")
