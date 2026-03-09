/* ============================================================
   NexusAgri — Frontend Application Logic
   ============================================================ */

const API_BASE = window.location.origin;

// ── State ────────────────────────────────────────────────────
let currentMode = "auto"; // "auto", "health", "market"
let uploadedFile = null;
let uploadedFileType = null; // "image" or "video"
let isProcessing = false;
let selectedVoiceLanguage = "en-US"; // Default to English

// ── Follow-up & Context Tracking ────────────────────────────
// Tracks whether the last response was a follow-up question so the
// next user message is sent as a follow_up_answer, not a new query.
let pendingFollowUp = null;   // { originalQuery, agentType }
let pendingLocation = null;   // { originalQuery, agentType }

// ── Market Session Context ──────────────────────────────────
// Stores the last market response so follow-up questions can be
// answered contextually without re-running the full ML pipeline.
let marketSession = null;     // { response, language, query }

// ── DOM References ───────────────────────────────────────────
const messagesContainer = document.getElementById("messages-container");
const queryInput = document.getElementById("query-input");
const sendBtn = document.getElementById("send-btn");
const welcomeScreen = document.getElementById("welcome-screen");
const statusBadge = document.getElementById("status-badge");
const currentModeText = document.getElementById("current-mode-text");
const filePreview = document.getElementById("file-preview");
const previewContent = document.getElementById("preview-content");

// ── Mode Selection ───────────────────────────────────────────
document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentMode = btn.dataset.mode;

        const labels = {
            auto: "Auto Detect Mode",
            health: "🌿 Health Agent",
            market: "📊 Market Agent",
        };
        currentModeText.textContent = labels[currentMode];
    });
});

// ── Sidebar Toggle (Mobile) ─────────────────────────────────
function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
}

// ── Auto-resize Textarea ────────────────────────────────────
function autoResize(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

// ── Keyboard Handling ───────────────────────────────────────
function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// ── File Upload ─────────────────────────────────────────────
function handleFileUpload(event, type) {
    const file = event.target.files[0];
    if (!file) return;

    uploadedFile = file;
    uploadedFileType = type;

    // Show preview
    filePreview.style.display = "flex";
    if (type === "image") {
        const url = URL.createObjectURL(file);
        previewContent.innerHTML = `<img src="${url}" alt="Upload preview"><span>${file.name}</span>`;
    } else {
        previewContent.innerHTML = `<span>🎥</span><span>${file.name}</span>`;
    }
}

function clearFile() {
    uploadedFile = null;
    uploadedFileType = null;
    filePreview.style.display = "none";
    previewContent.innerHTML = "";
    document.getElementById("image-input").value = "";
    document.getElementById("video-input").value = "";
}

// ── Voice Input (Web Speech API) ────────────────────────────
let recognition = null;
let isRecording = false;
let cumulativeText = "";

function toggleVoiceInput() {
    // If already recording, user clicked to stop
    if (isRecording) {
        isRecording = false;
        if (recognition) {
            try { recognition.stop(); } catch (e) { }
        }

        // Reset UI
        const micBtn = document.getElementById("mic-btn");
        micBtn.classList.remove("recording");
        micBtn.title = "Voice input";
        statusBadge.textContent = "Ready";
        statusBadge.classList.remove("processing");

        // Final text cleanup
        queryInput.value = queryInput.value.trim();
        queryInput.focus();
        return;
    }

    // Otherwise, start recording
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Speech recognition is not supported in your browser.\n\nPlease use:\n• Chrome\n• Edge\n• Safari (iOS/macOS)\n\nNote: Firefox does not support Web Speech API.");
        return;
    }

    // Check if we're on HTTPS or localhost
    const isSecure = window.location.protocol === 'https:' || 
                     window.location.hostname === 'localhost' || 
                     window.location.hostname === '127.0.0.1';
    
    if (!isSecure) {
        alert("⚠️ Microphone access requires HTTPS or localhost.\n\nCurrent URL: " + window.location.protocol + "//" + window.location.host + "\n\nPlease access the app via:\n• https://... (secure connection)\n• http://localhost:...\n• http://127.0.0.1:...");
        return;
    }

    isRecording = true;

    // Pick up whatever text is already in the box
    const currentText = queryInput.value.trim();
    cumulativeText = currentText ? currentText + " " : "";

    // Set UI to recording
    const micBtn = document.getElementById("mic-btn");
    micBtn.classList.add("recording");
    micBtn.title = "Stop recording";
    statusBadge.textContent = "🎤 Listening... (tap mic to stop)";
    statusBadge.classList.add("processing");

    // Start the continuous loop
    startRecognitionLoop(SpeechRecognition);
}

