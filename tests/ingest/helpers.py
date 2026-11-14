"""Fakes for tests/ingest: back-ends, a yt-dlp gate, records. No network, no GPU, no keys."""
import json
import random
import re
import string
import subprocess

from pipeline.ingest import config, providers

CHAN = {"slug": "test_channel", "display_name": "Test Channel", "channel_id": "UC" + "a" * 22, "enabled": True,
        "tier": 1, "layout_status": "pending", "has_chyron": False}


def vid(prefix="v"):
    return (prefix + "".join(random.choice(string.ascii_letters + string.digits) for _ in range(11)))[:11]


def router_cfg(chain, **over):
    cfg = {"schema": "pp.providers/1", "env_file": "/nonexistent/.env", "global": {"max_inflight": 20},
           "backends": {b: {"kind": "openai_compat", "vendor": f"vendor-{b}", "model": f"model-{b}", "enabled": True}
                        for b in chain},
           "roles": {"mine": {"chain": list(chain), "attempts": 3, "max_tokens": 1000},
                     "hook": {"chain": list(chain), "attempts": 3, "max_tokens": 1000},
                     "spotlight": {"chain": list(chain), "attempts": 3, "max_tokens": 1000},
                     "flagcheck": {"chain": list(chain), "attempts": 2, "max_tokens": 1000},
                     "judge": {"chain": list(chain), "attempts": 2, "max_tokens": 1000}},
           "health": {"consecutive_failures": 3, "window": 10, "failure_fraction": 0.5, "window_s": 600,
                      "slow_median_s": 150, "open_s": 300},
           "throttle": {"first_s": 0.01, "max_s": 0.05, "transport_retries": 2},
           "spend_meter": {"backend": chain[0], "label": "GW", "baseline_usage": 0.0, "cap_usd": 100.0,
                           "notify_fraction": 0.9,
                              "measure_every_s": 600, "stale_after_s": 3600, "probe_ledger": "/nonexistent"}}
    cfg.update(over)
    return cfg


class FakeBackend:
    """script: replies (str) or exceptions, returned in order; fn(prompt) -> str | Exception instead."""

    def __init__(self, bid, script=None, fn=None, model=None, enabled=True, cfg=None, usage_total=1.0):
        self.id, self.model, self.max_inflight = bid, model or f"model-{bid}", 4
        self.cfg = dict({"vendor": f"vendor-{bid}"}, **(cfg or {}), model=self.model, enabled=enabled)
        self.script, self.fn = list(script or []), fn
        self.calls = []
        self.usage_total = usage_total
        self.base = "fake://" + bid

    def enabled(self):
        return bool(self.cfg.get("enabled", True))

    def complete(self, prompt, schema, max_tokens):
        self.calls.append(prompt)
        r = self.fn(prompt) if self.fn else (self.script.pop(0) if self.script else
                                            providers.BackendError("network", "script exhausted"))
        if isinstance(r, Exception):
            raise r
        return providers.Reply(r, self.model, "fake", 0.01, {"prompt_tokens": 10, "completion_tokens": 5}, 0.001,
                               "test")

    def get_json(self, path, timeout=30):
        if isinstance(self.usage_total, Exception):
            raise self.usage_total
        return {"data": {"total_usage": self.usage_total, "total_credits": 500}}


def make_router(backends, chain=None, clock=None, freeze=(), **kw):
    chain = chain or [b.id for b in backends]
    cfg = router_cfg(chain)
    for b in backends:
        cfg["backends"][b.id] = dict(b.cfg, kind="openai_compat")
    if freeze:
        cfg["spend_freeze"] = {"vendors": list(freeze)}
    extra = {"clock": clock} if clock else {}
    return providers.Router(cfg, keyring=providers.Keyring("/nonexistent/.env"), backends={b.id: b for b in backends},
                            sleep=lambda s: None, **extra, **kw)


def offered_ids(prompt):
    return [int(x) for x in re.findall(r"^\[S(\d+) ", prompt, re.M)]


def reply(moments):
    return json.dumps({"moments": moments})


def moment(a, b, **over):
    m = {"first": a, "count": b - a + 1, "scores": {"hook_first_2s": 3, "quotable": 4, "surprising_fact": 2, "stance": 4, "stakes": 3,
                                 "stands_alone": 4, "contempt_outrage": 0},
         "names_person": False, "risk": [], "about_bitcoin": True, "altcoin": False, "reason": "a strong stance"}
    m.update(over)
    return m


def first_two(prompt):
    ids = offered_ids(prompt)
    return reply([moment(ids[0], ids[1])] if len(ids) >= 2 else [])


