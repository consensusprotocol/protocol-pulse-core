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
import re
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
# RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17): TWO CLASSES. A HARD row refuses (blockers, as before). A
# SOFT row of the inventory scores and FLAGS: its failure is said in plain words at the top of the Telegram note
# ('REVIEW FLAGS: ...') and never refuses; PBX decides. HARD: the words (G18, G3b), a cut mid-word (G17), speaker credit
# (G12, G15, G20), a crop through a face or burned text (G4s), a layout that cannot render and the runtime (G5), the
# locked outro (outro_locked). SOFT, ruling 137 (2)'s default: every other inventory row. V1's credits line repeats
# G12 / G15 / G20, which stay HARD.
SOFT = {"16x9": frozenset({"G3c_acoustic_tail", "G8_sharpness", "G9_tail", "G16_sentence_boundary", "G19_edge_shots",
                           "V1_visual_checklist", "G14_av_alignment"}),
        "9x16": frozenset({"G3c_acoustic_tail", "G8_sharpness", "G9_tail", "G16_sentence_boundary", "G19_edge_shots",
                           "V1_visual_checklist", "G14_audio_offset", "vertical_silent_fallback"})}
FLAG_TEXT = {      # ruling 138 (3): what the check doubted, about which clip, one plain sentence, no codes. {who}: the
    #                clips the gate report names ("a clip" when it names none); review_flags says the version.
    "G3c_acoustic_tail": "{who} might not end in silence (a breath or the next word may be heard at its end)",
    "G8_sharpness": "{who} looks softer than its source",
    "G9_tail": "the outro at the end {what}",
    "G16_sentence_boundary": "{who} might start or end in the middle of a sentence",
    "G19_edge_shots": "the picture cuts to another shot right at an edge of {who}",
    "V1_visual_checklist": "the vision check doubted that {what}",
    "G14_av_alignment": "the sound and picture of {who} might be slightly out of sync",
    "G14_audio_offset": "the sound of {who} might be slightly out of sync",
    "vertical_silent_fallback": "the picture fell back to a letterbox"}
CHECK_NAME = {"G3c_acoustic_tail": "the check for silence at each clip's end", "G8_sharpness": "the sharpness check",
              "G9_tail": "the check of the outro", "G16_sentence_boundary": "the sentence-edge check",
              "G19_edge_shots": "the shot-change check", "V1_visual_checklist": "the vision check",
              "G14_av_alignment": "the sync check", "G14_audio_offset": "the sync check",
              "vertical_silent_fallback": "the letterbox check"}
V1_WORDS = {"vertical_speaker_centred": "the speaker is centred in the 9:16 frame",
            "no_letterbox_on_talking_heads": "the talking heads have no black bars",
            "letterbox per shot": "the talking heads have no black bars",
            "no_bad_boundary_frames": "no frame at a cut is frozen, black or repeated",
            "next shot before the cut": "no frame of the next shot shows before a cut",
            "watermark_present": "a watermark is visible on the clips"}
CREDITS_ROW = "credits_round_and_match"     # ruling 137 (2): speaker credit is HARD, V1's credits row with it
# Ruling 136 (2)'s cap ("only if it has no more than 3 soft flags") is the never-empty SEAL's (the builder's): a render
# lists every soft flag it finds and never holds on them, because a SOFT gate "scores and FLAGS, it does not refuse".
FORMATS = ("16x9", "9x16")
REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")
BOUND = ("out/segment.mp4", "out/segment_vertical.mp4", "edl.json", "qa/concat_manifest_16x9.json",
         "qa/concat_manifest_9x16.json", "GATE_REPORT.json", "VERIFY/VERIFICATION.json",
         "qa/contact_sheet_16x9.jpg", "qa/contact_sheet_9x16.jpg")
# ruling 93 as amended (orchestrator 2026-11-14 '21:10'): a run releases the formats its pin SEALED (the EDL's
# 'formats', written by run_fresh.stage_pinned from moments_package["formats"]; absent = both). A format outside that
# set is neither attested nor bound nor sent, whatever its rows say; the set never follows the gates' outcome.
FORMAT_FILES = {"16x9": ("out/segment.mp4", "qa/concat_manifest_16x9.json", "qa/contact_sheet_16x9.jpg"),
                "9x16": ("out/segment_vertical.mp4", "qa/concat_manifest_9x16.json", "qa/contact_sheet_9x16.jpg")}
