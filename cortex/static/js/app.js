/**
 * Cortex UI Application — Integrated Camera, Voice, and Multi-View Sync
 */

import { RobotFace } from './face.js';
import { LiveVoiceEngine } from './voice.js';

class CortexApp {
    constructor() {
        this.face = null;
        this.voice = null;
        this.ws = null;
        this.reconnectTimer = null;

        // Viewport mode: 'none' | 'camera' | 'browser' | 'dual'
        this.viewMode = 'none';
        this.liveVoiceActive = false;

        // Camera video stream
        this.cameraStream = null;
        this.snapshotInterval = null;

        this._cacheDOM();
        this._initFace();
        this._initVoice();
        this._bindEvents();
        this._connectWS();
    }

    _cacheDOM() {
        this.dom = {
            mainStage:           document.getElementById('main'),
            sidebar:             document.getElementById('sidebar'),
            sidebarCollapse:     document.getElementById('sidebar-collapse-btn'),
            sidebarExpand:       document.getElementById('sidebar-expand-btn'),
            // Viewport buttons
            cameraTriggerBtn:    document.getElementById('camera-trigger-btn'),
            browserTriggerBtn:   document.getElementById('browser-trigger-btn'),
            dualViewTriggerBtn:  document.getElementById('dual-view-trigger-btn'),
            // Screen Controls
            closeCameraBtn:      document.getElementById('close-camera-btn'),
            closeBrowserBtn:     document.getElementById('close-browser-btn'),
            camSplitBtn:         document.getElementById('cam-split-btn'),
            browserSplitBtn:     document.getElementById('browser-split-btn'),
            cameraScreen:        document.getElementById('camera-screen'),
            browserScreen:       document.getElementById('browser-screen'),
            browserUrlPill:      document.getElementById('browser-url-pill'),
            readerCategoryBadge: document.getElementById('reader-category-badge'),
            readerSourceBadge:   document.getElementById('reader-source-badge'),
            readerTimestamp:     document.getElementById('reader-timestamp'),
            readerHeadline:      document.getElementById('reader-headline'),
            readerContentBody:   document.getElementById('reader-content-body'),
            readerTakeawaysBox:  document.getElementById('reader-takeaways-box'),
            readerTakeawaysList: document.getElementById('reader-takeaways-list'),
            readerSourcesBar:    document.getElementById('reader-sources-bar'),
            readerSourcesPillRow:document.getElementById('reader-sources-pill-row'),
            webMediaContainer:   document.getElementById('web-media-container'),
            webMediaImg:         document.getElementById('web-media-img'),
            // Camera video elements
            cameraVideo:         document.getElementById('camera-video'),
            cameraCanvas:        document.getElementById('camera-snapshot-canvas'),
            // Status & Chat
            statusTitle:         document.getElementById('status-title'),
            statusSubtitle:      document.getElementById('status-subtitle'),
            chatMessages:        document.getElementById('chat-messages'),
            inputBar:            document.getElementById('input-bar'),
            chatInput:           document.getElementById('chat-input'),
            sendBtn:             document.getElementById('send-btn'),
            micBtn:              document.getElementById('mic-btn'),
            cycleBtn:            document.getElementById('cycle-btn'),
            devicesList:         document.getElementById('devices-list'),
            connBadge:           document.getElementById('connection-badge'),
            connBadgeText:       document.querySelector('#connection-badge .badge-text'),
            // Live Voice elements
            liveVoiceBtn:        document.getElementById('live-voice-btn'),
            waveformContainer:   document.getElementById('waveform-container'),
            voiceStatusLabel:    document.getElementById('voice-status-label'),
            voiceMuteBtn:        document.getElementById('voice-mute-btn'),
            voiceEndBtn:         document.getElementById('voice-end-btn'),
        };
    }

    _initFace() {
        try {
            this.face = new RobotFace();
        } catch (err) {
            console.error('Face init error:', err);
        }
    }

