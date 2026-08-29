import os
import re
import io
import asyncio
import base64
from typing import Optional, Dict, List
try:
    import edge_tts
except ImportError:
    edge_tts = None

class TTSEngine:
    """
    High-Performance Neural Text-to-Speech engine.
    Specialized for natural, authoritative, and responsive male voices.
    """
    AVAILABLE_VOICES: Dict[str, Dict[str, str]] = {
        "guy": {
            "id": "en-US-GuyNeural",
            "name": "Guy (US - Crisp & Authoritative)",
            "gender": "Male",
            "recommended": True
        },
        "christopher": {
            "id": "en-US-ChristopherNeural",
            "name": "Christopher (US - Calm & Professional)",
            "gender": "Male",
            "recommended": False
        },
        "eric": {
            "id": "en-US-EricNeural",
            "name": "Eric (US - Energetic & Dynamic)",
            "gender": "Male",
            "recommended": False
        },
        "ryan": {
            "id": "en-GB-RyanNeural",
            "name": "Ryan (British - Refined & Tech-Focused)",
            "gender": "Male",
            "recommended": False
        },
        "william": {
            "id": "en-AU-WilliamNeural",
            "name": "William (Australian - Friendly & Clear)",
            "gender": "Male",
            "recommended": False
        }
    }

    def __init__(self, default_voice_key: str = "guy"):
        self.default_voice_key = default_voice_key if default_voice_key in self.AVAILABLE_VOICES else "guy"
        self.current_voice_id = self.AVAILABLE_VOICES[self.default_voice_key]["id"]
        self.rate = "+0%"
        self.pitch = "+0Hz"

    def set_voice(self, voice_key: str):
        if voice_key in self.AVAILABLE_VOICES:
            self.default_voice_key = voice_key
            self.current_voice_id = self.AVAILABLE_VOICES[voice_key]["id"]
            print(f"[TTSEngine] Voice changed to: {self.AVAILABLE_VOICES[voice_key]['name']}")
            return True
        return False

    def clean_text_for_speech(self, text: str) -> str:
        """Strip markdown markers, code blocks, and URLs so speech sounds clean and natural."""
        if not text:
            return ""
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        # Remove inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Remove markdown bold/italics
        text = re.sub(r'[*_]{1,3}([^*_]+)[*_]{1,3}', r'\1', text)
        # Remove markdown headers
        text = re.sub(r'#+\s*', '', text)
        # Remove markdown links, keep text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def synthesize_async(self, text: str, voice_key: Optional[str] = None) -> bytes:
        clean_text = self.clean_text_for_speech(text)
        if not clean_text or not edge_tts:
            return b""

        voice_id = self.AVAILABLE_VOICES.get(voice_key, {}).get("id", self.current_voice_id)
        communicate = edge_tts.Communicate(clean_text, voice_id, rate=self.rate, pitch=self.pitch)
        
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
                
        return audio_stream.getvalue()

    def synthesize_sync(self, text: str, voice_key: Optional[str] = None) -> bytes:
        return asyncio.run(self.synthesize_async(text, voice_key))

    async def synthesize_base64(self, text: str, voice_key: Optional[str] = None) -> Dict:
        audio_bytes = await self.synthesize_async(text, voice_key)
        if not audio_bytes:
            return {"audio_base64": "", "format": "audio/mp3", "length": 0}
        
        b64 = base64.b64encode(audio_bytes).decode('utf-8')
        return {
            "audio_base64": b64,
            "format": "audio/mp3",
            "length": len(audio_bytes),
            "voice": voice_key or self.default_voice_key
        }

    def list_voices(self) -> List[Dict]:
        return [
            {
                "key": k,
                "id": v["id"],
                "name": v["name"],
                "gender": v["gender"],
                "selected": k == self.default_voice_key
            }
            for k, v in self.AVAILABLE_VOICES.items()
        ]
