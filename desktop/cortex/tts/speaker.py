"""
Cortex Neural Male Voice Synthesizer
Uses Edge-TTS (en-US-ChristopherNeural) to generate rich, authoritative male voice audio.
"""

import os
import base64
import asyncio
import tempfile
from typing import Optional


class VoiceSpeaker:
    def __init__(self, voice: str = "en-US-ChristopherNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def synthesize_speech(self, text: str) -> Optional[str]:
        """
        Synthesize text into MP3 audio and return as base64 Data URI.
        """
        clean_text = text.strip()
        if not clean_text:
            return None

        # Remove raw markdown symbols or URLs for cleaner pronunciation
        spoken_text = self._sanitize_for_speech(clean_text)
        if not spoken_text:
            return None

        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=spoken_text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )

            # Accumulate audio chunks in memory
            audio_bytes = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes.extend(chunk["data"])

            if audio_bytes:
                b64 = base64.b64encode(audio_bytes).decode('ascii')
                return f"data:audio/mp3;base64,{b64}"

        except Exception as e:
            print(f"[VoiceSpeaker] Edge-TTS error: {e}")

        return None

    def _sanitize_for_speech(self, text: str) -> str:
        """Strip markdown syntax, raw URLs, and formatting characters before TTS."""
        import re
        # Remove images ![](url)
        t = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # Convert links [label](url) to just label
        t = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', t)
        # Remove raw URLs
        t = re.sub(r'https?://\S+', '', t)
        # Remove bold, italics, code markers
        t = re.sub(r'[*_`#~]', '', t)
        # Clean multiple spaces and newlines
        t = re.sub(r'\s+', ' ', t).strip()
        return t
