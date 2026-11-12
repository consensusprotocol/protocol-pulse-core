"""FAMILY 3 - authorisation mutations (law L-j: release is authorised on THESE bytes; fail closed).

One complete clean candidate run (adv_helpers.release_run: both finals at release dimensions, EDL, manifests,
contact sheets, GATE_REPORT with rows / evidence / measured digests, verification pack, ATTESTATION) is
authorised and delivered (the control). Every mutation the order names must then REFUSE through both public
entry points: release_auth.authorise (attest + authorise) AND telegram.deliver_run (nothing is sent; the sender
is injected, no network):
  a missing required gate          every REQUIRED row of both formats deleted, one at a time
  an extra unknown gate            unlisted rows, case / whitespace / lookalike variants of real rows
  a row that says 'PASS (waived)'  and every other non-exact verdict
  an empty evidence list           the whole evidence, a format's, a row's; non-int / zero / NaN samples
  a digest of a different file     in the attestation and in the gates' measured digests
  16:9 authorised, 9:16 swapped    replaced after attestation, finals swapped, swapped DURING delivery
  a skipped gate                   SKIPPED, with and without forged execution evidence
  a stale manifest                 edited after the gates measured it, replaced by an older one after attestation
plus the run-level ones (not deliverable, did not end clean, registry changed, another run's attestation).
"""
import copy
import json
import math
import os
import shutil

import pytest

import adv_helpers as H

RA = pytest.importorskip("release_auth")
TG = pytest.importorskip("telegram")
CLEAN = {"ok": True, "why": []}


class Sender:
    """telegram.deliver_run's send(kind, path, fields, data): records what would have gone out."""

    def __init__(self, on_send=None):
        self.sent, self.on_send = [], on_send

    def __call__(self, kind, path, fields, data=None):
        self.sent.append({"kind": kind, "name": os.path.basename(path or ""), "sha256": None if data is None
                          else __import__("hashlib").sha256(data).hexdigest()})
        if self.on_send:
            self.on_send(len(self.sent), kind)
        return len(self.sent)


def refused(rd):
    """authorise refuses and deliver_run sends nothing (it raises before the first send)."""
    ok, why, _ = RA.authorise(rd)
    assert not ok, "authorised"
    s = Sender()
    with pytest.raises(RuntimeError):
        TG.deliver_run(rd, send=s)
    assert s.sent == [], s.sent
    return why


def attested_hold(rd):
    att = RA.attest(rd, CLEAN)
    assert att["verdict"] == "HOLD", att
    return refused(rd)


@pytest.fixture
def parent(tmp_path):
    return str(tmp_path)


def mutate_report(parent, fn):
    rd = H.release_run(parent, attest=False)
    H.edit_json(os.path.join(rd, "GATE_REPORT.json"), fn)
    return rd


# ─────────────────────────────── control ───────────────────────────────

def test_control_the_clean_run_is_authorised_and_delivered(parent):
    rd = H.release_run(parent)
    ok, why, att = RA.authorise(rd)
    assert ok, why
    s = Sender()
    rec = TG.deliver_run(rd, send=s)
    assert rec["status"] == "complete"
    vids = [m for m in s.sent if m["kind"] == "video"]
    assert [v["name"] for v in vids] == ["segment.mp4", "segment_vertical.mp4"]
    assert [v["sha256"] for v in vids] == [att["files"]["out/segment.mp4"], att["files"]["out/segment_vertical.mp4"]]


# ─────────────────────────────── a missing required gate ───────────────────────────────

REQUIRED = [(fmt, row) for fmt in RA.FORMATS for row in sorted(RA.INVENTORY[fmt])]


@pytest.mark.parametrize("fmt,row", REQUIRED, ids=[f"{f}-{r}" for f, r in REQUIRED])
def test_a_missing_required_gate_refuses(parent, fmt, row):
    rd = mutate_report(parent, lambda d: d["rows"][fmt].pop(row))
    attested_hold(rd)


def test_a_missing_format_refuses(parent):
    for fn in (lambda d: d["rows"].pop("9x16"), lambda d: d["rows"].__setitem__("16x9", None),
               lambda d: d["rows"].__setitem__("16x9", []), lambda d: d.__setitem__("rows", {})):
        attested_hold(mutate_report(parent, fn))


# ─────────────────────────────── an extra unknown gate ───────────────────────────────

@pytest.mark.parametrize("extra", ["G21_new", "g5_tech", " G5_tech", "G5_tech ", "G5_TECH",
                                   "G3b_cut_out_clean(run_gates)", "G5_tеch", "V1_visual_checklist_v2", ""])
