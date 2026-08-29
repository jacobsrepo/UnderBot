"""
Cortex Agent Tool Definitions for Ollama Function Calling
"""

CORTEX_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "probe_and_identify_led_pin",
            "description": "Autonomously test all Arduino pins one-by-one (D2 to D13, A0 to A5) while actively monitoring the live camera feed to physically discover which pin illuminates a specific LED color (e.g. 'blue', 'green', 'red'). Use this whenever asked to find or identify which pin controls an LED.",
            "parameters": {
                "type": "object",
                "properties": {
                    "color": {
                        "type": "string",
                        "enum": ["blue", "green", "red"],
                        "description": "The LED color to search for and detect with the camera"
                    }
                },
                "required": ["color"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_arduino_pin",
            "description": "Control a pin on the connected Arduino Nano (D2 to D13, or A0 to A5 / pins 2 to 19). State 1 is HIGH (ON), state 0 is LOW (OFF).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pin": {
                        "type": "string",
                        "description": "The pin number or name (e.g. 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'A0', 'A1', 'A2', 'A3', 'A4', 'A5')"
                    },
                    "state": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "1 for HIGH (turn on), 0 for LOW (turn off)"
                    }
                },
                "required": ["pin", "state"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_all_arduino_pins",
            "description": "Set ALL pins (D2-D13 and A0-A5) on the Arduino to HIGH (1) or LOW (0). Use when asked to turn off all LEDs or turn on all LEDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "0 for LOW (turn all off), 1 for HIGH (turn all on)"
                    }
                },
                "required": ["state"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_camera",
            "description": "Capture the real webcam video frame and perform optical emission analysis to check what is physically visible and which LEDs (Red, Green, Blue) are physically illuminated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus_target": {
                        "type": "string",
                        "description": "What specific item or color to verify (e.g. 'Blue LEDs', 'Hours column', 'circuit board overview')"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pin_states",
            "description": "Read the current HIGH/LOW state of all digital pins on the Arduino Nano.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_or_browse_web",
            "description": "Search the live web or retrieve technical documentation, datasheets, pinouts, and circuit schematics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_or_url": {
                        "type": "string",
                        "description": "The search keywords or direct URL to surf"
                    }
                },
                "required": ["query_or_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_weather",
            "description": "Fetch real-time weather, temperature, and atmospheric conditions for a given city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city or locality name"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_viewport_mode",
            "description": "Change the visual display mode of the user interface.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["camera", "browser", "dual", "none"],
                        "description": "The target viewport layout"
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_memory",
            "description": "Save a learned fact, hardware pin mapping, or user preference into persistent long-term memory across restarts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category (e.g. 'pin_mapping', 'user_preference', 'notes')"
                    },
                    "key": {
                        "type": "string",
                        "description": "Identifier key"
                    },
                    "value": {
                        "type": "string",
                        "description": "The information to remember"
                    }
                },
                "required": ["category", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_from_memory",
            "description": "Search and retrieve previously saved facts or hardware mappings from persistent long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword or topic"
                    }
                },
                "required": ["query"]
            }
        }
    }
]