FORMAT_SETS = (("16x9",), FORMATS)


def release_formats(edl):
    """The formats this run may release: FORMATS when the EDL has no 'formats', else exactly ('16x9',) or FORMATS
    from a list in that order. Anything else (or an EDL that is not an object) raises ValueError."""
    if not isinstance(edl, dict):
        raise ValueError("the EDL is not an object")
    if "formats" not in edl:
        return FORMATS
    f = edl["formats"]
    if not (isinstance(f, list) and all(isinstance(x, str) for x in f) and tuple(f) in FORMAT_SETS):
        raise ValueError(f"EDL formats {f!r} is not one of {[list(s) for s in FORMAT_SETS]}")
    return tuple(f)


def package_formats(mp):
    """The formats a moments package SEALS (moments_package["formats"], inside package_sha256, the spelling agreed
    with the builder 2026-11-14): None when absent (both), else exactly ['16x9'] or ['16x9', '9x16']; anything else
    raises ValueError. run_fresh's pinned stage copies it into the EDL (pinned.py is an input of the pre-check's
    decoder sha, so the copy is not made there)."""
    if not isinstance(mp, dict) or "formats" not in mp:
        return None
    try:
        return list(release_formats({"formats": mp["formats"]}))
    except ValueError:
        raise ValueError(f"moments_package formats {mp['formats']!r} is not one of "
                         f"{[list(s) for s in FORMAT_SETS]} (absent = both)") from None


def bound(formats):
    """The files an attestation of `formats` binds: those formats' finals, manifests and sheets, plus the EDL, the
    gate report and the verification pack."""
    drop = {rel for fmt in FORMATS if fmt not in formats for rel in FORMAT_FILES[fmt]}
    return tuple(rel for rel in BOUND if rel not in drop)


def _edl_formats(run_dir):
    try:
        with open(os.path.join(run_dir, "edl.json")) as f:
            return release_formats(json.load(f)), None
    except (OSError, ValueError) as e:
        return None, f"release formats unreadable: {type(e).__name__}: {e}"


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
    soft = SOFT.get(fmt, frozenset())
    allowed = INVENTORY[fmt] | MONITORING[fmt] | set(NONBLOCKING[fmt])
    for k in sorted(set(rows) - allowed):
        bad[k] = f"unexpected gate row (not in inventory v{INVENTORY_VERSION})"
    for k in sorted(INVENTORY[fmt]):
        v = rows.get(k)
        if v is None:
            bad[k] = "required gate row missing"
        elif not isinstance(v, str) or v not in VERDICTS:
            bad[k] = f"verdict {v!r} is not one of {VERDICTS}"
        elif v != "PASS" and k not in soft:                # rulings 136 / 137: a SOFT row flags, never blocks
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
        for k in sorted(INVENTORY[fmt] - soft):              # a SOFT row without evidence is a flag (flags())
            e = ev.get(k)
            if not (isinstance(e, dict) and e.get("executed") is True and type(e.get("samples")) is int
                    and e["samples"] >= 1):
                bad.setdefault(k, f"no execution evidence (executed True, samples >= 1): {e!r}")
        for k in sorted(INVENTORY[fmt] & soft):     # a SOFT row that measured nothing is a flag, but its record must be
            e = ev.get(k)                           # well formed: the attestation is HARD (ruling 137 (2); F3)
            if e is not None and not (isinstance(e, dict) and type(e.get("executed")) is bool
                                      and type(e.get("samples")) is int and e["samples"] >= 0):
                bad.setdefault(k, f"malformed execution evidence (the attestation is HARD): {e!r}")
    return bad


def flags(fmt, rows, evidence, report=None, edl=None):
    """RULINGS 136 / 137: {row: plain words} for one format's SOFT rows that did not pass, or ran without execution
    evidence (never measured is said, never taken as a pass). A missing or malformed SOFT row is a blocker
    (blockers()), not a flag."""
    rows = rows if isinstance(rows, dict) else {}
    ev = evidence.get(fmt) if isinstance(evidence, dict) else None
    ev = ev if isinstance(ev, dict) else {}
    out = {}
    for k in sorted(SOFT.get(fmt, frozenset()) & INVENTORY.get(fmt, frozenset())):
        v, e = rows.get(k), ev.get(k)
        measured = isinstance(e, dict) and e.get("executed") is True and type(e.get("samples")) is int \
            and e["samples"] >= 1
        if v == "SKIPPED" or v == "PASS" and evidence is not NO_EVIDENCE_CHECK and not measured:
            out[k] = f"{CHECK_NAME.get(k, 'a check')} did not measure anything, so its result is unknown"
        elif isinstance(v, str) and v in VERDICTS and v != "PASS":
            out[k] = say(k, fmt, report, edl)
    return out


