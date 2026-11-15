#!/usr/bin/env python3
"""pipeline/oracle/run.py — one day through the blind oracle and the blind judge, every artefact saved.

<out>/<stamp>/
  BITCOIN_STATEMENTS_<stamp>.jsonl (+ .manifest.json)   the day's frozen input (export.py)
  oracle_prompt.txt, oracle_attempt<N>_raw.json           exactly what was sent / returned
  ORACLE.json         status OK | ORACLE_FAILED (+ every attempt's error), verdict, line-ups + deterministic checks
  judge_L<k>_prompt.txt, judge_L<k>_attempt<N>_raw.json, JUDGE_L<k>.json   one blind verdict per line-up
  DAY.json            the day's result: available (a line-up the oracle proposed, the checks pass and the judge
                      calls LEGAL), or not, or not measured (ORACLE_FAILED / every judgement failed)
Attempts: an oracle reply that fails the schema is re-asked once with the error (the JSON-retry law); a valid reply
whose line-ups all fail the deterministic checks is re-asked once with the violations. Every attempt is kept;
a day whose attempts all fail is ORACLE_FAILED, never NONE. A judge reply that fails its schema or ends early is
re-asked once; still failing = JUDGE_FAILED for that line-up (it never counts as LEGAL).
`call` is injectable (tests pass fakes; production passes provider role calls: providers.call / role_call).
"""
import hashlib
import json
import os

from pipeline.oracle import lineup as L
from pipeline.oracle import llm
from pipeline.oracle import prompts as P

ORACLE_ATTEMPTS = 2
JUDGE_ATTEMPTS = 2


def _write(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=True, default=str)
            f.write("\n")
    os.replace(tmp, path)


def run_oracle(day_dir, rows, now_utc, call, ledger, variant="same_dev_hard"):
    """Returns the ORACLE.json record (also written). call(system, user, schema, ledger, tag) -> (text, raw, usage)."""
    v = L.VARIANTS[variant]
    by_id = {r["id"]: r for r in rows}
    user = P.oracle_prompt(rows, now_utc, variant)
    _write(os.path.join(day_dir, "oracle_prompt.txt"), f"SYSTEM:\n{P.ORACLE_SYSTEM}\n\nUSER:\n{user}")
    rec = {"status": "ORACLE_FAILED", "attempts": [], "now_utc": now_utc, "rows": len(rows), "variant": variant,
           "reask_answered": False}
    msg, follow, reasked = user, None, False
    for n in range(1, ORACLE_ATTEMPTS + 1):
        att = {"attempt": n, "follow_up": follow}
        try:
            text, raw, usage = call(P.ORACLE_SYSTEM, msg, L.ORACLE_SCHEMA, ledger, f"oracle {_tag(day_dir)} #{n}")
        except Exception as e:                              # an API error is a failed attempt, never NONE
            att["error"] = llm.redact(f"{type(e).__name__}: {e}")[:600]
            rec["attempts"].append(att)
            if type(e).__name__ == "SpendStop":
                rec["spend_stop"] = True
                break
            continue
        _write(os.path.join(day_dir, f"oracle_attempt{n}_raw.json"), raw)
        att["usage"] = usage
        try:
            parsed = L.parse_oracle(text, by_id, v["max_lineups"])
        except L.OracleFailed as e:
            att["error"] = f"ORACLE_FAILED: {e}"
            rec["attempts"].append(att)
            follow = f"Your previous reply was not valid ({e}). Reply with ONLY the JSON object the OUTPUT section asks for."
            msg = f"{user}\n\nPREVIOUS REPLY (invalid):\n{text[:20000]}\n\n{follow}"
            continue
        for lu in parsed["lineups"]:
            lu["violations"], lu["summary"] = L.check(lu, by_id, windows_hard=v["windows_hard"])
        att["verdict"] = parsed["verdict"]
        rec["attempts"].append(att)
        rec.update(status="OK", verdict=parsed["verdict"], none_reason=parsed["none_reason"],
                   lineups=parsed["lineups"], attempt_used=n, reask_answered=reasked)
        if parsed["verdict"] == "LINEUPS" and not any(not lu["violations"] for lu in parsed["lineups"]) \
                and n < ORACLE_ATTEMPTS:
            viol = "\n".join(f"line-up {k}: " + "; ".join(lu["violations"]) for k, lu in enumerate(parsed["lineups"], 1))
            follow = ("Every line-up you returned breaks a rule:\n" + viol +
                      "\nReturn corrected line-ups that satisfy every rule, or NONE with the reason. Reply with "
                      "ONLY the JSON object the OUTPUT section asks for.")
            msg = f"{user}\n\nPREVIOUS REPLY:\n{text[:20000]}\n\n{follow}"
            reasked = True
            continue
        break
    _write(os.path.join(day_dir, "ORACLE.json"), rec)
    return rec


