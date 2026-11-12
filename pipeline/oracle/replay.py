#!/usr/bin/env python3
"""pipeline/oracle/replay.py — the selector's decision path on a saved universe at THIS code, without any GPU.

editorial_select.select_story runs unchanged, with the backtest harness's frozen inputs (pipeline/backtest.py: the
day's own transcript records by sha, existing word records only, the story-engine items the day saw, 'now' pinned
to the run's start) and two stand-ins:
  CacheOnlyLLM  gemma's validated-reply cache only (the production LocalLLM.chat_json computes the key and
                re-validates every cached reply). A prompt with no cached reply is a step that needs gemma: _post
                raises NotRerun (a BaseException, so no `except Exception` in the selector can turn it into an
                INCONCLUSIVE verdict) and the replay stops there: NOT_RERUN at that phase. stop() is a no-op: the
                production stop() unloads gemma from GPU0, which the live run owns.
  CpuEmbedder   the same bge model on CPU (float32). Chunk vectors come from the store's t2 cache when it holds
                them (computed on GPU0 by a real run: identical clusters); otherwise they are computed on CPU and
                NOT written back (the store is read-only here). CPU vectors differ from GPU float16 ones in the
                last digits, so a cluster or a retrieval rank built from them can differ: every video whose vectors
                were computed here is listed in the replay record.
Nothing here writes outside the replay's own output directory.
"""
import collections
import contextlib
import glob
import json
import os
import time
from datetime import datetime, timezone

import numpy as np

from pipeline.oracle import PIPELINE_DIR  # noqa: F401  (pipeline/ on sys.path)
import story_semantics as sm  # noqa: E402

TORCH_THREADS = 8
MISS_CALL = {700: "derive_story_query", 200: "verify_reaction", 350: "verify_support", 400: "adjudicate",
             500: "label_cluster", 1200: "rate_passages"}          # story_semantics' max_tokens per call


class NotRerun(BaseException):
    """A step needs gemma (no cached reply for its exact prompt): the replay stops; nothing is inferred."""


class CacheOnlyLLM(sm.LocalLLM):
    def __init__(self, digest):                       # never calls LocalLLM.__init__ (its GPU guard)
        self.model, self.host, self.digest = sm.LLM_MODEL, sm.LLM_HOST, digest
        self.calls, self.cache_hits, self.serve_pid, self.serve_env = 0, 0, None, None
        self.placement_checked = True
        self.miss = None

    def start(self):
        return self

    def _post(self, prompt, max_tokens, seed):
        import hashlib
        self.miss = {"call": MISS_CALL.get(max_tokens, f"max_tokens {max_tokens}"), "max_tokens": max_tokens,
                     "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt_head": prompt[:300]}
        raise NotRerun(f"no cached gemma reply for this prompt (max_tokens {max_tokens})")

    def stop(self):                                   # the live run's model stays loaded
        return None


