#!/usr/bin/env python3
"""pipeline/gpu0.py — law L-r GPU0 NEVER SURPRISES A RUN (orchestrator 2026-11-12 '01:55' B; PBX on the pinned run's
out-of-memory: "let's make sure that never happens again").

ONE OWNER. GPU0 belongs to whoever holds the lease: an exclusive flock on the lease file (/tmp/pulse_gpu0.lease; the
environment variable PP_GPU0_LEASE overrides it), the holder recorded in the file. Entry points take it:
scripts/pulse_check_run.sh on fd 8 for the whole run (preflight and run_fresh inherit that descriptor), and run_fresh,
replay, preflight, backtest and GPU test sessions with lease() when started on their own. held() is a check, never an
acquisition: true in a process that took the lease with lease(), or that holds a descriptor whose open file description
holds the flock while it is held (a private probe first proves the lock is held at all; a second flock then succeeds
only on the holding description). require() runs before every load AND every use of a loaded model: no lease, no load.

ONE MODEL AT A TIME. swap_to(key) is the one way anything gets onto GPU0. It refuses a foreign GPU0 user, unloads
everything else this run has resident (its Model objects; its models on the GPU0 Ollama via keep_alive=0, confirmed on
/api/ps), collects garbage and empties torch's cache, then waits until nvidia-smi shows GPU0 free >= REQUIREMENT_MIB[key]
+ MARGIN_MIB (MARGIN_MIB alone for a model already resident), re-checking for a foreign user while it waits. A Model
(whisper(), model()) loads through swap_to on first use, is deleted by any later swap, and loads again through swap_to
when used again; its calls re-resolve the live object and run inside guard(). The GPU0 work of a run is done from one
thread (the PeakSampler only reads nvidia-smi).

FOREIGN. Not this run's: a GPU0 compute process other than this process, its descendants and the processes holding the
lease file open (the wrapper that holds it); a model resident on the shared GPU0 Ollama that this process did not
request; GPU0 memory no listed process accounts for, beyond UNLISTED_MAX_MIB. A foreign user is named and the run HOLDs;
nothing of it is unloaded or killed.

EVERY GPU HAS ONE OWNER AT A TIME (PBX 2026-11-12, the GPU1 quarantine lifted; orchestrator '22:50'). GPU0 = renders
and the gates that need render-side models (NVENC, the face detector / vision gates, gemma for the editorial gate); GPU1
= everything else (the word-pass worker, the website's Ollama fallback, the watchdog / morning brief / stage broadcast
models, local A/B runs). Each GPU has its own lease (/tmp/pulse_gpu<N>.lease, PP_GPU<N>_LEASE) and its own Ollama
(:11434 on GPU0, :11435 on GPU1); everything above holds per GPU. A process that loads models itself works on ONE GPU,
the one its CUDA_VISIBLE_DEVICES names ('0' or '1'); every function here reads that GPU (current_gpu()). A caller that
only asks a GPU's Ollama (it loads nothing itself: the watchdog, the website) uses ollama_call(gpu, ...). Some Ollama
keys are pinned to one GPU (ON_GPU). A named CO-TENANT within its cap (CO_TENANTS: the website's own CUDA context on
GPU1) is reported, not foreign; the free-memory proof still counts its memory.

STOPS. Every refusal is a Gpu0Stop, a BaseException, so no `except Exception` between a load and the stage runner can
turn it into another error ('transcription failed' hid an out-of-memory on Nov 12, E-FAIL-052): GpuOOM (a CUDA / NVENC
out-of-memory inside guard() or a finished subprocess), Gpu0Foreign, LeaseMissing, LeaseBusy, Gpu0NotFree (the memory
did not come free in time), Gpu0Unreadable (nvidia-smi, ss or the Ollama listener cannot be read: never 'nothing
there'). run_fresh's stage runner owns the one retry of an out-of-memory and turns every other stop into a HOLD."""
import contextlib
import fcntl
import gc
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")   # CUDA device 0 = nvidia-smi GPU 0 (before any CUDA init)

