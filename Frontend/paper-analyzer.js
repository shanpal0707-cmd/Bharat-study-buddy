/**
 * Bharat Study Buddy — Paper Analyzer AI (Frontend JS)
 * ====================================================
 * Handles:
 * - Multi-paper upload (PDF, PNG, JPG, JPEG)
 * - Metadata association (Subject, Exam name, Year)
 * - Live list of uploaded question papers with removal
 * - AI Analysis execution with progress indicator
 * - 3-Tier Priority results (HIGH, MEDIUM, LOW)
 * - Grouped Repeated Questions section with variations
 * - Search & Filter for Important Questions
 * - Preparation recommendations & Exam overview
 * - Printable PDF Report Export
 */

(function () {
    const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
        ? "http://127.0.0.1:5000"
        : "https://bharat-study-buddy.onrender.com";

    // State
    let uploadedPapers = [];
    let currentReport = null;
    let selectedFiles = [];
    let activePriorityFilter = "ALL";
    let searchQuery = "";
    let activeTab = "overview";

    // DOM Elements
    let dropzone, fileInput, browseBtn, subjectInput, examNameInput, yearInput;
    let uploadBtn, uploadStatus, papersListContainer, papersCountBadge, clearPapersBtn;
    let analyzeBtn, loadingBox, loadingStepText, resultsContainer;
    let filterPills, searchInput, exportPdfBtn;

    function initPaperAnalyzer() {
        cacheDOMElements();
        setupEventListeners();
        loadUploadedPapers();
        loadLatestReport();
    }

    function cacheDOMElements() {
        dropzone = document.getElementById("paDropzone");
        fileInput = document.getElementById("paFileInput");
        browseBtn = document.getElementById("paBrowseBtn");
        subjectInput = document.getElementById("paSubjectInput");
        examNameInput = document.getElementById("paExamNameInput");
        yearInput = document.getElementById("paYearInput");
        uploadBtn = document.getElementById("paUploadBtn");
        uploadStatus = document.getElementById("paUploadStatus");
        papersListContainer = document.getElementById("paPapersList");
        papersCountBadge = document.getElementById("paPapersCount");
        clearPapersBtn = document.getElementById("paClearBtn");
        analyzeBtn = document.getElementById("paAnalyzeBtn");
        loadingBox = document.getElementById("paLoadingBox");
        loadingStepText = document.getElementById("paLoadingStepText");
        resultsContainer = document.getElementById("paResultsContainer");
        exportPdfBtn = document.getElementById("paExportPdfBtn");
    }

    function setupEventListeners() {
        if (browseBtn && fileInput) {
            browseBtn.addEventListener("click", () => fileInput.click());
        }

        if (fileInput) {
            fileInput.addEventListener("change", handleFileSelection);
        }

        if (dropzone) {
            ["dragenter", "dragover"].forEach(eventName => {
                dropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    dropzone.classList.add("dragover");
                });
            });

            ["dragleave", "drop"].forEach(eventName => {
                dropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    dropzone.classList.remove("dragover");
                });
            });

            dropzone.addEventListener("drop", (e) => {
                if (e.dataTransfer && e.dataTransfer.files) {
                    fileInput.files = e.dataTransfer.files;
                    handleFileSelection();
                }
            });
        }

        if (uploadBtn) {
            uploadBtn.addEventListener("click", uploadSelectedPapers);
        }

        if (clearPapersBtn) {
            clearPapersBtn.addEventListener("click", handleClearAllPapers);
        }

        if (analyzeBtn) {
            analyzeBtn.addEventListener("click", triggerPaperAnalysis);
        }

        if (exportPdfBtn) {
            exportPdfBtn.addEventListener("click", exportAnalysisAsPdf);
        }
    }

    function handleFileSelection() {
        if (!fileInput || !fileInput.files) return;
        selectedFiles = Array.from(fileInput.files);
        if (selectedFiles.length > 0) {
            uploadBtn.disabled = false;
            uploadStatus.textContent = `${selectedFiles.length} file(s) selected: ${selectedFiles.map(f => f.name).join(", ")}`;
            uploadStatus.style.color = "#4f46e5";
        } else {
            uploadBtn.disabled = true;
            uploadStatus.textContent = "";
        }
    }

    // =========================================================
    // API CALLS: PAPERS MANAGEMENT
    // =========================================================

    async function loadUploadedPapers() {
        try {
            const res = await fetch(`${API_BASE}/api/paper-analyzer/papers`, {
                method: "GET",
                credentials: "include"
            });
            const data = await res.json();
            if (data.success) {
                uploadedPapers = data.papers || [];
                renderUploadedPapersList();
            }
        } catch (e) {
            console.warn("Could not load uploaded papers:", e);
        }
    }

    async function uploadSelectedPapers() {
        if (!selectedFiles || selectedFiles.length === 0) return;

        const formData = new FormData();
        selectedFiles.forEach(f => formData.append("files", f));
        formData.append("subject", subjectInput?.value.trim() || "");
        formData.append("exam_name", examNameInput?.value.trim() || "");
        formData.append("year", yearInput?.value.trim() || "");

        uploadBtn.disabled = true;
        uploadBtn.textContent = "Uploading & Extracting Questions...";
        uploadStatus.textContent = "Extracting text with PyMuPDF...";
        uploadStatus.style.color = "#4f46e5";

        try {
            const res = await fetch(`${API_BASE}/api/paper-analyzer/upload`, {
                method: "POST",
                body: formData,
                credentials: "include"
            });
            const data = await res.json();

            if (data.success) {
                uploadStatus.textContent = `Successfully uploaded ${data.uploaded_count} paper(s)!`;
                uploadStatus.style.color = "#10b981";
                selectedFiles = [];
                fileInput.value = "";
                loadUploadedPapers();
            } else {
                uploadStatus.textContent = data.message || "Upload failed.";
                if (data.errors && data.errors.length > 0) {
                    uploadStatus.textContent += " " + data.errors.join(", ");
                }
                uploadStatus.style.color = "#dc2626";
            }
        } catch (err) {
            uploadStatus.textContent = `Upload error: ${err.message}`;
            uploadStatus.style.color = "#dc2626";
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = "Upload & Extract Questions";
        }
    }

    async function removePaper(paperId) {
        if (!confirm("Are you sure you want to remove this question paper?")) return;

        try {
            const res = await fetch(`${API_BASE}/api/paper-analyzer/papers/${paperId}`, {
                method: "DELETE",
                credentials: "include"
            });
            const data = await res.json();
            if (data.success) {
                loadUploadedPapers();
            } else {
                alert(data.message || "Could not delete paper.");
            }
        } catch (err) {
            alert(`Error deleting paper: ${err.message}`);
        }
    }

    async function handleClearAllPapers() {
        if (!confirm("Clear all uploaded question papers and previous reports?")) return;

        try {
            const res = await fetch(`${API_BASE}/api/paper-analyzer/clear`, {
                method: "POST",
                credentials: "include"
            });
            const data = await res.json();
            if (data.success) {
                uploadedPapers = [];
                currentReport = null;
                renderUploadedPapersList();
                if (resultsContainer) resultsContainer.innerHTML = "";
            }
        } catch (err) {
            alert("Error clearing papers: " + err.message);
        }
    }

    function renderUploadedPapersList() {
        if (!papersListContainer) return;

        const count = uploadedPapers.length;
        if (papersCountBadge) papersCountBadge.textContent = count;
        if (analyzeBtn) analyzeBtn.disabled = count === 0;

        if (count === 0) {
            papersListContainer.innerHTML = `
                <div style="text-align: center; padding: 24px; color: #94a3b8; font-size: 13px;">
                    No question papers uploaded yet.<br>Upload 2 or more previous papers to compare repetitions across years!
                </div>
            `;
            return;
        }

        papersListContainer.innerHTML = uploadedPapers.map(p => {
            const sizeKb = Math.round(p.file_size / 1024);
            const icon = p.file_type === "pdf" ? "📄" : "🖼️";
            return `
                <div class="pa-paper-item">
                    <div class="pa-paper-info">
                        <span class="pa-paper-icon">${icon}</span>
                        <div class="pa-paper-details">
                            <div class="pa-paper-name" title="${p.filename}">${p.filename}</div>
                            <div class="pa-paper-meta">
                                <span class="pa-paper-badge">${p.subject}</span>
                                <span>Year: <strong>${p.year || "N/A"}</strong></span>
                                <span>${sizeKb} KB</span>
                            </div>
                        </div>
                    </div>
                    <button type="button" class="pa-remove-btn" data-id="${p.id}" title="Remove this paper">
                        ✕
                    </button>
                </div>
            `;
        }).join("");

        papersListContainer.querySelectorAll(".pa-remove-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                removePaper(id);
            });
        });
    }

    // =========================================================
    // API CALLS: AI ANALYSIS
    // =========================================================

    async function loadLatestReport() {
        try {
            const res = await fetch(`${API_BASE}/api/paper-analyzer/report`, {
                method: "GET",
                credentials: "include"
            });
            const data = await res.json();
            if (data.success && data.has_report && data.report) {
                currentReport = data.report;
                renderReportDashboard(currentReport);
            }
        } catch (e) {
            console.warn("Could not load latest report:", e);
        }
    }

    async function triggerPaperAnalysis() {
        if (uploadedPapers.length === 0) {
            alert("Please upload at least one question paper before starting analysis.");
            return;
        }

        if (loadingBox) loadingBox.style.display = "block";
        if (resultsContainer) resultsContainer.innerHTML = "";
        if (analyzeBtn) analyzeBtn.disabled = true;

        // Animated progress steps
        const steps = [
            "Extracting text & formatting all questions from uploaded papers...",
            "Comparing questions across exam years with AI semantic similarity...",
            "Computing question repetition frequencies and marks distribution...",
            "Categorizing 3-tier priorities (High, Medium, Low) and exam strategy..."
        ];

        let stepIdx = 0;
        const intervalId = setInterval(() => {
            stepIdx = (stepIdx + 1) % steps.length;
            if (loadingStepText) loadingStepText.textContent = steps[stepIdx];
        }, 3200);

        try {
            const res = await fetch(`${API_BASE}/api/paper-analyzer/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({})
            });

            clearInterval(intervalId);
            const data = await res.json();

            if (data.success && data.report) {
                currentReport = data.report;
                renderReportDashboard(currentReport);
                // Scroll down to results smoothly
                resultsContainer?.scrollIntoView({ behavior: "smooth" });
            } else {
                alert(data.message || "Analysis failed. Please ensure papers contain legible exam questions.");
            }
        } catch (err) {
            clearInterval(intervalId);
            alert(`Analysis error: ${err.message}`);
        } finally {
            if (loadingBox) loadingBox.style.display = "none";
            if (analyzeBtn) analyzeBtn.disabled = uploadedPapers.length === 0;
        }
    }

    // =========================================================
    // RESULTS DASHBOARD RENDERING
    // =========================================================

    function renderReportDashboard(report) {
        if (!resultsContainer) return;

        const m = report.summary_metrics || {};
        const subject = report.subject || "All Subjects";
        const years = report.years_covered || "All Sessions";

        resultsContainer.innerHTML = `
            <!-- Summary Metric Cards -->
            <div class="pa-metrics-grid">
                <div class="pa-metric-card primary">
                    <span class="pa-metric-label">Papers Analyzed</span>
                    <span class="pa-metric-val">${report.total_papers_analyzed || uploadedPapers.length}</span>
                    <span class="pa-metric-sub">Years: ${years}</span>
                </div>
                <div class="pa-metric-card high">
                    <span class="pa-metric-label">High Priority Questions</span>
                    <span class="pa-metric-val">${m.high_priority_count || 0}</span>
                    <span class="pa-metric-sub">Most repeated in exams</span>
                </div>
                <div class="pa-metric-card repeated">
                    <span class="pa-metric-label">Repeated Questions</span>
                    <span class="pa-metric-val">${m.repeated_questions_count || 0}</span>
                    <span class="pa-metric-sub">Across multiple sessions</span>
                </div>
                <div class="pa-metric-card topics">
                    <span class="pa-metric-label">Total Questions Extracted</span>
                    <span class="pa-metric-val">${m.total_questions_extracted || 0}</span>
                    <span class="pa-metric-sub">Subject: ${subject}</span>
                </div>
            </div>

            <!-- Transparency Disclaimer Banner -->
            <div class="pa-disclaimer-banner">
                <span class="pa-disclaimer-icon">ℹ️</span>
                <div>
                    <strong>Exam Pattern Disclaimer:</strong> ${report.transparency_notice || "Predictions and priority tiers are derived from empirical repetition and semantic similarity across your uploaded papers. They reflect historical examination patterns and do not guarantee question appearance."}
                </div>
            </div>

            <!-- Navigation Tabs -->
            <div class="pa-tabs">
                <button type="button" class="pa-tab-btn ${activeTab === 'overview' ? 'active' : ''}" data-tab="overview">
                    📊 Exam Overview & Prep Strategy
                </button>
                <button type="button" class="pa-tab-btn ${activeTab === 'repeated' ? 'active' : ''}" data-tab="repeated">
                    🔁 Repeated Questions (${(report.repeated_questions || []).length})
                </button>
                <button type="button" class="pa-tab-btn ${activeTab === 'important' ? 'active' : ''}" data-tab="important">
                    ⭐ Important Questions (${(report.important_questions || []).length})
                </button>
            </div>

            <!-- Tab Content Container -->
            <div id="paTabContent"></div>

            <!-- Export / PDF Bar -->
            <div class="pa-export-bar">
                <button type="button" class="pa-btn" id="paExportPdfBtn">
                    🖨️ Export / Print Analysis Report
                </button>
            </div>
        `;

        // Bind Tabs
        resultsContainer.querySelectorAll(".pa-tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                resultsContainer.querySelectorAll(".pa-tab-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                activeTab = btn.getAttribute("data-tab");
                renderActiveTabContent();
            });
        });

        // Bind Export PDF Button
        resultsContainer.querySelector("#paExportPdfBtn")?.addEventListener("click", exportAnalysisAsPdf);

        renderActiveTabContent();
    }

    function renderActiveTabContent() {
        const container = document.getElementById("paTabContent");
        if (!container || !currentReport) return;

        if (activeTab === "overview") {
            renderOverviewTab(container);
        } else if (activeTab === "repeated") {
            renderRepeatedTab(container);
        } else if (activeTab === "important") {
            renderImportantTab(container);
        }
    }

    function renderOverviewTab(container) {
        const prep = currentReport.preparation_recommendation || {};
        const topics = currentReport.most_repeated_topics || [];
        const distribution = currentReport.paper_distribution || [];

        container.innerHTML = `
            <!-- Preparation Roadmap -->
            <h4 style="margin: 0 0 12px 0; color: #1e1b4b; font-size: 16px;">🎯 Recommended Exam Preparation Strategy</h4>
            <div class="pa-prep-grid">
                <div class="pa-prep-card" style="border-left: 4px solid #dc2626;">
                    <h4><span style="color: #dc2626;">●</span> Stage 1: High Yield (Must Master First)</h4>
                    <p>${prep.stage_1_high_yield || "Focus on core repeated definitions, theorems, and algorithms."}</p>
                </div>
                <div class="pa-prep-card" style="border-left: 4px solid #d97706;">
                    <h4><span style="color: #d97706;">●</span> Stage 2: Medium Yield (Core Practice)</h4>
                    <p>${prep.stage_2_medium_yield || "Solve numerical problems and conceptual differences appearing alternately."}</p>
                </div>
                <div class="pa-prep-card" style="border-left: 4px solid #4f46e5;">
                    <h4><span style="color: #4f46e5;">●</span> Stage 3: Final Revision</h4>
                    <p>${prep.stage_3_revision || "Review formulas, diagrams, and low-frequency edge case topics."}</p>
                </div>
                <div class="pa-prep-card" style="border-left: 4px solid #10b981;">
                    <h4><span style="color: #10b981;">●</span> Structural Paper Pattern Note</h4>
                    <p>${prep.pattern_note || "Questions are typically split between theory in Section A and long case studies in Section B."}</p>
                </div>
            </div>

            <!-- Most Repeated Topics Table -->
            <h4 style="margin: 24px 0 12px 0; color: #1e1b4b; font-size: 16px;">📚 High-Frequency Exam Topics & Weightage</h4>
            <div class="pa-table-container">
                <table class="pa-table">
                    <thead>
                        <tr>
                            <th>Topic Name</th>
                            <th>Repetition Count</th>
                            <th>Estimated Weightage</th>
                            <th>Historical Trend / Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${topics.length > 0 ? topics.map(t => `
                            <tr>
                                <td><strong>${t.topic}</strong></td>
                                <td><span class="pa-occurrences-badge">${t.frequency} times</span></td>
                                <td><strong style="color: #4f46e5;">${t.estimated_weightage || "15-20%"}</strong></td>
                                <td style="color: #475569;">${t.reason || ""}</td>
                            </tr>
                        `).join("") : `<tr><td colspan="4" style="text-align: center; color: #94a3b8;">No topic distribution available.</td></tr>`}
                    </tbody>
                </table>
            </div>

            <!-- Paper-wise breakdown table -->
            ${distribution.length > 0 ? `
                <h4 style="margin: 24px 0 12px 0; color: #1e1b4b; font-size: 16px;">📅 Session-Wise Paper Breakdown</h4>
                <div class="pa-table-container">
                    <table class="pa-table">
                        <thead>
                            <tr>
                                <th>Exam Session / Year</th>
                                <th>Paper Name</th>
                                <th>Questions Count</th>
                                <th>Dominant Topic Tested</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${distribution.map(d => `
                                <tr>
                                    <td><strong>${d.year || "N/A"}</strong></td>
                                    <td>${d.paper_title || "Question Paper"}</td>
                                    <td>${d.questions_count || "-"}</td>
                                    <td><span class="pa-tag">${d.dominant_topic || "Core Curriculum"}</span></td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            ` : ""}
        `;
    }

    function renderRepeatedTab(container) {
        const repeatedQs = currentReport.repeated_questions || [];

        if (repeatedQs.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0;">
                    <p style="color: #64748b; font-size: 14px;">No exact or semantically repeated questions detected across these papers.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="pa-questions-grid">
                ${repeatedQs.map((q, idx) => `
                    <div class="pa-question-card">
                        <div class="pa-q-header">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span class="pa-priority-badge HIGH">REPEATED ${q.occurrences}X</span>
                                <span class="pa-tag" style="background: #eef2ff; color: #4338ca;">${q.is_exact_or_semantic || "Semantically Similar"}</span>
                            </div>
                            <span style="font-size: 12px; color: #64748b;">Years: <strong>${(q.years_appeared || []).join(", ")}</strong></span>
                        </div>

                        <div class="pa-q-text">${q.primary_question}</div>

                        <div class="pa-q-meta-row">
                            <span>Topic: <strong class="pa-tag">${q.related_topic || "General"}</strong></span>
                            <span>Sources: ${(q.source_references || []).map(s => `<span class="pa-tag">${s}</span>`).join(" ")}</span>
                        </div>

                        <div class="pa-evidence-box">
                            <strong>Evidence:</strong> ${q.evidence || "Question concept recurring in multiple examination papers."}
                        </div>

                        ${q.variations && q.variations.length > 0 ? `
                            <button type="button" class="pa-variations-toggle" data-idx="${idx}">
                                <span>▶</span> View ${q.variations.length} Alternate Wording Variations from Papers
                            </button>
                            <div class="pa-variations-list" id="varList_${idx}" style="display: none;">
                                <strong>How this question was phrased in different papers:</strong>
                                <ul>
                                    ${q.variations.map(v => `<li>${v}</li>`).join("")}
                                </ul>
                            </div>
                        ` : ""}
                    </div>
                `).join("")}
            </div>
        `;

        // Bind variations toggle
        container.querySelectorAll(".pa-variations-toggle").forEach(btn => {
            btn.addEventListener("click", () => {
                const idx = btn.getAttribute("data-idx");
                const list = document.getElementById(`varList_${idx}`);
                if (list) {
                    const isHidden = list.style.display === "none";
                    list.style.display = isHidden ? "block" : "none";
                    btn.querySelector("span").textContent = isHidden ? "▼" : "▶";
                }
            });
        });
    }

    function renderImportantTab(container) {
        const importantQs = currentReport.important_questions || [];

        container.innerHTML = `
            <!-- Filter & Search Bar -->
            <div class="pa-filter-bar">
                <div class="pa-filter-pills">
                    <button type="button" class="pa-filter-pill ${activePriorityFilter === 'ALL' ? 'active' : ''}" data-filter="ALL">All (${importantQs.length})</button>
                    <button type="button" class="pa-filter-pill ${activePriorityFilter === 'HIGH' ? 'active' : ''}" data-filter="HIGH">High Priority</button>
                    <button type="button" class="pa-filter-pill ${activePriorityFilter === 'MEDIUM' ? 'active' : ''}" data-filter="MEDIUM">Medium Priority</button>
                    <button type="button" class="pa-filter-pill ${activePriorityFilter === 'LOW' ? 'active' : ''}" data-filter="LOW">Low Priority</button>
                </div>
                <input type="text" class="pa-search-input" id="paSearchInput" placeholder="🔍 Search questions or topics..." value="${searchQuery}">
            </div>

            <div class="pa-questions-grid" id="paFilteredQuestionsGrid"></div>
        `;

        // Bind filter pills
        container.querySelectorAll(".pa-filter-pill").forEach(pill => {
            pill.addEventListener("click", () => {
                container.querySelectorAll(".pa-filter-pill").forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                activePriorityFilter = pill.getAttribute("data-filter");
                filterAndRenderQuestions();
            });
        });

        // Bind search input
        const searchEl = document.getElementById("paSearchInput");
        if (searchEl) {
            searchEl.addEventListener("input", (e) => {
                searchQuery = e.target.value.toLowerCase().trim();
                filterAndRenderQuestions();
            });
        }

        filterAndRenderQuestions();
    }

    function filterAndRenderQuestions() {
        const grid = document.getElementById("paFilteredQuestionsGrid");
        if (!grid || !currentReport) return;

        let list = currentReport.important_questions || [];

        // Apply Priority Filter
        if (activePriorityFilter !== "ALL") {
            list = list.filter(q => (q.priority || "").toUpperCase() === activePriorityFilter);
        }

        // Apply Search Filter
        if (searchQuery) {
            list = list.filter(q =>
                (q.question || "").toLowerCase().includes(searchQuery) ||
                (q.related_topic || "").toLowerCase().includes(searchQuery) ||
                (q.evidence || "").toLowerCase().includes(searchQuery)
            );
        }

        if (list.length === 0) {
            grid.innerHTML = `
                <div style="text-align: center; padding: 40px; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; color: #64748b;">
                    No questions match the selected filter criteria.
                </div>
            `;
            return;
        }

        grid.innerHTML = list.map(q => {
            const prio = (q.priority || "MEDIUM").toUpperCase();
            const occ = q.occurrences || 1;
            const years = (q.years_appeared || []).join(", ");

            return `
                <div class="pa-question-card">
                    <div class="pa-q-header">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="pa-priority-badge ${prio}">${prio} PRIORITY</span>
                            <span class="pa-occurrences-badge">Appeared ${occ}x</span>
                        </div>
                        <span style="font-size: 12px; color: #64748b;">Exam Years: <strong>${years || "General"}</strong></span>
                    </div>

                    <div class="pa-q-text">${q.question}</div>

                    <div class="pa-q-meta-row">
                        <span>Related Topic: <strong class="pa-tag">${q.related_topic || "General"}</strong></span>
                        <span>Source: <span class="pa-tag">${q.source_reference || "Previous Paper"}</span></span>
                    </div>

                    <div class="pa-evidence-box">
                        <strong>Evidence:</strong> ${q.evidence || "Identified as a core examination topic."}
                    </div>
                </div>
            `;
        }).join("");
    }

    // =========================================================
    // EXPORT PDF / PRINT REPORT
    // =========================================================

    function exportAnalysisAsPdf() {
        if (!currentReport) {
            alert("No analysis report to export.");
            return;
        }

        // Create a printable window
        const printWindow = window.open("", "_blank");
        if (!printWindow) {
            alert("Please allow popups to export the PDF analysis report.");
            return;
        }

        const rep = currentReport;
        const metrics = rep.summary_metrics || {};

        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Paper Analyzer Report — ${rep.subject || 'Exam Intelligence'}</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; padding: 30px; color: #0f172a; line-height: 1.5; }
                    h1 { color: #1e1b4b; margin-bottom: 4px; font-size: 24px; }
                    .meta { color: #64748b; font-size: 13px; margin-bottom: 20px; }
                    .summary { display: flex; gap: 20px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 20px; margin-bottom: 24px; }
                    .metric { flex: 1; }
                    .metric-val { font-size: 20px; font-weight: 800; color: #4f46e5; }
                    .metric-lbl { font-size: 11px; text-transform: uppercase; color: #64748b; }
                    h2 { color: #312e81; font-size: 17px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-top: 28px; }
                    .q-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; page-break-inside: avoid; }
                    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; }
                    .badge.HIGH { background: #fee2e2; color: #dc2626; }
                    .badge.MEDIUM { background: #fef3c7; color: #b45309; }
                    .badge.LOW { background: #f1f5f9; color: #475569; }
                    .disclaimer { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 10px 14px; font-size: 12px; color: #1e40af; margin-top: 30px; }
                    @media print { button { display: none; } }
                </style>
            </head>
            <body>
                <button onclick="window.print()" style="margin-bottom:16px; padding:8px 16px; background:#4f46e5; color:#fff; border:none; border-radius:6px; cursor:pointer;">Print to PDF</button>
                <h1>Bharat Study Buddy — Paper Analyzer AI Report</h1>
                <div class="meta">Subject: <strong>${rep.subject || 'All Subjects'}</strong> • Years Covered: <strong>${rep.years_covered}</strong> • Generated by AI Intelligence</div>

                <div class="summary">
                    <div class="metric"><div class="metric-val">${rep.total_papers_analyzed || 0}</div><div class="metric-lbl">Papers Analyzed</div></div>
                    <div class="metric"><div class="metric-val">${metrics.high_priority_count || 0}</div><div class="metric-lbl">High Priority Qs</div></div>
                    <div class="metric"><div class="metric-val">${metrics.repeated_questions_count || 0}</div><div class="metric-lbl">Repeated Qs</div></div>
                    <div class="metric"><div class="metric-val">${metrics.total_questions_extracted || 0}</div><div class="metric-lbl">Total Questions</div></div>
                </div>

                <h2>Repeat Examination Questions (Frequency >= 2)</h2>
                ${(rep.repeated_questions || []).map(q => `
                    <div class="q-card">
                        <div style="margin-bottom:4px;">
                            <span class="badge HIGH">REPEATED ${q.occurrences}X</span>
                            <span style="font-size:12px; color:#64748b; margin-left:8px;">Years: ${(q.years_appeared || []).join(", ")}</span>
                        </div>
                        <div style="font-weight:600; font-size:14px; margin:6px 0;">${q.primary_question}</div>
                        <div style="font-size:12px; color:#475569;">Topic: <strong>${q.related_topic || ""}</strong> • Evidence: ${q.evidence || ""}</div>
                    </div>
                `).join("")}

                <h2>High & Medium Priority Exam Questions</h2>
                ${(rep.important_questions || []).filter(q => q.priority === 'HIGH' || q.priority === 'MEDIUM').map(q => `
                    <div class="q-card">
                        <div style="margin-bottom:4px;">
                            <span class="badge ${q.priority}">${q.priority}</span>
                            <span style="font-size:12px; color:#64748b; margin-left:8px;">Appeared: ${q.occurrences}x (${(q.years_appeared || []).join(", ")})</span>
                        </div>
                        <div style="font-weight:600; font-size:14px; margin:6px 0;">${q.question}</div>
                        <div style="font-size:12px; color:#475569;">Topic: ${q.related_topic || ""} • Source: ${q.source_reference || ""}</div>
                    </div>
                `).join("")}

                <div class="disclaimer">
                    <strong>Disclaimer:</strong> ${rep.transparency_notice || "Predictions reflect historical exam frequency and do not guarantee future question appearance."}
                </div>
            </body>
            </html>
        `);
        printWindow.document.close();
    }

    // Initialize when DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initPaperAnalyzer);
    } else {
        initPaperAnalyzer();
    }
})();