SENTENCES = [
    "Bitcoin just reclaimed the level everyone said was gone for good.",
    "The ETF flows turned positive for the first time in eleven days.",
    "Most people miss what that means for supply on exchanges.",
    "Miners are holding more coins than at any point this year.",
    "If that continues, the float gets very thin very quickly.",
    "I think the next leg is driven by treasuries, not retail.",
    "That is the part nobody is talking about right now.",
]


def caption_record(video_id, n_rep=1, channel=CHAN, extra=None, published="2026-11-12T01:00:00+00:00", lead=None):
    """A yt_auto-style record through transcript_store's own writer (valid sha, identity carried)."""
    ts = config.ts()
    meta = {"video_id": video_id, "canonical_url": ts.canonical_url(video_id), "channel_id": channel["channel_id"],
            "channel_name": channel["display_name"], "exact_title": "Bitcoin test video", "published_at": published,
            "duration": 600}
    segs, t = [], 0.0
    for s in lead or []:
        segs.append({"start": t, "end": t + 4.0, "text": s})
        t += 4.0
    for r in range(n_rep):
        for s in SENTENCES:
            segs.append({"start": t, "end": t + 4.0, "text": s})
            t += 4.0
    for s in extra or []:
        segs.append({"start": t, "end": t + 4.0, "text": s})
        t += 4.0
    return ts._make_record(meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)", segs), meta


class FakeGate:
    """Answers yt-dlp argument lists from canned JSON (listing / probe); records every call."""

    def __init__(self, listing=None, probes=None, rate_limited=False):
        self.listing, self.probes, self.rate_limited = listing or {}, probes or {}, rate_limited
        self.calls = []
        import threading
        self.sem = threading.BoundedSemaphore(3)

    def open_for(self):
        return 0.0

    def run(self, args, timeout=120):
        from pipeline.ingest.watch import ListError
        self.calls.append(args)
        if self.rate_limited:
            raise ListError("rate_limited", "fake breaker")
        url = args[-1]
        if "--flat-playlist" in args:
            cid = "UC" + url.split("list=UU", 1)[1]
            j = self.listing.get(cid)
            out = json.dumps(j) if j is not None else ""
            return subprocess.CompletedProcess(args, 0 if j is not None else 1, out, "" if j else "ERROR: listing")
        v = url.split("v=", 1)[1]
        j = self.probes.get(v)
        if isinstance(j, str):
            return subprocess.CompletedProcess(args, 1, "", j)
        return subprocess.CompletedProcess(args, 0, json.dumps(j) if j else "", "" if j else "ERROR: unknown")


def probe_json(video_id, channel=CHAN, **over):
    j = {"id": video_id, "title": "Bitcoin test video", "channel_id": channel["channel_id"], "channel": "Test Channel",
         "duration": 900, "live_status": "not_live", "media_type": "video", "timestamp": None,
         "release_timestamp": None, "description": "d", "subtitles": {}, "automatic_captions": {"en-orig": [{}], "en": [{}]}}
    j.update(over)
    return j


def is_hook(prompt):
    return "You are the HOOK miner" in prompt


def hooks_reply(prompt, spans=((0, 1),)):
    """The hook pass's answer: hooks at the offered ids' positions given (relative), each a valid moment shape."""
    ids = offered_ids(prompt)
    return json.dumps({"hooks": [moment(ids[a], ids[b]) for a, b in spans if b < len(ids)]})


def first_two_and_hooks(prompt):
    """The moment pass answers its first two ids; the hook pass answers the same two ids as a hook, and the spotlight
    question (asked of every unmarked episode since the 09:02 ruling A36) finds none."""
    if is_spot(prompt):
        return json.dumps({"spotlights": []})
    return hooks_reply(prompt) if is_hook(prompt) else first_two(prompt)


def marked_solo(rec):
    """A MARKED solo episode (the 09:02 ruling A36: the one kind the hook pass skips for (b) + (c)): one caption speaker
    marker on the second segment, over a record long enough to sit under 0.3 turns a minute."""
    rec["segments"][1]["text"] = ">> " + rec["segments"][1]["text"]
    return rec


def is_spot(prompt):
    return "You are the SPOTLIGHT miner" in prompt


def spots_reply(prompt, spans=((0, 3),)):
    """The spotlight question's answer: spans at the offered ids' positions given (relative), valid moment shapes."""
    ids = offered_ids(prompt)
    return json.dumps({"spotlights": [moment(ids[a], ids[b]) for a, b in spans if b < len(ids)]})


def conversation(rec, every=10):
    """Mark a speaker change ('>>') on every `every`-th segment of a record (4 s segments: 1.5 turns a minute at 10)."""
    for i, s in enumerate(rec["segments"]):
        if i % every == every - 1:
            s["text"] = ">> " + s["text"]
    return rec