def seg_name(seg, edl):
    """'hook' / 'clip_02' -> 'the opening clip (Channel)' / 'clip 2 (Channel)': which clip, as PBX reads it (ruling
    138 (3)); None for anything else (the outro, a voiceover)."""
    edl = edl if isinstance(edl, dict) else {}
    if seg == "hook":
        h = edl.get("hook")
        return f"the opening clip ({(h.get('channel') if isinstance(h, dict) else None) or 'channel unknown'})"
    m = re.fullmatch(r"clip[_ ]0*(\d+)", str(seg))
    if not m:
        return None
    n = int(m.group(1))
    ch = next((c.get("channel") for c in edl.get("clips") or [] if isinstance(c, dict) and c.get("index") == n), None)
    return f"clip {n} ({ch or 'channel unknown'})"


def join_names(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1] if names else ""


def _failed_segments(k, fmt, rep):
    """The segments the gate report says this SOFT row failed on ([] when it does not say: G8's production table
    is not in the report)."""
    try:
        if k == "G16_sentence_boundary":
            return [e.get("segment") for e in rep.get("G16") or []
                    if e.get("errors") or any((e.get(s) or {}).get("pass") is False for s in ("in", "out"))]
        if k == "G19_edge_shots":
            return [e.get("segment") for e in (rep.get("G19") or {}).get(fmt) or [] if e.get("pass") is not True]
        if k in ("G14_av_alignment", "G14_audio_offset"):
            return [e.get("label") for e in rep.get("G14_" + fmt) or [] if e.get("status") != "PASS"]
        if k == "G3c_acoustic_tail":
            return [e[0] for e in ((rep.get("L-c") or {}).get(fmt) or {}).get("g3c_failed_edges") or []]
    except (AttributeError, TypeError, KeyError, IndexError):
        pass
    return []


def _v1_doubts(fmt, rep):
    """V1's rows a model did not affirm (no / missing), its cut and letterbox checks, by name; None: no answer."""
    v = ((rep.get("V1") or {}).get(fmt)) if isinstance(rep.get("V1"), dict) else None
    if not isinstance(v, dict) or v.get("error"):
        return None
    per = [d for d in (v.get("per_model") or {}).values() if isinstance(d, dict)] \
        if isinstance(v.get("per_model"), dict) else []
    if not per:
        return None
    out = sorted({r for d in per for r, x in ((d.get("rows") or {}).items() if isinstance(d.get("rows"), dict) else ())
                  if not (isinstance(x, dict) and x.get("ok") is True)} - {"no_next_shot_before_transition"})
    if not (v.get("boundaries") or {"ok": True}).get("ok"):
        out.append("next shot before the cut")
    if not (v.get("letterbox_per_shot") or {"ok": True}).get("ok"):
        out.append("letterbox per shot")
    if any(CREDITS_ROW not in (d.get("rows") or {}) for d in per):
        out.append(CREDITS_ROW)                                       # a model that never answered it
    return out


def v1_credit_block(fmt, rows, report):
    """Ruling 137 (2): speaker credit is HARD. A V1 that did not pass blocks when its credits row was not affirmed
    by every model (no, missing, or no answer at all); V1's other rows are SOFT flags. -> the reason, or None."""
    if not isinstance(rows, dict) or rows.get("V1_visual_checklist") in (None, "PASS") \
            or "V1_visual_checklist" not in INVENTORY.get(fmt, ()):
        return None
    d = _v1_doubts(fmt, report if isinstance(report, dict) else {})
    if d is None:
        return "the vision check gave no answer, so the credits card is unchecked (speaker credit is HARD)"
    return "the vision check doubted the credits card (speaker credit is HARD)" if CREDITS_ROW in d else None