class CpuEmbedder(sm.Embedder):
    def __init__(self, vector_cache=None):            # never calls Embedder.__init__ (cuda:0)
        self.vector_cache = vector_cache              # CPU vectors kept OUTSIDE the store (re-runs reuse them)
        import torch
        from transformers import AutoModel, AutoTokenizer
        from huggingface_hub import snapshot_download
        torch.set_num_threads(TORCH_THREADS)
        path = snapshot_download(sm.EMBED_MODEL, revision=sm.EMBED_REVISION, local_files_only=True)
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModel.from_pretrained(path, dtype=torch.float32).eval()
        self.torch = torch
        self.model_id = f"{sm.EMBED_MODEL}@{sm.EMBED_REVISION[:12]}"
        self.computed_here = []

    def encode(self, texts, query=False, batch=32):
        out = []
        with self.torch.no_grad():
            for i in range(0, len(texts), batch):
                bt = [(sm.EMBED_QUERY_PREFIX + t) if query else t for t in texts[i:i + batch]]
                enc = self.tok(bt, padding=True, truncation=True, max_length=512, return_tensors="pt")
                cls = self.model(**enc).last_hidden_state[:, 0].float()
                out.append(self.torch.nn.functional.normalize(cls, dim=-1).numpy())
        return np.vstack(out) if out else np.zeros((0, 768), np.float32)

    def chunk_vectors(self, rec, chunks):
        """The store's t2 vectors when they exist for exactly these chunks; else CPU vectors, never saved."""
        ids = [c["chunk_id"] for c in chunks]
        p = os.path.join(sm.EMB_DIR, rec["video_id"], f"{rec['transcript_sha256'][:16]}.{sm.EMBED_REVISION[:12]}.t2.npz")
        own = (os.path.join(self.vector_cache, rec["video_id"], f"{rec['transcript_sha256'][:16]}.cpu.t2.npz")
               if self.vector_cache else None)
        for path in (p, own):
            if path and os.path.exists(path):
                z = np.load(path, allow_pickle=False)
                if list(z["ids"]) == ids:
                    if path == own:
                        self.computed_here.append(rec["video_id"])
                    return ids, z["vecs"]
        self.computed_here.append(rec["video_id"])
        vecs = self.encode([c["text"] for c in chunks])
        if own:
            os.makedirs(os.path.dirname(own), exist_ok=True)
            np.savez(own[:-4], ids=np.array(ids), vecs=vecs.astype(np.float32))
        return ids, vecs

    def close(self):
        return None


MAIN_TREE = "/home/ultron/protocol_pulse"


@contextlib.contextmanager
def no_writes_under(root=MAIN_TREE):
    """BEST EFFORT. While active, an open-for-write, create, rename, link or delete of a path under `root` through
    builtins.open / io.open / os.open / pathlib.Path / the os path functions (positional paths) raises PermissionError
    (a replay must only read the main tree's store; audit round 2, F15); creating a directory that already exists is
    not a write. NOT covered (audit round 3, F6): calls relative to a dir_fd, keyword-only paths, os.truncate / chmod /
    utime, C-level writers (sqlite3) and subprocesses. The stand-ins the replay uses (CacheOnlyLLM, CpuEmbedder) have
    no write path into the store; a read-only mount would be the real guarantee."""
    import builtins
    import io
    top = os.path.realpath(root) + os.sep

    def inside(p):
        try:
            return os.path.realpath(os.fspath(p)).startswith(top)
        except TypeError:
            return False

    def deny(what, p):
        raise PermissionError(f"replay write guard: {what} under {root}: {p}")
    real_open, real_os_open = builtins.open, os.open
    names = ("replace", "rename", "remove", "unlink", "link", "symlink", "rmdir", "mkdir", "makedirs")
    real = {n: getattr(os, n) for n in names}

    def g_open(file, mode="r", *a, **k):
        if isinstance(file, (str, bytes, os.PathLike)) and any(c in mode for c in "wax+") and inside(file):
            deny(f"open({mode!r})", file)
        return real_open(file, mode, *a, **k)

    def g_os_open(path, flags, *a, **k):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC) and inside(path):
            deny("os.open for writing", path)
        return real_os_open(path, flags, *a, **k)

    def wrap(n, f):
        def g(*args, **kw):
            paths = [x for x in args[:2] if isinstance(x, (str, bytes, os.PathLike))]
            if n in ("mkdir", "makedirs") and paths and os.path.isdir(paths[0]):
                return None if n == "makedirs" else f(*args, **kw)
            if any(inside(x) for x in paths):
                deny(f"os.{n}", paths)
            return f(*args, **kw)
        return g
    import pathlib                                   # its methods hold their own reference to io.open (3.10)
    pnames = ("open", "touch", "mkdir", "unlink", "rename", "replace", "rmdir", "symlink_to")
    preal = {n: getattr(pathlib.Path, n) for n in pnames if hasattr(pathlib.Path, n)}

    def pwrap(n, f):
        def g(self, *args, **kw):
            mode = (args[0] if args else kw.get("mode", "r")) if n == "open" else None
            if n == "open" and not any(c in mode for c in "wax+"):
                return f(self, *args, **kw)
            if n == "mkdir" and self.is_dir():
                return f(self, *args, **kw)
            targets = [self] + [x for x in args[:1] if isinstance(x, (str, os.PathLike)) and n != "open"]
            if any(inside(x) for x in targets):
                deny(f"Path.{n}", targets)
            return f(self, *args, **kw)
        return g
    builtins.open = io.open = g_open
    os.open = g_os_open
    for n, f in real.items():
        setattr(os, n, wrap(n, f))
    for n, f in preal.items():
        setattr(pathlib.Path, n, pwrap(n, f))
    try:
        yield
    finally:
        builtins.open = io.open = real_open
        os.open = real_os_open
        for n, f in real.items():
            setattr(os, n, f)
        for n, f in preal.items():
            setattr(pathlib.Path, n, f)


