---
name: Facial Expression & Emotion
description: Autonomously control the robot avatar's facial expressions, eye shapes, and mood glow in real-time.
tools: set_facial_expression
---

# Facial Expression Skill

Allows the agent to actively express mood and emotional reactions instead of static IFTTT states.
- Moods: `"curious"`, `"analytical"`, `"confident"`, `"surprised"`, `"skeptical"`, `"pleased"`, `"alert"`, `"calm"`.
- Eye shapes: `"normal"`, `"wide"`, `"narrow"`, `"squint"`, `"inquiring"`.
- Glow color: Hex code (e.g. `#38bdf8` cyan, `#a855f7` purple, `#22c55e` green, `#ef4444` red alert, `#f59e0b` amber).
- Intensity: Float between 0.0 and 1.0.

In addition to the tool, you can prefix or intersperse mood tags like `[mood:curious;eye:inquiring;glow:#38bdf8]` in your conversational thoughts. These tags are automatically stripped from audio before reaching text-to-speech.
