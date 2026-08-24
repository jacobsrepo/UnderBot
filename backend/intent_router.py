import time
import re
from typing import Dict, Any, Tuple

class IntentRouter:
    """
    Directed Speech, Wake-Word, and Sensory Routing Analyzer for Contender.
    Intelligently routes between Continuous Screen perception and Physical Camera vision
    and detects conversational speech triggers.
    """

    WAKE_TRIGGERS = ["contender", "hey contender", "ok contender", "okay contender", "computer"]

    # Physical environment / camera keywords
    CAMERA_TRIGGERS = [
        "camera", "webcam", "look at me", "see me", "holding", "in my hand",
        "on my desk", "my face", "my shirt", "this object", "physical",
        "room", "surroundings", "in front of me", "what is this in my hand",
        "look at this thing", "inspect this part", "look through camera", "my hands"
    ]

    # Digital / Desktop screen keywords
    SCREEN_TRIGGERS = [
        "screen", "on my screen", "desktop", "code", "error", "terminal",
        "browser", "window", "document", "tab", "vs code", "vscode",
        "this file", "website", "program", "app", "read this", "debug this",
        "what does this say", "summarize this", "my display", "look at this code"
    ]

    def __init__(self, conversation_timeout_seconds: float = 35.0):
        self.last_directed_interaction = 0.0
        self.conversation_timeout = conversation_timeout_seconds
        self.is_session_active = False

    def process_utterance(self, text: str) -> Dict[str, Any]:
        """
        Analyzes user speech, checks for wake-word presence or ongoing active thread,
        classifies intent, and automatically selects the optimal sensory source (Screen vs Camera).
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

        # ==================== SENSORY SOURCE ARBITRATION ====================
        # Automatically choose between Screen and Camera based on semantic context
        vision_source = "screen"  # Screen is default for desktop assistant

        has_cam_keywords = any(k in lower for k in self.CAMERA_TRIGGERS)
        has_screen_keywords = any(k in lower for k in self.SCREEN_TRIGGERS)

        if has_cam_keywords and not has_screen_keywords:
            vision_source = "camera"
        elif has_screen_keywords:
            vision_source = "screen"

        # ==================== INTENT CATEGORIZATION ====================
        intent = "CONVERSATION"

        if any(k in lower for k in ["launch", "open app", "start app", "open program", "open chrome", "open vscode", "open code", "open calculator", "open notepad", "open terminal", "open spotify"]):
            intent = "DESKTOP_APP"
        elif any(k in lower for k in ["copy file", "move file", "delete file", "list files", "search files", "organize desktop", "read file"]):
            intent = "FILE_OPERATION"
        elif any(k in lower for k in ["arduino", "esp32", "esp8266", "com port", "serial port", "flash firmware", "upload sketch", "baud rate", "sensor reading", "relay"]):
            intent = "EMBEDDED_HARDWARE"
        elif vision_source == "camera":
            intent = "CAMERA_QUERY"
        elif vision_source == "screen" and (has_screen_keywords or any(k in lower for k in ["look", "see", "what is", "explain", "summarize", "inspect", "debug"])):
            intent = "SCREEN_QUERY"
        elif any(k in lower for k in ["cpu", "ram usage", "battery", "system stats", "disk space"]):
            intent = "SYSTEM_METRICS"

        return {
            "is_directed": is_directed,
            "has_wake_word": has_wake_word,
            "is_thread_active": is_in_active_thread,
            "raw_text": clean,
            "prompt": stripped_prompt,
            "intent": intent,
            "vision_source": vision_source
        }

    def reset_thread(self):
        self.last_directed_interaction = 0.0
        self.is_session_active = False