def cache_digest():
    """The gemma digest the validated-reply cache was written with: the most common one over EVERY cached reply
    (sorted, so the same cache always gives the same answer); None if empty."""
    seen = collections.Counter()
    for p in sorted(glob.glob(os.path.join(sm.LLM_CACHE_DIR, "*", "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                seen[json.load(f).get("digest")] += 1
        except (OSError, ValueError):
            continue
    return seen.most_common(1)[0][0] if seen else None


def replay(run_dir, out_dir, embedder, digest, runs_dir):
    """Run select_story on run_dir's saved universe into out_dir; returns the replay record (REPLAY.json)."""
    import backtest
    import editorial_select as es
    with open(os.path.join(run_dir, "TOPIC_SELECTION.json"), encoding="utf-8") as f:
        saved = json.load(f)
    with open(es.CHANNELS_PATH, encoding="utf-8") as f:
        registry = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    sp = os.path.join(out_dir, "stories.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(backtest.stories_of(saved), f)
    now = datetime.fromisoformat(saved["started"]).astimezone(timezone.utc)
    L = CacheOnlyLLM(digest)
    n_before = len(getattr(embedder, "computed_here", []))
    t0, outcome = time.time(), None
    seen = []

    class _Checkpoint(es.Checkpoint):                # keeps the selector's live record, so the state reached
        def __init__(self, *a, **kw):                # before a NOT_RERUN is written, not the last checkpoint's
            super().__init__(*a, **kw)
            seen.append(self)
    real = es.Checkpoint
    es.Checkpoint = _Checkpoint
    with open(os.path.join(out_dir, "selection.log"), "w", encoding="utf-8") as logf:
        try:
            es.select_story(out_dir, log=lambda s: (logf.write(str(s) + "\n"), logf.flush()), embedder=embedder,
                            llm=L, universe_fn=backtest.universe_of(saved, registry), stories_path=sp, topup=False,
                            now=now, transcript_fn=backtest.frozen_transcripts(saved),
                            words_fn=backtest.offline_words(runs_dir))
            outcome = "COMPLETE: SELECTED"
        except es.NoProducibleStory as e:
            outcome = f"COMPLETE: {e}"
        except NotRerun as e:
            outcome = f"NOT_RERUN: {e}"
            if seen:
                last = (seen[-1].rec.get("progress") or {}).get("phase")
                seen[-1]("not_rerun", after=last, miss=L.miss)           # the in-memory record up to the miss
        except Exception as e:                                       # a crash is recorded, never a silent skip
            outcome = f"CRASH: {type(e).__name__}: {e}"
        finally:
            es.Checkpoint = real
    ts_path = os.path.join(out_dir, "TOPIC_SELECTION.json")
    progress = None
    if os.path.exists(ts_path):
        with open(ts_path, encoding="utf-8") as f:
            progress = json.load(f).get("progress")
    rec = {"run": os.path.basename(os.path.normpath(run_dir)), "outcome": outcome, "seconds": round(time.time() - t0),
           "stopped_at": progress and {**progress, "phase": progress.get("after") or progress.get("phase")},
           "gemma_cache_hits": L.cache_hits, "gemma_miss": L.miss, "digest": digest,
           "cpu_vectors_for": sorted(set(getattr(embedder, "computed_here", [])[n_before:]))}
    with open(os.path.join(out_dir, "REPLAY.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    return rec
