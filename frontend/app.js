/**
 * AURA Local Vision & Voice Assistant - Frontend Controller
 */

class VisionVoiceApp {
    constructor() {
        this.ws = null;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.micStream = null;
        this.cameraStream = null;
        this.activeCameraSource = 'browser'; // 'browser' or 'server'
        this.visualizer = null;
        this.frameInterval = null;

        // Elements
        this.browserVideo = document.getElementById('browser-video-element');
        this.serverStream = document.getElementById('server-stream-element');
        this.frameCanvas = document.getElementById('browser-frame-canvas');
        this.audioPlayer = document.getElementById('tts-audio-element');
        this.chatTimeline = document.getElementById('chat-timeline');
        this.thinkingState = document.getElementById('thinking-state');
        this.thinkingLabel = document.getElementById('thinking-label');
        this.btnPtt = document.getElementById('btn-ptt');
        this.pttLabel = document.getElementById('ptt-label');
        this.textInput = document.getElementById('text-input-field');
        this.btnSend = document.getElementById('btn-send-message');
        this.btnSceneScan = document.getElementById('btn-scene-scan');
        this.btnSnapInspect = document.getElementById('btn-snap-inspect');
        this.btnSourceBrowser = document.getElementById('btn-source-browser');
        this.btnSourceServer = document.getElementById('btn-source-server');
        this.serverCamDropdownWrap = document.getElementById('server-cam-dropdown-wrap');
        this.serverCameraSelect = document.getElementById('server-camera-select');
        this.visualizerStatus = document.getElementById('visualizer-status-text');
        this.connectionStatus = document.getElementById('connection-status');
        this.connectionLabel = document.getElementById('connection-label');
        this.viewportResolution = document.getElementById('viewport-resolution');

        // Modal Elements
        this.settingsModal = document.getElementById('settings-modal');
        this.btnOpenSettings = document.getElementById('btn-open-settings');
        this.btnCloseSettings = document.getElementById('btn-close-settings');
        this.btnCancelSettings = document.getElementById('btn-cancel-settings');
        this.btnSaveSettings = document.getElementById('btn-save-settings');
        this.configVoice = document.getElementById('config-voice-select');

        this.init();
    }

