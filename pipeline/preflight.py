#!/usr/bin/env python3
"""pipeline/preflight.py — fail fast before a Pulse Check run spends an hour (orchestrator order 2026-11-11 '21:10').

Checks (seconds; secrets are read through relay.get_key and never printed):
  gpu0        GPU0 has no compute job except the GPU0 Ollama server's own runners, and enough memory free once
              that model is counted as ours
  ollama      the editorial model is installed on the GPU0 Ollama and answers a 1-token request
  yt_dlp      yt-dlp reads one known video's metadata
  elevenlabs  the API answers with the account's quota and enough characters left for a sign-off
  telegram    the approval bot answers getMe
  disk        free space on the repo's filesystem
  git         pipeline / segment_v1 tracked files unmodified, HEAD pushed (an ancestor of the upstream branch)
  no_other_run no run_fresh.py process besides this run
  assets      outro masters, brand mark, music, channel registry and every layout-eligible channel's avatar
Exit 0 = all pass, 3 = HOLD (the wrapper records the reasons and never starts run_fresh). Usage: python3 preflight.py
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)
sys.path.insert(1, os.path.join(REPO, "video_pipeline_v3"))     # relay.get_key (the pipeline's key loader)
import gpu0  # noqa: E402  (law L-r)

GPU0_FREE_MIB = 20000             # editorial model ~19 GB + Whisper; counted with our own Ollama model released
DISK_FREE_GB = 25
ELEVEN_MIN_CHARS = 2000           # a sign-off is ~150 characters; this leaves room for retries
KNOWN_VIDEO = "RBFN4CB60To"       # a v2f source video (references/v2f_2026-11-06), public and stable


def _run(cmd, timeout=30):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _get_json(url, headers=None, timeout=15, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def check_gpu0():
    """L-r: no foreign process on GPU0 (gpu0.foreign: anything but this run's processes and the GPU0 Ollama's), and
    room for the largest single model swap_to will load (its measured need + margin) once the Ollama's models, ours
    to unload, are released."""
    foreign = gpu0.foreign()
    if foreign:
        return False, f"GPU0 is used by something that is not this run's: {gpu0.describe(foreign)}"
    used, total = gpu0.memory()
    need = max(GPU0_FREE_MIB, max(gpu0.REQUIREMENT_MIB.values()) + gpu0.MARGIN_MIB)
    return total - used >= need, f"{total - used} MiB free (need {need}: the largest single model + margin)"


def check_ollama():
    import story_semantics as sm
    digest = sm.model_digest(sm.LLM_HOST, sm.LLM_MODEL)
    if not digest:
        return False, f"{sm.LLM_MODEL} not installed on {sm.LLM_HOST}"
    gpu0.swap_to(f"ollama:{sm.LLM_MODEL}")           # L-r: the model reaches GPU0 only through swap_to
    body = json.dumps({"model": sm.LLM_MODEL, "prompt": "ok", "stream": False, "keep_alive": 0,   # unloaded after
                       "options": {"num_predict": 1}}).encode()                                  # its answer (L-r)
    try:
        r = _get_json(f"http://{sm.LLM_HOST}/api/generate", {"Content-Type": "application/json"}, timeout=180, data=body)
    except urllib.error.HTTPError as e:
        text = e.read().decode(errors="replace")
        if gpu0.is_oom(RuntimeError(text)):                # named as what it is, never 'HTTPError (raised)'
            raise gpu0.GpuOOM(f"{sm.LLM_MODEL}: CUDA out of memory (HTTP {e.code}: {text[-300:]})") from None
        raise
    return "response" in r, f"{sm.LLM_MODEL} {digest[:12]} answered"


def check_yt_dlp():
    import transcript_store as ts
    r = ts._ytdlp(["-J", "--skip-download", ts.canonical_url(KNOWN_VIDEO)], timeout=60)
    try:
        ok = json.loads(r.stdout).get("id") == KNOWN_VIDEO
    except ValueError:
        ok = False
    return ok, "metadata read" if ok else f"yt-dlp failed: {(r.stderr or '')[-160:]}"


def check_elevenlabs():
    from relay import get_key
    s = _get_json("https://api.elevenlabs.io/v1/user/subscription", {"xi-api-key": get_key("ELEVENLABS_API_KEY")})
    left = int(s.get("character_limit", 0)) - int(s.get("character_count", 0))
    return left >= ELEVEN_MIN_CHARS, f"{left} characters left (need {ELEVEN_MIN_CHARS})"


def check_telegram():
    from relay import get_key
    r = _get_json(f"https://api.telegram.org/bot{get_key('TELEGRAM_BOT_TOKEN')}/getMe")
    return bool(r.get("ok")), "bot answers" if r.get("ok") else "getMe not ok"


def check_disk():
    free = shutil.disk_usage(REPO).free / 1e9
    return free >= DISK_FREE_GB, f"{free:.0f} GB free (need {DISK_FREE_GB})"


def check_git():
    # the code the run imports: pipeline/ and segment_v1/ (tracked files) and video_pipeline_v3's modules (its data
    # files change all day and are not code); untracked pipeline/*.py too (cycle 2 F6). segment_v1's historical
    # untracked scratch scripts are never imported; any module a run does import untracked or modified is a hold
    # at the end of the run (run_fresh.executed_code).
    dirty = _run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=no", "--", "pipeline",
                  "segment_v1", "video_pipeline_v3/*.py"]).stdout.strip()
    untracked = _run(["git", "-C", REPO, "ls-files", "--others", "--exclude-standard", "--", "pipeline/*.py"]).stdout.strip()
    if dirty or untracked:
        return False, "pipeline code not at a clean revision: " + " ".join((dirty + " " + untracked).split()[:8])
    up = _run(["git", "-C", REPO, "rev-parse", "--abbrev-ref", "@{u}"]).stdout.strip()
    if not up:
        return False, "the branch has no upstream"
    pushed = _run(["git", "-C", REPO, "merge-base", "--is-ancestor", "HEAD", up]).returncode == 0
    head = _run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"]).stdout.strip()
    return pushed, f"HEAD {head} " + ("pushed" if pushed else f"NOT on {up}")


def check_no_other_run():
    me = os.getpid()
    procs = [l for l in _run(["pgrep", "-af", "run_fresh.py"]).stdout.splitlines()
             if l and int(l.split()[0]) != me and "pgrep" not in l]
    return not procs, "none" if not procs else f"running: {procs[0][:80]}"


def check_assets():
    import config
    reg = json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))
    need = {"outro 16:9": config.OUTRO_MASTER_16x9, "outro 9:16": config.OUTRO_MASTER_9x16,
            "brand mark": config.resolve_brand(PIPELINE_DIR)}
    missing = [k for k, p in need.items() if not (p and os.path.isfile(p) and os.path.getsize(p) > 0)]
    if not glob.glob(os.path.join(REPO, "video_pipeline_v3", "assets", "music", "*.mp3")):
        missing.append("music")
    import editorial_select as es
    avatars = [c["display_name"] for c in reg if c.get("enabled", True) and es.layout_eligible(c)
               and not (c.get("avatar_path") and os.path.isfile(c["avatar_path"]))]
    missing += [f"avatar: {n}" for n in avatars]
    return not missing, "present" if not missing else "missing: " + ", ".join(missing[:8])


CHECKS = [("gpu0", check_gpu0), ("ollama", check_ollama), ("yt_dlp", check_yt_dlp),
          ("elevenlabs", check_elevenlabs), ("telegram", check_telegram), ("disk", check_disk),
          ("git", check_git), ("no_other_run", check_no_other_run), ("assets", check_assets)]


def run_checks(checks=None):
    out = []
    for name, fn in (CHECKS if checks is None else checks):
        try:
            ok, detail = fn()
        except gpu0.Gpu0Stop as e:                    # a GPU0 refusal names its cause (pids, MiB; never a secret)
            ok, detail = False, f"GPU0 {type(e).__name__}: {e}"
        except Exception as e:                        # an exception is a failed check, never a pass; reported by
            ok, detail = False, f"{type(e).__name__} (raised)"   # TYPE only: a network error's text can carry a
                                                                  # key or token in its URL (claude-fable audit #6)
        out.append({"check": name, "ok": bool(ok), "detail": detail})
    return out


def left_as_found(found_used, found_models, wait_s=60, slack_mib=256):
    """L-r item 2: (ok, detail): GPU0 holds no more than the preflight found (memory within slack_mib of it, no Ollama
    model that was not resident before), waiting up to wait_s for an unload to land."""
    t0 = time.time()
    while True:
        used, _ = gpu0.memory()
        resident = gpu0.ollama_loaded()
        extra = sorted(set(resident) - set(found_models))
        if used <= found_used + slack_mib and not extra:
            return True, f"GPU0 at {used} MiB (found at {found_used} MiB); Ollama resident now {resident or 'none'}"
        if time.time() - t0 > wait_s:
            return False, f"the preflight left GPU0 at {used} MiB (found at {found_used} MiB), added {extra}"
        time.sleep(1)


def main():
    try:
        with gpu0.lease(f"preflight (pid {os.getpid()})"):   # L-r: custody of the wrapper's fd 8, else its own
            found_used, found_models = gpu0.memory()[0], gpu0.ollama_loaded()
            res = run_checks()
            try:
                gpu0.leave()                                # what the checks loaded (keep_alive 0 may not have landed)
                ok, detail = left_as_found(found_used, found_models)
            except gpu0.Gpu0Stop as e:
                ok, detail = False, f"GPU0 {type(e).__name__}: {e}"
            res.append({"check": "gpu0_left", "ok": ok, "detail": detail})
    except gpu0.Gpu0Stop as e:
        print(f"HOLD (preflight): GPU0 {type(e).__name__}: {e}", flush=True)
        return 3
    for r in res:
        print(f"  preflight {r['check']:13s} [{'PASS' if r['ok'] else 'FAIL'}] {r['detail']}", flush=True)
    bad = [r for r in res if not r["ok"]]
    if bad:
        print("HOLD (preflight): " + "; ".join(f"{r['check']}: {r['detail']}" for r in bad), flush=True)
        return 3
    print("preflight: all checks passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
