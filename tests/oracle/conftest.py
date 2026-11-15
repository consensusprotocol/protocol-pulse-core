"""Shared fixtures for the supply-backtest tests: a small synthetic day of export rows and fake model calls."""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def row(vid, i, channel, cid, start, end, text, timing="word", layout_eligible=True):
    from pipeline.oracle import lineup as L  # noqa: F401  (pipeline/ on sys.path)
    import canon
    t = text.rstrip()
    return {"id": f"{vid}:{i}", "video_id": vid, "sentence_index": i, "channel": channel, "channel_id": cid,
            "title": f"{channel} show", "published_at": "2026-11-10T06:00:00+00:00", "age_h": 3.5,
            "start_s": start, "end_s": end, "duration_s": round(end - start, 2), "timing": timing, "text": text,
            "canon": canon.canon(text), "bitcoin": "bitcoin" in text.lower(), "complete": t.endswith((".", "!", "?")),
            "ends_statement": t.endswith((".", "!")), "layout_eligible": layout_eligible,
            "layout_eligible_run": layout_eligible, "layout_status": "pending", "has_chyron": not layout_eligible,
            "transcript_method": "whisper_words_punct", "transcript_sha256": "0" * 64}


@pytest.fixture
def day_rows():
    """Three channels on one development (Bitcoin below $74,000), one Ethereum sentence, one question."""
    A, B, C = "vidAAAAAAAA", "vidBBBBBBBB", "vidCCCCCCCC"
    return [
        row(A, 0, "Alpha", "UCa", 0.0, 9.5, "Bitcoin fell below $74,000 over the weekend, its lowest close since September."),
        row(A, 1, "Alpha", "UCa", 9.6, 15.0, "Traders now watch the 50-week moving average."),
        row(A, 2, "Alpha", "UCa", 15.1, 30.0, "That line sat near $75,500 when the week closed."),
        row(B, 4, "Beta", "UCb", 40.0, 47.0, "Bitcoin dropped about 16 percent from its high."),
        row(B, 5, "Beta", "UCb", 47.1, 54.0, "Spot ETFs saw outflows on Friday and Monday."),
        row(B, 6, "Beta", "UCb", 54.2, 61.0, "Buyers stepped in just above $73,000 on Sunday night."),
        row(B, 7, "Beta", "UCb", 61.1, 69.2, "So the weekend low held, at least for now."),
        row(B, 8, "Beta", "UCb", 69.3, 75.0, "Will it hold next week?"),
        row(C, 10, "Gamma", "UCc", 100.0, 108.0, "Bitcoin is trading around $74,200 this morning after the weekend sell-off."),
        row(C, 11, "Gamma", "UCc", 108.1, 114.5, "The drop wiped out more than a billion dollars of leveraged longs."),
        row(C, 12, "Gamma", "UCc", 114.6, 121.0, "Ethereum fell even harder, down twelve percent."),
        row(C, 13, "Gamma", "UCc", 121.1, 128.0, "Funding rates turned negative on most exchanges."),
    ]


def legal_lineup():
    return {"development": "Bitcoin fell below $74,000 over the weekend.", "current_because": "weekend statements",
            "hook": ["vidAAAAAAAA:0"], "clips": [["vidBBBBBBBB:4", "vidBBBBBBBB:5"],
                                                 ["vidBBBBBBBB:6", "vidBBBBBBBB:7"],
                                                 ["vidCCCCCCCC:10", "vidCCCCCCCC:11"]]}


def oracle_reply(lineups=None, verdict="LINEUPS", none_reason=""):
    return json.dumps({"verdict": verdict, "none_reason": none_reason,
                       "lineups": [legal_lineup()] if lineups is None else lineups})


def judge_reply(verdict="LEGAL", false=()):
    from pipeline.oracle import lineup as L
    checks = {k: k not in false for k in L.JUDGE_CHECKS}
    return json.dumps({"development": "Bitcoin fell below $74,000 over the weekend.", "checks": checks,
                       "failed": sorted(false), "verdict": verdict, "reason": "checked"})


class FakeCall:
    """A model call returning scripted replies in order; records every prompt it was given."""

    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def __call__(self, system, user, schema, ledger, tag):
        self.prompts.append((system, user))
        r = self.replies.pop(0) if self.replies else ""
        if isinstance(r, Exception):
            raise r
        return r, {"fake": True, "text": r}, {"usd": 0.0, "stop_reason": "end_turn"}


@pytest.fixture
def fake():
    return FakeCall
