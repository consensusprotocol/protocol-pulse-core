"""Item 3 (amendment A, 09:35 ET Nov 24): the three must-fail OUT edges through EDGE_OUT alone (the second recogniser's
sentence end, HARD, no model question), on the REAL audio: the recorded second-ear replies on the cached audio
windows (Router replay=True: a reply not recorded raises; nothing is fetched or paid)."""
import json, os, re, sys
W = sys.argv[1]
sys.path.insert(0, os.path.join(W, "tests/package")); sys.path.insert(0, os.path.join(W, "pipeline"))
import providers as P
import proof_ly as PL
import transcript_truth as TT
LV2 = os.path.join(PL.SCRATCH, "lv2")
rt = P.Router(record_dir=PL.REPLIES, replay=True)


def moment(rec_dir, mid):
    inp = json.load(open(os.path.join(W, "tests/package/proof", rec_dir, "inputs.json")))
    return next(m for m in inp["moments"] if m["moment_id"] == mid)


def run(name, m, end=None, text=None):
    start, end = float(m["start"]), float(end if end is not None else m["end"])
    text = text if text is not None else m["text"]
    wav, wav_start = TT.audio_window(m["video_id"], float(m["start"]), float(m["end"]), LV2)   # the cached window
    sec, rep = TT.second_pass(rt, wav)
    e = TT.edges(sec, wav_start, start, end, text)
    out = e["out"]
    print(json.dumps({"fixture": name, "clip": f'{m["moment_id"][:8]} {m["video_id"]} {start:.2f}-{end:.2f}',
                      "ends": text[-60:], "recogniser": rep.backend, "replayed": rep.replayed,
                      "out_ok": out.get("ok"), "out_word": out.get("word"), "after": out.get("after"),
                      "why": out.get("why"), "RESULT": "SEALED (the OUT edge passes)" if out.get("ok") else "DROPPED"}))
    return sec, wav_start


story = moment("ledger_20261123_232747", "1cb1675158fd53f1033a")
run("and everybody had the same story.", story)
dan = moment("ledger_20261124_004415", "ad47eab4a19c2324a9eb")
sec, wav_start = run("Let me read that again.", dan)
words = [w for w in sec.get("words") or [] if w.get("start") is not None]
idx = next(i for i in range(len(words) - 1) if re.sub(r"\W", "", words[i]["text"]).lower() == "new" and
           re.sub(r"\W", "", words[i + 1]["text"]).lower() == "low")
t_end = wav_start + float(words[idx].get("end") or words[idx]["start"])
cut = dan["text"][:dan["text"].lower().index("we hit a new") + len("we hit a new")]
run("a cut after 'we hit a new'", dan, end=t_end, text=cut)