    async init() {
        console.log('[AURA] Starting local assistant controller...');
        this.visualizer = new AudioSpectrumVisualizer('minimal-audio-canvas');
        this.visualizer.connectAudioElement(this.audioPlayer);

        const savedVoice = localStorage.getItem('aura_voice') || 'guy';
        this.configVoice.value = savedVoice;

        this.initWebSocket();
        this.initBrowserCamera();
        this.initMicrophone();
        this.initEventListeners();
        this.fetchServerCameras();
    }

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/live`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.connectionStatus.className = 'status-indicator online';
            this.connectionLabel.textContent = 'Connected (100% Local)';
            const voice = localStorage.getItem('aura_voice') || 'guy';
            this.ws.send(JSON.stringify({ type: 'set_voice', voice_key: voice }));
        };

        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this.handleServerEvent(data);
            } catch (err) {
                console.error('[WS] Parse error:', err);
            }
        };

        this.ws.onclose = () => {
            this.connectionStatus.className = 'status-indicator offline';
            this.connectionLabel.textContent = 'Reconnecting...';
            setTimeout(() => this.initWebSocket(), 2000);
        };
    }

    async initBrowserCamera() {
        try {
            if (this.cameraStream) {
                this.cameraStream.getTracks().forEach(t => t.stop());
            }

            this.cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }
            });

            this.browserVideo.srcObject = this.cameraStream;
            this.browserVideo.onloadedmetadata = () => {
                this.browserVideo.play();
                this.viewportResolution.textContent = `${this.browserVideo.videoWidth} × ${this.browserVideo.videoHeight}`;
            };

            if (this.frameInterval) clearInterval(this.frameInterval);
            this.frameInterval = setInterval(() => this.broadcastCurrentFrame(), 600);

            console.log('[Camera] Browser webcam active.');
        } catch (e) {
            console.warn('[Camera] Browser webcam not accessible, switching to host camera:', e);
            this.switchCameraSource('server');
        }
    }

    async initMicrophone() {
        try {
            this.micStream = await navigator.mediaDevices.getUserMedia({
                audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
            });
            console.log('[Audio] Microphone ready.');
        } catch (e) {
            console.warn('[Audio] Microphone access denied:', e);
        }
    }

    initEventListeners() {
        this.btnSourceBrowser.addEventListener('click', () => this.switchCameraSource('browser'));
        this.btnSourceServer.addEventListener('click', () => this.switchCameraSource('server'));

        this.btnPtt.addEventListener('mousedown', () => this.startRecording());
        this.btnPtt.addEventListener('mouseup', () => this.stopRecording());
        this.btnPtt.addEventListener('mouseleave', () => { if (this.isRecording) this.stopRecording(); });
        this.btnPtt.addEventListener('touchstart', (e) => { e.preventDefault(); this.startRecording(); });
        this.btnPtt.addEventListener('touchend', (e) => { e.preventDefault(); this.stopRecording(); });

        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && document.activeElement !== this.textInput && !this.isRecording && !this.settingsModal.style.display.includes('flex')) {
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

        this.btnSend.addEventListener('click', () => this.sendTextMessage());
        this.textInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.sendTextMessage();
        });

        this.btnSceneScan.addEventListener('click', () => this.triggerSceneScan());
        this.btnSnapInspect.addEventListener('click', () => {
            this.sendTextMessage("Describe what is in front of the camera in detail.");
        });

        this.serverCameraSelect.addEventListener('change', async (e) => {
            const idx = e.target.value;
            try {
                await fetch(`/api/camera/select?index=${idx}`, { method: 'POST' });
                this.serverStream.src = `/api/camera/stream?t=${Date.now()}`;
            } catch (err) {}
        });

        this.btnOpenSettings.addEventListener('click', () => { this.settingsModal.style.display = 'flex'; });
        this.btnCloseSettings.addEventListener('click', () => { this.settingsModal.style.display = 'none'; });
        this.btnCancelSettings.addEventListener('click', () => { this.settingsModal.style.display = 'none'; });
        this.btnSaveSettings.addEventListener('click', () => {
            const voice = this.configVoice.value;
            localStorage.setItem('aura_voice', voice);
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'set_voice', voice_key: voice }));
            }
            this.settingsModal.style.display = 'none';
        });
    }

    switchCameraSource(source) {
        this.activeCameraSource = source;
        if (source === 'browser') {
            this.btnSourceBrowser.classList.add('active');
            this.btnSourceServer.classList.remove('active');
            this.browserVideo.style.display = 'block';
            this.serverStream.style.display = 'none';
            this.serverCamDropdownWrap.style.display = 'none';
            this.initBrowserCamera();
        } else {
            this.btnSourceServer.classList.add('active');
            this.btnSourceBrowser.classList.remove('active');
            this.browserVideo.style.display = 'none';
            this.serverStream.style.display = 'block';
            this.serverCamDropdownWrap.style.display = 'block';
            if (this.frameInterval) clearInterval(this.frameInterval);
            this.serverStream.src = `/api/camera/stream?t=${Date.now()}`;
            this.viewportResolution.textContent = 'Host Camera';
        }
    }

    captureCurrentFrameBase64() {
        if (this.activeCameraSource === 'browser' && this.browserVideo.videoWidth > 0) {
            this.frameCanvas.width = 640;
            this.frameCanvas.height = 360;
            const ctx = this.frameCanvas.getContext('2d');
            ctx.drawImage(this.browserVideo, 0, 0, 640, 360);
            return this.frameCanvas.toDataURL('image/jpeg', 0.8).split(',')[1];
        }
        return null;
    }

    broadcastCurrentFrame() {
        if (this.activeCameraSource === 'browser' && this.ws && this.ws.readyState === WebSocket.OPEN) {
            const b64 = this.captureCurrentFrameBase64();
            if (b64) {
                this.ws.send(JSON.stringify({ type: 'client_frame', image_base64: b64 }));
            }
        }
    }

    startRecording() {
        if (!this.micStream) return;
        if (this.isRecording) return;

        this.isRecording = true;
        this.audioChunks = [];
        this.btnPtt.classList.add('recording');
        this.pttLabel.textContent = 'Listening...';
        this.visualizerStatus.textContent = 'Listening';
        this.visualizerStatus.className = 'visualizer-status active';

        this.visualizer.connectMediaStream(this.micStream);

        const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
        this.mediaRecorder = new MediaRecorder(this.micStream, { mimeType: mime });

        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) this.audioChunks.push(e.data);
        };

        this.mediaRecorder.onstop = () => this.processRecordedAudio();
        this.mediaRecorder.start();
    }

    stopRecording() {
        if (!this.isRecording) return;
        this.isRecording = false;
        this.btnPtt.classList.remove('recording');
        this.pttLabel.textContent = 'Hold to Speak';
        this.visualizerStatus.textContent = 'Processing';

        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
    }

    processRecordedAudio() {
        if (this.audioChunks.length === 0) return;

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.showThinking('Transcribing speech...');

        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = () => {
            const b64 = reader.result.split(',')[1];
            const frameB64 = this.captureCurrentFrameBase64();

            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'audio_query',
                    audio_base64: b64,
                    image_base64: frameB64,
                    format: 'webm'
                }));
            }
        };
    }

    sendTextMessage(overrideText = null) {
        const text = overrideText || this.textInput.value.trim();
        if (!text) return;

        if (!overrideText) this.textInput.value = '';

        this.appendMessage('user', text);
        this.showThinking('Analyzing visual surroundings with Qwen2.5-VL...');

        const frameB64 = this.captureCurrentFrameBase64();

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'text_query',
                text: text,
                image_base64: frameB64
            }));
        }
    }

    triggerSceneScan() {
        this.appendMessage('user', '🔍 Scan scene requested');
        this.showThinking('Assessing environment with Qwen2.5-VL...');

        const frameB64 = this.captureCurrentFrameBase64();

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'scene_scan',
                image_base64: frameB64
            }));
        }
    }

    handleServerEvent(data) {
        if (!data || !data.type) return;

        if (data.type === 'status_update') {
            if (data.state === 'thinking') this.showThinking('Analyzing visual feed...');
            else if (data.state === 'transcribing') this.showThinking('Transcribing speech...');
            else if (data.state === 'idle') this.hideThinking();
        } else if (data.type === 'stt_result') {
            if (data.text) this.appendMessage('user', data.text);
        } else if (data.type === 'brain_response' || data.type === 'scene_briefing') {
            this.hideThinking();
            const reply = data.response || 'No response.';
            this.appendMessage('assistant', reply, data.speech);

            if (data.speech && data.speech.audio_base64) {
                this.playSpeech(data.speech.audio_base64);
            }
        }
    }

    appendMessage(role, text, speechData = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${role}-message`;

