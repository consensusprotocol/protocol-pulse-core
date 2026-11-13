#!/usr/bin/env python3
"""The FUNNEL TABLE of one ledger build record (orchestrator 02:45 item 1): per stage, the moments lost per exact
reason, with one example moment text per reason. No vendor call: it reads the record (inputs.json, package.json,
step_a.json, package.log), the ledger for row texts, and recomputes the CUTTABLE edges from the RECORDED scribe replies
(Router replay=True: a reply not recorded raises, it is never fetched).
usage: tests/package/funnel.py <build dir>"""
import collections
import json
import os
import re
import sys

D = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "package"))
import ledger_build as LB  # noqa: E402  (the build's own roots: PP_INGEST_ROOT, audit 0332 C1 qwen P2-2)
import proof_ly as PL  # noqa: E402
LEDGER = os.path.join(LB.INGEST_ROOT, "data", "editorial", "moments", "moment_ledger.jsonl")
REPLIES = os.path.join(REPO, "tests", "package", "fixtures", "replies")
LV2 = os.path.join(PL.SCRATCH, "lv2")                 # the build's default L-v 2 work dir (proof_ledger --work-dir)
inp = json.load(open(os.path.join(D, "inputs.json")))
pk = json.load(open(os.path.join(D, "package.json")))
sa = json.load(open(os.path.join(D, "step_a.json"))) if os.path.exists(os.path.join(D, "step_a.json")) else {}
rep, moments = inp["inputs"], inp["moments"]
by = {m["moment_id"]: m for m in moments}
texts = {}
for line in open(LEDGER):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if isinstance(r, dict) and r.get("moment_id"):
        texts[r["moment_id"]] = r.get("text") or ""


def q(t, n=140):
    t = " ".join(str(t or "").split()).replace("|", "/")
    return t if len(t) <= n else t[:n - 1] + "…"


def tx(mid):
    return by.get(mid, {}).get("text") or texts.get(mid) or ""


def emit(title, rows, head=("lost", "exact reason", "one example (moment text)")):
    print(f"\n**{title}**\n")
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join(str(c) for c in r) + " |")


def grouped(items):
    """items: [(reason, mid)] -> rows [count, reason, example] by count, the example the first moment of the reason."""
    g = collections.OrderedDict()
    for why, mid in items:
        g.setdefault(why, []).append(mid)
    return [[len(ms), why, f'"{q(tx(ms[0]))}"' if ms[0] else "n/a"] for why, ms in
            sorted(g.items(), key=lambda kv: -len(kv[1]))]


def flags_rows(per_moment, describe, example_note=None):
    """per_moment: {mid: [flag, ...]} -> rows [moments carrying it, of them it ALONE keeps out, flag, example]."""
    carry, alone = collections.Counter(), collections.Counter()
    ex = {}
    for mid, fl in per_moment.items():
        for f in fl:
            carry[f] += 1
            ex.setdefault(f, mid)
            if len(set(fl)) == 1:
                alone[f] += 1
                ex[f] = ex[f] if len(set(per_moment[ex[f]])) == 1 else mid      # prefer an example it alone rejects
    rows = []
    for f, n in carry.most_common():
        note = (example_note(ex[f], f) if example_note else "")
        rows.append([n, alone[f], f"`{f}`: {describe(f)}", f'"{q(tx(ex[f]))}"' + (f" ({note})" if note else "")])
    return rows


print(f"Build `{os.path.basename(D)}`: code {pk.get('code')}, render clock {pk.get('now')}.")
ar = inp.get("adapter_report") or {}
print(f"Adapter (pp-ingest, before the ledger rows): excluded {json.dumps(ar.get('excluded'))}.")

# ---- stage 0: ledger rows -> moments
s0 = []
for why, n in (rep.get("no_word_record_why") or {}).items():
    s0 += [(f"SUPPLY: no word record yet ({why})", None)] * int(n)
s0 += [("SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row)", None)] * \
    int(rep.get("window_waiting") or 0)
s0 += [("its window record failed a check", None)] * int(rep.get("window_failed") or 0)
na = rep.get("not_anchored") or {}
ws_rows = {}
for mid, why in na.items():
    m = re.search(r"\((\d+) word\(s\) before (?:it|the anchored text),? and (\d+) after", why)
    if m:
        ws_rows[mid] = (int(m.group(1)), int(m.group(2)), why)
    s0.append(("does not re-anchor: " + re.sub(r"\d+(\.\d+)?", "N", re.sub(r"searched [\d.]+-[\d.]+ s",
                                                                       "searched around the row's time", why)), mid))
s0 += [("duplicate: the same speech as a kept moment (time overlap in the same video)", mid)
       for mid in (rep.get("duplicates_of") or {})]
