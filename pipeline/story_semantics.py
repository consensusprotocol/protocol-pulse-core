#!/usr/bin/env python3
"""pipeline/story_semantics.py — semantic story identity over attributed transcript chunks.

Resources (all local, GPU0 only):
  embeddings  BAAI/bge-base-en-v1.5 (pinned revision), transformers, fp16 on cuda:0
  LLM         gemma3:27b via the shared Ollama service on :11434, used only after proving from
              the live process environment and nvidia-smi that it is GPU0-only. The separate
              Ollama on :11435 is pinned to the quarantined GPU1 and is never called.

Nothing here substitutes a lexical heuristic for semantic identity:
  - retrieval = embedding similarity + word-boundary alias hits (recall only)
  - identity  = LLM adjudication per video, whose evidence quote must appear verbatim in the
                supplied attributed chunks (otherwise the verdict does not count)
"""
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import urllib.request

import numpy as np

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
STORE_DIR = os.environ.get("PP_EDITORIAL_STORE", os.path.join(REPO, "data", "editorial"))
EMB_DIR = os.path.join(STORE_DIR, "embeddings")

EMBED_MODEL = "BAAI/bge-base-en-v1.5"
EMBED_REVISION = "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a"
EMBED_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
LLM_MODEL = "gemma3:27b"
LLM_HOST = "127.0.0.1:11434"
LLM_CTX = 16384

VERDICTS = ("SAME_EVENT", "RELATED_DIFFERENT_EVENT", "UNRELATED")


def _gpu_guard():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise RuntimeError("semantic layer requires CUDA_VISIBLE_DEVICES=0 (GPU1 quarantined)")


# ── embeddings ──

class Embedder:
    def __init__(self):
        _gpu_guard()
        import torch
        from transformers import AutoModel, AutoTokenizer
        from huggingface_hub import snapshot_download
        path = snapshot_download(EMBED_MODEL, revision=EMBED_REVISION, local_files_only=True)
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModel.from_pretrained(path, dtype=torch.float16).to("cuda:0").eval()
        self.torch = torch
        self.model_id = f"{EMBED_MODEL}@{EMBED_REVISION[:12]}"

    def encode(self, texts, query=False, batch=64):
        out = []
        with self.torch.no_grad():
            for i in range(0, len(texts), batch):
                bt = [(EMBED_QUERY_PREFIX + t) if query else t for t in texts[i:i + batch]]
                enc = self.tok(bt, padding=True, truncation=True, max_length=512,
                               return_tensors="pt").to("cuda:0")
                cls = self.model(**enc).last_hidden_state[:, 0].float()
                out.append(self.torch.nn.functional.normalize(cls, dim=-1).cpu().numpy())
        return np.vstack(out) if out else np.zeros((0, 768), np.float32)

    def chunk_vectors(self, rec, chunks):
        """Cached per (video, transcript sha, model). Returns (ids, vecs)."""
        d = os.path.join(EMB_DIR, rec["video_id"])
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{rec['transcript_sha256'][:16]}.{EMBED_REVISION[:12]}.npz")
        ids = [c["chunk_id"] for c in chunks]
        if os.path.exists(p):
            z = np.load(p, allow_pickle=False)
            if list(z["ids"]) == ids:
                return ids, z["vecs"]
        vecs = self.encode([c["text"] for c in chunks])
        np.savez(p, ids=np.array(ids), vecs=vecs.astype(np.float32))
        return ids, vecs

    def close(self):
        del self.model
        self.torch.cuda.empty_cache()


# ── private GPU0 LLM ──