def test_an_extra_unknown_gate_refuses(parent, extra):
    rd = mutate_report(parent, lambda d: (d["rows"]["16x9"].__setitem__(extra, "PASS"),
                                          d["evidence"]["16x9"].__setitem__(extra, {"executed": True, "samples": 3})))
    attested_hold(rd)


# ─────────────────────────────── 'PASS (waived)' and every other non-exact verdict ───────────────────────────────

@pytest.mark.parametrize("verdict", ["PASS (waived)", "PASS ", " PASS", "pass", "Pass", "PASS\n", "PASS*",
                                     "PASS/WAIVED", "WAIVED", "PАSS", "PASS (L-c: proved)", "PASSED", "OK",
                                     "SKIPPED", "LIMITED", "HOLD", "FAIL", "", True, 1, ["PASS"], {"v": "PASS"}, None])
def test_a_required_row_that_is_not_exactly_pass_refuses(parent, verdict):
    rd = mutate_report(parent, lambda d: d["rows"]["9x16"].__setitem__("G20_signoff_names_all", verdict))
    attested_hold(rd)


def test_a_monitoring_row_reported_with_a_waiver_string_refuses(parent):
    rd = mutate_report(parent, lambda d: d["rows"]["16x9"].__setitem__("G1_voice", "PASS (waived)"))
    attested_hold(rd)


# ─────────────────────────────── an empty evidence list ───────────────────────────────

@pytest.mark.parametrize("label,fn", [
    ("evidence = []", lambda d: d.__setitem__("evidence", [])),
    ("evidence = {}", lambda d: d.__setitem__("evidence", {})),
    ("evidence missing", lambda d: d.pop("evidence")),
    ("format evidence = []", lambda d: d["evidence"].__setitem__("16x9", [])),
    ("row evidence = []", lambda d: d["evidence"]["9x16"].__setitem__("G18_word_for_word", [])),
    ("samples = []", lambda d: d["evidence"]["16x9"].__setitem__("G16_sentence_boundary",
                                                                 {"executed": True, "samples": []})),
    ("samples = 0", lambda d: d["evidence"]["16x9"]["G8_sharpness"].__setitem__("samples", 0)),
    ("samples = -1", lambda d: d["evidence"]["16x9"]["G8_sharpness"].__setitem__("samples", -1)),
    ("samples = 3.0", lambda d: d["evidence"]["16x9"]["G8_sharpness"].__setitem__("samples", 3.0)),
    ("samples = NaN", lambda d: d["evidence"]["16x9"]["G8_sharpness"].__setitem__("samples", math.nan)),
    ("samples = '3'", lambda d: d["evidence"]["16x9"]["G8_sharpness"].__setitem__("samples", "3")),
    ("samples = True", lambda d: d["evidence"]["16x9"]["G8_sharpness"].__setitem__("samples", True)),
    ("executed = 'true'", lambda d: d["evidence"]["16x9"]["G8_sharpness"].__setitem__("executed", "true")),
    ("executed = 1", lambda d: d["evidence"]["16x9"]["G8_sharpness"].__setitem__("executed", 1))])
def test_empty_or_malformed_evidence_refuses(parent, label, fn):
    attested_hold(mutate_report(parent, fn))


# ─────────────────────────────── a digest of a different file ───────────────────────────────

def test_an_attested_digest_of_a_different_file_refuses(parent):
    rd = H.release_run(parent)
    other = H.sha256(os.path.join(rd, "out", "segment_vertical.mp4"))
    H.edit_json(os.path.join(rd, "ATTESTATION.json"), lambda d: d["files"].__setitem__("out/segment.mp4", other))
    why = refused(rd)
    assert any("out/segment.mp4" in w for w in why), why


def test_the_two_finals_digests_swapped_in_the_attestation_refuses(parent):
    rd = H.release_run(parent)

    def swap(d):
        f = d["files"]
        f["out/segment.mp4"], f["out/segment_vertical.mp4"] = f["out/segment_vertical.mp4"], f["out/segment.mp4"]
    H.edit_json(os.path.join(rd, "ATTESTATION.json"), swap)
    refused(rd)


def test_gates_that_measured_a_different_file_hold(parent):
    rd = mutate_report(parent, lambda d: d["measured_files"].__setitem__("out/segment_vertical.mp4",
                                                                          H.sha256(H.other_vertical())))
    why = attested_hold(rd)
    assert any("not the bytes the gates measured" in w for w in json.load(
        open(os.path.join(rd, "ATTESTATION.json")))["other_blockers"]), why


# ─────────────────────────────── 16:9 authorised, 9:16 swapped ───────────────────────────────

def test_the_9x16_replaced_after_authorisation_refuses_and_nothing_is_sent(parent):
    rd = H.release_run(parent)
    assert RA.authorise(rd)[0]
    shutil.copy(H.other_vertical(), os.path.join(rd, "out", "segment_vertical.mp4"))
    why = refused(rd)                                   # the 16:9 is NOT sent either
    assert any("segment_vertical.mp4" in w for w in why), why


