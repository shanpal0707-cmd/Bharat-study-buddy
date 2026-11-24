/**
 * Bharat Study Buddy — Guru Index Page Assistant (JS)
 * Website Introduction Assistant
 *
 * Responsibilities:
 * - Floating widget UI open/close
 * - Website feature explanation
 * - Registration and login guidance
 * - Text conversation + voice input (SpeechRecognition / Whisper)
 * - Spoken responses via HTML5 Audio / SpeechSynthesis
 * - Zero access to authenticated student data
 */

(function () {
    const API_BASE = "http://127.0.0.1:5000";

    let isOpen = false;
    let voiceOutputEnabled = true;
    let isRecording = false;
    let recognition = null;
    let currentAudio = null;
    let conversationHistory = [];

    // DOM Elements
    let launcherBtn, popup, closeBtn, voiceToggleBtn, messagesContainer;
    let chipsContainer, inputField, sendBtn, micBtn, voiceStatus;

    function initGuruIndex() {
        createWidgetElements();
        setupSpeechRecognition();
        setupEventListeners();
    }

    function createWidgetElements() {
        // Floating Launcher
        launcherBtn = document.createElement("button");
        launcherBtn.className = "guru-launcher";
        launcherBtn.setAttribute("id", "guruLauncherBtn");
        launcherBtn.setAttribute("aria-label", "Talk to Guru, AI Guide");
        launcherBtn.innerHTML = `
            <div class="guru-launcher-icon">
                🤖
                <span class="guru-pulse-dot"></span>
            </div>
            <span>Talk to Guru</span>
        `;
        document.body.appendChild(launcherBtn);

        // Chat Popup
        popup = document.createElement("div");
        popup.className = "guru-popup";
        popup.setAttribute("id", "guruPopup");
        popup.setAttribute("role", "dialog");
        popup.setAttribute("aria-label", "Guru Website Guide");
        popup.innerHTML = `
            <div class="guru-header">
                <div class="guru-header-info">
                    <div class="guru-avatar">🤖</div>
                    <div class="guru-header-text">
                        <h3>Guru — AI Guide</h3>
                        <p><span></span> Online • Website Guide</p>
                    </div>
                </div>
                <div class="guru-header-actions">
                    <button class="guru-icon-btn active" id="guruVoiceToggle" title="Toggle Voice Responses" aria-label="Toggle Voice Responses">
                        🔊
                    </button>
                    <button class="guru-icon-btn" id="guruCloseBtn" title="Close" aria-label="Close Chat">
                        ✕
                    </button>
                </div>
            </div>

            <div class="guru-voice-bar" id="guruVoiceStatus">
                <div class="guru-voice-wave">
                    <span></span><span></span><span></span><span></span>
                </div>
                <span id="guruVoiceStatusText">Listening to your question...</span>
            </div>

            <div class="guru-messages" id="guruMessages">
                <div class="guru-msg bot">
                    <div class="guru-msg-bubble">
                        Namaste! 🙏 I'm <strong>Guru</strong>, your AI guide. Welcome to <strong>Bharat Study Buddy</strong>!
                        <br><br>
                        I can explain our 8 learning features, show you how to register via email OTP, or answer any questions about the platform. What would you like to know?
                    </div>
                    <span class="guru-msg-time">${getCurrentTime()}</span>
                </div>
            </div>

            <div class="guru-chips" id="guruChips">
                <button class="guru-chip" data-q="What is Bharat Study Buddy?">What is Bharat Study Buddy?</button>
                <button class="guru-chip" data-q="Explain all 8 features">Explain all 8 features</button>
                <button class="guru-chip" data-q="How do I register and login?">How to register?</button>
                <button class="guru-chip" data-q="What is Paper Analyzer?">Paper Analyzer?</button>
                <button class="guru-chip" data-q="What is Dashboard Guru?">Dashboard Guru?</button>
            </div>

            <div class="guru-footer">
                <button class="guru-action-btn guru-mic-btn" id="guruMicBtn" title="Speak question" aria-label="Voice Input">
                    🎙️
                </button>
                <input type="text" class="guru-input" id="guruInput" placeholder="Ask Guru about Bharat Study Buddy..." autocomplete="off">
                <button class="guru-action-btn guru-send-btn" id="guruSendBtn" title="Send message" aria-label="Send">
                    ➤
                </button>
            </div>
        `;
        document.body.appendChild(popup);

        // Bind references
        closeBtn = document.getElementById("guruCloseBtn");
        voiceToggleBtn = document.getElementById("guruVoiceToggle");
        messagesContainer = document.getElementById("guruMessages");
        chipsContainer = document.getElementById("guruChips");
        inputField = document.getElementById("guruInput");
        sendBtn = document.getElementById("guruSendBtn");
        micBtn = document.getElementById("guruMicBtn");
        voiceStatus = document.getElementById("guruVoiceStatus");
    }

    function setupEventListeners() {
        launcherBtn.addEventListener("click", togglePopup);
        closeBtn.addEventListener("click", closePopup);

        voiceToggleBtn.addEventListener("click", () => {
            voiceOutputEnabled = !voiceOutputEnabled;
            voiceToggleBtn.classList.toggle("active", voiceOutputEnabled);
            voiceToggleBtn.textContent = voiceOutputEnabled ? "🔊" : "🔇";
            if (!voiceOutputEnabled && currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            if (!voiceOutputEnabled && window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
        });

        sendBtn.addEventListener("click", handleUserSend);

        inputField.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleUserSend();
            }
        });

        micBtn.addEventListener("click", toggleVoiceInput);

        // Quick prompt chips
        chipsContainer.addEventListener("click", (e) => {
            if (e.target.classList.contains("guru-chip")) {
                const query = e.target.getAttribute("data-q");
                inputField.value = query;
                handleUserSend();
            }
        });
    }

    function togglePopup() {
        isOpen = !isOpen;
        popup.classList.toggle("active", isOpen);
        launcherBtn.style.display = isOpen ? "none" : "flex";
        if (isOpen) {
            inputField.focus();
        } else {
            stopAudio();
        }
    }

    function closePopup() {
        isOpen = false;
        popup.classList.remove("active");
        launcherBtn.style.display = "flex";
        stopAudio();
    }

    function stopAudio() {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        if (isRecording && recognition) {
            recognition.stop();
        }
    }

    function getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    function appendMessage(text, isUser = false) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `guru-msg ${isUser ? "user" : "bot"}`;

        const bubble = document.createElement("div");
        bubble.className = "guru-msg-bubble";

        if (isUser) {
            bubble.textContent = text;
        } else {
            // Render basic markdown formatting
            bubble.innerHTML = formatMarkdown(text);
        }

        const timeSpan = document.createElement("span");
        timeSpan.className = "guru-msg-time";
        timeSpan.textContent = getCurrentTime();

        msgDiv.appendChild(bubble);
        msgDiv.appendChild(timeSpan);
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        return msgDiv;
    }

    function showTypingIndicator() {
        const typingDiv = document.createElement("div");
        typingDiv.className = "guru-msg bot";
        typingDiv.setAttribute("id", "guruTyping");
        typingDiv.innerHTML = `
            <div class="guru-typing">
                <span></span><span></span><span></span>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function hideTypingIndicator() {
        const el = document.getElementById("guruTyping");
        if (el) el.remove();
    }

    function formatMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/### (.*?)\n/g, "<h4 style='margin:8px 0 4px;'>$1</h4>")
            .replace(/\n- (.*?)/g, "<br>• $1")
            .replace(/\n/g, "<br>");
    }

    async function handleUserSend() {
        const text = inputField.value.trim();
        if (!text) return;

        inputField.value = "";
        appendMessage(text, true);

        conversationHistory.push({ role: "user", content: text });
        sendBtn.disabled = true;
        showTypingIndicator();

        try {
            const response = await fetch(`${API_BASE}/api/guru/intro-chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    history: conversationHistory
                })
            });

            hideTypingIndicator();
            sendBtn.disabled = false;

            if (!response.ok) {
                throw new Error("Intro chat request failed");
            }

            const data = await response.json();
            const reply = data.reply || "Namaste! Bharat Study Buddy helps students excel with AI. Click 'Get Started' to begin!";

            appendMessage(reply, false);
            conversationHistory.push({ role: "assistant", content: reply });

            if (voiceOutputEnabled) {
                speakReply(reply);
            }

        } catch (error) {
            console.error("Guru intro chat error:", error);
            hideTypingIndicator();
            sendBtn.disabled = false;
            appendMessage("Namaste! Bharat Study Buddy is an AI learning platform with Study Material Upload, Ask AI, Paper Analyzer, Study Planner, Smart Notes, Flashcards, and Video Lecture Transcription. Click 'Get Started' to sign up!", false);
        }
    }

    // =========================================================
    // VOICE INPUT (STT)
    // =========================================================

    function setupSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-IN"; // Supports Indian English & common Hindi terms

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add("recording");
            voiceStatus.classList.add("active");
            document.getElementById("guruVoiceStatusText").textContent = "Listening to your voice...";
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            inputField.value = transcript;
            handleUserSend();
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            stopVoiceInput();
        };

        recognition.onend = () => {
            stopVoiceInput();
        };
    }

    function toggleVoiceInput() {
        if (!recognition) {
            alert("Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
            return;
        }

        if (isRecording) {
            recognition.stop();
        } else {
            try {
                recognition.start();
            } catch (e) {
                console.error("Recognition start error:", e);
            }
        }
    }

    function stopVoiceInput() {
        isRecording = false;
        micBtn.classList.remove("recording");
        voiceStatus.classList.remove("active");
    }

    // =========================================================
    // VOICE OUTPUT (TTS)
    // =========================================================

    function speakReply(text) {
        stopAudio();

        // 1. First attempt: Server-side TTS endpoint (/api/guru/tts)
        const cleanText = text.replace(/[*#_`~>]/g, "").replace(/\n/g, " ").slice(0, 300);
        const ttsUrl = `${API_BASE}/api/guru/tts?text=${encodeURIComponent(cleanText)}`;

        currentAudio = new Audio(ttsUrl);
        currentAudio.play().catch((err) => {
            console.warn("Server TTS audio play error, falling back to browser SpeechSynthesis:", err);
            speakBrowserFallback(cleanText);
        });
    }

    function speakBrowserFallback(cleanText) {
        if (!window.speechSynthesis) return;

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.0;

        // Try to pick Hindi or Indian English voice if available
        const voices = window.speechSynthesis.getVoices();
        const indianVoice = voices.find(v => v.lang.includes("hi") || v.lang.includes("en-IN"));
        if (indianVoice) {
            utterance.voice = indianVoice;
        }

        window.speechSynthesis.speak(utterance);
    }

    // Initialize when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initGuruIndex);
    } else {
        initGuruIndex();
    }
})();
