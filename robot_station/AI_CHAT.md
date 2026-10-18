# Raspberry Pi Qwen chat

The UnderBot Controls panel sends text on `/station/ai/request` and receives
correlated replies on `/station/ai/response` (both `std_msgs/msg/String` with JSON).
The station gateway calls the Pi's existing Ollama `qwen2.5:1.5b` model.
It runs inference on a worker thread so ROS heartbeats and the command watchdog
continue while a reply is generated. One request can run at a time.

On this Windows station, launch **D:\Robotics\Start UnderBot EMEET Live.cmd**.
The base-link helper opens a loopback-only SSH forward from Windows port 11435
to the Pi's Ollama port 11434. No public Ollama listener or cloud API key is needed.
The Pi, Tailscale, Ollama and SSH link must be running. Open **UnderBot EMEET Live**,
scroll the **UnderBot Controls** panel to **Robot AI chat**, type and press Send.
The first answer may take longer while the model loads.

For a manual station launch, add `--ai-url http://127.0.0.1:11435`
to `start.py`; on the Pi itself use `--ai-url http://127.0.0.1:11434`.
The default model can be overridden with `--ai-model` for another installed model.
Without `--ai-url`, chat remains unconfigured. The gateway never downloads models.

Replies are limited to 192 generated tokens and a 2048-token context. The backend
waits up to 150 seconds; the panel waits 180 seconds. Questions are independent:
the visible transcript is not sent back as conversation memory or saved to PostgreSQL.
Before each question a fixed helper queries active enrolled names in a read-only
PostgreSQL transaction. Credentials stay in the private config. No face embeddings,
photos or raw observation records are included. Identity questions such as "Who is
Sam?" use deterministic name matching; unknown, ambiguous and unavailable results
are explicit. Other questions send this fresh memory context to Qwen. Its generated
answers can still be mistaken. Only 100 names are included; truncation is labeled.
This is name retrieval, not live face recognition or a biography database.

The launcher passes --memory-python (perception Python with psycopg) and
--memory-config (authoritative base.json). Chat memory therefore depends on this
PC's PostgreSQL. For a Pi-local deployment use its Python with psycopg and robot.json;
the replica must have synchronized within seven days. This launcher does not
automatically fall back to the Pi database when the base database is unavailable.

Camera awareness now subscribes to /perception/emeet/objects and publishes its
bounded snapshot on /station/ai/world_state. The source is the PC EMEET camera.
Each perception message includes capture time and recognition health. Current
visibility expires after three seconds using both capture and monotonic receipt
age. Names require two consecutive distinct frames, healthy recognition, detection
confidence >= 0.35 and accepted face similarity >= 0.5. The perception matcher also
enforces its configured runner-up margin. Similarity is not a calibrated probability.
Replayed, future and stale frames do not renew visibility; a new empty frame clears
current identities immediately. These checks do not provide face anti-spoofing.

"Can you see Sam?", "Who can you see?" and "When did you last see Sam?" use
deterministic evidence-based responses, avoiding LLM latency for visibility checks.
Enrollment is rechecked against current PostgreSQL names before naming someone.
Up to ten minutes of confirmed sightings (100 names maximum) are retained in RAM
since gateway startup; last-seen history is not restored from PostgreSQL.
Unknown faces remain generic people. Camera outages are unknown visibility, not
proof that someone is absent. No room/map position can be derived from this feed.
Other chat questions receive a timestamped world-state snapshot; generated answers
remain model outputs, not guaranteed facts or live tracking.

No raw images or microphone audio are sent to Qwen.
General chat cannot issue robot commands or run arbitrary tools. In navigation
simulation mode the separate navigation_language.py requests schema-constrained
Qwen proposals for named goals, relative turns and distance movements. Python
validates them before the PC simulator executes them. Physical execution remains
disabled. /station/nav/events supplies correlated execution feedback to chat.
See ../navigation/README.md for supported examples and cancellation behavior.
The existing Pi VLA node is independent
and was not modified. Moondream is installed on the Pi but is not connected here.

The station's room map, IMU and movement remain synthetic demo data. Camera and
audio publishers are independent of this chat integration.

The supported "Bring PERSON the OBJECT" request uses a deterministic seven-step
task template, with enrolled-name resolution and explicit blockers. This is not a
learned general planner. Chat shows the proposal and /station/ai/plan publishes a
correlated JSON record with executable=false. No executor consumes it. Unrelated
questions publish plan=null. Other physical requests are discussed by Qwen only.

Next integration stages: speech-to-text -> existing AI request topic; perception
and localization -> timestamped validated world state; task executive -> Nav2 ROS
actions with result/cancellation handling; base controller -> ESP32 velocity control.
Manipulation is deferred. A VLA policy is a separate later option requiring suitable
robot data and validation, not a replacement for memory retrieval or Nav2.

If chat reports unavailable, check Pi connectivity, `systemctl status ollama`,
the base-link log and `http://127.0.0.1:11435/api/tags`, then retry.
No prompts are written to the station application logs.

Validation in a sourced ROS environment:
`python -m unittest test_gateway test_ai_backend -v`.
