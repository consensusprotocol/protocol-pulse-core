"""RULING 115: THE RIGS' HOOK BAR. Every test under tests/package judges hooks on a calibrated bar whose floors are
PINNED here: the floors ruling 115's calibration measured at 13:07 ET Nov 15 (scroll 3, alone 4, setup 3), for the
rigs' own rater name, "xai:grok". A daily re-calibration may move production's floors; it never moves a rig's
verdict. The fixture patches only package._live_bar: hook_bar's own functions, which tests/package/test_hook_bar.py
tests on files of its own (and that the live file's floors are derived from their source), are never touched. A test
class that needs production's calibration file sets `real_hook_bar = True`. RULING 116: the same for the line-up bar
(package._live_lineup_bar): RIG_LINEUP's floors (every clip after the hook >= 3, the VO point >= 3) for the rigs'
rater, so a rig verdict given as "xai:grok" is judged on the calibrated bar and any other back-end on the standard."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "pipeline"))
import package as PK  # noqa: E402

RIG_RATER = "xai:grok"
RIG_FLOORS = {"scroll": 3, "alone": 4, "setup": 3}
RIG_LINEUP = {"clips_alone": {"clip": 3}, "coherence": {"clip": 3, "vo_point": 3}}   # RULING 116's floors, pinned


def rig_bar():
    return {"floors": dict(RIG_FLOORS), "sha256": "t" * 64, "rater": RIG_RATER,
            "question_version": PK.HOOK_VERSION, "seed": PK.HOOK_SEED, "measured_at": "2026-11-15T18:07:52+00:00"}


def rig_lineup_bar():
    return dict({k: dict(v) for k, v in RIG_LINEUP.items()}, rater=RIG_RATER, sha256="l" * 64, valid_h=None)


@pytest.fixture(autouse=True)
def _rig_hook_bar(request, monkeypatch):
    if getattr(request.cls, "real_hook_bar", False):
        yield
        return
    bar, lbar = rig_bar(), rig_lineup_bar()
    monkeypatch.setattr(PK, "_live_bar", lambda: (bar, None))
    monkeypatch.setattr(PK, "_live_lineup_bar", lambda: (lbar, None))   # ruling 116: the rigs' line-up bar
    yield


@pytest.fixture(autouse=True)
def _driver_under_test(monkeypatch):
    """VERIFIER ROWS 12 / 16 (Nov 24): proof_ledger.main refuses any entry but its own file run as __main__; inside
    pytest, with this variable set here, the tests may call main() (the build record then says under_test)."""
    monkeypatch.setenv("PP_SELECTID_DRIVER_UNDER_TEST", "1")
    yield


@pytest.fixture(autouse=True)
def _outcomes_off_the_real_file(monkeypatch, tmp_path):
    """RULING 160 (2b): a test's driver run writes its outcome line into a file of its own, never into the real
    data/builds/outcomes.jsonl (tests that ran main() on a temporary record folder appended lines to it, Nov 24)."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import outcomes
    monkeypatch.setattr(outcomes, "OUTCOMES", str(tmp_path / "outcomes.jsonl"))
    yield
