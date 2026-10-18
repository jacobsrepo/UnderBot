import os
import sys
import io
import time
import base64
from typing import Dict, Any, Optional

try:
    from rapidocr_onnxruntime import RapidOCR
    _OCR = RapidOCR()
except Exception:
    _OCR = None

class VisionEngine:
    """
    Secondary Engine: On-Demand Vision & Screen Ingestion.
    Provides fast local RapidOCR screen text extraction and isolated on-demand visual queries.
    Never runs continuous uncompressed frame loops.
    """

    def __init__(self):
        self.is_ready = True

    def capture_screen_context(self) -> Dict[str, Any]:
        """
        Captures the active screen, runs fast local OCR, and returns the structured text buffer.
        """
        if not _OCR:
            return {"success": False, "text": "", "line_count": 0}

        try:
            import numpy as np
            from PIL import ImageGrab

            screenshot = ImageGrab.grab()
            img_np = np.array(screenshot)
            img_bgr = img_np[:, :, ::-1]

            results, _ = _OCR(img_bgr)
            lines = []
            if results:
                for line in results:
                    text = line[1]
                    conf = line[2]
                    if conf > 0.4:
                        lines.append(text)

            full_text = "\n".join(lines)
            return {
                "success": True,
                "text": full_text,
                "line_count": len(lines),
                "preview": full_text[:300]
            }
        except Exception as e:
            print(f"[VisionEngine] Screen OCR notice: {e}")
            return {"success": False, "text": "", "line_count": 0}

    def inspect_visual_target(self, image_base64: Optional[str], prompt: str = "") -> str:
        """
        Executes an isolated, on-demand visual inspection of a captured frame/camera image.
        Returns a concise text summary back to the Coder brain.
        """
        if not image_base64:
            return "Visual context empty: No image frame provided."

        try:
            import numpy as np
            from PIL import Image

            img_bytes = base64.b64decode(image_base64)
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            img_np = np.array(pil_img)
            
            # Extract any visible text labels or markers in the camera/frame
            if _OCR:
                img_bgr = img_np[:, :, ::-1]
                results, _ = _OCR(img_bgr)
                detected_text = [r[1] for r in results if r[2] > 0.45] if results else []
                if detected_text:
                    return f"Visual inspection detected text/labels: {', '.join(detected_text[:5])}."

            w, h = pil_img.size
            return f"Visual target captured ({w}x{h} resolution). Image active and verified."
        except Exception as e:
            return f"Visual inspection error: {e}"
