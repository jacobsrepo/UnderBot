import io
import os
import tempfile
from typing import Optional, Dict
from faster_whisper import WhisperModel

class STTEngine:
    """
    Faster-Whisper Speech-To-Text pipeline with low-latency local inference.
    """
    def __init__(self, model_size: str = "base.en", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model: Optional[WhisperModel] = None
        self._init_model()

    def _init_model(self):
        print(f"[STTEngine] Initializing Faster-Whisper ({self.model_size}, {self.device}, {self.compute_type})...")
        try:
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            print("[STTEngine] Faster-Whisper loaded successfully.")
        except Exception as e:
            print(f"[STTEngine] Warning: Faster-Whisper initialization error: {e}")
            if self.device != "cpu":
                print("[STTEngine] Retrying with CPU int8 fallback...")
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

    def transcribe_audio_bytes(self, audio_bytes: bytes, file_format: str = "wav") -> Dict:
        """
        Transcribes raw audio bytes into text.
        """
        if not self.model:
            return {"text": "", "error": "STT model not initialized"}

        if not audio_bytes or len(audio_bytes) < 100:
            return {"text": "", "segments": []}

        # Write to a temporary file for Whisper decoding
        with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, info = self.model.transcribe(
                tmp_path,
                beam_size=5,
                language="en",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            full_text = []
            segment_list = []
            for seg in segments:
                text_clean = seg.text.strip()
                if text_clean:
                    full_text.append(text_clean)
                    segment_list.append({
                        "start": seg.start,
                        "end": seg.end,
                        "text": text_clean
                    })

            result_text = " ".join(full_text).strip()
            return {
                "text": result_text,
                "language": info.language,
                "duration": info.duration,
                "segments": segment_list
            }
        except Exception as e:
            print(f"[STTEngine] Transcription error: {e}")
            return {"text": "", "error": str(e)}
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
