"""The suite's own guard (order: no GPU at all; GPU0 is leased to the live run, GPU1 is quarantined; nothing reaches
the network): no module this suite imports may expose a device unnoticed, no CUDA runtime is initialised, every
Whisper load is refused (at law L-r's GPU0 lease, or at the faster_whisper stub, which records it), no socket / name
lookup / network tool gets out, and the guards are this directory's only (conftest.py)."""
import ast
import importlib.util
import os
import re
import shutil
import socket
import subprocess
import sys

import pytest

import adv_helpers as H
import conftest as CF

# modules that assign CUDA_VISIBLE_DEVICES, reviewed: qa_gates sets "0" AT IMPORT (line 22); conftest imports it
# first, under the guards, and empties the variable again before anything is collected
KNOWN_CUDA_SETTERS = {"qa_gates"}
_SETTER = re.compile(r"""environ\s*\[\s*['"]CUDA_VISIBLE_DEVICES['"]\s*\]\s*=|environ\.(setdefault|update)\([^)]*"""
                     r"""CUDA_VISIBLE_DEVICES|putenv\(\s*['"]CUDA_VISIBLE_DEVICES""")


def _imported_names():
    """Every top-level module name an import statement of this suite names (test modules and helpers)."""
    names = set()
    for f in os.listdir(H.HERE):
        if f.endswith(".py"):
            for node in ast.walk(ast.parse(open(os.path.join(H.HERE, f)).read())):
                if isinstance(node, ast.Import):
                    names |= {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    names.add(node.module.split(".")[0])
    return names


def _resolve(name):
    """The file `import <name>` gives THIS suite: the module already imported under that name, else what the suite's
    sys.path finds (a package resolves to its __init__.py, scanned like any module; a compiled or stub module without
    a .py file is not scanned). Never a bare file-name match: `import conftest` is this directory's own conftest
    (pytest's), and matching the name against pipeline/ blamed pipeline/conftest.py (law L-r's teardown, on the
    release line since Nov 12), which this suite never imports (integrator cycle 2, 2026-11-14)."""
    m = sys.modules.get(name)
    f = getattr(m, "__file__", None) if m is not None else None
    if m is None:
        spec = importlib.util.find_spec(name)
        f = spec.origin if spec is not None else None
    return os.path.realpath(f) if f and f.endswith(".py") else None


def test_no_module_this_suite_imports_sets_cuda_visible_devices_unreviewed():
    """Static (integrator audit: the old check read back the value the fixture had just written): every pipeline /
    segment_v1 module this suite imports is scanned for code that sets CUDA_VISIBLE_DEVICES. A setter not reviewed
    here (KNOWN_CUDA_SETTERS) could expose GPU0 in the middle of a test, so it fails until it is reviewed.
    INTENTIONALLY BRITTLE: a new import of a module that sets the variable fails here on purpose; review where it
    sets it (at import or in a function the suite calls) before adding it to KNOWN_CUDA_SETTERS. Nothing is skipped
    silently (integrator batch 78, glm): a name that has a pipeline / segment_v1 file but resolves elsewhere or to
    nothing (no .py behind it) fails, listed, except the suite's own conftest."""
    roots = tuple(os.path.join(os.path.realpath(H.REPO), d) + os.sep for d in ("pipeline", "segment_v1"))
    own = os.path.realpath(os.path.join(H.HERE, "conftest.py"))
    H.control(_resolve("conftest") == own, f"the suite's `import conftest` is its own conftest: {_resolve('conftest')}")
    names, found = _imported_names(), {}
    for name in names:
        f = _resolve(name)
        if f and f.startswith(roots):
            found[name] = f
    H.control(len(found) >= 15, f"the suite's pipeline imports were found: {sorted(found)}")
    unscanned = {n for n in names - set(found)          # a module file or a package (glm, batch 78)
                 if any(os.path.exists(os.path.join(r, n + ".py")) or os.path.exists(os.path.join(r, n, "__init__.py"))
                        for r in roots)}
    assert unscanned <= {"conftest"}, f"pipeline / segment_v1 modules the scan cannot see: {sorted(unscanned)}"
    setters = {n for n, p in found.items() if _SETTER.search(open(p).read())}
    assert setters == KNOWN_CUDA_SETTERS, sorted(setters)


def test_no_cuda_runtime_was_initialised_by_any_import():
    """Runtime: after collection (every test module imported, qa_gates included): no CUDA runtime is initialised in
    this process and none of the libraries that would load a model on the GPU is imported."""
    torch = sys.modules.get("torch")
    assert torch is None or not torch.cuda.is_initialized(), "torch initialised CUDA in the test process"
    assert "ctranslate2" not in sys.modules, "ctranslate2 (faster_whisper's backend) was imported"
    assert sys.modules["faster_whisper"].WhisperModel is CF._NoWhisper
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""


def test_no_network_connection_can_be_opened():
    """Telegram, the vision gateway and a model server are unreachable from this suite (a missing fake or a
    regressed send path raises instead of sending): IPv4 / IPv6, loopback included (Ollama listens on 127.0.0.1)."""
    import urllib.request
    from adv_helpers import NetworkBlocked
    addrs = [("127.0.0.1", 11434), ("192.0.2.1", 443)]           # literal addresses
    try:                                                         # IPv6 only where the kernel has it (else socket()
        socket.socket(socket.AF_INET6).close()                   # itself fails before any connect)
        addrs.append(("::1", 11434))
    except OSError:
        pass
    for addr in addrs:
        with pytest.raises(NetworkBlocked, match="network is disabled"):
            socket.create_connection(addr, timeout=2)
        s = socket.socket(socket.AF_INET6 if ":" in addr[0] else socket.AF_INET)
        try:
            with pytest.raises(NetworkBlocked, match="network is disabled"):
                s.connect(addr)
            with pytest.raises(NetworkBlocked, match="network is disabled"):
                s.connect_ex(addr)
        finally:
            s.close()
    with pytest.raises(NetworkBlocked, match="network is disabled"):
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
    try:                                                   # what a production `except Exception` would do
        socket.create_connection(("127.0.0.1", 9), timeout=2)
    except Exception:                                      # noqa: BLE001
        pytest.fail("the network guard was absorbed by `except Exception`")
    except NetworkBlocked:
        pass
    else:                                                  # integrator audit: a silent success must not pass
        pytest.fail("a connection to 127.0.0.1:9 was opened")


def test_no_datagram_and_no_name_lookup_gets_out():
    """UDP and name resolution are covered too (integrator audit: connect alone left sendto and DNS open)."""
    from adv_helpers import NetworkBlocked
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with pytest.raises(NetworkBlocked, match="network is disabled"):
            u.sendto(b"x", ("192.0.2.1", 53))
        with pytest.raises(NetworkBlocked, match="network is disabled"):
            u.sendmsg([b"x"], [], 0, ("192.0.2.1", 53))
    finally:
        u.close()
    for fn, args in ((socket.getaddrinfo, ("api.telegram.org", 443)), (socket.gethostbyname, ("example.com",)),
                     (socket.gethostbyname_ex, ("example.com",)), (socket.gethostbyaddr, ("192.0.2.1",)),
                     (socket.getnameinfo, (("192.0.2.1", 443), 0))):        # the two reverse lookups (batch 78)
        with pytest.raises(NetworkBlocked, match="network is disabled"):
            fn(*args)


def test_a_network_tool_cannot_be_started():
    """A child process is outside this process's socket guard, so only local tools may start: yt-dlp / curl through
    any subprocess entry point are refused before they run; ffmpeg still runs (control)."""
    from adv_helpers import NetworkBlocked
    for cmd in (["yt-dlp", "--version"], ["curl", "-sI", "http://192.0.2.1"], "wget http://192.0.2.1"):
        quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        for call, kw in ((subprocess.run, quiet), (subprocess.check_output, {"stderr": subprocess.DEVNULL}),
                         (subprocess.Popen, quiet), (subprocess.call, quiet)):
            with pytest.raises(NetworkBlocked, match="not allowed in this suite"):
                call(cmd, shell=isinstance(cmd, str), **kw)
    H.control(subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0, "ffmpeg runs (allowed)")


def test_a_python_child_refuses_the_network_too():
    """A child interpreter does not inherit this process's patches (integrator audit cycle 2, P0): the suite starts
    every Python child with child_guard/ on its PYTHONPATH, so the child's own sockets and lookups are guarded; the
    exam's documented opt-in (PP_MOMENTS_ALLOW_NETWORK=1) is the only way around it, and a flag that would skip the
    guard is refused. Nothing here touches the network: a numeric getaddrinfo needs none."""
    from adv_helpers import NetworkBlocked
    probe = ("import socket; print(socket.socket.connect.__name__, socket.socket.sendto.__name__, "
             "socket.getaddrinfo.__name__, socket.gethostbyaddr.__name__, socket.getnameinfo.__name__)")
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=60)
    assert out.stdout.split() == ["_child_no_connect", "_child_no_sendto", "_child_no_getaddrinfo",
                                  "_child_no_gethostbyaddr", "_child_no_getnameinfo"], out
    r = subprocess.run([sys.executable, "-c", "import socket; socket.getaddrinfo('127.0.0.1', 1)"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "network is disabled" in r.stderr, r.stderr[-400:]
    allowed = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=60,
                             env=dict(os.environ, PP_MOMENTS_ALLOW_NETWORK="1"))
    assert allowed.stdout.split() == ["connect", "sendto", "getaddrinfo", "gethostbyaddr", "getnameinfo"], allowed
    for flags in (["-I"], ["-S"], ["-E"], ["-IS"], ["-u", "-E"]):
        with pytest.raises(NetworkBlocked, match="without the network guard"):
            subprocess.run([sys.executable, *flags, "-c", "pass"], capture_output=True)


def test_keys_are_read_only_by_name_through_the_pipelines_loader():
    """Secrets (integrator batch 78, PP-E31; the detection glm asked for): no .py file of this suite names a key file
    (no string constant ends in, or contains a path to, the project's key file name), and the frontier baseline's
    key path is the pipeline's loader: relay.get_key of the main tree's video_pipeline_v3, opening no file itself.
    Nothing is loaded and no key is read here: the check is on the source."""
    import inspect
    from baselines import frontier_blind as FB
    key_file = "." + "env"                               # spelled apart, so this file names none either
    named, scanned = [], 0
    for root, dirs, files in os.walk(H.HERE):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in (f for f in files if f.endswith(".py")):
            p, scanned = os.path.join(root, f), scanned + 1
            for node in ast.walk(ast.parse(open(p).read())):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
                        node.value.endswith(key_file) or "/" + key_file in node.value):
                    named.append(f"{os.path.relpath(p, H.HERE)}:{node.lineno}")
    H.control(scanned >= 20, f"the scan walked the suite's .py files ({scanned})")
    assert named == [], f"a key file is named in the suite (read keys by name through relay.get_key): {named}"
    assert FB.KEY_LOADER == "/home/ultron/protocol_pulse/video_pipeline_v3/relay.py" and os.path.isfile(FB.KEY_LOADER)
    src = inspect.getsource(FB._key)
    assert ".get_key" in src and "open(" not in src, "frontier_blind._key must only call relay.get_key"


