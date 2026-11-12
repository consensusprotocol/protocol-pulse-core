#!/usr/bin/env python3
"""Smoke test of the moments-first wiring AS DEPLOYED (REQUESTS R7; the integrator's main tree: pinned.py 380a06f3 and
edl_rules.py a5ec0f17). It reads COPIES of the main tree's pinned.py, edl_rules.py and config.py into a temporary
directory beside this worktree's pipeline/ (nothing is written to the main tree), makes a pin with
pipeline/package_pin.py from a gated package, and runs the deployed pinned.build_edl on it with a faked acquisition
(the transcript words of each range; no download, no Whisper, no GPU, no network).

Checks:
- the EDL carries the package's VO (intro, and a line after each clip, the LAST clip included), the ONE title and
  caption (law L-t), the digest and both gate verdicts; the deployed R4 for moments passes on it;
- package_pin refuses a package whose gate inventory is not exactly PASS; a pin edited after the gates breaks its seal
  (package_pin.seal), and the deployed moments_vo refuses a gate verdict that is not exactly true;
- a pin without a package keeps today's VO (Editorial Law 2's default).
Usage: python3 tests/package/smoke_r7.py [MAIN_TREE]   (default /home/ultron/protocol_pulse)"""
import copy
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def fake_acq(pin):
    """The transcript words of each range, spread over the segment's own start-end (its real duration)."""
    acq = {}
    for s in pin["segments"]:
        ws = s["approved_text"].split()
        a, b = float(s["start"]), float(s["end"])
        step = (b - a) / len(ws)
        words = [{"word": w, "start": round(a + i * step, 3), "end": round(a + (i + 1) * step - 0.02, 3)}
                 for i, w in enumerate(ws)]
        acq[s["video_id"]] = {"transcript": {"words": words, "segments": []}, "transcript_path": __file__,
                              "offset": 0.0, "provenance": {"kind": "smoke"}}
    return acq


