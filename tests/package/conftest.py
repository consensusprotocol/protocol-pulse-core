"""RULING 115: THE RIGS' HOOK BAR. Every test under tests/package judges hooks on a calibrated bar whose floors are
PINNED here: the floors ruling 115's calibration measured at 13:07 ET Nov 15 (scroll 3, alone 4, setup 3), for the
rigs' own rater name, "xai:grok". A daily re-calibration may move production's floors; it never moves a rig's
verdict. The fixture patches only package._live_bar: hook_bar's own functions, which tests/package/test_hook_bar.py
tests on files of its own (and that the live file's floors are derived from their source), are never touched. A test
class that needs production's calibration file sets `real_hook_bar = True`."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "pipeline"))
import package as PK  # noqa: E402

RIG_RATER = "xai:grok"
RIG_FLOORS = {"scroll": 3, "alone": 4, "setup": 3}


def rig_bar():
    return {"floors": dict(RIG_FLOORS), "sha256": "t" * 64, "rater": RIG_RATER,
            "question_version": PK.HOOK_VERSION, "seed": PK.HOOK_SEED, "measured_at": "2026-11-15T18:07:52+00:00"}


@pytest.fixture(autouse=True)
def _rig_hook_bar(request, monkeypatch):
    if getattr(request.cls, "real_hook_bar", False):
        yield
        return
    bar = rig_bar()
    monkeypatch.setattr(PK, "_live_bar", lambda: (bar, None))
    yield