function startRecognitionLoop(SpeechRecognition) {
    if (!isRecording) return; // User stopped it manually

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    
    // Use the selected language from the dropdown
    recognition.lang = selectedVoiceLanguage;
    
    console.log("🎤 Starting recognition with language:", recognition.lang);

    recognition.onstart = () => {
        console.log("✅ Recognition started successfully");
    };

    recognition.onresult = (event) => {
        console.log("🎤 Got speech result:", event.results.length, "results");
        
        let interimText = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const res = event.results[i];
            const transcript = res[0].transcript;
            console.log(`  Result ${i}: "${transcript}" (final: ${res.isFinal})`);
            
            if (res.isFinal) {
                cumulativeText += transcript + " ";
            } else {
                interimText += transcript;
            }
        }
        
        // Update input box immediately with both final + current interim
        const fullText = (cumulativeText + interimText).trim();
        console.log("📝 Updating input box with:", fullText);
        queryInput.value = fullText;
        autoResize(queryInput);
    };

    recognition.onerror = (event) => {
        console.error("❌ Speech error:", event.error, event);
        
        if (event.error === "not-allowed" || event.error === "not-supported") {
            alert("Microphone access denied or not supported. Please:\n1. Allow microphone permissions in your browser\n2. Use HTTPS or localhost\n3. Use Chrome, Edge, or Safari");
            isRecording = false;
            const micBtn = document.getElementById("mic-btn");
            micBtn.classList.remove("recording");
            statusBadge.textContent = "Ready";
            statusBadge.classList.remove("processing");
        } else if (event.error === "no-speech") {
            // Silence detected, just continue listening
            console.log("⚠️ No speech detected, continuing...");
        } else if (event.error === "aborted") {
            // User stopped or browser killed it
            console.log("⏹️ Recognition aborted");
            isRecording = false;
        } else if (event.error === "network") {
            console.error("❌ Network error - speech recognition requires internet connection");
            alert("Speech recognition requires an internet connection. Please check your connection and try again.");
            isRecording = false;
            const micBtn = document.getElementById("mic-btn");
            micBtn.classList.remove("recording");
            statusBadge.textContent = "Ready";
            statusBadge.classList.remove("processing");
        } else {
            console.error("❌ Unknown error:", event.error);
        }
    };

    recognition.onend = () => {
        console.log("🔄 Recognition ended, isRecording:", isRecording);
        // Did the user click stop? If so, isRecording=false and we don't restart.
        // Did Chrome kill it due to HTTP security/silence? If so, isRecording=true and we restart silently!
        if (isRecording) {
            // Must use a timeout because starting synchronously inside onend triggers an InvalidStateError
            setTimeout(() => {
                if (isRecording) startRecognitionLoop(SpeechRecognition);
            }, 250);
        } else {
            // Clean up UI if it somehow hasn't been cleaned up
            const micBtn = document.getElementById("mic-btn");
            if (micBtn.classList.contains("recording")) {
                micBtn.classList.remove("recording");
                statusBadge.textContent = "Ready";
                statusBadge.classList.remove("processing");
            }
        }
    };

    try {
        recognition.start();
        console.log("🎤 Calling recognition.start()...");
    } catch (e) {
        console.error("❌ Failed to start speech recognition:", e);
        alert("Failed to start recording: " + e.message);
        isRecording = false;
        const micBtn = document.getElementById("mic-btn");
        micBtn.classList.remove("recording");
        statusBadge.textContent = "Ready";
        statusBadge.classList.remove("processing");
    }
}