def main(argv=None):
    main_tree = (argv or sys.argv[1:] or ["/home/ultron/protocol_pulse"])[0]
    tmp = tempfile.mkdtemp(prefix="pp_r7_smoke_")
    try:
        shutil.copytree(os.path.join(REPO, "pipeline"), os.path.join(tmp, "pipeline"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.mp4", "*.onnx", "fixtures", "avatars"))
        for f in ("pinned.py", "edl_rules.py", "config.py"):          # the DEPLOYED versions (read-only copies)
            shutil.copy(os.path.join(main_tree, "pipeline", f), os.path.join(tmp, "pipeline", f))
        sys.path.insert(0, os.path.join(tmp, "pipeline"))
        import edl_rules
        import package_pin
        import pinned
        assert os.path.dirname(pinned.__file__) == os.path.join(tmp, "pipeline")
        gates = {k: {"status": "PASS", "by": "smoke", "replayed": False, "n": 1} for k in package_pin.REQUIRED_GATES}
        segs = [("vgsSZ4mAHfQ", "Saifedean Ammous", 5144.99, 5153.37), ("c1JGheQBPH4", "What Bitcoin Did", 2480.28, 2491.52),
                ("wdk5JZ9hPzs", "Natalie Brunell", 529.05, 539.34)]
        pk = {"schema": "pp.package/1", "type": "moments", "title": "Nobody is in charge of Bitcoin.",
              "caption": "no authority. three voices on why that is the point.", "vo_kind": "smoke",
              "hook_first_words": "Bitcoin is the subject of", "runtime_s_estimate": 60.75, "models": {}, "gates": gates,
              "vo": {"intro": "Nobody is in charge of Bitcoin. That's not a flaw. That's the design.",
                     "bridges": ["Next, from Natalie Brunell's show: what does a system with no one in charge have to "
                                 "get right?", "No ruler. Just rules nobody gets to bend. That's the idea."],
                     "bridges_after_clip": [1, 2], "signoff": "Clips today from ..."},
              "segments": [{"video_id": v, "channel": ch, "start": a, "end": b, "transcript_sha256": "t",
                            "url_30s_before": f"https://www.youtube.com/watch?v={v}&t={int(a) - 30}s",
                            "text": f"Bitcoin is the subject of sentence {i} spoken on {ch} here today."}
                           for i, (v, ch, a, b) in enumerate(segs)]}
        pk["lines"] = [{"slot": "intro", "text": pk["vo"]["intro"]}] + \
            [{"slot": f"bridge_{i + 1}", "text": t} for i, t in enumerate(pk["vo"]["bridges"])] + \
            [{"slot": "title", "text": pk["title"]}, {"slot": "caption", "text": pk["caption"]}]
        pin = package_pin.to_pin(pk, "smoke")
        pinned.validate_range = lambda s, a: {"i0": 0, "i1": len(a["transcript"]["words"]) - 1,
                                              "text": s["approved_text"], "first_word": s["approved_text"].split()[0],
                                              "last_word": s["approved_text"].split()[-1], "start_file": s["start"],
                                              "end_file": s["end"], "source_duration": 9999.0,
                                              "words": a["transcript"]["words"], "transcript_word_straddles_boundary": False,
                                              "edge_words_from": "smoke", "approved_text_similarity": 1.0}
        pinned.L.make_lock = lambda *a, **k: {"smoke": True}
        pinned.L.sha256_file = lambda p: "0" * 64
        edl, ov, rep = pinned.build_edl(pin, fake_acq(pin))
        assert edl["vo"]["intro"] == pk["vo"]["intro"], edl["vo"]
        assert [b["after_clip"] for b in edl["vo"]["bridges"]] == [1, 2], edl["vo"]
        assert edl["title"] == pk["title"] and edl["caption"] == pk["caption"], edl
        assert edl["moments_package_sha256"] == package_pin.seal(pin["segments"], pin["moments_package"]["edl_vo"],
                                                                 pin["moments_package"]["signoff_expected"],
                                                                 pk["title"], pk["caption"], gates)
        for c in edl["clips"]:
            c.setdefault("duration", round(c.get("end_file", 0) - c.get("start_file", 0), 2))
        ok, why = edl_rules.rule_r4(edl)
        assert ok, why
        bad_pk = copy.deepcopy(pk)
        bad_pk["gates"]["second_pass"]["status"] = "NOT RUN"
        try:
            package_pin.to_pin(bad_pk, "smoke")
            raise SystemExit("FAIL: a package with a gate NOT RUN was pinned")
        except package_pin.PinRefused:
            pass
        tampered = copy.deepcopy(pin)
        tampered["moments_package"]["title"] = "Bitcoin is at 126K today"
        mp = tampered["moments_package"]
        assert package_pin.seal(tampered["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"],
                                mp["gates"]) != mp["package_sha256"], "the seal does not see a title edited after the gates"
        accepted = []
        for name, mutate in (("title edited after the gates", lambda p: p["moments_package"].update(title="Bitcoin hits 126K")),
                             ("VO edited after the gates", lambda p: p["moments_package"]["edl_vo"].update(intro="Buy now.")),
                             ("a FAIL row with both flags still true",
                              lambda p: p["moments_package"]["gates"]["coherence"].update(status="FAIL"))):
            t = copy.deepcopy(pin)
            mutate(t)
            m_ = t["moments_package"]
            assert package_pin.seal(t["segments"], m_["edl_vo"], m_["signoff_expected"], m_["title"], m_["caption"],
                                    m_["gates"]) != m_["package_sha256"], name     # the seal sees every one of them
            try:
                pinned.build_edl(t, fake_acq(t))
                accepted.append(name)
            except pinned.PinError:
                pass
        bad2 = copy.deepcopy(pin)
        bad2["moments_package"]["checks"]["context_integrity_ok"] = "true"
        try:
            pinned.build_edl(bad2, fake_acq(bad2))
            raise SystemExit("FAIL: the deployed moments_vo accepted a truthy string as a gate verdict")
        except pinned.PinError:
            pass
        plain = copy.deepcopy(pin)
        plain.pop("moments_package")
        edl2, _, _ = pinned.build_edl(plain, fake_acq(plain))
        assert "title" not in edl2, edl2
        print("SMOKE R7 PASS (deployed pinned.py / edl_rules.py): the package's VO (a line after every clip, the last "
              "included), title and caption reach the EDL; R4 for moments passes (" + why + "); an ungated package is "
              "refused at the pin; an edited pin breaks its seal; a truthy-string verdict is refused; a plain pin is "
              "unchanged")
        print("RECORDED (REQUESTS R7 1b, the integrator's file): the deployed build_edl ACCEPTS these tampered pins, "
              "because it reads the two flags, not the sealed inventory: " + "; ".join(accepted or ["none"]))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
