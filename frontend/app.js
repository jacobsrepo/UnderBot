/**
 * Contender Tactical Studio - Client Controller
 * Autonomous Sensory Switching, Autonomous Hardware Flashing, Live Steps, Voice Barge-In & Mute Control
 */

class ContenderStudioApp {
    constructor() {
        this.ws = null;
        this.isRecording = false;
        this.isHandsFreeActive = true;
        this.isMuted = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.micStream = null;
        this.screenStream = null;
        this.cameraStream = null;
        this.activeVisionSource = 'screen';
        this.selectedDeviceId = null;
        this.isMiniHud = false;
        this.visualizer = null;
        this.screenFrameInterval = null;
        this.cameraFrameInterval = null;
        this.diagnosticsInterval = null;
        
        // Continuous Hands-Free Voice, Barge-In & Echo Rejection
        this.speechRecognizer = null;
        this.handsFreeSilenceTimer = null;
        this.currentSpokenSentence = '';
        this.isAssistantSpeaking = false;
        this.lastAssistantSpeech = '';

        // Elements
        this.screenVideo = document.getElementById('screen-video');
        this.clientVideo = document.getElementById('client-video');
        this.hiddenFrameCanvas = document.getElementById('hidden-frame-canvas');
        this.ttsAudioPlayer = document.getElementById('tts-audio-element');
        this.transcriptFeed = document.getElementById('transcript-feed');
        this.processingIndicator = document.getElementById('processing-indicator');
        this.processingText = document.getElementById('processing-text');
        this.btnPtt = document.getElementById('btn-ptt');
        this.pttLabel = document.getElementById('ptt-label');
        this.textInput = document.getElementById('text-input');
        this.btnSend = document.getElementById('btn-send');
        this.btnInspectFrame = document.getElementById('btn-inspect-frame');
        this.tabScreen = document.getElementById('tab-screen');
        this.tabCam = document.getElementById('tab-cam');
        this.browserCameraSelect = document.getElementById('browser-camera-select');
        this.visionModeTag = document.getElementById('vision-mode-tag');
        this.audioStatusLabel = document.getElementById('audio-status-label');
        
        // Mute Elements
        this.btnToggleMute = document.getElementById('btn-toggle-mute');
        this.btnMiniMute = document.getElementById('btn-mini-mute');
        this.iconMicUnmuted = document.getElementById('icon-mic-unmuted');
        this.iconMicMuted = document.getElementById('icon-mic-muted');
        this.labelMuteState = document.getElementById('label-mute-state');

        // Status Elements
        this.statusDot = document.getElementById('status-dot');
        this.statusModelName = document.getElementById('status-model-name');
        this.statusStateText = document.getElementById('status-state-text');
        this.diagEngineName = document.getElementById('diag-engine-name');
        this.diagSensoryMode = document.getElementById('diag-sensory-mode');
        this.diagStatusBadge = document.getElementById('diag-status-badge');

        // Mini HUD Elements
        this.miniHudWidget = document.getElementById('mini-hud-widget');
        this.mainStudioLayout = document.getElementById('main-studio-layout');
        this.btnToggleMiniHud = document.getElementById('btn-toggle-mini-hud');
        this.btnExpandStudio = document.getElementById('btn-expand-studio');
        this.miniStatusDot = document.getElementById('mini-status-dot');

        // Hardware Drawer Elements
        this.hardwareDrawer = document.getElementById('hardware-drawer');
        this.btnToggleHardware = document.getElementById('btn-toggle-hardware');
        this.selectComPorts = document.getElementById('select-com-ports');
        this.btnRefreshPorts = document.getElementById('btn-refresh-ports');
        this.btnConnectPort = document.getElementById('btn-connect-port');
        this.serialConsole = document.getElementById('serial-console');
        this.serialSendInput = document.getElementById('serial-send-input');
        this.btnSendSerial = document.getElementById('btn-send-serial');

        // Modals
        this.modalPreferences = document.getElementById('modal-preferences');
        this.btnOpenSettings = document.getElementById('btn-open-settings');
        this.btnModalClose = document.getElementById('btn-modal-close');
        this.btnModalCancel = document.getElementById('btn-modal-cancel');
        this.btnModalSave = document.getElementById('btn-modal-save');
        this.voiceSelect = document.getElementById('voice-select');
        this.btnStopSystem = document.getElementById('btn-stop-system');
        this.modalShutdown = document.getElementById('modal-shutdown');
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
        console.log('[Contender Studio] Initializing voice-interruption enabled assistant...');
        this.visualizer = new AudioSpectrumVisualizer('audio-waveform-canvas');

        const savedVoice = localStorage.getItem('vla_voice') || 'guy';
        this.voiceSelect.value = savedVoice;

        this.initWebSocket();
        await this.initMicrophone();
        await this.initContinuousScreenFeed();
        await this.initCameraFeed();
        this.initContinuousHandsFreeRecognition();
        this.initEventListeners();
        this.startDiagnosticsPolling();
        this.refreshHardwarePorts();
    }

