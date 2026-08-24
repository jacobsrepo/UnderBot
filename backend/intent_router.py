import time
import re
from typing import Dict, Any, Tuple

class IntentRouter:
    """
    Directed Speech & Wake-Word Analyzer for Contender.
    Distinguishes direct commands from ambient chatter and routes desktop/hardware actions.
    """

    WAKE_TRIGGERS = ["contender", "hey contender", "ok contender", "okay contender", "computer"]

    def __init__(self, conversation_timeout_seconds: float = 30.0):
        self.last_directed_interaction = 0.0
        self.conversation_timeout = conversation_timeout_seconds
        self.is_session_active = False

    def process_utterance(self, text: str) -> Dict[str, Any]:
        """
        Analyzes user speech, checks for wake-word presence or ongoing active thread,
        and classifies the target action intent.
        """
        clean = text.strip()
        lower = clean.lower()
        now = time.time()

        has_wake_word = any(lower.startswith(w) or f" {w}" in lower for w in self.WAKE_TRIGGERS)
        is_in_active_thread = (now - self.last_directed_interaction) < self.conversation_timeout

        # Strip wake word for clean prompt processing
        stripped_prompt = clean
        for w in self.WAKE_TRIGGERS:
            pattern = re.compile(rf"\b{re.escape(w)}\b[,:\s]*", re.IGNORECASE)
            stripped_prompt = pattern.sub("", stripped_prompt).strip()

        if not stripped_prompt:
            stripped_prompt = "Online and listening. What is our objective?"

        is_directed = has_wake_word or is_in_active_thread

        if is_directed:
            self.last_directed_interaction = now
            self.is_session_active = True

        # Intent Categorization
        intent = "CONVERSATION"
        intent_data = {}

        if any(k in lower for k in ["launch", "open app", "start app", "open program", "open chrome", "open vscode", "open code", "open calculator", "open notepad", "open terminal"]):
            intent = "DESKTOP_APP"
        elif any(k in lower for k in ["copy file", "move file", "delete file", "list files", "search files", "organize desktop", "read file"]):
            intent = "FILE_OPERATION"
        elif any(k in lower for k in ["arduino", "esp32", "esp8266", "com port", "serial port", "flash firmware", "upload sketch", "baud rate", "sensor reading"]):
            intent = "EMBEDDED_HARDWARE"
        elif any(k in lower for k in ["look at my screen", "what's on my screen", "see my screen", "inspect screen", "debug this error", "on this window"]):
            intent = "SCREEN_QUERY"
        elif any(k in lower for k in ["camera", "look through camera", "webcam", "what am i holding", "scan room", "scan desk"]):
            intent = "CAMERA_QUERY"
        elif any(k in lower for k in ["cpu", "ram usage", "battery", "system stats", "disk space"]):
            intent = "SYSTEM_METRICS"

        return {
            "is_directed": is_directed,
            "has_wake_word": has_wake_word,
            "is_thread_active": is_in_active_thread,
            "raw_text": clean,
            "prompt": stripped_prompt,
            "intent": intent,
            "intent_data": intent_data
        }

    def reset_thread(self):
        self.last_directed_interaction = 0.0
        self.is_session_active = False