def run_judge(day_dir, k, lu, rows_by_id, now_utc, call, ledger, variant="same_dev_hard"):
    """One blind verdict on one line-up (JUDGE_L<k>.json)."""
    v = L.VARIANTS[variant]
    user = P.judge_prompt(lu, rows_by_id, now_utc, v.get("judge_as", variant))
    _write(os.path.join(day_dir, f"judge_L{k}_prompt.txt"), f"SYSTEM:\n{P.JUDGE_SYSTEM}\n\nUSER:\n{user}")
    rec = {"lineup": k, "status": "JUDGE_FAILED", "attempts": []}
    for n in range(1, JUDGE_ATTEMPTS + 1):
        att = {"attempt": n}
        try:
            text, raw, usage = call(P.JUDGE_SYSTEM, user, L.judge_schema(v["checks"]), ledger,
                                    f"judge {_tag(day_dir)} L{k} #{n}")
        except Exception as e:
            att["error"] = llm.redact(f"{type(e).__name__}: {e}")[:600]
            rec["attempts"].append(att)
            if type(e).__name__ == "SpendStop":
                rec["spend_stop"] = True
                break
            continue
        _write(os.path.join(day_dir, f"judge_L{k}_attempt{n}_raw.json"), raw)
        att["usage"] = usage
        try:
            verdict = L.parse_judge(text, v["checks"])
        except L.JudgeFailed as e:
            att["error"] = f"JUDGE_FAILED: {e} (stop {usage.get('stop_reason')})"
            rec["attempts"].append(att)
            continue
        rec["attempts"].append(att)
        rec.update(status="OK", **verdict)
        break
    _write(os.path.join(day_dir, f"JUDGE_L{k}.json"), rec)
    return rec


def oracle_rows(rows):
    """The rows the oracle is shown: a sentence longer than the clip budget (an unpunctuated caption or Whisper
    stretch read as one 'sentence') can be in no segment, so it is not shown (counted in DAY.json)."""
    return [r for r in rows if r["duration_s"] <= L.CLIP_S[1]]


