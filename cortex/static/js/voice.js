/**
 * Cortex Live Voice Engine
 * Gapless Web Audio API Queue + Neural Voice Streaming + STT
 */

export class GaplessVoiceQueue {
    constructor(callbacks = {}) {
        this.ctx = null;
        this.nextStartTime = 0;
        this.activeSources = [];
        this.onSpeakingStateChange = callbacks.onSpeakingStateChange || (() => {});
        this.onFinishedAll = callbacks.onFinishedAll || (() => {});
        this.isPlaying = false;
        this.cooldownTimer = null;
    }

    _ensureAudioContext() {
        if (!this.ctx || this.ctx.state === 'closed') {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    async enqueueAudioBase64(base64Data, text = "", isFinal = false) {
        if (!base64Data) return;
        this._ensureAudioContext();

        clearTimeout(this.cooldownTimer);

        let rawBase64 = base64Data;
        if (rawBase64.includes(',')) {
            rawBase64 = rawBase64.split(',')[1];
        }

        const binary = atob(rawBase64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }

        try {
            const audioBuffer = await this.ctx.decodeAudioData(bytes.buffer.slice(0));
            const source = this.ctx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.ctx.destination);

            const now = this.ctx.currentTime;
            const startTime = Math.max(now, this.nextStartTime);
            source.start(startTime);

            this.nextStartTime = startTime + audioBuffer.duration;
            this.activeSources.push(source);

            if (!this.isPlaying) {
                this.isPlaying = true;
                this.onSpeakingStateChange(true);
            }

            source.onended = () => {
                const idx = this.activeSources.indexOf(source);
                if (idx > -1) this.activeSources.splice(idx, 1);

                if (this.activeSources.length === 0) {
                    this.nextStartTime = 0;
                    this.cooldownTimer = setTimeout(() => {
                        this.isPlaying = false;
                        this.onSpeakingStateChange(false);
                        this.onFinishedAll();
                    }, 400);
                }
            };
        } catch (e) {
            console.error("[GaplessVoiceQueue] Audio decoding error:", e);
        }
    }

    bargeIn() {
        clearTimeout(this.cooldownTimer);
        for (const source of this.activeSources) {
            try {
                source.stop(0);
            } catch (e) {}
        }
        this.activeSources = [];
        this.nextStartTime = 0;
        if (this.isPlaying) {
            this.isPlaying = false;
            this.onSpeakingStateChange(false);
            this.onFinishedAll();
        }
    }
}

export class LiveVoiceEngine {
    constructor(callbacks = {}) {
        this.onVolumeChange        = callbacks.onVolumeChange || (() => {});
        this.onStateChange         = callbacks.onStateChange || (() => {});
        this.onSpeechRecognized    = callbacks.onSpeechRecognized || (() => {});
        this.onSpeakingStateChange = callbacks.onSpeakingStateChange || (() => {});

        this.audioCtx = null;
        this.analyser = null;
        this.microphone = null;
        this.stream = null;

        this.isActive = false;
        this.isMuted = false;
        this.isSpeaking = false;
        this.isSimulated = false;

        this.recognition = null;
        this.currentAudio = null;
        this.lastSpokenText = "";
        this.cooldownTimer = null;

        this.voiceQueue = new GaplessVoiceQueue({
            onSpeakingStateChange: (speaking) => {
                this.isSpeaking = speaking;
                this.onSpeakingStateChange(speaking);
            },
            onFinishedAll: () => {
                this.isSpeaking = false;
                if (this.isActive && !this.isMuted && this.recognition) {
                    try { this.recognition.start(); } catch (e) {}
                }
            }
        });

        this.canvas = document.getElementById('live-audio-canvas');
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;

        this.dataArray = null;
        this.bufferLength = 32;
        this.animFrameId = null;
        this.simTime = 0;

        this._renderWave = this._renderWave.bind(this);
        this._initSpeechRecognition();
    }