def test_the_two_finals_swapped_on_disk_refuses(parent):
    rd = H.release_run(parent)
    a, b = os.path.join(rd, "out", "segment.mp4"), os.path.join(rd, "out", "segment_vertical.mp4")
    tmp = a + ".tmp"
    os.replace(a, tmp)
    os.replace(b, a)
    os.replace(tmp, b)
    refused(rd)


def test_the_9x16_swapped_during_delivery_never_reaches_the_chat(parent):
    """The 16:9 goes out, then the 9:16 on disk is replaced: what is sent as the 9:16 must still be exactly the
    attested bytes (deliver_run reads and verifies every payload before the first send)."""
    rd = H.release_run(parent)
    att = RA.authorise(rd)[2]
    # NOTE: this pins deliver_run's contract that EVERY payload is read and verified before the first send (the
    # bytes sent are the bytes verified, never a re-read path). If delivery is ever refactored to stream payloads
    # one by one, this swap must still never reach the chat (audit A, Gemini UI-2).
    swapped = []

    def swap(n, kind):
        if kind == "video" and not swapped:                    # right after the first VIDEO goes out (the 16:9)
            shutil.copy(H.other_vertical(), os.path.join(rd, "out", "segment_vertical.mp4"))
            swapped.append(n)
    s = Sender(on_send=swap)
    try:
        TG.deliver_run(rd, send=s)
    except RuntimeError:                                       # a delivery that re-verifies before each send and
        pass                                                   # refuses the swapped 9:16 is also correct
    H.control(len(swapped) == 1 and s.sent[swapped[0] - 1]["name"] == "segment.mp4",
              f"the swap happened right after the 16:9 went out: {s.sent}")
    vert = [m for m in s.sent if m["name"] == "segment_vertical.mp4"]
    assert all(m["sha256"] == att["files"]["out/segment_vertical.mp4"] for m in vert), vert


# ─────────────────────────────── a skipped gate ───────────────────────────────

@pytest.mark.parametrize("forged", [False, True])
def test_a_skipped_required_gate_refuses(parent, forged):
    ev = {"executed": True, "samples": 3} if forged else {"executed": False, "samples": 0}
    rd = mutate_report(parent, lambda d: (d["rows"]["16x9"].__setitem__("G12_credits", "SKIPPED"),
                                          d["evidence"]["16x9"].__setitem__("G12_credits", ev)))
    attested_hold(rd)


# ─────────────────────────────── a stale manifest ───────────────────────────────

def test_a_manifest_edited_after_the_gates_measured_it_holds(parent):
    rd = H.release_run(parent, attest=False)
    H.edit_json(os.path.join(rd, "qa", "concat_manifest_9x16.json"),
                lambda d: d["segments"][0].__setitem__("end", 0.45))
    attested_hold(rd)


def test_an_older_manifest_put_back_after_attestation_refuses(parent):
    old = H.release_run(parent)
    H.edit_json(os.path.join(old, "qa", "concat_manifest_16x9.json"),
                lambda d: d["segments"].insert(1, {"label": "clip_01", "type": "talking_head", "start": 0.5,
                                                   "end": 0.5}))
    rd = H.release_run(parent)
    shutil.copy(os.path.join(old, "qa", "concat_manifest_16x9.json"),
                os.path.join(rd, "qa", "concat_manifest_16x9.json"))
    why = refused(rd)
    assert any("concat_manifest_16x9.json" in w for w in why), why


def test_gates_that_measured_a_stale_manifest_hold(parent):
    rd = mutate_report(parent, lambda d: d["measured_files"].__setitem__("qa/concat_manifest_16x9.json", "0" * 64))
    attested_hold(rd)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Grok47-select F8 (OPEN): the EDL the drop is described from is bound at "
                                       "attestation but never proven to be the EDL the gates measured; REQUESTS.md R-12")
def test_an_edl_changed_after_the_gates_ran_holds(parent):
    """The finals and manifests must be the bytes the gates measured; the EDL (locks read by G16 / G18, channels
    read by G15 / G20, headline and credits of the drop) must be too: here another headline and another credited
    channel replace the gated ones before the attestation is written."""
    rd = H.release_run(parent, attest=False)
    H.edit_json(os.path.join(rd, "edl.json"), lambda d: (d.__setitem__("headline", "Bitcoin price surges past "
                                                                                    "$90,000"),
                                                         d["clips"][0].__setitem__("channel", "Coin Bureau")))
    att = RA.attest(rd, CLEAN)
    assert att["verdict"] == "HOLD", "an EDL the gates never saw was attested ALL_PASS"


