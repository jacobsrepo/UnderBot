# PostgreSQL memory and personal recognition

## Implemented architecture

Pi: local PostgreSQL gallery + recent observations; local OpenCV YuNet/SFace
recognition alongside YOLO detection/pose. PC: authoritative enrollment gallery
and long-term observations in a dedicated PostgreSQL instance on loopback port 55432.
The PC edge-test database exercises the Pi role before hardware deployment.
No SQLite. Embeddings are PostgreSQL real[128] values; matching runs locally in
NumPy. pgvector is optional and is not installed by this implementation.

Only metadata (time, category, tentative identity and similarity) is stored. No
image/audio recordings or live face embeddings are saved as observations. Enrollment
images are read only on explicit command. Private credentials, data and downloaded
model weights are excluded from Git. Windows data resides under perception/.private
with a restricted user ACL. This is access control, not database encryption at rest.

## Windows operation

From perception/ with Pixi:

```powershell
pixi run python -m memory.bootstrap_windows
pixi run python -m memory.download_models
pixi run python -m memory.cli --config .private/base.json status
pixi run start --memory-config .private/edge-test.json
```

Stop an existing camera pipeline with `pixi run stop` before starting another.
The supervisor starts camera, YOLO/face recognition and periodic database sync.
Audio remains a separate opt-in process. Foxglove retains its annotated-image topic;
recognized names overlay faces. Object result JSON adds an optional `identity`
(person_id/name/similarity); category remains person when identity is absent.
`/perception/emeet/status` contains recognition_state. Similarity is not a calibrated
probability. Missing face models, database failures and an empty gallery preserve
YOLO category detection. Recognition work counts toward the existing 2-second
freshness limit; slow Pi hardware may require a smaller model/lower resolution.

## Enroll and remove people

```powershell
pixi run python -m memory.cli --config .private/base.json enroll --consent --name "Sam Jacob" --images "D:\private-photos\sam.jpg"
# Add further examples to the same person using the returned UUID:
pixi run python -m memory.cli --config .private/base.json enroll --consent --name "Sam Jacob" --person-id PERSON_UUID --images "D:\private-photos\sam-side.jpg"
pixi run python -m memory.cli --config .private/base.json revoke --person-id PERSON_UUID
```

Enrollment requires one sufficiently clear face per image. Enroll only with the
person's agreement. Several views and independent live tests are needed; one photo
is a starter reference, not proof of accuracy. Default cosine threshold 0.5 and
runner-up margin 0.08 are provisional and require calibration with known and unknown
people. This is a prototype, not access control, liveness detection or authentication.
Revocation removes reference embeddings and synchronizes gallery deletion. It does
not erase historical observations automatically; manage those separately if required.

## Offline and retention behavior

- Local DB survives reboot. Station offline: local gallery still works and events queue.
- Gallery lease: 7 days since successful sync; then identity becomes unknown/person.
- Local DB unavailable: cached references expire after 15 seconds; category detection
  continues. The in-memory event queue is limited to 30 items; failures can lose events.
- Local observations: uploaded records expire after 24 h, pending records after 7 days,
  with a hard cap of 100,000 rows. Long outages can therefore lose oldest observations.
- Base observations are retained until explicitly deleted; plan backups and a retention
  policy before extended use. These are sampled observations, not reliable track history.
- Sync every 10 seconds, up to 250 records per pass. Remote commit precedes local ACK;
  UUID deduplication handles interrupted ACKs. PC is sole enrollment authority.

## Pi deployment (requires working SSH and sudo)

Target: Ubuntu 24.04, ROS 2 Jazzy, user underbot. Not yet hardware-validated.
Copy perception source to /home/underbot/UnderBot/perception, excluding .pixi, .private,
models, logs and recordings. Run `bash memory/setup_pi.sh` from that folder.
It installs a local PostgreSQL DB, Python venv and vision dependencies. A Pi camera
or USB camera must be exposed through a compatible driver; this capture script uses
V4L2 for USB webcams. A CSI camera may need a separate ROS/libcamera publisher.

Base access uses an SSH reverse tunnel initiated from the PC:

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 127.0.0.1:55433:127.0.0.1:55432 underbot@100.123.136.69
```

PostgreSQL remains loopback-only; no public database port or Windows inbound firewall
opening is needed. Provision the generated `underbot_sync` password from the private
PC credentials file into the Pi's private pgpass entry for host127.0.0.1 port55433,
database underbot_base, user underbot_sync. Transfer only this restricted credential,
never the PC admin credential. The sync role can read gallery data and insert/read
observations, but cannot change enrollment. Keep pgpass mode0600.

On the Pi, with Jazzy sourced:

```bash
source /opt/ros/jazzy/setup.bash
.venv/bin/python -m memory.cli --config .private/robot.json sync
# Separate terminals, same ROS domain; keep localhost discovery for local bridge:
.venv/bin/python camera_node.py --camera-index 0 --domain 74
.venv/bin/python yolo_node.py --domain 74 --memory-config .private/robot.json
```

memory/underbot-memory.service is a systemd template for the sync worker. Adjust paths
before installing it; the camera/recognition services are not auto-enabled. Network
ROS discovery can be configured separately; Foxglove can use a bridge on the Pi.
Test reboot, station shutdown and camera unplug/replug before unattended operation.

## Validation

`pixi run python -m unittest test_memory -v` uses temporary schemas in the local
base/edge-test databases; it does not enroll test identities in the production gallery.
Tests cover matching/rejection, invalid embeddings, offline gallery use, idempotent
upload retry, gallery expiry, revocation propagation and event retention.
Live camera/recognition speed and false matches need separate Pi and enrollment tests.

Sources: https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html
and https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface

## Current deployment

The Pi memory service and stored-photo checks are now deployed and verified. See [deployment results and startup](DEPLOYMENT.md). The earlier not-yet-hardware-validated note still applies to live camera operation, not to the tested database and stored-image components.
