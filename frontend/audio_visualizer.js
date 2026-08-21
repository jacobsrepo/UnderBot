/**
 * Audio Spectrum Visualizer - Isolated Read-Only Analyzer (No Audio Loopback)
 */

class AudioSpectrumVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.audioCtx = null;
        this.analyser = null;
        this.source = null;
        this.dataArray = null;
        this.bufferLength = 0;
        this.animationId = null;
        this.isActive = false;

        if (this.canvas) {
            this.initCanvasSize();
            window.addEventListener('resize', () => this.initCanvasSize());
            this.renderIdleWaveform();
        }
    }

    initCanvasSize() {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = (rect.width || 110) * (window.devicePixelRatio || 1);
        this.canvas.height = (rect.height || 20) * (window.devicePixelRatio || 1);
    }

    ensureAudioContext() {
        if (!this.audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            this.audioCtx = new AudioContextClass();
            this.analyser = this.audioCtx.createAnalyser();
            this.analyser.fftSize = 64;
            this.analyser.smoothingTimeConstant = 0.8;
            this.bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);
            // CRITICAL: NEVER connect this.analyser to this.audioCtx.destination!
            // Keeping it isolated ensures microphone audio is never routed to the speakers.
        }
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
    }

    connectMediaStream(stream) {
        if (!stream) return;
        this.ensureAudioContext();
        try {
            if (this.source) {
                try { this.source.disconnect(); } catch (e) {}
            }
            this.source = this.audioCtx.createMediaStreamSource(stream);
            // Connect mic source ONLY to analyser (NOT to audioCtx.destination)
            this.source.connect(this.analyser);
            this.isActive = true;
            this.startLoop();
        } catch (e) {
            console.warn('[Visualizer] Stream connection error:', e);
        }
    }

    connectAudioElement(audioElement) {
        // Audio element is played natively by browser HTML5 <audio> tag.
        // We do not route mic or HTML5 audio through Web Audio Graph destination to avoid loops.
        this.renderIdleWaveform();
    }

    startLoop() {
        if (this.animationId) cancelAnimationFrame(this.animationId);

        const draw = () => {
            this.animationId = requestAnimationFrame(draw);

            if (!this.analyser || !this.isActive || !this.ctx) {
                this.renderIdleWaveform();
                return;
            }

            this.analyser.getByteFrequencyData(this.dataArray);

            const width = this.canvas.width;
            const height = this.canvas.height;
            this.ctx.clearRect(0, 0, width, height);

            const count = 14;
            const barWidth = (width / count) * 0.55;
            const gap = (width - (count * barWidth)) / (count - 1);

            for (let i = 0; i < count; i++) {
                const idx = Math.floor((i / count) * this.bufferLength);
                const val = this.dataArray[idx] || 0;
                const percent = val / 255;
                const barHeight = Math.max(3, percent * height * 0.85);

                const x = i * (barWidth + gap);
                const y = (height - barHeight) / 2;

                this.ctx.fillStyle = percent > 0.15 ? '#10b981' : '#3b82f6';
                this.ctx.beginPath();
                this.ctx.roundRect(x, y, barWidth, barHeight, 2);
                this.ctx.fill();
            }
        };

        draw();
    }

    setIdle() {
        this.isActive = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        this.renderIdleWaveform();
    }

    renderIdleWaveform() {
        if (!this.ctx || !this.canvas) return;
        const width = this.canvas.width;
        const height = this.canvas.height;
        this.ctx.clearRect(0, 0, width, height);

        const count = 14;
        const barWidth = (width / count) * 0.55;
        const gap = (width - (count * barWidth)) / (count - 1);

        for (let i = 0; i < count; i++) {
            const barHeight = 3;
            const x = i * (barWidth + gap);
            const y = (height - barHeight) / 2;

            this.ctx.fillStyle = '#2f323c';
            this.ctx.beginPath();
            this.ctx.roundRect(x, y, barWidth, barHeight, 1);
            this.ctx.fill();
        }
    }
}