s0 += [(f"malformed: {why}", mid) for mid, why in (rep.get("malformed") or {}).items()]
s0 += [("its video's rows name two channels", None) for _ in (rep.get("channel_conflict") or {})]
emit(f"Stage 0: {rep.get('rows')} ledger rows -> {len(moments)} moments ({len(s0)} not moments)", grouped(s0))
if ws_rows:
    print("\nThe rows that are not whole sentences of the word record, exactly (words of the edge sentences outside "
          "the anchored text, before / after, and why each stays out):")
    for mid, (l, r, why) in sorted(ws_rows.items(), key=lambda kv: kv[1][0] + kv[1][1]):
        print(f"- {l} before / {r} after: \"{q(texts.get(mid), 90)}\" (why: {q(why, 140)})")

# ---- stage 1: moments -> usable
DESC = {"opener": "opens on a pronoun or reply word that needs what came before (stand_alone.opener)",
        "no_bitcoin": "does not name Bitcoin: regex `\\b(bitcoins?|btcs?)\\b` (T11, the old story selector's subject "
                      "screen; 'Bitcoiners', 'sats', 'Satoshi' do not count)",
        "too_many_sentences": "more than 3 sentences (T9, the old selector's MAX_WINDOW_SENTENCES = 3)",
        "layout_ineligible": "the channel has a burned-in chyron (registry has_chyron, DEC-12d)",
        "not_statement": "ends on a question",
        "hook_lead": "hook only: transcript gap before the first word < 80 ms",
        "start_case": "starts lower-case", "fragment": "not a sentence start / end", "too_short": "< 5 words",
        "no_content": "interjections only", "unpunctuated": "boundary in an unpunctuated stretch",
        "duration": "no word timestamps", "not_sentence_ready": "no sentence-ready word record"}
un = pk.get("unusable") or {}
clipflags, other = {}, []
for mid, why in un.items():
    m = re.match(r"not eligible on screen: (.*)$", why)
    if m:
        roles = dict(p.split(": ", 1) for p in m.group(1).split("; ") if ": " in p)
        clipflags[mid] = [f.strip() for f in roles.get("clip", "").split(",") if f.strip()]
    else:
        other.append((re.sub(r"^[\d.]+ s:", "N s:", why), mid))
print(f"\n**Stage 1: {len(moments)} moments -> {pk.get('usable')} usable** (package.usable; {len(un)} lost)")
print("\nA moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the "
      "binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).")
emit(f"Stage 1a: not eligible on screen ({len(clipflags)} moments)",
     flags_rows(clipflags, lambda f: DESC.get(f, f)), head=("moments", "alone", "exact reason (clip role)",
                                                             "one example"))
if other:
    emit(f"Stage 1b: the other usable() reasons ({len(other)} moments)", grouped(other))

# ---- stage 2: usable -> cleared step A
pre = pk.get("prescreen") or {}
failed = pre.get("failed") or {}
sa_by = {}
for k, v in sa.items():
    if isinstance(v, dict):
        sa_by[k.split(":")[0]] = v


def a_note(mid, rule):
    a = next((v for lb, v in sa_by.items() if mid.startswith(lb)), None)
    if not a:
        return ""
    if rule == "REFERENT_OUTSIDE":
        rs = [r for r in a.get("referents") or [] if isinstance(r, dict) and r.get("inside") is not True]
        return "; ".join(f"'{r.get('word')}' -> '{q(r.get('refers_to'), 50)}', changes the assertion: "
                         f"{r.get('changes_assertion')}" for r in rs[:2])
    if rule == "NOT_OWN_SINCERE":
        return f"view: {a.get('view')}"
    if rule == "STALE_TIME":
        return f"time_ok: {a.get('time_ok')}"
    if rule == "CONDITION_OUTSIDE":
        return "; ".join(f"'{q((c or {}).get('text'), 60)}'" for c in a.get("conditions") or [])
    if rule == "SPEAKER_CHANGE":
        return f"speaker_changes_inside: {a.get('speaker_changes_inside')}"
    if rule == "UNCERTAIN":
        return f"certainty: {a.get('certainty')}"
    if rule == "RETRACTION":
        return f"retraction: {q(a.get('retraction'), 60)}"
    return ""


SDESC = {"REFERENT_OUTSIDE": "a word refers to something outside the clip AND resolving it could change the assertion "
                             "(anything but an explicit 'no' fails, L-m)",
         "NOT_OWN_SINCERE": "not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...)",
         "STALE_TIME": "time words stale on the show date (L-v 3)", "CONDITION_OUTSIDE": "a condition outside the clip",
         "SPEAKER_CHANGE": "a speaker change inside", "RETRACTION": "retracted or corrected later",
         "UNCERTAIN": "the judge is not certain", "CONTEXT_UNAVAILABLE": "no source context to judge"}
