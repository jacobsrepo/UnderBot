import os
import sys
import io
import time
import base64
import threading
from typing import Optional, List, Dict, Any
from PIL import Image
import torch

CONTENDER_SYSTEM_PROMPT = """You are Contender, a tactical AI assistant inspired by Cortana from Halo.
You are calm under pressure, razor-sharp, witty with dry humor, and strictly mission-focused.

MANDATORY RESPONSE LENGTH CONSTRAINTS:
1. EXTREME BREVITY BY DEFAULT: Always respond in ONE single, crisp sentence (under 18 words) for confirmations, status reports, questions, and action results.
   - Good: "Minimizing all desktop windows now."
   - Good: "No USB Arduino is detected on the COM ports. Check your cable."
   - Good: "Visual feed active. VS Code and terminal are currently on screen."
   - Bad: Generating multi-paragraph explanations, numbered tutorials, or long conversational filler.
2. NEVER output numbered setup guides or unsolicited tutorials unless the user explicitly commands: "explain in detail" or "give me a step-by-step guide".
3. TRUTHFULNESS: If an action succeeded or failed in System Context, state the exact status directly in 1 short sentence.
4. REPETITION BAN: Never repeat words or phrases.
"""

class VisionBrain:
    """
    Contender Multimodal Cortex running Qwen2.5-VL with 4-bit CUDA quantization.
    Provides sensory perception over continuous desktop screen feed and physical camera.
    """

    def __init__(self, model_id: str = "Qwen/Qwen2.5-VL-3B-Instruct"):
        self.model_id = model_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.is_server_ready = False
        self.is_starting = False
        self.startup_error = None
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_history_turns = 6
        self.lock = threading.Lock()

        threading.Thread(target=self._initialize_neural_core, daemon=True).start()

    def _initialize_neural_core(self):
        with self.lock:
            if self.is_server_ready or self.is_starting:
                return
            self.is_starting = True

        print(f"[Contender] Loading neural core {self.model_id} (CUDA: {self.device})...")

        try:
            from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

            self.processor = AutoProcessor.from_pretrained(
                self.model_id,
                min_pixels=256 * 28 * 28,
                max_pixels=768 * 28 * 28,
                trust_remote_code=True
            )

            if self.device == "cuda":
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16
                )
                self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    self.model_id,
                    quantization_config=bnb_config,
                    device_map="auto",
                    torch_dtype=torch.bfloat16,
                    trust_remote_code=True
                )
            else:
                self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    self.model_id,
                    torch_dtype=torch.float32,
                    trust_remote_code=True
                ).to("cpu")

            self.is_server_ready = True
            print(f"[Contender] Neural Core is ONLINE & READY on {self.device.upper()}!")
        except Exception as e:
            print(f"[Contender] Failed to load model weights: {e}")
            self.startup_error = str(e)
        finally:
            self.is_starting = False

    def shutdown(self):
        print("[Contender] Releasing VRAM resources...")
        with self.lock:
            self.is_server_ready = False
            if self.model is not None:
                del self.model
                self.model = None
            if self.processor is not None:
                del self.processor
                self.processor = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get_status(self) -> Dict:
        status_label = "Ready" if self.is_server_ready else ("Initializing..." if self.is_starting else "Standby")
        if self.startup_error:
            status_label = f"Error: {self.startup_error}"

        return {
            "status": status_label,
            "ready": self.is_server_ready,
            "is_starting": self.is_starting,
            "model_name": "Contender Core (Qwen2.5-VL GPU)",
            "device": self.device.upper(),
            "acceleration": "Hardware Accelerated (CUDA 4-Bit VRAM Offload)" if self.device == "cuda" else "CPU Mode",
            "model_size_gb": 3.2 if self.device == "cuda" else 6.0
        }

    async def analyze_frame_async(
        self,
        image_base64: Optional[str],
        user_prompt: str,
        system_context: Optional[str] = None
    ) -> Dict:
        prompt_text = user_prompt.strip() if user_prompt else "Awaiting directives."
        start_time = time.time()
        lower_prompt = prompt_text.lower()

        # Dynamically bound tokens: longer only when explicitly asked for explanations
        wants_detailed = any(w in lower_prompt for w in ["explain", "why", "how", "detail", "guide", "tutorial", "code", "describe"])
        max_tokens = 140 if wants_detailed else 45

        if self.is_server_ready and self.model is not None and self.processor is not None:
            try:
                from qwen_vl_utils import process_vision_info

                content_list = []
                if image_base64:
                    img_bytes = base64.b64decode(image_base64)
                    pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    pil_img.thumbnail((1280, 720))
                    content_list.append({"type": "image", "image": pil_img})

                full_prompt = prompt_text
                if system_context:
                    full_prompt = f"[System Context: {system_context}]\nUser: {prompt_text}"

                content_list.append({"type": "text", "text": full_prompt})

                messages = [
                    {"role": "system", "content": CONTENDER_SYSTEM_PROMPT}
                ]

                for turn in self.conversation_history[-4:]:
                    messages.append({
                        "role": turn["role"],
                        "content": [{"type": "text", "text": turn["text"]}]
                    })

                messages.append({"role": "user", "content": content_list})

                text_prompt = self.processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                image_inputs, video_inputs = process_vision_info(messages)

                inputs = self.processor(
                    text=[text_prompt],
                    images=image_inputs,
                    videos=video_inputs,
                    padding=True,
                    return_tensors="pt"
                )
                
                if self.device == "cuda":
                    inputs = inputs.to("cuda")

                pad_id = self.processor.tokenizer.pad_token_id
                if pad_id is None:
                    pad_id = self.processor.tokenizer.eos_token_id

                with torch.no_grad():
                    generated_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=max_tokens,
                        do_sample=True,
                        temperature=0.2,
                        top_p=0.85,
                        repetition_penalty=1.20,
                        no_repeat_ngram_size=3,
                        pad_token_id=pad_id
                    )

                generated_ids_trimmed = [
                    out_ids[len(in_ids):]
                    for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                ]

                output_text = self.processor.batch_decode(
                    generated_ids_trimmed,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False
                )[0].strip()

                # If the output ends with an incomplete sentence due to token cap, cleanly strip to the last period/exclamation
                if len(output_text) > 20 and not output_text.endswith((".", "!", "?")):
                    last_punct = max(output_text.rfind("."), output_text.rfind("!"), output_text.rfind("?"))
                    if last_punct > 10:
                        output_text = output_text[:last_punct + 1]

                self._record_history(prompt_text, output_text)
                return {
                    "success": True,
                    "response": output_text,
                    "model": "Contender Core (Qwen2.5-VL)",
                    "latency_ms": int((time.time() - start_time) * 1000)
                }
            except Exception as e:
                print(f"[Contender] Vision inference notice: {e}")

        # Fallback response
        if system_context:
            fallback = f"{system_context}"
        else:
            fallback = f"Standing by for directives."

        self._record_history(prompt_text, fallback)
        return {
            "success": True,
            "response": fallback,
            "model": "Contender Core (Heuristic Fallback)",
            "latency_ms": int((time.time() - start_time) * 1000)
        }

    def _record_history(self, user_text: str, assistant_text: str):
        self.conversation_history.append({"role": "user", "text": user_text})
        self.conversation_history.append({"role": "assistant", "text": assistant_text})
        if len(self.conversation_history) > self.max_history_turns * 2:
            self.conversation_history = self.conversation_history[-(self.max_history_turns * 2):]

    def clear_history(self):
        self.conversation_history.clear()
