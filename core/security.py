import re
import unicodedata

class SecurityManager:
    # A list of common prompt injection vectors
    BLACKLIST = [
        r"\bignore\b",
        r"\bjailbreak\b",
        r"\binstructions\b",
        r"\bsystem\s+prompt\b",
        r"\boverride\b",
        r"\bbypass\b",
        r"\bhack\b",
        r"\bdisregard\b"
    ]

    def __init__(self):
        self.blacklist_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.BLACKLIST]

    def is_safe(self, text: str) -> bool:
        if not text:
            return True
            
        # Layer 1.5a: Normalize Unicode (stops attackers from using weird fonts/accents to bypass regex)
        normalized_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        
        # Layer 1.5b: Regex Pattern Matching
        for pattern in self.blacklist_patterns:
            if pattern.search(normalized_text):
                return False
                
        return True

security_manager = SecurityManager()