DEFAULT_LEASE = "/tmp/pulse_gpu0.lease"
OLLAMA_HOST = "127.0.0.1:11434"            # the GPU0 Ollama listener (story_semantics.LLM_HOST)
GPUS = (0, 1)
DEFAULT_LEASES = {0: DEFAULT_LEASE, 1: "/tmp/pulse_gpu1.lease"}
OLLAMA_HOSTS = {0: OLLAMA_HOST, 1: "127.0.0.1:11435"}
# A named co-tenant within its cap is not foreign (its memory still counts in every free-memory proof): the website's
# waitress process keeps a small CUDA context on GPU1 (480 MiB, nvidia-smi 2026-11-12 22:43)
CO_TENANTS = {1: ((re.compile(r"\bwaitress\b"), 1024),)}
MARGIN_MIB = 1024
UNLISTED_MAX_MIB = 1024                    # GPU0 memory no listed compute process accounts for, beyond this = foreign
# Peak GPU0 memory one load needs (MiB, its process's CUDA context included): the peak measured on this host's 24564 MiB
# GPU0 by pipeline/measure_gpu0.py on 2026-11-12 (Whisper keys on 600 s of speech; DoD 'L-r GPU0 requirements'), rounded
# up by ~5%; swap_to adds MARGIN_MIB. A key missing here can never be loaded.
REQUIREMENT_MIB = {
    "ollama:gemma3:27b": 20600,            # resident 20548-20559 (nvidia-smi 01:43 / 01:55 ET); measured peak 19241
    "whisper:large-v3": 6000,              # measured 5657 (beam 5, word timestamps, 600 s)
    "whisper:large-v3:batched": 9600,      # measured 9145 (batch 16 full: 600 s)
    "whisper:distil-large-v3:batched": 5700,   # measured 5401 (batch 16 full: 600 s)
    "whisper:medium": 2800,                # measured 2649
    "embedder": 1500,                      # measured 1379 (bge-base fp16, 64 x 512 tokens)
    "resemblyzer": 850,                    # measured 775
    "nvenc": 600,                          # measured 536 (one 1080x1920 h264_nvenc encode at a time)
    "ollama:qwen3-coder:30b": 22400,       # GPU1 Ollama runner 21302 (nvidia-smi 2026-11-12 22:43): the watchdog, briefs
    "ollama:deepseek-coder-v2:16b": 19100,  # 18128 when the site's fallback loaded it on GPU0 (11:50 ET): now GPU1's
}
ON_GPU = {"ollama:qwen3-coder:30b": 1, "ollama:deepseek-coder-v2:16b": 1}   # keys pinned to one GPU (the layout)
WAIT_S = 180
FOREIGN_WAIT_S, FOREIGN_POLL_S = 600, 15   # L-r 4 amended (orchestrator 2026-11-12 '11:57'): a foreign GPU0 user at a
                                           # swap is waited out (an Ollama keep-alive leaves by itself), then HOLD


class Gpu0Stop(BaseException):
    """A GPU0 refusal. A BaseException on purpose: it passes every `except Exception` up to the stage runner."""


class GpuOOM(Gpu0Stop):
    """A CUDA / NVENC out-of-memory (the original exception, when there is one, is its __cause__)."""


class Gpu0Foreign(Gpu0Stop):
    """GPU0 is used by something that is not this run's."""


class LeaseMissing(Gpu0Stop):
    """A GPU0 load or use in a process that does not hold the lease (or not on GPU0 only)."""


class LeaseBusy(Gpu0Stop):
    """Another owner holds the lease."""


class Gpu0NotFree(Gpu0Stop):
    """The memory a load needs did not come free in time."""


class Gpu0Unreadable(Gpu0Stop):
    """nvidia-smi, ss or the GPU0 Ollama listener cannot be read."""


_lock = threading.RLock()
_own = {}           # lease path -> {"file", "pid", "depth"}: this process's own lease() holdings
_resident = []      # Model objects loaded on GPU0 by this process
_ollama_ours_by = {g: {} for g in GPUS}
_ollama_ours = _ollama_ours_by[0]   # GPU0's (story_semantics.LocalLLM and the tests read it by this name). Per GPU:
                    # name -> 'pending' (requested by this process, not yet seen resident) | 'resident' (seen resident
                    # ever since it was requested); a model seen gone is no longer this process's: a later load of the
                    # same name by another client is foreign
CONTEXT_MAX_MIB = 1024                     # what this process may still hold on GPU0 once its models are released
_events = []        # every swap's evidence (run_fresh copies it into PROVENANCE)
_gen = [0]          # bumped whenever the resident set changes (LocalLLM re-swaps only when it moved)


_tls = threading.local()


def current_gpu():
    """The GPU these calls act on: inside ollama_call, the GPU it was given; otherwise this process's own, named by its
    CUDA_VISIBLE_DEVICES ('1' is GPU1; anything else, a CPU session included, reads GPU0's lease and listener)."""
    g = getattr(_tls, "gpu", None)
    if g is not None:
        return g
    return 1 if os.environ.get("CUDA_VISIBLE_DEVICES") == "1" else 0


@contextlib.contextmanager
def _on(g):
    if g not in GPUS:
        raise LeaseMissing(f"no GPU{g} on this host (GPUs {GPUS})")
    prev = getattr(_tls, "gpu", None)
    _tls.gpu = g
    try:
        yield
    finally:
        _tls.gpu = prev


def _ours():
    return _ollama_ours_by[current_gpu()]


# ── the lease ──