def say(k, fmt, report=None, edl=None):
    """One SOFT row's flag in plain words (ruling 138 (3)): what the check doubted, about which clip."""
    rep = report if isinstance(report, dict) else {}
    names = []
    for s in _failed_segments(k, fmt, rep):
        n = seg_name(s, edl)
        if n and n not in names:
            names.append(n)
    what = ""
    if k == "V1_visual_checklist":
        words = []
        for r in _v1_doubts(fmt, rep) or []:
            w = V1_WORDS.get(r)
            if w and w not in words:
                words.append(w)
        what = " and that ".join(words) or "the video looks right"
    elif k == "G9_tail":
        g = (((rep.get("G9") or {}).get(fmt) or {}).get("gate") or {}) if isinstance(rep.get("G9"), dict) else {}
        bad = [w for w, ok in (("looks too dark", g.get("luma_ok")), ("sounds too loud or too quiet", g.get("audio_ok")))
               if str(ok) == "False"] if isinstance(g, dict) else []
        what = " and ".join(bad) or "might look or sound wrong"
    return FLAG_TEXT.get(k, "a check doubted the video").format(who=join_names(names) or "a clip", what=what)


def review_flags(att_flags, pin_flags):
    """The note's flags, each ONE plain sentence (ruling 138 (3)): the pin's and the render stages' as written, then each
    flagged gate once, saying the version it was seen in. Each sentence once, in order."""
    out = []
    for f in list(pin_flags or []):
        if isinstance(f, str) and f and f not in out:
            out.append(f)
    seen = {}
    for fmt in sorted(att_flags or {}):
        for row, text in (att_flags[fmt] or {}).items():
            seen.setdefault((row, text), []).append(fmt)
    for (_, text), fmts in seen.items():
        where = "both versions" if len(fmts) > 1 else f"the {fmts[0].replace('x', ':')} version"
        s = f"In {where}, {text}."
        if s not in out:
            out.append(s)
    return out


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


def _edl(run_dir):
    """edl.json (bound) for the clip names in the flags; {} when unreadable (the names say 'a clip')."""
    try:
        with open(os.path.join(run_dir, "edl.json")) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def pin_review_flags(run_dir):
    """The pin's sealed review_flags (the builder's never-empty seal, ruling 136 (2)), from PINNED_DECISION.json, or []
    (an auto run, or a pin without flags). Unreadable or malformed -> None (the caller HOLDs)."""
    p = os.path.join(run_dir, "PINNED_DECISION.json")
    if not os.path.exists(p):
        return []
    try:
        pin = json.load(open(p))["pin"]
        mp = pin.get("moments_package") or {}
        f = mp.get("review_flags", [])
        if f:                                            # bound to the attested EDL by the package digest (bar_lines' way)
            edl = json.load(open(os.path.join(run_dir, "edl.json")))
            sha = mp.get("package_sha256")
            if not (isinstance(sha, str) and sha and sha == edl.get("moments_package_sha256")):
                return None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return list(f) if isinstance(f, list) and all(isinstance(x, str) and x for x in f) else None


