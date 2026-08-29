/**
 * Cortex Animated Robotic Eye Face — Hardware Native Vector Engine
 */

export const SCREEN_THEMES = {
    idle: {
        screenBg:    '#4a5f3a',  // Olive sage green
        accentColor: '#86efac',  // Soft sage green
        glowColor:   'rgba(134, 239, 172, 0.4)',
        label:       'Ready',
        subtext:     'Standing by',
    },
    listening: {
        screenBg:    '#2d4c63',  // Oceanic slate blue
        accentColor: '#38bdf8',  // Cyan blue
        glowColor:   'rgba(56, 189, 248, 0.45)',
        label:       'Listening…',
        subtext:     'I am all ears',
    },
    thinking: {
        screenBg:    '#634f2d',  // Warm amber
        accentColor: '#fbbf24',  // Gold amber
        glowColor:   'rgba(251, 191, 36, 0.45)',
        label:       'Thinking…',
        subtext:     'Analyzing neural stream',
    },
    speaking: {
        screenBg:    '#2d6349',  // Aquatic jade emerald
        accentColor: '#4ade80',  // Vivid emerald
        glowColor:   'rgba(74, 222, 128, 0.45)',
        label:       'Speaking…',
        subtext:     'PocketTTS audio active',
    },
    seeing: {
        screenBg:    '#4b3163',  // Optical violet
        accentColor: '#c084fc',  // Electric violet
        glowColor:   'rgba(192, 132, 252, 0.45)',
        label:       'Seeing…',
        subtext:     'Inspecting webcam feed',
    },
    programming: {
        screenBg:    '#63392d',  // Terracotta copper
        accentColor: '#fb923c',  // Warm orange
        glowColor:   'rgba(251, 146, 60, 0.45)',
        label:       'Controlling Pins',
        subtext:     'Arduino Nano execution',
    },
    error: {
        screenBg:    '#632626',  // Alert crimson
        accentColor: '#f87171',  // Bright coral red
        glowColor:   'rgba(248, 113, 113, 0.45)',
        label:       'Error',
        subtext:     'Command failed',
    },
};

export class RobotFace {
    constructor() {
        this.dom = {
            faceHardware: document.getElementById('robot-face-hardware'),
            screen:       document.getElementById('robot-screen'),
            eyeLeft:      document.getElementById('eye-left'),
            eyeRight:     document.getElementById('eye-right'),
        };

        this.currentState = 'idle';

        // Mouse gaze tracking
        this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
        this._bindMouse();

        // Eye state variables
        this.eyes = {
            spacing: 48,
            left:  { x: -48, y: 0, scaleX: 1, scaleY: 1, rot: 0 },
            right: { x:  48, y: 0, scaleX: 1, scaleY: 1, rot: 0 },
            blink: 1.0,
            targetBlink: 1.0,
            blinkSquash: 1.0,
            audioVolume: 0.0,
        };

        // Timers
        this.lastBlinkTime = performance.now();
        this.nextBlinkInterval = 2800 + Math.random() * 2500;
        this.time = 0;
        this.lastTime = performance.now();

        this._animate = this._animate.bind(this);
        requestAnimationFrame(this._animate);
    }

    setVoiceVolume(vol) {
        this.eyes.audioVolume = vol;
    }

    setState(stateName) {
        const theme = SCREEN_THEMES[stateName];
        if (!theme) return;
        this.currentState = stateName;
        if (this.dom.faceHardware) {
            this.dom.faceHardware.style.setProperty('--screen-color', theme.screenBg);
            this.dom.faceHardware.style.background = theme.screenBg;
        }

        // Propagate theme variables globally to root for synchronized UI coloring
        document.documentElement.style.setProperty('--theme-accent', theme.accentColor);
        document.documentElement.style.setProperty('--theme-glow', theme.glowColor);
        document.documentElement.style.setProperty('--theme-bg', theme.screenBg);
    }

    getStateInfo(stateName) {
        return SCREEN_THEMES[stateName] || SCREEN_THEMES.idle;
    }

    _bindMouse() {
        window.addEventListener('mousemove', (e) => {
            const rect = this.dom.faceHardware?.getBoundingClientRect() || { left: window.innerWidth / 2, top: window.innerHeight / 2, width: 280, height: 280 };
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = (e.clientX - cx) / (window.innerWidth / 2);
            const dy = (e.clientY - cy) / (window.innerHeight / 2);
            this.mouse.targetX = Math.max(-1, Math.min(1, dx)) * 16;
            this.mouse.targetY = Math.max(-1, Math.min(1, dy)) * 12;
        });
    }

    _animate(now) {
        requestAnimationFrame(this._animate);

        const dt = Math.min((now - this.lastTime) / 1000, 0.1);
        this.lastTime = now;
        this.time += dt;

        // Smooth physics spring lerp
        const lf = 1.0 - Math.pow(0.015, dt);
        this.mouse.x += (this.mouse.targetX - this.mouse.x) * lf;
        this.mouse.y += (this.mouse.targetY - this.mouse.y) * lf;

        // Natural Organic Blinking with Elastic Squash & Stretch
        if (now - this.lastBlinkTime > this.nextBlinkInterval) {
            this.eyes.targetBlink = 0.04;
            this.eyes.blinkSquash = 1.20;
            this.lastBlinkTime = now;
            this.nextBlinkInterval = 2500 + Math.random() * 3500;

            setTimeout(() => {
                this.eyes.targetBlink = 1.0;
                this.eyes.blinkSquash = 1.0;
            }, 110);
        }

        this.eyes.blink += (this.eyes.targetBlink - this.eyes.blink) * (lf * 2.8);

        this._updateExpression(now, lf);
        this._render();
    }