# ─────────────────────────────── the verification pack and legacy state ───────────────────────────────

@pytest.mark.parametrize("label,fn", [
    ("built without vision", lambda d: d.__setitem__("vision", False)),
    ("vision a string", lambda d: d.__setitem__("vision", "true")),
    ("incomplete", lambda d: d.__setitem__("complete", False)),
    ("complete missing", lambda d: d.pop("complete")),
    ("complete a string", lambda d: d.__setitem__("complete", "yes")),
    ("not a mapping", None)])
def test_a_pack_without_vision_or_incomplete_refuses(parent, label, fn):
    """GPT-gates F08 / F09, Claude-gates V9 / V10: a pack built without the vision check, or incomplete, is a
    waiver switch; release refuses it."""
    rd = H.release_run(parent, attest=False)
    p = os.path.join(rd, "VERIFY", "VERIFICATION.json")
    if fn is None:
        with open(p, "w") as f:
            json.dump(["complete", "vision"], f)
    else:
        H.edit_json(p, fn)
    attested_hold(rd)


def test_a_missing_pack_refuses(parent):
    rd = H.release_run(parent, attest=False)
    os.remove(os.path.join(rd, "VERIFY", "VERIFICATION.json"))
    attested_hold(rd)


def test_legacy_markers_authorise_nothing(parent):
    """GPT-gates F11 / Claude-gates C3 / Grok-gates 15: a run killed before its attestation, carrying the legacy
    markers (VERIFIED_BY_ORCHESTRATOR, gate_results_*.json all_pass, no GATE_FAIL.txt), is never authorised."""
    rd = H.release_run(parent, attest=False)
    open(os.path.join(rd, "out", "VERIFIED_BY_ORCHESTRATOR_16x9"), "w").close()
    for fmt in RA.FORMATS:
        with open(os.path.join(rd, "qa", f"gate_results_{fmt}.json"), "w") as f:
            json.dump({"all_pass": True, "format": fmt}, f)
    refused(rd)


def test_the_legacy_send_path_is_gone():
    """GPT-gates F03 / Claude-gates X5: the old entry point cannot send anything."""
    with pytest.raises(RuntimeError):
        TG.send_telegram_preview("run_dir", "caption")


# ─────────────────────────────── run-level ───────────────────────────────

def test_a_replay_or_an_unclean_run_refuses(parent):
    rd = H.release_run(parent, attest=False)
    RA.attest(rd, CLEAN, deliverable=False, why_not="replay")
    refused(rd)
    for state in ({"ok": False, "why": ["hold: G16"]}, {"ok": "true"}, {}, None):
        rd = H.release_run(parent, attest=False)
        RA.attest(rd, state)
        refused(rd)


def test_a_run_without_an_attestation_refuses(parent):
    """GPT-cut F25: a killed or crashed run has no attestation and is never sent."""
    rd = H.release_run(parent, attest=False)
    refused(rd)
    with open(os.path.join(rd, "ATTESTATION.json"), "w") as f:
        f.write('{"schema": "pulse.attestation.v1"')                           # truncated JSON
    refused(rd)


def test_another_runs_attestation_copied_in_refuses(parent):
    a = H.release_run(parent)
    b = H.release_run(parent, attest=False)
    shutil.copy(H.other_vertical(), os.path.join(b, "out", "segment_vertical.mp4"))
    H.edit_json(os.path.join(b, "GATE_REPORT.json"), lambda d: d["measured_files"].__setitem__(
        "out/segment_vertical.mp4", H.sha256(os.path.join(b, "out", "segment_vertical.mp4"))))
    shutil.copy(os.path.join(a, "ATTESTATION.json"), os.path.join(b, "ATTESTATION.json"))
    refused(b)


def test_an_attestation_edited_to_all_pass_refuses(parent):
    rows = H.passing_rows(RA)
    rows["16x9"]["G18_word_for_word"] = "FAIL"
    rd = H.release_run(parent, rows=rows)
    H.edit_json(os.path.join(rd, "ATTESTATION.json"), lambda d: (d.__setitem__("verdict", "ALL_PASS"),
                                                                 d["rows"]["16x9"].__setitem__("G18_word_for_word", "PASS")))
    refused(rd)


def test_a_partially_delivered_run_is_never_resent_automatically(parent):
    rd = H.release_run(parent)

    def boom(n, kind):
        if n == 1:
            raise ConnectionError("network dropped after the request")
    with pytest.raises(ConnectionError):
        TG.deliver_run(rd, send=Sender(on_send=boom))
    s = Sender()
    with pytest.raises(RuntimeError):
        TG.deliver_run(rd, send=s)
    assert s.sent == []
