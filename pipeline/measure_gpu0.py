#!/usr/bin/env python3
"""pipeline/measure_gpu0.py — measure the peak GPU0 memory each gpu0.REQUIREMENT_MIB key needs (law L-r item 2:
'the incoming model's known requirement'). Holds the GPU0 lease for the whole measurement; runs one child process per
key (it inherits the lease descriptor and loads through gpu0, as the pipeline does) on a representative workload while
this process samples nvidia-smi every 0.1 s. Prints the peak above the idle baseline per key; changes nothing.
Usage: CUDA_VISIBLE_DEVICES=0 [MEASURE_SECONDS=600] python3 pipeline/measure_gpu0.py [key ...]"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)
import gpu0  # noqa: E402

SOURCE = os.environ.get("MEASURE_SOURCE") or os.path.join(REPO, "references", "pulse_preview_2026-11-11", "sources",
                                                       "jbDqdLytkNM.mp4")     # 733 s of speech (protected, read-only)

CHILD = r'''
import os, sys, json, urllib.request
sys.path.insert(0, sys.argv[1])
import gpu0
key, wav = sys.argv[2], sys.argv[3]
if key.startswith("whisper:"):
    parts = key.split(":")
    m = gpu0.whisper(parts[1], batched=len(parts) > 2)
    kw = {"language": "en", "word_timestamps": True}
    kw.update({"batch_size": 16} if len(parts) > 2 else {"beam_size": 5, "vad_filter": False})
    segs, _ = m.transcribe(wav, **kw)
    n = sum(len(s.words or []) for s in segs)
    print(json.dumps({"words": n}))
elif key == "embedder":
    import story_semantics as sm
    e = sm.Embedder()                                   # its model loads through gpu0.model('embedder')
    v = e.encode([("bitcoin price support moving average " * 60)] * 64)
    print(json.dumps({"vectors": len(v)}))
elif key == "resemblyzer":
    from resemblyzer import VoiceEncoder, preprocess_wav
    enc = gpu0.model("resemblyzer", VoiceEncoder)          # as qa_gates' G1 loads it
    print(json.dumps({"dims": len(enc.embed_utterance(preprocess_wav(wav)))}))
elif key == "nvenc":
    gpu0.swap_to("nvenc")
    import subprocess
    for size in ("1920x1080", "1080x1920"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30", "-t", "8",
                        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18", "-f", "null", "-"],
                       check=True, timeout=300)
    print(json.dumps({"encoded": 2}))
elif key.startswith("ollama:"):
    import story_semantics as sm
    llm = sm.LocalLLM(model=key.split(":", 1)[1])          # as the editorial stages ask it (swap_to inside _post)
    out = llm._post("Reply with a JSON object about Bitcoin's 200-day average in 150 words.", 200, seed=7)
    llm.stop()
    print(json.dumps({"chars": len(out)}))
'''


def main():
    keys = sys.argv[1:] or list(gpu0.REQUIREMENT_MIB)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        sys.exit("CUDA_VISIBLE_DEVICES must be 0")
    with gpu0.lease("measure_gpu0 (L-r requirements)"), tempfile.TemporaryDirectory(prefix="gpu0m_") as tmp:
        lease_fd = gpu0._own[gpu0.lease_path()]["file"].fileno()
        os.set_inheritable(lease_fd, True)
        wav = os.path.join(tmp, "a.wav")
        secs = os.environ.get("MEASURE_SECONDS", "600")    # >= 480 s fills a batched 16 x 30 s window
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "60", "-t", secs, "-i", SOURCE, "-vn", "-ac", "1",
                        "-ar", "16000", wav], check=True, timeout=120)
        rows = []
        for key in keys:
            gpu0.release_all()
            base, total = gpu0.memory()
            peak, samples = [base], [0, 0]                   # [ok, failed]
            stop = threading.Event()

            def sample():
                while not stop.wait(0.1):
                    try:
                        peak[0] = max(peak[0], gpu0.memory()[0])
                        samples[0] += 1
                    except gpu0.Gpu0Stop:
                        samples[1] += 1
            t = threading.Thread(target=sample, daemon=True)
            t.start()
            t0 = time.time()
            r = subprocess.run([sys.executable, "-c", CHILD, PIPELINE_DIR, key, wav], capture_output=True, text=True,
                               timeout=1800, pass_fds=(lease_fd,))
            stop.set()
            t.join()
            rows.append({"key": key, "baseline_mib": base, "peak_mib": peak[0], "need_mib": peak[0] - base,
                         "seconds": round(time.time() - t0, 1), "samples": samples[0], "failed_samples": samples[1],
                         "rc": r.returncode if samples[0] > 0 else (r.returncode or 99),
                         "out": (r.stdout.strip().splitlines() or [""])[-1][:120],
                         "err": "" if r.returncode == 0 else r.stderr.strip()[-300:]})
            print(json.dumps(rows[-1]), flush=True)
        gpu0.release_all()
        print("\n| key | baseline MiB | peak MiB | need MiB | s | rc |\n|---|---|---|---|---|---|")
        for x in rows:
            print(f"| {x['key']} | {x['baseline_mib']} | {x['peak_mib']} | {x['need_mib']} | {x['seconds']} | {x['rc']} |")
        if any(x["rc"] != 0 for x in rows):
            sys.exit(f"measure_gpu0: {sum(x['rc'] != 0 for x in rows)} key(s) failed; their peaks are not requirements")


if __name__ == "__main__":
    main()
