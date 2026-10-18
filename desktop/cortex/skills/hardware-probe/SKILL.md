---
name: Hardware Probe & Control
description: Direct 16-pin control of Arduino Nano on COM4 (pins D2-D13, A0-A5) and automated closed-loop optical pin discovery.
tools: probe_and_identify_led_pin, set_arduino_pin, set_all_arduino_pins, get_pin_states
---

# Hardware Probe Skill

Controls physical pins on the connected Arduino Nano without blocking the async event loop.
- To discover which pin controls an LED (e.g. blue or green), call `probe_and_identify_led_pin(color)`. This will test pins sequentially in both Active-HIGH and Active-LOW polarities while measuring optical emission changes.
- To actuate specific pins, call `set_arduino_pin(pin, state)`.
- Never guess an unverified pin.
