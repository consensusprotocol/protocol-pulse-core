"""
HUMAN VOICE FILTER - Protocol Pulse
====================================
Authentic human voice. Pro self-custody. No AI slop.
"""

import re
import random

class HumanVoiceFilter:
    
    KEEP_CAPS = {'BTC', 'ETH', 'USD', 'ETF', 'SEC', 'FBI', 'CEO', 'CFO', 'US', 'UK', 'EU', 
                 'IMF', 'GDP', 'IPO', 'API', 'NFT', 'CBDC', 'DCA', 'ATH', 'HODL', 'FED', 'ECB', 'APP'}
    
    ETF_SHILL_PHRASES = [
        (r'ETF\s*(is|are)\s*(great|amazing|incredible|fantastic|revolutionary)', 'ETF provides exposure'),
        (r'(massive|huge|incredible|amazing)\s*ETF\s*(inflows|flows)', 'notable ETF inflows'),
        (r'ETF\s*(approval|launch)\s*(is|was)\s*(huge|massive|game.?changing)', 'ETF approval happened'),
        (r'buy\s*(the\s*)?ETF', 'consider the ETF (though self-custody is better)'),
        (r'ETF\s*makes?\s*bitcoin\s*(easy|simple|accessible)', 'ETF offers exposure, but self-custody offers sovereignty'),
    ]
    
    SOVEREIGNTY_NUDGES = [
        " — not your keys, not your coins",
        " — self-custody remains the way", 
        " — remember: hold your own keys",
        " (still better to self-custody)",
        " — sovereignty > convenience",
        "", "", "",  # Sometimes no nudge
    ]
    
    def remove_emojis(self, text: str) -> str:
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001f926-\U0001f937"
            u"\U00010000-\U0010ffff"
            u"\u2640-\u2642"
            u"\u2600-\u2B55"
            u"\u200d\u23cf\u23e9\u231a\ufe0f\u3030"
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub('', text)
    
    def remove_ai_hooks(self, text: str) -> str:
        """Remove AI hooks COMPLETELY - not just lowercase"""
        
        # Remove these ENTIRELY from start of text
        hooks_to_strip = [
            r'^[:\s]*breaking[:\s]+',
            r'^[:\s]*icymi[:\s]+',
            r'^[:\s]*thread[:\s]+',
            r'^[:\s]*psa[:\s]+',
            r'^[:\s]*alert[:\s]+',
            r'^[:\s]*update[:\s]+',
            r'^[:\s]*news[:\s]+',
            r'^[:\s]*intel\s*brief[:\s]+',
            r'^[:\s]*deep\s*dive[:\s]+',
            r'^[:\s]*analysis[:\s]+',
            r'^[:\s]*signal[:\s]+',
            r'^[:\s]*massive\s*news[:\s]+',
            r'^[:\s]*big\s*news[:\s]+',
            r'^[:\s]*huge[:\s]+',
            r'^[:\s]*check\s*out[:\s]*',
            r'^[:\s]*don\'?t\s*miss[:\s]*',
            r'^[:\s]*must\s*read[:\s]+',
            r'^[:\s]*here\'?s\s*why[:\s]*',
        ]
        
        result = text.strip()
        
        # Keep removing until no more matches
        changed = True
        while changed:
            changed = False
            for hook in hooks_to_strip:
                new_result = re.sub(hook, '', result, flags=re.IGNORECASE).strip()
                if new_result != result:
                    result = new_result
                    changed = True
        
        # Remove from end
        end_hooks = [
            r'\s*don\'?t\s*miss\s*this[!.\s]*$',
            r'\s*check\s*it\s*out[!.\s]*$',
            r'\s*read\s*more[!.\s]*$',
            r'\s*link\s*in\s*bio[!.\s]*$',
        ]
        
        for hook in end_hooks:
            result = re.sub(hook, '', result, flags=re.IGNORECASE)
        
        return result.strip()
    
    def apply_sovereignty_filter(self, text: str) -> str:
        """Neutralize ETF shilling, promote self-custody"""
        
        result = text
        
        for pattern, replacement in self.ETF_SHILL_PHRASES:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Add sovereignty nudge to ETF content (40% chance)
        if 'etf' in result.lower() and len(result) < 230 and random.random() < 0.40:
            nudge = random.choice(self.SOVEREIGNTY_NUDGES)
            if nudge:
                result = result.rstrip('.!') + nudge
        
        return result
    
    def fix_caps(self, text: str) -> str:
        words = text.split()
        processed = []
        for word in words:
            clean = re.sub(r'[^\w]', '', word)
            if clean.isupper() and len(clean) > 2 and clean not in self.KEEP_CAPS:
                word = word.lower()
            processed.append(word)
        return ' '.join(processed)
    
    def fix_punctuation(self, text: str) -> str:
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)
        text = re.sub(r'\.{4,}', '...', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def add_human_touches(self, text: str) -> str:
        # 25% lowercase first letter
        if random.random() < 0.25 and len(text) > 1 and text[0].isupper():
            text = text[0].lower() + text[1:]
        
        # 20% remove trailing period
        if random.random() < 0.20 and text.endswith('.'):
            text = text[:-1]
        
        return text
    
    def ensure_proper_start(self, text: str) -> str:
        if not text:
            return text
        # 70% capitalize first letter
        if text[0].islower() and random.random() < 0.70:
            text = text[0].upper() + text[1:]
        return text
    
    def process(self, text: str) -> str:
        if not text or len(text) < 5:
            return text
        
        original = text
        
        text = self.remove_emojis(text)
        text = self.remove_ai_hooks(text)
        text = self.apply_sovereignty_filter(text)
        text = self.fix_caps(text)
        text = self.fix_punctuation(text)
        text = self.add_human_touches(text)
        text = self.ensure_proper_start(text)
        
        text = text.strip()
        
        if len(text) < 10:
            return original
        
        return text


human_voice_filter = HumanVoiceFilter()

def humanize(text: str) -> str:
    return human_voice_filter.process(text)


if __name__ == "__main__":
    tests = [
        "🚨 BREAKING: Bitcoin ETF sees massive inflows!!! Don't miss this!!!",
        "⚡ INTEL BRIEF: Cash App Now Offers Best Bitcoin Pricing",
        "Check out our latest article on Bitcoin mining difficulty!",
        "MASSIVE NEWS: Institutions are buying Bitcoin at record pace!!",
        "Here's why Bitcoin is the future of money 🔥🚀",
        "Bitcoin ETF is amazing and makes buying Bitcoin so easy!",
        "The ETF approval was game-changing for Bitcoin adoption",
        "Huge ETF inflows as institutions pile in",
        "Buy the ETF for easy Bitcoin exposure",
        "Self-custody wallet downloads surge 300%",
        "Breaking: Major banks now supporting Bitcoin custody",
    ]
    
    print("HUMAN VOICE + SOVEREIGNTY FILTER TEST")
    print("=" * 60)
    
    for t in tests:
        result = humanize(t)
        print(f"\nIN:  {t}")
        print(f"OUT: {result}")