def attest(run_dir, run_state, deliverable=True, why_not=None):
    """Write ATTESTATION.json (atomically) from what is ON DISK: GATE_REPORT.json (rows, evidence, the digests
    the gates measured), VERIFY/VERIFICATION.json and the digests of every bound file now. verdict ALL_PASS
    only when every released format (release_formats of the EDL; unreadable = HOLD) satisfies the inventory, the
    pack passed, the files the gates measured are unchanged,
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
    formats, f_why = _edl_formats(run_dir)
    if formats is None:                              # unreadable: HOLD, and every format is checked and bound
        formats = FORMATS
        why.append(f_why)
    bad = {fmt: blockers(fmt, rows.get(fmt), evidence) for fmt in formats}
    for fmt in formats:                                  # ruling 137 (2): V1's credits row is speaker credit, HARD
        cb = v1_credit_block(fmt, rows.get(fmt), rep)
        if cb:
            bad[fmt]["V1_visual_checklist"] = cb
    try:
        pack = json.load(open(os.path.join(run_dir, "VERIFY", "VERIFICATION.json")))
    except (OSError, ValueError):
        pack = None
    v_ok, v_why = verification_ok(pack)
    files = {rel: (sha256(os.path.join(run_dir, rel)) if os.path.isfile(os.path.join(run_dir, rel)) else None)
             for rel in bound(formats)}
    missing = [rel for rel, d in files.items() if d is None]
    measured = rep.get("measured_files") or {}
    for rel in (r for fmt in formats for r in FORMAT_FILES[fmt][:2]):   # each released final and its manifest
        if measured.get(rel) is None or measured.get(rel) != files.get(rel):
            why.append(f"{rel}: not the bytes the gates measured")
    if rep.get("inventory_version") != INVENTORY_VERSION:
        why.append(f"gate report inventory version {rep.get('inventory_version')!r} != {INVENTORY_VERSION}")
    if not (isinstance(run_state, dict) and run_state.get("ok") is True):
        why.append("run did not end clean: " + "; ".join(map(str, (run_state or {}).get("why") or ["no state"])))
    soft = {fmt: flags(fmt, rows.get(fmt), evidence, rep, _edl(run_dir)) for fmt in formats}    # 136 / 137 / 138
    pin_flags = pin_review_flags(run_dir)
    if pin_flags is None:
        why.append("the pin's review_flags are unreadable")
    stage = list((run_state or {}).get("review_flags") or []) if isinstance(run_state, dict) else []
    note = review_flags(soft, (pin_flags or []) + stage)          # the pin's, the render's stages', the gates'
    ok = not any(bad.values()) and v_ok and not missing and not why
    verdict = ("PASS_WITH_FLAGS" if note else "ALL_PASS") if ok else "HOLD"
    att = {"schema": SCHEMA, "inventory_version": INVENTORY_VERSION, "verdict": verdict,
           "soft_flags": soft, "review_flags": note,
           "formats": list(formats),
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
    if att.get("verdict") not in ("ALL_PASS", "PASS_WITH_FLAGS"):       # rulings 136 / 137: flags go to PBX
        why.append(f"attestation verdict {att.get('verdict')!r}")
    if att.get("deliverable") is not True:
        why.append(f"not deliverable: {att.get('why_not_deliverable')}")
    if not (isinstance(att.get("run_state"), dict) and att["run_state"].get("ok") is True):
        why.append("the run did not end clean")
    formats, f_why = _edl_formats(run_dir)          # the EDL NOW (its digest is checked below with every bound file)
    if formats is None:
        return False, why + [f_why], att
    if att.get("formats") != list(formats):
        why.append(f"attested formats {att.get('formats')!r} differ from the EDL's {list(formats)}")
    rows, evidence = att.get("rows") or {}, att.get("evidence")
    try:
        rep = _gate_report(run_dir)                     # bound: its digest is checked below with every bound file
    except (OSError, ValueError):
        rep = None
    for fmt in formats:
        for k, v in blockers(fmt, rows.get(fmt), evidence).items():
            why.append(f"{fmt} {k}: {v}")
        cb = v1_credit_block(fmt, rows.get(fmt), rep)   # ruling 137 (2): V1's credits row is HARD
        if cb:
            why.append(f"{fmt} V1_visual_checklist: {cb}")
    pin_flags = pin_review_flags(run_dir)               # rulings 136 / 137: the note says exactly the attested flags
    stage = list((att.get("run_state") or {}).get("review_flags") or [])
    edl = _edl(run_dir)
    note = review_flags({fmt: flags(fmt, rows.get(fmt), evidence, rep, edl) for fmt in formats},
                        (pin_flags or []) + stage)
    if pin_flags is None:
        why.append("the pin record is unreadable: its review flags cannot be said (rulings 136 / 137)")
    elif note != (att.get("review_flags") or []):
        why.append(f"review flags {note} differ from the attested {att.get('review_flags')!r}")
    if (att.get("verdict") == "PASS_WITH_FLAGS") != bool(note):
        why.append("the verdict and the review flags disagree")
    if rep is None:
        why.append("GATE_REPORT.json unreadable")
    elif not isinstance(rep, dict) or rep.get("rows") != rows or rep.get("evidence") != evidence:
        why.append("GATE_REPORT.json rows / evidence differ from the attested ones")
    try:
        v_ok, v_why = verification_ok(json.load(open(os.path.join(run_dir, "VERIFY", "VERIFICATION.json"))))
        why += [] if v_ok else v_why
    except (OSError, ValueError):
        why.append("VERIFICATION.json unreadable")
    if not att.get("registry_sha256") or not os.path.isfile(REGISTRY) or sha256(REGISTRY) != att["registry_sha256"]:
        why.append("the channel registry changed since it was attested")
    files = att.get("files") or {}
    if set(files) != set(bound(formats)):
        why.append("attested file set differs from the bound set")
    for rel in bound(formats):
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