    _initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
            try {
                this.recognition = new SpeechRec();
                this.recognition.continuous = true;
                this.recognition.interimResults = false;
                this.recognition.lang = 'en-US';

                this.recognition.onresult = (event) => {
                    // If Cortex is currently speaking or in post-speech echo cooldown, ignore all audio
                    if (this.isSpeaking || this.isMuted) {
                        console.log('[VoiceEngine] Echo suppressed (Cortex is speaking)');
                        return;
                    }

                    const lastResult = event.results[event.results.length - 1];
                    if (lastResult && lastResult.isFinal) {
                        const transcript = lastResult[0].transcript.trim();
                        if (!transcript) return;

                        // Anti-Echo filter: verify transcript is not an echo of what Cortex just said
                        const cleanT = transcript.toLowerCase();
                        if (this.lastSpokenText && (
                            this.lastSpokenText.includes(cleanT) || 
                            cleanT.includes(this.lastSpokenText) ||
                            this._similarity(cleanT, this.lastSpokenText) > 0.6
                        )) {
                            console.log('[VoiceEngine] Echo suppressed (matches last assistant speech):', transcript);
                            return;
                        }

                        console.log('[VoiceEngine] Valid user voice command:', transcript);
                        this.onSpeechRecognized(transcript);
                    }
                };

                this.recognition.onerror = (err) => {
                    if (err.error !== 'no-speech' && err.error !== 'aborted') {
                        console.warn('[VoiceEngine] Speech recognition error:', err.error);
                    }
                };

                this.recognition.onend = () => {
                    // Only auto-restart if active, not muted, and not currently speaking
                    if (this.isActive && !this.isMuted && !this.isSpeaking) {
                        try {
                            this.recognition.start();
                        } catch (e) {}
                    }
                };
            } catch (e) {
                console.warn('[VoiceEngine] Web Speech init failed:', e);
            }
        }
    }

    _similarity(s1, s2) {
        if (!s1 || !s2) return 0;
        const w1 = new Set(s1.split(/\s+/));
        const w2 = new Set(s2.split(/\s+/));
        let common = 0;
        for (const w of w1) {
            if (w2.has(w)) common++;
        }
        return (2.0 * common) / (w1.size + w2.size);
    }

    async start() {
        if (this.isActive) return;

        let hardwareSuccess = false;

        try {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                this.analyser = this.audioCtx.createAnalyser();
                this.analyser.fftSize = 64;
                this.analyser.smoothingTimeConstant = 0.75;

                this.microphone = this.audioCtx.createMediaStreamSource(this.stream);
                this.microphone.connect(this.analyser);

                this.bufferLength = this.analyser.frequencyBinCount;
                this.dataArray = new Uint8Array(this.bufferLength);
                this.isSimulated = false;
                hardwareSuccess = true;
            }
        } catch (err) {
            console.warn('[VoiceEngine] Hardware microphone not accessible:', err.name, err.message);
            hardwareSuccess = false;
        }

        if (!hardwareSuccess) {
            this.isSimulated = true;
            this.bufferLength = 32;
            this.dataArray = new Uint8Array(this.bufferLength);
        }

        this.isActive = true;
        this.onStateChange(true, this.isSimulated ? 'simulated' : null);

        if (this.recognition && !this.isMuted && !this.isSpeaking) {
            try {
                this.recognition.start();
            } catch (e) {}
        }

        if (this.canvas) {
            this.canvas.width = 300;
            this.canvas.height = 28;
        }

        this._renderWave();
    }

    stop() {
        if (!this.isActive) return;

        clearTimeout(this.cooldownTimer);

        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }

        if (this.recognition) {
            try {
                this.recognition.abort();
            } catch (e) {}
        }

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }

        if (this.audioCtx && this.audioCtx.state !== 'closed') {
            this.audioCtx.close();
            this.audioCtx = null;
        }

        this.isActive = false;
        this.isSpeaking = false;
        this.isSimulated = false;
        this.onStateChange(false);

        if (this.ctx && this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        if (this.stream) {
            this.stream.getAudioTracks().forEach(track => {
                track.enabled = !this.isMuted;
            });
        }
        if (this.recognition) {
            if (this.isMuted) {
                try { this.recognition.abort(); } catch (e) {}
            } else if (this.isActive && !this.isSpeaking) {
                try { this.recognition.start(); } catch (e) {}
            }
        }
        return this.isMuted;
    }

    enqueueAudioChunk(audioDataUri, text = "", isFinal = false) {
        if (!audioDataUri) return;
        this.lastSpokenText = (text || "").toLowerCase().trim();
        if (this.recognition) {
            try { this.recognition.abort(); } catch (e) {}
        }
        this.voiceQueue.enqueueAudioBase64(audioDataUri, text, isFinal);
    }

    bargeIn() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
        this.voiceQueue.bargeIn();
    }

    async playAudio(audioDataUri, text = "") {
        this.enqueueAudioChunk(audioDataUri, text, true);
    }

    _renderWave() {
        if (!this.isActive) return;
        this.animFrameId = requestAnimationFrame(this._renderWave);

        this.simTime += 0.05;
        let avgVol = 0;

        if (this.isMuted) {
            avgVol = 0;
            if (this.dataArray) this.dataArray.fill(0);
        } else if (this.isSpeaking) {
            const speechPulse = 0.5 + Math.abs(Math.sin(this.simTime * 4.0)) * 0.5;
            avgVol = speechPulse * 0.85;

            for (let i = 0; i < this.bufferLength; i++) {
                const wave = Math.sin(this.simTime * 5.0 + i * 0.4) * Math.cos(this.simTime * 2.0);
                this.dataArray[i] = Math.max(15, Math.round(speechPulse * Math.abs(wave) * 255));
            }
        } else if (this.isSimulated) {
            const speechPulse = Math.max(0, Math.sin(this.simTime * 2.2) * Math.sin(this.simTime * 0.8));
            avgVol = speechPulse * 0.7;

            for (let i = 0; i < this.bufferLength; i++) {
                const wave = Math.sin(this.simTime * 4.0 + i * 0.35) * Math.cos(this.simTime * 1.5);
                this.dataArray[i] = Math.max(8, Math.round(speechPulse * Math.abs(wave) * 230));
            }
        } else if (this.analyser) {
            this.analyser.getByteFrequencyData(this.dataArray);
            let sum = 0;
            for (let i = 0; i < this.bufferLength; i++) {
                sum += this.dataArray[i];
            }
            avgVol = (sum / this.bufferLength) / 255;
        }

        this.onVolumeChange(avgVol);

        if (this.ctx && this.canvas) {
            const ctx = this.ctx;
            const w = this.canvas.width;
            const h = this.canvas.height;
            ctx.clearRect(0, 0, w, h);

            const accentColor = getComputedStyle(document.documentElement).getPropertyValue('--theme-accent').trim() || '#4ade80';

            const numBars = 24;
            const barWidth = 3;
            const gap = (w - (numBars * barWidth)) / (numBars - 1);

            for (let i = 0; i < numBars; i++) {
                const val = (this.isMuted) ? 0 : (this.dataArray[i % this.bufferLength] || 0);
                const normalized = (val / 255);
                const barHeight = Math.max(3, normalized * h * 0.95);
                const x = i * (barWidth + gap);
                const y = (h - barHeight) / 2;

                const grad = ctx.createLinearGradient(x, y, x, y + barHeight);
                grad.addColorStop(0.0, '#ffffff');
                grad.addColorStop(0.35, accentColor);
                grad.addColorStop(1.0, accentColor);

                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.roundRect(x, y, barWidth, barHeight, 2);
                ctx.fill();
            }
        }
    }
}