def lease_path():
    g = current_gpu()
    return os.path.realpath(os.environ.get(f"PP_GPU{g}_LEASE", DEFAULT_LEASES[g]))


def _fds_on(target):
    out = []
    for name in os.listdir("/proc/self/fd"):
        try:
            if os.path.realpath(os.readlink(f"/proc/self/fd/{name}")) == target:
                out.append(int(name))
        except (OSError, ValueError):
            continue
    return out


def _locked(target):
    """True when some open file description holds the flock (probed on a private one, released at once); an
    unopenable lease file counts as held (never 'free')."""
    try:
        f = open(target, "a+")
    except OSError:
        return True
    with f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)              # this probe's own private description only
        return False


def held():
    """True when this process holds the lease (see the module docstring). A check, never an acquisition: with the lock
    free no descriptor is probed. (Were it released between the two probes, the second could take it on this
    process's own descriptor: the process then holds it.)"""
    target = lease_path()
    with _lock:
        h = _own.get(target)
        if h and h["pid"] == os.getpid():
            return True
    fds = _fds_on(target)
    if not fds or not _locked(target):
        return False
    for fd in fds:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # succeeds only on the holding description
            return True
        except OSError:
            continue
    return False


def holder():
    """The recorded holder {"pid", "owner", "since"} while the lease is held, None when it is free."""
    target = lease_path()
    if not _locked(target):
        return None
    try:
        with open(target) as f:
            return _record(f)
    except OSError as e:
        return {"pid": None, "owner": f"lease file unreadable ({type(e).__name__})"}


def _record(f):
    try:
        rec = json.loads(os.pread(f.fileno(), 4096, 0).decode(errors="replace") or "{}")
    except (OSError, ValueError):
        rec = {}
    return rec if isinstance(rec, dict) else {}


@contextlib.contextmanager
def lease(owner, wait_s=0.0, poll_s=0.2):
    """Hold the lease for the block. Re-entrant (any thread) where this process took it: the descriptor closes when the
    last holder leaves; custody of an inherited descriptor is used as is (its owner releases it); otherwise acquired
    within wait_s, or LeaseBusy naming the holder. Every decision (mine / custody / acquire) is taken under one lock, so
    two threads entering together never both skip the count. Released by closing the descriptor (never LOCK_UN)."""
    target = lease_path()
    t0 = time.time()
    while True:
        with _lock:
            h = _own.get(target)
            if h is not None and h["pid"] == os.getpid():
                h["depth"] += 1
                break
            if held():
                h = None
                break
            f = open(target, "a+")
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                rec = _record(f)
                f.close()
                if time.time() - t0 >= wait_s:
                    raise LeaseBusy(f"the GPU{current_gpu()} lease is held by {rec.get('owner', 'an unrecorded owner')} "
                                    f"(pid {rec.get('pid')})") from None
                f = None
            if f is not None:
                f.seek(0)
                f.truncate()
                json.dump({"pid": os.getpid(), "owner": owner, "since": time.time()}, f)
                f.flush()
                h = _own[target] = {"file": f, "pid": os.getpid(), "depth": 1}
                break
        time.sleep(poll_s)
    if h is None:                                   # custody of an inherited descriptor
        yield
        return
    try:
        yield
    finally:
        with _lock:
            h["depth"] -= 1
            if h["depth"] == 0:
                if _own.get(target) is h:
                    _own.pop(target)
                h["file"].close()


def require(what, in_process=True):
    """No lease, no load (law L-r: every GPU has one owner at a time). An in-process load (torch, Whisper, NVENC) also
    needs CUDA_VISIBLE_DEVICES to name exactly the lease's GPU ('0' or '1': CUDA device 0 is then that nvidia-smi GPU;
    one GPU per process); a load inside a GPU's own Ollama server (keys 'ollama:') needs only that GPU's lease."""
    g = current_gpu()
    if in_process:
        if os.environ.get("CUDA_VISIBLE_DEVICES") != str(g):
            raise LeaseMissing(f"{what}: GPU{g} loads need CUDA_VISIBLE_DEVICES={g} (it is "
                               f"{os.environ.get('CUDA_VISIBLE_DEVICES')!r}; one GPU per process)")
        if os.environ.get("CUDA_DEVICE_ORDER") != "PCI_BUS_ID":
            raise LeaseMissing(f"{what}: CUDA_DEVICE_ORDER must be PCI_BUS_ID (CUDA device 0 = nvidia-smi GPU {g})")
    if not held():
        raise LeaseMissing(f"{what}: a GPU{g} load without the GPU{g} lease (law L-r: no lease, no load); "
                           f"holder: {holder()}")


# ── what is on GPU0 ──

