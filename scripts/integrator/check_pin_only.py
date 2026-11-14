"""A sealed moments-first pin checked on its OWN content (CPU only; orchestrator '06:22': render the instant the pin is
readable). Ready = type 'moments'; every required gate of the sealed inventory exactly PASS and not replayed
(pp-selectid's gate_problems); THEIR seal() recomputed over the pin's own bytes equals package_sha256 (and, when given,
the digest named on the READY line); main's pinned.validate_schema and the strict pinned.moments_vo accept it.
Usage: python3 check_pin_only.py PIN.json [expected_sha_prefix]  -> exit 0 ready / 1 not (reason printed)"""
import importlib.util
import json
import sys

sys.path.insert(0, "/home/ultron/protocol_pulse/pipeline")
import pinned  # noqa: E402


def main(path, want=None):
    pin = json.load(open(path))
    mp = pin.get("moments_package") or {}
    if mp.get("type") != "moments":
        return False, f"type {mp.get('type')!r}, not 'moments'"
    spec = importlib.util.spec_from_file_location("pp_pin", "/home/ultron/worktrees/pp-selectid/pipeline/package_pin.py")
    PP = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(PP)
    problems = PP.gate_problems(mp.get("gates"))
    if problems:
        return False, "gates: " + "; ".join(problems)
    problems = PP.trim_problems(pin["segments"])        # ruling 49 (builder 07:19): scorer_pending on, and only on, a
    if problems:                                        # trimmed clip; at most one trimmed clip per pin
        return False, "trim: " + "; ".join(problems)
    spot = {"shape": mp["shape"], "first_comment": mp.get("first_comment")} if mp.get("shape") == "spotlight" else {}
    seal = PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"],
                   mp.get("btc_screen"), **spot)         # ruling 34 (builder 04:19): in the body only when the pin has it;
    #                                                     law L-ab: a spotlight's kind, closing line and first comment too
    if seal != mp.get("package_sha256"):
        return False, "seal mismatch: the pin's bytes or gates differ from what was sealed"
    if want and not seal.startswith(want):
        return False, f"package_sha256 {seal[:16]} is not the READY line's {want}"
    pinned.validate_schema(pin)
    segs = pin["segments"]
    vo = pinned.moments_vo(mp, [{"index": i} for i in range(1, len(segs))], segs)
    out = [f"READY (pin only) {seal[:16]} title={mp.get('title')!r} intro={str(vo['intro'])[:80]!r} "
           f"bridges after {[b['after_clip'] for b in vo['bridges']]}"]
    out += [f"  {s['role']:4} {s['channel']} {s['video_id']} {s['start']:.2f}-{s['end']:.2f} ({s['end'] - s['start']:.2f} s)"
            for s in segs]
    return True, "\n".join(out)


if __name__ == "__main__":
    try:
        ok, msg = main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    except pinned.PinError as e:
        ok, msg = False, f"PinError: {e}"
    except Exception as e:
        ok, msg = False, f"{type(e).__name__}: {e}"
    print(msg)
    sys.exit(0 if ok else 1)
