/**
 * Neural Sensory Cortex - Robot Brain Frontend Controller
 */

class RobotBrainCockpit {
    constructor() {
        this.ws = null;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.micStream = null;
        this.visualizer = null;
        this.audioPlayer = document.getElementById('speech-audio-player');
        this.isSpeaking = false;
        this.handsFreeVAD = false;
        this.vadTimer = null;

        // Elements
        this.thoughtStream = document.getElementById('thought-stream');
        this.thinkingHud = document.getElementById('thinking-hud');
        this.thinkingText = document.getElementById('thinking-text');
        this.btnPushToTalk = document.getElementById('btn-push-to-talk');
        this.micLabel = document.getElementById('mic-btn-label');
        this.textInput = document.getElementById('text-prompt-input');
        this.btnSendText = document.getElementById('btn-send-text');
        this.btnSceneScan = document.getElementById('btn-scene-scan');
        this.btnSnapAnalyze = document.getElementById('btn-snap-analyze');
        this.btnClearChat = document.getElementById('btn-clear-chat');
        this.cameraSelect = document.getElementById('camera-select');
        this.btnRefreshCams = document.getElementById('btn-refresh-cams');
        this.selectModel = document.getElementById('select-model');
        this.selectVoice = document.getElementById('select-voice');
        this.autoPerceiveToggle = document.getElementById('auto-perceive-toggle');
        this.reactorState = document.getElementById('reactor-state');
        this.tLatency = document.getElementById('t-latency');
        this.tWsStatus = document.getElementById('t-ws-status');
        this.activeVoicePill = document.getElementById('active-voice-pill');
        this.modelPill = document.getElementById('model-pill');

        this.init();
    }