def test_the_guards_are_this_directorys_only():
    """conftest.remove() restores exactly what install() replaced (other suites of a session run unguarded), and
    install() puts every guard back; the module fixture re-installs them around each module of this directory."""
    real_connect = CF._REAL["connect"]
    H.control(socket.socket.connect is not real_connect, "the guards are on inside this module")
    added, before = list(CF._SAVED["paths"]), list(sys.path)
    CF.remove()
    try:
        assert socket.socket.connect is real_connect and socket.getaddrinfo is CF._REAL["getaddrinfo"]
        assert subprocess.Popen.__init__ is CF._REAL["popen_init"]
        assert sys.modules.get("faster_whisper") is not CF._FW and CF._SAVED == {}
        assert all(sys.path.count(p) == before.count(p) - 1 for p in added), "the suite's sys.path entries stayed"
    finally:
        CF.install()
    assert socket.socket.connect is not real_connect and sys.modules["faster_whisper"] is CF._FW
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""


def test_every_whisper_load_is_refused_and_recorded(whisper_attempts, tmp_path):
    """No Whisper model loads in this suite, by either way in (integrator cycle 2: law L-r reached the release line
    after this suite's first base):
    - the pipeline's way: every load AND every use goes through gpu0 (gpu0.whisper -> Model.get -> require), which
      refuses a process whose CUDA_VISIBLE_DEVICES is not '0' or that lacks the GPU0 lease; this suite has neither.
      G18's default transcriber is built lazily (constructing it loads nothing), so it is refused at its first use,
      before faster_whisper is reached; the refusal is a Gpu0Stop, a BaseException that no `except Exception` absorbs;
    - a direct faster_whisper load (outside gpu0): the stub refuses it and records the attempt."""
    import faster_whisper
    import gpu0
    import word_diff
    with pytest.raises(RuntimeError, match="forbidden"):
        faster_whisper.WhisperModel("large-v3", device="cuda", compute_type="float16")
    H.control(len(whisper_attempts()) == 1, "the direct load reached the stub and was recorded")
    wav = str(tmp_path / "tone.wav")                   # preconditions (audit cycle 2): the transcriber runs ffmpeg too
    H.control(shutil.which("ffmpeg") is not None, "ffmpeg is on PATH (Transcriber.span runs it before the model)")
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-ar", "16000",
                        wav], capture_output=True, text=True, timeout=60)
    H.control(r.returncode == 0 and os.path.exists(wav) and os.path.getsize(wav) > 0,
              f"the 1 s tone was synthesised: {r.stderr[-200:]}")
    tr = word_diff.Transcriber()                       # G18's default transcriber: nothing loaded yet (lazy)
    with pytest.raises(gpu0.LeaseMissing, match=r"^whisper:large-v3: GPU0 loads need CUDA_VISIBLE_DEVICES=0 "
                                                 r"\(it is ''"):
        tr.span(wav, 0.0, 1.0)                         # its first use: refused at the lease
    assert not issubclass(gpu0.LeaseMissing, Exception)
    assert len(whisper_attempts()) == 1, "the refused transcriber reached faster_whisper"
    assert not gpu0.whisper(word_diff.ASR["model"]).loaded