class LocalLLM:
    """Uses the shared Ollama service on :11434 ONLY after proving it is GPU0-only:
    the listening process must run with CUDA_VISIBLE_DEVICES=0, and after the first call every
    runner under it must sit on GPU0. (A separate instance on :11435 is pinned to the
    quarantined GPU1 and is never used.)"""

    def __init__(self, model=LLM_MODEL, host=LLM_HOST):
        _gpu_guard()
        self.model, self.host = model, host
        self.calls = 0
        self.serve_pid = None

    def _listener_pid(self):
        port = self.host.rsplit(":", 1)[1]
        out = subprocess.run(["ss", "-ltnpH"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if re.search(rf"[:.]{port}\s", line):
                m = re.search(r"pid=(\d+)", line)
                if m:
                    return int(m.group(1))
        return None

    def start(self):
        pid = self._listener_pid()
        if not pid:
            raise RuntimeError(f"no Ollama listening on {self.host}")
        with open(f"/proc/{pid}/environ", "rb") as f:
            env = dict(x.split("=", 1) for x in f.read().decode(errors="ignore").split("\0") if "=" in x)
        if env.get("CUDA_VISIBLE_DEVICES") != "0":
            raise RuntimeError(f"Ollama on {self.host} (pid {pid}) is not GPU0-only: "
                               f"CUDA_VISIBLE_DEVICES={env.get('CUDA_VISIBLE_DEVICES')}")
        self.serve_pid = pid
        self.serve_env = {k: env.get(k) for k in ("CUDA_VISIBLE_DEVICES", "OLLAMA_HOST")}
        return self

    def gpu_placement(self):
        """GPU indices used by the serving process's runners (must be ['0'])."""
        kids = subprocess.run(["pgrep", "-P", str(self.serve_pid)], capture_output=True,
                              text=True).stdout.split() + [str(self.serve_pid)]
        q = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid", "--format=csv,noheader"],
                           capture_output=True, text=True).stdout
        mine = {l.split(",")[1].strip() for l in q.strip().splitlines()
                if l.split(",")[0].strip() in kids}
        gpus = dict(l.split(", ") for l in subprocess.run(
            ["nvidia-smi", "--query-gpu=uuid,index", "--format=csv,noheader"],
            capture_output=True, text=True).stdout.strip().splitlines())
        return sorted(gpus.get(u, u) for u in mine)

    def chat_json(self, prompt, max_tokens=700):
        body = json.dumps({"model": self.model, "stream": False, "format": "json",
                           "messages": [{"role": "user", "content": prompt}],
                           "options": {"temperature": 0, "seed": 7, "num_ctx": LLM_CTX,
                                       "num_predict": max_tokens}}).encode()
        req = urllib.request.Request(f"http://{self.host}/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=600).read())
        self.calls += 1
        if self.calls == 1:
            placement = self.gpu_placement()
            if placement != ["0"]:
                self.stop()
                raise RuntimeError(f"private LLM not on GPU0 only: {placement}")
        txt = resp["message"]["content"]
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0) if m else txt)

    def stop(self):
        """Release our model from GPU0 VRAM (keep_alive 0) so renders get the memory back."""
        try:
            body = json.dumps({"model": self.model, "keep_alive": 0}).encode()
            urllib.request.urlopen(urllib.request.Request(
                f"http://{self.host}/api/generate", data=body,
                headers={"Content-Type": "application/json"}), timeout=60).read()
        except Exception:
            pass


def prompt_sha(p):
    return hashlib.sha256(p.encode()).hexdigest()[:16]


# ── story query derivation ──

DERIVE_PROMPT = """You are the editor of a Bitcoin news show. Analyse this news item and describe the
UNDERLYING real-world event so that transcripts of video discussions can be matched to it even
when they use completely different vocabulary. Today is {today}.

ITEM:
headline: {headline}
summary: {summary}
source: {source}

Return ONLY JSON with keys:
"short_label": 1-3 word label for the story (e.g. "midterm elections"),
"underlying_event": one sentence naming the core real-world event (who did what, when),
"angle": one sentence for this item's specific angle on that event,
"entities": [{{"name": str, "aliases": [other names, tickers, abbreviations people say aloud]}}],
"action": str, "affected_object": str, "date_context": str,
"concepts": [5-10 short phrases a speaker discussing this event might use, NOT copied from the headline],
"must_not_confuse_with": [names/phrases that look similar but are different things],
"bitcoin_relevance": integer 0-5 (5 = directly about Bitcoin; 3 = clearly moves Bitcoin or Bitcoin policy; 0 = unrelated),
"importance": integer 0-5 (significance for a sophisticated Bitcoin audience today),
"is_specific_event": true/false (false for evergreen themes or generic commentary),
"rationale": one sentence}}"""


