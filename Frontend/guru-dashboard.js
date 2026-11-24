/**
 * Bharat Study Buddy — Dashboard Guru Floating Voice Assistant (JS)
 *
 * Requirements:
 * - Floating assistant widget on all dashboard views (fixed bottom-right corner)
 * - Opens panel with:
 *   1. Guru heading and status
 *   2. Voice chat interface with microphone and voice controls (Orb, canvas, continuous toggle, stop)
 *   3. Text conversation area immediately below voice chat interface
 * - Text conversation area displays user message and complete written response directly below it
 * - Voice + text in Hindi, English, Hinglish
 * - Interruptibility and stop controls
 * - Does NOT restart listening when muted or closed
 * - Preserves RAG, Paper Analyzer, Smart Notes, Flashcards, Practice Papers, Study Planner, Exam Dates
 */

(function () {
    const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
        ? "http://127.0.0.1:5000"
        : "https://bharat-study-buddy.onrender.com";

    // Assistant State
    let isOpen = false;
    let state = "idle"; // "idle" | "listening" | "thinking" | "speaking" | "muted"
    let continuousMode = false;
    let voiceOutputEnabled = true;
    let recognition = null;
    let isWebSpeechRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let currentAudio = null;
    let studentContext = null;
    let conversationHistory = [];
    let animationFrameId = null;

    // Academic tools state
    let flashcardsList = [];
    let currentCardIndex = 0;
    let isCardFlipped = false;

    // DOM Elements Cache
    let launcherBtn, popup, closeBtn, voiceToggleBtn;
    let statusBadge, statusText, orbBtn, waveformCanvas, heroTranscript;
    let continuousSwitch, stopSpeakingBtn, chatFeed, chatInput, chatMicBtn, chatSendBtn;

    let ctx = null;

    function initGuruDashboard() {
        createFloatingWidgetElements();
        setupCanvas();
        setupSpeechRecognition();
        setupEventListeners();
        loadGuruContext();
        startWaveformAnimation();
    }

    // =========================================================
    // DYNAMIC DOM CREATION (FLOATING LAUNCHER + PANEL)
    // =========================================================

    function createFloatingWidgetElements() {
        // 1. Floating Launcher Button
        launcherBtn = document.createElement("button");
        launcherBtn.className = "guru-launcher guru-dashboard-launcher";
        launcherBtn.setAttribute("id", "guruDashboardLauncher");
        launcherBtn.setAttribute("title", "Talk to Guru (Personal AI Voice Assistant)");
        launcherBtn.setAttribute("aria-label", "Talk to Guru");
        launcherBtn.innerHTML = `
            <div class="guru-launcher-icon">
                🤖
                <span class="guru-pulse-dot"></span>
            </div>
            <span>Talk to Guru</span>
        `;
        document.body.appendChild(launcherBtn);

        // 2. Floating Assistant Panel
        popup = document.createElement("div");
        popup.className = "guru-popup guru-dashboard-popup";
        popup.setAttribute("id", "guruDashboardPopup");
        popup.setAttribute("role", "dialog");
        popup.setAttribute("aria-label", "Guru AI Voice Assistant");
        popup.innerHTML = `
            <!-- 1. GURU HEADING AND STATUS -->
            <div class="guru-header">
                <div class="guru-header-info">
                    <div class="guru-avatar">🤖</div>
                    <div class="guru-header-text">
                        <h3>Guru — Personal AI Tutor</h3>
                        <p><span></span> Online • Voice Assistant</p>
                    </div>
                </div>
                <div class="guru-header-actions">
                    <button class="guru-icon-btn active" id="guruVoiceToggleBtn" title="Toggle Voice Output (Mute/Unmute)" aria-label="Toggle Voice Output">
                        🔊
                    </button>
                    <button class="guru-icon-btn" id="guruClosePopupBtn" title="Close Guru" aria-label="Close Guru">
                        ✕
                    </button>
                </div>
            </div>

            <!-- 2. VOICE CHAT INTERFACE WITH MICROPHONE & CONTROLS -->
            <div class="guru-voice-box">
                <div class="guru-voice-top-row">
                    <div class="guru-status-badge idle" id="guruStatusBadge">
                        <span class="guru-status-dot"></span>
                        <span id="guruStatusText">IDLE</span>
                    </div>

                    <div class="guru-voice-controls">
                        <div class="guru-toggle-wrap" title="When ON, Guru automatically listens after speaking">
                            <span>Continuous</span>
                            <label class="guru-switch">
                                <input type="checkbox" id="guruContinuousSwitch">
                                <span class="guru-slider"></span>
                            </label>
                        </div>

                        <button type="button" class="guru-stop-btn" id="guruStopSpeakingBtn" title="Stop speaking">
                            ⏹ Stop
                        </button>
                    </div>
                </div>

                <!-- Central Voice Orb -->
                <div class="guru-orb-stage">
                    <div class="guru-orb-ring r1"></div>
                    <div class="guru-orb-ring r2"></div>
                    <button type="button" class="guru-orb-btn" id="guruOrbBtn" title="Click to speak or toggle conversation" aria-label="Guru Voice Orb">
                        🤖
                    </button>
                </div>

                <!-- Live Waveform Animation -->
                <div class="guru-waveform-container" aria-label="Audio Visualizer">
                    <canvas id="guruWaveformCanvas" width="220" height="28" aria-hidden="true" role="presentation"></canvas>
                </div>

                <!-- Live Spoken Prompt / Status Text -->
                <p class="guru-hero-transcript" id="guruHeroTranscript">
                    Tap Orb or speak in Hindi, English, or Hinglish
                </p>

                <!-- Quick Academic Tool Chips -->
                <div class="guru-tool-chips">
                    <button type="button" class="guru-tool-chip" id="toolTodayStudy">🎯 What to study today?</button>
                    <button type="button" class="guru-tool-chip" id="toolPaperAnalyzer">📊 Paper Analyzer</button>
                    <button type="button" class="guru-tool-chip" id="toolSmartNotes">📒 Smart Notes</button>
                    <button type="button" class="guru-tool-chip" id="toolFlashcards">📇 Flashcards</button>
                    <button type="button" class="guru-tool-chip" id="toolPracticePaper">📝 Practice Test</button>
                    <button type="button" class="guru-tool-chip" id="toolExamDates">📅 Exam Dates</button>
                </div>
            </div>

            <!-- 3. TEXT CONVERSATION AREA IMMEDIATELY BELOW VOICE CHAT INTERFACE -->
            <div class="guru-chat-area">
                <div class="guru-chat-feed" id="guruChatFeed">
                    <div class="guru-bubble bot">
                        <div class="guru-bubble-content">
                            Namaste! 🙏 I am <strong>Guru</strong>, your personal AI study assistant.
                            <br><br>
                            Speak to me using the Orb above or type below. I can answer from your uploaded materials, advise what to study today based on your exam dates, or generate smart notes and flashcards!
                        </div>
                        <div class="guru-bubble-meta">
                            <span>Ready</span>
                        </div>
                    </div>
                </div>

                <!-- Input Footer -->
                <div class="guru-chat-footer">
                    <button type="button" class="guru-chat-mic-btn" id="guruChatMicBtn" title="Speak question" aria-label="Voice Input">
                        🎙️
                    </button>
                    <input type="text" class="guru-chat-input" id="guruChatInput" placeholder="Ask Guru in Hindi, English, or Hinglish..." autocomplete="off">
                    <button type="button" class="guru-chat-send-btn" id="guruChatSendBtn" title="Send message" aria-label="Send">
                        ➤
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(popup);

        // Bind References
        closeBtn = document.getElementById("guruClosePopupBtn");
        voiceToggleBtn = document.getElementById("guruVoiceToggleBtn");
        statusBadge = document.getElementById("guruStatusBadge");
        statusText = document.getElementById("guruStatusText");
        orbBtn = document.getElementById("guruOrbBtn");
        waveformCanvas = document.getElementById("guruWaveformCanvas");
        heroTranscript = document.getElementById("guruHeroTranscript");
        continuousSwitch = document.getElementById("guruContinuousSwitch");
        stopSpeakingBtn = document.getElementById("guruStopSpeakingBtn");
        chatFeed = document.getElementById("guruChatFeed");
        chatInput = document.getElementById("guruChatInput");
        chatMicBtn = document.getElementById("guruChatMicBtn");
        chatSendBtn = document.getElementById("guruChatSendBtn");
    }

    function setupCanvas() {
        if (!waveformCanvas) return;
        ctx = waveformCanvas.getContext("2d");
        waveformCanvas.width = waveformCanvas.parentElement.clientWidth || 220;
        waveformCanvas.height = 28;
    }

    // =========================================================
    // OPEN / CLOSE FLOATING PANEL
    // =========================================================

    function togglePopup() {
        isOpen = !isOpen;
        popup.classList.toggle("active", isOpen);
        launcherBtn.style.display = isOpen ? "none" : "flex";

        if (isOpen) {
            setupCanvas();
            chatInput?.focus();
            if (chatFeed) chatFeed.scrollTop = chatFeed.scrollHeight;
        } else {
            // Strict requirement: stop audio and do NOT auto-listen when closed
            stopSpeaking();
            stopListening();
        }
    }

    function closePopup() {
        isOpen = false;
        popup.classList.remove("active");
        launcherBtn.style.display = "flex";
        // Stop audio and listening
        stopSpeaking();
        stopListening();
    }

    // =========================================================
    // STATE MANAGEMENT
    // =========================================================

    function setState(newState, message) {
        state = newState;

        if (statusBadge && statusText) {
            statusBadge.className = `guru-status-badge ${newState}`;
            statusText.textContent = newState.toUpperCase();
        }

        if (orbBtn) {
            orbBtn.className = `guru-orb-btn ${newState}`;
            if (newState === "listening") orbBtn.textContent = "🎙️";
            else if (newState === "speaking") orbBtn.textContent = "🔊";
            else if (newState === "thinking") orbBtn.textContent = "✦";
            else orbBtn.textContent = "🤖";
        }

        if (stopSpeakingBtn) {
            stopSpeakingBtn.classList.toggle("active", newState === "speaking");
        }

        if (message && heroTranscript) {
            heroTranscript.textContent = message;
        }
    }

    // =========================================================
    // ANIMATED AUDIO WAVEFORM VISUALIZER
    // =========================================================

    function startWaveformAnimation() {
        if (!ctx) return;

        let phase = 0;
        function draw() {
            if (!waveformCanvas) return;
            ctx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);
            const w = waveformCanvas.width;
            const h = waveformCanvas.height;
            const centerY = h / 2;

            phase += 0.08;

            if (state === "listening") {
                // Vibrant green soundwave bars
                const barCount = 22;
                const barW = (w / barCount) - 3;
                ctx.fillStyle = "#10b981";

                for (let i = 0; i < barCount; i++) {
                    const amp = Math.sin(phase + i * 0.45) * 0.5 + 0.5;
                    const barH = Math.max(3, amp * (h - 6));
                    const x = i * (barW + 3);
                    const y = centerY - barH / 2;
                    ctx.beginPath();
                    ctx.roundRect(x, y, barW, barH, 2);
                    ctx.fill();
                }
            } else if (state === "speaking") {
                // Blue equalizer wave
                ctx.strokeStyle = "#38bdf8";
                ctx.lineWidth = 2.5;
                ctx.beginPath();
                for (let x = 0; x < w; x++) {
                    const y = centerY + Math.sin(x * 0.06 + phase * 2) * (8 + Math.sin(phase) * 4);
                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();

                ctx.strokeStyle = "rgba(129, 140, 248, 0.45)";
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                for (let x = 0; x < w; x++) {
                    const y = centerY + Math.cos(x * 0.09 - phase) * 6;
                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            } else if (state === "thinking") {
                // Purple shimmering wave
                ctx.strokeStyle = "#c084fc";
                ctx.lineWidth = 2;
                ctx.beginPath();
                for (let x = 0; x < w; x++) {
                    const y = centerY + Math.sin(x * 0.04 + phase * 1.5) * 5;
                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            } else if (state === "muted") {
                // Flat red line
                ctx.strokeStyle = "#ef4444";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(8, centerY);
                ctx.lineTo(w - 8, centerY);
                ctx.stroke();
            } else {
                // Idle gentle breathing line
                ctx.strokeStyle = "rgba(224, 231, 255, 0.4)";
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                for (let x = 0; x < w; x++) {
                    const y = centerY + Math.sin(x * 0.03 + phase * 0.5) * 2.5;
                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            }

            animationFrameId = requestAnimationFrame(draw);
        }

        draw();
    }

    // =========================================================
    // SPEECH RECOGNITION (STT) & CONTINUOUS VOICE
    // =========================================================

    function setupSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("Web Speech API not available. Whisper fallback active.");
            return;
        }

        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = "en-IN"; // Supports bilingual Indian accents & Hindi terms

        recognition.onstart = () => {
            isWebSpeechRecording = true;
            setState("listening", "Listening to you... (Hindi / English / Hinglish)");
            if (chatMicBtn) chatMicBtn.classList.add("recording");
        };

        recognition.onresult = (event) => {
            let finalTranscript = "";
            let interimTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            if (heroTranscript) {
                heroTranscript.textContent = `"${interimTranscript || finalTranscript}"`;
            }

            if (finalTranscript.trim()) {
                if (chatInput) chatInput.value = finalTranscript.trim();
                stopListening();
                handleSendQuestion(finalTranscript.trim());
            }
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            stopListening();
            if (event.error === "not-allowed") {
                setState("idle", "Microphone blocked. Please allow mic access in browser.");
            } else {
                setState("idle", "Tap Orb or speak to ask Guru.");
            }
        };

        recognition.onend = () => {
            isWebSpeechRecording = false;
            if (chatMicBtn) chatMicBtn.classList.remove("recording");
            if (state === "listening") {
                setState("idle", "Tap Orb to speak with Guru.");
            }
        };
    }

    function startListening() {
        if (!isOpen) return;
        stopSpeaking();

        if (recognition) {
            try {
                recognition.start();
            } catch (err) {
                console.warn("Recognition start error:", err);
            }
        } else {
            startMediaRecorderFallback();
        }
    }

    function stopListening() {
        if (recognition && isWebSpeechRecording) {
            try {
                recognition.stop();
            } catch (e) { }
        }
        isWebSpeechRecording = false;
        if (chatMicBtn) chatMicBtn.classList.remove("recording");
    }

    function startMediaRecorderFallback() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert("Microphone not supported in this browser.");
            return;
        }

        navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
                setState("thinking", "Transcribing with Groq Whisper...");
                const formData = new FormData();
                formData.append("audio", audioBlob, "voice_input.webm");

                try {
                    const res = await fetch(`${API_BASE}/api/guru/transcribe`, {
                        method: "POST",
                        body: formData,
                        credentials: "include"
                    });
                    const d = await res.json();
                    if (d.success && d.text) {
                        handleSendQuestion(d.text);
                    } else {
                        setState("idle", "Could not catch that. Please speak again.");
                    }
                } catch (err) {
                    console.error("Whisper transcription error:", err);
                    setState("idle", "Transcription failed. Please try again.");
                }
            };

            mediaRecorder.start();
            setState("listening", "Listening via Groq Whisper... (Tap Orb when done)");
        }).catch((err) => {
            console.error("Mic error:", err);
            setState("idle", "Microphone permission required.");
        });
    }

    function toggleOrbListening() {
        if (state === "speaking") {
            // Interrupt speech immediately!
            stopSpeaking();
            startListening();
            return;
        }

        if (state === "listening") {
            stopListening();
            if (mediaRecorder && mediaRecorder.state === "recording") {
                mediaRecorder.stop();
            }
            setState("idle", "Listening paused. Tap Orb to speak.");
        } else {
            startListening();
        }
    }

    // =========================================================
    // TEXT TO SPEECH (VOICE OUTPUT) & INTERRUPTIBILITY
    // =========================================================

    function speakGuruResponse(text) {
        stopSpeaking();

        if (!voiceOutputEnabled) {
            onSpeechFinished();
            return;
        }

        setState("speaking", "Guru is speaking...");

        // Clean text for natural speech
        const cleanText = text
            .replace(/\[.*?\]/g, "")
            .replace(/[*#_`~>]/g, "")
            .replace(/\n+/g, ". ")
            .trim();

        const ttsUrl = `${API_BASE}/api/guru/tts?text=${encodeURIComponent(cleanText.slice(0, 450))}`;
        currentAudio = new Audio(ttsUrl);

        currentAudio.onended = () => {
            currentAudio = null;
            onSpeechFinished();
        };

        currentAudio.onerror = (e) => {
            console.warn("Server TTS play error, using browser SpeechSynthesis fallback:", e);
            speakBrowserUtterance(cleanText);
        };

        currentAudio.play().catch((err) => {
            console.warn("Audio play prevented or interrupted:", err);
            speakBrowserUtterance(cleanText);
        });
    }

    function speakBrowserUtterance(cleanText) {
        if (!window.speechSynthesis || !voiceOutputEnabled) {
            onSpeechFinished();
            return;
        }

        const utterance = new SpeechSynthesisUtterance(cleanText.slice(0, 400));
        utterance.rate = 1.0;

        const voices = window.speechSynthesis.getVoices();
        const indianVoice = voices.find(v => v.lang.includes("hi") || v.lang.includes("en-IN"));
        if (indianVoice) utterance.voice = indianVoice;

        utterance.onend = () => { onSpeechFinished(); };
        utterance.onerror = () => { onSpeechFinished(); };

        window.speechSynthesis.speak(utterance);
    }

    function stopSpeaking() {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio.currentTime = 0;
            currentAudio = null;
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        if (state === "speaking") {
            setState("idle", "Speech stopped. Ready for next question.");
        }
    }

    function onSpeechFinished() {
        // Strict requirement: Do not automatically restart listening when muted or closed
        if (!isOpen || !voiceOutputEnabled) {
            setState("idle", "Ready for your next question.");
            return;
        }

        if (continuousMode) {
            setState("listening", "Continuous mode: Listening to your reply...");
            startListening();
        } else {
            setState("idle", "Tap Orb or speak to ask another question.");
        }
    }

    // =========================================================
    // CHAT DIALOGUE & WRITTEN RESPONSES (BELOW VOICE CHAT)
    // =========================================================

    async function handleSendQuestion(questionText) {
        const text = questionText || (chatInput ? chatInput.value.trim() : "");
        if (!text) return;

        if (chatInput) chatInput.value = "";
        stopSpeaking();

        // 1. Display user message in conversation area
        appendChatBubble(text, true);
        conversationHistory.push({ role: "user", content: text });

        // Show typing indicator
        showTypingIndicator();
        setState("thinking", "Guru is reviewing your study materials...");

        try {
            const response = await fetch(`${API_BASE}/api/guru/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({
                    message: text,
                    history: conversationHistory
                })
            });

            hideTypingIndicator();

            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = "login.html";
                    return;
                }
                throw new Error("Guru chat failed");
            }

            const data = await response.json();
            const reply = data.reply || "Namaste! I am here to help you study.";
            const sources = data.sources || [];

            conversationHistory.push({ role: "assistant", content: reply });

            // 2. Display Guru's complete written response directly below user's message
            appendChatBubble(reply, false, sources);

            // 3. Simultaneously speak the response aloud
            speakGuruResponse(reply);

        } catch (error) {
            console.error("Guru chat request error:", error);
            hideTypingIndicator();
            setState("idle", "Connection error. Please try again.");
            appendChatBubble("Namaste! I had trouble reaching the AI engine. Please verify the backend connection and try again.", false);
        }
    }

    function appendChatBubble(text, isUser = false, sources = []) {
        if (!chatFeed) return;

        const bubble = document.createElement("div");
        bubble.className = `guru-bubble ${isUser ? "user" : "bot"}`;

        let formattedText = formatMarkdown(text);

        let citationsHtml = "";
        if (!isUser && sources && sources.length > 0) {
            citationsHtml = `
                <div class="guru-citations">
                    ${sources.map(s => {
                let ref = s.source;
                if (ref === "PDF") ref += ` Page ${s.page}`;
                else if (ref === "PPT") ref += ` Slide ${s.slide}`;
                else if (ref === "VIDEO") ref += ` ${s.start}s`;
                return `<span class="guru-source-pill">📄 ${ref}</span>`;
            }).join("")}
                </div>
            `;
        }

        let listenAgainHtml = !isUser ? `
            <button class="guru-listen-again-btn" title="Listen again">
                🔊 Listen
            </button>
        ` : "";

        bubble.innerHTML = `
            <div class="guru-bubble-content">
                ${formattedText}
                ${citationsHtml}
            </div>
            <div class="guru-bubble-meta">
                <span>${getCurrentTime()}</span>
                ${listenAgainHtml}
            </div>
        `;

        if (!isUser) {
            const listenBtn = bubble.querySelector(".guru-listen-again-btn");
            if (listenBtn) {
                listenBtn.addEventListener("click", () => {
                    speakGuruResponse(text);
                });
            }
        }

        chatFeed.appendChild(bubble);
        chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    function showTypingIndicator() {
        hideTypingIndicator();
        if (!chatFeed) return;
        const typingDiv = document.createElement("div");
        typingDiv.className = "guru-bubble bot";
        typingDiv.setAttribute("id", "guruTypingIndicator");
        typingDiv.innerHTML = `
            <div class="guru-typing">
                <span></span><span></span><span></span>
            </div>
        `;
        chatFeed.appendChild(typingDiv);
        chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    function hideTypingIndicator() {
        const el = document.getElementById("guruTypingIndicator");
        if (el) el.remove();
    }

    function formatMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/### (.*?)\n/g, "<h4 style='margin:8px 0 4px;'>$1</h4>")
            .replace(/## (.*?)\n/g, "<h3 style='margin:10px 0 6px;'>$1</h3>")
            .replace(/\|(.+)\|/g, function (match) {
                return `<div style="font-family:monospace; background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:11.5px;">${match}</div>`;
            })
            .replace(/\n- (.*?)/g, "<br>• $1")
            .replace(/\n/g, "<br>");
    }

    function getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    // =========================================================
    // CONTEXT LOADER & ACADEMIC TOOLS MODALS
    // =========================================================

    async function loadGuruContext() {
        try {
            const res = await fetch(`${API_BASE}/api/guru/context`, {
                method: "GET",
                credentials: "include"
            });
            if (res.ok) {
                studentContext = await res.json();
            }
        } catch (e) {
            console.warn("Could not load Guru context:", e);
        }
    }

    async function openFlashcardsModal(topic) {
        showModal("📇 Guru Interactive Flashcards", `
            <div style="text-align:center; padding:30px;">
                <div class="notes-loader" style="margin: 0 auto 16px;"></div>
                <p>Generating flashcards from your uploaded materials...</p>
            </div>
        `);

        try {
            const res = await fetch(`${API_BASE}/api/guru/flashcards`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ topic: topic || "Core Concepts" })
            });
            const data = await res.json();
            if (data.success && data.flashcards && data.flashcards.length > 0) {
                flashcardsList = data.flashcards;
                currentCardIndex = 0;
                renderFlashcardUI();
            } else {
                updateModalBody(`<p style="color:#ef4444; text-align:center;">${data.message || "Could not generate flashcards."}</p>`);
            }
        } catch (err) {
            updateModalBody(`<p style="color:#ef4444; text-align:center;">Error generating flashcards: ${err.message}</p>`);
        }
    }

    function renderFlashcardUI() {
        const card = flashcardsList[currentCardIndex];
        const total = flashcardsList.length;
        isCardFlipped = false;

        const html = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <span style="font-size:13px; font-weight:600; color:#6366f1;">Card ${currentCardIndex + 1} of ${total}</span>
                <span style="font-size:12px; color:#64748b;">${card.source_reference || ""}</span>
            </div>

            <div class="guru-flashcard-stage" id="flashcardStage">
                <div class="guru-flashcard" id="activeFlashcard">
                    <div class="guru-card-front">
                        <span class="guru-card-tag">${card.category || "CONCEPT"}</span>
                        <div class="guru-card-text">${card.question}</div>
                        <div class="guru-card-hint">Tap card or 'Reveal Answer' to flip ↻</div>
                    </div>
                    <div class="guru-card-back">
                        <span class="guru-card-tag">ANSWER</span>
                        <div class="guru-card-text">${card.answer}</div>
                        <div class="guru-card-hint">Tap card to see question ↺</div>
                    </div>
                </div>
            </div>

            <div class="guru-flashcard-nav">
                <button class="guru-card-btn secondary" id="prevCardBtn" ${currentCardIndex === 0 ? "disabled" : ""}>← Previous</button>
                <button class="guru-card-btn" id="flipCardBtn">Reveal Answer ↻</button>
                <button class="guru-card-btn secondary" id="nextCardBtn" ${currentCardIndex === total - 1 ? "disabled" : ""}>Next →</button>
            </div>
        `;

        updateModalBody(html);

        const cardEl = document.getElementById("activeFlashcard");
        const flipBtn = document.getElementById("flipCardBtn");
        const prevBtn = document.getElementById("prevCardBtn");
        const nextBtn = document.getElementById("nextCardBtn");

        function toggleFlip() {
            isCardFlipped = !isCardFlipped;
            cardEl.classList.toggle("flipped", isCardFlipped);
            flipBtn.textContent = isCardFlipped ? "Show Question ↺" : "Reveal Answer ↻";
        }

        if (cardEl) cardEl.addEventListener("click", toggleFlip);
        if (flipBtn) flipBtn.addEventListener("click", toggleFlip);

        if (prevBtn) {
            prevBtn.addEventListener("click", () => {
                if (currentCardIndex > 0) {
                    currentCardIndex--;
                    renderFlashcardUI();
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener("click", () => {
                if (currentCardIndex < total - 1) {
                    currentCardIndex++;
                    renderFlashcardUI();
                }
            });
        }
    }

    async function openPaperAnalyzerModal(subject) {
        showModal("📊 Guru Paper & Syllabus Analyzer", `
            <div style="text-align:center; padding:30px;">
                <div class="notes-loader" style="margin: 0 auto 16px;"></div>
                <p>Analyzing question papers, frequency patterns and weightage...</p>
            </div>
        `);

        try {
            const res = await fetch(`${API_BASE}/api/guru/paper-analyzer`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ subject: subject || "" })
            });
            const data = await res.json();
            if (data.success && data.analysis) {
                const a = data.analysis;
                const html = `
                    <div style="margin-bottom:16px;">
                        <h4 style="color:#1e1b4b; margin:0 0 6px 0;">Subject: ${a.subject}</h4>
                        <p style="color:#64748b; font-size:12.5px; margin:0;">AI insights extracted from your uploaded study materials & question papers.</p>
                    </div>

                    <h4 style="color:#4f46e5; border-bottom:1px solid #e2e8f0; padding-bottom:4px; margin:14px 0 8px;">🔁 Repeated Questions & High-Yield Concepts</h4>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        ${(a.repeated_questions || []).map(q => `
                            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:10px 14px;">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                    <strong style="font-size:13.5px; color:#0f172a;">${q.question}</strong>
                                    <span style="font-size:10.5px; background:#fee2e2; color:#dc2626; font-weight:700; padding:2px 8px; border-radius:12px;">${q.frequency || "HIGH"}</span>
                                </div>
                                <small style="color:#64748b;">${q.importance || ""}</small>
                            </div>
                        `).join("")}
                    </div>

                    <h4 style="color:#4f46e5; border-bottom:1px solid #e2e8f0; padding-bottom:4px; margin:18px 0 8px;">⭐ Important Topics & Marks Weightage</h4>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        ${(a.important_topics || []).map(t => `
                            <div style="background:#eef2ff; border-left:4px solid #4f46e5; padding:8px 12px; border-radius:6px;">
                                <div style="display:flex; justify-content:space-between;">
                                    <strong>${t.topic}</strong>
                                    <span style="color:#4338ca; font-weight:600;">${t.weightage}</span>
                                </div>
                                <small style="color:#475569;">${t.reason}</small>
                            </div>
                        `).join("")}
                    </div>

                    <h4 style="color:#4f46e5; border-bottom:1px solid #e2e8f0; padding-bottom:4px; margin:18px 0 8px;">🎯 Priority Revision Strategy</h4>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        ${(a.priority_revision_strategy || []).map(s => `
                            <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; padding:10px 14px;">
                                <strong style="color:#166534;">${s.tier}</strong>: ${(s.topics || []).join(", ")}
                                <div style="font-size:12px; color:#15803d; margin-top:3px;">Action: ${s.action}</div>
                            </div>
                        `).join("")}
                    </div>
                `;
                updateModalBody(html);
            } else {
                updateModalBody(`<p style="color:#ef4444; text-align:center;">${data.message || "Analysis failed."}</p>`);
            }
        } catch (err) {
            updateModalBody(`<p style="color:#ef4444; text-align:center;">Error analyzing papers: ${err.message}</p>`);
        }
    }

    async function openPracticePaperModal(subject, paperType = "mcq") {
        showModal(`📝 Guru Practice Paper (${paperType.toUpperCase()})`, `
            <div style="text-align:center; padding:30px;">
                <div class="notes-loader" style="margin: 0 auto 16px;"></div>
                <p>Generating realistic exam questions from your notes...</p>
            </div>
        `);

        try {
            const res = await fetch(`${API_BASE}/api/guru/practice-paper`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ subject: subject || "", paper_type: paperType })
            });
            const data = await res.json();
            if (data.success && data.paper && data.paper.questions) {
                renderPracticePaperUI(data.paper);
            } else {
                updateModalBody(`<p style="color:#ef4444; text-align:center;">${data.message || "Failed to generate practice test."}</p>`);
            }
        } catch (err) {
            updateModalBody(`<p style="color:#ef4444; text-align:center;">Error generating paper: ${err.message}</p>`);
        }
    }

    function renderPracticePaperUI(paper) {
        const questions = paper.questions || [];
        const isMcq = paper.type === "MCQ";

        const html = `
            <div style="margin-bottom:16px;">
                <h3 style="margin:0 0 6px 0; color:#0f172a;">${paper.title}</h3>
                <p style="color:#64748b; font-size:12.5px; margin:0;">Total Questions: ${questions.length} • Interactive Practice</p>
            </div>

            <div style="display:flex; flex-direction:column; gap:16px;">
                ${questions.map((q, idx) => `
                    <div class="question-card" style="padding:14px; border:1px solid #e2e8f0; border-radius:12px; background:#ffffff;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                            <span class="question-label" style="font-size:11px;">Q${idx + 1} (${q.marks || 2} Marks)</span>
                        </div>
                        <h4 style="margin:0 0 10px 0; font-size:14px; color:#1e293b;">${q.question}</h4>
                        
                        ${isMcq && q.options ? `
                            <div class="options" style="display:flex; flex-direction:column; gap:7px;">
                                ${q.options.map((opt, optIdx) => `
                                    <button class="option-button guru-test-opt" data-qidx="${idx}" data-oidx="${optIdx}" data-correct="${q.correct_index}" style="padding:8px 12px; font-size:13px; text-align:left; border-radius:8px; border:1px solid #cbd5e1; background:#f8fafc; cursor:pointer;">
                                        ${String.fromCharCode(65 + optIdx)}. ${opt}
                                    </button>
                                `).join("")}
                            </div>
                            <div id="qExpl_${idx}" style="display:none; margin-top:8px; padding:8px 12px; background:#f8fafc; border-radius:6px; font-size:12px; color:#334155;">
                                <strong>Explanation:</strong> ${q.explanation || "Correct answer marked."}
                            </div>
                        ` : `
                            <div style="margin-top:8px; padding:10px; background:#f8fafc; border-radius:6px; font-size:12.5px; line-height:1.5;">
                                <strong style="color:#4f46e5;">Model Answer:</strong>
                                <p style="margin:4px 0 0 0; color:#334155;">${q.model_answer || ""}</p>
                            </div>
                        `}
                    </div>
                `).join("")}
            </div>
        `;

        updateModalBody(html);

        if (isMcq) {
            document.querySelectorAll(".guru-test-opt").forEach(btn => {
                btn.addEventListener("click", () => {
                    const qIdx = btn.getAttribute("data-qidx");
                    const oIdx = parseInt(btn.getAttribute("data-oidx"));
                    const cIdx = parseInt(btn.getAttribute("data-correct"));

                    const parent = btn.parentElement;
                    const allOpts = parent.querySelectorAll(".guru-test-opt");
                    allOpts.forEach(o => o.disabled = true);

                    if (oIdx === cIdx) {
                        btn.style.background = "#dcfce7";
                        btn.style.borderColor = "#22c55e";
                        btn.style.color = "#15803d";
                    } else {
                        btn.style.background = "#fee2e2";
                        btn.style.borderColor = "#ef4444";
                        btn.style.color = "#b91c1c";
                        allOpts[cIdx].style.background = "#dcfce7";
                        allOpts[cIdx].style.borderColor = "#22c55e";
                    }

                    const expl = document.getElementById(`qExpl_${qIdx}`);
                    if (expl) expl.style.display = "block";
                });
            });
        }
    }

    async function openExamDatesModal() {
        let datesList = [];
        try {
            const res = await fetch(`${API_BASE}/api/guru/exam-dates`, {
                method: "GET",
                credentials: "include"
            });
            const data = await res.json();
            if (data.success) datesList = data.exam_dates || [];
        } catch (e) { }

        const datesHtml = datesList.length > 0 ? `
            <div class="guru-exam-grid">
                ${datesList.map(d => {
            let pillClass = "normal";
            let daysText = `${d.days_remaining} days left`;
            if (d.days_remaining !== null) {
                if (d.days_remaining <= 2) { pillClass = "urgent"; daysText = `⚠️ ${d.days_remaining} days left!`; }
                else if (d.days_remaining <= 7) { pillClass = "soon"; daysText = `⏳ ${d.days_remaining} days left`; }
                else if (d.days_remaining < 0) { pillClass = "past"; daysText = `Done`; }
            }
            return `
                        <div class="guru-exam-card">
                            <h4 class="guru-exam-subject">${d.subject}</h4>
                            <div class="guru-exam-date-row">📅 ${d.exam_date}</div>
                            <span class="guru-countdown-pill ${pillClass}">${daysText}</span>
                        </div>
                    `;
        }).join("")}
            </div>
        ` : `<p style="color:#64748b; font-size:13px;">No exam dates saved yet.</p>`;

        const html = `
            <h4 style="margin:0 0 10px 0; color:#1e1b4b;">Upcoming Examinations</h4>
            ${datesHtml}

            <hr style="border:none; border-top:1px solid #e2e8f0; margin:18px 0;">

            <h4 style="margin:0 0 10px 0; color:#1e1b4b;">Add New Exam Date</h4>
            <form id="guruAddExamForm">
                <div style="margin-bottom:12px;">
                    <label style="display:block; font-size:12.5px; font-weight:600; margin-bottom:5px;">Subject Name</label>
                    <input type="text" id="newExamSubject" class="guru-chat-input" placeholder="e.g. DBMS, Operating System" required style="width:100%; border-radius:8px;">
                </div>
                <div style="margin-bottom:12px;">
                    <label style="display:block; font-size:12.5px; font-weight:600; margin-bottom:5px;">Exam Date</label>
                    <input type="date" id="newExamDate" class="guru-chat-input" required style="width:100%; border-radius:8px;">
                </div>
                <div style="margin-bottom:16px;">
                    <label style="display:block; font-size:12.5px; font-weight:600; margin-bottom:5px;">Notes (optional)</label>
                    <input type="text" id="newExamNotes" class="guru-chat-input" placeholder="e.g. Units 1 to 4 revision priority" style="width:100%; border-radius:8px;">
                </div>
                <button type="submit" class="guru-card-btn" style="width:100%; padding:10px;">Save Exam Date →</button>
            </form>
        `;

        showModal("📅 Examination Dates & Countdown", html);

        const form = document.getElementById("guruAddExamForm");
        if (form) {
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                const subject = document.getElementById("newExamSubject").value.trim();
                const examDate = document.getElementById("newExamDate").value;
                const notes = document.getElementById("newExamNotes").value.trim();

                try {
                    const res = await fetch(`${API_BASE}/api/guru/exam-dates`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        credentials: "include",
                        body: JSON.stringify({ subject, exam_date: examDate, notes })
                    });
                    const d = await res.json();
                    if (d.success) {
                        closeModal();
                        loadGuruContext();
                        appendChatBubble(`I have saved your exam date for **${subject}** on **${examDate}**! I will keep track of the remaining days and help you prioritize your daily revision.`, false);
                    } else {
                        alert(d.message || "Failed to save exam date.");
                    }
                } catch (err) {
                    alert("Error saving exam date: " + err.message);
                }
            });
        }
    }

    // Modal Helper Functions
    function showModal(title, bodyHtml) {
        closeModal();
        const overlay = document.createElement("div");
        overlay.className = "guru-panel-overlay";
        overlay.setAttribute("id", "guruModalOverlay");
        overlay.innerHTML = `
            <div class="guru-modal">
                <div class="guru-modal-header">
                    <h3>${title}</h3>
                    <button class="guru-modal-close" id="guruModalCloseBtn">✕</button>
                </div>
                <div class="guru-modal-body" id="guruModalBody">
                    ${bodyHtml}
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        overlay.querySelector("#guruModalCloseBtn").addEventListener("click", closeModal);
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) closeModal();
        });
    }

    function updateModalBody(html) {
        const body = document.getElementById("guruModalBody");
        if (body) body.innerHTML = html;
    }

    function closeModal() {
        const overlay = document.getElementById("guruModalOverlay");
        if (overlay) overlay.remove();
    }

    // =========================================================
    // EVENT LISTENERS BINDING
    // =========================================================

    function setupEventListeners() {
        // Floating launcher toggle
        if (launcherBtn) launcherBtn.addEventListener("click", togglePopup);
        if (closeBtn) closeBtn.addEventListener("click", closePopup);

        // Voice output toggle
        if (voiceToggleBtn) {
            voiceToggleBtn.addEventListener("click", () => {
                voiceOutputEnabled = !voiceOutputEnabled;
                voiceToggleBtn.classList.toggle("active", voiceOutputEnabled);
                voiceToggleBtn.textContent = voiceOutputEnabled ? "🔊" : "🔇";
                if (!voiceOutputEnabled) {
                    stopSpeaking();
                    stopListening();
                }
            });
        }

        // Orb click
        if (orbBtn) orbBtn.addEventListener("click", toggleOrbListening);
        if (chatMicBtn) chatMicBtn.addEventListener("click", toggleOrbListening);

        // Stop speaking button
        if (stopSpeakingBtn) stopSpeakingBtn.addEventListener("click", stopSpeaking);

        // Continuous mode switch
        if (continuousSwitch) {
            continuousSwitch.addEventListener("change", (e) => {
                continuousMode = e.target.checked;
                if (continuousMode && state === "idle" && isOpen) {
                    startListening();
                } else if (!continuousMode && state === "listening") {
                    stopListening();
                }
            });
        }

        // Chat send button
        if (chatSendBtn) {
            chatSendBtn.addEventListener("click", () => handleSendQuestion());
        }

        // Chat input enter key
        if (chatInput) {
            chatInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendQuestion();
                }
            });
        }

        // Quick academic tool chips
        document.getElementById("toolTodayStudy")?.addEventListener("click", () => {
            handleSendQuestion("Guru, mera exam aane wala hai. Mere notes aur schedule dekh kar batao aaj mujhe kya padhna chahiye?");
        });

        document.getElementById("toolPaperAnalyzer")?.addEventListener("click", () => {
            openPaperAnalyzerModal();
        });

        document.getElementById("toolSmartNotes")?.addEventListener("click", () => {
            handleSendQuestion("Guru, make smart revision notes from my uploaded study materials.");
        });

        document.getElementById("toolFlashcards")?.addEventListener("click", () => {
            openFlashcardsModal();
        });

        document.getElementById("toolPracticePaper")?.addEventListener("click", () => {
            openPracticePaperModal();
        });

        document.getElementById("toolExamDates")?.addEventListener("click", () => {
            openExamDatesModal();
        });
    }

    // Initialize when DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initGuruDashboard);
    } else {
        initGuruDashboard();
    }
})();
