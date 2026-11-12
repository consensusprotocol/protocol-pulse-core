"""tests/adversarial: the adversarial test wall (red-team 2026-11-11; session pipeline_pp_tests).

CPU ONLY, NO NETWORK. GPU0 is leased to the live run and GPU1 is quarantined, and nothing may reach Telegram, the
vision gateway or a model server, so every such path is made impossible before any pipeline module is imported:
  - CUDA_VISIBLE_DEVICES is emptied (segment_v1/qa_gates.py sets it to "0" at import: it is imported here first and
    the variable emptied again; the autouse fixture empties it before every test), so no CUDA library sees a device;
  - faster_whisper is replaced by a stub whose WhisperModel raises (and records the attempt), so no Whisper model
    can load; a test that needs a transcript injects it (qa_gates.whisper_segment, gate_g18's transcriber);
  - no socket of this process can connect over AF_INET / AF_INET6 (loopback included: a real Ollama listens on
    127.0.0.1): a fake that is missing, or a send path that regressed, raises NetworkBlocked (a BaseException, so no
    `except Exception` in the code under test and no pytest.raises(RuntimeError) in a test can absorb it);
    model / vision replies are injected at their one HTTP seam (LocalLLM._post, visual_check._call), the Telegram
    sender at deliver_run's `send`.
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

os.environ["CUDA_VISIBLE_DEVICES"] = ""

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(REPO, "segment_v1"), os.path.join(REPO, "pipeline"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


class _NoWhisper:
    """faster_whisper.WhisperModel stand-in: any attempt to load a model is recorded and refused."""
    attempts = []

    def __init__(self, *a, **k):
        _NoWhisper.attempts.append((a, k))
        raise RuntimeError("tests/adversarial: Whisper (GPU) is forbidden in this suite")


_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = _NoWhisper
sys.modules["faster_whisper"] = _fw


from adv_helpers import NetworkBlocked  # noqa: E402  (a BaseException: see adv_helpers)

_REAL_CONNECT, _REAL_CONNECT_EX = socket.socket.connect, socket.socket.connect_ex


def _no_network(self, address, *a, **k):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise NetworkBlocked(f"tests/adversarial: network is disabled in this suite (connect to {address!r})")
    return _REAL_CONNECT(self, address, *a, **k)


def _no_network_ex(self, address, *a, **k):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise NetworkBlocked(f"tests/adversarial: network is disabled in this suite (connect to {address!r})")
    return _REAL_CONNECT_EX(self, address, *a, **k)


socket.socket.connect, socket.socket.connect_ex = _no_network, _no_network_ex

import qa_gates  # noqa: E402,F401  (it sets CUDA_VISIBLE_DEVICES='0' at import: load it first, then undo that
os.environ["CUDA_VISIBLE_DEVICES"] = ""          # before any test module is collected; modules are cached)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _cpu_only():
    """Before every test: no CUDA device visible (qa_gates re-sets it to '0' when it is imported)."""
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    yield
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


@pytest.fixture
def whisper_attempts():
    """The Whisper loads attempted during one test (each one was refused)."""
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