print(f"\n**Stage 2: {pk.get('usable')} usable -> {pre.get('cleared')} cleared step A** (L-s on the moment's own "
      f"context; {pre.get('screened')} screened, {len(failed)} failed)")
emit(f"Stage 2: step A rules ({len(failed)} moments)",
     flags_rows(failed, lambda f: SDESC.get(f, f), a_note), head=("moments", "alone", "exact reason", "one example"))

# ---- stage 3: cleared -> L-v 2 + CUTTABLE (edges recomputed from the recorded scribe replies, offline)
sp = pre.get("second_pass") or {}
lost3 = [mid for mid, v in sp.items() if v != "PASS"]
detail = {}
try:
    import providers as P
    import transcript_truth as TT
    rt = P.Router(record_dir=REPLIES, replay=True)
    for mid in lost3:
        m = by[mid]
        try:
            t = TT.verify_segment(rt, m["video_id"], float(m["start"]), float(m["end"]), m["text"], LV2)
            e = t.get("edges") or {}
            if not t.get("ok"):
                bits = []
                if not t.get("transcript_ok"):
                    bits.append(f"the two recognisers disagree on {json.dumps(t.get('disagree'))[:160]}")
                if t["speakers"].get("turn_change_inside") is not False:
                    bits.append(f"speakers measured inside: {t['speakers'].get('labels')}")
                detail[mid] = ("L-v 2 FAIL", "; ".join(bits))
            else:
                bad = [f"{k.upper()}: {e[k].get('why')}" for k in ("in", "out") if not (e.get(k) or {}).get("ok")]
                detail[mid] = ("not CUTTABLE: " + " + ".join(b.split(":")[0] for b in bad) + " edge", "; ".join(bad))
        except Exception as ex:                              # noqa: BLE001
            detail[mid] = (sp[mid], f"(edge detail not recomputed offline: {type(ex).__name__}: {str(ex)[:120]})")
except Exception as ex:                                      # noqa: BLE001
    print(f"(stage-3 detail not recomputed: {type(ex).__name__}: {ex})")
rows3 = []
g3 = collections.OrderedDict()
for mid in lost3:
    k = detail.get(mid, (sp[mid], ""))[0]
    g3.setdefault(k, []).append(mid)
for k, ms in sorted(g3.items(), key=lambda kv: -len(kv[1])):
    rows3.append([len(ms), k, f'"{q(tx(ms[0]))}" ({q(detail.get(ms[0], ("", ""))[1], 200)})'])
emit(f"Stage 3: {pre.get('cleared')} cleared -> {pre.get('cuttable')} pass L-v 2 + CUTTABLE ({len(lost3)} lost)", rows3)
if len(lost3) > 1:
    print("\nEvery stage-3 loss, exactly:")
    for mid in lost3:
        k, d = detail.get(mid, (sp[mid], ""))
        print(f"- {by[mid].get('channel_name')}: {k}: {q(d, 260)}")

# ---- stage 4: cuttable -> can open
ho = pre.get("hook_onset") or {}
lost4 = [(v, mid) for mid, v in ho.items() if v != "PASS"]
emit(f"Stage 4: {pre.get('cuttable')} cuttable -> {sum(v == 'PASS' for v in ho.values())} can open a medley (G17a; "
     f"the others stay in play as non-hook clips)", grouped(lost4) or [[0, "-", "-"]])

# ---- stage 5: -> angle -> line-ups
print(f"\n**Stage 5: the angle step and the line-ups.** why_none: {pk.get('why_none')!r}; angles: "
      f"{len(pk.get('angles') or [])} from {pk.get('angle_backend')}")
cl = [mid for mid, v in sp.items() if v == "PASS"]
print("\nThe moments offered to the angle step:")
for mid in cl:
    m = by.get(mid, {})
    print(f"- {m.get('channel_name')} ({m.get('video_id')}), {m.get('duration_s')} s, can open: "
          f"{ho.get(mid) == 'PASS'}: \"{q(m.get('text'), 150)}\"")
print(f"\nTogether {round(sum(float(by[m]['duration_s']) for m in cl if m in by), 2)} s from "
      f"{len({by[m]['channel_id'] for m in cl if m in by})} channels.")
for a in pk.get("angles") or []:
    print(f"- angle: \"{q(a.get('angle'), 200)}\" moments {len(a.get('moments') or [])}")
log = open(os.path.join(D, "package.log")).read().splitlines()
k = next((i for i, l in enumerate(log) if re.search(r"angles? from|no readable angles|readable angle", l)), None)
if k is not None:
    print("\nThe build's own log from the angle step on:")
    print("```")
    for l in log[k:]:
        print(l.rstrip()[:240])
    print("```")
