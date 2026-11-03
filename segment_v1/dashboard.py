#!/usr/bin/env python3
"""Segment V1 live dashboard — lightweight Flask on port 9090."""
import json, os, time, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

BASE = "/home/ultron/protocol_pulse/segment_v1"


def get_status():
    """Gather current pipeline status."""
    status = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S ET"), "stages": {}}

    # Stage 1: Transcripts
    transcripts_dir = os.path.join(BASE, "transcripts")
    expected = ["bSmFGoAKPBc", "5ripuS9GDaM", "Eojd18J_wuU", "7QIB_zdKU9A"]
    transcripts = {}
    for vid in expected:
        fp = os.path.join(transcripts_dir, f"{vid}.json")
        if os.path.exists(fp) and os.path.getsize(fp) > 100:
            sz = os.path.getsize(fp)
            try:
                with open(fp) as f:
                    d = json.load(f)
                transcripts[vid] = {"status": "DONE", "words": len(d.get("words", [])),
                                    "duration": d.get("duration", 0), "size_kb": round(sz / 1024)}
            except:
                transcripts[vid] = {"status": "CORRUPT", "size_kb": round(sz / 1024)}
        else:
            transcripts[vid] = {"status": "PENDING"}

    done = sum(1 for v in transcripts.values() if v["status"] == "DONE")
    status["stages"]["transcription"] = {
        "progress": f"{done}/{len(expected)}",
        "files": transcripts,
        "status": "DONE" if done == len(expected) else "RUNNING"
    }

    # Stage 1: PCM MOVs
    pcm_dir = os.path.join(BASE, "sources_pcm")
    src_dir = os.path.join(BASE, "sources")
    pcm_status = {}
    for vid in expected:
        mov = os.path.join(pcm_dir, f"{vid}.mov")
        mp4 = os.path.join(src_dir, f"{vid}.mp4")
        if os.path.exists(mov):
            try:
                mov_dur = float(subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mov],
                    capture_output=True, text=True, timeout=5).stdout.strip())
                src_dur = float(subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                    capture_output=True, text=True, timeout=5).stdout.strip()) if os.path.exists(mp4) else 0
                pct = round(mov_dur / src_dur * 100) if src_dur > 0 else 0
                ok = pct >= 99
                pcm_status[vid] = {"status": "VALID" if ok else "TRUNCATED",
                                   "duration": round(mov_dur), "source_duration": round(src_dur),
                                   "pct": pct}
            except:
                pcm_status[vid] = {"status": "ERROR"}
        else:
            pcm_status[vid] = {"status": "MISSING"}

    valid = sum(1 for v in pcm_status.values() if v["status"] == "VALID")
    status["stages"]["pcm_transcode"] = {
        "progress": f"{valid}/{len(expected)} valid",
        "files": pcm_status,
        "status": "DONE" if valid == len(expected) else "NEEDS_REDO"
    }

    # Stage 2: EDL
    edl_path = os.path.join(BASE, "edl.json")
    if os.path.exists(edl_path):
        try:
            with open(edl_path) as f:
                edl = json.load(f)
            n_clips = len(edl.get("clips", []))
            channels = list(set(c.get("channel", "") for c in edl.get("clips", [])))
            has_hook = bool(edl.get("hook", {}).get("video_id"))
            has_vo = bool(edl.get("vo", {}).get("intro"))
            total_dur = edl.get("total_clip_duration", 0)
            status["stages"]["edl"] = {
                "status": "READY" if n_clips >= 4 else "PRELIMINARY",
                "clips": n_clips, "channels": channels,
                "has_hook": has_hook, "has_vo": has_vo,
                "total_clip_duration": total_dur
            }
        except:
            status["stages"]["edl"] = {"status": "ERROR"}
    else:
        status["stages"]["edl"] = {"status": "NOT_STARTED"}

    # Stage 3: Cuts, seams, preview
    cuts_path = os.path.join(BASE, "cuts.json")
    seams_path = os.path.join(BASE, "seams.json")
    preview_path = os.path.join(BASE, "preview_v1.mp4")
    contact_path = os.path.join(BASE, "contact_sheet_v1.png")
    status_path = os.path.join(BASE, "status.json")

    s3 = {"status": "NOT_STARTED"}
    if os.path.exists(cuts_path):
        s3["cuts"] = "READY"
    if os.path.exists(seams_path):
        try:
            with open(seams_path) as f:
                seams = json.load(f)
            passed = sum(1 for s in seams if s.get("pass"))
            s3["seams"] = f"{passed}/{len(seams)} PASS"
        except:
            pass
    if os.path.exists(preview_path):
        s3["preview"] = "READY"
    if os.path.exists(contact_path):
        s3["contact_sheet"] = "READY"
    if os.path.exists(status_path):
        try:
            with open(status_path) as f:
                st = json.load(f)
            s3["status"] = st.get("status", "UNKNOWN")
        except:
            pass

    status["stages"]["cutting"] = s3

    # GPU status
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5)
        gpus = []
        for line in r.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                gpus.append({"gpu": parts[0], "util": parts[1], "mem_used": parts[2], "mem_total": parts[3]})
        status["gpus"] = gpus
    except:
        status["gpus"] = []

    return status


