/**
 * VLA Studio - Executive Client Controller (Zero Feedback & High-Accuracy Audio)
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
        this.selectedDeviceId = null;
        this.isFacingUser = true;
        this.visualizer = null;
        this.frameInterval = null;
        this.diagnosticsInterval = null;
        this.speechRecognizer = null;
        this.recognizedSpeechText = '';

        // Elements
        this.clientVideo = document.getElementById('client-video');
        this.serverVideoFeed = document.getElementById('server-video-feed');
        this.hiddenFrameCanvas = document.getElementById('hidden-frame-canvas');
        this.ttsAudioPlayer = document.getElementById('tts-audio-element');
        this.transcriptFeed = document.getElementById('transcript-feed');
        this.processingIndicator = document.getElementById('processing-indicator');
        this.processingText = document.getElementById('processing-text');
        this.btnPtt = document.getElementById('btn-ptt');
        this.pttLabel = document.getElementById('ptt-label');
        this.textInput = document.getElementById('text-input');
        this.btnSend = document.getElementById('btn-send');
        this.btnSceneScan = document.getElementById('btn-scene-scan');
        this.btnInspectFrame = document.getElementById('btn-inspect-frame');
        this.btnFlipCamera = document.getElementById('btn-flip-camera');
        this.browserCameraSelect = document.getElementById('browser-camera-select');
        this.tabCamBrowser = document.getElementById('tab-cam-browser');
        this.tabCamHost = document.getElementById('tab-cam-host');
        this.hostCamSelectWrap = document.getElementById('host-cam-select-wrap');
        this.hostCameraSelect = document.getElementById('host-camera-select');
        this.audioStatusLabel = document.getElementById('audio-status-label');
        this.videoResolutionTag = document.getElementById('video-resolution-tag');
        
        // Status & Diagnostics Elements
        this.statusDot = document.getElementById('status-dot');
        this.statusModelName = document.getElementById('status-model-name');
        this.statusStateText = document.getElementById('status-state-text');
        this.diagEngineName = document.getElementById('diag-engine-name');
        this.diagHwMode = document.getElementById('diag-hw-mode');
        this.diagStatusBadge = document.getElementById('diag-status-badge');

        // Modal Elements
        this.modalPreferences = document.getElementById('modal-preferences');
        this.btnOpenSettings = document.getElementById('btn-open-settings');
        this.btnModalClose = document.getElementById('btn-modal-close');
        this.btnModalCancel = document.getElementById('btn-modal-cancel');
        this.btnModalSave = document.getElementById('btn-modal-save');
        this.voiceSelect = document.getElementById('voice-select');
        this.btnStopSystem = document.getElementById('btn-stop-system');
        this.modalShutdown = document.getElementById('modal-shutdown');

        // Network / Mobile Pairing Modal
        this.btnNetworkConnect = document.getElementById('btn-network-connect');
        this.modalNetwork = document.getElementById('modal-network');
        this.btnCloseNetwork = document.getElementById('btn-close-network');
        this.btnCloseNetworkFooter = document.getElementById('btn-close-network-footer');
        this.qrCodeImage = document.getElementById('qr-code-image');
        this.networkUrlInput = document.getElementById('network-url-input');
        this.btnCopyNetworkUrl = document.getElementById('btn-copy-network-url');

        this.init();
    }

    async init() {
        console.log('[VLA Studio] Initializing zero-feedback multimodal client...');
        this.visualizer = new AudioSpectrumVisualizer('audio-waveform-canvas');

        const savedVoice = localStorage.getItem('vla_voice') || 'guy';
        this.voiceSelect.value = savedVoice;

        if (/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent)) {
            if (this.btnFlipCamera) this.btnFlipCamera.style.display = 'flex';
        }

        this.initSpeechRecognition();
        this.initWebSocket();
        await this.initBrowserCamera();
        await this.enumerateAllCameras();
        await this.initMicrophone();
        this.initEventListeners();
        this.startDiagnosticsPolling();
    }

    initSpeechRecognition() {
        const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognitionClass) {
            try {
                this.speechRecognizer = new SpeechRecognitionClass();
                this.speechRecognizer.continuous = false;
                this.speechRecognizer.interimResults = true;
                this.speechRecognizer.lang = 'en-US';

                this.speechRecognizer.onresult = (event) => {
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        transcript += event.results[i][0].transcript;
                    }
                    if (transcript.trim()) {
                        this.recognizedSpeechText = transcript.trim();
                        this.textInput.placeholder = `Listening: "${this.recognizedSpeechText}"`;
                    }
                };

                this.speechRecognizer.onerror = (e) => {
                    // Fail gracefully and rely on Faster-Whisper backend
                };
            } catch (e) {}
        }
    }

    async enumerateAllCameras() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;

        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(d => d.kind === 'videoinput');

            this.browserCameraSelect.innerHTML = '';

            if (videoDevices.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'Default Camera';
                this.browserCameraSelect.appendChild(opt);
                return;
            }

            videoDevices.forEach((device, index) => {
                const opt = document.createElement('option');
                opt.value = device.deviceId;
                opt.textContent = device.label || `Camera ${index + 1}`;
                if (this.selectedDeviceId === device.deviceId) {
                    opt.selected = true;
                }
                this.browserCameraSelect.appendChild(opt);
            });
        } catch (e) {}
    }

    async initBrowserCamera(deviceId = null) {
        try {
            if (this.cameraStream) {
                this.cameraStream.getTracks().forEach(t => t.stop());
            }

            const videoConstraints = {
                width: { ideal: 1920, min: 1280 },
                height: { ideal: 1080, min: 720 }
            };

            if (deviceId) {
                videoConstraints.deviceId = { exact: deviceId };
                this.selectedDeviceId = deviceId;
            } else if (this.selectedDeviceId) {
                videoConstraints.deviceId = { exact: this.selectedDeviceId };
            } else {
                videoConstraints.facingMode = this.isFacingUser ? 'user' : 'environment';
            }

            this.cameraStream = await navigator.mediaDevices.getUserMedia({
                video: videoConstraints
            });

            this.clientVideo.srcObject = this.cameraStream;
            this.clientVideo.onloadedmetadata = () => {
                this.clientVideo.play();
                this.videoResolutionTag.textContent = `${this.clientVideo.videoWidth} x ${this.clientVideo.videoHeight} (Full HD)`;
            };

            if (this.frameInterval) clearInterval(this.frameInterval);
            this.frameInterval = setInterval(() => this.broadcastCurrentFrame(), 600);
        } catch (e) {
            try {
                const fallbackConstraints = deviceId ? { deviceId: { exact: deviceId } } : true;
                this.cameraStream = await navigator.mediaDevices.getUserMedia({ video: fallbackConstraints });
                this.clientVideo.srcObject = this.cameraStream;
                this.clientVideo.play();
            } catch (err) {
                this.switchCameraSource('host');
            }
        }
    }

    async initMicrophone() {
        try {
            if (this.micStream) {
                this.micStream.getTracks().forEach(t => t.stop());
            }

            // High-fidelity voice constraints with acoustic echo cancellation
            this.micStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: { ideal: true },
                    noiseSuppression: { ideal: true },
                    autoGainControl: { ideal: true },
                    channelCount: 1,
                    sampleRate: 16000
                }
            });

            this.visualizer.connectMediaStream(this.micStream);
            console.log('[Audio] Feedback-isolated microphone active.');
        } catch (e) {
            console.warn('[Audio] Microphone access issue:', e);
        }
    }

    startDiagnosticsPolling() {
        const updateDiagnostics = async () => {
            try {
                const res = await fetch('/api/diagnostics');
                if (res.ok) {
                    const data = await res.json();
                    const brain = data.brain || {};
                    
                    if (brain.ready) {
                        this.statusDot.className = 'status-dot online';
                        this.statusModelName.textContent = brain.model_name || 'Qwen2.5-VL';
                        this.statusStateText.textContent = 'Ready (GPU Active)';
                        
                        this.diagStatusBadge.className = 'diag-badge';
                        this.diagStatusBadge.textContent = 'ONLINE & READY (GPU ACCELERATED)';
                        this.diagHwMode.textContent = brain.acceleration || 'Hardware Accelerated (CUDA 4-Bit VRAM Offload)';
                        this.diagEngineName.textContent = `${brain.model_name || 'Qwen2.5-VL'} (${brain.model_size_gb || '3.2'} GB VRAM)`;
                    } else if (brain.is_starting) {
                        this.statusDot.className = 'status-dot loading';
                        this.statusStateText.textContent = 'Loading weights...';
                        
                        this.diagStatusBadge.className = 'diag-badge loading';
                        this.diagStatusBadge.textContent = 'INITIALIZING WEIGHTS INTO VRAM...';
                    } else {
                        this.statusDot.className = 'status-dot offline';
                        this.statusStateText.textContent = brain.status || 'Standby';
                        
                        this.diagStatusBadge.className = 'diag-badge loading';
                        this.diagStatusBadge.textContent = brain.status || 'STANDBY';
                    }
                }
            } catch (err) {
                this.statusDot.className = 'status-dot offline';
                this.statusStateText.textContent = 'Server Offline';
                this.diagStatusBadge.className = 'diag-badge loading';
                this.diagStatusBadge.textContent = 'OFFLINE';
            }
        };

        updateDiagnostics();
        this.diagnosticsInterval = setInterval(updateDiagnostics, 2500);
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
            } catch (err) {}
        };

        this.ws.onclose = () => {
            setTimeout(() => this.initWebSocket(), 2000);
        };
    }

    initEventListeners() {
        this.tabCamBrowser.addEventListener('click', () => this.switchCameraSource('browser'));
        this.tabCamHost.addEventListener('click', () => {
            this.switchCameraSource('host');
            this.fetchHostCamerasOnce();
        });

        this.browserCameraSelect.addEventListener('change', (e) => {
            const devId = e.target.value;
            if (devId) {
                this.initBrowserCamera(devId);
            }
        });

        if (this.btnFlipCamera) {
            this.btnFlipCamera.addEventListener('click', () => {
                this.isFacingUser = !this.isFacingUser;
                this.selectedDeviceId = null;
                this.initBrowserCamera();
            });
        }

        // Push-to-Talk Event Listeners
        this.btnPtt.addEventListener('mousedown', (e) => { e.preventDefault(); this.startRecording(); });
        this.btnPtt.addEventListener('mouseup', (e) => { e.preventDefault(); this.stopRecording(); });
        this.btnPtt.addEventListener('mouseleave', () => { if (this.isRecording) this.stopRecording(); });
        this.btnPtt.addEventListener('touchstart', (e) => { e.preventDefault(); this.startRecording(); });
        this.btnPtt.addEventListener('touchend', (e) => { e.preventDefault(); this.stopRecording(); });

        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && document.activeElement !== this.textInput && !this.isRecording && this.modalPreferences.style.display !== 'flex' && this.modalNetwork.style.display !== 'flex') {
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
        this.btnInspectFrame.addEventListener('click', () => {
            this.sendTextMessage("Analyze this visual frame and describe key elements in detail.");
        });

        this.hostCameraSelect.addEventListener('change', async (e) => {
            const idx = e.target.value;
            try {
                await fetch(`/api/camera/select?index=${idx}`, { method: 'POST' });
                this.serverVideoFeed.src = `/api/camera/stream?t=${Date.now()}`;
            } catch (err) {}
        });

        // Network Modal
        this.btnNetworkConnect.addEventListener('click', () => this.openNetworkModal());
        this.btnCloseNetwork.addEventListener('click', () => { this.modalNetwork.style.display = 'none'; });
        this.btnCloseNetworkFooter.addEventListener('click', () => { this.modalNetwork.style.display = 'none'; });
        this.btnCopyNetworkUrl.addEventListener('click', () => {
            navigator.clipboard.writeText(this.networkUrlInput.value);
            this.btnCopyNetworkUrl.textContent = 'Copied!';
            setTimeout(() => { this.btnCopyNetworkUrl.textContent = 'Copy'; }, 2000);
        });

        // Preferences Modal
        this.btnOpenSettings.addEventListener('click', () => { this.modalPreferences.style.display = 'flex'; });
        this.btnModalClose.addEventListener('click', () => { this.modalPreferences.style.display = 'none'; });
        this.btnModalCancel.addEventListener('click', () => { this.modalPreferences.style.display = 'none'; });
        this.btnModalSave.addEventListener('click', () => {
            const voice = this.voiceSelect.value;
            localStorage.setItem('vla_voice', voice);
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'set_voice', voice_key: voice }));
            }
            this.modalPreferences.style.display = 'none';
        });

        // Stop System Button
        this.btnStopSystem.addEventListener('click', () => this.confirmShutdown());
    }

    async openNetworkModal() {
        try {
            const res = await fetch('/api/network/info');
            if (res.ok) {
                const data = await res.json();
                this.networkUrlInput.value = data.network_url;
                if (data.qr_base64) {
                    this.qrCodeImage.src = `data:image/png;base64,${data.qr_base64}`;
                }
            }
        } catch (e) {
            this.networkUrlInput.value = window.location.href;
        }
        this.modalNetwork.style.display = 'flex';
    }

    async confirmShutdown() {
        const confirmed = confirm("Are you sure you want to stop the local neural model and shut down the server?");
        if (!confirmed) return;

        this.modalShutdown.style.display = 'flex';
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
            this.tabCamBrowser.classList.add('active');
            this.tabCamHost.classList.remove('active');
            this.clientVideo.style.display = 'block';
            this.serverVideoFeed.style.display = 'none';
            this.hostCamSelectWrap.style.display = 'none';
            this.browserCameraSelect.style.display = 'block';
            this.initBrowserCamera(this.selectedDeviceId);
        } else {
            this.tabCamHost.classList.add('active');
            this.tabCamBrowser.classList.remove('active');
            this.clientVideo.style.display = 'none';
            this.serverVideoFeed.style.display = 'block';
            this.hostCamSelectWrap.style.display = 'block';
            this.browserCameraSelect.style.display = 'none';
            if (this.frameInterval) clearInterval(this.frameInterval);
            this.serverVideoFeed.src = `/api/camera/stream?t=${Date.now()}`;
            this.videoResolutionTag.textContent = 'Host Camera 1080p';
        }
    }

    captureCurrentFrameBase64() {
        if (this.activeCameraSource === 'browser' && this.clientVideo.videoWidth > 0) {
            this.hiddenFrameCanvas.width = 1280;
            this.hiddenFrameCanvas.height = 720;
            const ctx = this.hiddenFrameCanvas.getContext('2d');
            ctx.drawImage(this.clientVideo, 0, 0, 1280, 720);
            return this.hiddenFrameCanvas.toDataURL('image/jpeg', 0.85).split(',')[1];
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

        // Instant Silence: Stop any assistant audio immediately to eliminate feedback
        if (this.ttsAudioPlayer) {
            this.ttsAudioPlayer.pause();
            this.ttsAudioPlayer.currentTime = 0;
        }

        this.isRecording = true;
        this.audioChunks = [];
        this.recognizedSpeechText = '';
        this.btnPtt.classList.add('recording');
        this.pttLabel.textContent = 'Listening...';
        this.audioStatusLabel.textContent = 'Listening';
        this.audioStatusLabel.className = 'audio-label active';

        // Start native browser SpeechRecognition in parallel if available
        if (this.speechRecognizer) {
            try { this.speechRecognizer.start(); } catch (e) {}
        }

        const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
        this.mediaRecorder = new MediaRecorder(this.micStream, { mimeType: mime });

        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
                this.audioChunks.push(e.data);
            }
        };

        this.mediaRecorder.onstop = () => this.processRecordedAudio();
        // Record in 100ms slices so no speech is clipped
        this.mediaRecorder.start(100);
    }

    stopRecording() {
        if (!this.isRecording) return;
        this.isRecording = false;
        this.btnPtt.classList.remove('recording');
        this.pttLabel.textContent = 'Hold to Speak';
        this.audioStatusLabel.textContent = 'Processing';

        if (this.speechRecognizer) {
            try { this.speechRecognizer.stop(); } catch (e) {}
        }

        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
    }

    processRecordedAudio() {
        this.textInput.placeholder = 'Ask what the camera sees or enter query...';

        if (this.audioChunks.length === 0 && !this.recognizedSpeechText) return;

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
                    fallback_text: this.recognizedSpeechText,
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
        this.showProcessing('Running Qwen2.5-VL GPU inference...');

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
        this.appendMessage('user', 'System visual scan request');
        this.showProcessing('Analyzing visual environment (Qwen2.5-VL)...');

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
            if (data.state === 'thinking') this.showProcessing('Analyzing visual context with Qwen2.5-VL...');
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
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;

        const header = document.createElement('div');
        header.className = 'bubble-header';

        const author = document.createElement('span');
        author.className = 'bubble-author';
        author.textContent = role === 'user' ? 'User' : 'Qwen2.5-VL';

        const timeSpan = document.createElement('span');
        timeSpan.className = 'bubble-time';
        const now = new Date();
        timeSpan.textContent = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;

        header.appendChild(author);
        header.appendChild(timeSpan);

        if (speechData && speechData.audio_base64) {
            const playBtn = document.createElement('button');
            playBtn.className = 'audio-play-btn';
            playBtn.textContent = 'Audio';
            playBtn.onclick = () => this.playSpeech(speechData.audio_base64);
            header.appendChild(playBtn);
        }

        const body = document.createElement('div');
        body.className = 'bubble-body';
        body.textContent = text;

        bubble.appendChild(header);
        bubble.appendChild(body);

        this.transcriptFeed.appendChild(bubble);
        this.transcriptFeed.scrollTop = this.transcriptFeed.scrollHeight;
    }

    showProcessing(label) {
        this.processingText.textContent = label;
        this.processingIndicator.style.display = 'flex';
    }

    hideProcessing() {
        this.processingIndicator.style.display = 'none';
        this.audioStatusLabel.textContent = 'Standby';
        this.audioStatusLabel.className = 'audio-label';
    }

    playSpeech(audioBase64) {
        if (!audioBase64) return;
        try {
            this.audioStatusLabel.textContent = 'Speaking';
            this.audioStatusLabel.className = 'audio-label active';

            this.ttsAudioPlayer.src = `data:audio/mp3;base64,${audioBase64}`;
            this.ttsAudioPlayer.play().catch(() => {});

            this.ttsAudioPlayer.onended = () => {
                this.audioStatusLabel.textContent = 'Standby';
                this.audioStatusLabel.className = 'audio-label';
                this.visualizer.setIdle();
            };
        } catch (e) {}
    }

    async fetchHostCamerasOnce() {
        try {
            const res = await fetch('/api/camera/devices');
            const data = await res.json();
            this.hostCameraSelect.innerHTML = '';
            data.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.index;
                opt.textContent = c.name;
                this.hostCameraSelect.appendChild(opt);
            });
        } catch (e) {}
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.vlaStudio = new VLAStudioApp();
});
