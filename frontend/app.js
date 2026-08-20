/**
 * VLA Studio - Executive Client Controller
 */

class VLAStudioApp {
    constructor() {
        this.ws = null;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.micStream = null;
        this.cameraStream = null;
        this.activeCameraSource = 'browser';
        this.visualizer = null;
        this.frameInterval = null;
        this.diagnosticsInterval = null;

        // Elements
        this.webcamVideo = document.getElementById('webcam-video-element');
        this.hostStream = document.getElementById('host-stream-element');
        this.captureCanvas = document.getElementById('hidden-capture-canvas');
        this.audioPlayer = document.getElementById('speech-audio-element');
        this.transcriptScroll = document.getElementById('transcript-scroll');
        this.processingBar = document.getElementById('processing-bar');
        this.processingLabel = document.getElementById('processing-label');
        this.btnPtt = document.getElementById('btn-ptt-trigger');
        this.pttLabel = document.getElementById('ptt-text-label');
        this.userTextInput = document.getElementById('user-text-input');
        this.btnSend = document.getElementById('btn-send-text');
        this.btnScan = document.getElementById('btn-scan-environment');
        this.btnCaptureFrame = document.getElementById('btn-capture-frame');
        this.btnCameraBrowser = document.getElementById('btn-camera-browser');
        this.btnCameraHost = document.getElementById('btn-camera-host');
        this.hostCamDropdownContainer = document.getElementById('host-camera-select-container');
        this.hostCamDropdown = document.getElementById('host-camera-dropdown');
        this.audioMonitorLabel = document.getElementById('audio-monitor-label');
        this.telemetryRes = document.getElementById('telemetry-res');
        this.engineStatusDot = document.getElementById('engine-status-dot');
        this.engineStatusText = document.getElementById('engine-status-text');

        // Modal Elements
        this.preferencesModal = document.getElementById('preferences-modal');
        this.btnPreferences = document.getElementById('btn-preferences');
        this.btnCloseModal = document.getElementById('btn-close-modal');
        this.btnModalCancel = document.getElementById('btn-modal-cancel');
        this.btnModalSave = document.getElementById('btn-modal-save');
        this.selectVoice = document.getElementById('select-voice');
        this.btnShutdown = document.getElementById('btn-shutdown-system');
        this.shutdownModal = document.getElementById('shutdown-modal');

        this.init();
    }

    async init() {
        console.log('[VLA Studio] Initializing interface...');
        this.visualizer = new AudioSpectrumVisualizer('audio-waveform-canvas');
        this.visualizer.connectAudioElement(this.audioPlayer);

        const savedVoice = localStorage.getItem('vla_voice') || 'guy';
        this.selectVoice.value = savedVoice;

        this.initWebSocket();
        this.initBrowserCamera();
        this.initMicrophone();
        this.initEventListeners();
        this.fetchHostCameras();
        this.startDiagnosticsPolling();
    }

