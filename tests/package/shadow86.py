#!/usr/bin/env python3
"""RULING 86 (orchestrator 21:18 Nov 13): THE SHADOW'S SIDE-BY-SIDE. A heimdall_first build writes SHADOW86.jsonl in
its build directory: one line per verdict Heimdall decided, with Grok's answer to the SAME prompt (asked in shadow,
never deciding: providers.Router). This reads it with the replay's decision rules (replay85.kind / decide / compare)
and writes SHADOW86.md there:
- every decision where Heimdall and Grok differ, and which side was stricter;
- whether the pin would have sealed under Grok: a verdict on the pin's clips where Grok fails what Heimdall passed
  would have stopped it. This is read from the verdicts themselves; the gates that depend on them are not re-run;
- verdict types without a decision rule (the visual sheets, step B) are listed as "not compared".
tests/package/proof/SHADOW86.json keeps the pins in order and the streak of pins with no decision-changing
difference; the build driver stops asking the shadow when the streak reaches routing.shadow_until_clean_pins (3).
Usage: python3 -B tests/package/shadow86.py <build dir>   (re-reads a build's SHADOW86.jsonl, rewrites its report)"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay85 as R  # noqa: E402

STATE = os.path.join(HERE, "proof", "SHADOW86.json")


def _load(path=STATE):
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) and isinstance(d.get("pins"), list) else {"pins": [], "clean_streak": 0}
    except (OSError, ValueError):
        return {"pins": [], "clean_streak": 0}


def clean_streak(path=STATE):
    """The pins in a row with no decision-changing difference (0 when nothing is recorded or the file cannot be read:
    the shadow then keeps running, which is the safe side)."""
    return int(_load(path).get("clean_streak") or 0)


def pin_texts(res):
    """The SEALED pins' clip texts, normalised as replay85 matches prompts: the medley's (res["pin"], set by the pin
    stage, with res["package"] as sealed, adopted texts included) and the spotlight's (RULING 90: res["spotlight_pin"],
    with res["spotlight"]["package"]). None sealed (no package, or the pin stage refused it): []."""
    pks = ([res.get("package") or {}] if res.get("pin") else []) + \
        ([(res.get("spotlight") or {}).get("package") or {}] if res.get("spotlight_pin") else [])
    return [R._norm(s.get("text") or "")[10:70] for pk in pks for s in pk.get("segments") or [] if isinstance(s, dict)]


def compare_lines(lines, texts=()):
    """-> rows: one per (shadow line, unit): {type, unit, heimdall, grok, compare, on_pin, deciding, shadow}."""
    rows, skipped = [], []
    for x in lines:
        k = R.kind({"role": x.get("role"), "prompt": x.get("prompt") or ""})
        sh = x.get("shadow") or {}
        if k is None or k not in R.DECIDING or "text" not in sh:
            skipped.append({"role": x.get("role"), "type": k, "why": sh.get("error") or "no decision rule"})
            continue
        pr = x.get("prompt") or ""
        on_pin = bool(texts) and any(t and t in R._norm(pr) for t in texts)
        try:
            h = R.decide(k, (x.get("deciding") or {}).get("text"), pr)
        except (ValueError, TypeError, KeyError) as e:
            skipped.append({"role": x.get("role"), "type": k, "why": f"Heimdall's answer unreadable: {e}"})
            continue
        try:
            g = R.decide(k, sh["text"], pr)
        except (ValueError, TypeError, KeyError) as e:
            g = None
            rows.append({"type": k, "unit": "*", "heimdall": "answered", "grok": f"out of contract: {e}"[:120],
                         "compare": "grok no verdict", "on_pin": on_pin,
                         "deciding": (x.get("deciding") or {}).get("backend"), "shadow": sh.get("backend")})
        if g is None:
            continue
        for u, hv in h.items():
            gv = g.get(u)
            rows.append({"type": k, "unit": u, "heimdall": hv, "grok": gv, "compare": R.compare(k, gv, hv),
                         "on_pin": on_pin, "deciding": (x.get("deciding") or {}).get("backend"),
                         "shadow": sh.get("backend")})
    return rows, skipped


def report(out_dir, res, missing=0, path=STATE, update_streak=True):
    """SHADOW86.md for one build, and (update_streak) the pins' streak updated when it sealed one. -> a summary."""
    lines = []
    p = os.path.join(out_dir, "SHADOW86.jsonl")
    if os.path.exists(p):
        with open(p) as f:
            for ln in f:
                try:
                    lines.append(json.loads(ln))
                except ValueError:
                    pass
    texts = pin_texts(res)
    rows, skipped = compare_lines(lines, texts)
    diff = [r for r in rows if r["compare"] != "agree"]
    pin_diff = [r for r in diff if r["on_pin"]]
    on_pin = [r for r in rows if r["on_pin"]]
    #   "grok no verdict" on a pin's decision counts as a stop: a pin is said to seal under Grok only when Grok's own
    #   answer passed every one of its decisions (fail closed, qwen 0108 C1). With missing shadows and no compared
    #   decision on the pin, nothing was verified: None, never True (audit 0108 C1, glm)
    would_seal = None if not texts or (missing and not on_pin) else \
        not any(r["compare"] in ("looser", "grok no verdict") for r in pin_diff)
    usd = sum(float((x.get("shadow") or {}).get("usd_reported") or 0) for x in lines
              if not (x.get("shadow") or {}).get("cached"))
    summ = {"verdicts": len(lines), "compared_units": len(rows), "differ": len(diff), "on_pin_differ": len(pin_diff),
            "not_compared": len(skipped), "missing": int(missing), "shadow_usd_reported": round(usd, 4),
            "pin": bool(texts), "would_seal_under_grok": would_seal}
    summ["summary"] = (f"{len(lines)} verdicts shadowed, {len(rows)} decisions compared, {len(diff)} differ "
                       f"({len(pin_diff)} on the pin's clips); {len(skipped)} not compared; {int(missing)} still "
                       f"running; shadow cost ${usd:.4f} reported" +
                       ("" if would_seal is None else f"; the pin WOULD {'' if would_seal else 'NOT '}have sealed "
                                                      f"under Grok"))
    out = ["# Ruling 86: the shadow's side-by-side (Heimdall decided; Grok asked the same prompts)", "",
           f"Build {os.path.basename(out_dir)}, written {time.strftime('%Y-%m-%d %H:%M %Z')}. {summ['summary']}.", "",
           "Heimdall stricter: Heimdall failed what Grok passed. Heimdall looser: Heimdall passed what Grok failed "
           "(on the pin's clips, Grok would have stopped it).", "",
           "| type | unit | Heimdall | Grok | compare | on the pin | Heimdall model |", "|---|---|---|---|---|---|---|"]
    for r in diff:
        out.append(f"| {r['type']} | {r['unit']} | {r['heimdall']} | {r['grok']} | {r['compare']} | "
                   f"{'yes' if r['on_pin'] else ''} | {r['deciding']} |")
    if skipped:
        out += ["", "## Not compared", ""] + [f"- {s['role']} ({s['type']}): {s['why']}" for s in skipped]
    with open(os.path.join(out_dir, "SHADOW86.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    if texts and update_streak:                  # a sealed pin: the streak moves (once, by the build itself)
        st = _load(path)
        changed = bool(pin_diff) or bool(missing)
        st["pins"].append({"build": os.path.basename(out_dir), "decision_changing": len(pin_diff),
                           "missing": int(missing), "would_seal_under_grok": would_seal,
                           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        st["clean_streak"] = 0 if changed else int(st.get("clean_streak") or 0) + 1
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            json.dump(st, f, indent=1)
        os.replace(tmp, path)
        summ["clean_streak"] = st["clean_streak"]
    return summ


def main():
    d = sys.argv[1]
    with open(os.path.join(d, "package.json")) as f:
        res = json.load(f)
    print(json.dumps(report(d, res, update_streak=False), indent=1))     # a re-read never moves the streak


if __name__ == "__main__":
    main()
