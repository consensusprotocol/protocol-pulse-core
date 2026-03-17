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
def readn(path,n=300):
    try:
        lines=open(path).readlines()
        return "".join(f"{i+1:4d} | {l}" for i,l in enumerate(lines[:n]))
    except: return "(not found)"
def keysec(path,kw,c=4,mx=20):
    try:
        lines=open(path).readlines(); hits=[]
        for i,l in enumerate(lines):
            if any(k in l for k in kw):
                s=max(0,i-c); e=min(len(lines),i+c+1)
                hits.append("".join(f"{j+1:4d}|{lines[j]}" for j in range(s,e)))
                if len(hits)>=mx: break
        return "\n---\n".join(hits)
    except: return "(err)"
results={}
def call_gemini(p):
    url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}"
    body=json.dumps({"contents":[{"parts":[{"text":p}]}],"generationConfig":{"temperature":0.1,"maxOutputTokens":6000}}).encode()
    try:
        resp=urllib.request.urlopen(urllib.request.Request(url,body,{"Content-Type":"application/json"}),timeout=180,context=ctx)
        d=json.loads(resp.read()); return d["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e: return f"GEMINI_ERROR:{e}"
def call_gpt4(p):
    url="https://api.openai.com/v1/chat/completions"
    body=json.dumps({"model":"gpt-4o","messages":[{"role":"user","content":p}],"temperature":0.1,"max_tokens":5000}).encode()
    try:
        req=urllib.request.Request(url,body,{"Content-Type":"application/json","Authorization":f"Bearer {OPENAI_KEY}"})
        resp=urllib.request.urlopen(req,timeout=180); d=json.loads(resp.read()); return d["choices"][0]["message"]["content"]
    except Exception as e: return f"GPT4_ERROR:{e}"
def call_grok(p):
    url="https://api.x.ai/v1/chat/completions"
    body=json.dumps({"model":"grok-3","messages":[{"role":"user","content":p}],"temperature":0.1,"max_tokens":5000}).encode()
    try:
        req=urllib.request.Request(url,body,{"Content-Type":"application/json","Authorization":f"Bearer {XAI_KEY}"})
        resp=urllib.request.urlopen(req,timeout=180); d=json.loads(resp.read()); return d["choices"][0]["message"]["content"]
    except Exception as e: return f"GROK_ERROR:{e}"
def run(name,fn,prompt):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} started")
    t0=time.time(); results[name]=fn(prompt)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} done {time.time()-t0:.0f}s")
known="GEMINI GRADE F FAILURES: AUDIO_SILENT -70 LUFS, 40 silence gaps, 10 black frames, 17 freeze frames, HTTP 404 voice_id uxKr2vlA4hYgXZR1oPRT, DUAL_HOST_ENABLED=False but still silent. Only valid voice: PBX=HmUVvDlHsEz0m3eUGLgu"
prompt="You are a senior video pipeline engineer. Fresh audit, zero prior context. Be brutal.\n"+known+"\n=== dual_host_tts.py ===\n"+readn(PIPE/"dual_host_tts.py",50)+"\n=== tts_engine.py (300 lines) ===\n"+readn(PIPE/"tts_engine.py",300)+"\n=== script_writer.py (250 lines) ===\n"+readn(PIPE/"script_writer.py",250)+"\n=== render_loop.py (200 lines) ===\n"+readn(BASE/"autonomous_render_loop.py",200)+"\n=== assembler.py TTS/AUDIO KEY SECTIONS ===\n"+keysec(PIPE/"assembler.py",["tts_elevenlabs","generate_tts","voice_id","bgl_audio","silence","DUAL_HOST","PBX_VOICE"])+"\nANSWER: 1)Why silent despite DUAL_HOST=False? 2)Where does voice_id uxKr2vlA4hYgXZR1oPRT originate? 3)Root cause black+silence? 4)P0 bugs with file/line/fix."
print(f"Prompt: {len(prompt):,} chars")
threads=[threading.Thread(target=run,args=(n,fn,prompt)) for n,fn in [("Gemini",call_gemini),("GPT4o",call_gpt4),("Grok3",call_grok)]]
for t in threads: t.start()
for t in threads: t.join()
ts=datetime.now().strftime("%Y%m%d_%H%M%S")
out=OUT/f"forensic_{ts}.md"
with open(out,"w") as f:
    f.write(f"# Pipeline Forensic Audit {datetime.now()}\n\n")
    for m,res in results.items():
        f.write(f"\n---\n## {m}\n{res}\n")
print(f"\nSaved: {out}")
for m,res in results.items():
    print(f"\n=== {m} ==="); print(res[:2000]); print("...")
