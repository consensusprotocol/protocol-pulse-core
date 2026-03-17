import os,json,threading,time,urllib.request,ssl
from pathlib import Path
from datetime import datetime

BASE=Path("/home/ultron/protocol_pulse")
PIPE=BASE/"video_pipeline_v3"
OUT=BASE/"docs/audits"
OUT.mkdir(parents=True,exist_ok=True)
ctx=ssl._create_unverified_context()

for line in open(BASE/".env"):
    l=line.strip()
    if "=" in l and not l.startswith("#"):
        k,_,v=l.partition("="); k=k.strip(); v=v.strip().strip("'").strip('"')
        if k: os.environ[k]=v

GEMINI_KEY=os.environ.get("GEMINI_API_KEY","")
OPENAI_KEY=os.environ.get("OPENAI_API_KEY","")
XAI_KEY=os.environ.get("XAI_API_KEY","")

def readn(path,n=200):
    try:
        lines=open(path).readlines()
        return "".join(f"{i+1:4d}|{l}" for i,l in enumerate(lines[:n]))
    except: return "(not found)"

def keysec(path,kw,c=4,mx=15):
    try:
        lines=open(path).readlines(); hits=[]
        for i,l in enumerate(lines):
            if any(k in l for k in kw):
                s=max(0,i-c); e=min(len(lines),i+c+1)
                hits.append("".join(f"{j+1:4d}|{lines[j]}" for j in range(s,e)))
                if len(hits)>=mx: break
        return "\n---\n".join(hits)
    except: return "(err)"

CONTEXT = """
PROTOCOL PULSE PIPELINE — FULL FORENSIC AUDIT + SOLUTION VALIDATION

=== WHAT THIS IS ===
Autonomous daily Bitcoin video show. Renders 8-10min episodes using:
- ElevenLabs TTS (only PBX voice HmUVvDlHsEz0m3eUGLgu allowed)  
- ffmpeg assembly (APEX V2 architecture)
- YouTube clip extraction (80 channels)
- Gemini 2.5 Pro quality grading (target: Grade A = 90+/100)

=== ROOT CAUSES IDENTIFIED TONIGHT ===
1. GHOST VOICE: assembler.py defaulted host=1 when key missing → called deleted voice uxKr2vlA4hYgXZR1oPRT → ElevenLabs 404 → silent TTS. FIXED: host default now 2.
2. SILENT FALLBACK: _generate_fallback_silent_audio() swallowed TTS failures silently. FIXED: now raises RuntimeError.
3. AMIX BUG (ROOT CAUSE OF -70 LUFS): concatenate_parts() used amix duration=longest with BGM weight=0.04. When BGM loop outlasted TTS track, only 4% BGM remained = -70 LUFS. FIXED: duration=first, weight=0.08, audio guard validates concat_raw has audio before mixing.
4. GEMINI GRADING STALE FILE: grader was picking up bgl_audio.mp4 temp files instead of final mp4. FIXED: excluded in candidates filter.

=== PROPOSED HARDENING SOLUTIONS (VALIDATE THESE) ===
A. Circuit breakers: every external API (ElevenLabs, CoinGecko, Anthropic, Twitter) gets fallback chain. ElevenLabs→OpenAI TTS→pyttsx3 local.
B. Pre-render confidence score: 60s pre-check validates all APIs, asset sources, clip availability, TTS quota. Render starts with known confidence level.
C. UTC date lock: one canonical date object set at daily_producer.py entry, passed through all functions. No datetime.now() downstream.
D. Multi-tier clip fallback: Tier1=fresh 48h YouTube, Tier2=evergreen curated library, Tier3=X Spaces audio, Tier4=synthetic B-roll.
E. X Spaces live clip system: records HLS stream, Whisper transcribes, scores 20-30s highlights by info density, PBX narrates over actual Space audio.

=== QUESTIONS FOR YOU ===
1. Are the three root cause fixes above complete and correct? Any edge cases we missed?
2. Are the proposed hardening solutions A-E complete? What are we missing?
3. What is the single highest-impact fix we have NOT yet made?
4. In the amix fix: duration=first means the output length = TTS track length. Is this correct or could it cut off BGM prematurely in edge cases?
5. For the X Spaces system: what's the most reliable way to capture Twitter Spaces HLS stream using yt-dlp or ffmpeg without rate limiting?
6. What other runtime failure modes exist that a pre-render confidence check would NOT catch?

=== CODE BEING AUDITED ===
"""