        const meta = document.createElement('div');
        meta.className = 'message-meta';

        const sender = document.createElement('span');
        sender.className = 'message-sender';
        sender.textContent = role === 'user' ? 'You' : 'AURA (Qwen2.5-VL)';

        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        const now = new Date();
        timeSpan.textContent = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;

        meta.appendChild(sender);
        meta.appendChild(timeSpan);

        if (speechData && speechData.audio_base64) {
            const playBtn = document.createElement('button');
            playBtn.className = 'message-audio-btn';
            playBtn.textContent = '🔊 Play';
            playBtn.onclick = () => this.playSpeech(speechData.audio_base64);
            meta.appendChild(playBtn);
        }

        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = text;

        msgDiv.appendChild(meta);
        msgDiv.appendChild(content);

        this.chatTimeline.appendChild(msgDiv);
        this.chatTimeline.scrollTop = this.chatTimeline.scrollHeight;
    }

    showThinking(label) {
        this.thinkingLabel.textContent = label;
        this.thinkingState.style.display = 'flex';
    }

    hideThinking() {
        this.thinkingState.style.display = 'none';
        this.visualizerStatus.textContent = 'Standby';
        this.visualizerStatus.className = 'visualizer-status';
    }

    playSpeech(audioBase64) {
        if (!audioBase64) return;
        try {
            this.visualizerStatus.textContent = 'Speaking';
            this.visualizerStatus.className = 'visualizer-status active';

            this.audioPlayer.src = `data:audio/mp3;base64,${audioBase64}`;
            this.audioPlayer.play().catch(e => console.warn('[Audio] Play error:', e));

            this.audioPlayer.onended = () => {
                this.visualizerStatus.textContent = 'Standby';
                this.visualizerStatus.className = 'visualizer-status';
                this.visualizer.setIdle();
            };
        } catch (e) {
            console.error('[Audio] Error:', e);
        }
    }

    async fetchServerCameras() {
        try {
            const res = await fetch('/api/camera/devices');
            const data = await res.json();
            this.serverCameraSelect.innerHTML = '';
            data.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.index;
                opt.textContent = c.name;
                this.serverCameraSelect.appendChild(opt);
            });
        } catch (e) {}
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.auraApp = new VisionVoiceApp();
});
