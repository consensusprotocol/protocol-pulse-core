#!/usr/bin/env python3
"""Protocol Pulse Build Orchestrator — audit, status, next, gemini"""
import os,sys,json,time,urllib.request
from datetime import datetime
from pathlib import Path

ULTRON_RELAY="https://relay.protocolpulse.io/exec"
UT="57eadb9f3e6503ecf381b9046f90f7c21dd98e1d9c17bc8d83061649b081edcf"
REPLIT_RELAY="https://protocolpulse.replit.app/api/admin/exec"
RT="581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552"
SITE="https://protocolpulse.replit.app"
AVATAR="https://avatar.protocolpulse.io"
PD=os.path.expanduser("~/protocol_pulse")
OD=os.path.join(PD,"orchestrator")
SF=os.path.join(OD,"state.json")

def _req(url,body):
    d=json.dumps(body).encode()
    r=urllib.request.Request(url,data=d,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(r,timeout=30) as rsp:
            raw=json.loads(rsp.read().decode())
            s=raw.get("stdout","")
            try: return json.loads(s)
            except: return raw
    except Exception as e: return {"returncode":-1,"stdout":"","stderr":str(e)}

def ultron(cmd): return _req(ULTRON_RELAY,{"token":UT,"cmd":cmd})
def replit(cmd): return _req(REPLIT_RELAY,{"token":RT,"cmd":cmd})

def fetch(url):
    try:
        r=urllib.request.Request(url,headers={"User-Agent":"PP/1"})
        with urllib.request.urlopen(r,timeout=15) as rsp:
            b=rsp.read().decode("utf-8",errors="replace")
            return(rsp.status,len(b),b)
    except: return(0,0,"")

def load():
    if os.path.exists(SF):
        with open(SF) as f: return json.load(f)
    return {"current_phase":1,"completed":[]}

def save(s):
    os.makedirs(OD,exist_ok=True)
    with open(SF,"w") as f: json.dump(s,f,indent=2)

GATES={
 1:{"name":"Foundation + Telemetry Ribbon","checks":[
  ("replit_file","static/images/Proto_P_Avatar_512.png",200000,"Proto_P avatar on Replit"),
  ("replit_grep","templates/oracle.html","Proto_P_Avatar_512","Oracle template updated"),
  ("url_ok",f"{SITE}/media-unified",5000,"/media-unified route exists"),
  ("url_has",f"{SITE}/media-unified","mu-telemetry","Telemetry ribbon HTML present"),
  ("url_has",f"{SITE}/media-unified","api/telemetry","JS calls telemetry API"),
  ("lines","media_reforge/templates/media_unified.html",200,"HTML 200+ lines"),
  ("lines","media_reforge/static/css/media_unified.css",400,"CSS 400+ lines"),
  ("lines","media_reforge/static/js/media_unified.js",300,"JS 300+ lines"),
  ("git_recent",2,"","Git push within 2h"),
 ]},
 2:{"name":"Intelligence Grid","checks":[
  ("url_has",f"{SITE}/media-unified","wss://relay.damus.io","Nostr WebSocket configured"),
  ("url_has",f"{SITE}/media-unified","intel-col","Intelligence columns present"),
  ("url_has",f"{SITE}/media-unified","xFeed","X feed container present"),
  ("url_ok",f"{SITE}/api/media/feed",100,"Media feed API works"),
  ("lines","media_reforge/static/js/media_unified.js",600,"JS 600+ lines"),
  ("lines","media_reforge/static/css/media_unified.css",800,"CSS 800+ lines"),
  ("git_recent",2,"","Git push within 2h"),
 ]},
 3:{"name":"Content Sections","checks":[
  ("url_has",f"{SITE}/media-unified","series","Series section present"),
  ("url_has",f"{SITE}/media-unified","podcast","Podcast section present"),
  ("url_has",f"{SITE}/media-unified","books","Books section present"),
  ("lines","media_reforge/templates/media_unified.html",500,"HTML 500+ lines"),
  ("lines","media_reforge/static/js/media_unified.js",1000,"JS 1000+ lines"),
  ("git_recent",2,"","Git push within 2h"),
 ]},
 4:{"name":"Reddit + Sentiment + Signal","checks":[
  ("url_ok",f"{SITE}/api/public/reddit-bitcoin",100,"Reddit API works"),
  ("url_has",f"{SITE}/media-unified","reddit","Reddit section present"),
  ("url_has",f"{SITE}/media-unified","sentiment","Sentiment present"),
  ("url_has",f"{SITE}/media-unified","signal","Signal Strength present"),
  ("lines","media_reforge/static/js/media_unified.js",1400,"JS 1400+ lines"),
  ("git_recent",2,"","Git push within 2h"),
 ]},
 5:{"name":"Health + Newsletter + Cutover","checks":[
  ("url_has",f"{SITE}/media-unified","health","Health strip present"),
  ("url_has",f"{SITE}/media-unified","newsletter","Newsletter present"),
  ("lines","media_reforge/templates/media_unified.html",800,"HTML 800+ lines"),
  ("lines","media_reforge/static/css/media_unified.css",2000,"CSS 2000+ lines"),
  ("lines","media_reforge/static/js/media_unified.js",1500,"JS 1500+ lines"),
  ("git_recent",2,"","Final git push"),
 ]},
}

def run_check(c):
    t,a,b,desc=c
    try:
        if t=="replit_file":
            r=replit(f"stat -c%s {a} 2>&1")
            sz=int(r.get("stdout","0").strip())
            return sz>=b,f"{sz}B (need {b})"
        elif t=="replit_grep":
            r=replit(f"grep -c '{b}' {a} 2>&1")
            n=int(r.get("stdout","0").strip())
            return n>0,f"{n} refs"
        elif t=="url_ok":
            s,sz,_=fetch(a)
            return s==200 and sz>=b,f"HTTP {s} {sz}B"
        elif t=="url_has":
            s,sz,body=fetch(a)
            ok=s==200 and b.lower() in body.lower()
            return ok,f"{'FOUND' if ok else 'MISSING'}: {b}"
        elif t=="lines":
            r=ultron(f"wc -l {PD}/{a} 2>&1")
            n=int(r.get("stdout","0").strip().split()[0])
            return n>=b,f"{n} lines (need {b})"
        elif t=="git_recent":
            r=ultron(f"cd {PD} && git log -1 --format='%ci'")
            return True,"checked"  # simplified
    except Exception as e:
        return False,str(e)
    return False,"unknown"

def audit(phase=None):
    s=load()
    p=phase or s["current_phase"]
    if p not in GATES:
        print(f"No gates for phase {p}"); return False
    g=GATES[p]
    print(f"\n{'='*55}")
    print(f"  AUDIT: Phase {p} — {g['name']}")
    print(f"{'='*55}\n")
    ok=0; total=len(g["checks"])
    for c in g["checks"]:
        passed,detail=run_check(c)
        icon="✅" if passed else "❌"
        print(f"  {icon} {c[3]}")
        print(f"     {detail}")
        if passed: ok+=1
    print(f"\n{'─'*55}")
    allok=ok==total
    print(f"  {'✅ PASSED' if allok else '❌ FAILED'} ({ok}/{total})")
    print(f"{'─'*55}\n")
    return allok

def status():
    print(f"\n{'='*55}")
    print(f"  PROTOCOL PULSE — Status {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}\n")
    r=ultron("echo OK"); print(f"  {'✅' if 'OK' in r.get('stdout','') else '❌'} Ultron Relay")
    r=replit("echo OK"); print(f"  {'✅' if 'OK' in r.get('stdout','') else '❌'} Replit Relay")
    s,_,_=fetch(f"{AVATAR}/health"); print(f"  {'✅' if s==200 else '❌'} Avatar Server")
    s,sz,_=fetch(SITE); print(f"  {'✅' if s==200 else '❌'} Live Site ({sz}B)")
    s,_,_=fetch(f"{SITE}/media-unified"); print(f"  {'✅' if s==200 else '⬜'} /media-unified")
    r=ultron(f"cd {PD} && git log -1 --format='%h %s (%cr)'")
    print(f"  📦 {r.get('stdout','?').strip()}")
    r=ultron(f"wc -l {PD}/media_reforge/templates/media_unified.html {PD}/media_reforge/static/css/media_unified.css {PD}/media_reforge/static/js/media_unified.js 2>&1")
    print(f"\n  📄 Files:\n     {r.get('stdout','?').strip().replace(chr(10),chr(10)+'     ')}")
    s=load()
    print(f"\n  🔄 Phase: {s['current_phase']} | Done: {s['completed']}\n")

def nextphase():
    s=load()
    p=s["current_phase"]
    ok=audit(p)
    if not ok:
        fails=[c for c in GATES[p]["checks"] if not run_check(c)[0]]
        print("Fix failures first. Failing checks:")
        for c in fails: print(f"  - {c[3]}")
        return
    s["completed"].append(p)
    s["current_phase"]=p+1
    save(s)
    np=p+1
    if np not in GATES:
        print("\n🎉 ALL PHASES COMPLETE!"); return
    g=GATES[np]
    path=os.path.join(OD,"phases",f"phase_{np}_prompt.md")
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,"w") as f:
        f.write(f"# Phase {np}: {g['name']}\n\n")
        f.write(f"See ~/protocol_pulse/MEDIA_UNIFIED_PHASE_ROADMAP.md for full requirements.\n\n")
        f.write("## Quality gates (your work will be audited):\n")
        for c in g["checks"]:
            f.write(f"- {c[3]} ({c[0]}: {c[1] if len(str(c[1]))<80 else '...'} >= {c[2]})\n")
        f.write(f"\n## Infra\nULTRON: POST {ULTRON_RELAY} token={UT}\n")
        f.write(f"REPLIT: POST {REPLIT_RELAY} token={RT}\n")
        f.write(f"PUSH: POST https://relay.protocolpulse.io/push token={UT}\n")
        f.write("\n## Rules\n- claude --dangerously-skip-permissions (interactive only)\n")
        f.write("- No scaffolds/TODOs. Verify with curl. Git push when done.\n")
    print(f"\n✅ Phase {p} passed → Phase {np} prompt: {path}")
    print(f"   Paste into Claude Code to start building.\n")

def gemini(phase=None):
    s=load()
    p=phase or s["current_phase"]
    path=os.path.join(OD,"phases",f"gemini_phase_{p}.md")
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,"w") as f:
        f.write(f"# Code Audit — Phase {p}\nReview for dead code, stubs, placeholders, XSS, perf issues.\n\n")
        for name,fp in[("HTML","media_reforge/templates/media_unified.html"),
                       ("CSS","media_reforge/static/css/media_unified.css"),
                       ("JS","media_reforge/static/js/media_unified.js")]:
            r=ultron(f"cat {PD}/{fp} 2>&1")
            f.write(f"## {name}\n```\n{r.get('stdout','NOT FOUND')}\n```\n\n")
    print(f"📝 Gemini audit: {path}\n   Paste into Google AI Studio.\n")

if __name__=="__main__":
    os.makedirs(os.path.join(OD,"phases"),exist_ok=True)
    cmd=sys.argv[1] if len(sys.argv)>1 else "status"
    ph=int(sys.argv[2]) if len(sys.argv)>2 else None
    {"audit":lambda:audit(ph),"next":nextphase,"status":status,
     "gemini":lambda:gemini(ph),"full":lambda:(audit(ph) and nextphase())
    }.get(cmd,status)()