PROMPT = CONTEXT + "\n=== dual_host_tts.py ===\n" + readn(PIPE/"dual_host_tts.py",30) + \
    "\n=== tts_engine.py (200 lines) ===\n" + readn(PIPE/"tts_engine.py",200) + \
    "\n=== assembler.py AMIX/CONCAT SECTION ===\n" + keysec(PIPE/"assembler.py",["amix","duration=","weights=","has_bgm","bgl_audio","audio guard","concat_raw","music_mixed"]) + \
    "\n=== assembler.py TTS BUILD SECTION ===\n" + keysec(PIPE/"assembler.py",["host_num","generate_tts","tts_elevenlabs","ABORT","fallback_silent"]) + \
    "\n=== autonomous_render_loop.py (150 lines) ===\n" + readn(BASE/"autonomous_render_loop.py",150) + \
    "\n=== script_writer.py (100 lines) ===\n" + readn(PIPE/"script_writer.py",100) + \
    "\n\nBe brutally specific. Line numbers where relevant. Rate every proposed solution P0/P1/P2."

results={}

def call_gemini(p):
    url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}"
    body=json.dumps({"contents":[{"parts":[{"text":p}]}],"generationConfig":{"temperature":0.1,"maxOutputTokens":8000}}).encode()
    try:
        resp=urllib.request.urlopen(urllib.request.Request(url,body,{"Content-Type":"application/json"}),timeout=180,context=ctx)
        d=json.loads(resp.read()); return d["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e: return f"GEMINI_ERROR:{e}"

def call_gpt4(p):
    url="https://api.openai.com/v1/chat/completions"
    body=json.dumps({"model":"gpt-4o","messages":[{"role":"user","content":p}],"temperature":0.1,"max_tokens":6000}).encode()
    try:
        req=urllib.request.Request(url,body,{"Content-Type":"application/json","Authorization":f"Bearer {OPENAI_KEY}"})
        resp=urllib.request.urlopen(req,timeout=180); d=json.loads(resp.read()); return d["choices"][0]["message"]["content"]
    except Exception as e: return f"GPT4_ERROR:{e}"

def call_grok(p):
    url="https://api.x.ai/v1/chat/completions"
    body=json.dumps({"model":"grok-3","messages":[{"role":"user","content":p}],"temperature":0.1,"max_tokens":6000}).encode()
    try:
        req=urllib.request.Request(url,body,{"Content-Type":"application/json","Authorization":f"Bearer {XAI_KEY}"})
        resp=urllib.request.urlopen(req,timeout=180); d=json.loads(resp.read()); return d["choices"][0]["message"]["content"]
    except Exception as e: return f"GROK_ERROR:{e}"

print(f"[{datetime.now().strftime('%H:%M:%S')}] Firing full audit: Gemini + GPT-4o + Grok-3 in parallel")
print(f"Prompt: {len(PROMPT):,} chars")

def run(name,fn):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} started")
    t0=time.time(); results[name]=fn(PROMPT)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} done {time.time()-t0:.0f}s ({len(results[name])} chars)")

threads=[threading.Thread(target=run,args=(n,fn)) for n,fn in [("Gemini",call_gemini),("GPT4o",call_gpt4),("Grok3",call_grok)]]
for t in threads: t.start()
for t in threads: t.join()

ts=datetime.now().strftime("%Y%m%d_%H%M%S")
out=OUT/f"full_hardening_audit_{ts}.md"
with open(out,"w") as f:
    f.write(f"# Protocol Pulse Full Hardening Audit\nGenerated: {datetime.now()}\n\n")
    for m,res in results.items():
        f.write(f"\n---\n## {m}\n{res}\n")

print(f"\n[COMPLETE] Saved: {out}")
for m,res in results.items():
    print(f"\n=== {m} ==="); print(res[:2500]); print("...")
