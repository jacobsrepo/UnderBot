import io
import os
import tempfile
from typing import Optional, Dict
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

class STTEngine:
    """
    High-accuracy Speech-To-Text engine using Faster-Whisper small.en.
    Optimized for low-latency conversational speech recognition.
    """
    def __init__(self, model_size: str = "small.en", device: Optional[str] = None, compute_type: Optional[str] = None):
        self.model_size = model_size
        
        # Auto-detect CUDA capability if not explicitly passed
        if device is None:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                self.device = "cpu"
        else:
            self.device = device

        if compute_type is None:
            self.compute_type = "float16" if self.device == "cuda" else "int8"
        else:
            self.compute_type = compute_type

        self.model: Optional[WhisperModel] = None
        self._init_model()

    def _init_model(self):
        if not WhisperModel:
            print("[STTEngine] faster-whisper package not installed. Speech-to-text standing by.")
            return

        print(f"[STTEngine] Initializing Faster-Whisper ({self.model_size}, {self.device}, {self.compute_type})...")
        try:
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            print(f"[STTEngine] Faster-Whisper ({self.model_size}) loaded on {self.device}.")
        except Exception as e:
            print(f"[STTEngine] Warning: Failed loading on {self.device} ({e}). Falling back to cpu int8 base.en...")
            try:
                self.model_size = "base.en"
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel("base.en", device="cpu", compute_type="int8")
                print("[STTEngine] Faster-Whisper (base.en) loaded on CPU.")
            except Exception as fallback_e:
                print(f"[STTEngine] Critical STT error: {fallback_e}")

    def transcribe_audio_bytes(self, audio_bytes: bytes, file_format: str = "webm") -> Dict:
        """
        Transcribes raw audio bytes into text with high sensitivity.
        """
        if not self.model:
            return {"text": "", "error": "STT model not initialized"}

        if not audio_bytes or len(audio_bytes) < 200:
            return {"text": "", "segments": []}

        with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Transcribe with zero temperature and gentle VAD to never drop short phrases
            segments, info = self.model.transcribe(
                tmp_path,
                beam_size=5,
                language="en",
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=False
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
                "language": info.language if hasattr(info, "language") else "en",
                "duration": info.duration if hasattr(info, "duration") else 0,
                "segments": segment_list
            }
        except Exception as e:
            print(f"[STTEngine] Transcription notice: {e}")
            return {"text": "", "error": str(e)}
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
