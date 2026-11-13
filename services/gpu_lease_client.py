"""services/gpu_lease_client.py — Ollama calls on GPU1 for code OUTSIDE the pipeline (the watchdog, the morning brief, the
stage broadcast, the website's article fallback): law L-r, EVERY GPU HAS ONE OWNER AT A TIME (PBX 2026-11-12 lifted the
GPU1 quarantine; orchestrator '22:50'). Each call goes through pipeline/gpu0.py's ollama_call: the GPU1 lease taken
with a bounded wait (the word-pass worker leaves between batches), the free-memory proof, keep_alive 0, the model's
unload confirmed before the lease is released, so nothing squats on GPU1 between calls.

pipeline/gpu0.py is loaded by its file path under a private module name: the pipeline directory is never put on
sys.path (its module names, config / telegram / ..., would shadow the site's own). gpu0's stops are BaseExceptions; here
they become Gpu1Unavailable (a RuntimeError), so a caller's existing `except Exception` fallback keeps working."""
import importlib.util
import os
import sys

_GPU0_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline", "gpu0.py")
GPU1 = 1


class Gpu1Unavailable(RuntimeError):
    """GPU1 could not be used for this call (its lease stayed busy, a foreign user stayed, memory never came free)."""


def gpu0():
    m = sys.modules.get("pp_gpu0")
    if m is None:
        spec = importlib.util.spec_from_file_location("pp_gpu0", _GPU0_PATH)
        m = importlib.util.module_from_spec(spec)
        sys.modules["pp_gpu0"] = m
        try:
            spec.loader.exec_module(m)
        except BaseException:
            sys.modules.pop("pp_gpu0", None)
            raise
    return m


def chat_gpu1(model, messages, owner, options=None, fmt=None, wait_s=600.0, timeout=120):
    """The content of one /api/chat reply from `model` on GPU1's Ollama ('' when the reply has none). `owner` names the
    caller in the lease file. Raises Gpu1Unavailable, or the request's own error."""
    g = gpu0()
    body = {"messages": messages, "stream": False}
    if options:
        body["options"] = options
    if fmt:
        body["format"] = fmt
    try:
        r = g.ollama_call(GPU1, model, "/api/chat", body, owner, wait_s=wait_s, timeout=timeout)
    except g.Gpu0Stop as e:
        raise Gpu1Unavailable(f"GPU1 {type(e).__name__}: {e}") from None
    return ((r or {}).get("message") or {}).get("content", "") or ""
