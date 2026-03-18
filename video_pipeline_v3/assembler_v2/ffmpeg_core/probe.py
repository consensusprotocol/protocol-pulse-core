from __future__ import annotations
import subprocess,re,json,logging
from pathlib import Path
logger=logging.getLogger(__name__)

def measure_lufs(path:Path)->tuple:
    """Measure integrated loudness via loudnorm JSON output. Returns (lufs,true_peak) or (-99,-99)."""
    try:
        res=subprocess.run(
            ['ffmpeg','-hide_banner','-i',str(path),
             '-af','loudnorm=I=-14:TP=-2:LRA=7:print_format=json',
             '-f','null','-'],
            capture_output=True,text=True,timeout=120)
        # loudnorm JSON is in stderr — find the JSON block
        stderr=res.stderr
        json_start=stderr.rfind('{')
        json_end=stderr.rfind('}')+1
        if json_start>=0 and json_end>json_start:
            data=json.loads(stderr[json_start:json_end])
            lufs=float(data.get('input_i',-99))
            tp=float(data.get('input_tp',-99))
            return lufs,tp
        # Fallback to regex if JSON not found
        i_m=re.search(r'"input_i"\s*:\s*"([^"]+)"',stderr)
        tp_m=re.search(r'"input_tp"\s*:\s*"([^"]+)"',stderr)
        return (float(i_m.group(1)) if i_m else -99.0),(float(tp_m.group(1)) if tp_m else -99.0)
    except Exception as e:
        logger.warning(f'[probe] lufs failed {path.name}: {e}')
        return -99.0,-99.0

def detect_black_frames(path:Path,min_dur:float=0.5)->list:
    """Returns list of (start,end,duration) tuples for black segments."""
    try:
        res=subprocess.run(
            ['ffmpeg','-hide_banner','-i',str(path),
             '-vf',f'blackdetect=d={min_dur}:pix_th=0.02','-an','-f','null','-'],
            capture_output=True,text=True,timeout=120)
        return [(float(m.group(1)),float(m.group(2)),float(m.group(3)))
                for m in re.finditer(
                    r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)',
                    res.stderr)]
    except Exception as e:
        logger.warning(f'[probe] blackdetect failed: {e}')
        return []

def detect_silence(path:Path,min_dur:float=1.0,noise_db:float=-50.0)->list:
    """Returns list of (start,end) tuples for silence gaps."""
    try:
        res=subprocess.run(
            ['ffmpeg','-hide_banner','-i',str(path),
             '-af',f'silencedetect=n={noise_db}dB:d={min_dur}','-f','null','-'],
            capture_output=True,text=True,timeout=120)
        starts=re.findall(r'silence_start: ([\d.]+)',res.stderr)
        ends=re.findall(r'silence_end: ([\d.]+)',res.stderr)
        return [(float(s),float(e)) for s,e in zip(starts,ends)]
    except Exception as e:
        logger.warning(f'[probe] silencedetect failed: {e}')
        return []

def has_motion(path:Path)->bool:
    """Quick check video has actual frames (not frozen/static)."""
    try:
        res=subprocess.run(
            ['ffprobe','-v','error','-select_streams','v',
             '-show_entries','stream=nb_frames','-of','csv=p=0',str(path)],
            capture_output=True,text=True,timeout=15)
        val=res.stdout.strip()
        return int(val)>1 if val and val.isdigit() else True
    except Exception:
        return True