def oracle_sha(day_dir):
    """sha256 of the ORACLE.json a derived file (GROUPS / WITNESS / SCORE) was computed from."""
    with open(os.path.join(day_dir, "ORACLE.json"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def fresh(day_dir, name):
    """True when the derived file `name` belongs to the day dir's CURRENT ORACLE.json: its recorded oracle_sha256
    matches, or (files written before the stamp existed) it is not older than ORACLE.json. A stale file is never read
    as a result (audit F8)."""
    p = os.path.join(day_dir, name)
    if not os.path.exists(p) or not os.path.exists(os.path.join(day_dir, "ORACLE.json")):
        return False
    with open(p, encoding="utf-8") as f:
        stamp = json.load(f).get("oracle_sha256")
    if stamp:
        return stamp == oracle_sha(day_dir)
    return os.path.getmtime(p) >= os.path.getmtime(os.path.join(day_dir, "ORACLE.json"))


def archive_previous(day_dir):
    """A re-run never overwrites an earlier attempt: every oracle / judge artefact already in the day dir, and every
    file derived from them (grouping, witness, score), moves to previous_<n>/ (the export stays). Returns the archive
    dir or None."""
    old = [f for f in os.listdir(day_dir) if f.startswith(("oracle_", "judge_", "ORACLE", "JUDGE", "DAY",
                                                           "group_", "GROUPS", "witness_", "WITNESS", "SCORE"))]
    if not old:
        return None
    n = 1 + sum(1 for f in os.listdir(day_dir) if f.startswith("previous_"))
    dest = os.path.join(day_dir, f"previous_{n}")
    os.makedirs(dest)
    for f in old:
        os.replace(os.path.join(day_dir, f), os.path.join(dest, f))
    return dest


def _tag(day_dir):
    """The run stamp, plus the variant / oracle-model subdirectories when there are any ('20261110_093150',
    '20261110_093150/moments', '20261110_093150/same_dev_hard_max')."""
    parts = os.path.normpath(day_dir).split(os.sep)
    k = next((i for i, x in enumerate(parts) if x[:8].isdigit() and "_" in x), len(parts) - 1)
    return "/".join(parts[k:])


def run_day(day_dir, rows, now_utc, oracle_call, judge_call, ledger, judge=True, variant="same_dev_hard"):
    """Oracle, deterministic checks, blind judge on every structurally legal line-up -> DAY.json. A variant other than
    the order's own (same_dev_hard) writes into its own subdirectory of the day."""
    v = L.VARIANTS[variant]
    if v["subdir"]:
        day_dir = os.path.join(day_dir, v["subdir"])
        os.makedirs(day_dir, exist_ok=True)
    archived = archive_previous(day_dir)
    o = run_oracle(day_dir, oracle_rows(rows), now_utc, oracle_call, ledger, variant)
    return assess_day(day_dir, o, rows, now_utc, judge_call, ledger, judge, variant, archived)


def rejudge_day(day_dir, rows, now_utc, judge_call, ledger, variant="same_dev_hard"):
    """Judge again ONLY the line-ups of an existing ORACLE.json whose judge never returned a whole verdict (e.g. the
    spend guard refused the call); a verdict already OK is reused, never re-asked; the failed judge record is moved to
    previous_<n>/ first (never overwritten). Rewrites DAY.json the same way run_day does."""
    with open(os.path.join(day_dir, "ORACLE.json"), encoding="utf-8") as f:
        o = json.load(f)
    with open(os.path.join(day_dir, "DAY.json"), encoding="utf-8") as f:
        archived = json.load(f).get("previous_attempts_archived")
    redo = []
    for k, lu in enumerate(o.get("lineups") or [], 1):
        p = os.path.join(day_dir, f"JUDGE_L{k}.json")
        if lu["violations"] or not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            if json.load(f).get("status") != "OK":
                redo.append(k)
    if redo:
        n = 1 + sum(1 for f in os.listdir(day_dir) if f.startswith("previous_"))
        dest = os.path.join(day_dir, f"previous_{n}")
        os.makedirs(dest)
        for f in os.listdir(day_dir):
            if any(f.startswith((f"JUDGE_L{k}.", f"judge_L{k}_")) for k in redo):
                os.replace(os.path.join(day_dir, f), os.path.join(dest, f))
    return assess_day(day_dir, o, rows, now_utc, judge_call, ledger, True, variant, archived, reuse=True)


def assess_day(day_dir, o, rows, now_utc, judge_call, ledger, judge, variant, archived, reuse=False):
    """Deterministic checks are in o already; the blind judge on every line-up that passed them; DAY.json. reuse: a
    JUDGE_L<k>.json already OK is read instead of asking again."""
    shown = oracle_rows(rows)
    by_id = {r["id"]: r for r in shown}
    used = (o["attempts"][o["attempt_used"] - 1].get("usage") or {}) if o.get("attempt_used") else {}
    day = {"stamp": _tag(day_dir), "now_utc": now_utc, "previous_attempts_archived": archived,
           "oracle_model": used.get("model"), "judge_model": None,
           "rows_exported": len(rows),
           "rows_shown": len(shown), "rows_hidden_longer_than_clip_budget": len(rows) - len(shown),
           "oracle_status": o["status"],
           "oracle_verdict": o.get("verdict"), "none_reason": o.get("none_reason"), "lineups": []}
    for k, lu in enumerate(o.get("lineups") or [], 1):
        row = {"lineup": k, "development": lu["development"], "violations": lu["violations"],
               "summary": lu["summary"], "judge": None}
        if not lu["violations"] and judge:
            jp = os.path.join(day_dir, f"JUDGE_L{k}.json")
            if reuse and os.path.exists(jp):
                with open(jp, encoding="utf-8") as f:
                    j = json.load(f)
            else:
                j = run_judge(day_dir, k, lu, by_id, now_utc, judge_call, ledger, variant)
            row["judge"] = {"status": j["status"], "verdict": j.get("verdict"), "failed": j.get("failed"),
                            "development": j.get("development"), "reason": j.get("reason")}
        row["accepted"] = bool(not lu["violations"] and row["judge"] and row["judge"]["status"] == "OK"
                               and row["judge"]["verdict"] == "LEGAL")
        if row["judge"]:
            j_used = [x.get("usage") or {} for x in j["attempts"] if x.get("usage")]
            row["judge"]["model"] = j_used[-1].get("model") if j_used else None
        day["lineups"].append(row)
    jm = sorted({r["judge"]["model"] for r in day["lineups"] if r["judge"] and r["judge"].get("model")})
    day["judge_model"] = ", ".join(jm) or None
    acc = [lu for lu, r in zip(o.get("lineups") or [], day["lineups"]) if r["accepted"]]
    hard = [lu for lu in acc if not lu["summary"]["window_misses"]]
    day.update(variant=variant, accepted=len(acc), accepted_hard_windows=len(hard),
               distinct_accepted=len(L.disjoint_max(acc)), distinct_accepted_hard_windows=len(L.disjoint_max(hard)))
    legal = [r for r in day["lineups"] if not r["violations"]]
    unjudged = [r for r in legal if not (r["judge"] and r["judge"]["status"] == "OK")]
    if o["status"] != "OK":
        day["availability"] = "NOT_MEASURED (ORACLE_FAILED" + (", spend guard" if o.get("spend_stop") else "") + ")"
    elif any(r["accepted"] for r in day["lineups"]):
        day["availability"] = "AVAILABLE"
    elif o.get("verdict") == "NONE":
        day["availability"] = "NONE (oracle)"
    elif unjudged:                                   # a line-up nobody judged might have been legal: not measured
        day["availability"] = (f"NOT_MEASURED (JUDGE_FAILED on {len(unjudged)} of {len(legal)} line-ups)" if judge
                               else f"NOT_MEASURED (judge not asked: --no-judge; {len(legal)} line-ups unjudged)")
    elif not legal and o.get("reask_answered") is False:
        # every line-up failed the checks and the corrective re-ask was never answered whole (it failed, or an
        # earlier failure used its attempt): the protocol's answer is missing, so nothing is measured
        day["availability"] = ("NOT_MEASURED (re-ask not answered" + (", spend guard" if o.get("spend_stop") else "")
                               + "; every proposed line-up failed the deterministic checks)")
    elif legal:
        day["availability"] = "NOT_AVAILABLE (the blind judge said every checked line-up fails our rules)"
    else:
        day["availability"] = "NOT_AVAILABLE (every proposed line-up failed the deterministic checks)"
    _write(os.path.join(day_dir, "DAY.json"), day)
    return day


# ── distinct developments (integrator Q1, 01:58): two accepted line-ups on the same development count once ──

GROUP_SYSTEM = ("You group proposed line-ups for Bitcoin news videos by the development each one reports. Judge only "
                "what the text shows; when unsure whether two line-ups report the same development, they do not.")
GROUP_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["groups", "reason"],
                "properties": {"groups": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["lineups", "development"],
                    "properties": {"lineups": {"type": "array", "items": {"type": "integer"}},
                                   "development": {"type": "string"}}}},
                    "reason": {"type": "string"}}}


