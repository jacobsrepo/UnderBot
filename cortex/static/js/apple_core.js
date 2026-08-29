/**
 * Cortex — Apple Intelligence Fluid Core & Siri Glow Visualizer
 *
 * Recreates the signature Apple Intelligence multi-color iridescent gradient
 * mesh with organic blob interpolation, audio-reactive ripples, and state transitions.
 */

const APPLE_STATES = {
    idle: {
        label: 'Siri is Ready',
        subtext: 'Tap or speak to start',
        colors: ['#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4', '#ffffff'],
        glowIntensity: 0.6,
        speed: 0.8,
        scale: 1.0,
        rippleSpeed: 1.0,
        borderGlow: 0.25,
    },
    listening: {
        label: 'Listening…',
        subtext: 'Speak naturally',
        colors: ['#06b6d4', '#3b82f6', '#8b5cf6', '#38bdf8', '#ffffff'],
        glowIntensity: 1.0,
        speed: 1.8,
        scale: 1.15,
        rippleSpeed: 2.5,
        borderGlow: 0.85,
    },
    thinking: {
        label: 'Thinking…',
        subtext: 'Processing request with Qwen3-VL',
        colors: ['#f59e0b', '#ec4899', '#8b5cf6', '#f97316', '#ffffff'],
        glowIntensity: 0.9,
        speed: 2.2,
        scale: 1.08,
        rippleSpeed: 1.8,
        borderGlow: 0.70,
    },
    speaking: {
        label: 'Speaking…',
        subtext: 'PocketTTS audio stream active',
        colors: ['#10b981', '#06b6d4', '#3b82f6', '#a7f3d0', '#ffffff'],
        glowIntensity: 1.1,
        speed: 2.0,
        scale: 1.22,
        rippleSpeed: 3.2,
        borderGlow: 0.90,
    },
    seeing: {
        label: 'Inspecting Camera…',
        subtext: 'Analyzing visual frame',
        colors: ['#8b5cf6', '#ec4899', '#3b82f6', '#d8b4fe', '#ffffff'],
        glowIntensity: 0.95,
        speed: 1.4,
        scale: 1.05,
        rippleSpeed: 1.5,
        borderGlow: 0.75,
    },
    programming: {
        label: 'Controlling Hardware…',
        subtext: 'Arduino Nano pin execution',
        colors: ['#f97316', '#f59e0b', '#ec4899', '#fed7aa', '#ffffff'],
        glowIntensity: 0.95,
        speed: 1.7,
        scale: 1.10,
        rippleSpeed: 2.0,
        borderGlow: 0.80,
    },
    error: {
        label: 'Error',
        subtext: 'Connection or execution failed',
        colors: ['#ef4444', '#f97316', '#b91c1c', '#fca5a5', '#ffffff'],
        glowIntensity: 1.0,
        speed: 2.5,
        scale: 1.05,
        rippleSpeed: 3.5,
        borderGlow: 0.80,
    }
};

export class AppleIntelligenceCore {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error(`#${containerId} not found`);

        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d', { alpha: true });
        this.container.innerHTML = '';
        this.container.appendChild(this.canvas);

        this.borderAura = document.getElementById('apple-edge-glow');

        this.currentState = 'idle';
        this.time = 0;
        this.lastTime = performance.now();

        // 4 Multi-colored morphing plasma blobs inside the core
        this.blobs = [
            { x: 0, y: 0, r: 60, angle: 0, speed: 1.1, radiusOffset: 35 },
            { x: 0, y: 0, r: 70, angle: Math.PI * 0.5, speed: 0.9, radiusOffset: 40 },
            { x: 0, y: 0, r: 65, angle: Math.PI * 1.0, speed: 1.3, radiusOffset: 30 },
            { x: 0, y: 0, r: 55, angle: Math.PI * 1.5, speed: 0.8, radiusOffset: 45 },
        ];

        // Interpolated physics
        const init = APPLE_STATES.idle;
        this.cur = {
            glow: init.glowIntensity,
            speed: init.speed,
            scale: init.scale,
            borderGlow: init.borderGlow,
        };
        this.target = { ...this.cur };

        this._resize = this._resize.bind(this);
        window.addEventListener('resize', this._resize);
        this._resize();