def derive_story_query(llm, item, today):
    p = DERIVE_PROMPT.format(today=today, headline=item.get("headline", ""),
                             summary=(item.get("summary") or "")[:800],
                             source=item.get("source_domain") or item.get("source", ""))
    q = llm.chat_json(p)
    q["_prompt_sha"] = prompt_sha(DERIVE_PROMPT)
    q["_model"] = llm.model
    return q


def query_texts(q):
    t = [q.get("underlying_event", "")]
    t += [c for c in q.get("concepts", []) if isinstance(c, str)]
    return [x for x in t if x and len(x) >= 4][:12]


def alias_patterns(q):
    """Word-boundary patterns for entity names/aliases (recall aid only; never identity)."""
    names = []
    for e in q.get("entities", []) or []:
        if isinstance(e, dict):
            names += [e.get("name", "")] + list(e.get("aliases") or [])
    pats = []
    for n in {n.strip() for n in names if isinstance(n, str)}:
        if len(n) < 3 and not n.isupper():
            continue
        pats.append(re.compile(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])",
                               0 if n.isupper() and len(n) <= 5 else re.I))
    return pats


# ── adjudication ──

ADJUDICATE_PROMPT = """You verify whether a video discusses a specific news event.

EVENT: {event}
Key entities: {entities}
Do NOT confuse with: {confuse}

VIDEO: "{title}" ({channel})
Transcript excerpts (each tagged with its chunk id):
{excerpts}

Decide:
- "SAME_EVENT": the speakers substantively discuss THIS underlying event (different wording is fine).
- "RELATED_DIFFERENT_EVENT": same broad topic or entity type, but a different event/situation.
- "UNRELATED": not about this event (shared words or similar-sounding names do not count).

Return ONLY JSON: {{"verdict": one of the three, "supporting_chunk_ids": [ids from the excerpts that
support SAME_EVENT], "evidence_quote": an exact verbatim quote (8-30 words) copied from the excerpts,
"confidence": number 0-1, "reason": one sentence}}"""


def _norm(s):
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


def adjudicate(llm, q, video, excerpts):
    """video: dict(title, channel); excerpts: list of chunk dicts. Returns verdict dict."""
    ents = []
    for e in q.get("entities", []) or []:
        if isinstance(e, dict):
            ents.append(e.get("name", "") + (f" ({', '.join(e.get('aliases') or [])})" if e.get("aliases") else ""))
    ex = "\n".join(f"[{c['chunk_id']}] {c['text'][:1400]}" for c in excerpts)
    p = ADJUDICATE_PROMPT.format(event=q.get("underlying_event", ""), entities="; ".join(ents) or "-",
                                 confuse="; ".join(q.get("must_not_confuse_with") or []) or "-",
                                 title=video.get("title", ""), channel=video.get("channel", ""),
                                 excerpts=ex)
    v = llm.chat_json(p, max_tokens=400)
    verdict = v.get("verdict") if v.get("verdict") in VERDICTS else "UNRELATED"
    valid_ids = {c["chunk_id"] for c in excerpts}
    sup = [i for i in (v.get("supporting_chunk_ids") or []) if i in valid_ids]
    quote = v.get("evidence_quote") or ""
    corpus = _norm(" ".join(c["text"] for c in excerpts))
    quote_ok = len(_norm(quote).split()) >= 5 and _norm(quote) in corpus
    counted = verdict == "SAME_EVENT" and quote_ok and bool(sup)
    return {"verdict": verdict, "counted_as_same_event": counted, "quote_verified": quote_ok,
            "supporting_chunk_ids": sup, "evidence_quote": quote,
            "confidence": v.get("confidence"), "reason": v.get("reason"),
            "excerpt_chunk_ids": [c["chunk_id"] for c in excerpts],
            "_prompt_sha": prompt_sha(ADJUDICATE_PROMPT), "_model": llm.model}