    startDiagnosticsPolling() {
        const check = async () => {
            try {
                const res = await fetch('/api/diagnostics');
                if (res.ok) {
                    const data = await res.json();
                    const brain = data.brain || {};
                    if (brain.ready) {
                        this.engineStatusDot.className = 'status-indicator-dot online';
                        this.engineStatusText.textContent = `Model: ${brain.model_name || 'Qwen2.5-VL 7B'} (GPU Active)`;
                    } else if (brain.is_starting) {
                        this.engineStatusDot.className = 'status-indicator-dot loading';
                        this.engineStatusText.textContent = `Model: Initializing ${brain.model_name || 'Qwen2.5-VL 7B'}...`;
                    } else {
                        this.engineStatusDot.className = 'status-indicator-dot offline';
                        this.engineStatusText.textContent = `Model: Standby (${brain.status || 'Offline'})`;
                    }
                }
            } catch (err) {
                this.engineStatusDot.className = 'status-indicator-dot offline';
                this.engineStatusText.textContent = 'Server Offline';
            }
        };

        check();
        this.diagnosticsInterval = setInterval(check, 2500);
    }

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/live`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            const voice = localStorage.getItem('vla_voice') || 'guy';
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

            this.webcamVideo.srcObject = this.cameraStream;
            this.webcamVideo.onloadedmetadata = () => {
                this.webcamVideo.play();
                this.telemetryRes.textContent = `${this.webcamVideo.videoWidth} x ${this.webcamVideo.videoHeight}`;
            };

            if (this.frameInterval) clearInterval(this.frameInterval);
            this.frameInterval = setInterval(() => this.broadcastCurrentFrame(), 600);

            console.log('[Camera] Browser webcam streaming.');
        } catch (e) {
            console.warn('[Camera] Browser webcam unavailable, switching to host camera:', e);
            this.switchCameraSource('host');
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
        this.btnCameraBrowser.addEventListener('click', () => this.switchCameraSource('browser'));
        this.btnCameraHost.addEventListener('click', () => this.switchCameraSource('host'));

        this.btnPtt.addEventListener('mousedown', () => this.startRecording());
        this.btnPtt.addEventListener('mouseup', () => this.stopRecording());
        this.btnPtt.addEventListener('mouseleave', () => { if (this.isRecording) this.stopRecording(); });
        this.btnPtt.addEventListener('touchstart', (e) => { e.preventDefault(); this.startRecording(); });
        this.btnPtt.addEventListener('touchend', (e) => { e.preventDefault(); this.stopRecording(); });

        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && document.activeElement !== this.userTextInput && !this.isRecording && this.preferencesModal.style.display !== 'flex') {
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
        this.userTextInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.sendTextMessage();
        });

        this.btnScan.addEventListener('click', () => this.triggerSceneScan());
        this.btnCaptureFrame.addEventListener('click', () => {
            this.sendTextMessage("Analyze this visual frame and describe key elements in detail.");
        });

        this.hostCamDropdown.addEventListener('change', async (e) => {
            const idx = e.target.value;
            try {
                await fetch(`/api/camera/select?index=${idx}`, { method: 'POST' });
                this.hostStream.src = `/api/camera/stream?t=${Date.now()}`;
            } catch (err) {}
        });

        // Preferences modal
        this.btnPreferences.addEventListener('click', () => { this.preferencesModal.style.display = 'flex'; });
        this.btnCloseModal.addEventListener('click', () => { this.preferencesModal.style.display = 'none'; });
        this.btnModalCancel.addEventListener('click', () => { this.preferencesModal.style.display = 'none'; });
        this.btnModalSave.addEventListener('click', () => {
            const voice = this.selectVoice.value;
            localStorage.setItem('vla_voice', voice);
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'set_voice', voice_key: voice }));
            }
            this.preferencesModal.style.display = 'none';
        });

        // Stop / Shutdown Button
        this.btnShutdown.addEventListener('click', () => this.confirmShutdown());
    }

    async confirmShutdown() {
        const confirmed = confirm("Are you sure you want to stop the local neural model and shut down the server?");
        if (!confirmed) return;

        this.shutdownModal.style.display = 'flex';
        try {
            if (this.cameraStream) {
                this.cameraStream.getTracks().forEach(t => t.stop());
            }
            await fetch('/api/system/shutdown', { method: 'POST' });
        } catch (e) {}

        setTimeout(() => {
            window.close();
        }, 1500);
    }

    switchCameraSource(source) {
        this.activeCameraSource = source;
        if (source === 'browser') {
            this.btnCameraBrowser.classList.add('active');
            this.btnCameraHost.classList.remove('active');
            this.webcamVideo.style.display = 'block';
            this.hostStream.style.display = 'none';
            this.hostCamDropdownContainer.style.display = 'none';
            this.initBrowserCamera();
        } else {
            this.btnCameraHost.classList.add('active');
            this.btnCameraBrowser.classList.remove('active');
            this.webcamVideo.style.display = 'none';
            this.hostStream.style.display = 'block';
            this.hostCamDropdownContainer.style.display = 'block';
            if (this.frameInterval) clearInterval(this.frameInterval);
            this.hostStream.src = `/api/camera/stream?t=${Date.now()}`;
            this.telemetryRes.textContent = 'Host Camera';
        }
    }

    captureCurrentFrameBase64() {
        if (this.activeCameraSource === 'browser' && this.webcamVideo.videoWidth > 0) {
            this.captureCanvas.width = 640;
            this.captureCanvas.height = 360;
            const ctx = this.captureCanvas.getContext('2d');
            ctx.drawImage(this.webcamVideo, 0, 0, 640, 360);
            return this.captureCanvas.toDataURL('image/jpeg', 0.8).split(',')[1];
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
        this.audioMonitorLabel.textContent = 'Recording';
        this.audioMonitorLabel.className = 'monitor-label active';

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
        this.pttLabel.textContent = 'Hold to Talk';
        this.audioMonitorLabel.textContent = 'Processing';

        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
    }

    processRecordedAudio() {
        if (this.audioChunks.length === 0) return;

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.showProcessing('Transcribing speech...');

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
        const text = overrideText || this.userTextInput.value.trim();
        if (!text) return;

        if (!overrideText) this.userTextInput.value = '';

        this.appendMessage('user', text);
        this.showProcessing('Executing visual inference (Qwen2.5-VL)...');

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
        this.appendMessage('user', 'System scan request');
        this.showProcessing('Scanning visual environment (Qwen2.5-VL)...');

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
            if (data.state === 'thinking') this.showProcessing('Analyzing visual context...');
            else if (data.state === 'transcribing') this.showProcessing('Transcribing speech...');
            else if (data.state === 'idle') this.hideProcessing();
        } else if (data.type === 'stt_result') {
            if (data.text) this.appendMessage('user', data.text);
        } else if (data.type === 'brain_response' || data.type === 'scene_briefing') {
            this.hideProcessing();
            const reply = data.response || 'No output generated.';
            this.appendMessage('assistant', reply, data.speech);

            if (data.speech && data.speech.audio_base64) {
                this.playSpeech(data.speech.audio_base64);
            }
        }
    }

    appendMessage(role, text, speechData = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message-card ${role}`;

