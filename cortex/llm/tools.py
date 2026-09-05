"""
Cortex Agent Tool Definitions with Host CLI & Active Facial Control
"""

CORTEX_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_hardware_connection",
            "description": "Check whether an Arduino, microcontroller, or USB serial device is physically plugged into the computer and online.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_serial_output",
            "description": "Read live serial COM port output and communication logs from the connected Arduino microcontroller (COM4). Call this whenever asked to show serial com output, read serial port, monitor serial output, or inspect incoming serial messages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lines": {
                        "type": "integer",
                        "description": "Number of recent lines to retrieve (default: 40)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_cli_command",
            "description": "Execute a native Windows PowerShell command on the host system. Use this to inspect files, query system metrics, run scripts, check directory contents, or execute tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The Windows PowerShell command line string (e.g. 'Get-ChildItem', 'Get-Date', 'Test-Path file.txt')"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional working directory path"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_facial_expression",
            "description": "Actively adjust your robot face's emotional expression, eye shape, and aura glow to reflect your internal thoughts, mood, and reactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mood": {
                        "type": "string",
                        "enum": ["curious", "analytical", "confident", "surprised", "skeptical", "pleased", "alert", "calm"],
                        "description": "Emotional mood"
                    },
                    "eye_shape": {
                        "type": "string",
                        "enum": ["normal", "wide", "narrow", "squint", "inquiring"],
                        "description": "Geometry of eyes"
                    },
                    "glow_color": {
                        "type": "string",
                        "description": "Hex color code for face glow (e.g. '#38bdf8' cyan, '#a855f7' purple, '#22c55e' green, '#ef4444' red alert, '#f59e0b' amber)"
                    },
                    "intensity": {
                        "type": "number",
                        "description": "Expression intensity from 0.0 to 1.0"
                    }
                },
                "required": ["mood"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "probe_and_identify_led_pin",
            "description": "Autonomously test Arduino pins one-by-one (D2 to D13, A0 to A5) while actively checking live optical camera feed to physically discover which pin illuminates a specific LED color (e.g. 'blue', 'green', 'red').",
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
            "description": "Inspect the physical optical webcam feed to visually check the scene or see if an external physical LED or component on a circuit board is visible or illuminated. Only call this when the camera is active and visual inspection is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus_target": {
                        "type": "string",
                        "description": "What specific item, component, or color to verify"
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
            "description": "Search the web, Google, DuckDuckGo, and read documentation or online web pages. Use this to look up latest news, technical documentation, hardware pinouts, or current information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_or_url": {
                        "type": "string",
                        "description": "The search keywords or direct URL to read"
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
            "name": "save_to_memory",
            "description": "Save a learned fact or hardware pin mapping into persistent long-term memory across restarts.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "build_and_flash_sketch",
            "description": "Write, compile, and physically flash NEW or custom Arduino sketch code to the connected microcontroller. Use this whenever asked to create, write, run, or flash a new script, test pins with code, or program the board. Writes code to a scratch sketch folder, compiles with arduino-cli, installs missing libraries, pauses serial, flashes over COM4, and resumes serial.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sketch_code": {
                        "type": "string",
                        "description": "The complete Arduino C++ code (including setup and loop functions)"
                    },
                    "sketch_name": {
                        "type": "string",
                        "description": "Descriptive folder/file name for the sketch (e.g. 'pin_test_sequence', 'rtc_sync')"
                    },
                    "port": {
                        "type": "string",
                        "description": "Optional COM port (e.g. 'COM4'). If omitted, uses active port."
                    },
                    "fqbn": {
                        "type": "string",
                        "description": "Board architecture FQBN (defaults to 'arduino:avr:nano')"
                    }
                },
                "required": ["sketch_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compile_and_upload_sketch",
            "description": "Compile and flash an ALREADY EXISTING Arduino sketch file (.ino) from disk. ONLY use if the user gives a specific existing file path. If creating or testing new code, use build_and_flash_sketch instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sketch_path": {
                        "type": "string",
                        "description": "The file path to the existing .ino sketch (e.g. 'C:\\Users\\Athul C S\\Documents\\binary_RTConly\\binary_RTConly.ino')"
                    },
                    "port": {
                        "type": "string",
                        "description": "Optional COM port (e.g. 'COM4'). If omitted, uses active port."
                    },
                    "fqbn": {
                        "type": "string",
                        "description": "Board architecture FQBN (defaults to 'arduino:avr:nano')"
                    }
                },
                "required": ["sketch_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_package_or_tool",
            "description": "Autonomously install a required Python package, Arduino library, or system utility using pip, arduino-cli, winget, or npm without asking repetitive permission.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_type": {
                        "type": "string",
                        "enum": ["python", "arduino", "winget", "npm"],
                        "description": "The package manager / type of dependency"
                    },
                    "package_name": {
                        "type": "string",
                        "description": "The name of the package or library (e.g. 'pyserial', 'RTClib', 'ffmpeg')"
                    }
                },
                "required": ["package_type", "package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_display_view",
            "description": "Explicitly switch or dismiss the active UI screen on the stage ('none' to close screens and return to the animated robot face avatar, 'browser' to show the web reader, 'camera' for camera inspection, or 'dual' for split screen).",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["none", "browser", "camera", "dual"],
                        "description": "The target display mode"
                    }
                },
                "required": ["mode"]
            }
        }
    }
]