def group_prompt(lineups, rows_by_id, now_utc):
    blocks = "\n\n".join(f"LINE-UP {n}\n" + P.lineup_block(lu, rows_by_id) for n, lu in enumerate(lineups, 1))
    return f"""TASK
Below are {len(lineups)} line-ups for Bitcoin news videos made at {P._utc(now_utc)} from partner channels' own words. Group
them by DEVELOPMENT. Two line-ups are the same development when they report the same specific event or move (the
same actor, action and object, or the same price level or figure), even when told with different sentences or
channels. A different event, a different aspect reported as its own news, or a different figure is a different
development. Every line-up belongs to exactly one group.

LINE-UPS
{blocks}

OUTPUT
Return ONLY a JSON object: {{"groups": [{{"lineups": [line-up numbers], "development": the development in one
sentence}}], "reason": one sentence}}"""


def parse_groups(text, n):
    """[[line-up numbers], ...] covering 1..n exactly once, or GroupingFailed."""
    try:
        o = json.loads(text) if isinstance(text, str) and text.strip() else None
    except ValueError as e:
        raise GroupingFailed(f"not JSON: {e}")
    if not isinstance(o, dict) or set(o) != {"groups", "reason"} or not isinstance(o["groups"], list):
        raise GroupingFailed("reply is not {groups, reason}")
    seen, out = [], []
    for g in o["groups"]:
        if not isinstance(g, dict) or set(g) != {"lineups", "development"} or not isinstance(g["lineups"], list) \
                or not g["lineups"] or not all(type(x) is int for x in g["lineups"]) \
                or not isinstance(g["development"], str) or not g["development"].strip():
            raise GroupingFailed(f"malformed group {str(g)[:120]}")
        seen += g["lineups"]
        out.append({"lineups": sorted(g["lineups"]), "development": g["development"].strip()})
    if sorted(seen) != list(range(1, n + 1)):
        raise GroupingFailed(f"groups cover {sorted(seen)}, not 1..{n} exactly once")
    return out


