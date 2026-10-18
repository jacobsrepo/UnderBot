---
name: Vision Inspection
description: Instant optical light emission measurement and scene description from the asynchronous VisualSceneBuffer.
tools: inspect_camera
---

# Vision Inspection Skill

Use `inspect_camera` to read physical reality from the camera stream.
- Zero latency: reads directly from the debounced in-memory `VisualSceneBuffer`.
- Reports actual physical light emitted (Blue, Green, Red pixels) and verifies whether LEDs are physically ON or OFF.
- Never state an LED is ON unless confirmed by optical emission metrics.