// Add audio level indicator (optional debugging)
function checkMicrophoneInput() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            console.log("✅ Microphone stream obtained");
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const analyser = audioContext.createAnalyser();
            const microphone = audioContext.createMediaStreamSource(stream);
            microphone.connect(analyser);
            analyser.fftSize = 256;
            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            
            function checkLevel() {
                analyser.getByteFrequencyData(dataArray);
                const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
                if (average > 10) {
                    console.log("🔊 Audio detected, level:", Math.round(average));
                }
            }
            
            // Check for 5 seconds
            const interval = setInterval(checkLevel, 500);
            setTimeout(() => {
                clearInterval(interval);
                stream.getTracks().forEach(track => track.stop());
                console.log("🔇 Microphone test complete");
            }, 5000);
        })
        .catch(err => {
            console.error("❌ Cannot access microphone:", err);
        });
}

// ── Quick Query ─────────────────────────────────────────────
function sendQuickQuery(text) {
    queryInput.value = text;
    autoResize(queryInput);
    sendMessage();
}

// ── Send Message ────────────────────────────────────────────
async function sendMessage() {
    const userInput = queryInput.value.trim();
    if (!userInput || isProcessing) return;

    // Hide welcome screen
    if (welcomeScreen) {
        welcomeScreen.style.display = "none";
    }

    // Add user message
    addMessage("user", userInput, uploadedFile);

    // Clear input
    queryInput.value = "";
    queryInput.style.height = "auto";

    // Set processing state
    isProcessing = true;
    sendBtn.disabled = true;
    statusBadge.textContent = "Processing...";
    statusBadge.classList.add("processing");

    // Add typing indicator
    const typingId = addTypingIndicator();

    try {
        const farmId = document.getElementById("farm-id").value || "anonymous";
        const sidebarLocation = document.getElementById("farm-location").value || "";

        let response;

        // ── Handle pending follow-up (health agent asked a question) ──
        if (pendingFollowUp) {
            const orig = pendingFollowUp;
            pendingFollowUp = null; // clear before calling

            const formData = new FormData();
            formData.append("query", orig.originalQuery);
            formData.append("farm_id", farmId);
            formData.append("follow_up_answer", userInput);

            if (orig.agentType === "health" || currentMode === "health") {
                const res = await fetch(`${API_BASE}/health/diagnose`, { method: "POST", body: formData });
                if (!res.ok) throw new Error(`API error: ${res.status}`);
                response = await res.json();
            } else {
                const res = await fetch(`${API_BASE}/chat`, { method: "POST", body: formData });
                if (!res.ok) throw new Error(`API error: ${res.status}`);
                response = await res.json();
            }

            // ── Handle pending location (market agent asked for address) ──
        } else if (pendingLocation) {
            const orig = pendingLocation;
            pendingLocation = null;

            // The user's input IS the location
            response = await callMarketEndpoint(orig.originalQuery, farmId, userInput);

            // ── Handle market continuation (follow-up after recommendation) ──
        } else if (marketSession && !uploadedFile) {
            response = await callMarketFollowup(userInput, farmId);

            // ── Normal message flow ──
        } else if (currentMode === "health" || (currentMode === "auto" && uploadedFile)) {
            response = await callHealthEndpoint(userInput, farmId);
        } else if (currentMode === "market") {
            response = await callMarketEndpoint(userInput, farmId, sidebarLocation);
        } else {
            response = await callChatEndpoint(userInput, farmId, sidebarLocation);
        }

        // Remove typing indicator
        removeTypingIndicator(typingId);

        // ── Track follow-up / location state for next message ──
        if (response.needs_follow_up && response.follow_up_question) {
            pendingFollowUp = {
                originalQuery: userInput,
                agentType: response.agent_type || (currentMode !== "auto" ? currentMode : "health"),
            };
        } else if (response.needs_location && response.follow_up_question) {
            pendingLocation = {
                originalQuery: userInput,
                agentType: "market",
            };
        } else {
            // Successful response — clear any pending state
            pendingFollowUp = null;
            pendingLocation = null;
        }

        // ── Track market session for continuations ──
        const isMarketResp = response.agent_type === "market"
            || response.price_predictions
            || response.recommendation;
        if (isMarketResp && response.response && !response.needs_location && !response.is_continuation) {
            marketSession = {
                response: response.response,
                language: response.original_language || "en",
                query: userInput,
            };
        } else if (response.agent_type === "health") {
            // Clear market session when switching to health agent
            marketSession = null;
        }

        // Add response
        addAssistantMessage(response);
    } catch (error) {
        removeTypingIndicator(typingId);
        addMessage("assistant", `Error: ${error.message}. Please check your connection and try again.`);
        // Clear pending state on error
        pendingFollowUp = null;
        pendingLocation = null;
    }

    // Reset state
    isProcessing = false;
    sendBtn.disabled = false;
    statusBadge.textContent = "Ready";
    statusBadge.classList.remove("processing");
    clearFile();
}