    init() {
        console.log('[Cockpit] Initializing sensory loop...');
        this.visualizer = new AudioSpectrumVisualizer('audio-spectrum-canvas');
        this.visualizer.connectAudioElement(this.audioPlayer);

        this.initWebSocket();
        this.initMicrophone();
        this.initEventListeners();
        this.fetchCameraDevices();
        this.fetchVoices();
    }

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/live`;
        
        console.log(`[WebSocket] Connecting to ${wsUrl}...`);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('[WebSocket] Connected.');
            this.tWsStatus.textContent = 'ONLINE';
            this.tWsStatus.className = 't-val status-online';
        };

        this.ws.onmessage = (event) => {
            try {
                const data = jsonParseSafe(event.data);
                this.handleServerMessage(data);
            } catch (e) {
                console.error('[WebSocket] Error parsing message:', e);
            }
        };

        this.ws.onclose = () => {
            console.warn('[WebSocket] Disconnected. Reconnecting in 2s...');
            this.tWsStatus.textContent = 'RECONNECTING';
            this.tWsStatus.className = 't-val highlight';
            setTimeout(() => this.initWebSocket(), 2000);
        };

        this.ws.onerror = (err) => {
            console.error('[WebSocket] Error:', err);
        };
    }

    async initMicrophone() {
        try {
            this.micStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            console.log('[Audio] Microphone access granted.');
        } catch (e) {
            console.warn('[Audio] Microphone access denied or not available:', e);
        }
    }

    initEventListeners() {
        // Push-to-Talk Mouse & Touch Events
        this.btnPushToTalk.addEventListener('mousedown', () => this.startRecording());
        this.btnPushToTalk.addEventListener('mouseup', () => this.stopRecording());
        this.btnPushToTalk.addEventListener('mouseleave', () => {
            if (this.isRecording) this.stopRecording();
        });

        this.btnPushToTalk.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        this.btnPushToTalk.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopRecording();
        });

        // Spacebar shortcut for Push-To-Talk
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && document.activeElement !== this.textInput && !this.isRecording) {
                e.preventDefault();
                this.startRecording();
            }
        });
        window.addEventListener('keyup', (e) => {
            if (e.code === 'Space' && this.isRecording) {
                e.preventDefault();
                this.stopRecording();
            }
        });

        // Text input send
        this.btnSendText.addEventListener('click', () => this.sendTextQuery());
        this.textInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.sendTextQuery();
        });

        // Scene Scan button
        this.btnSceneScan.addEventListener('click', () => this.triggerSceneScan());
        this.btnSnapAnalyze.addEventListener('click', () => {
            this.sendTextQuery("Inspect this exact snapshot. What objects, text, or activities do you observe?");
        });

        // Clear Timeline
        this.btnClearChat.addEventListener('click', () => {
            this.thoughtStream.innerHTML = '';
            this.appendMessage('system', 'Timeline cleared. Sensory system standing by.');
        });

        // Camera Switcher
        this.cameraSelect.addEventListener('change', async (e) => {
            const idx = parseInt(e.target.value, 10);
            try {
                await fetch(`/api/camera/select?index=${idx}`, { method: 'POST' });
                // Force refresh image tag
                const camFeed = document.getElementById('live-camera-feed');
                camFeed.src = `/api/camera/stream?t=${Date.now()}`;
            } catch (err) {
                console.error('[Camera] Select error:', err);
            }
        });

        this.btnRefreshCams.addEventListener('click', () => this.fetchCameraDevices());

        // Model Selector
        this.selectModel.addEventListener('change', (e) => {
            const modelName = e.target.value;
            this.modelPill.textContent = modelName.toUpperCase();
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'set_model', model_name: modelName }));
            }
        });

        // Voice Selector
        this.selectVoice.addEventListener('change', (e) => {
            const voiceKey = e.target.value;
            const text = e.target.options[e.target.selectedIndex].text.split('(')[0].trim();
            this.activeVoicePill.textContent = `${text} (Male)`;
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'set_voice', voice_key: voiceKey }));
            }
        });

        // Auto VAD toggle
        this.autoPerceiveToggle.addEventListener('change', (e) => {
            this.handsFreeVAD = e.target.checked;
            if (this.handsFreeVAD) {
                this.appendMessage('system', 'Autonomous hands-free voice detection active.');
            }
        });
    }

    startRecording() {
        if (!this.micStream) {
            this.appendMessage('system', 'Microphone stream not accessible. Please grant mic permission in your browser.');
            return;
        }

        if (this.isRecording) return;

        this.isRecording = true;
        this.audioChunks = [];
        this.btnPushToTalk.classList.add('recording');
        this.micLabel.textContent = 'LISTENING... (RELEASE TO SEND)';
        this.reactorState.textContent = 'LISTENING';
        this.reactorState.className = 'reactor-state active';

        // Connect mic stream to visualizer
        this.visualizer.connectMediaStream(this.micStream);

        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
        this.mediaRecorder = new MediaRecorder(this.micStream, { mimeType });

        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
                this.audioChunks.push(e.data);
            }
        };

        this.mediaRecorder.onstop = () => {
            this.processRecordedAudio();
        };

        this.mediaRecorder.start();
    }

    stopRecording() {
        if (!this.isRecording) return;
        this.isRecording = false;
        this.btnPushToTalk.classList.remove('recording');
        this.micLabel.textContent = 'HOLD TO SPEAK';
        this.reactorState.textContent = 'PROCESSING';

        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
    }

    async processRecordedAudio() {
        if (this.audioChunks.length === 0) return;

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.showThinking('Transcribing voice input with Faster-Whisper...');

        // Convert blob to base64
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = () => {
            const base64Audio = reader.result.split(',')[1];
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'audio_query',
                    audio_base64: base64Audio,
                    format: 'webm'
                }));
            }
        };
    }

    sendTextQuery(overrideText = null) {
        const text = overrideText || this.textInput.value.trim();
        if (!text) return;

        if (!overrideText) {
            this.textInput.value = '';
        }

        this.appendMessage('user', text);
        this.showThinking('Qwen-VL analyzing scene & synthesizing response...');

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'text_query',
                text: text
            }));
        }
    }

    triggerSceneScan() {
        this.appendMessage('user', '🔍 [Environmental Scan Requested]');
        this.showThinking('Scanning optical feed and assessing environment...');

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'scene_scan'
            }));
        }
    }

    handleServerMessage(data) {
        if (!data || !data.type) return;

        switch (data.type) {
            case 'handshake':
                console.log('[Server Handshake]', data);
                if (data.system && data.system.selected_model) {
                    this.selectModel.value = data.system.selected_model;
                    this.modelPill.textContent = data.system.selected_model.toUpperCase();
                }
                break;

            case 'status_update':
                if (data.state === 'thinking') {
                    this.showThinking('Vision Cortex reasoning on camera feed...');
                } else if (data.state === 'transcribing') {
                    this.showThinking('Transcribing speech...');
                } else if (data.state === 'idle') {
                    this.hideThinking();
                }
                break;

            case 'stt_result':
                if (data.text) {
                    this.appendMessage('user', data.text);
                }
                break;

            case 'brain_response':
            case 'scene_briefing':
                this.hideThinking();
                const reply = data.response || 'No visual response received.';
                const tokensSec = data.tokens_per_sec ? `${data.tokens_per_sec} tok/s` : null;
                const latency = data.latency_seconds ? `${data.latency_seconds}s` : null;

                if (data.latency_seconds) {
                    this.tLatency.textContent = `${Math.round(data.latency_seconds * 1000)} ms`;
                }

                this.appendMessage('assistant', reply, {
                    tokensSec,
                    latency,
                    speechData: data.speech
                });

                // Auto play male voice speech
                if (data.speech && data.speech.audio_base64) {
                    this.playSpeechAudio(data.speech.audio_base64);
                }
                break;

            case 'voice_updated':
                console.log(`[Voice Updated] ${data.voice_key}`);
                break;

            case 'model_updated':
                console.log(`[Model Updated] ${data.model_name}`);
                break;
        }
    }

    appendMessage(role, text, meta = {}) {
        const card = document.createElement('div');
        card.className = `message-card ${role}-card`;

        const header = document.createElement('div');
        header.className = 'msg-header';

        const author = document.createElement('span');
        author.className = 'msg-author';
        author.textContent = role === 'user' ? 'OPERATOR (YOU)' : (role === 'assistant' ? 'QWEN-VL COGNITIVE CORTEX' : 'SYSTEM');

        header.appendChild(author);

        if (meta.tokensSec || meta.latency) {
            const metrics = document.createElement('div');
            metrics.className = 'msg-metrics';

            if (meta.tokensSec) {
                const tag1 = document.createElement('span');
                tag1.className = 'metric-tag';
                tag1.textContent = meta.tokensSec;
                metrics.appendChild(tag1);
            }
            if (meta.latency) {
                const tag2 = document.createElement('span');
                tag2.className = 'metric-tag';
                tag2.textContent = meta.latency;
                metrics.appendChild(tag2);
            }
            if (meta.speechData && meta.speechData.audio_base64) {
                const playBtn = document.createElement('button');
                playBtn.className = 'msg-play-btn';
                playBtn.title = 'Replay Voice';
                playBtn.textContent = '🔊';
                playBtn.onclick = () => this.playSpeechAudio(meta.speechData.audio_base64);
                metrics.appendChild(playBtn);
            }
            header.appendChild(metrics);
        }

        const body = document.createElement('div');
        body.className = 'msg-body';
        body.textContent = text;

        card.appendChild(header);
        card.appendChild(body);

        this.thoughtStream.appendChild(card);
        this.thoughtStream.scrollTop = this.thoughtStream.scrollHeight;
    }

    showThinking(label) {
        this.thinkingText.textContent = label;
        this.thinkingHud.style.display = 'flex';
    }

    hideThinking() {
        this.thinkingHud.style.display = 'none';
        this.reactorState.textContent = 'IDLE';
        this.reactorState.className = 'reactor-state';
    }

    playSpeechAudio(audioBase64) {
        if (!audioBase64) return;
        try {
            this.reactorState.textContent = 'SPEAKING (MALE VOICE)';
            this.reactorState.className = 'reactor-state active';

            this.audioPlayer.src = `data:audio/mp3;base64,${audioBase64}`;
            this.audioPlayer.play().catch(e => console.warn('[Audio] Autoplay policy block:', e));

            this.audioPlayer.onended = () => {
                this.reactorState.textContent = 'IDLE';
                this.reactorState.className = 'reactor-state';
                this.visualizer.setIdle();
            };
        } catch (e) {
            console.error('[Audio] Playback error:', e);
        }
    }

    async fetchCameraDevices() {
        try {
            const res = await fetch('/api/camera/devices');
            const data = await res.json();
            this.cameraSelect.innerHTML = '';
            data.forEach(cam => {
                const opt = document.createElement('option');
                opt.value = cam.index;
                opt.textContent = `${cam.name} ${cam.accessible ? '(Online)' : ''}`;
                this.cameraSelect.appendChild(opt);
            });
        } catch (e) {
            console.warn('[Camera] Failed to fetch devices:', e);
        }
    }

    async fetchVoices() {
        try {
            const res = await fetch('/api/voices');
            const data = await res.json();
            this.selectVoice.innerHTML = '';
            data.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.key;
                opt.textContent = `${v.name} (${v.gender})`;
                if (v.selected) opt.selected = true;
                this.selectVoice.appendChild(opt);
            });
        } catch (e) {
            console.warn('[Voices] Failed to fetch voices:', e);
        }
    }
}

function jsonParseSafe(str) {
    try {
        return JSON.parse(str);
    } catch {
        return null;
    }
}

// Initialize on DOM load
window.addEventListener('DOMContentLoaded', () => {
    window.cockpit = new RobotBrainCockpit();
});
