"""For each stage-3 'no word before it' loss in a build: what is in the audio before the clip? Offline (recorded scribe
replies, replay=True) + the cached L-v 2 WAV, CPU only. usage: tests/package/funnel_pre_edge.py <build dir>"""
import json, os, sys, wave
import numpy as np
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import providers as P, transcript_truth as TT
D = sys.argv[1]
sys.path.insert(0, os.path.join(REPO, "tests", "package"))
import proof_ly as PL  # noqa: E402
LV2 = os.path.join(PL.SCRATCH, "lv2")                 # the build's default L-v 2 work dir (proof_ledger --work-dir)
inp = json.load(open(os.path.join(D, "inputs.json"))); pk = json.load(open(os.path.join(D, "package.json")))
by = {m["moment_id"]: m for m in inp["moments"]}
rt = P.Router(record_dir=os.path.join(REPO, "tests/package/fixtures/replies"), replay=True)
for mid, v in (pk["prescreen"].get("second_pass") or {}).items():
    if v == "PASS":
        continue
    m = by[mid]; s, e = float(m["start"]), float(m["end"])
    wav, a = TT.audio_window(m["video_id"], s, e, LV2)
    sec, _ = TT.second_pass(rt, wav)
    edg = TT.edges(sec, a, s, e, m["text"])
    w = wave.open(wav); n = w.getnframes(); sr = w.getframerate()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    off = s - a
    fr = int(0.05 * sr)
    def db(seg):
        r = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
        return -120.0 if r <= 0 else 20 * np.log10(r)
    pre = [round(db(x[i:i + fr]), 1) for i in range(0, int(off * sr), fr)]
    words = [(round(float(w_["start"]), 2), w_.get("text"), w_.get("speaker")) for w_ in sec.get("words") or []
             if w_.get("start") is not None][:6]
    print(f"\n{m['channel_name']} {m['video_id']} clip {s:.2f}-{e:.2f}, window from {a:.2f} (pad {off:.2f} s); "
          f"IN: {edg['in'].get('why')} | OUT: {edg['out'].get('why')}")
    print("  recogniser's first words (s into the window, text, speaker):", words)
    print("  pre-clip RMS dBFS per 50 ms:", pre)
    print("  clip's first 0.5 s RMS dBFS per 50 ms:", [round(db(x[i:i + fr]), 1) for i in range(int(off * sr), int((off + 0.5) * sr), fr)])
    print("  primary (store) text starts:", repr(m["text"][:70]))