class GroupingFailed(ValueError):
    pass


def group_developments(day_dir, rows, now_utc, call, ledger):
    """GROUPS.json + DAY.json 'distinct_developments' for one (variant) day dir: the accepted line-ups grouped by
    development (one blind call when there are two or more; none needed for 0 or 1). A failed grouping is
    GROUPING_FAILED: the column reads not measured, never a count."""
    with open(os.path.join(day_dir, "DAY.json"), encoding="utf-8") as f:
        day = json.load(f)
    with open(os.path.join(day_dir, "ORACLE.json"), encoding="utf-8") as f:
        lus = json.load(f).get("lineups") or []
    acc = [(r["lineup"], lus[r["lineup"] - 1]) for r in day["lineups"] if r["accepted"]]
    rec = {"accepted": [k for k, _ in acc], "status": "OK", "attempts": [], "oracle_sha256": oracle_sha(day_dir)}
    if len(acc) < 2:
        rec["groups"] = [{"lineups": [k], "development": lu["development"]} for k, lu in acc]
    else:
        by_id = {r["id"]: r for r in rows}
        user = group_prompt([lu for _, lu in acc], by_id, now_utc)
        _write(os.path.join(day_dir, "group_prompt.txt"), f"SYSTEM:\n{GROUP_SYSTEM}\n\nUSER:\n{user}")
        rec["status"] = "GROUPING_FAILED"
        for n in range(1, JUDGE_ATTEMPTS + 1):
            try:
                text, raw, usage = call(GROUP_SYSTEM, user, GROUP_SCHEMA, ledger, f"group {_tag(day_dir)} #{n}")
                _write(os.path.join(day_dir, f"group_attempt{n}_raw.json"), raw)
                groups = parse_groups(text, len(acc))
            except Exception as e:                       # SpendStop, API error, malformed reply: not measured
                rec["attempts"].append({"attempt": n, "error": llm.redact(f"{type(e).__name__}: {e}")[:400]})
                if type(e).__name__ == "SpendStop":
                    break
                continue
            rec.update(status="OK", groups=[{"lineups": [acc[i - 1][0] for i in g["lineups"]],
                                              "development": g["development"]} for g in groups])
            rec["attempts"].append({"attempt": n, "usage": usage})
            break
    day["distinct_developments"] = len(rec["groups"]) if rec["status"] == "OK" else None
    day["development_groups"] = rec.get("groups")
    _write(os.path.join(day_dir, "GROUPS.json"), rec)
    _write(os.path.join(day_dir, "DAY.json"), day)
    return rec