// ── API Calls ───────────────────────────────────────────────
async function callChatEndpoint(query, farmId, location) {
    const formData = new FormData();
    formData.append("query", query);
    formData.append("farm_id", farmId);
    if (location) formData.append("location", location);
    if (uploadedFile && uploadedFileType === "image") {
        formData.append("image", uploadedFile);
    }
    if (uploadedFile && uploadedFileType === "video") {
        formData.append("video", uploadedFile);
    }

    const res = await fetch(`${API_BASE}/chat`, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
}

async function callHealthEndpoint(query, farmId) {
    const formData = new FormData();
    formData.append("query", query);
    formData.append("farm_id", farmId);
    if (uploadedFile && uploadedFileType === "image") {
        formData.append("image", uploadedFile);
    }
    if (uploadedFile && uploadedFileType === "video") {
        formData.append("video", uploadedFile);
    }

    const res = await fetch(`${API_BASE}/health/diagnose`, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
}

async function callMarketEndpoint(query, farmId, location) {
    const body = {
        query: query,
        farm_id: farmId,
        location: location || null,
    };

    const res = await fetch(`${API_BASE}/market/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
}

async function callMarketFollowup(query, farmId) {
    const body = {
        query: query,
        previous_response: marketSession.response,
        farm_id: farmId,
        original_language: marketSession.language || "en",
    };

    const res = await fetch(`${API_BASE}/market/followup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
}

// ── Message Rendering ───────────────────────────────────────
function addMessage(role, text, file = null) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;

    const avatar = role === "user" ? "👤" : "🌾";
    let fileHtml = "";
    if (file && uploadedFileType === "image") {
        const url = URL.createObjectURL(file);
        fileHtml = `<img class="message-image" src="${url}" alt="Uploaded image">`;
    } else if (file && uploadedFileType === "video") {
        fileHtml = `<p style="color: var(--text-muted); font-size: 12px;">📎 ${file.name}</p>`;
    }

    msgDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-bubble">
            <p>${escapeHtml(text)}</p>
            ${fileHtml}
        </div>
    `;

    messagesContainer.appendChild(msgDiv);
    scrollToBottom();
}

function addAssistantMessage(data) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant";

    // Check if it's a structured health response
    const responseText = data.response || data.final_response || "";
    const isHealthResponse = data.result && data.severity;
    const isMarketResponse = data.price_predictions && data.price_predictions.length > 0;

    let cardHtml = "";

    if (data.needs_follow_up && data.follow_up_question) {
        cardHtml = `
            <div class="response-card">
                <h4>❓ More Information Needed</h4>
                <p>${escapeHtml(data.follow_up_question)}</p>
            </div>
        `;
    } else if (data.needs_location && data.follow_up_question) {
        cardHtml = `
            <div class="response-card">
                <h4>📍 Location Required</h4>
                <p>${escapeHtml(data.follow_up_question)}</p>
            </div>
        `;
    } else if (responseText) {
        cardHtml = `
            <div class="response-card">
                <pre style="white-space: pre-wrap; word-break: break-word; font-family: inherit; font-size: 14px; color: var(--text-secondary);">${escapeHtml(responseText)}</pre>
            </div>
        `;
    } else {
        cardHtml = `<p>${escapeHtml(JSON.stringify(data, null, 2))}</p>`;
    }

    msgDiv.innerHTML = `
        <div class="message-avatar">🌾</div>
        <div class="message-bubble">
            ${cardHtml}
        </div>
    `;

    messagesContainer.appendChild(msgDiv);
    scrollToBottom();
}

// ── Typing Indicator ────────────────────────────────────────
let typingCounter = 0;

function addTypingIndicator() {
    const id = `typing-${++typingCounter}`;
    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant";
    msgDiv.id = id;
    msgDiv.innerHTML = `
        <div class="message-avatar">🌾</div>
        <div class="message-bubble">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(msgDiv);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ── Farm Profile ────────────────────────────────────────────
async function saveProfile() {
    const farmId = document.getElementById("farm-id").value;
    const location = document.getElementById("farm-location").value;
    const crops = document.getElementById("farm-crops").value;

    if (!farmId) {
        alert("Please enter a Farm ID");
        return;
    }

    try {
        const body = {
            farm_id: farmId,
            location: location || null,
            crops: crops ? crops.split(",").map((c) => c.trim()) : [],
        };

        const res = await fetch(`${API_BASE}/farm/update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (res.ok) {
            const btn = document.getElementById("btn-save-profile");
            btn.textContent = "✓ Saved!";
            btn.style.color = "var(--accent-primary)";
            setTimeout(() => {
                btn.textContent = "Save Profile";
                btn.style.color = "";
            }, 2000);
        }
    } catch (error) {
        console.error("Failed to save profile:", error);
    }
}

// ── Voice Language Selection ────────────────────────────────
function updateVoiceLanguage() {
    const select = document.getElementById("voice-language");
    selectedVoiceLanguage = select.value;
    
    // Save to localStorage
    localStorage.setItem("voiceLanguage", selectedVoiceLanguage);
    
    console.log("🌐 Voice language changed to:", selectedVoiceLanguage);
    
    // Show confirmation
    const languageNames = {
        "en-US": "English",
        "hi-IN": "Hindi",
        "ta-IN": "Tamil",
        "te-IN": "Telugu",
        "kn-IN": "Kannada",
        "mr-IN": "Marathi",
        "bn-IN": "Bengali",
        "gu-IN": "Gujarati",
        "ml-IN": "Malayalam",
        "pa-IN": "Punjabi",
        "ur-IN": "Urdu"
    };
    
    statusBadge.textContent = `Language: ${languageNames[selectedVoiceLanguage]}`;
    setTimeout(() => {
        statusBadge.textContent = "Ready";
    }, 2000);
}

function loadVoiceLanguage() {
    const saved = localStorage.getItem("voiceLanguage");
    if (saved) {
        selectedVoiceLanguage = saved;
        document.getElementById("voice-language").value = saved;
        console.log("🌐 Loaded saved voice language:", saved);
    }
}

// ── Helpers ─────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ── Initialize ──────────────────────────────────────────────
queryInput.focus();

// Load saved voice language
loadVoiceLanguage();

// Check speech recognition support on load
(function checkSpeechSupport() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const isSecure = window.location.protocol === 'https:' || 
                     window.location.hostname === 'localhost' || 
                     window.location.hostname === '127.0.0.1';
    
    console.log("🎤 Speech Recognition Status:");
    console.log("  - API Available:", !!SpeechRecognition);
    console.log("  - Secure Context:", isSecure);
    console.log("  - Protocol:", window.location.protocol);
    console.log("  - Hostname:", window.location.hostname);
    console.log("  - Selected Language:", selectedVoiceLanguage);
    
    if (!SpeechRecognition) {
        console.warn("⚠️ Web Speech API not supported in this browser");
    } else if (!isSecure) {
        console.warn("⚠️ Microphone requires HTTPS or localhost");
    } else {
        console.log("✅ Voice input ready!");
    }
})();