    _updateExpression(now, lf) {
        const left = this.eyes.left;
        const right = this.eyes.right;
        const spacing = this.eyes.spacing;

        switch (this.currentState) {
            case 'idle': {
                const breathe = Math.sin(this.time * 2.2) * 1.8;
                left.x  = -spacing + this.mouse.x;
                left.y  = breathe + this.mouse.y;
                right.x =  spacing + this.mouse.x;
                right.y = breathe + this.mouse.y;

                left.scaleX  = this.eyes.blinkSquash;
                left.scaleY  = this.eyes.blink;
                right.scaleX = this.eyes.blinkSquash;
                right.scaleY = this.eyes.blink;
                left.rot  = 0;
                right.rot = 0;
                break;
            }

            case 'listening': {
                const attentiveFloat = Math.sin(this.time * 4.0) * 1.5;
                const audioDilation = 1.0 + this.eyes.audioVolume * 0.45;
                left.x  = -spacing + this.mouse.x * 1.15;
                left.y  = -5 + attentiveFloat + this.mouse.y * 1.15;
                right.x =  spacing + this.mouse.x * 1.15;
                right.y = -5 + attentiveFloat + this.mouse.y * 1.15;

                left.scaleX  = 1.15 * this.eyes.blinkSquash * audioDilation;
                left.scaleY  = 1.15 * this.eyes.blink * audioDilation;
                right.scaleX = 1.15 * this.eyes.blinkSquash * audioDilation;
                right.scaleY = 1.15 * this.eyes.blink * audioDilation;
                left.rot  =  0.06;
                right.rot = -0.06;
                break;
            }

            case 'thinking': {
                const glanceFloat = Math.sin(this.time * 2.5) * 2.0;
                left.x  = -spacing - 8 + glanceFloat;
                left.y  = -14;
                right.x =  spacing - 8 + glanceFloat;
                right.y = -14;

                left.scaleX  = 0.95;
                left.scaleY  = 0.72 * this.eyes.blink;
                right.scaleX = 0.95;
                right.scaleY = 0.72 * this.eyes.blink;
                left.rot  = -0.16;
                right.rot = -0.16;
                break;
            }

            case 'speaking': {
                const talkBounce = Math.abs(Math.sin(this.time * 7.5)) * 6.5;
                const talkSquint = (0.75 + 0.25 * Math.sin(this.time * 15.0)) * (1.0 + this.eyes.audioVolume * 0.3);

                left.x  = -spacing + this.mouse.x * 0.4;
                left.y  = -talkBounce;
                right.x =  spacing + this.mouse.x * 0.4;
                right.y = -talkBounce;

                left.scaleX  = 1.08 * (1.0 + this.eyes.audioVolume * 0.2);
                left.scaleY  = talkSquint * this.eyes.blink;
                right.scaleX = 1.08 * (1.0 + this.eyes.audioVolume * 0.2);
                right.scaleY = talkSquint * this.eyes.blink;
                left.rot  =  0.04 * Math.sin(this.time * 7.5);
                right.rot = -0.04 * Math.sin(this.time * 7.5);
                break;
            }

            case 'seeing': {
                const scan = Math.sin(this.time * 4.0) * 6.0;
                left.x  = -spacing + 8 + scan;
                left.y  = 6;
                right.x =  spacing + 8 + scan;
                right.y = 6;

                left.scaleX  = 1.25;
                left.scaleY  = 0.42;
                right.scaleX = 1.25;
                right.scaleY = 0.42;
                left.rot  = 0.08;
                right.rot = 0.08;
                break;
            }

            case 'programming': {
                const pulse = Math.sin(this.time * 5.0) * 1.5;
                left.x  = -spacing;
                left.y  = 2 + pulse;
                right.x =  spacing;
                right.y = 2 + pulse;

                left.scaleX  = 1.12;
                left.scaleY  = 0.85 * this.eyes.blink;
                right.scaleX = 1.12;
                right.scaleY = 0.85 * this.eyes.blink;
                left.rot  =  0.14;
                right.rot = -0.14;
                break;
            }

            case 'error': {
                const shake = Math.sin(this.time * 22.0) * 3.5;
                left.x  = -spacing + shake;
                left.y  = 0;
                right.x =  spacing + shake;
                right.y = 0;

                left.scaleX  = 0.90;
                left.scaleY  = 0.90;
                right.scaleX = 0.90;
                right.scaleY = 0.90;
                left.rot  = -0.28;
                right.rot =  0.28;
                break;
            }
        }
    }

    _render() {
        const l = this.eyes.left;
        const r = this.eyes.right;

        if (this.dom.eyeLeft) {
            this.dom.eyeLeft.style.transform =
                `translate(${l.x.toFixed(1)}px, ${l.y.toFixed(1)}px) rotate(${l.rot.toFixed(2)}rad) scale(${l.scaleX.toFixed(2)}, ${l.scaleY.toFixed(2)})`;
        }

        if (this.dom.eyeRight) {
            this.dom.eyeRight.style.transform =
                `translate(${r.x.toFixed(1)}px, ${r.y.toFixed(1)}px) rotate(${r.rot.toFixed(2)}rad) scale(${r.scaleX.toFixed(2)}, ${r.scaleY.toFixed(2)})`;
        }
    }
}
