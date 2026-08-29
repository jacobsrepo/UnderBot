/**
 * Cortex Orb — Photorealistic Crystal Glass Sphere with Swirling Energy Core
 *
 * Faithfully matches the iconic glass orb aesthetic:
 * 1. Thick optical crystal glass shell with realistic studio room reflections & caustic refraction
 * 2. Floating inner luminous tri-spiral energy core (swirling vortex arms & glowing white center)
 * 3. Faint orbital micro-sparkle ring
 * 4. Speech/audio-reactive harmonic pulsation & dynamic state animations
 */

// ── State Palette & Physics Config ──────────────────────────────────
const STATES = {
    idle: {
        coreColor:   [0.85, 0.92, 1.00],  // Ice pearl white
        glowColor:   [0.35, 0.60, 0.95],  // Soft ethereal cyan-blue
        rimColor:    [0.55, 0.75, 1.00],  // Glass rim sheen
        spinSpeed:   0.65,
        pulseFreq:   1.8,
        pulseAmp:    0.025,
        armDensity:  1.0,
        coreScale:   0.52,
        glimmerAlpha:0.45,
    },
    listening: {
        coreColor:   [0.70, 0.95, 1.00],  // Vivid acoustic ice blue
        glowColor:   [0.10, 0.65, 1.00],  // Deep responsive cyan
        rimColor:    [0.40, 0.85, 1.00],  // Crisp blue rim
        spinSpeed:   1.10,
        pulseFreq:   3.6,
        pulseAmp:    0.060,
        armDensity:  1.25,
        coreScale:   0.56,
        glimmerAlpha:0.75,
    },
    thinking: {
        coreColor:   [1.00, 0.96, 0.82],  // Radiant warm white
        glowColor:   [0.98, 0.68, 0.15],  // Warm amber gold
        rimColor:    [1.00, 0.82, 0.35],  // Golden glass rim
        spinSpeed:   2.20,
        pulseFreq:   2.4,
        pulseAmp:    0.040,
        armDensity:  1.40,
        coreScale:   0.54,
        glimmerAlpha:0.85,
    },
    speaking: {
        coreColor:   [0.88, 1.00, 0.94],  // Luminous seafoam white
        glowColor:   [0.15, 0.85, 0.65],  // Vibrant speech turquoise
        rimColor:    [0.35, 0.95, 0.75],  // Mint glass sheen
        spinSpeed:   1.40,
        pulseFreq:   5.0,
        pulseAmp:    0.085,
        armDensity:  1.35,
        coreScale:   0.58,
        glimmerAlpha:0.90,
    },
    seeing: {
        coreColor:   [0.95, 0.88, 1.00],  // Violet-white focus
        glowColor:   [0.65, 0.25, 0.95],  // Royal amethyst
        rimColor:    [0.80, 0.45, 1.00],  // Ultraviolet sheen
        spinSpeed:   0.85,
        pulseFreq:   2.2,
        pulseAmp:    0.035,
        armDensity:  1.10,
        coreScale:   0.50,
        glimmerAlpha:0.60,
    },
    programming: {
        coreColor:   [1.00, 0.92, 0.80],  // Incandescent white
        glowColor:   [0.98, 0.45, 0.12],  // Warm fiery copper
        rimColor:    [1.00, 0.65, 0.25],  // Bronze glass rim
        spinSpeed:   1.60,
        pulseFreq:   3.2,
        pulseAmp:    0.055,
        armDensity:  1.30,
        coreScale:   0.54,
        glimmerAlpha:0.80,
    },
    error: {
        coreColor:   [1.00, 0.85, 0.85],  // Ruby flare
        glowColor:   [0.92, 0.15, 0.18],  // Crimson alert
        rimColor:    [1.00, 0.40, 0.40],  // Red glass sheen
        spinSpeed:   2.50,
        pulseFreq:   6.5,
        pulseAmp:    0.090,
        armDensity:  1.50,
        coreScale:   0.55,
        glimmerAlpha:0.95,
    },
};

