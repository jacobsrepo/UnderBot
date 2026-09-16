import type { PanelExtensionContext } from "@foxglove/extension";

type Status = { mode?: string; hardware_enabled?: boolean; comms?: string; ai?: string };
type Config = { prefix: string; lateral: boolean };
const zero = () => ({ linear: { x: 0, y: 0, z: 0 }, angular: { x: 0, y: 0, z: 0 } });
const stringDefinition = { definitions: [{ name: "data", type: "string", isArray: false, isComplex: false }] };
const vectorDefinition = { definitions: ["x", "y", "z"].map((name) => ({ name, type: "float64", isArray: false, isComplex: false })) };
const twistDefinition = { definitions: ["linear", "angular"].map((name) => ({ name, type: "geometry_msgs/msg/Vector3", isArray: false, isComplex: true })) };

export function initStation(context: PanelExtensionContext): () => void {
  const initial = (context.initialState ?? {}) as Partial<Config>;
  let config: Config = { prefix: initial.prefix ?? "/station", lateral: initial.lateral ?? false };
  let status: Status = {};
  let statusAt = 0;
  let imuAt = 0;
  let odomAt = 0;
  let armed = false;
  let command = zero();
  let pan = zero();
  let held = false;
  let panHeld = false;
  let advertised = false;
  let disposed = false;
  let pendingChat: string | undefined;
  let chatSentAt = 0;
  const root = context.panelElement;
  root.innerHTML = `<style>
    .ub{font:13px system-ui;color:#e4edf4;background:#101921;height:100%;overflow:auto;padding:16px;box-sizing:border-box}
    .ub *{box-sizing:border-box}.ub h2{font-size:18px;margin:0}.ub h3{font-size:13px;text-transform:uppercase;letter-spacing:1px;color:#8da5b8;margin:18px 0 10px}
    .ub header,.ub .row{display:flex;align-items:center;justify-content:space-between;gap:10px}.ub .tag{color:#64dbd5;font-size:11px;border:1px solid #34555e;border-radius:12px;padding:4px 8px}
    .ub .note{color:#9dafbe;font-size:12px;margin:8px 0;line-height:1.5}.ub .error{color:#ffb9a2}
    .ub button,.ub input,.ub select{font:inherit;color:inherit;background:#213342;border:1px solid #405969;border-radius:7px;padding:9px}
    .ub button{cursor:pointer;touch-action:none}.ub button:disabled{opacity:.35;cursor:default}.ub button:active{background:#27645f}
    .ub .pad{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;max-width:290px;margin:8px auto}.ub .stop{background:#652f36}.ub .accent{background:#18534f}
    .ub .telemetry{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.ub .card{background:#182630;border-radius:9px;padding:12px}.ub .speed{font-size:30px;font-variant-numeric:tabular-nums}
    .ub .horizon{height:94px;position:relative;overflow:hidden;border-radius:8px;background:#263849}.ub .attitude{position:absolute;inset:-100px;background:linear-gradient(#25506d 50%,#795438 50%);transform-origin:center}
    .ub .cross{position:absolute;top:50%;left:20%;right:20%;border-top:2px solid #fff}.ub .angles{font-size:11px;margin-top:8px}
    .ub .messages{height:140px;overflow:auto;background:#0c141b;padding:9px;border-radius:7px;white-space:pre-wrap;overflow-wrap:anywhere}.ub .messages p{margin:5px 0}.ub textarea{width:100%;margin:8px 0;background:#172630;border:1px solid #405969;color:inherit;padding:8px;resize:vertical}
    .ub details{margin-top:18px}.ub label{display:block;margin:8px 0}.ub input[type=text]{width:100%}
  </style><div class="ub">
    <header><h2>UnderBot station</h2><span class="tag" data-id="mode">NO ROBOT DATA</span></header>
    <p class="note" data-id="connection">Waiting for the station heartbeat.</p>
    <div class="telemetry"><div class="card"><div class="note">Measured planar speed</div><div class="speed" data-id="speed">—</div><div class="note">m/s · from odometry</div></div>
    <div class="card"><div class="horizon"><div class="attitude" data-id="attitude"></div><div class="cross"></div></div><div class="angles" data-id="angles">IMU: no data</div></div></div>
    <h3>Robot movement</h3><div class="row"><button class="accent" data-id="arm">Enable controls</button><label>Speed <select data-id="speedSet"><option value="0.05">0.05 m/s</option><option value="0.1" selected>0.10 m/s</option><option value="0.2">0.20 m/s</option></select></label></div>
    <div class="pad"><span></span><button data-drive="F">F ↑</button><span></span><button data-drive="L">L ↶</button><button class="stop" data-id="stop">STOP</button><button data-drive="R">R ↷</button><span></span><button data-drive="B">B ↓</button><span></span></div>
    <p class="note">Hold to move. Release to stop. Left/right turn by default. STOP sends a zero velocity request; it is not a hardware emergency stop.</p>
    <h3>Camera aim</h3><div class="pad"><span></span><button data-pan="U">U ↑</button><span></span><button data-pan="L">L ←</button><button data-id="cameraStop">Hold</button><button data-pan="R">R →</button><span></span><button data-pan="D">D ↓</button><span></span></div>
    <p class="note">Pan/tilt velocity requests · requires a camera actuator adapter.</p>
    <h3>Communications</h3><button data-id="comms">Request comms ON</button><button data-id="commsOff">Request comms OFF</button><p class="note" data-id="commsState">Audio backend: not connected</p>
    <h3>Robot AI chat</h3><div class="messages" data-id="messages"><p>Waiting for the robot AI backend. Chat does not issue motor commands.</p></div><textarea data-id="prompt" rows="2" placeholder="Ask about the robot…" maxlength="2000"></textarea><button data-id="send">Send</button><p class="note" data-id="chatState">No AI provider configured.</p>
    <p class="note error" data-id="error"></p>
    <details><summary>Topic settings</summary><label>Station namespace<input type="text" data-id="prefix"></label><label><input type="checkbox" data-id="lateral"> Left/right means strafe (holonomic base)</label><button data-id="apply">Apply and disable controls</button><p class="note">Telemetry: /imu/data and /odom. Configure other views in their panel settings.</p></details>
  </div>`;
  const el = <T extends HTMLElement = HTMLElement>(id: string) => root.querySelector<T>(`[data-id="${id}"]`)!;
  el<HTMLInputElement>("prefix").value = config.prefix;
  el<HTMLInputElement>("lateral").checked = config.lateral;
  const text = (id: string, value: string) => { el(id).textContent = value; };
  const fresh = () => Date.now() - statusAt < 1800;
  const canPublish = () => !!context.publish && !!context.advertise && fresh();
  const canMove = () => canPublish() && armed && (status.mode === "demo" || status.hardware_enabled === true);
  function advertise() {
    if (advertised || !context.advertise) { return; }
    for (const suffix of ["cmd_vel", "camera_cmd"]) {
      context.advertise(`${config.prefix}/${suffix}`, "geometry_msgs/msg/Twist", {
        datatypes: new Map([["geometry_msgs/msg/Vector3", vectorDefinition], ["geometry_msgs/msg/Twist", twistDefinition]]),
      });
    }
    for (const suffix of ["comms/request", "ai/request"]) {
      context.advertise(`${config.prefix}/${suffix}`, "std_msgs/msg/String", { datatypes: new Map([["std_msgs/msg/String", stringDefinition]]) });
    }
    advertised = true;
  }
  function publish(suffix: string, msg: unknown) {
    if (!context.publish || !context.advertise) { return; }
    try { advertise(); context.publish(`${config.prefix}/${suffix}`, msg); }
    catch (err) { text("error", `Publish failed: ${String(err)}`); armed = false; held = false; panHeld = false; }
  }
  function stop() { held = false; panHeld = false; command = zero(); pan = zero(); if (advertised) { publish("cmd_vel", command); publish("camera_cmd", pan); } }
  function refresh() {
    if (!fresh()) { if (armed || held || panHeld) { stop(); } armed = false; }
    text("mode", !fresh() ? "NO ROBOT DATA" : status.mode === "demo" ? "SYNTHETIC DEMO" : status.hardware_enabled ? "HARDWARE ENABLED" : "HARDWARE DISABLED");
    text("connection", fresh() ? "Station heartbeat received" : "Waiting for /station/status. Connect to ws://100.123.136.69:8765.");
    el<HTMLButtonElement>("arm").disabled = !canPublish() || !(status.mode === "demo" || status.hardware_enabled);
    text("arm", armed ? "Disable controls" : "Enable controls");
    root.querySelectorAll<HTMLButtonElement>("[data-drive], [data-pan]").forEach((b) => { b.disabled = !canMove(); });
    el<HTMLButtonElement>("comms").disabled = !canPublish(); el<HTMLButtonElement>("commsOff").disabled = !canPublish();
    el<HTMLButtonElement>("send").disabled = !canPublish() || !!pendingChat;
    if (Date.now() - imuAt > 1800) { text("angles", "IMU: no recent valid orientation"); el("attitude").style.opacity = "0.25"; }
    if (Date.now() - odomAt > 1800) { text("speed", "—"); }
    if (pendingChat && Date.now() - chatSentAt > 20000) { pendingChat = undefined; text("chatState", "No response. Check the AI backend."); }
    text("commsState", fresh() ? `Audio backend: ${status.comms ?? "not configured"}` : "Audio backend: no recent status");
  }
  function subscribe() { context.subscribe(["/imu/data", "/odom", `${config.prefix}/status`, `${config.prefix}/ai/response`].map((topic) => ({ topic }))); }
  function chatLine(value: string) { const p = document.createElement("p"); p.textContent = value; el("messages").append(p); while (el("messages").children.length > 40) { el("messages").firstElementChild?.remove(); } el("messages").scrollTop = el("messages").scrollHeight; }
  el("arm").onclick = () => { if (armed) { stop(); armed = false; } else if (fresh()) { armed = true; } refresh(); };
  el("stop").onclick = () => { stop(); armed = false; refresh(); };
  el("cameraStop").onclick = () => { panHeld = false; pan = zero(); publish("camera_cmd", pan); };
  function bindHold(button: HTMLButtonElement, camera: boolean) {
    button.onpointerdown = (event) => {
      if (!canMove() || event.button !== 0) { return; }
      event.preventDefault(); stop(); button.setPointerCapture(event.pointerId);
      const dir = camera ? button.dataset.pan : button.dataset.drive;
      if (camera) { panHeld = true; pan.angular.z = dir === "L" ? 0.3 : dir === "R" ? -0.3 : 0; pan.angular.y = dir === "U" ? -0.3 : dir === "D" ? 0.3 : 0; publish("camera_cmd", pan); }
      else { held = true; const v = Number(el<HTMLSelectElement>("speedSet").value); command.linear.x = dir === "F" ? v : dir === "B" ? -v : 0;
        if (config.lateral) { command.linear.y = dir === "L" ? v : dir === "R" ? -v : 0; } else { command.angular.z = dir === "L" ? 0.35 : dir === "R" ? -0.35 : 0; } publish("cmd_vel", command); }
    };
    button.onpointerup = stop; button.onpointercancel = stop; button.onlostpointercapture = stop;
  }
  root.querySelectorAll<HTMLButtonElement>("[data-drive]").forEach((b) => bindHold(b, false));
  root.querySelectorAll<HTMLButtonElement>("[data-pan]").forEach((b) => bindHold(b, true));
  el("comms").onclick = () => publish("comms/request", { data: JSON.stringify({ enabled: true }) });
  el("commsOff").onclick = () => publish("comms/request", { data: JSON.stringify({ enabled: false }) });
  el("send").onclick = () => {
    const prompt = el<HTMLTextAreaElement>("prompt").value.trim(); if (!prompt || !canPublish() || pendingChat) { return; }
    pendingChat = `${Date.now()}-${Math.random().toString(36).slice(2)}`; chatSentAt = Date.now();
    publish("ai/request", { data: JSON.stringify({ id: pendingChat, text: prompt }) });
    chatLine(`You: ${prompt}`); el<HTMLTextAreaElement>("prompt").value = ""; text("chatState", "Waiting for robot AI…"); refresh();
  };
  el("apply").onclick = () => {
    const prefix = el<HTMLInputElement>("prefix").value.trim().replace(/\/$/, "");
    if (!/^\/[A-Za-z][A-Za-z0-9_/]*$/.test(prefix)) { text("error", "Use an absolute ROS namespace, e.g. /station"); return; }
    stop(); armed = false;
    for (const suffix of ["cmd_vel", "camera_cmd", "comms/request", "ai/request"]) { context.unadvertise?.(`${config.prefix}/${suffix}`); }
    config = { prefix, lateral: el<HTMLInputElement>("lateral").checked }; advertised = false; statusAt = 0; context.saveState(config); subscribe(); refresh();
  };
  const loseFocus = () => { stop(); armed = false; refresh(); };
  window.addEventListener("blur", loseFocus); document.addEventListener("visibilitychange", loseFocus);
  const timer = window.setInterval(() => { if (disposed) { return; } refresh(); if (canMove()) { if (held) { publish("cmd_vel", command); } if (panHeld) { publish("camera_cmd", pan); } } }, 100);
  context.onRender = (state, done) => {
    try {
      if (state.didSeek) { loseFocus(); statusAt = 0; imuAt = 0; odomAt = 0; }
      for (const event of state.currentFrame ?? []) {
        const m = event.message as Record<string, any>;
        if (event.topic === `${config.prefix}/status`) { status = JSON.parse(m.data) as Status; statusAt = Date.now(); }
        else if (event.topic === "/imu/data") {
          const q = m.orientation; const n = q ? Math.hypot(q.x, q.y, q.z, q.w) : 0;
          if (n > 0.0001 && Number.isFinite(n) && m.orientation_covariance?.[0] !== -1) {
            const x=q.x/n,y=q.y/n,z=q.z/n,w=q.w/n;
            const roll=Math.atan2(2*(w*x+y*z),1-2*(x*x+y*y))*180/Math.PI;
            const pitch=Math.asin(Math.max(-1,Math.min(1,2*(w*y-z*x))))*180/Math.PI;
            const yaw=Math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))*180/Math.PI;
            el("attitude").style.transform=`translateY(${pitch}px) rotate(${-roll}deg)`; el("attitude").style.opacity="1";
            text("angles", `R ${roll.toFixed(1)}° · P ${pitch.toFixed(1)}° · Y ${yaw.toFixed(1)}°`); imuAt=Date.now();
          }
        } else if (event.topic === "/odom") { const v=m.twist?.twist?.linear; if (v && Number.isFinite(v.x) && Number.isFinite(v.y)) { text("speed", Math.hypot(v.x,v.y).toFixed(2)); odomAt=Date.now(); } }
        else if (event.topic === `${config.prefix}/ai/response`) { const response=JSON.parse(m.data); if (response.id === pendingChat) { chatLine(`Robot: ${String(response.text)}`); pendingChat=undefined; text("chatState", response.ok ? "Response received" : "Backend not ready"); } }
      }
      refresh();
    } catch (err) { text("error", `Invalid telemetry: ${String(err)}`); }
    finally { done(); }
  };
  context.watch("currentFrame"); context.watch("didSeek"); subscribe(); refresh();
  return () => { stop(); disposed=true; window.clearInterval(timer); window.removeEventListener("blur",loseFocus); document.removeEventListener("visibilitychange",loseFocus); for(const suffix of ["cmd_vel","camera_cmd","comms/request","ai/request"]){ context.unadvertise?.(`${config.prefix}/${suffix}`); } root.replaceChildren(); };
}
