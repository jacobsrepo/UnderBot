/**
 * Minimalist Audio Wave Visualizer
 */

class AudioSpectrumVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.audioCtx = null;
        this.analyser = null;
        this.source = null;
        this.dataArray = null;
        this.bufferLength = 0;
        this.animationId = null;
        this.isActive = false;

        this.initCanvasSize();
        window.addEventListener('resize', () => this.initCanvasSize());
        this.renderIdleWaveform();
    }

    initCanvasSize() {
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = (rect.width || 140) * (window.devicePixelRatio || 1);
        this.canvas.height = (rect.height || 24) * (window.devicePixelRatio || 1);
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
        }
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
    }

    connectMediaStream(stream) {
        this.ensureAudioContext();
        try {
            if (this.source) this.source.disconnect();
            this.source = this.audioCtx.createMediaStreamSource(stream);
            this.source.connect(this.analyser);
            this.isActive = true;
            this.startLoop();
        } catch (e) {
            console.warn('[Visualizer] Stream error:', e);
        }
    }

    connectAudioElement(audioElement) {
        this.ensureAudioContext();
        try {
            if (!audioElement._hasSource) {
                const audioSource = this.audioCtx.createMediaElementSource(audioElement);
                audioSource.connect(this.analyser);
                this.analyser.connect(this.audioCtx.destination);
                audioElement._hasSource = true;
            }
            this.isActive = true;
            this.startLoop();
        } catch (e) {
            console.warn('[Visualizer] Audio element error:', e);
        }
    }

    startLoop() {
        if (this.animationId) cancelAnimationFrame(this.animationId);

        const draw = () => {
            this.animationId = requestAnimationFrame(draw);

            if (!this.analyser || !this.isActive) {
                this.renderIdleWaveform();
                return;
            }

            this.analyser.getByteFrequencyData(this.dataArray);

            const width = this.canvas.width;
            const height = this.canvas.height;
            this.ctx.clearRect(0, 0, width, height);

            const count = 16;
            const barWidth = (width / count) * 0.6;
            const gap = (width - (count * barWidth)) / (count - 1);

            for (let i = 0; i < count; i++) {
                const idx = Math.floor((i / count) * this.bufferLength);
                const val = this.dataArray[idx] || 0;
                const percent = val / 255;
                const barHeight = Math.max(3, percent * height * 0.85);

                const x = i * (barWidth + gap);
                const y = (height - barHeight) / 2;

                this.ctx.fillStyle = '#3b82f6';
                this.ctx.beginPath();
                this.ctx.roundRect(x, y, barWidth, barHeight, 2);
                this.ctx.fill();
            }
        };

        draw();
    }

    renderIdleWaveform() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        this.ctx.clearRect(0, 0, width, height);

        const count = 16;
        const barWidth = (width / count) * 0.6;
        const gap = (width - (count * barWidth)) / (count - 1);

        for (let i = 0; i < count; i++) {
            const x = i * (barWidth + gap);
            const barHeight = 3;
            const y = (height - barHeight) / 2;

            this.ctx.fillStyle = '#1e2433';
            this.ctx.beginPath();
            this.ctx.roundRect(x, y, barWidth, barHeight, 2);
            this.ctx.fill();
        }
    }

    setIdle() {
        this.isActive = false;
    }
}

window.AudioSpectrumVisualizer = AudioSpectrumVisualizer;