// ── Vertex Shader ───────────────────────────────────────────────────
const VERT_SRC = `
attribute vec2 a_position;
varying vec2 v_uv;
void main() {
    v_uv = a_position * 0.5 + 0.5;
    gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

// ── Fragment Shader ─────────────────────────────────────────────────
const FRAG_SRC = `
precision highp float;

varying vec2 v_uv;

uniform vec2  u_resolution;
uniform float u_time;

uniform vec3  u_coreColor;
uniform vec3  u_glowColor;
uniform vec3  u_rimColor;
uniform float u_spinSpeed;
uniform float u_pulseFreq;
uniform float u_pulseAmp;
uniform float u_armDensity;
uniform float u_coreScale;
uniform float u_glimmerAlpha;

#define PI 3.14159265359
#define TWO_PI 6.28318530718

// ── Studio Environment Map Synthesis ─────────────────────────────────
// Simulates high-end studio softboxes and architectural window reflections
vec3 getStudioReflection(vec3 refDir, float roughness) {
    // 1. Primary Left Studio Softbox / Window
    vec3 boxDir1 = normalize(vec3(-0.65, 0.45, 0.60));
    float d1 = max(dot(refDir, boxDir1), 0.0);
    float softbox1 = pow(d1, 32.0 / (roughness + 0.5)) * 0.95;
    float softbox1_broad = pow(d1, 6.0) * 0.25;

    // 2. Secondary Right Warm Softbox Fill
    vec3 boxDir2 = normalize(vec3(0.70, 0.35, 0.60));
    float d2 = max(dot(refDir, boxDir2), 0.0);
    float softbox2 = pow(d2, 24.0 / (roughness + 0.5)) * 0.40;

    // 3. Dark Studio Horizon & Ceiling Ambient
    float horizon = smoothstep(-0.2, 0.4, refDir.y) * 0.12 + 0.03;
    vec3 studioAmb = vec3(0.70, 0.75, 0.85) * horizon;

    // 4. Subtle Architectural Window Grid Lines on Primary Softbox
    vec2 windowUV = refDir.xy * 2.5 + vec2(0.5, 0.0);
    float grid = smoothstep(0.02, 0.06, abs(fract(windowUV.x * 2.0) - 0.5)) *
                 smoothstep(0.02, 0.06, abs(fract(windowUV.y * 2.0) - 0.5));
    float windowHighlight = (softbox1 * (0.6 + 0.4 * grid)) + softbox1_broad;

    vec3 refl = studioAmb + vec3(0.95, 0.98, 1.0) * windowHighlight + vec3(0.90, 0.85, 0.80) * softbox2;
    return refl;
}

// ── Pseudo-random noise for micro-glimmers ───────────────────────────
float hash(vec2 p) {
    p = fract(p * vec2(234.34, 435.345));
    p += dot(p, p + 34.23);
    return fract(p.x * p.y);
}