        const header = document.createElement('div');
        header.className = 'message-header';

        const sender = document.createElement('span');
        sender.className = 'sender-name';
        sender.textContent = role === 'user' ? 'User' : 'Qwen2.5-VL';

        const timeSpan = document.createElement('span');
        timeSpan.className = 'timestamp';
        const now = new Date();
        timeSpan.textContent = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;

        header.appendChild(sender);
        header.appendChild(timeSpan);

        if (speechData && speechData.audio_base64) {
            const playBtn = document.createElement('button');
            playBtn.className = 'message-audio-btn';
            playBtn.textContent = 'Audio';
            playBtn.onclick = () => this.playSpeech(speechData.audio_base64);
            header.appendChild(playBtn);
        }

        const body = document.createElement('div');
        body.className = 'message-body';
        body.textContent = text;

        msgDiv.appendChild(header);
        msgDiv.appendChild(body);

        this.transcriptScroll.appendChild(msgDiv);
        this.transcriptScroll.scrollTop = this.transcriptScroll.scrollHeight;
    }

    showProcessing(label) {
        this.processingLabel.textContent = label;
        this.processingBar.style.display = 'flex';
    }

    hideProcessing() {
        this.processingBar.style.display = 'none';
        this.audioMonitorLabel.textContent = 'Idle';
        this.audioMonitorLabel.className = 'monitor-label';
    }

    playSpeech(audioBase64) {
        if (!audioBase64) return;
        try {
            this.audioMonitorLabel.textContent = 'Speaking';
            this.audioMonitorLabel.className = 'monitor-label active';

            this.audioPlayer.src = `data:audio/mp3;base64,${audioBase64}`;
            this.audioPlayer.play().catch(() => {});

            this.audioPlayer.onended = () => {
                this.audioMonitorLabel.textContent = 'Idle';
                this.audioMonitorLabel.className = 'monitor-label';
                this.visualizer.setIdle();
            };
        } catch (e) {}
    }

    async fetchHostCameras() {
        try {
            const res = await fetch('/api/camera/devices');
            const data = await res.json();
            this.hostCamDropdown.innerHTML = '';
            data.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.index;
                opt.textContent = c.name;
                this.hostCamDropdown.appendChild(opt);
            });
        } catch (e) {}
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.vlaStudio = new VLAStudioApp();
});
