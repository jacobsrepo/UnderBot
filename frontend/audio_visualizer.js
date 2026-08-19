/**
 * Real-time Audio Spectrum & Waveform Visualizer
 * Powered by HTML5 Canvas & Web Audio API
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
        this.canvas.width = rect.width * window.devicePixelRatio || 600;
        this.canvas.height = 70 * window.devicePixelRatio || 70;
    }

    ensureAudioContext() {
        if (!this.audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            this.audioCtx = new AudioContextClass();
            this.analyser = this.audioCtx.createAnalyser();
            this.analyser.fftSize = 128;
            this.analyser.smoothingTimeConstant = 0.85;
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
            if (this.source) {
                this.source.disconnect();
            }
            this.source = this.audioCtx.createMediaStreamSource(stream);
            this.source.connect(this.analyser);
            this.isActive = true;
            this.startLoop();
        } catch (e) {
            console.warn('[Visualizer] Error connecting stream:', e);
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
            console.warn('[Visualizer] Error connecting audio element:', e);
        }
    }

    startLoop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }

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

            const barWidth = (width / this.bufferLength) * 1.8;
            let x = 0;

            for (let i = 0; i < this.bufferLength; i++) {
                const val = this.dataArray[i];
                const percent = val / 255;
                const barHeight = percent * height * 0.9;

                // Cyberpunk Neon Gradient
                const gradient = this.ctx.createLinearGradient(0, height, 0, 0);
                gradient.addColorStop(0, 'rgba(0, 243, 255, 0.2)');
                gradient.addColorStop(0.5, 'rgba(0, 243, 255, 0.8)');
                gradient.addColorStop(1, 'rgba(0, 255, 136, 1)');

                this.ctx.fillStyle = gradient;
                this.ctx.shadowBlur = 8;
                this.ctx.shadowColor = 'rgba(0, 243, 255, 0.5)';

                // Draw symmetrical centered bar
                const y = height - barHeight;
                this.ctx.fillRect(x, y, barWidth - 2, barHeight);

                x += barWidth;
            }
        };

        draw();
    }

    renderIdleWaveform() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        this.ctx.clearRect(0, 0, width, height);

        this.ctx.beginPath();
        this.ctx.moveTo(0, height / 2);

        const time = Date.now() * 0.003;
        for (let x = 0; x < width; x += 4) {
            const y = (height / 2) + Math.sin(x * 0.02 + time) * 3;
            this.ctx.lineTo(x, y);
        }

        this.ctx.strokeStyle = 'rgba(0, 243, 255, 0.25)';
        this.ctx.lineWidth = 2;
        this.ctx.shadowBlur = 4;
        this.ctx.shadowColor = 'rgba(0, 243, 255, 0.3)';
        this.ctx.stroke();
    }

    setIdle() {
        this.isActive = false;
    }
}

window.AudioSpectrumVisualizer = AudioSpectrumVisualizer;
