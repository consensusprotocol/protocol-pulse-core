"""
Viseme Generator — CMU Arpabet to 18-viseme Oculus mapping with co-articulation.
Converts ElevenLabs character-level alignment into a viseme timeline for client-side rendering.
"""

# 18-viseme set (14 Oculus + 4 added for premium)
PHONEME_TO_VISEME = {
    # Silence
    'SIL': 0, 'SP': 0,
    # PP — bilabials (lips together)
    'P': 1, 'B': 1, 'M': 1,
    # FF — labiodentals
    'F': 2, 'V': 2,
    # TH — dentals
    'TH': 3, 'DH': 3,
    # DD — alveolars
    'T': 4, 'D': 4, 'N': 4, 'L': 4,
    # KK — velars
    'K': 5, 'G': 5, 'NG': 5,
    # CH — palatoalveolars
    'CH': 6, 'JH': 6, 'SH': 6, 'ZH': 6,
    # SS — sibilants
    'S': 7, 'Z': 7,
    # NN — nasals (final position)
    'HH': 8,
    # RR — rhotics
    'R': 9, 'ER': 9,
    # AA — open vowels
    'AA': 10, 'AH': 10,
    # EE — mid-front vowels
    'EH': 11, 'AE': 11, 'AY': 11, 'EY': 11,
    # IH — high-front vowels
    'IH': 12, 'IY': 12,
    # OH — mid-back rounded vowels
    'AO': 13, 'OW': 13, 'OY': 13,
    # OU — high-back rounded vowels
    'UW': 14, 'UH': 14,
    # W/Y semi-vowels
    'W': 14, 'Y': 12,
    # NEW visemes 15-17
    # 15 = half-open neutral (between sil and aa — used for mid-stress)
    'AW': 15,
    # 16 = wide-E emphasis (exaggerated E for stressed syllables)
    # mapped dynamically based on amplitude
    # 17 = smile-neutral (idle/rest state)
}

WIDE_VOWELS = {10, 11, 15, 16}
CLOSED_CONSONANTS = {0, 1, 3, 7}
COARTICULATION_OFFSET = 0.020  # 20ms look-ahead


def text_to_viseme_timeline(text: str, alignment: dict) -> list:
    """Convert text + ElevenLabs alignment into a viseme timeline.

    Args:
        text: original text
        alignment: ElevenLabs alignment dict with 'characters',
                   'character_start_times_seconds', 'character_end_times_seconds'

    Returns:
        list of {time, viseme, duration, word} dicts
    """
    import nltk
    try:
        cmu = nltk.corpus.cmudict.dict()
    except LookupError:
        nltk.download('cmudict', quiet=True)
        cmu = nltk.corpus.cmudict.dict()

    from viseme.bitcoin_lexicon import get_phonemes

    chars = alignment.get('characters', [])
    starts = alignment.get('character_start_times_seconds', [])
    ends = alignment.get('character_end_times_seconds', [])

    if not chars:
        return [{"time": 0, "viseme": 0, "duration": 1.0, "word": ""}]

    # Reconstruct words with timing
    words = []
    current_word = ''
    word_start = 0.0

    for i, (char, start, end) in enumerate(zip(chars, starts, ends)):
        is_last = (i == len(chars) - 1)
        if char == ' ' or is_last:
            if is_last and char != ' ':
                current_word += char
            if current_word.strip():
                words.append({'word': current_word, 'start': word_start, 'end': end})
            current_word = ''
            word_start = end
        else:
            if not current_word:
                word_start = start
            current_word += char

    timeline = []

    for word_data in words:
        word = word_data['word']
        word_start = word_data['start']
        word_end = word_data['end']
        word_duration = word_end - word_start
        if word_duration <= 0:
            continue

        phonemes = get_phonemes(word, cmu)

        if not phonemes:
            # Fallback: open mouth for word duration
            timeline.append({
                'time': word_start, 'viseme': 10,
                'duration': word_duration, 'word': word
            })
            continue

        # Strip stress markers, map to visemes
        visemes = []
        for ph in phonemes:
            ph_clean = ph.rstrip('012')
            visemes.append(PHONEME_TO_VISEME.get(ph_clean, 0))

        # Distribute phonemes across word duration
        ph_dur = word_duration / len(visemes)
        for j, v in enumerate(visemes):
            timeline.append({
                'time': word_start + j * ph_dur,
                'viseme': v,
                'duration': ph_dur,
                'word': word
            })

    # Apply co-articulation: pull wide vowels 20ms earlier when preceded by closed consonant
    result = []
    for i, entry in enumerate(timeline):
        if (i > 0
            and entry['viseme'] in WIDE_VOWELS
            and timeline[i-1]['viseme'] in CLOSED_CONSONANTS):
            adjusted = entry.copy()
            adjusted['time'] = max(0.0, entry['time'] - COARTICULATION_OFFSET)
            result.append(adjusted)
        else:
            result.append(entry)

    # Add final silence
    if result:
        last = result[-1]
        result.append({'time': last['time'] + last['duration'], 'viseme': 0, 'duration': 0.5, 'word': ''})

    return result