    _initVoice() {
        this.voice = new LiveVoiceEngine({
            onVolumeChange: (vol) => {
                if (this.face) {
                    this.face.setVoiceVolume(vol);
                }
            },
            onSpeakingStateChange: (isSpeaking) => {
                if (this.face) {
                    this._setState(isSpeaking ? 'speaking' : (this.viewMode !== 'none' ? 'seeing' : 'idle'));
                }
            },
            onSpeechRecognized: (transcript) => {
                // User voice command recognized — send to Cortex
                this._sendChatText(transcript);
            },
            onStateChange: (active, mode) => {
                this.liveVoiceActive = active;
                if (active) {
                    this.dom.inputBar.classList.add('live-active');
                    this.dom.liveVoiceBtn.classList.add('active');
                    this._setState('listening');
                    if (mode === 'simulated') {
                        this._addMessage('system', 'Live Talk active (Microphone simulated)');
                    } else {
                        this._addMessage('system', 'Live Talk active — listening for voice');
                    }
                } else {
                    this.dom.inputBar.classList.remove('live-active');
                    this.dom.liveVoiceBtn.classList.remove('active');
                    if (this.face && this.viewMode === 'none') {
                        this._setState('idle');
                    }
                }
            }
        });
    }

    _bindEvents() {
        this.dom.sidebarCollapse.addEventListener('click', () => {
            this.dom.sidebar.classList.add('collapsed');
        });

        this.dom.sidebarExpand.addEventListener('click', () => {
            this.dom.sidebar.classList.remove('collapsed');
        });

        this.dom.cameraTriggerBtn.addEventListener('click', () => {
            this.setViewMode(this.viewMode === 'camera' ? 'none' : 'camera');
        });

        this.dom.browserTriggerBtn.addEventListener('click', () => {
            this.setViewMode(this.viewMode === 'browser' ? 'none' : 'browser');
        });

        this.dom.dualViewTriggerBtn.addEventListener('click', () => {
            this.setViewMode(this.viewMode === 'dual' ? 'none' : 'dual');
        });

        this.dom.camSplitBtn.addEventListener('click', () => {
            this.setViewMode(this.viewMode === 'dual' ? 'camera' : 'dual');
        });

        this.dom.browserSplitBtn.addEventListener('click', () => {
            this.setViewMode(this.viewMode === 'dual' ? 'browser' : 'dual');
        });

        this.dom.closeCameraBtn.addEventListener('click', () => {
            this.setViewMode(this.viewMode === 'dual' ? 'browser' : 'none');
        });

        this.dom.closeBrowserBtn.addEventListener('click', () => {
            this.setViewMode(this.viewMode === 'dual' ? 'camera' : 'none');
        });

        this.dom.liveVoiceBtn.addEventListener('click', () => this.toggleLiveVoice());
        this.dom.micBtn.addEventListener('click', () => this.toggleLiveVoice());
        this.dom.voiceEndBtn.addEventListener('click', () => this.voice.stop());

        this.dom.voiceMuteBtn.addEventListener('click', () => {
            const isMuted = this.voice.toggleMute();
            this.dom.voiceMuteBtn.classList.toggle('active', isMuted);
            this.dom.voiceStatusLabel.textContent = isMuted ? 'MUTED' : 'LIVE TALK';
        });

        this.dom.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._sendChat();
            }
        });

        this.dom.sendBtn.addEventListener('click', () => this._sendChat());

        this.dom.cycleBtn.addEventListener('click', () => {
            this._wsSend({ type: 'demo_cycle' });
            this.dom.cycleBtn.disabled = true;
            this.dom.cycleBtn.textContent = 'Cycling…';
            setTimeout(() => {
                this.dom.cycleBtn.disabled = false;
                this.dom.cycleBtn.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="5 3 19 12 5 21 5 3"/>
                    </svg>
                    <span>Cycle Expressions</span>`;
            }, 18000);
        });
    }

    toggleLiveVoice() {
        if (this.liveVoiceActive) {
            this.voice.stop();
        } else {
            this.voice.start();
        }
    }

    async setViewMode(mode, data = null) {
        this.viewMode = mode;

        this.dom.mainStage.classList.remove('camera-active', 'browser-active', 'dual-active');
        this.dom.cameraTriggerBtn.classList.remove('active');
        this.dom.browserTriggerBtn.classList.remove('active');
        this.dom.dualViewTriggerBtn.classList.remove('active');

        if (data && (mode === 'browser' || mode === 'dual')) {
            this.updateBrowserContent(data);
        }

        const isCameraNeeded = (mode === 'camera' || mode === 'dual');
        if (isCameraNeeded) {
            await this._startCameraStream();
        } else {
            this._stopCameraStream();
        }

        switch (mode) {
            case 'camera':
                this.dom.mainStage.classList.add('camera-active');
                this.dom.cameraTriggerBtn.classList.add('active');
                this._setState('seeing');
                break;

            case 'browser':
                this.dom.mainStage.classList.add('browser-active');
                this.dom.browserTriggerBtn.classList.add('active');
                this._setState('thinking');
                break;

            case 'dual':
                this.dom.mainStage.classList.add('camera-active', 'browser-active', 'dual-active');
                this.dom.dualViewTriggerBtn.classList.add('active');
                this._setState('seeing');
                break;

            case 'none':
            default:
                this._setState(this.liveVoiceActive ? 'listening' : 'idle');
                break;
        }
    }

    async _startCameraStream() {
        if (this.cameraStream) return;
        try {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                this.cameraStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 1280 }, height: { ideal: 720 } },
                    audio: false
                });
                if (this.dom.cameraVideo) {
                    this.dom.cameraVideo.srcObject = this.cameraStream;
                    await this.dom.cameraVideo.play();
                }

                // Start periodic snapshot timer (sends frame to backend every 3s)
                clearInterval(this.snapshotInterval);
                this.snapshotInterval = setInterval(() => this._captureAndSendSnapshot(), 3000);
            }
        } catch (err) {
            console.warn('[Camera] WebRTC webcam access not granted or unavailable:', err);
        }
    }

    _stopCameraStream() {
        clearInterval(this.snapshotInterval);
        this.snapshotInterval = null;

        if (this.cameraStream) {
            this.cameraStream.getTracks().forEach(t => t.stop());
            this.cameraStream = null;
        }
        if (this.dom.cameraVideo) {
            this.dom.cameraVideo.srcObject = null;
        }
    }

    _captureAndSendSnapshot() {
        if (!this.dom.cameraVideo || !this.cameraStream) return;
        try {
            const video = this.dom.cameraVideo;
            const canvas = this.dom.cameraCanvas;
            if (!canvas || video.videoWidth === 0) return;

            canvas.width = 640;
            canvas.height = 360;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
            this._wsSend({
                type: 'camera_frame',
                frame: dataUrl
            });
        } catch (e) {
            console.warn('[Camera] Snapshot capture error:', e);
        }
    }

    updateBrowserContent(data) {
        if (!data) return;

        // 1. Browser address bar URL
        if (data.url && this.dom.browserUrlPill) {
            this.dom.browserUrlPill.textContent = data.url;
            this.dom.browserUrlPill.href = data.url;
        }

        // 2. Category badge
        if (this.dom.readerCategoryBadge) {
            this.dom.readerCategoryBadge.textContent = data.category || (data.is_news ? 'BREAKING NEWS' : 'WEB INTEL');
        }

        // 3. Source badge & timestamp
        if (this.dom.readerSourceBadge) {
            this.dom.readerSourceBadge.textContent = (data.publisher || data.domain || 'LIVE WIRE').toUpperCase();
        }
        if (this.dom.readerTimestamp) {
            this.dom.readerTimestamp.textContent = data.published_date || 'TODAY';
        }

        // 4. Headline
        if (this.dom.readerHeadline) {
            this.dom.readerHeadline.textContent = data.headline || data.title || 'Web Intelligence Briefing';
        }

        // 5. Image preview
        if (data.image_url && this.dom.webMediaContainer && this.dom.webMediaImg) {
            this.dom.webMediaImg.src = data.image_url;
            this.dom.webMediaContainer.style.display = 'flex';
        } else if (this.dom.webMediaContainer) {
            this.dom.webMediaContainer.style.display = 'none';
        }

        // 6. Narrative content body (Actual synthesized story / article content)
        if (this.dom.readerContentBody) {
            let bodyText = data.briefing || data.summary || '';
            // Strip out [LIVE BREAKING NEWS ...] or raw bracket headers if any
            bodyText = bodyText.replace(/^\[LIVE BREAKING NEWS INTEL:[^\]]+\]\s*/i, '');
            // Format markdown headers, bold, bullets
            let formatted = this._esc(bodyText)
                .replace(/^###\s*(.*$)/gm, '<h4 style="color:#c084fc;margin:8px 0 4px;">$1</h4>')
                .replace(/^##\s*(.*$)/gm, '<h3 style="color:#38bdf8;margin:10px 0 6px;">$1</h3>')
                .replace(/^•\s*(.*$)/gm, '<div style="margin:4px 0 4px 8px;"><span style="color:#38bdf8;font-weight:bold;">•</span> $1</div>')
                .replace(/^(\d+\.\s+\[.*?\])/gm, '<strong style="color:#38bdf8;">$1</strong>')
                .replace(/\n\n/g, '</p><p class="reader-paragraph">')
                .replace(/\n/g, '<br>');
            this.dom.readerContentBody.innerHTML = `<p class="reader-paragraph">${formatted}</p>`;
        }

        // 7. Key developments / highlights list
        if (this.dom.readerTakeawaysBox && this.dom.readerTakeawaysList) {
            const devs = data.developments || [];
            if (Array.isArray(devs) && devs.length > 0) {
                this.dom.readerTakeawaysList.innerHTML = '';
                for (const d of devs.slice(0, 6)) {
                    const text = typeof d === 'string' ? d : d.text;
                    const source = typeof d === 'object' ? d.source : null;
                    const item = document.createElement('div');
                    item.className = 'takeaway-item';
                    item.innerHTML = `
                        <span class="takeaway-bullet">›</span>
                        <div class="takeaway-text">
                            ${this._esc(text)}
                            ${source ? `<span class="takeaway-source-pill">${this._esc(source)}</span>` : ''}
                        </div>
                    `;
                    this.dom.readerTakeawaysList.appendChild(item);
                }
                this.dom.readerTakeawaysBox.style.display = 'flex';
            } else {
                this.dom.readerTakeawaysBox.style.display = 'none';
            }
        }

        // 8. Discreet Citations Bar at Bottom (Pills only, not giant link cards)
        if (this.dom.readerSourcesBar && this.dom.readerSourcesPillRow) {
            const sources = data.sources || (data.results ? data.results.map(r => ({ name: r.source || r.domain || 'Source', url: r.url })) : []);
            if (Array.isArray(sources) && sources.length > 0) {
                this.dom.readerSourcesPillRow.innerHTML = '';
                const seen = new Set();
                for (const s of sources) {
                    const name = (s.name || s.domain || 'Source').trim();
                    if (seen.has(name) || !s.url) continue;
                    seen.add(name);
                    const pill = document.createElement('a');
                    pill.className = 'source-chip';
                    pill.href = s.url;
                    pill.target = '_blank';
                    pill.rel = 'noopener noreferrer';
                    pill.textContent = `${name} ↗`;
                    this.dom.readerSourcesPillRow.appendChild(pill);
                    if (seen.size >= 6) break;
                }
                this.dom.readerSourcesBar.style.display = 'flex';
            } else {
                this.dom.readerSourcesBar.style.display = 'none';
            }
        }
    }

    _connectWS() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${proto}//${location.host}/ws`);

        this.ws.onopen = () => {
            this._setOnline(true);
            this._addMessage('system', 'Connected to Cortex Core');
        };

        this.ws.onmessage = (e) => {
            try {
                this._handleMessage(JSON.parse(e.data));
            } catch (err) {
                console.error('WS error:', err);
            }
        };

        this.ws.onclose = () => {
            this._setOnline(false);
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = setTimeout(() => this._connectWS(), 3000);
        };
    }

    _wsSend(data) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    _setOnline(online) {
        this.dom.connBadge.classList.toggle('online', online);
        this.dom.connBadgeText.textContent = online ? 'Online' : 'Offline';
    }

    _handleMessage(msg) {
        switch (msg.type) {
            case 'state_change':
                this._setState(msg.state);
                break;
            case 'set_view_mode':
                this.setViewMode(msg.mode, msg.data);
                break;
            case 'chat_message':
                this._addMessage(msg.role, msg.content);
                break;
            case 'voice_audio':
                // Play Neural Male Voice Audio through TTS engine with anti-echo text
                if (this.voice && msg.audio) {
                    this.voice.playAudio(msg.audio, msg.text || '');
                }
                break;
            case 'facial_expression':
                if (this.face) {
                    this.face.setExpression(msg);
                }
                break;
            case 'device_update':
                this._renderDevices(msg.devices);
                break;
        }
    }

    _setState(state) {
        if (this.face) {
            this.face.setState(state);
            const info = this.face.getStateInfo(state);
            this.dom.statusTitle.textContent = info.label;
            this.dom.statusSubtitle.textContent = info.subtext;
        }
    }

    _sendChat() {
        const text = this.dom.chatInput.value.trim();
        if (!text) return;
        this._sendChatText(text);
        this.dom.chatInput.value = '';
        this.dom.chatInput.focus();
    }

    _sendChatText(text) {
        if (!text) return;
        // Trigger a fresh snapshot if camera is active so Cortex sees current frame
        this._captureAndSendSnapshot();
        this._wsSend({ type: 'chat_message', content: text });
    }

    _addMessage(role, content) {
        const el = document.createElement('div');
        el.className = `message ${role}`;

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        if (role === 'system') {
            bubble.textContent = content;
        } else {
            bubble.innerHTML = this._formatMessageContent(content);
        }

        el.appendChild(bubble);
        this.dom.chatMessages.appendChild(el);
        this.dom.chatMessages.scrollTop = this.dom.chatMessages.scrollHeight;

        while (this.dom.chatMessages.children.length > 100) {
            this.dom.chatMessages.removeChild(this.dom.chatMessages.firstChild);
        }
    }

    _formatMessageContent(text) {
        if (!text) return '';
        
        // 1. Escape HTML entities
        let html = this._esc(text);

        // 2. Format Markdown Images: !\[(.*?)\]\((https?:\/\/[^\s\)]+)\)
        html = html.replace(/!\[(.*?)\]\((https?:\/\/[^\s\)]+)\)/g, (match, alt, url) => {
            return `<div class="chat-img-wrapper"><img src="${url}" alt="${alt || 'Image'}" class="chat-inline-img" loading="lazy" /></div>`;
        });

        // 3. Format Markdown Links: \[(.*?)\]\((https?:\/\/[^\s\)]+)\)
        html = html.replace(/\[(.*?)\]\((https?:\/\/[^\s\)]+)\)/g, (match, label, url) => {
            return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="chat-inline-link">${label || url} ↗</a>`;
        });

        // 4. Format Bold **text**
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // 5. Format Inline Code `code`
        html = html.replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>');

        // 6. Format Newlines
        html = html.replace(/\n/g, '<br>');

        return html;
    }

    _renderDevices(devices) {
        this.dom.devicesList.innerHTML = '';
        if (!devices || devices.length === 0) {
            this.dom.devicesList.innerHTML = '<div class="device-card empty">No devices connected</div>';
            return;
        }

        for (const dev of devices) {
            const card = document.createElement('div');
            card.className = 'device-card';
            card.innerHTML = `
                <div class="device-info">
                    <span class="device-dot ${dev.status}"></span>
                    <span class="device-name">${this._esc(dev.name)}</span>
                </div>
                <div class="device-meta">${this._esc(dev.detail || dev.status)}</div>
            `;
            this.dom.devicesList.appendChild(card);
        }
    }

    _esc(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.cortex = new CortexApp();
});