def _smi(args, timeout=15):
    try:
        r = subprocess.run(["nvidia-smi", *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Gpu0Unreadable(f"nvidia-smi: {type(e).__name__}") from None
    if r.returncode != 0:
        raise Gpu0Unreadable(f"nvidia-smi exit {r.returncode}: {r.stderr.strip()[:200]}")
    return r.stdout


def memory():
    """(used_mib, total_mib) of this caller's GPU (current_gpu())."""
    out = _smi(["-i", str(current_gpu()), "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"])
    try:
        used, total = (int(x) for x in out.strip().split(","))
    except ValueError:
        raise Gpu0Unreadable(f"nvidia-smi memory line unreadable: {out.strip()[:80]!r}") from None
    return used, total


def processes():
    """[(pid, name, MiB or None)] of every compute process on this caller's GPU; an unreadable line is a
    Gpu0Unreadable."""
    g = current_gpu()
    uuid = _smi(["-i", str(g), "--query-gpu=uuid", "--format=csv,noheader"]).strip()
    if not uuid:
        raise Gpu0Unreadable(f"nvidia-smi names no GPU {g}")
    out = []
    for line in _smi(["--query-compute-apps=pid,gpu_uuid,used_memory,process_name",
                      "--format=csv,noheader,nounits"]).strip().splitlines():
        p = [x.strip() for x in line.split(",", 3)]
        if len(p) != 4 or not p[0].isdigit():
            raise Gpu0Unreadable(f"nvidia-smi compute-apps line unreadable: {line[:80]!r}")
        if p[1] == uuid:
            out.append((int(p[0]), os.path.basename(p[3]), int(p[2]) if p[2].isdigit() else None))
    return out


def describe(procs):
    return ", ".join(f"pid {p if p is not None else '?'} {n} {m} MiB" for p, n, m in procs) or \
        f"no GPU{current_gpu()} process"


def _children(pid):
    out = set()
    try:
        tids = os.listdir(f"/proc/{pid}/task")
    except OSError:
        return out
    for tid in tids:
        try:
            with open(f"/proc/{pid}/task/{tid}/children") as f:
                out |= {int(x) for x in f.read().split()}
        except (OSError, ValueError):
            continue
    return out


def _descendants(root=None):
    out, todo = set(), [os.getpid() if root is None else root]
    while todo:
        for k in _children(todo.pop()):
            if k not in out:
                out.add(k)
                todo.append(k)
    return out


def _lease_holders():
    """The process that holds the lease's flock (from /proc/locks, by the lease file's inode) and every process under
    it: the wrapper that holds it on fd 8 and the stages it started. A process that merely has the file open is not
    one of them."""
    try:
        ino = os.stat(lease_path()).st_ino
        with open("/proc/locks") as f:
            lines = f.read().splitlines()
    except OSError:
        return set()
    out = set()
    for line in lines:
        p = line.split()
        if len(p) >= 6 and p[1] == "FLOCK" and p[5].rsplit(":", 1)[-1] == str(ino) and p[4].isdigit():
            out.add(int(p[4]))
    live = set()
    for pid in out:                                    # the locker must still be alive with the lease file open (a
        try:                                           # dead flock(1) helper's pid, or a reused pid, is no holder)
            if any(os.path.realpath(os.readlink(f"/proc/{pid}/fd/{fd}")) == lease_path()
                   for fd in os.listdir(f"/proc/{pid}/fd")):
                live.add(pid)
        except OSError:
            continue
    for pid in list(live):
        live |= _descendants(pid)
    return live


def _ollama_pids():
    """This GPU's Ollama listener (the process on its port) and every process under it."""
    port = OLLAMA_HOSTS[current_gpu()].rsplit(":", 1)[1]
    try:
        r = subprocess.run(["ss", "-ltnpH", f"sport = :{port}"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Gpu0Unreadable(f"cannot read the GPU{current_gpu()} Ollama listener: {type(e).__name__}") from None
    if r.returncode != 0:
        raise Gpu0Unreadable(f"ss exit {r.returncode}: {r.stderr.strip()[:200]}")
    serve = {int(p) for p in re.findall(r"pid=(\d+)", r.stdout)}
    if r.stdout.strip() and not serve:
        raise Gpu0Unreadable(f"the GPU{current_gpu()} Ollama listener's pid is not visible to this user")
    out = set(serve)
    for p in serve:
        out |= _descendants(p)
    return out


def foreign():
    """[(pid, what, MiB)] using GPU0 that is not this run's (see the module docstring)."""
    procs = processes()
    ollama = _ollama_pids()
    ours = {os.getpid()} | _descendants() | _lease_holders() | ollama
    co = _co_tenants([p for p in procs if p[0] not in ours])
    out = [p for p in procs if p[0] not in ours and p not in co]
    for name, mib in ollama_resident():
        if name not in _ours():
            out.append((min(ollama) if ollama else None, f"ollama model {name} (not requested by this run)", mib))
    if all(m is not None for _, _, m in procs):             # a process whose memory is not reported: cannot account
        used, _ = memory()
        unlisted = used - sum(m for _, _, m in procs)
        if unlisted > UNLISTED_MAX_MIB:
            out.append((None, "GPU0 memory no listed compute process accounts for", unlisted))
    return out


def _co_tenants(procs):
    """The processes among `procs` that are a named co-tenant of this GPU within its cap (CO_TENANTS): reported in the
    swap evidence, not foreign; a co-tenant over its cap, or with its memory unreported, is foreign."""
    out = []
    for p in procs:
        pid, _, mib = p
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if any(rx.search(cmd) and mib is not None and mib <= cap for rx, cap in CO_TENANTS.get(current_gpu(), ())):
            out.append(p)
    return out


# ── the GPU's Ollama ──

def _ollama(path, body=None, timeout=30):
    req = urllib.request.Request(f"http://{OLLAMA_HOSTS[current_gpu()]}{path}",
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read() or b"{}")


def ollama_resident():
    """[(name, MiB on the GPU)] of the models resident on the GPU0 Ollama ([] only when nothing listens there); any
    other unreadable or malformed answer is a Gpu0Unreadable. Also observes this process's ownership: a model of ours
    seen gone is ours no more."""
    try:
        r = _ollama("/api/ps")
        if not isinstance(r, dict) or not isinstance(r.get("models"), list):
            raise ValueError(f"no models list in {str(r)[:80]!r}")
        if not all(isinstance(m, dict) and isinstance(m.get("name"), str) and m["name"] for m in r["models"]):
            raise ValueError("a model entry without a name string")
        out = [(m["name"], int(m.get("size_vram") or 0) // (1024 * 1024)) for m in r["models"]]
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), ConnectionRefusedError):
            out = []
        else:
            raise Gpu0Unreadable(f"Ollama {OLLAMA_HOSTS[current_gpu()]} /api/ps: {e}") from None
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise Gpu0Unreadable(f"Ollama {OLLAMA_HOSTS[current_gpu()]} /api/ps: {type(e).__name__}: {e}") from None
    names = {n for n, _ in out}
    with _lock:
        for n, state in list(_ours().items()):
            if n in names:
                _ours()[n] = "resident"
            elif state == "resident":
                del _ours()[n]
    return out


def ollama_loaded():
    return [n for n, _ in ollama_resident()]


def ollama_settle(name):
    """Called when a request for `name` has ended (answered or failed): a still-'pending' ownership whose model is not
    resident now is dropped, so another client's later load of the same name is foreign, never 'ours'."""
    resident = name in ollama_loaded()
    with _lock:
        if _ours().get(name) == "pending" and not resident:
            del _ours()[name]


def _ollama_unload(names, wait_s=60):
    """Unload these models (this run's own: swap_to proved nothing foreign first) and confirm on /api/ps."""
    for n in names:
        try:
            _ollama("/api/generate", {"model": n, "keep_alive": 0}, timeout=120)
        except (OSError, ValueError) as e:
            raise Gpu0NotFree(f"Ollama would not unload {n}: {type(e).__name__}: {e}") from None
    t0 = time.time()
    while True:
        left = [n for n in ollama_loaded() if n in names]
        if not left:
            with _lock:
                for n in names:
                    _ours().pop(n, None)
            return list(names)
        if time.time() - t0 > wait_s:
            raise Gpu0NotFree(f"Ollama still holds {left} {wait_s}s after keep_alive=0")
        time.sleep(1)


# ── swaps ──

def generation():
    return _gen[0]


def events():
    return list(_events)


def _empty_caches():
    gc.collect()
    torch = sys.modules.get("torch")
    if torch is not None:
        try:
            if torch.cuda.is_initialized():
                torch.cuda.empty_cache()
        except Exception as e:
            if is_oom(e):
                raise GpuOOM(f"torch empty_cache: {e}") from e


def _ollama_key(key):
    return key[len("ollama:"):] if key.startswith("ollama:") else None


def _refuse_foreign(what):
    """L-r item 4 as amended (orchestrator 2026-11-12 '11:57'): a foreign GPU0 user is first WAITED OUT: polled every
    FOREIGN_POLL_S for up to FOREIGN_WAIT_S (an Ollama model's keep-alive expires by itself), who it was printed and
    recorded in the run's GPU0 events; Gpu0Foreign (a HOLD naming it) only when it is still there after the wait.
    Nothing that is not this run's is ever killed or unloaded. (Nov 12 11:47: the site's article job loaded
    deepseek-coder-v2:16b, 18 GB, on GPU0 for its 5-min keep-alive and a run HELD at prepare.)"""
    f = foreign()
    if not f:
        return
    t0, first = time.time(), describe(f)
    g = current_gpu()
    print(f"  GPU{g}: {what}: a foreign GPU{g} user, waiting it out (L-r 4, up to {FOREIGN_WAIT_S}s): {first}", flush=True)
    while f and time.time() - t0 < FOREIGN_WAIT_S:
        time.sleep(FOREIGN_POLL_S)
        f = foreign()
    waited = round(time.time() - t0, 1)
    _events.append({"key": "foreign_wait", "gpu": g, "what": what, "foreign": first, "waited_s": waited, "left": not f})
    if f:
        raise Gpu0Foreign(f"{what}: GPU{g} is used by something that is not this run's, still there after a "
                          f"{FOREIGN_WAIT_S}s wait: {describe(f)}")
    print(f"  GPU{g}: {what}: the foreign user left after {waited}s; proceeding", flush=True)


def swap_to(key, wait_s=WAIT_S, poll_s=2.0, gpu=None):
    """Make this caller's GPU ready for `key` and nothing else of this run's (see the module docstring). `gpu`, when
    given, must be that GPU (a process works on one GPU; an Ollama-only caller uses ollama_call). Returns the evidence
    it recorded. Raises a Gpu0Stop."""
    g = current_gpu()
    if gpu is not None and gpu != g:
        raise LeaseMissing(f"swap_to({key}, gpu={gpu}): this caller works on GPU{g} (one GPU per process; a caller that "
                           f"only asks an Ollama uses ollama_call)")
    require(f"swap_to({key})", in_process=_ollama_key(key) is None)
    if key not in REQUIREMENT_MIB:
        raise Gpu0NotFree(f"{key}: no measured GPU{g} requirement (gpu0.REQUIREMENT_MIB): never loaded")
    if ON_GPU.get(key, g) != g:
        raise Gpu0NotFree(f"{key}: pinned to GPU{ON_GPU[key]} by the layout (law L-r), never loaded on GPU{g}")
    with _lock:
        _refuse_foreign(f"swap_to({key})")
        ev = {"key": key, "gpu": g, "at": time.time(), "before": memory(), "unloaded": []}
        for m in [m for m in _resident if m.key != key]:
            m.unload()
            ev["unloaded"].append(m.key)
        name = _ollama_key(key)
        drop = [n for n in ollama_loaded() if n != name and n in _ours()]   # this run's only, never a newcomer
        ev["unloaded"] += [f"ollama:{n}" for n in _ollama_unload(drop)]
        if name and name not in _ours():
            _ours()[name] = "pending"                     # ours once seen resident; a request loads it now
        try:
            return _swap_wait(key, name, ev, wait_s, poll_s)
        except BaseException:
            if name:
                ollama_settle(name)                            # the swap failed: no request follows, no claim stays
            raise


def _swap_wait(key, name, ev, wait_s, poll_s):
    with _lock:
        already = name in ollama_loaded() if name else any(m.key == key for m in _resident)
        _empty_caches()
        need = MARGIN_MIB if already else REQUIREMENT_MIB[key] + MARGIN_MIB
        t0 = time.time()
        while True:
            used, total = memory()
            if total - used >= need:
                break
            if time.time() - t0 > wait_s:
                raise Gpu0NotFree(f"{key}: GPU{current_gpu()} has {total - used} MiB free {wait_s}s after the swap, needs {need} "
                                  f"({'already resident: the margin' if already else f'{REQUIREMENT_MIB[key]} + margin {MARGIN_MIB}'}); "
                                  f"on GPU{current_gpu()}: {describe(processes())}")
            time.sleep(poll_s)
            _refuse_foreign(f"swap_to({key}) while waiting")
        if not already:
            _gen[0] += 1
        ev.update(after=[used, total], free_mib=total - used, already_resident=already,
                  waited_s=round(time.time() - t0, 1))
        _events.append(ev)
        return ev


def release_all(wait_s=WAIT_S, poll_s=2.0):
    """Unload everything this run has on GPU0 (its Models, its models on the GPU0 Ollama), then wait until nvidia-smi
    shows GPU0 free: room for the largest single model (max REQUIREMENT_MIB + MARGIN_MIB). Under the lease; a foreign
    user is refused, never unloaded. Returns evidence; Gpu0NotFree names every GPU0 process when it does not come free."""
    require("release_all")
    g = current_gpu()
    need = max(v for k, v in REQUIREMENT_MIB.items() if ON_GPU.get(k, g) == g) + MARGIN_MIB   # the largest load THIS GPU takes
    with _lock:
        _refuse_foreign("release_all")
        ev = {"at": time.time(), "before": memory(), "unloaded": []}
        for m in list(_resident):
            m.unload()
            ev["unloaded"].append(m.key)
        ev["unloaded"] += [f"ollama:{n}" for n in _ollama_unload([n for n in ollama_loaded() if n in _ours()])]
        _empty_caches()
        _gen[0] += 1
        t0 = time.time()
        while True:
            used, total = memory()
            rows = [m for p, _, m in processes() if p == os.getpid()]
            mine = None if any(m is None for m in rows) else sum(rows)          # unreported: cannot prove the release
            if total - used >= need and mine is not None and mine <= CONTEXT_MAX_MIB:
                ev.update(after=[used, total], this_process_mib=mine, waited_s=round(time.time() - t0, 1))
                return ev
            if time.time() - t0 > wait_s:
                raise Gpu0NotFree(f"GPU{g} has {total - used} MiB free and this process still holds {mine} MiB {wait_s}s "
                                  f"after releasing everything it owns (free means >= {need} with this process at <= "
                                  f"{CONTEXT_MAX_MIB}: the failed model was not freed); on GPU{g}: {describe(processes())}")
            time.sleep(poll_s)
            _refuse_foreign("release_all while waiting")


def leave():
    """At a process's end, before its lease goes: unload what it put on GPU0 (its Models, its Ollama models still
    resident) so the next owner does not find this run's model and HOLD on it as foreign. Never touches a foreign one."""
    with _lock:
        for m in list(_resident):
            m.unload()
        mine = [n for n in ollama_loaded() if n in _ours()]
        if mine:
            _ollama_unload(mine)
        _ours().clear()
        _empty_caches()
        return mine


# ── a caller that only asks a GPU's Ollama ──

_call_locks = {g: threading.Lock() for g in GPUS}


def ollama_call(gpu, model, path, body, owner, wait_s=600.0, timeout=300):
    """One request to GPU `gpu`'s Ollama for a caller that loads nothing itself (the watchdog, the morning brief, the
    stage broadcast, the website): law L-r, every GPU has one owner at a time. One call per GPU per process at a time
    (an in-process lock: the website serves several threads); GPU `gpu`'s lease is taken, waiting up to wait_s for its
    holder to leave (the word-pass worker leaves between batches); swap_to proves the memory free and waits a foreign
    user out (then a Gpu0Foreign naming it); the request runs with keep_alive 0; the model is confirmed gone from that
    Ollama before the lease is released, so the GPU is left as found. Nothing of this process on another GPU is
    touched. Returns the reply's JSON; raises a Gpu0Stop (LeaseBusy, Gpu0Foreign, Gpu0NotFree, ...) or the request's
    own error."""
    key = f"ollama:{model}"
    with _on(gpu):
        if not _call_locks[gpu].acquire(timeout=max(0.0, float(wait_s))):
            raise LeaseBusy(f"{owner}: another call of this process has held GPU{gpu} for longer than {wait_s}s")
        try:
            with lease(owner, wait_s=wait_s, poll_s=1.0):
                swap_to(key, wait_s=min(WAIT_S, float(wait_s)))          # the caller's bound covers the memory wait too
                try:
                    return _ollama(path, dict(body, model=model, keep_alive=0), timeout=timeout)
                finally:
                    ollama_settle(model)
                    mine = [n for n in ollama_loaded() if n in _ours()]
                    if mine:
                        _ollama_unload(mine)                     # keep_alive 0 asked; this confirms it on /api/ps
        finally:
            _call_locks[gpu].release()


# ── out of memory ──

_OOM = re.compile(r"out of memory|CUDA_ERROR_OUT_OF_MEMORY|cudaErrorMemoryAllocation|CUBLAS_STATUS_ALLOC_FAILED|"
                  r"CUDNN_STATUS_ALLOC_FAILED|NV_ENC_ERR_OUT_OF_MEMORY|OutOfMemoryError|cudaMalloc failed|"
                  r"unable to allocate (?:a )?(?:CUDA|GPU|CUDA\d+) buffer|failed to allocate (?:CUDA|GPU)", re.I)


def is_oom(e):
    """True for a CUDA / NVENC / Ollama out-of-memory, read from the exception, its type and any captured stderr."""
    if isinstance(e, GpuOOM):
        return True
    parts = [type(e).__name__, str(e)]
    for attr in ("stderr", "output"):
        v = getattr(e, attr, None)
        if isinstance(v, bytes):
            v = v.decode(errors="replace")
        if isinstance(v, str):
            parts.append(v[-1_000_000:])
    return bool(_OOM.search(" ".join(parts)))


def raise_if_oom(result, what):
    """A finished subprocess (run with capture_output) that failed on a CUDA / NVENC out-of-memory leaves as GpuOOM,
    never as the caller's later 'render failed' (law L-r item 3)."""
    if getattr(result, "returncode", 0) != 0:
        err = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else (result.stderr or "")
        if _OOM.search(err):
            raise GpuOOM(f"{what}: out of memory ({err.strip()[-300:]})")


@contextlib.contextmanager
def guard(what):
    """A CUDA out-of-memory raised inside the block leaves it as GpuOOM (nothing can rename it on the way up)."""
    try:
        yield
    except Gpu0Stop:
        raise
    except Exception as e:
        if is_oom(e):
            raise GpuOOM(f"{what}: CUDA out of memory ({type(e).__name__}: {str(e)[:300]})") from e
        raise


def guard_iter(it, what):
    """Iterate a lazily decoding iterator (faster-whisper segments) with every step inside guard(). The iterator keeps
    its model alive until it is exhausted or dropped."""
    while True:
        require(what)                                      # every decoding step under the lease, not only the first
        with guard(what):
            try:
                x = next(it)
            except StopIteration:
                return
        yield x


def drop_traceback(e):
    """Break the frames an exception chain pins (the failed call's model and tensors), so a release can free them."""
    seen = set()
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        e.__traceback__ = None
        e = e.__cause__ or e.__context__


# ── the only GPU0 models ──

class Model:
    """A GPU0 object loaded only through swap_to (see the module docstring). Every use checks the lease; a call
    re-resolves the live object (a later swap deleted it: it loads again through swap_to) and runs inside guard();
    only plain values (str, int, float, bool, None) of the object are readable directly."""

    def __init__(self, key, build):
        self.key, self._build, self._obj = key, build, None

    def get(self):
        require(self.key)
        with _lock:
            if self._obj is None:
                swap_to(self.key)
                with guard(f"{self.key}: load"):
                    self._obj = self._build()
                _resident.append(self)
            return self._obj

    def unload(self):
        with _lock:
            self._obj = None
            if self in _resident:
                _resident.remove(self)

    @property
    def loaded(self):
        return self._obj is not None

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        attr = getattr(self.get(), name)
        if callable(attr):
            del attr                                     # no stale reference: each call re-resolves the live object
            key = self.key

            def call(*a, **k):
                obj = self.get()
                with guard(f"{key}: {name}"):
                    return getattr(obj, name)(*a, **k)
            return call
        if isinstance(attr, (str, int, float, bool, type(None))):
            return attr
        raise AttributeError(f"gpu0.Model {self.key}: {name!r} is an object inside the model; reach the model only "
                             f"through its calls (law L-r: nothing may keep it alive past a swap)")

    def __call__(self, *a, **k):
        obj = self.get()
        with guard(f"{self.key}: call"):
            return obj(*a, **k)


class Whisper(Model):
    def transcribe(self, *a, **k):
        obj = self.get()
        with guard(f"{self.key}: transcribe"):
            segments, info = obj.transcribe(*a, **k)
        del obj
        return guard_iter(iter(segments), f"{self.key}: decode"), info


_models = {}


def whisper(name, batched=False):
    """The process's one faster-whisper model `name` (float16 on GPU0; batched = a BatchedInferencePipeline)."""
    key = f"whisper:{name}" + (":batched" if batched else "")
    with _lock:
        if key not in _models:
            def build():
                from faster_whisper import WhisperModel
                m = WhisperModel(name, device="cuda", compute_type="float16")
                if batched:
                    from faster_whisper import BatchedInferencePipeline
                    m = BatchedInferencePipeline(model=m)
                return m
            _models[key] = Whisper(key, build)
        return _models[key]


def model(key, build):
    """The process's one Model for `key` (a torch module, an encoder...): `build` makes the loaded object."""
    with _lock:
        if key not in _models:
            _models[key] = Model(key, build)
        return _models[key]


# ── evidence ──

class PeakSampler:
    """memory.used of EVERY GPU sampled every interval_s on a daemon thread; the peak per label (run_fresh: the stage)
    per GPU (peaks_by_gpu) and for this run's own GPU (peaks). A sampled maximum: a lower bound of the true peak
    (transients shorter than the interval are missed)."""

    def __init__(self, interval_s=1.0):
        self.interval_s, self.label, self.peaks, self.errors = interval_s, None, {}, 0
        self.peaks_by_gpu = {g: {} for g in GPUS}       # every GPU's (REPORT.md's per-GPU table); peaks = this run's GPU
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def set(self, label):
        self.label = label
        self._sample()

    def _sample(self):
        label = self.label                       # read before the measurement: a sample never crosses a stage edge
        mine = current_gpu()
        for g in GPUS:
            try:
                with _on(g):
                    used, _ = memory()
            except Gpu0Stop:
                self.errors += 1
                continue
            if label is not None and self.label == label:
                by = self.peaks_by_gpu[g]
                by[label] = max(by.get(label, 0), used)
                if g == mine:
                    self.peaks[label] = max(self.peaks.get(label, 0), used)

    def _run(self):
        while not self._stop.wait(self.interval_s):
            self._sample()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=5)
        self._sample()
        return dict(self.peaks)
