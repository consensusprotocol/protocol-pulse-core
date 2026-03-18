from __future__ import annotations
import subprocess,re,logging
from pathlib import Path
logger=logging.getLogger(__name__)

def measure_lufs(path):
    try:
        res=subprocess.run(['ffmpeg','-i',str(path),'-af','loudnorm=I=-14:TP=-2:LRA=7:print_format=json','-f','null','-'],capture_output=True,text=True,timeout=120)
        i_m=re.search(r'"input_i"\s*:\s*"([^"]+)"',res.stderr)
        tp_m=re.search(r'"input_tp"\s*:\s*"([^"]+)"',res.stderr)
        return float(i_m.group(1)) if i_m else -99.0, float(tp_m.group(1)) if tp_m else -99.0
    except Exception as e:
        logger.warning(f"[probe] lufs failed {path.name}: {e}")
        return -99.0,-99.0

def detect_black_frames(path,min_dur=0.5):
    try:
        res=subprocess.run(['ffmpeg','-i',str(path),'-vf',f'blackdetect=d={min_dur}:pix_th=0.02','-an','-f','null','-'],capture_output=True,text=True,timeout=120)
        return [(float(m.group(1)),float(m.group(2)),float(m.group(3))) for m in re.finditer(r'black_start:([\.\d]+).*?black_end:([\.\d]+).*?black_duration:([\.\d]+)',res.stderr)]
    except:
        return []

def detect_silence(path,min_dur=1.0,noise_db=-50.0):
    try:
        res=subprocess.run(['ffmpeg','-i',str(path),'-af',f'silencedetect=n={noise_db}dB:d={min_dur}','-f','null','-'],capture_output=True,text=True,timeout=120)
        starts=re.findall(r'silence_start: ([\.\d]+)',res.stderr)
        ends=re.findall(r'silence_end: ([\.\d]+)',res.stderr)
        return [(float(s),float(e)) for s,e in zip(starts,ends)]
    except:
        return []

def has_motion(path):
    try:
        res=subprocess.run(['ffprobe','-v','error','-select_streams','v','-show_entries','stream=nb_frames','-of','csv=p=0',str(path)],capture_output=True,text=True,timeout=15)
        frames=res.stdout.strip()
        return int(frames)>1 if frames and frames.isdigit() else True
    except:
        return True