void main() {
    vec2 st = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / min(u_resolution.x, u_resolution.y);
    float dist = length(st);

    const float R_OUTER = 0.42;  // Outer Glass Sphere Radius

    // Soft outer ambient shadow underneath the glass orb
    if (dist > R_OUTER + 0.006) {
        float shadow = smoothstep(R_OUTER + 0.06, R_OUTER, dist) * 0.025;
        gl_FragColor = vec4(0.0, 0.0, 0.0, shadow);
        return;
    }

    // ── 3D Glass Sphere Normal & Ray Calculations ────────────────────
    float normDist = dist / R_OUTER;
    float z = sqrt(max(0.0, 1.0 - normDist * normDist));
    vec3 N = normalize(vec3(st / R_OUTER, z)); // Surface Normal
    vec3 V = vec3(0.0, 0.0, 1.0);              // View Direction (Camera)

    // Fresnel Factor
    float NdotV = max(dot(N, V), 0.0);
    float fresnel = pow(1.0 - NdotV, 2.6);
    float grazing = pow(1.0 - NdotV, 5.0);

    // Refraction into the thick glass marble
    vec3 refr = refract(-V, N, 1.0 / 1.54); // Crystal Glass Index

    // ── Interior Luminous Tri-Spiral Energy Core ─────────────────────
    // Speech harmonic pulsation
    float pulse = sin(u_time * u_pulseFreq) * u_pulseAmp;
    float speechRipple = sin(dist * 28.0 - u_time * 8.0) * (u_pulseAmp * 0.5);

    // Core coordinates with refraction distortion
    vec2 coreUV = (st + refr.xy * 0.12) / (u_coreScale + pulse + speechRipple);
    float r = length(coreUV);
    float angle = atan(coreUV.y, coreUV.x);

    // Dynamic Tri-Spiral Vortex Math
    // Spin with smooth angular acceleration toward the center
    float spin = u_time * u_spinSpeed;
    float spiralAngle = angle + (3.2 / (r + 0.28)) - spin;

    // 3 Swirling Spiral Arms
    float arm1 = sin(3.0 * spiralAngle);
    float arm2 = sin(3.0 * spiralAngle + PI * 0.5);
    float spiralArms = smoothstep(-0.2, 0.85, arm1) * 0.75 + smoothstep(0.1, 0.95, arm2) * 0.35;

    // Multi-layered Core Density & Radial Falloff
    float coreShape = smoothstep(1.05, 0.05, r);
    float innerGlow = smoothstep(0.70, 0.0, r);
    float photonCenter = smoothstep(0.35, 0.0, r);

    // Combine Spiral Arms with Core Luminescence
    float plasmaDensity = (spiralArms * u_armDensity * 0.65 + 0.35) * coreShape;
    plasmaDensity += innerGlow * 0.75 + photonCenter * 1.5;

    // Core Colors: Soft Glow → Core Color → White Hot Center
    vec3 plasmaColor = mix(u_glowColor * 0.6, u_glowColor, smoothstep(0.1, 0.5, plasmaDensity));
    plasmaColor = mix(plasmaColor, u_coreColor, smoothstep(0.4, 0.9, plasmaDensity));
    plasmaColor += vec3(1.0, 1.0, 1.0) * pow(photonCenter, 2.2) * 1.35;

    // Internal Soft Ethereal Halo inside the glass
    float innerHalo = smoothstep(1.3, 0.1, r) * 0.45;
    plasmaColor += u_glowColor * innerHalo;

    // ── Delicate Orbital Micro-Sparkles / Stardust Ring ──────────────
    float ringR = length(coreUV);
    float ringDist = abs(ringR - 0.72);
    float ringBand = smoothstep(0.12, 0.0, ringDist);

    // Sparkle points around the ring
    float sparkAngle = angle + spin * 0.4;
    float sparkHash = hash(vec2(floor(sparkAngle * 18.0) / 18.0, 3.42));
    float sparkBlink = sin(u_time * 4.0 + sparkHash * TWO_PI) * 0.5 + 0.5;
    float glimmers = ringBand * smoothstep(0.65, 0.98, sparkHash) * sparkBlink * u_glimmerAlpha;
    vec3 glimmerColor = mix(u_coreColor, vec3(1.0, 1.0, 1.0), 0.75) * glimmers * 1.8;

    // Composite Interior Volume
    vec3 interior = plasmaColor * coreShape + glimmerColor;

    // ── Photorealistic Glass Shading & Surface Reflections ───────────
    vec3 reflDir = reflect(-V, N);

    // Studio Environment Reflections
    vec3 studioRefl = getStudioReflection(reflDir, 0.05);

    // Internal Glass Caustic Depth & Thickness
    // The bottom of the glass ball collects deep ambient shadow
    float bottomShadow = smoothstep(0.4, -0.6, N.y) * 0.45;
    vec3 glassBody = mix(vec3(0.08, 0.10, 0.14), vec3(0.02, 0.03, 0.04), bottomShadow);

    // Glass Rim Brightness & Anti-Reflective Glaze
    vec3 rimGlow = mix(u_rimColor, vec3(0.85, 0.92, 1.0), 0.5);
    vec3 glassEdge = rimGlow * (fresnel * 0.85 + grazing * 0.65);

    // Secondary Soft Rim Highlight (bottom-left grounding rim)
    vec3 subRimDir = normalize(vec3(0.3, -0.7, 0.5));
    float subRim = pow(max(dot(reflDir, subRimDir), 0.0), 16.0) * 0.35;

    // ── Final Optical Composite ──────────────────────────────────────
    // 1. Start with glass body darkness
    vec3 finalColor = glassBody;

    // 2. Add floating inner energy core (refracted through glass)
    finalColor += interior * (1.0 - fresnel * 0.4);

    // 3. Add studio softbox & window reflections on top of glass
    finalColor += studioRefl * 0.85;

    // 4. Add glass rim fresnel + sub-rim
    finalColor += glassEdge + rimGlow * subRim;

    // Precision Anti-Aliased Outer Glass Boundary
    float edgeAA = smoothstep(R_OUTER, R_OUTER - 0.005, dist);

    gl_FragColor = vec4(finalColor * edgeAA, edgeAA);
}
`;

// ── Orb Controller Class ────────────────────────────────────────────
export class Orb {

    /** @param {string} containerId – id of the DOM element to render into */
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error(`#${containerId} not found`);

        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.style.display = 'block';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.container.innerHTML = '';
        this.container.appendChild(this.canvas);

        const gl = this.canvas.getContext('webgl', {
            alpha: true,
            antialias: true,
            premultipliedAlpha: false,
            powerPreference: 'high-performance',
        });
        if (!gl) throw new Error('WebGL not supported');
        this.gl = gl;

        // Current & target state values (interpolated smoothly)
        const idle = STATES.idle;
        this.cur = {
            core:    [...idle.coreColor],
            glow:    [...idle.glowColor],
            rim:     [...idle.rimColor],
            spin:    idle.spinSpeed,
            pFreq:   idle.pulseFreq,
            pAmp:    idle.pulseAmp,
            density: idle.armDensity,
            scale:   idle.coreScale,
            glimmer: idle.glimmerAlpha,
        };
        this.target = {
            core:    [...idle.coreColor],
            glow:    [...idle.glowColor],
            rim:     [...idle.rimColor],
            spin:    idle.spinSpeed,
            pFreq:   idle.pulseFreq,
            pAmp:    idle.pulseAmp,
            density: idle.armDensity,
            scale:   idle.coreScale,
            glimmer: idle.glimmerAlpha,
        };

        this._initWebGL();
        this._onResize = this._onResize.bind(this);
        window.addEventListener('resize', this._onResize);
        this._onResize();

        this.startTime = performance.now();
        this.lastTime = performance.now();
        this._animate = this._animate.bind(this);
        requestAnimationFrame(this._animate);
    }

    /* ── Public API ─────────────────────────────────────────────── */

    setState(name) {
        const s = STATES[name];
        if (!s) return;
        this.target.core    = [...s.coreColor];
        this.target.glow    = [...s.glowColor];
        this.target.rim     = [...s.rimColor];
        this.target.spin    = s.spinSpeed;
        this.target.pFreq   = s.pulseFreq;
        this.target.pAmp    = s.pulseAmp;
        this.target.density = s.armDensity;
        this.target.scale   = s.coreScale;
        this.target.glimmer = s.glimmerAlpha;
    }

    /** Returns current primary colour as CSS rgb() string */
    getCSSColor() {
        const r = Math.round(this.cur.glow[0] * 255);
        const g = Math.round(this.cur.glow[1] * 255);
        const b = Math.round(this.cur.glow[2] * 255);
        return `rgb(${r}, ${g}, ${b})`;
    }

    /* ── WebGL Setup ────────────────────────────────────────────── */

    _initWebGL() {
        const gl = this.gl;

        const vert = this._compileShader(gl.VERTEX_SHADER, VERT_SRC);
        const frag = this._compileShader(gl.FRAGMENT_SHADER, FRAG_SRC);

        const prog = gl.createProgram();
        gl.attachShader(prog, vert);
        gl.attachShader(prog, frag);
        gl.linkProgram(prog);

        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
            throw new Error('Shader link failed: ' + gl.getProgramInfoLog(prog));
        }
        this.program = prog;
        gl.useProgram(prog);

        // Full-screen quad
        const quad = new Float32Array([
            -1, -1,
             1, -1,
            -1,  1,
            -1,  1,
             1, -1,
             1,  1,
        ]);

        const buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, quad, gl.STATIC_DRAW);

        const posLoc = gl.getAttribLocation(prog, 'a_position');
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

        // Cache uniform locations
        this.uLoc = {
            resolution:   gl.getUniformLocation(prog, 'u_resolution'),
            time:         gl.getUniformLocation(prog, 'u_time'),
            coreColor:    gl.getUniformLocation(prog, 'u_coreColor'),
            glowColor:    gl.getUniformLocation(prog, 'u_glowColor'),
            rimColor:     gl.getUniformLocation(prog, 'u_rimColor'),
            spinSpeed:    gl.getUniformLocation(prog, 'u_spinSpeed'),
            pulseFreq:    gl.getUniformLocation(prog, 'u_pulseFreq'),
            pulseAmp:     gl.getUniformLocation(prog, 'u_pulseAmp'),
            armDensity:   gl.getUniformLocation(prog, 'u_armDensity'),
            coreScale:    gl.getUniformLocation(prog, 'u_coreScale'),
            glimmerAlpha: gl.getUniformLocation(prog, 'u_glimmerAlpha'),
        };

        // Enable alpha blending
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }

    _compileShader(type, src) {
        const gl = this.gl;
        const s = gl.createShader(type);
        gl.shaderSource(s, src);
        gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
            const err = gl.getShaderInfoLog(s);
            gl.deleteShader(s);
            throw new Error('Shader compile error: ' + err);
        }
        return s;
    }

    /* ── Animation Loop ─────────────────────────────────────────── */

    _animate(now) {
        requestAnimationFrame(this._animate);

        const dt = Math.min((now - this.lastTime) / 1000, 0.1);
        this.lastTime = now;
        const totalTime = (now - this.startTime) / 1000;

        const gl = this.gl;
        const lf = 1.0 - Math.pow(0.02, dt); // Smooth cinematic lerp

        // Interpolate state values
        for (let i = 0; i < 3; i++) {
            this.cur.core[i] += (this.target.core[i] - this.cur.core[i]) * lf;
            this.cur.glow[i] += (this.target.glow[i] - this.cur.glow[i]) * lf;
            this.cur.rim[i]  += (this.target.rim[i]  - this.cur.rim[i])  * lf;
        }
        this.cur.spin    += (this.target.spin    - this.cur.spin)    * lf;
        this.cur.pFreq   += (this.target.pFreq   - this.cur.pFreq)   * lf;
        this.cur.pAmp    += (this.target.pAmp    - this.cur.pAmp)    * lf;
        this.cur.density += (this.target.density - this.cur.density) * lf;
        this.cur.scale   += (this.target.scale   - this.cur.scale)   * lf;
        this.cur.glimmer += (this.target.glimmer - this.cur.glimmer) * lf;

        gl.viewport(0, 0, this.canvas.width, this.canvas.height);
        gl.clearColor(0.0, 0.0, 0.0, 0.0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        gl.useProgram(this.program);

        gl.uniform2f(this.uLoc.resolution, this.canvas.width, this.canvas.height);
        gl.uniform1f(this.uLoc.time, totalTime);
        gl.uniform3fv(this.uLoc.coreColor, this.cur.core);
        gl.uniform3fv(this.uLoc.glowColor, this.cur.glow);
        gl.uniform3fv(this.uLoc.rimColor, this.cur.rim);
        gl.uniform1f(this.uLoc.spinSpeed, this.cur.spin);
        gl.uniform1f(this.uLoc.pulseFreq, this.cur.pFreq);
        gl.uniform1f(this.uLoc.pulseAmp, this.cur.pAmp);
        gl.uniform1f(this.uLoc.armDensity, this.cur.density);
        gl.uniform1f(this.uLoc.coreScale, this.cur.scale);
        gl.uniform1f(this.uLoc.glimmerAlpha, this.cur.glimmer);

        gl.drawArrays(gl.TRIANGLES, 0, 6);
    }

    _onResize() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const w = this.container.clientWidth || 300;
        const h = this.container.clientHeight || 300;

        this.canvas.width = w * dpr;
        this.canvas.height = h * dpr;
    }
}
