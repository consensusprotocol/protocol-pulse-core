#!/usr/bin/env python3
"""Seal a gated package into MOMENTS_PIN.json and verify the pin against the factory AS DEPLOYED (read-only copies of
the main tree's pinned.py, edl_rules.py and config.py in a temporary directory, as smoke_r7.py does; nothing is
written to the main tree; no download, no Whisper, no GPU, no network).

Checks on the REAL pin: package_pin.to_pin authorises it (every required gate exactly PASS, measured live, the lines
equal the VO / title / caption); pinned.validate_schema accepts it; pinned.build_edl (moments_vo) carries the VO
(a line after every clip, the last included), the ONE title and caption and the seal; edl_rules.rule_r4 (R4 for
moments) passes on the pin's own segment durations.
Where the factory copy has edl_rules.rule_r11 (law L-y's VO shape), it runs too.
Usage: python3 tests/package/pin_and_verify.py PACKAGE.json RUN_NAME OUT_DIR [MAIN_TREE]
(MAIN_TREE: any directory holding pipeline/{pinned,edl_rules,config}.py, e.g. a `git show` export of a branch)"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from smoke_r7 import fake_acq  # noqa: E402


def main(argv=None):
    argv = argv or sys.argv[1:]
    pkg_path, run_name, out_dir = argv[:3]
    main_tree = argv[3] if len(argv) > 3 else "/home/ultron/protocol_pulse"
    tmp = tempfile.mkdtemp(prefix="pp_pin_verify_")
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
        pk = json.load(open(pkg_path))
        path, pin = package_pin.write_pin(pk, run_name, out_dir)        # refuses unless every gate is exactly PASS
        pinned.validate_schema(pin)
        # the acquisition is faked (no download): each range's own approved words spread over its own start-end
        pinned.validate_range = lambda s, a: {"i0": 0, "i1": len(a["transcript"]["words"]) - 1,
                                              "text": s["approved_text"], "first_word": s["approved_text"].split()[0],
                                              "last_word": s["approved_text"].split()[-1], "start_file": s["start"],
                                              "end_file": s["end"], "source_duration": 99999.0,
                                              "words": a["transcript"]["words"],
                                              "transcript_word_straddles_boundary": False,
                                              "edge_words_from": "verify", "approved_text_similarity": 1.0}
        pinned.L.make_lock = lambda *a, **k: {"verify": True}
        pinned.L.sha256_file = lambda p: "0" * 64
        if hasattr(pinned, "adjudicate_lock"):          # ruling 17 (main e492ec60): the second recogniser adjudicates
            pinned.adjudicate_lock = lambda lock, *a, **k: lock   # the lock on the acquired AUDIO, at render; offline
                                                                  # here there is no audio, as with make_lock above
        acq = fake_acq(pin)
        for v in acq.values():                          # the acquired media's path (read by ruling 17's adjudication,
            v.setdefault("path", None)                  # faked above): offline there is none
        edl, _, _ = pinned.build_edl(pin, acq)
        mp = pin["moments_package"]
        assert edl["vo"]["intro"] == pk["vo"]["intro"], edl["vo"]
        assert [b["text"] for b in edl["vo"]["bridges"]] == list(pk["vo"]["bridges"]), edl["vo"]
        assert [b["after_clip"] for b in edl["vo"]["bridges"]] == list(pk["vo"]["bridges_after_clip"]), edl["vo"]
        assert edl["title"] == pk["title"] and edl["caption"] == pk["caption"], (edl.get("title"), edl.get("caption"))
        assert edl["moments_package_sha256"] == mp["package_sha256"] == package_pin.seal(
            pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"], mp["gates"])
        for c in edl["clips"]:
            c.setdefault("duration", round(c.get("end_file", 0) - c.get("start_file", 0), 2))
        ok, why = edl_rules.rule_r4(edl)
        print(f"PIN {path}\n  story_id {pin['story_id']} seal {mp['package_sha256']}")
        print(f"  pinned.validate_schema: OK; build_edl (moments_vo): VO, title, caption, seal carried")
        print(f"  edl_rules.rule_r4 ({main_tree}): {'PASS' if ok else 'FAIL'}: {why}")
        if hasattr(edl_rules, "rule_r11"):                  # law L-y's VO shape, where that factory has it
            ok11, why11 = edl_rules.rule_r11(edl)
            print(f"  edl_rules.rule_r11 ({main_tree}): {'PASS' if ok11 else 'FAIL'}: {why11}")
            ok = ok and ok11
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