        this._animate = this._animate.bind(this);
        requestAnimationFrame(this._animate);
    }

    setState(stateName) {
        const s = APPLE_STATES[stateName];
        if (!s) return;
        this.currentState = stateName;
        this.target.glow = s.glowIntensity;
        this.target.speed = s.speed;
        this.target.scale = s.scale;
        this.target.borderGlow = s.borderGlow;

        // Update screen edge glow opacity & animation
        if (this.borderAura) {
            this.borderAura.style.opacity = s.borderGlow;
            this.borderAura.className = `apple-edge-glow state-${stateName}`;
        }
    }

    getStateInfo(stateName) {
        return APPLE_STATES[stateName] || APPLE_STATES.idle;
    }

    _resize() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.container.getBoundingClientRect();
        const size = Math.min(rect.width || 340, rect.height || 340);

        this.canvas.width = size * dpr;
        this.canvas.height = size * dpr;
        this.canvas.style.width = `${size}px`;
        this.canvas.style.height = `${size}px`;

        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx.scale(dpr, dpr);
        this.width = size;
        this.height = size;
    }

    _animate(now) {
        requestAnimationFrame(this._animate);

        const dt = Math.min((now - this.lastTime) / 1000, 0.1);
        this.lastTime = now;
        this.time += dt * this.cur.speed;

        // Smooth spring lerp
        const lf = 1.0 - Math.pow(0.02, dt);
        this.cur.glow += (this.target.glow - this.cur.glow) * lf;
        this.cur.speed += (this.target.speed - this.cur.speed) * lf;
        this.cur.scale += (this.target.scale - this.cur.scale) * lf;
        this.cur.borderGlow += (this.target.borderGlow - this.cur.borderGlow) * lf;

        this._render();
    }

    _render() {
        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;
        const cx = w / 2;
        const cy = h / 2;

        ctx.clearRect(0, 0, w, h);

        const stateConfig = APPLE_STATES[this.currentState] || APPLE_STATES.idle;
        const colors = stateConfig.colors;

        // Speech harmonic breathing
        const pulse = Math.sin(this.time * 2.5) * 6;
        const baseR = 78 * this.cur.scale + pulse;

        // ── 1. Soft Ambient Luminescent Outer Aura ───────────────────
        ctx.save();
        const outerAura = ctx.createRadialGradient(cx, cy, 0, cx, cy, baseR * 2.0);
        outerAura.addColorStop(0.0, colors[1] + '44');
        outerAura.addColorStop(0.4, colors[2] + '22');
        outerAura.addColorStop(1.0, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = outerAura;
        ctx.beginPath();
        ctx.arc(cx, cy, baseR * 2.0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // ── 2. Fluid Morphing Blobs (Apple Intelligence Gradient Mesh) ─
        ctx.save();
        ctx.globalCompositeOperation = 'screen';

        for (let i = 0; i < this.blobs.length; i++) {
            const b = this.blobs[i];
            const angle = b.angle + this.time * b.speed * 0.7;
            const dist = b.radiusOffset * (0.8 + 0.2 * Math.sin(this.time * 1.5 + i));

            const bx = cx + Math.cos(angle) * dist;
            const by = cy + Math.sin(angle) * dist;
            const br = b.r * this.cur.scale * (0.9 + 0.1 * Math.cos(this.time * 2.0 + i));

            const blobGrad = ctx.createRadialGradient(bx, by, 0, bx, by, br);
            blobGrad.addColorStop(0.0, colors[i % colors.length] + 'ee');
            blobGrad.addColorStop(0.5, colors[(i + 1) % colors.length] + '88');
            blobGrad.addColorStop(1.0, 'rgba(0, 0, 0, 0)');

            ctx.fillStyle = blobGrad;
            ctx.beginPath();
            ctx.arc(bx, by, br, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();

        // ── 3. Central Luminous White Core ───────────────────────────
        ctx.save();
        const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, baseR * 0.7);
        coreGrad.addColorStop(0.0, 'rgba(255, 255, 255, 0.98)');
        coreGrad.addColorStop(0.35, 'rgba(255, 255, 255, 0.65)');
        coreGrad.addColorStop(0.70, colors[0] + '33');
        coreGrad.addColorStop(1.0, 'rgba(0, 0, 0, 0)');

        ctx.fillStyle = coreGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, baseR * 0.7, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // ── 4. Precision Glass Specular Sheen (Apple Lens Reflection) ─
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, baseR * 1.05, 0, Math.PI * 2);
        const rimGrad = ctx.createLinearGradient(cx - baseR, cy - baseR, cx + baseR, cy + baseR);
        rimGrad.addColorStop(0.0, 'rgba(255, 255, 255, 0.55)');
        rimGrad.addColorStop(0.3, 'rgba(255, 255, 255, 0.15)');
        rimGrad.addColorStop(0.7, 'rgba(255, 255, 255, 0.05)');
        rimGrad.addColorStop(1.0, 'rgba(255, 255, 255, 0.40)');

        ctx.strokeStyle = rimGrad;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.restore();
    }
}
