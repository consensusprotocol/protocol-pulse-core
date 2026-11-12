#!/usr/bin/env python3
"""pipeline/release_auth.py — the ONE answer to "may this exact file be sent as passing" (red-team 2026-11-11, A).

FAIL CLOSED: absent, empty, malformed, mistyped or unexpected evidence is never a pass.
  inventory   a versioned, exact set of gate rows per format: REQUIRED rows (INVENTORY) decide release and pass only
              when their verdict is exactly "PASS" (no prefixes, no waiver strings); MONITORING rows (gates without
              a passing fixture, a failing fixture and a missing-evidence answer: addendum '22:15' item 4) must be
              present with an exact verdict and are reported, not deciding; the few known non-blocking rows are
              enumerated with their allowed verdicts (NONBLOCKING); any other row, a missing row, or a verdict
              outside VERDICTS is a failure
  evidence    every row records that it executed and on how many samples (>= 1)
  attestation run_fresh writes ATTESTATION.json LAST (after the verification pack and provenance) from what is on
              disk: the rows, the evidence, the pack's strict result, the run's terminal state (any hold, code
              not at the launch revision = not ok), and the sha256 of both finals, the EDL, both manifests,
              GATE_REPORT.json, VERIFICATION.json and both contact sheets; the finals and manifests must be the
              bytes the gates measured (GATE_REPORT measured_files). A replay is attested but never deliverable.
  authorise   re-derives the verdict from the attested rows, re-reads GATE_REPORT.json and VERIFICATION.json, and
              recomputes every digest NOW; delivery calls it before the first send and checks each file's digest
              again immediately before sending it (telegram.deliver_run). Every send path goes through here; a run
              without an attestation (killed, crashed, older code) is never authorised.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

SCHEMA = "pulse.attestation.v1"
INVENTORY_VERSION = 1
VERDICTS = ("PASS", "FAIL", "HOLD", "SKIPPED", "LIMITED")
# Orchestrator addendum '22:15' item 4: a gate DECIDES release (REQUIRED) only with a real passing fixture, a
# realistic failing fixture and a defined answer to missing evidence (here: no executed sample = blocker). Every
# other gate is MONITORING: it must be present with an exact verdict (it is reported), but its verdict does not
# decide release until it has all three. The per-gate fixture table is in docs/audits/DEFINITION_OF_DONE_PULSE_CHECK.md
# ("REQUIRED / MONITORING"). No gate is deleted.
_REQUIRED = ("G3b_cut_out_clean", "G3c_acoustic_tail", "G4s_layout_truth", "G5_tech", "G8_sharpness", "G9_tail",
             "outro_locked", "G12_credits", "G15_credits", "G16_sentence_boundary", "G17_onset_tail",
             "G18_word_for_word", "G19_edge_shots", "G20_signoff_names_all", "V1_visual_checklist")
_MONITORING = ("G1_voice", "G2_watermark", "G3_cuts", "G4_faces", "G4_faces_per_shot", "G6_preroll", "G10_chyron",
               "G13_vo_audible")
INVENTORY = {"16x9": frozenset(_REQUIRED + ("G14_av_alignment",)),
             "9x16": frozenset(_REQUIRED + ("G14_audio_offset", "vertical_silent_fallback"))}
MONITORING = {"16x9": frozenset(_MONITORING),
              "9x16": frozenset(_MONITORING + ("G11_parity", "G14c_duration_parity"))}
NONBLOCKING = {"16x9": {}, "9x16": {"G14_frame_similarity": frozenset({"LIMITED"})}}   # known limitation, not a pass
FORMATS = ("16x9", "9x16")
REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")
BOUND = ("out/segment.mp4", "out/segment_vertical.mp4", "edl.json", "qa/concat_manifest_16x9.json",
         "qa/concat_manifest_9x16.json", "GATE_REPORT.json", "VERIFY/VERIFICATION.json",
         "qa/contact_sheet_16x9.jpg", "qa/contact_sheet_9x16.jpg")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


NO_EVIDENCE_CHECK = object()     # only for a rows-only question (a unit test of verdict rules); never on release


def blockers(fmt, rows, evidence):
    """{row: why} for one format; empty only when the rows satisfy the inventory exactly: every REQUIRED row is
    exactly "PASS" with execution evidence, every MONITORING row is present with an exact verdict (reported, not
    deciding), the enumerated non-blocking rows carry their allowed verdict, and no other row exists."""
    if fmt not in INVENTORY or not isinstance(rows, dict):
        return {"format": f"unknown format {fmt!r} or rows not a mapping"}
    bad = {}
    allowed = INVENTORY[fmt] | MONITORING[fmt] | set(NONBLOCKING[fmt])
    for k in sorted(set(rows) - allowed):
        bad[k] = f"unexpected gate row (not in inventory v{INVENTORY_VERSION})"
    for k in sorted(INVENTORY[fmt]):
        v = rows.get(k)
        if v is None:
            bad[k] = "required gate row missing"
        elif not isinstance(v, str) or v not in VERDICTS:
            bad[k] = f"verdict {v!r} is not one of {VERDICTS}"
        elif v != "PASS":
            bad[k] = v
    for k in sorted(MONITORING[fmt]):
        if not (isinstance(rows.get(k), str) and rows[k] in VERDICTS):
            bad[k] = f"monitoring row must be reported with one of {VERDICTS}, got {rows.get(k)!r}"
    for k, ok in NONBLOCKING[fmt].items():
        if not (isinstance(rows.get(k), str) and rows[k] in ok):       # an unhashable value never crashes here
            bad[k] = f"non-blocking row must be one of {sorted(ok)}, got {rows.get(k)!r}"
    if evidence is not NO_EVIDENCE_CHECK:            # GPT audit #1: absent or malformed evidence is NO evidence
        ev = evidence.get(fmt) if isinstance(evidence, dict) else None
        ev = ev if isinstance(ev, dict) else {}
        for k in sorted(INVENTORY[fmt]):
            e = ev.get(k)
            if not (isinstance(e, dict) and e.get("executed") is True and type(e.get("samples")) is int
                    and e["samples"] >= 1):
                bad.setdefault(k, f"no execution evidence (executed True, samples >= 1): {e!r}")
    return bad


def monitoring_report(rows):
    """{fmt: {row: verdict}} of the MONITORING rows that did not pass (shown with a delivery, never deciding)."""
    return {fmt: {k: (rows.get(fmt) or {}).get(k) for k in sorted(MONITORING[fmt])
                  if (rows.get(fmt) or {}).get(k) != "PASS"} for fmt in FORMATS}


def verification_ok(pack):
    """The verification pack is complete (every frame, sheet, credits row and both G18 tables) and was built WITH
    the vision check (a pack without it is a waiver switch: GPT-gates F08, Claude-gates V9). The visual verdict
    itself is the V1 row, which decides release only when V1 is in the REQUIRED inventory."""
    if not isinstance(pack, dict):
        return False, ["verification pack missing or not a mapping"]
    why = []
    if pack.get("vision") is not True:
        why.append("pack built without the vision check")
    if pack.get("complete") is not True:
        why.append("pack incomplete")
    return not why, why


def _gate_report(run_dir):
    return json.load(open(os.path.join(run_dir, "GATE_REPORT.json")))


def attest(run_dir, run_state, deliverable=True, why_not=None):
    """Write ATTESTATION.json (atomically) from what is ON DISK: GATE_REPORT.json (rows, evidence, the digests
    the gates measured), VERIFY/VERIFICATION.json and the digests of every bound file now. verdict ALL_PASS
    only when both formats satisfy the inventory, the pack passed, the files the gates measured are unchanged,
    every bound file exists and the run itself ended clean (run_state["ok"] is True: no hold anywhere, code at
    the launch revision). A run that is not deliverable (a replay is diagnostic) is recorded with why_not and is
    never authorised, whatever its verdict."""
    why = []
    try:
        rep = _gate_report(run_dir)
    except (OSError, ValueError) as e:
        rep = {}
        why.append(f"GATE_REPORT.json unreadable: {type(e).__name__}")
    rows, evidence = rep.get("rows") or {}, rep.get("evidence")
    bad = {fmt: blockers(fmt, rows.get(fmt), evidence) for fmt in FORMATS}
    try:
        pack = json.load(open(os.path.join(run_dir, "VERIFY", "VERIFICATION.json")))
    except (OSError, ValueError):
        pack = None
    v_ok, v_why = verification_ok(pack)
    files = {rel: (sha256(os.path.join(run_dir, rel)) if os.path.isfile(os.path.join(run_dir, rel)) else None)
             for rel in BOUND}
    missing = [rel for rel, d in files.items() if d is None]
    measured = rep.get("measured_files") or {}
    for rel in ("out/segment.mp4", "out/segment_vertical.mp4", "qa/concat_manifest_16x9.json",
                "qa/concat_manifest_9x16.json"):
        if measured.get(rel) is None or measured.get(rel) != files.get(rel):
            why.append(f"{rel}: not the bytes the gates measured")
    if rep.get("inventory_version") != INVENTORY_VERSION:
        why.append(f"gate report inventory version {rep.get('inventory_version')!r} != {INVENTORY_VERSION}")
    if not (isinstance(run_state, dict) and run_state.get("ok") is True):
        why.append("run did not end clean: " + "; ".join(map(str, (run_state or {}).get("why") or ["no state"])))
    ok = not any(bad.values()) and v_ok and not missing and not why
    att = {"schema": SCHEMA, "inventory_version": INVENTORY_VERSION, "verdict": "ALL_PASS" if ok else "HOLD",
           "deliverable": bool(deliverable), "why_not_deliverable": why_not, "run_state": run_state,
           "registry_sha256": sha256(REGISTRY) if os.path.isfile(REGISTRY) else None,   # the drop's handles / urls
           "rows": rows, "evidence": evidence, "notes": rep.get("notes") or {}, "blockers": bad,
           "verification": {"ok": v_ok, "why": v_why}, "other_blockers": why, "missing_files": missing,
           "files": files, "created_at": datetime.now(timezone.utc).isoformat()}
    tmp = os.path.join(run_dir, "ATTESTATION.json.tmp")
    with open(tmp, "w") as f:
        json.dump(att, f, indent=2, default=str)
    os.replace(tmp, os.path.join(run_dir, "ATTESTATION.json"))
    return att


def authorise(run_dir):
    """(ok, reasons, attestation). ok only when ATTESTATION.json is ALL_PASS and deliverable, its rows re-check
    clean here, GATE_REPORT.json still carries exactly those rows and evidence, the verification pack still
    passes, the run ended clean, and every bound file's sha256 equals the attested digest NOW."""
    p = os.path.join(run_dir, "ATTESTATION.json")
    try:
        att = json.load(open(p))
    except (OSError, ValueError) as e:
        return False, [f"no readable attestation: {type(e).__name__}"], None
    if not isinstance(att, dict) or att.get("schema") != SCHEMA or att.get("inventory_version") != INVENTORY_VERSION:
        return False, ["attestation schema / inventory version mismatch"], att
    why = []
    if att.get("verdict") != "ALL_PASS":
        why.append(f"attestation verdict {att.get('verdict')!r}")
    if att.get("deliverable") is not True:
        why.append(f"not deliverable: {att.get('why_not_deliverable')}")
    if not (isinstance(att.get("run_state"), dict) and att["run_state"].get("ok") is True):
        why.append("the run did not end clean")
    rows, evidence = att.get("rows") or {}, att.get("evidence")
    for fmt in FORMATS:
        for k, v in blockers(fmt, rows.get(fmt), evidence).items():
            why.append(f"{fmt} {k}: {v}")
    try:
        rep = _gate_report(run_dir)
        if rep.get("rows") != rows or rep.get("evidence") != evidence:
            why.append("GATE_REPORT.json rows / evidence differ from the attested ones")
    except (OSError, ValueError):
        why.append("GATE_REPORT.json unreadable")
    try:
        v_ok, v_why = verification_ok(json.load(open(os.path.join(run_dir, "VERIFY", "VERIFICATION.json"))))
        why += [] if v_ok else v_why
    except (OSError, ValueError):
        why.append("VERIFICATION.json unreadable")
    if not att.get("registry_sha256") or not os.path.isfile(REGISTRY) or sha256(REGISTRY) != att["registry_sha256"]:
        why.append("the channel registry changed since it was attested")
    files = att.get("files") or {}
    if set(files) != set(BOUND):
        why.append("attested file set differs from the bound set")
    for rel in BOUND:
        path = os.path.join(run_dir, rel)
        if not files.get(rel):
            why.append(f"{rel}: no attested digest")
        elif not os.path.isfile(path):
            why.append(f"{rel}: missing")
        elif sha256(path) != files[rel]:
            why.append(f"{rel}: changed since it was attested")
    return not why, why, att


def check_file(run_dir, att, rel):
    """True when `rel` still has its attested digest (delivery checks this immediately before each send)."""
    path = os.path.join(run_dir, rel)
    return bool(att and att.get("files", {}).get(rel)) and os.path.isfile(path) and sha256(path) == att["files"][rel]
