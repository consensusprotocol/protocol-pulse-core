"""pytest and GPU0 (law L-r ONE OWNER, pipeline/gpu0.py). Decided once, before collection:
  unset, '' or '-1'                a CPU session: takes nothing, hides every GPU (CUDA_VISIBLE_DEVICES=''); a GPU0 load in
                                   it is refused (gpu0.require), and a CUDA context of it on GPU0 stops the session
  '0'                              a GPU session, GPU0 only: holds the GPU0 lease for the whole session, or stops at
                                   once with exit 75 naming the holder (a run or another session has GPU0)
  anything else ('0,1', '1', ...)  refused (exit 2): GPU1 is quarantined"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # gpu0 lives next to this file

_CVD = os.environ.get("CUDA_VISIBLE_DEVICES")
_CPU = _CVD in (None, "", "-1")
_LEASE = []
if _CPU:
    import tempfile
    os.environ["CUDA_VISIBLE_DEVICES"] = ""            # unset would show every GPU to the libraries: hide them all
    # and a private lease file: code under test that enters gpu0.lease() (preflight.main, replay) never takes or blocks
    # the production GPU0 lease from a CPU session (Nov 12: test_preflight briefly held /tmp/pulse_gpu0.lease)
    os.environ["PP_GPU0_LEASE"] = os.path.join(tempfile.mkdtemp(prefix="pp_cpu_session_"), "gpu0.lease")


def pytest_configure(config):
    if _CPU:
        return
    if _CVD != "0":
        pytest.exit(f"CUDA_VISIBLE_DEVICES={_CVD!r}: test sessions run on GPU0 only ('0', or '' for CPU)", returncode=2)
    import gpu0
    cm = gpu0.lease(f"pytest session (pid {os.getpid()})")
    try:
        cm.__enter__()
    except gpu0.LeaseBusy as e:
        pytest.exit(f"GPU0 is busy, no GPU test session now: {e}", returncode=75)
    _LEASE.append(cm)


def pytest_unconfigure(config):
    while _LEASE:
        _LEASE.pop().__exit__(None, None, None)


def _holds_gpu0_context(pid):
    """True / False, or None when GPU0 cannot be read (the caller stops the session: never 'nothing there')."""
    import subprocess
    try:
        a = subprocess.run(["nvidia-smi", "-i", "0", "--query-gpu=uuid", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=15)
        b = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    uuid = a.stdout.strip()
    if a.returncode != 0 or b.returncode != 0 or not uuid:
        return None
    return any([x.strip() for x in line.split(",")][:2] == [str(pid), uuid] for line in b.stdout.splitlines())


def pytest_runtest_teardown(item, nextitem):
    """L-r: a CPU session never touches GPU0. After each test module, a CUDA context of this process on GPU0 stops the
    session at once, naming the module (on Nov 12 render16's import forced CUDA_VISIBLE_DEVICES=0 into a CPU session,
    which then held 394 MiB on GPU0 without the lease)."""
    if not _CPU or (nextitem is not None and nextitem.module is item.module):
        return
    held = _holds_gpu0_context(os.getpid())
    if held is None:
        pytest.exit(f"law L-r: GPU0 cannot be read after {item.module.__name__}: this CPU session cannot prove it left "
                    f"GPU0 alone", returncode=3)
    if held:
        pytest.exit(f"law L-r: this CPU test session holds a CUDA context on GPU0 after {item.module.__name__} "
                    f"(last test {item.nodeid}, CUDA_VISIBLE_DEVICES now {os.environ.get('CUDA_VISIBLE_DEVICES')!r})",
                    returncode=3)
