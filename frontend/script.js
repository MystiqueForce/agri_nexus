/* ============================================================
   NexusAgri — Frontend Application Logic
   ============================================================ */

const API_BASE = window.location.origin;

// ── State ────────────────────────────────────────────────────
let currentMode = "auto"; // "auto", "health", "market"
let uploadedFile = null;
let uploadedFileType = null; // "image" or "video"
let isProcessing = false;

// ── Follow-up & Context Tracking ────────────────────────────
// Tracks whether the last response was a follow-up question so the
// next user message is sent as a follow_up_answer, not a new query.
let pendingFollowUp = null;   // { originalQuery, agentType }
let pendingLocation = null;   // { originalQuery, agentType }

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
