from __future__ import annotations
from typing import Dict, List, Tuple
from pronunciation import lookup_pronunciation, normalize_word

PHONEME_TO_VISEME: Dict[str, int] = {
    "SIL":0,"SP":0,"PAUSE":0,"HH":0,
    "P":1,"B":1,"M":1,
    "F":2,"V":2,
    "TH":3,"DH":3,
    "T":4,"D":4,"L":4,
    "K":5,"G":5,"Q":5,
    "CH":6,"JH":6,"SH":6,"ZH":6,
    "S":7,"Z":7,
    "N":8,"NG":8,
    "R":9,"ER":9,
    "AA":10,"AH":10,
    "AE":11,"EH":11,"AY":11,
    "IH":12,"IY":12,"EY":12,"Y":12,
    "AO":13,"OY":13,"OW":13,
    "UW":14,"UH":14,"W":14,"AW":14,
}

def chars_to_word_spans(alignment: dict) -> List[Tuple[str, float, float]]:
    chars = alignment.get("characters",[])
    starts = alignment.get("character_start_times_seconds",[])
    ends = alignment.get("character_end_times_seconds",[])
    if not chars or not (len(chars)==len(starts)==len(ends)):
        return []
    spans = []
    current = []; current_start = None
    for idx,(ch,st,en) in enumerate(zip(chars,starts,ends)):
        is_last = idx==len(chars)-1
        if ch.isspace():
            if current:
                spans.append(("".join(current),float(current_start),float(ends[idx-1])))
                current=[]; current_start=None
            continue
        if current_start is None: current_start=float(st)
        current.append(ch)
        if is_last: spans.append(("".join(current),float(current_start),float(en)))
    return spans

def phonemes_to_visemes(phones: List[str]) -> List[int]:
    return [PHONEME_TO_VISEME.get(p.rstrip("012"),10) for p in phones] or [0]

def _duration_weight(phone: str) -> float:
    b = phone.rstrip("012")
    if b in {"AA","AH","AE","EH","IH","IY","AO","OW","UW","UH","AY","OY","AW","EY"}: return 1.55
    if b in {"M","N","NG","R","L"}: return 1.15
    if b in {"S","Z","SH","ZH","F","V","TH","DH"}: return 1.2
    return 0.95

def build_viseme_timeline(text: str, alignment: dict) -> List[dict]:
    spans = chars_to_word_spans(alignment)
    if not spans:
        return [{"time":0.0,"viseme":0,"duration":0.25,"word":""}]
    timeline = []
    for raw_word, start_t, end_t in spans:
        word = normalize_word(raw_word)
        if not word: continue
        phones = lookup_pronunciation(word) or ["AH"]
        visemes = phonemes_to_visemes(phones)
        word_dur = max(0.05, end_t - start_t)
        weights = [_duration_weight(p) for p in phones]
        weight_sum = sum(weights) or 1.0
        cursor = start_t
        for i,(phone,viseme_id,w) in enumerate(zip(phones,visemes,weights)):
            dur = word_dur * (w / weight_sum)
            if viseme_id==1 and i>0:
                pre = min(0.025, dur*0.25)
                if timeline:
                    timeline[-1]["duration"] = max(0.015, timeline[-1]["duration"]-pre)
                    cursor -= pre; dur += pre
            timeline.append({"time":round(cursor,4),"viseme":int(viseme_id),
                              "duration":round(max(0.018,dur),4),"word":word})
            cursor += dur
        if raw_word.endswith((".",  "!", "?", ",", ";", ":")):
            timeline.append({"time":round(end_t,4),"viseme":0,"duration":0.06,"word":""})
    # coalesce
    coalesced = []
    for item in timeline:
        if coalesced and coalesced[-1]["viseme"]==item["viseme"]:
            coalesced[-1]["duration"] = round(coalesced[-1]["duration"]+item["duration"],4)
        else:
            coalesced.append(item.copy())
    end_time = (coalesced[-1]["time"]+coalesced[-1]["duration"]) if coalesced else 0.0
    coalesced.append({"time":round(end_time,4),"viseme":0,"duration":0.15,"word":""})
    return coalesced