    // ==================== MUTE CONTROLLER ====================

    toggleMute() {
        this.isMuted = !this.isMuted;
        if (this.isMuted) {
            if (this.micStream) {
                this.micStream.getAudioTracks().forEach(t => t.enabled = false);
            }
            if (this.speechRecognizer) {
                try { this.speechRecognizer.abort(); } catch (e) {}
            }
            this.iconMicUnmuted.style.display = 'none';
            this.iconMicMuted.style.display = 'inline-block';
            this.labelMuteState.textContent = 'Unmute';
            this.audioStatusLabel.textContent = 'Muted';
            this.audioStatusLabel.className = 'audio-label';
            this.pttLabel.textContent = 'Microphone Muted (Click Unmute or Type)';
            this.btnPtt.classList.add('muted');
            this.visualizer.setIdle();
        } else {
            if (this.micStream) {
                this.micStream.getAudioTracks().forEach(t => t.enabled = true);
            }
            this.iconMicUnmuted.style.display = 'inline-block';
            this.iconMicMuted.style.display = 'none';
            this.labelMuteState.textContent = 'Mute';
            this.audioStatusLabel.textContent = 'Hands-Free (Active)';
            this.audioStatusLabel.className = 'audio-label active';
            this.pttLabel.textContent = 'Hands-Free Listening ("Contender...")';
            this.btnPtt.classList.remove('muted');
            if (this.isHandsFreeActive && this.speechRecognizer) {
                try { this.speechRecognizer.start(); } catch (e) {}
            }
        }
    }

    // ==================== CONTINUOUS HANDS-FREE VOICE & BARGE-IN ====================

    initContinuousHandsFreeRecognition() {
        const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognitionClass) {
            console.log('[Voice] SpeechRecognition API not supported. Using push-to-talk.');
            return;
        }

        try {
            this.speechRecognizer = new SpeechRecognitionClass();
            this.speechRecognizer.continuous = true;
            this.speechRecognizer.interimResults = true;
            this.speechRecognizer.lang = 'en-US';

            this.speechRecognizer.onstart = () => {
                if (this.isHandsFreeActive && !this.isMuted) {
                    this.audioStatusLabel.textContent = this.isAssistantSpeaking ? 'Speaking (Speak to Interrupt)' : 'Hands-Free (Active)';
                    this.audioStatusLabel.className = 'audio-label active';
                }
            };

            this.speechRecognizer.onresult = (event) => {
                if (this.isMuted) return;

                let interim = '';
                let final = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript;
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }

                const currentText = (final || interim).trim();
                if (currentText) {
                    // VOICE BARGE-IN: If the assistant is speaking and user says anything, INSTANTLY CUT OFF SPEECH!
                    if (this.isAssistantSpeaking) {
                        console.log('[Voice] Barge-In Triggered! Silencing assistant speech instantly.');
                        this.interruptAssistant();
                    }

                    // Echo check
                    if (this.lastAssistantSpeech && currentText.toLowerCase().includes(this.lastAssistantSpeech.slice(0, 15).toLowerCase())) {
                        return;
                    }

                    this.currentSpokenSentence = currentText;
                    this.textInput.placeholder = `Hearing: "${currentText}"`;
                    this.audioStatusLabel.textContent = 'Hearing Voice...';

                    if (this.handsFreeSilenceTimer) clearTimeout(this.handsFreeSilenceTimer);

                    this.handsFreeSilenceTimer = setTimeout(() => {
                        this.commitHandsFreeUtterance();
                    }, 1000);
                }
            };