HTML_TEMPLATE = """<!DOCTYPE html>
<html><head>
<title>Segment V1 Dashboard</title>
<meta http-equiv="refresh" content="15">
<style>
body { background:#1a1a2e; color:#e0e0e0; font-family:monospace; margin:20px; }
h1 { color:#ff6b35; }
h2 { color:#ffa94d; margin-top:20px; }
.card { background:#16213e; border:1px solid #333; border-radius:8px; padding:15px; margin:10px 0; }
.done { color:#2ecc71; } .running { color:#f39c12; } .fail { color:#e74c3c; } .pending { color:#888; }
table { border-collapse:collapse; width:100%; }
td,th { text-align:left; padding:5px 10px; border-bottom:1px solid #333; }
th { color:#ffa94d; }
.gpu-bar { background:#333; height:16px; border-radius:3px; overflow:hidden; display:inline-block; width:120px; }
.gpu-fill { background:#ff6b35; height:100%; }
</style>
</head><body>
<h1>Protocol Pulse — Segment V1 Dashboard</h1>
<p style="color:#888;">Auto-refresh: 15s | {ts}</p>
{content}
</body></html>
"""


def render_html(status):
    parts = []

    # Transcription
    t = status["stages"].get("transcription", {})
    cls = "done" if t.get("status") == "DONE" else "running"
    parts.append(f'<h2>Stage 1d: Transcription [{t.get("progress","?")}]</h2><div class="card"><table>')
    parts.append("<tr><th>Video ID</th><th>Status</th><th>Words</th><th>Duration</th></tr>")
    for vid, info in t.get("files", {}).items():
        scls = "done" if info["status"] == "DONE" else "pending"
        words = info.get("words", "-")
        dur = f"{info.get('duration', 0):.0f}s" if info.get("duration") else "-"
        parts.append(f'<tr><td>{vid}</td><td class="{scls}">{info["status"]}</td><td>{words}</td><td>{dur}</td></tr>')
    parts.append("</table></div>")

    # PCM MOVs
    p = status["stages"].get("pcm_transcode", {})
    parts.append(f'<h2>Stage 1c: PCM MOV Transcode [{p.get("progress","?")}]</h2><div class="card"><table>')
    parts.append("<tr><th>Video ID</th><th>Status</th><th>Duration</th><th>Source</th><th>%</th></tr>")
    for vid, info in p.get("files", {}).items():
        scls = "done" if info["status"] == "VALID" else "fail"
        dur = f"{info.get('duration', 0)}s" if info.get("duration") else "-"
        src = f"{info.get('source_duration', 0)}s" if info.get("source_duration") else "-"
        pct = f"{info.get('pct', 0)}%" if info.get("pct") else "-"
        parts.append(f'<tr><td>{vid}</td><td class="{scls}">{info["status"]}</td><td>{dur}</td><td>{src}</td><td>{pct}</td></tr>')
    parts.append("</table></div>")

    # EDL
    e = status["stages"].get("edl", {})
    ecls = "done" if e.get("status") == "READY" else "running" if e.get("status") == "PRELIMINARY" else "pending"
    parts.append(f'<h2>Stage 2: EDL <span class="{ecls}">[{e.get("status","?")}]</span></h2><div class="card">')
    if e.get("clips"):
        parts.append(f'Clips: {e["clips"]} | Channels: {", ".join(e.get("channels",[]))} | '
                     f'Hook: {"YES" if e.get("has_hook") else "NO"} | '
                     f'VO: {"YES" if e.get("has_vo") else "NO"} | '
                     f'Total clip dur: {e.get("total_clip_duration", 0):.1f}s')
    else:
        parts.append("Not started yet.")
    parts.append("</div>")

    # Stage 3
    s3 = status["stages"].get("cutting", {})
    s3cls = "done" if s3.get("status") == "PREVIEW_READY" else "pending"
    parts.append(f'<h2>Stage 3: Cut & Preview <span class="{s3cls}">[{s3.get("status","?")}]</span></h2><div class="card">')
    items = []
    if s3.get("cuts"): items.append(f'Cuts: {s3["cuts"]}')
    if s3.get("seams"): items.append(f'Seams: {s3["seams"]}')
    if s3.get("preview"): items.append(f'Preview: {s3["preview"]}')
    if s3.get("contact_sheet"): items.append(f'Contact Sheet: {s3["contact_sheet"]}')
    parts.append(" | ".join(items) if items else "Not started yet.")
    parts.append("</div>")

    # GPUs
    parts.append('<h2>GPU Status</h2><div class="card"><table>')
    parts.append("<tr><th>GPU</th><th>Util</th><th>VRAM</th></tr>")
    for g in status.get("gpus", []):
        util_num = int(g["util"].replace(" %", "").replace("%", "")) if "%" in g["util"] else 0
        parts.append(f'<tr><td>GPU {g["gpu"]}</td><td>'
                     f'<div class="gpu-bar"><div class="gpu-fill" style="width:{util_num}%"></div></div> {g["util"]}'
                     f'</td><td>{g["mem_used"]} / {g["mem_total"]}</td></tr>')
    parts.append("</table></div>")

    return HTML_TEMPLATE.format(ts=status["ts"], content="\n".join(parts))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            status = get_status()
            html = render_html(status)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())
        elif self.path == "/api/status":
            status = get_status()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress logs


if __name__ == "__main__":
    port = 9090
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Dashboard: http://localhost:{port}/", flush=True)
    server.serve_forever()
