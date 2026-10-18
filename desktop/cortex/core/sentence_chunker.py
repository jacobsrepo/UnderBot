import re
from typing import List


class SentenceChunker:
    """Accurately segments token streams without splitting numbers, paths, or abbreviations."""

    SPLIT_REGEX = re.compile(
        r'(?<!\be\.g)(?<!\bi\.e)(?<!\bdr)(?<!\bmr)(?<!\bvs)(?<!\b\d)(?<=[.?!])\s+(?=[A-Z0-9])|(?:\n\n+)'
    )

    def __init__(self, min_char_threshold: int = 5):
        self.buffer = ""
        self.min_char_threshold = min_char_threshold

    def append(self, token: str) -> List[str]:
        self.buffer += token
        extracted = []

        segments = self.SPLIT_REGEX.split(self.buffer)
        if len(segments) > 1:
            accumulated = ""
            for s in segments[:-1]:
                accumulated += (" " + s.strip() if accumulated else s.strip())
                if len(accumulated) >= self.min_char_threshold:
                    extracted.append(accumulated)
                    accumulated = ""
            if accumulated:
                self.buffer = accumulated + " " + segments[-1]
            else:
                self.buffer = segments[-1]
            
        return extracted

    def flush(self) -> List[str]:
        clean = self.buffer.strip()
        self.buffer = ""
        return [clean] if clean else []