            this.speechRecognizer.onerror = (e) => {
                if (this.isHandsFreeActive && !this.isMuted) {
                    setTimeout(() => {
                        try { this.speechRecognizer.start(); } catch (err) {}
                    }, 800);
                }
            };

            this.speechRecognizer.onend = () => {
                if (this.isHandsFreeActive && !this.isMuted) {
                    setTimeout(() => {
                        try { this.speechRecognizer.start(); } catch (err) {}
                    }, 300);
                }
            };

            this.speechRecognizer.start();
            console.log('[Voice] Voice recognition with instant Barge-In active.');
        } catch (e) {
            console.warn('[Voice] Recognizer error:', e);
        }
    }

    commitHandsFreeUtterance() {
        if (this.isMuted) return;

        const text = this.currentSpokenSentence.trim();
        if (!text) return;

        this.currentSpokenSentence = '';
        this.textInput.placeholder = "Give command (e.g. 'minimize all windows', 'what's on my screen')...";
        
        console.log('[Voice] Dispatching query:', text);
        this.sendTextMessage(text);
    }

    // ==================== VISUAL STREAMS (SCREEN & CAMERA) ====================

    async initContinuousScreenFeed() {
        try {
            if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
                this.screenStream = await navigator.mediaDevices.getDisplayMedia({
                    video: { frameRate: 15, width: { ideal: 1920 }, height: { ideal: 1080 } }
                });
                this.screenVideo.srcObject = this.screenStream;
                this.screenVideo.play();
            }
        } catch (e) {
            console.log('[Screen] Using native desktop background screen capture.');
        }

        if (this.screenFrameInterval) clearInterval(this.screenFrameInterval);
        this.screenFrameInterval = setInterval(() => this.broadcastScreenFrame(), 800);
    }

    async initCameraFeed() {
        try {
            if (this.cameraStream) {
                this.cameraStream.getTracks().forEach(t => t.stop());
            }

            const constraints = {
                video: { width: { ideal: 1280 }, height: { ideal: 720 } }
            };
            if (this.selectedDeviceId) {
                constraints.video.deviceId = { exact: this.selectedDeviceId };
            }

            this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.clientVideo.srcObject = this.cameraStream;
            this.clientVideo.play();
            await this.enumerateCameras();

            if (this.cameraFrameInterval) clearInterval(this.cameraFrameInterval);
            this.cameraFrameInterval = setInterval(() => this.broadcastCameraFrame(), 800);
        } catch (e) {
            console.warn('[Camera] Notice:', e);
        }
    }

    async enumerateCameras() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(d => d.kind === 'videoinput');
            this.browserCameraSelect.innerHTML = '';
            videoDevices.forEach((device, index) => {
                const opt = document.createElement('option');
                opt.value = device.deviceId;
                opt.textContent = device.label || `Camera ${index + 1}`;
                if (this.selectedDeviceId === device.deviceId) opt.selected = true;
                this.browserCameraSelect.appendChild(opt);
            });
        } catch (e) {}
    }

    async initMicrophone() {
        try {
            if (this.micStream) {
                this.micStream.getTracks().forEach(t => t.stop());
            }

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
            console.log('[Audio] Isolated microphone stream online.');
        } catch (e) {
            console.warn('[Audio] Mic issue:', e);
        }
    }

    // ==================== AUTOMATIC SENSORY SWITCHING ====================

    switchVisionSource(source) {
        if (this.activeVisionSource === source) return;
        this.activeVisionSource = source;

        if (source === 'screen') {
            this.tabScreen.classList.add('active');
            this.tabCam.classList.remove('active');
            this.screenVideo.style.display = 'block';
            this.clientVideo.style.display = 'none';
            this.browserCameraSelect.style.display = 'none';
            this.visionModeTag.textContent = 'Continuous Screen';
            this.diagSensoryMode.textContent = 'Continuous Screen (GPU Accelerated)';
        } else {
            this.tabCam.classList.add('active');
            this.tabScreen.classList.remove('active');
            this.screenVideo.style.display = 'none';
            this.clientVideo.style.display = 'block';
            this.browserCameraSelect.style.display = 'block';
            this.visionModeTag.textContent = 'Physical Camera';
            this.diagSensoryMode.textContent = 'Physical Camera (1080p)';
        }
    }

    captureFrameBase64(videoElement) {
        if (videoElement && videoElement.videoWidth > 0) {
            this.hiddenFrameCanvas.width = 1280;
            this.hiddenFrameCanvas.height = 720;
            const ctx = this.hiddenFrameCanvas.getContext('2d');
            ctx.drawImage(videoElement, 0, 0, 1280, 720);
            return this.hiddenFrameCanvas.toDataURL('image/jpeg', 0.85).split(',')[1];
        }
        return null;
    }

    broadcastScreenFrame() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const b64 = this.captureFrameBase64(this.screenVideo);
            if (b64) {
                this.ws.send(JSON.stringify({ type: 'screen_frame', image_base64: b64 }));
            }
        }
    }

    broadcastCameraFrame() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const b64 = this.captureFrameBase64(this.clientVideo);
            if (b64) {
                this.ws.send(JSON.stringify({ type: 'client_frame', image_base64: b64 }));
            }
        }
    }

    // ==================== WEBSOCKET & ACTION DISPATCH ====================

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

    sendTextMessage(overrideText = null) {
        const text = overrideText || this.textInput.value.trim();
        if (!text) return;

        if (!overrideText) this.textInput.value = '';

        this.appendMessage('user', text);
        this.showProcessing('Contender executing directive...');

        const screenB64 = this.captureFrameBase64(this.screenVideo);
        const camB64 = this.captureFrameBase64(this.clientVideo);

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'text_query',
                text: text,
                screen_base64: screenB64,
                camera_base64: camB64
            }));
        }
    }

    handleServerEvent(data) {
        if (!data || !data.type) return;

        if (data.type === 'status_update') {
            if (data.state === 'thinking') this.showProcessing('Analyzing directive and compiling actions...');
            else if (data.state === 'transcribing') this.showProcessing('Transcribing speech...');
            else if (data.state === 'idle') this.hideProcessing();
        } else if (data.type === 'progress_update') {
            this.showProcessing(data.message);
            this.appendSerialLine(`[Contender] ${data.message}`);
        } else if (data.type === 'stt_result') {
            if (data.auto_vision) {
                this.switchVisionSource(data.auto_vision);
            }
        } else if (data.type === 'brain_response') {
            this.hideProcessing();
            
            if (data.auto_vision) {
                this.switchVisionSource(data.auto_vision);
            }

            const reply = data.response || 'Mission confirmed.';
            this.lastAssistantSpeech = reply;
            this.appendMessage('assistant', reply, data.speech, data.action_card);

            if (data.speech && data.speech.audio_base64) {
                this.playSpeech(data.speech.audio_base64);
            }

            if (data.action_card && data.action_card.type === 'hardware_flash') {
                this.refreshHardwarePorts();
            }
        } else if (data.type === 'serial_telemetry') {
            this.appendSerialLine(data.data);
        }
    }

    playSpeech(audioBase64) {
        if (!audioBase64) return;
        try {
            this.isAssistantSpeaking = true;
            this.audioStatusLabel.textContent = 'Speaking (Speak to Interrupt)';
            this.audioStatusLabel.className = 'audio-label active';

            this.ttsAudioPlayer.src = `data:audio/mp3;base64,${audioBase64}`;
            this.ttsAudioPlayer.play().catch(() => {});

            this.ttsAudioPlayer.onended = () => {
                this.isAssistantSpeaking = false;
                if (!this.isMuted) {
                    this.audioStatusLabel.textContent = 'Hands-Free (Active)';
                    this.audioStatusLabel.className = 'audio-label active';
                }
                this.visualizer.setIdle();
            };
        } catch (e) {
            this.isAssistantSpeaking = false;
        }
    }

    interruptAssistant() {
        if (this.ttsAudioPlayer) {
            this.ttsAudioPlayer.pause();
            this.ttsAudioPlayer.currentTime = 0;
        }
        this.isAssistantSpeaking = false;
        if (!this.isMuted) {
            this.audioStatusLabel.textContent = 'Hands-Free (Active)';
            this.audioStatusLabel.className = 'audio-label active';
        }
        this.visualizer.setIdle();
    }

    appendMessage(role, text, speechData = null, actionCard = null) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;

        const header = document.createElement('div');
        header.className = 'bubble-header';

        const author = document.createElement('span');
        author.className = 'bubble-author';
        author.textContent = role === 'user' ? 'Operator' : 'Contender';

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

        if (actionCard) {
            const cardEl = document.createElement('div');
            cardEl.className = 'action-card';
            cardEl.innerHTML = `<span class="action-card-icon">⚡</span> <strong>[ACTION]</strong> ${actionCard.title || 'Task Executed'} - <em>${actionCard.status || ''}</em>`;
            bubble.appendChild(cardEl);
        }

        this.transcriptFeed.appendChild(bubble);
        this.transcriptFeed.scrollTop = this.transcriptFeed.scrollHeight;
    }

    showProcessing(label) {
        this.processingText.textContent = label;
        this.processingIndicator.style.display = 'flex';
    }

    hideProcessing() {
        this.processingIndicator.style.display = 'none';
        if (!this.isMuted) {
            this.audioStatusLabel.textContent = 'Hands-Free (Active)';
            this.audioStatusLabel.className = 'audio-label active';
        }
    }

    // ==================== EVENT LISTENERS & MODALS ====================

    initEventListeners() {
        this.btnToggleMute.addEventListener('click', () => this.toggleMute());
        if (this.btnMiniMute) {
            this.btnMiniMute.addEventListener('click', () => this.toggleMute());
        }

        this.tabScreen.addEventListener('click', () => this.switchVisionSource('screen'));
        this.tabCam.addEventListener('click', () => this.switchVisionSource('camera'));

        this.browserCameraSelect.addEventListener('change', (e) => {
            this.selectedDeviceId = e.target.value;
            this.initCameraFeed();
        });

        // Mini HUD Toggle
        this.btnToggleMiniHud.addEventListener('click', () => this.toggleMiniHud(true));
        this.btnExpandStudio.addEventListener('click', () => this.toggleMiniHud(false));

        // Hardware Drawer Toggle
        this.btnToggleHardware.addEventListener('click', () => {
            const isHidden = this.hardwareDrawer.style.display === 'none';
            this.hardwareDrawer.style.display = isHidden ? 'flex' : 'none';
            if (isHidden) this.refreshHardwarePorts();
        });

        this.btnRefreshPorts.addEventListener('click', () => this.refreshHardwarePorts());
        this.btnConnectPort.addEventListener('click', () => this.togglePortConnection());
        this.btnSendSerial.addEventListener('click', () => this.sendSerialCommand());
        this.serialSendInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.sendSerialCommand();
        });

        // Click on transcript feed or press Space/Esc to instantly interrupt speech
        this.transcriptFeed.addEventListener('click', () => {
            if (this.isAssistantSpeaking) this.interruptAssistant();
        });

        window.addEventListener('keydown', (e) => {
            if (this.isAssistantSpeaking && (e.code === 'Escape' || e.code === 'Space')) {
                e.preventDefault();
                this.interruptAssistant();
            }
        });

        this.btnSend.addEventListener('click', () => this.sendTextMessage());
        this.textInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.sendTextMessage();
        });

        this.btnInspectFrame.addEventListener('click', () => {
            this.sendTextMessage("Contender, inspect the visual context and report key status.");
        });

        // Modals
        this.btnNetworkConnect.addEventListener('click', () => this.openNetworkModal());
        this.btnCloseNetwork.addEventListener('click', () => { this.modalNetwork.style.display = 'none'; });
        this.btnCloseNetworkFooter.addEventListener('click', () => { this.modalNetwork.style.display = 'none'; });
        this.btnCopyNetworkUrl.addEventListener('click', () => {
            navigator.clipboard.writeText(this.networkUrlInput.value);
            this.btnCopyNetworkUrl.textContent = 'Copied!';
            setTimeout(() => { this.btnCopyNetworkUrl.textContent = 'Copy'; }, 2000);
        });

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

        this.btnStopSystem.addEventListener('click', () => this.confirmShutdown());
    }

    toggleMiniHud(enable) {
        this.isMiniHud = enable;
        if (enable) {
            this.mainStudioLayout.style.display = 'none';
            this.miniHudWidget.style.display = 'flex';
            if (window.pywebview && window.pywebview.api) {
                try { window.pywebview.api.toggle_mini_mode(); } catch (e) {}
            }
        } else {
            this.miniHudWidget.style.display = 'none';
            this.mainStudioLayout.style.display = 'flex';
            if (window.pywebview && window.pywebview.api) {
                try { window.pywebview.api.expand_studio_mode(); } catch (e) {}
            }
        }
    }

    // Hardware Drawer Methods
    async refreshHardwarePorts() {
        try {
            const res = await fetch('/api/embedded/ports');
            const ports = await res.json();
            this.selectComPorts.innerHTML = '';
            if (ports.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'No COM ports detected';
                this.selectComPorts.appendChild(opt);
                return;
            }
            ports.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.port;
                opt.textContent = `${p.port} - ${p.board_type}`;
                if (p.is_active) opt.selected = true;
                this.selectComPorts.appendChild(opt);
            });
        } catch (e) {}
    }

    async togglePortConnection() {
        const port = this.selectComPorts.value;
        if (!port) return;
        if (this.btnConnectPort.textContent === 'Connect') {
            const res = await fetch('/api/embedded/serial/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ port: port, baudrate: 115200 })
            });
            const data = await res.json();
            if (data.success) {
                this.btnConnectPort.textContent = 'Disconnect';
                this.btnConnectPort.className = 'control-btn btn-danger';
                this.appendSerialLine(`[Contender] Connected to ${port} @ 115200 baud.`);
            }
        } else {
            await fetch('/api/embedded/serial/disconnect', { method: 'POST' });
            this.btnConnectPort.textContent = 'Connect';
            this.btnConnectPort.className = 'control-btn btn-primary';
            this.appendSerialLine(`[Contender] Disconnected from serial port.`);
        }
    }

    async sendSerialCommand() {
        const text = this.serialSendInput.value.trim();
        if (!text) return;
        this.serialSendInput.value = '';
        await fetch('/api/embedded/serial/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: text })
        });
        this.appendSerialLine(`> ${text}`);
    }

    appendSerialLine(text) {
        const line = document.createElement('div');
        line.className = 'console-line';
        line.textContent = text;
        this.serialConsole.appendChild(line);
        this.serialConsole.scrollTop = this.serialConsole.scrollHeight;
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
        const confirmed = confirm("Power down Contender tactical core and shut down server?");
        if (!confirmed) return;

        this.modalShutdown.style.display = 'flex';
        try {
            await fetch('/api/system/shutdown', { method: 'POST' });
        } catch (e) {}

        setTimeout(() => {
            if (window.pywebview && window.pywebview.api) {
                try { window.pywebview.api.close_app(); } catch (e) {}
            } else {
                window.close();
            }
        }, 1200);
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
                        this.miniStatusDot.className = 'mini-status-dot';
                        this.statusModelName.textContent = 'Contender Core';
                        this.statusStateText.textContent = 'Ready (Tactical Mode)';
                        this.diagStatusBadge.className = 'diag-badge';
                        this.diagStatusBadge.textContent = 'ONLINE & READY';
                    } else if (brain.is_starting) {
                        this.statusDot.className = 'status-dot loading';
                        this.statusStateText.textContent = 'Loading neural core...';
                        this.diagStatusBadge.className = 'diag-badge loading';
                        this.diagStatusBadge.textContent = 'INITIALIZING...';
                    }
                }
            } catch (err) {}
        };

        updateDiagnostics();
        this.diagnosticsInterval = setInterval(updateDiagnostics, 3000);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.contenderStudio = new ContenderStudioApp();
});