# ── emergent clusters (what Bitcoin media is discussing, bottom-up) ──

LABEL_PROMPT = """These transcript excerpts come from DIFFERENT Bitcoin/finance videos and were grouped
because they are semantically similar. Today is {today}.
{excerpts}

Is there ONE specific, current real-world news event that most of these excerpts discuss?
Return ONLY JSON: {{"is_specific_event": true/false (false if this is an evergreen theme, generic
price talk, an ad read or small talk), "headline": a neutral news headline for the event,
"summary": two sentences, "member_chunk_ids": [ids of the excerpts that discuss it]}}"""


def emergent_clusters(chunks, vecs, min_channels=3, threshold=0.22, max_clusters=8):
    """Agglomerative clustering (cosine, average linkage) over chunk vectors; returns clusters
    that span >= min_channels distinct channels, largest coverage first."""
    from sklearn.cluster import AgglomerativeClustering
    if len(chunks) < 3:
        return []
    labels = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                     distance_threshold=threshold).fit_predict(vecs)
    groups = {}
    for i, l in enumerate(labels):
        groups.setdefault(int(l), []).append(i)
    out = []
    for l, idx in groups.items():
        chans = {chunks[i]["channel_id"] or chunks[i]["channel_name"] for i in idx}
        if len(chans) >= min_channels:
            out.append({"label": l, "chunk_idx": idx, "channels": sorted(chans)})
    out.sort(key=lambda g: (-len(g["channels"]), -len(g["chunk_idx"])))
    return out[:max_clusters]


def label_cluster(llm, chunks, vecs, group, today, k=8):
    idx = group["chunk_idx"]
    centroid = vecs[idx].mean(axis=0)
    order = sorted(idx, key=lambda i: -float(vecs[i] @ centroid))
    picked, seen = [], set()
    for i in order:                       # one excerpt per video first, for diversity
        if chunks[i]["video_id"] not in seen:
            picked.append(i)
            seen.add(chunks[i]["video_id"])
        if len(picked) >= k:
            break
    ex = "\n".join(f"[{chunks[i]['chunk_id']}] ({chunks[i]['channel_name']}) {chunks[i]['text'][:900]}"
                   for i in picked)
    r = llm.chat_json(LABEL_PROMPT.format(today=today, excerpts=ex), max_tokens=400)
    r["_prompt_sha"] = prompt_sha(LABEL_PROMPT)
    r["excerpt_chunk_ids"] = [chunks[i]["chunk_id"] for i in picked]
    return r


# ── clip judgment ──

CLIP_PROMPT = """You pick clips for a short Bitcoin news video about this event:
EVENT: {event}

Rate each candidate passage 1-5 for use as a standalone clip:
5 = complete, strong, specific statement about this event that makes sense on its own;
3 = relevant but weak, partial or dependent on missing context;
1 = off-topic, a question, filler, an ad, or starts/ends mid-thought.
{passages}
Return ONLY JSON: {{"ratings": [{{"id": passage id, "score": 1-5, "reason": short}}]}}"""


def rate_passages(llm, q, passages):
    ex = "\n".join(f"[{p['pid']}] ({p['channel']}, {p['duration']:.0f}s) {p['text']}" for p in passages)
    r = llm.chat_json(CLIP_PROMPT.format(event=q.get("underlying_event", ""), passages=ex),
                      max_tokens=1200)
    out = {}
    for x in r.get("ratings", []) or []:
        try:
            out[str(x["id"])] = (float(x["score"]), x.get("reason", ""))
        except Exception:
            pass
    return out
