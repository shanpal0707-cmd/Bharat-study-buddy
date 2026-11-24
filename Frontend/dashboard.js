
/* =========================================================
   BHARAT STUDY BUDDY — DASHBOARD
========================================================= */

const API_BASE = "http://127.0.0.1:5000";

/* =========================================================
   LOGGED-IN USER
========================================================= */

let currentUserId = null;
let currentUserName = "Student";
let currentUserEmail = "Email not available";

async function loadLoggedInUser() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/me`, {
            method: "GET",
            credentials: "include"
        });

        if (response.status === 401) {
            window.location.href = "login.html";
            return;
        }

        if (!response.ok) {
            throw new Error("Backend connection failed.");
        }

        const result = await response.json();

        if (!result.success || !result.user) {
            throw new Error("Unable to verify the logged-in user.");
        }

        currentUserId = result.user.id;
        currentUserName = result.user.name || "Student";
        currentUserEmail = result.user.email || "Email not available";

        const profileName = document.getElementById("profileName");
        const profileAvatar = document.getElementById("profileAvatar");
        const panelName = document.getElementById("panelName");
        const panelEmail = document.getElementById("panelEmail");
        const panelAvatar = document.getElementById("panelAvatar");

        if (profileName) {
            profileName.textContent = currentUserName;
        }

        if (profileAvatar) {
            profileAvatar.textContent =
                currentUserName.charAt(0).toUpperCase();
        }

        if (panelName) panelName.textContent = currentUserName;
        if (panelEmail) panelEmail.textContent = currentUserEmail;

        if (panelAvatar) {
            panelAvatar.textContent =
                currentUserName.charAt(0).toUpperCase();
        }

        loadProgress();
        updateProfileStats();
        loadSavedStudyPlans();

    } catch (error) {
        console.error("Login verification failed:", error);
        alert("Backend start hai ya nahi, check karo.");
    }
}

/* =========================================================
   PROFILE STATISTICS
========================================================= */

function updateProfileStats() {
    if (currentUserId === null) return;

    let history = [];

    try {
        history = JSON.parse(
            localStorage.getItem(
                `bharatStudyProgress_${currentUserId}`
            ) || "[]"
        );

        if (!Array.isArray(history)) {
            history = [];
        }
    } catch (error) {
        console.error("Unable to read quiz history:", error);
        history = [];
    }

    const percentages = history.map(item =>
        Math.max(
            0,
            Math.min(100, Number(item.percentage) || 0)
        )
    );

    const attempts = percentages.length;
    const best = attempts ? Math.max(...percentages) : 0;

    const average = attempts
        ? Math.round(
            percentages.reduce((sum, value) => sum + value, 0) /
            attempts
        )
        : 0;

    const attemptsElement =
        document.getElementById("profileAttempts");

    const bestElement =
        document.getElementById("profileBestScore");

    const averageElement =
        document.getElementById("profileAverage");

    const uploadsElement =
        document.getElementById("profileUploads");

    const plansElement =
        document.getElementById("profilePlans");

    if (attemptsElement) {
        attemptsElement.textContent = attempts;
    }

    if (bestElement) {
        bestElement.textContent = `${best}%`;
    }

    if (averageElement) {
        averageElement.textContent = `${average}%`;
    }

    let uploadCount = 0;

    try {
        uploadCount = Number(
            localStorage.getItem(
                `bharatStudyUploads_${currentUserId}`
            )
        ) || 0;
    } catch (error) {
        uploadCount = 0;
    }

    if (uploadsElement) {
        uploadsElement.textContent = uploadCount;
    }

    // Study plan generator/count storage has not been provided yet.
    if (plansElement) {
        plansElement.textContent = "Not tracked";
    }
}

/* =========================================================
   FILE INPUTS
========================================================= */

const pdfInput = document.getElementById("pdfInput");
const pptInput = document.getElementById("pptInput");
const videoInput = document.getElementById("videoInput");

const pdfStatus = document.getElementById("pdfStatus");
const pptStatus = document.getElementById("pptStatus");
const videoStatus = document.getElementById("videoStatus");

const sourceCount = document.querySelector(".source-count");
const processButton = document.getElementById("processButton");

/* =========================================================
   FILE NAME DISPLAY
========================================================= */

function updateFileStatus(input, statusElement) {
    if (!input || !statusElement) return;

    input.addEventListener("change", () => {
        if (input.files.length > 0) {
            statusElement.textContent = input.files[0].name;
            statusElement.style.color = "#315ee8";
        } else {
            statusElement.textContent = "No file selected";
            statusElement.style.color = "#9aa4b4";
        }

        updateSourceCount();
    });
}

updateFileStatus(pdfInput, pdfStatus);
updateFileStatus(pptInput, pptStatus);
updateFileStatus(videoInput, videoStatus);

/* =========================================================
   SOURCE COUNT
========================================================= */

function updateSourceCount() {
    if (!sourceCount) return;

    let count = 0;

    if (pdfInput?.files.length > 0) count++;
    if (pptInput?.files.length > 0) count++;
    if (videoInput?.files.length > 0) count++;

    sourceCount.textContent =
        `${count} SOURCE${count === 1 ? "" : "S"}`;
}

/* =========================================================
   PROCESS STUDY MATERIAL
========================================================= */

async function uploadMaterial(input, statusElement, endpoint, label) {
    const file = input?.files[0];

    if (!file) return null;

    const formData = new FormData();
    formData.append("file", file);

    if (statusElement) {
        statusElement.textContent = "Processing...";
        statusElement.style.color = "#315ee8";
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        credentials: "include",
        body: formData
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok || !result.success) {
        throw new Error(
            `${label}: ${result.message || "Upload failed."}`
        );
    }

    if (statusElement) {
        statusElement.textContent = `${file.name} ✓`;
        statusElement.style.color = "#1b7f5b";
    }

    // Count only successful uploads.
    if (currentUserId !== null) {
        const uploadKey =
            `bharatStudyUploads_${currentUserId}`;

        let uploadCount = 0;

        try {
            uploadCount = Number(
                localStorage.getItem(uploadKey)
            ) || 0;
        } catch (error) {
            uploadCount = 0;
        }

        try {
            localStorage.setItem(
                uploadKey,
                String(uploadCount + 1)
            );
        } catch (error) {
            console.error("Unable to save upload count:", error);
        }
    }

    updateProfileStats();

    console.log(`${label} Processing Result:`, result);
    return result;
}

function processPDF() {
    return uploadMaterial(
        pdfInput,
        pdfStatus,
        "/api/upload/pdf",
        "PDF"
    );
}

function processPPT() {
    return uploadMaterial(
        pptInput,
        pptStatus,
        "/api/upload/ppt",
        "PPT"
    );
}

function processVideo() {
    return uploadMaterial(
        videoInput,
        videoStatus,
        "/api/upload/video",
        "VIDEO"
    );
}

/* =========================================================
   PROCESS ALL MATERIALS
========================================================= */

if (processButton) {
    processButton.addEventListener("click", async () => {
        const hasPDF = pdfInput?.files.length > 0;
        const hasPPT = pptInput?.files.length > 0;
        const hasVideo = videoInput?.files.length > 0;

        if (!hasPDF && !hasPPT && !hasVideo) {
            alert("Please upload at least one study material.");
            return;
        }

        processButton.disabled = true;

        const buttonLabel =
            processButton.querySelector("span:first-child");

        if (buttonLabel) {
            buttonLabel.textContent = "Processing materials...";
        }

        try {
            let pdfResult = null;
            let pptResult = null;
            let videoResult = null;

            if (hasPDF) pdfResult = await processPDF();
            if (hasPPT) pptResult = await processPPT();
            if (hasVideo) videoResult = await processVideo();

            if (buttonLabel) {
                buttonLabel.textContent = "Materials processed ✓";
            }

            processButton.style.background = "#1b7f5b";

            let message = "Study materials processed successfully!";

            if (pdfResult) {
                message +=
                    `\n\nPDF pages extracted: ${pdfResult.total_pages}`;
            }

            if (pptResult) {
                message +=
                    `\nPPT slides extracted: ${pptResult.total_slides}`;
            }

            if (videoResult) {
                message +=
                    `\nVideo segments transcribed: ${videoResult.segments}`;
            }

            alert(message);

        } catch (error) {
            console.error("Processing error:", error);

            alert(`Processing failed.\n\n${error.message}`);

            if (buttonLabel) {
                buttonLabel.textContent = "Process Study Materials";
            }

            processButton.style.background = "";

        } finally {
            processButton.disabled = false;
        }
    });
}

/* =========================================================
   ASK AI
========================================================= */

const questionInput = document.getElementById("questionInput");
const askButton = document.getElementById("askButton");
const chatArea = document.getElementById("chatArea");
const voiceButton = document.getElementById("voiceButton");
const voiceStatus = document.getElementById("voiceStatus");

// Diagram Explainer Elements
const imageUploadBtn = document.getElementById("imageUploadBtn");
const diagramFileInput = document.getElementById("diagramFileInput");
const diagramPreviewContainer = document.getElementById("diagramPreviewContainer");
const diagramPreviewImg = document.getElementById("diagramPreviewImg");
const diagramFileName = document.getElementById("diagramFileName");
const diagramReplaceBtn = document.getElementById("diagramReplaceBtn");
const diagramRemoveBtn = document.getElementById("diagramRemoveBtn");

let selectedDiagramFile = null;
let activeDiagramContextName = null;

let voiceRecognition = null;
let isVoiceRecording = false;
let speechTextPrefix = "";
let voiceStatusTimer = null;

function showVoiceStatus(message, type = "info", autoDismiss = 0) {
    if (!voiceStatus) return;

    if (voiceStatusTimer) {
        clearTimeout(voiceStatusTimer);
        voiceStatusTimer = null;
    }

    voiceStatus.className = `voice-status ${type}`;
    voiceStatus.style.display = "flex";

    const dotHtml = type === "listening" ? '<span class="status-dot"></span>' : '';
    voiceStatus.innerHTML = `
        ${dotHtml}
        <span>${message}</span>
        <button type="button" class="status-close" aria-label="Close message" id="voiceStatusCloseBtn">&times;</button>
    `;

    const closeBtn = document.getElementById("voiceStatusCloseBtn");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            hideVoiceStatus();
        });
    }

    if (autoDismiss > 0) {
        voiceStatusTimer = setTimeout(() => {
            hideVoiceStatus();
        }, autoDismiss);
    }
}

function hideVoiceStatus() {
    if (!voiceStatus) return;
    if (voiceStatusTimer) {
        clearTimeout(voiceStatusTimer);
        voiceStatusTimer = null;
    }
    voiceStatus.style.display = "none";
}

function updateVoiceButtonState(listening) {
    if (!voiceButton) return;
    const label = voiceButton.querySelector(".voice-btn-label");

    if (listening) {
        voiceButton.classList.add("listening");
        voiceButton.title = "Listening... Click to stop";
        if (label) label.textContent = "Stop";
    } else {
        voiceButton.classList.remove("listening");
        voiceButton.title = "Voice Input (Click to speak)";
        if (label) label.textContent = "Voice";
    }
}

function initVoiceRecognition() {
    if (!voiceButton) return;

    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        voiceButton.addEventListener("click", () => {
            showVoiceStatus(
                "Voice input is not supported in this browser. Please use Chrome, Edge, or Safari.",
                "error",
                8000
            );
        });
        return;
    }

    try {
        voiceRecognition = new SpeechRecognition();
        voiceRecognition.continuous = false;
        voiceRecognition.interimResults = true;
        voiceRecognition.lang = navigator.language || "en-IN";

        voiceRecognition.onstart = () => {
            isVoiceRecording = true;
            updateVoiceButtonState(true);
            speechTextPrefix = questionInput ? questionInput.value.trim() : "";
            if (speechTextPrefix.length > 0) {
                speechTextPrefix += " ";
            }
            showVoiceStatus("Listening... Speak your question now (click Stop when done)", "listening");
        };

        voiceRecognition.onresult = event => {
            let interimTranscript = "";
            let finalTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            const currentSpoken = finalTranscript || interimTranscript;
            if (questionInput && currentSpoken) {
                questionInput.value = speechTextPrefix + currentSpoken;
            }
        };

        voiceRecognition.onerror = event => {
            console.warn("Speech recognition error:", event.error);
            isVoiceRecording = false;
            updateVoiceButtonState(false);

            if (event.error === "not-allowed" || event.error === "permission-denied") {
                showVoiceStatus(
                    "Microphone access was denied. Please allow microphone permissions in your browser address bar.",
                    "error",
                    10000
                );
            } else if (event.error === "no-speech") {
                showVoiceStatus(
                    "No speech detected. Click Voice and try speaking again.",
                    "error",
                    5000
                );
            } else if (event.error === "audio-capture") {
                showVoiceStatus(
                    "No microphone found. Please check your audio input device.",
                    "error",
                    7000
                );
            } else if (event.error === "network") {
                showVoiceStatus(
                    "Network error during speech recognition. Please check your internet connection.",
                    "error",
                    7000
                );
            } else if (event.error !== "aborted") {
                showVoiceStatus(
                    `Voice recognition notice: ${event.error}. Please try again.`,
                    "error",
                    5000
                );
            }
        };

        voiceRecognition.onend = () => {
            isVoiceRecording = false;
            updateVoiceButtonState(false);

            if (questionInput && questionInput.value.trim().length > 0) {
                showVoiceStatus(
                    "Voice captured! You can review and edit your question before sending.",
                    "success",
                    5000
                );
                questionInput.focus();
                const len = questionInput.value.length;
                questionInput.setSelectionRange(len, len);
            } else {
                hideVoiceStatus();
            }
        };

        voiceButton.addEventListener("click", () => {
            if (isVoiceRecording) {
                try {
                    voiceRecognition.stop();
                } catch (e) {
                    console.warn("Stop recognition error:", e);
                }
                isVoiceRecording = false;
                updateVoiceButtonState(false);
            } else {
                try {
                    hideVoiceStatus();
                    voiceRecognition.start();
                } catch (err) {
                    console.error("Failed to start speech recognition:", err);
                    showVoiceStatus(
                        "Could not start microphone. Please check permissions and try again.",
                        "error",
                        6000
                    );
                }
            }
        });

    } catch (err) {
        console.error("SpeechRecognition initialization failed:", err);
        voiceButton.addEventListener("click", () => {
            showVoiceStatus(
                "Voice recognition could not be initialized in this browser.",
                "error",
                6000
            );
        });
    }
}

// Initialize Voice Recognition
initVoiceRecognition();

/* =========================================================
   DIAGRAM EXPLAINER
========================================================= */

function initDiagramExplainer() {
    if (!imageUploadBtn || !diagramFileInput) return;

    imageUploadBtn.addEventListener("click", () => {
        diagramFileInput.click();
    });

    diagramReplaceBtn?.addEventListener("click", () => {
        diagramFileInput.click();
    });

    diagramRemoveBtn?.addEventListener("click", () => {
        clearSelectedDiagram();
    });

    diagramFileInput.addEventListener("change", () => {
        const file = diagramFileInput.files && diagramFileInput.files[0];
        if (!file) return;

        const validExtensions = [".png", ".jpg", ".jpeg", ".webp"];
        const lowerName = file.name.toLowerCase();
        const isValidExt = validExtensions.some(ext => lowerName.endsWith(ext));

        if (!isValidExt || (file.type && !file.type.startsWith("image/"))) {
            showVoiceStatus("Invalid file format. Please upload a PNG, JPG, or JPEG image.", "error", 7000);
            diagramFileInput.value = "";
            return;
        }

        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            showVoiceStatus("Image file exceeds the 10 MB limit. Please select a smaller image.", "error", 7000);
            diagramFileInput.value = "";
            return;
        }

        selectedDiagramFile = file;
        activeDiagramContextName = file.name;

        const reader = new FileReader();
        reader.onload = e => {
            if (diagramPreviewImg) {
                diagramPreviewImg.src = e.target.result;
            }
            if (diagramFileName) {
                diagramFileName.textContent = file.name;
            }
            if (diagramPreviewContainer) {
                diagramPreviewContainer.style.display = "flex";
            }
            imageUploadBtn.classList.add("has-image");
        };
        reader.readAsDataURL(file);

        if (questionInput) {
            questionInput.placeholder = "Ask a question about this diagram, or click Ask AI to explain...";
            questionInput.focus();
        }
    });
}

function clearSelectedDiagram() {
    selectedDiagramFile = null;
    if (diagramFileInput) diagramFileInput.value = "";
    if (diagramPreviewContainer) diagramPreviewContainer.style.display = "none";
    if (diagramPreviewImg) diagramPreviewImg.src = "";
    if (imageUploadBtn) imageUploadBtn.classList.remove("has-image");
    if (questionInput) {
        questionInput.placeholder = "Ask a question from study material or diagram...";
    }
}

// Initialize Diagram Explainer
initDiagramExplainer();

function formatAIResponse(rawText) {
    return String(rawText || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/^### (.*$)/gim, "<strong>✦ $1</strong>")
        .replace(/^## (.*$)/gim, "<strong>$1</strong>")
        .replace(/^# (.*$)/gim, "<strong>$1</strong>")
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/^\* (.*$)/gim, "• $1")
        .replace(/^- (.*$)/gim, "• $1")
        .replace(/\n/g, "<br>")
        .replace(/【(.*?)】/g, "<br><small>📌 $1</small>");
}

function addChatMessage(type, content, isHTML = false, attachment = null) {
    if (!chatArea) return;

    const message = document.createElement("div");
    message.className =
        type === "user" ? "user-message" : "ai-message";

    const heading = document.createElement("strong");
    heading.textContent = type === "user" ? "You" : "AI Tutor";
    message.appendChild(heading);

    if (attachment && attachment.imageUrl) {
        const attachDiv = document.createElement("div");
        attachDiv.className = "chat-diagram-attachment";
        const img = document.createElement("img");
        img.src = attachment.imageUrl;
        img.className = "chat-diagram-thumb";
        img.alt = attachment.filename || "Uploaded Diagram";
        attachDiv.appendChild(img);

        if (attachment.filename) {
            const cap = document.createElement("div");
            cap.className = "chat-diagram-caption";
            cap.textContent = `📊 ${attachment.filename}`;
            attachDiv.appendChild(cap);
        }
        message.appendChild(attachDiv);
    }

    if (attachment && attachment.isDiagramExplanation) {
        const badge = document.createElement("div");
        badge.className = "diagram-badge-pill";
        badge.textContent = "📊 AI Diagram Explanation";
        message.appendChild(badge);
    }

    const paragraph = document.createElement("p");
    if (isHTML) {
        paragraph.innerHTML = content;
    } else {
        paragraph.textContent = content;
    }
    message.appendChild(paragraph);

    chatArea.appendChild(message);
    chatArea.scrollTop = chatArea.scrollHeight;
}

async function askAI() {
    // If voice recognition is active, stop it cleanly
    if (isVoiceRecording && voiceRecognition) {
        try {
            voiceRecognition.stop();
        } catch (_) {}
        isVoiceRecording = false;
        updateVoiceButtonState(false);
    }
    hideVoiceStatus();

    const question = questionInput?.value.trim();

    // Check if we have either a diagram attached or a typed question
    if (!question && !selectedDiagramFile) return;
    if (!askButton) return;

    if (selectedDiagramFile) {
        // DIAGRAM EXPLAINER FLOW
        const fileToSend = selectedDiagramFile;
        const displayQuestion = question || "Please explain this diagram step by step.";
        const previewUrl = URL.createObjectURL(fileToSend);

        addChatMessage("user", displayQuestion, false, {
            imageUrl: previewUrl,
            filename: fileToSend.name
        });

        clearSelectedDiagram();
        if (questionInput) questionInput.value = "";

        askButton.disabled = true;
        askButton.textContent = "Analyzing Diagram...";

        try {
            const formData = new FormData();
            formData.append("image", fileToSend);
            if (question) {
                formData.append("question", question);
            }

            const response = await fetch(`${API_BASE}/api/ask/diagram`, {
                method: "POST",
                credentials: "include",
                body: formData
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Unable to analyze diagram."
                );
            }

            const answerHTML = formatAIResponse(result.answer);
            addChatMessage("ai", answerHTML, true, { isDiagramExplanation: true });

        } catch (error) {
            console.error("Diagram Explainer error:", error);
            addChatMessage(
                "ai",
                error.message || "Sorry, I couldn't analyze the diagram."
            );
        } finally {
            askButton.disabled = false;
            askButton.textContent = "Ask AI →";
        }

    } else {
        // STANDARD TEXT-ONLY ASK AI FLOW (100% PRESERVED)
        addChatMessage("user", question);
        if (questionInput) questionInput.value = "";

        askButton.disabled = true;
        askButton.textContent = "Thinking...";

        try {
            const response = await fetch(`${API_BASE}/api/ask`, {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ question })
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Unable to get answer."
                );
            }

            const answerHTML = formatAIResponse(result.answer);
            addChatMessage("ai", answerHTML, true);

        } catch (error) {
            console.error("Ask AI error:", error);

            addChatMessage(
                "ai",
                error.message || "Sorry, I couldn't process your question."
            );

        } finally {
            askButton.disabled = false;
            askButton.textContent = "Ask AI →";
        }
    }
}

askButton?.addEventListener("click", askAI);

questionInput?.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        event.preventDefault();
        askAI();
    }
});

/* =========================================================
   QUIZ ELEMENTS
========================================================= */

const startQuizButton = document.getElementById("startQuizButton");
const quizStart = document.getElementById("quizStart");
const quizQuestionArea = document.getElementById("quizQuestionArea");
const quizResult = document.getElementById("quizResult");
const questionText = document.getElementById("questionText");
const quizOptions = document.getElementById("quizOptions");
const questionNumber = document.getElementById("questionNumber");
const quizScore = document.getElementById("quizScore");
const quizProgressFill = document.getElementById("quizProgressFill");
const nextQuestionButton = document.getElementById("nextQuestionButton");
const finalScore = document.getElementById("finalScore");
const resultMessage = document.getElementById("resultMessage");
const restartQuizButton = document.getElementById("restartQuizButton");
const weakTopicCard = document.getElementById("weakTopicCard");
const weakTopicText = document.getElementById("weakTopicText");
const adaptiveButton = document.getElementById("adaptiveButton");

let quizQuestions = [];
let currentQuestion = 0;
let score = 0;
let selectedAnswer = null;
let wrongQuestions = [];
let quizMode = "normal";
let currentWeakTopic = "";

/* =========================================================
   START NORMAL QUIZ
========================================================= */

async function startQuiz() {
    quizMode = "normal";
    currentWeakTopic = "";
    wrongQuestions = [];

    if (!startQuizButton) return;

    startQuizButton.disabled = true;
    startQuizButton.textContent = "Generating...";

    try {
        const response = await fetch(`${API_BASE}/api/quiz`, {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Quiz generation failed."
            );
        }

        if (
            !Array.isArray(result.questions) ||
            result.questions.length === 0
        ) {
            throw new Error("No quiz questions were generated.");
        }

        quizQuestions = result.questions;
        currentQuestion = 0;
        score = 0;
        selectedAnswer = null;

        quizStart.style.display = "none";
        quizResult.style.display = "none";
        quizQuestionArea.style.display = "block";

        if (weakTopicCard) weakTopicCard.style.display = "none";
        if (adaptiveButton) adaptiveButton.style.display = "";

        showQuestion();

    } catch (error) {
        console.error("Quiz error:", error);
        alert(error.message || "Unable to generate quiz.");

    } finally {
        startQuizButton.disabled = false;
        startQuizButton.textContent = "Start Quiz →";
    }
}

/* =========================================================
   SHOW QUESTION
========================================================= */

function showQuestion() {
    const question = quizQuestions[currentQuestion];

    if (!question || !Array.isArray(question.options)) {
        alert("Quiz question data is invalid. Please restart.");
        return;
    }

    selectedAnswer = null;

    questionText.textContent = question.question;

    questionNumber.textContent =
        `Question ${currentQuestion + 1} of ${quizQuestions.length}`;

    quizScore.textContent = `Score: ${score}`;

    quizProgressFill.style.width =
        `${((currentQuestion + 1) / quizQuestions.length) * 100}%`;

    quizOptions.innerHTML = "";
    nextQuestionButton.disabled = true;

    question.options.forEach((option, index) => {
        const button = document.createElement("button");
        button.className = "quiz-option";
        button.textContent = option;

        button.addEventListener("click", () => {
            selectAnswer(button, index);
        });

        quizOptions.appendChild(button);
    });

    nextQuestionButton.textContent =
        currentQuestion === quizQuestions.length - 1
            ? "Finish Quiz →"
            : "Next Question →";
}

/* =========================================================
   SELECT ANSWER
========================================================= */

function selectAnswer(button, index) {
    selectedAnswer = index;

    quizOptions.querySelectorAll(".quiz-option").forEach(option => {
        option.classList.remove("selected");
    });

    button.classList.add("selected");
    nextQuestionButton.disabled = false;
}

/* =========================================================
   CHECK CURRENT ANSWER
========================================================= */

function checkCurrentAnswer() {
    const current = quizQuestions[currentQuestion];
    const correctAnswer = Number(current.answer);

    if (selectedAnswer === correctAnswer) {
        score++;
    } else {
        wrongQuestions.push({
            question: current.question,
            selectedAnswer: current.options[selectedAnswer],
            correctAnswer: current.options[correctAnswer],
            explanation: current.explanation || ""
        });
    }
}

/* =========================================================
   NEXT QUESTION
========================================================= */

nextQuestionButton?.addEventListener("click", () => {
    if (selectedAnswer === null) return;

    checkCurrentAnswer();
    currentQuestion++;

    if (currentQuestion < quizQuestions.length) {
        showQuestion();
    } else {
        showQuizResult();
    }
});

/* =========================================================
   QUIZ RESULT
========================================================= */

function showQuizResult() {
    quizQuestionArea.style.display = "none";
    quizResult.style.display = "block";

    finalScore.textContent =
        `${score} / ${quizQuestions.length}`;

    if (currentUserId === null) {
        alert("Login verify nahi hua. Please login again.");
        window.location.href = "login.html";
        return;
    }

    const storageKey =
        `bharatStudyProgress_${currentUserId}`;

    let progressData = [];

    try {
        progressData = JSON.parse(
            localStorage.getItem(storageKey) || "[]"
        );

        if (!Array.isArray(progressData)) {
            progressData = [];
        }
    } catch (error) {
        progressData = [];
    }

    progressData.push({
        score,
        total: quizQuestions.length,
        percentage: Math.round(
            (score / quizQuestions.length) * 100
        ),
        mode: quizMode,
        topic: currentWeakTopic || "General Study",
        date: new Date().toLocaleDateString()
    });

    try {
        localStorage.setItem(
            storageKey,
            JSON.stringify(progressData)
        );
    } catch (error) {
        console.error("Unable to save quiz progress:", error);
        alert("Quiz completed, but progress could not be saved.");
    }

    updateProfileStats();

    if (quizMode === "adaptive") {
        resultMessage.textContent =
            `You completed your ${currentWeakTopic || "weak-topic"} practice.`;

        if (weakTopicCard) weakTopicCard.style.display = "block";

        if (weakTopicText) {
            weakTopicText.textContent =
                `Practiced topic: ${currentWeakTopic || "Weak topic"}`;
        }

        if (adaptiveButton) adaptiveButton.style.display = "none";

        loadProgress();
        return;
    }

    if (score === quizQuestions.length) {
        resultMessage.textContent =
            "Excellent! You have a strong understanding of the material.";

        if (weakTopicCard) weakTopicCard.style.display = "none";

    } else {
        resultMessage.textContent =
            score >= 3
                ? "Good work! A little more practice will strengthen your understanding."
                : "Keep practicing. Let's focus on the topics that need improvement.";

        if (weakTopicCard) weakTopicCard.style.display = "block";

        if (weakTopicText) {
            weakTopicText.textContent = "Analyzing your weak topic...";
        }
    }

    loadProgress();
}

/* =========================================================
   ANALYZE WEAK TOPIC
========================================================= */

async function analyzeWeakTopic() {
    if (!wrongQuestions.length) {
        alert("No weak topic found. Great job!");
        return;
    }

    adaptiveButton.disabled = true;
    adaptiveButton.textContent = "Analyzing...";

    if (weakTopicText) {
        weakTopicText.textContent = "Analyzing your weak topic...";
    }

    try {
        const response = await fetch(`${API_BASE}/api/adaptive-quiz`, {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                wrongQuestions
            })
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Adaptive quiz generation failed."
            );
        }

        if (
            !Array.isArray(result.questions) ||
            result.questions.length === 0
        ) {
            throw new Error("No adaptive questions were generated.");
        }

        currentWeakTopic =
            result.weak_topic || "Needs more practice";

        if (weakTopicText) {
            weakTopicText.textContent = currentWeakTopic;
        }

        startAdaptiveQuiz(result.questions, currentWeakTopic);

    } catch (error) {
        console.error("Adaptive quiz error:", error);
        alert(error.message || "Unable to generate adaptive quiz.");

    } finally {
        adaptiveButton.disabled = false;
        adaptiveButton.textContent = "Practice Weak Topic →";
    }
}

/* =========================================================
   START ADAPTIVE QUIZ
========================================================= */

function startAdaptiveQuiz(questions, weakTopic) {
    quizMode = "adaptive";
    currentWeakTopic = weakTopic || "Needs more practice";
    quizQuestions = questions;

    currentQuestion = 0;
    score = 0;
    selectedAnswer = null;
    wrongQuestions = [];

    quizStart.style.display = "none";
    quizResult.style.display = "none";
    quizQuestionArea.style.display = "block";

    if (weakTopicCard) weakTopicCard.style.display = "block";

    if (weakTopicText) {
        weakTopicText.textContent = currentWeakTopic;
    }

    showQuestion();
}

/* =========================================================
   RESTART QUIZ
========================================================= */

restartQuizButton?.addEventListener("click", () => {
    quizMode = "normal";
    currentWeakTopic = "";
    wrongQuestions = [];
    quizQuestions = [];
    currentQuestion = 0;
    score = 0;
    selectedAnswer = null;

    quizResult.style.display = "none";
    quizQuestionArea.style.display = "none";
    quizStart.style.display = "flex";

    if (weakTopicCard) weakTopicCard.style.display = "none";
    if (adaptiveButton) adaptiveButton.style.display = "";
});

/* =========================================================
   QUIZ BUTTONS
========================================================= */

adaptiveButton?.addEventListener("click", analyzeWeakTopic);
startQuizButton?.addEventListener("click", startQuiz);

/* =========================================================
   LOAD PROGRESS
========================================================= */

function loadProgress() {
    const masteryPercentage =
        document.getElementById("masteryPercentage");

    const masteryFill =
        document.getElementById("masteryFill");

    const masteryMessage =
        document.getElementById("masteryMessage");

    const quizAttempts =
        document.getElementById("quizAttempts");

    const bestScore =
        document.getElementById("bestScore");

    const progressWeakTopic =
        document.getElementById("progressWeakTopic");

    const progressRecommendation =
        document.getElementById("progressRecommendation");

    if (currentUserId === null) return;

    let progressData = [];

    try {
        progressData = JSON.parse(
            localStorage.getItem(
                `bharatStudyProgress_${currentUserId}`
            ) || "[]"
        );

        if (!Array.isArray(progressData)) {
            progressData = [];
        }
    } catch (error) {
        progressData = [];
    }

    if (progressData.length === 0) {
        if (masteryPercentage) masteryPercentage.textContent = "0%";
        if (masteryFill) masteryFill.style.width = "0%";
        if (quizAttempts) quizAttempts.textContent = "0";
        if (bestScore) bestScore.textContent = "0%";

        if (progressWeakTopic) {
            progressWeakTopic.textContent = "Not yet available";
        }

        if (masteryMessage) {
            masteryMessage.textContent =
                "Complete a quiz to see your progress.";
        }

        if (progressRecommendation) {
            progressRecommendation.textContent =
                "Start a quiz to receive a study recommendation.";
        }

        return;
    }

    const totalPercentage = progressData.reduce(
        (sum, item) => sum + (Number(item.percentage) || 0),
        0
    );

    const averagePercentage = Math.round(
        totalPercentage / progressData.length
    );

    const best = Math.max(
        ...progressData.map(item => Number(item.percentage) || 0)
    );

    const latest = progressData[progressData.length - 1];
    const topic = latest.topic || "General Study";

    if (masteryPercentage) {
        masteryPercentage.textContent = `${averagePercentage}%`;
    }

    if (masteryFill) {
        masteryFill.style.width = `${averagePercentage}%`;
    }

    if (quizAttempts) {
        quizAttempts.textContent = progressData.length;
    }

    if (bestScore) {
        bestScore.textContent = `${best}%`;
    }

    if (progressWeakTopic) {
        progressWeakTopic.textContent = topic;
    }

    if (averagePercentage < 40) {
        if (masteryMessage) {
            masteryMessage.textContent =
                "Let's strengthen your fundamentals.";
        }

        if (progressRecommendation) {
            progressRecommendation.textContent =
                `Focus more on ${topic} and try another adaptive quiz.`;
        }

    } else if (averagePercentage < 70) {
        if (masteryMessage) {
            masteryMessage.textContent =
                "Good progress. Keep practicing.";
        }

        if (progressRecommendation) {
            progressRecommendation.textContent =
                `Continue practicing ${topic} to improve your mastery.`;
        }

    } else {
        if (masteryMessage) {
            masteryMessage.textContent =
                "Excellent progress! Keep it up.";
        }

        if (progressRecommendation) {
            progressRecommendation.textContent =
                "Your overall understanding is getting stronger.";
        }
    }
}

/* =========================================================
   SMART NOTES
========================================================= */

const generateNotesButton =
    document.getElementById("generateNotesButton");

const notesLoading =
    document.getElementById("notesLoading");

const generatedNotes =
    document.getElementById("generatedNotes");

generateNotesButton?.addEventListener("click", async () => {
    try {
        generateNotesButton.disabled = true;

        const buttonLabel =
            generateNotesButton.querySelector("span:first-child");

        if (buttonLabel) {
            buttonLabel.textContent = "Generating Notes...";
        }

        if (notesLoading) notesLoading.style.display = "block";

        if (generatedNotes) {
            generatedNotes.style.display = "none";
            generatedNotes.innerHTML = "";
        }

        const response = await fetch(`${API_BASE}/api/notes`, {
            method: "POST",
            credentials: "include"
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || "Unable to generate notes."
            );
        }

        if (generatedNotes) {
            generatedNotes.innerHTML = "";

            (data.notes || []).forEach(note => {
                const section = document.createElement("div");
                section.className = "note-topic";

                const heading = document.createElement("h3");
                heading.textContent = note.heading || "Study Notes";
                section.appendChild(heading);

                const list = document.createElement("ul");

                (note.points || []).forEach(point => {
                    const item = document.createElement("li");
                    item.textContent = point;
                    list.appendChild(item);
                });

                section.appendChild(list);
                generatedNotes.appendChild(section);
            });

            generatedNotes.style.display = "block";
        }

    } catch (error) {
        console.error("Smart Notes Error:", error);

        if (generatedNotes) {
            generatedNotes.textContent =
                error.message || "Unable to generate notes.";

            generatedNotes.style.display = "block";
        }

    } finally {
        if (notesLoading) notesLoading.style.display = "none";

        generateNotesButton.disabled = false;

        const buttonLabel =
            generateNotesButton.querySelector("span:first-child");

        if (buttonLabel) {
            buttonLabel.textContent = "Generate Smart Notes";
        }
    }
});

/* =========================================================
   PROFILE PANEL
========================================================= */

const profileButton = document.getElementById("profileButton");
const profileOverlay = document.getElementById("profileOverlay");
const closeProfile = document.getElementById("closeProfile");
const logoutButton = document.getElementById("logoutButton");

function openProfile() {
    if (!profileOverlay) return;

    // Refresh the name and email if those fields exist.
    const panelName = document.getElementById("panelName");
    const panelEmail = document.getElementById("panelEmail");
    const panelAvatar = document.getElementById("panelAvatar");

    if (panelName) panelName.textContent = currentUserName;
    if (panelEmail) panelEmail.textContent = currentUserEmail;

    if (panelAvatar) {
        panelAvatar.textContent =
            currentUserName.charAt(0).toUpperCase();
    }

    updateProfileStats();

    profileOverlay.hidden = false;
    profileButton?.setAttribute("aria-expanded", "true");
}

function hideProfile() {
    if (!profileOverlay) return;

    profileOverlay.hidden = true;
    profileButton?.setAttribute("aria-expanded", "false");
    profileButton?.focus();
}

profileButton?.addEventListener("click", openProfile);
closeProfile?.addEventListener("click", hideProfile);

profileOverlay?.addEventListener("click", event => {
    if (event.target === profileOverlay) {
        hideProfile();
    }
});

document.addEventListener("keydown", event => {
    if (
        event.key === "Escape" &&
        profileOverlay &&
        !profileOverlay.hidden
    ) {
        hideProfile();
    }
});

/* =========================================================
   LOGOUT
========================================================= */

logoutButton?.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to logout?")) return;

    logoutButton.disabled = true;
    logoutButton.textContent = "Logging out...";

    try {
        const response = await fetch(
            `${API_BASE}/api/auth/logout`,
            {
                method: "POST",
                credentials: "include"
            }
        );

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Logout failed."
            );
        }

        window.location.href = "login.html";

    } catch (error) {
        console.error("Logout error:", error);
        alert("Logout failed. Please try again.");

        logoutButton.disabled = false;
        logoutButton.textContent = "↪ Logout";
    }
});

/* =========================================================
   INITIALIZE DASHBOARD
========================================================= */

loadLoggedInUser();

/* =========================================================
   STEP 06 - AI STUDY PLANNER
========================================================= */

const plannerForm = document.getElementById("studyPlannerForm");
const plannerMessage = document.getElementById("studyPlannerMessage");
const savedPlansContainer = document.getElementById("savedStudyPlans");
const planDetailsContainer = document.getElementById("studyPlanDetails");
const planTasksContainer = document.getElementById("studyPlanTasks");
const generatePlanButton = document.getElementById("generateStudyPlanButton");

let activeStudyPlanId = null;

function showPlannerMessage(message, isError = false) {
    if (!plannerMessage) return;

    plannerMessage.textContent = message;
    plannerMessage.style.color = isError ? "#c0392b" : "#1b7f5b";
}

function plannerDate(value) {
    if (!value) return "Date not available";

    const parts = String(value).slice(0, 10).split("-");
    if (parts.length !== 3) return String(value);

    return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function plannerElement(tag, text, className = "") {
    const element = document.createElement(tag);
    element.textContent = text ?? "";

    if (className) element.className = className;

    return element;
}

async function plannerRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        credentials: "include",
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...(options.headers || {})
        }
    });

    const result = await response.json().catch(() => ({}));

    if (response.status === 401) {
        window.location.href = "login.html";
        throw new Error("Please log in again.");
    }

    if (!response.ok || result.success === false) {
        throw new Error(result.message || "Study Planner request failed.");
    }

    return result;
}

function renderSavedPlanCard(plan) {
    const card = plannerElement("div", "", "study-plan-card");

    const title = plannerElement(
        "h4",
        plan.title || "My Study Plan"
    );

    const examDate = plannerElement(
        "p",
        `Exam date: ${plannerDate(plan.exam_date)}`
    );

    const total = Number(plan.total_tasks) || 0;
    const completed = Number(plan.completed_tasks) || 0;
    const percentage = total
        ? Math.round((completed / total) * 100)
        : 0;

    const progress = plannerElement(
        "p",
        `Progress: ${percentage}% (${completed}/${total} tasks)`
    );

    const actions = plannerElement("div", "", "study-plan-actions");

    const openButton = plannerElement("button", "View timetable");
    openButton.type = "button";

    openButton.addEventListener("click", () => {
        openStudyPlan(plan.id);
    });

    const deleteButton = plannerElement("button", "Delete plan");
    deleteButton.type = "button";

    deleteButton.addEventListener("click", async () => {
        if (!confirm("Delete this study plan and all its tasks?")) return;

        deleteButton.disabled = true;

        try {
            await plannerRequest(
                `/api/study-planner/plans/${plan.id}`,
                { method: "DELETE" }
            );

            if (String(activeStudyPlanId) === String(plan.id)) {
                activeStudyPlanId = null;
                planDetailsContainer.hidden = true;
            }

            showPlannerMessage("Study plan deleted successfully.");
            await loadSavedStudyPlans();

        } catch (error) {
            showPlannerMessage(error.message, true);
            deleteButton.disabled = false;
        }
    });

    actions.append(openButton, deleteButton);
    card.append(title, examDate, progress, actions);

    return card;
}

async function loadSavedStudyPlans() {
    if (!savedPlansContainer || currentUserId === null) return;

    savedPlansContainer.replaceChildren(
        plannerElement("p", "Loading your saved study plans...")
    );

    try {
        const result = await plannerRequest("/api/study-planner/plans");
        const plans = Array.isArray(result.plans) ? result.plans : [];

        savedPlansContainer.replaceChildren();

        if (!plans.length) {
            savedPlansContainer.appendChild(
                plannerElement(
                    "p",
                    "No saved plans yet. Create your first study plan!"
                )
            );
        } else {
            plans.forEach(plan => {
                savedPlansContainer.appendChild(renderSavedPlanCard(plan));
            });
        }

        const profilePlans = document.getElementById("profilePlans");

        if (profilePlans) {
            profilePlans.textContent = String(plans.length);
        }

    } catch (error) {
        console.error("Loading study plans failed:", error);

        savedPlansContainer.replaceChildren(
            plannerElement("p", error.message)
        );
    }
}

async function openStudyPlan(planId) {
    if (!planDetailsContainer || !planTasksContainer) return;

    activeStudyPlanId = planId;
    planDetailsContainer.hidden = false;

    planTasksContainer.replaceChildren(
        plannerElement("p", "Loading timetable...")
    );

    planDetailsContainer.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    try {
        const result = await plannerRequest(
            `/api/study-planner/plans/${planId}`
        );

        // Ignore a slower response if the user opened another plan.
        if (String(activeStudyPlanId) !== String(planId)) return;

        const plan = result.plan || {};
        const tasks = Array.isArray(result.tasks) ? result.tasks : [];

        document.getElementById("studyPlanTitle").textContent =
            plan.title || "Study Plan";

        planTasksContainer.replaceChildren();

        if (!tasks.length) {
            planTasksContainer.appendChild(
                plannerElement("p", "No tasks found in this plan.")
            );
        }

        const groupedTasks = {};

        tasks.forEach(task => {
            const taskDate = task.task_date || task.date || "Undated";

            if (!groupedTasks[taskDate]) groupedTasks[taskDate] = [];
            groupedTasks[taskDate].push(task);
        });

        Object.keys(groupedTasks).sort().forEach(taskDate => {
            planTasksContainer.appendChild(
                plannerElement(
                    "h4",
                    taskDate === "Undated" ? taskDate : plannerDate(taskDate),
                    "study-task-date"
                )
            );

            groupedTasks[taskDate].forEach(task => {
                const row = plannerElement("div", "", "study-task");

                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.checked = Boolean(Number(task.is_completed));
                checkbox.setAttribute(
                    "aria-label",
                    `Mark ${task.topic || task.subject} as completed`
                );

                const content = plannerElement("div", "", "study-task-content");

                content.appendChild(
                    plannerElement(
                        "strong",
                        `${task.subject || "Subject"}: ${task.topic || "Study task"}`
                    )
                );

                const duration = Number(task.duration_minutes) || 60;
                const time = task.start_time
                    ? `${task.start_time} · `
                    : "";

                content.appendChild(
                    plannerElement(
                        "p",
                        `${time}${duration} minutes`
                    )
                );

                if (checkbox.checked) row.classList.add("is-completed");

                checkbox.addEventListener("change", async () => {
                    checkbox.disabled = true;

                    try {
                        await plannerRequest(
                            `/api/study-planner/tasks/${task.id}`,
                            {
                                method: "PATCH",
                                body: JSON.stringify({
                                    is_completed: checkbox.checked
                                })
                            }
                        );

                        task.is_completed = checkbox.checked ? 1 : 0;
                        row.classList.toggle(
                            "is-completed",
                            checkbox.checked
                        );

                        updateStudyPlanProgress(tasks);
                        await loadSavedStudyPlans();

                    } catch (error) {
                        checkbox.checked = !checkbox.checked;
                        showPlannerMessage(error.message, true);

                    } finally {
                        checkbox.disabled = false;
                    }
                });

                row.append(checkbox, content);
                planTasksContainer.appendChild(row);
            });
        });

        updateStudyPlanProgress(tasks);

    } catch (error) {
        console.error("Opening study plan failed:", error);

        planTasksContainer.replaceChildren(
            plannerElement("p", error.message)
        );
    }
}

function updateStudyPlanProgress(tasks) {
    const total = tasks.length;
    const completed = tasks.filter(
        task => Boolean(Number(task.is_completed))
    ).length;

    const percentage = total
        ? Math.round((completed / total) * 100)
        : 0;

    const progressText = document.getElementById("studyPlanProgress");
    const progressFill = document.getElementById("studyPlanProgressFill");

    if (progressText) {
        progressText.textContent =
            `${percentage}% complete (${completed}/${total})`;
    }

    if (progressFill) {
        progressFill.style.width = `${percentage}%`;
    }
}

plannerForm?.addEventListener("submit", async event => {
    event.preventDefault();

    if (currentUserId === null) {
        showPlannerMessage("Please log in before creating a study plan.", true);
        return;
    }

    const subjects = document.getElementById("plannerSubjects")
        .value.split(",").map(value => value.trim()).filter(Boolean);

    const topicsText = document.getElementById("plannerTopics").value.trim();

    const topics = topicsText
        ? topicsText.split(";").map(value => value.trim()).filter(Boolean)
        : [];

    const weakSubjects = document.getElementById("plannerWeakSubjects")
        .value.split(",").map(value => value.trim()).filter(Boolean);

    const examDate = document.getElementById("plannerExamDate").value;
    const dailyHours = Number(document.getElementById("plannerHours").value);

    if (!subjects.length) {
        showPlannerMessage("Enter at least one subject.", true);
        return;
    }

    if (!examDate || examDate <= new Date().toISOString().slice(0, 10)) {
        showPlannerMessage("Choose an exam date in the future.", true);
        return;
    }

    if (!Number.isFinite(dailyHours) || dailyHours < 1 || dailyHours > 16) {
        showPlannerMessage("Daily study hours must be between 1 and 16.", true);
        return;
    }

    generatePlanButton.disabled = true;
    generatePlanButton.textContent = "Generating timetable...";
    showPlannerMessage("AI is preparing your study timetable. Please wait.");

    try {
        const result = await plannerRequest(
            "/api/study-planner/generate",
            {
                method: "POST",
                body: JSON.stringify({
                    subjects,
                    topics,
                    weak_subjects: weakSubjects,
                    exam_date: examDate,
                    daily_hours: dailyHours
                })
            }
        );

        showPlannerMessage(
            result.message || "Your study plan has been created!"
        );

        await loadSavedStudyPlans();

        const planId = result.plan_id ?? result.plan?.id ?? result.id;

        if (planId !== undefined && planId !== null) {
            await openStudyPlan(planId);
        } else {
            showPlannerMessage(
                "Plan created. Select it from Your saved plans to view the timetable."
            );
        }

    } catch (error) {
        console.error("Study plan generation failed:", error);
        showPlannerMessage(error.message, true);

    } finally {
        generatePlanButton.disabled = false;
        generatePlanButton.textContent = "Generate AI Timetable →";
    }
});

// The logged-in user is verified before their saved plans are loaded.

loadLoggedInUser();