// API endpoints and WebSocket configuration
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
let socket = null;
let currentFiles = [];
let selectedFilePath = "";
let selectedFileAction = "CREATE";

// DOM elements
const logsTimeline = document.getElementById("logs-timeline");
const fileTree = document.getElementById("file-tree");
const codeViewer = document.getElementById("code-viewer");
const diffViewer = document.getElementById("diff-viewer");
const activeFilename = document.getElementById("active-filename");
const fileActionBadge = document.getElementById("file-action-badge");
const terminalBody = document.getElementById("terminal-body");
const prMarkdownBody = document.getElementById("pr-markdown-body");
const prHeadlineTitle = document.getElementById("pr-headline-title");

const runBtn = document.getElementById("run-btn");
const resetBtn = document.getElementById("reset-btn");
const settingsBtn = document.getElementById("settings-btn");
const saveKeysBtn = document.getElementById("save-keys-btn");
const closeModalBtn = document.getElementById("close-modal-btn");
const settingsModal = document.getElementById("settings-modal");
const mergePrBtn = document.getElementById("merge-pr-btn");

const promptInput = document.getElementById("prompt-input");
const providerSelect = document.getElementById("provider-select");
const crossModelCheck = document.getElementById("cross-model-check");

const viewCodeBtn = document.getElementById("view-code-btn");
const viewDiffBtn = document.getElementById("view-diff-btn");

// Agent colors for glow borders
const agentGlowColors = {
    planner: "var(--planner-color)",
    engineer: "var(--engineer-color)",
    reviewer: "var(--reviewer-color)",
    tester: "var(--tester-color)",
    documenter: "var(--documenter-color)",
    system: "var(--system-color)"
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initSettings();
    connectWebSocket();
    fetchFiles();
    fetchHistory();
    
    // Load existing keys from local storage
    loadSavedKeys();

    // Bind event listeners
    runBtn.addEventListener("click", handleRunOrchestration);
    resetBtn.addEventListener("click", handleClearSystem);
    settingsBtn.addEventListener("click", () => settingsModal.classList.remove("hidden"));
    closeModalBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
    saveKeysBtn.addEventListener("click", handleSaveKeys);
    mergePrBtn.addEventListener("click", handleMergePr);
    
    viewCodeBtn.addEventListener("click", () => toggleCodeView("code"));
    viewDiffBtn.addEventListener("click", () => toggleCodeView("diff"));

    // Demo triggers
    document.querySelectorAll(".btn-demo").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const demoId = btn.getAttribute("data-demo");
            triggerDemo(demoId);
        });
    });
});

// Tab Management
function initTabs() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            const tabId = btn.getAttribute("data-tab");
            document.getElementById(tabId).classList.add("active");
        });
    });
}

// Key Storage
function initSettings() {
    window.addEventListener("click", (e) => {
        if (e.target === settingsModal) {
            settingsModal.classList.add("hidden");
        }
    });
}

function handleSaveKeys() {
    const keys = {
        ANTHROPIC_API_KEY: document.getElementById("key-anthropic").value.trim(),
        OPENAI_API_KEY: document.getElementById("key-openai").value.trim(),
        GEMINI_API_KEY: document.getElementById("key-gemini").value.trim()
    };
    localStorage.setItem("advocate_keys", JSON.stringify(keys));
    settingsModal.classList.add("hidden");
    addLogToTimeline({
        sender: "system",
        event_type: "info",
        message: "Developer API credentials saved locally.",
        timestamp: new Date().toLocaleTimeString()
    });
}

function loadSavedKeys() {
    const saved = localStorage.getItem("advocate_keys");
    if (saved) {
        try {
            const keys = JSON.parse(saved);
            document.getElementById("key-anthropic").value = keys.ANTHROPIC_API_KEY || "";
            document.getElementById("key-openai").value = keys.OPENAI_API_KEY || "";
            document.getElementById("key-gemini").value = keys.GEMINI_API_KEY || "";
        } catch (e) {
            console.error("Failed to parse keys from localStorage:", e);
        }
    }
}

function getSavedKeys() {
    const saved = localStorage.getItem("advocate_keys");
    return saved ? JSON.parse(saved) : {};
}

// WebSocket connection
function connectWebSocket() {
    socket = new WebSocket(WS_URL);
    
    socket.onopen = () => {
        console.log("WebSocket connected.");
        document.querySelector(".status-indicator").className = "status-indicator online";
        document.querySelector(".status-text").innerText = "SYSTEM ONLINE";
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleIncomingEvent(data);
    };

    socket.onclose = () => {
        console.log("WebSocket disconnected. Retrying in 5 seconds...");
        document.querySelector(".status-indicator").className = "status-indicator offline";
        document.querySelector(".status-text").innerText = "SYSTEM DISCONNECTED";
        setTimeout(connectWebSocket, 5000);
    };

    socket.onerror = (err) => {
        console.error("WebSocket error:", err);
    };
}

// Handle Bus Events
function handleIncomingEvent(event) {
    // 1. Add log to screen
    addLogToTimeline(event);
    
    // 2. Set active node in canvas
    highlightActiveAgent(event.sender);
    
    // 3. Handle payload updates
    const { event_type, payload } = event;
    
    if (event_type === "code_written" || event_type === "pr_drafted") {
        fetchFiles();
    }
    
    if (event_type === "test_started") {
        document.querySelector("[data-tab='terminal-tab']").click();
        terminalBody.innerHTML = `<span class="term-prompt">C:\\workspace&gt;</span> <span class="term-text gray">Running tests for task...</span><br>`;
    }
    
    if (event_type === "test_completed" && payload) {
        const textClass = payload.success ? "term-success" : "term-error";
        let output = `<br><span class="term-prompt">C:\\workspace&gt;</span> <span class="term-text gray">python -m unittest ${payload.test_file_path || ''}</span><br>`;
        if (payload.stdout) {
            output += `<pre class="term-text">${escapeHTML(payload.stdout)}</pre>`;
        }
        if (payload.stderr) {
            output += `<pre class="term-text red">${escapeHTML(payload.stderr)}</pre>`;
        }
        output += `<br><span class="${textClass}">== Test Status: ${payload.success ? 'PASSED' : 'FAILED'} (Exit code: ${payload.exit_code}) ==</span><br>`;
        
        terminalBody.innerHTML = output;
        terminalBody.scrollTop = terminalBody.scrollHeight;
    }
    
    if (event_type === "pr_drafted" && payload && payload.pr_markdown) {
        document.querySelector("[data-tab='pr-tab']").click();
        renderPR(payload.pr_markdown);
    }
}

// Highlight Agent Node
function highlightActiveAgent(agentName) {
    document.querySelectorAll(".agent-node").forEach(node => {
        node.classList.remove("active");
        node.style.removeProperty("--node-glow-color");
    });
    
    if (agentName && agentName !== "system") {
        const activeNode = document.getElementById(`node-${agentName}`);
        if (activeNode) {
            activeNode.classList.add("active");
            activeNode.style.setProperty("--node-glow-color", agentGlowColors[agentName]);
            
            // Set dynamic status sub-text on node
            const statusMap = {
                planner: "Planning",
                engineer: "Writing Code",
                reviewer: "Reviewing",
                tester: "Testing Code",
                documenter: "Drafting PR"
            };
            activeNode.querySelector(".node-info span").innerText = statusMap[agentName] || "Running";
        }
    }
}

// Add Log Line
function addLogToTimeline(event) {
    // Remove empty state if present
    const emptyMsg = logsTimeline.querySelector(".timeline-empty");
    if (emptyMsg) {
        emptyMsg.remove();
    }
    
    const item = document.createElement("div");
    item.className = `log-item ${event.sender} ${event.event_type === 'error' ? 'error' : ''}`;
    
    const header = document.createElement("div");
    header.className = "log-header";
    header.innerHTML = `
        <span class="log-sender-badge">${event.sender}</span>
        <span class="log-time">${event.timestamp}</span>
    `;
    
    const msg = document.createElement("div");
    msg.className = "log-message";
    msg.innerText = event.message;
    
    item.appendChild(header);
    item.appendChild(msg);
    
    // Check if we have logs data to display (e.g. comments, explanations, JSON details)
    if (event.payload) {
        const payload = event.payload;
        let summaryText = "";
        
        if (event.event_type === "planning_completed" && payload.tasks) {
            summaryText = "TASKS DECOMPOSED:\n" + payload.tasks.map(t => `- [${t.action}] ${t.file_path}: ${t.title}`).join("\n");
        } else if (event.event_type === "code_written") {
            summaryText = `EXPLANATION: ${payload.explanation || ''}\nFILE: ${payload.file_path}`;
        } else if (event.event_type === "review_completed" && payload.comments) {
            summaryText = `APPROVED: ${payload.approved}\nCOMMENTS:\n` + payload.comments.map(c => `- ${c}`).join("\n");
        } else if (event.event_type === "test_completed" && payload.test_explanation) {
            summaryText = `EXPLANATION: ${payload.test_explanation}\nSTATUS: ${payload.success ? 'PASS' : 'FAIL'}`;
        }
        
        if (summaryText) {
            const pre = document.createElement("pre");
            pre.className = "log-payload-summary";
            pre.innerText = summaryText;
            item.appendChild(pre);
        }
    }
    
    logsTimeline.appendChild(item);
    logsTimeline.scrollTop = logsTimeline.scrollHeight;
}

// RENDER FILES IN EXPLORER
async function fetchFiles() {
    try {
        const res = await fetch("/api/files");
        const files = await res.json();
        currentFiles = files;
        renderFileTree(files);
    } catch (e) {
        console.error("Failed to fetch files:", e);
    }
}

function renderFileTree(files) {
    fileTree.innerHTML = "";
    if (files.length === 0) {
        fileTree.innerHTML = `<li class="empty-tree">No files written yet</li>`;
        return;
    }
    
    files.forEach(file => {
        const li = document.createElement("li");
        const ext = file.path.split(".").pop();
        const iconClass = ext === "py" ? "fa-brands fa-python" : "fa-regular fa-file-lines";
        
        li.innerHTML = `<i class="${iconClass}"></i> ${file.path}`;
        li.setAttribute("data-path", file.path);
        
        if (file.path === selectedFilePath) {
            li.classList.add("active");
        }
        
        li.addEventListener("click", () => {
            selectFile(file);
        });
        
        fileTree.appendChild(li);
    });
    
    // Auto-select PR description or first python file if none selected
    if (!selectedFilePath && files.length > 0) {
        const first = files.find(f => f.path.endsWith(".py")) || files[0];
        selectFile(first);
    }
}

function selectFile(file) {
    selectedFilePath = file.path;
    document.querySelectorAll("#file-tree li").forEach(li => {
        if (li.getAttribute("data-path") === file.path) {
            li.classList.add("active");
        } else {
            li.classList.remove("active");
        }
    });

    activeFilename.innerHTML = `<i class="fa-regular fa-file-code"></i> ${file.path}`;
    
    // Determine action badge (CREATE/MODIFY)
    const isTest = file.path.startsWith("test_");
    const isPr = file.path === "PR_DESCRIPTION.md";
    if (isPr) {
        fileActionBadge.innerText = "PR DOC";
        fileActionBadge.style.background = "rgba(6, 182, 212, 0.15)";
        fileActionBadge.style.color = "var(--documenter-color)";
        fileActionBadge.style.borderColor = "rgba(6, 182, 212, 0.3)";
    } else if (isTest) {
        fileActionBadge.innerText = "TEST SUITE";
        fileActionBadge.style.background = "rgba(16, 185, 129, 0.15)";
        fileActionBadge.style.color = "var(--tester-color)";
        fileActionBadge.style.borderColor = "rgba(16, 185, 129, 0.3)";
    } else {
        fileActionBadge.innerText = selectedFileAction;
        fileActionBadge.style.background = "rgba(59, 130, 246, 0.15)";
        fileActionBadge.style.color = "var(--engineer-color)";
        fileActionBadge.style.borderColor = "rgba(59, 130, 246, 0.3)";
    }

    // Render code
    codeViewer.innerText = file.content;
    
    // Render diffs
    const history = logsTimeline.querySelectorAll(".log-item.engineer");
    let original = "";
    // Pull the original code from engineer events history payload
    // Search history for matching file path code event
    const engineerLogs = getHistoryLogs().filter(e => e.event_type === "code_written" && e.payload && e.payload.file_path === file.path);
    if (engineerLogs.length > 0) {
        const lastLog = engineerLogs[engineerLogs.length - 1];
        original = lastLog.payload.original_code || "";
        selectedFileAction = lastLog.payload.action || "CREATE";
        fileActionBadge.innerText = isTest ? "TEST SUITE" : (isPr ? "PR DOC" : selectedFileAction);
    }
    
    renderDiff(original, file.content);
}

// Line by Line Diffs calculation
function renderDiff(original, updated) {
    diffViewer.innerHTML = "";
    
    if (!original) {
        // Entirely new file
        const lines = updated.split("\n");
        lines.forEach(l => {
            const div = document.createElement("div");
            div.className = "diff-line addition";
            div.innerText = "+ " + l;
            diffViewer.appendChild(div);
        });
        return;
    }
    
    const origLines = original.split("\n");
    const updLines = updated.split("\n");
    
    let i = 0, j = 0;
    while (i < origLines.length || j < updLines.length) {
        if (i < origLines.length && j < updLines.length) {
            if (origLines[i] === updLines[j]) {
                const div = document.createElement("div");
                div.className = "diff-line context";
                div.innerText = "  " + origLines[i];
                diffViewer.appendChild(div);
                i++;
                j++;
            } else {
                // Renders modification as deletion + addition
                const delDiv = document.createElement("div");
                delDiv.className = "diff-line deletion";
                delDiv.innerText = "- " + origLines[i];
                diffViewer.appendChild(delDiv);
                i++;
                
                const addDiv = document.createElement("div");
                addDiv.className = "diff-line addition";
                addDiv.innerText = "+ " + updLines[j];
                diffViewer.appendChild(addDiv);
                j++;
            }
        } else if (i < origLines.length) {
            const div = document.createElement("div");
            div.className = "diff-line deletion";
            div.innerText = "- " + origLines[i];
            diffViewer.appendChild(div);
            i++;
        } else {
            const div = document.createElement("div");
            div.className = "diff-line addition";
            div.innerText = "+ " + updLines[j];
            diffViewer.appendChild(div);
            j++;
        }
    }
}

function toggleCodeView(viewType) {
    if (viewType === "code") {
        viewCodeBtn.classList.add("active");
        viewDiffBtn.classList.remove("active");
        document.getElementById("code-viewer-pre").classList.remove("hidden");
        diffViewer.classList.add("hidden");
    } else {
        viewCodeBtn.classList.remove("active");
        viewDiffBtn.classList.add("active");
        document.getElementById("code-viewer-pre").classList.add("hidden");
        diffViewer.classList.remove("hidden");
    }
}

// Retrieve History
let fetchedHistory = [];
async function fetchHistory() {
    try {
        const res = await fetch("/api/history");
        const history = await res.json();
        fetchedHistory = history;
        if (history.length > 0) {
            logsTimeline.innerHTML = "";
            history.forEach(addLogToTimeline);
            
            // Check if there's a PR generated in history
            const prLog = history.find(h => h.event_type === "pr_drafted");
            if (prLog) {
                renderPR(prLog.payload.pr_markdown);
            }
        }
    } catch (e) {
        console.error("Failed to fetch history:", e);
    }
}

function getHistoryLogs() {
    return fetchedHistory;
}

// Run Actions
async function handleRunOrchestration() {
    const request = promptInput.value.trim();
    if (!request) {
        alert("Please enter a feature request to start.");
        return;
    }
    
    const provider = providerSelect.value;
    const keys = getSavedKeys();
    const crossModel = crossModelCheck.checked;
    
    if (provider !== "simulation" && !keys.ANTHROPIC_API_KEY && !keys.OPENAI_API_KEY && !keys.GEMINI_API_KEY) {
        alert("Please click the 'Keys' button to add your API credentials before running real mode.");
        settingsModal.classList.remove("hidden");
        return;
    }
    
    // Set UI to running
    document.querySelector(".status-indicator").className = "status-indicator running";
    document.querySelector(".status-text").innerText = "AGENTS ACTIVE";
    
    logsTimeline.innerHTML = "";
    
    try {
        let endpoint = "/api/run-simulation";
        let body = {};
        
        if (provider === "simulation") {
            // Pick a scenario or default
            endpoint = "/api/run-simulation";
            body = { scenario: "lru_cache" };
        } else {
            endpoint = "/api/run-real";
            body = {
                request: request,
                provider: provider,
                keys: keys,
                cross_model_review: crossModel
            };
        }
        
        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const status = await res.json();
        console.log("Runner status:", status);
    } catch (e) {
        console.error("Failed to start run:", e);
        document.querySelector(".status-indicator").className = "status-indicator online";
        document.querySelector(".status-text").innerText = "RUN ERROR";
    }
}

async function triggerDemo(scenarioId) {
    promptInput.value = getDemoPrompt(scenarioId);
    providerSelect.value = "simulation";
    
    document.querySelector(".status-indicator").className = "status-indicator running";
    document.querySelector(".status-text").innerText = "AGENTS ACTIVE";
    
    logsTimeline.innerHTML = "";
    
    try {
        const res = await fetch("/api/run-simulation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario: scenarioId })
        });
        const status = await res.json();
        console.log("Demo started:", status);
    } catch (e) {
        console.error("Failed to trigger demo:", e);
    }
}

function getDemoPrompt(scenarioId) {
    if (scenarioId === "lru_cache") {
        return "Create a thread-safe LRU Cache in Python using collections.OrderedDict with capacity limit and O(1) lookups.";
    } else if (scenarioId === "jwt_auth") {
        return "Build a JWT authentication decorator in Python for routing functions that decodes tokens, verifies expiration, and injects user context.";
    } else if (scenarioId === "rate_limiter") {
        return "Implement an in-memory token bucket rate limiter in Python that allows requests under a burst threshold and refills dynamically over time.";
    }
    return "";
}

async function handleClearSystem() {
    if (!confirm("Are you sure you want to reset the message bus history and delete all sandbox files?")) {
        return;
    }
    try {
        const res = await fetch("/api/clear", { method: "POST" });
        await res.json();
        
        // Clear UI states
        logsTimeline.innerHTML = `
            <div class="timeline-empty">
                <i class="fa-solid fa-circle-nodes"></i>
                <p>Launch an orchestration run to monitor active agent communication events.</p>
            </div>
        `;
        fileTree.innerHTML = `<li class="empty-tree">No files written yet</li>`;
        codeViewer.innerText = "# Select a file from the explorer sidebar to view implemented source code.";
        activeFilename.innerHTML = `<i class="fa-regular fa-file-code"></i> select_a_file.py`;
        terminalBody.innerHTML = `<span class="term-prompt">C:\\workspace&gt;</span> <span class="term-text gray">Waiting for automated testing logs...</span>`;
        prMarkdownBody.innerHTML = `
            <div class="markdown-empty">
                <i class="fa-solid fa-code-pull-request"></i>
                <p>Pull Request release notes will display here once generated by the Documenter Agent.</p>
            </div>
        `;
        highlightActiveAgent(null);
        selectedFilePath = "";
        
        alert("System environment reset completed successfully.");
    } catch (e) {
        console.error("Failed to clear system:", e);
    }
}

function handleMergePr() {
    alert("Merging Branch! Pull request branch has been merged into main. Sandbox files pushed successfully.");
}

// RENDER PR MARKDOWN IN HTML
function renderPR(markdown) {
    prMarkdownBody.innerHTML = "";
    
    // Very basic regex-based markdown-to-HTML converter for styling PR descriptions cleanly
    let html = markdown
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n\s*-\s*(.*)/g, '\n<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/\n\n/g, '<br>');

    // Handle tables in markdown
    if (html.includes("|")) {
        const lines = html.split("<br>");
        let inTable = false;
        let tableHTML = "<table>";
        let newLines = [];
        
        lines.forEach(line => {
            if (line.includes("|")) {
                const cols = line.split("|").map(c => c.trim()).filter(c => c !== "");
                if (cols.length > 0) {
                    if (line.includes("---")) {
                        // Skip table separator line
                        return;
                    }
                    if (!inTable) {
                        inTable = true;
                        tableHTML += "<thead><tr>" + cols.map(c => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
                    } else {
                        tableHTML += "<tr>" + cols.map(c => `<td>${c}</td>`).join("") + "</tr>";
                    }
                }
            } else {
                if (inTable) {
                    inTable = false;
                    tableHTML += "</tbody></table>";
                    newLines.push(tableHTML);
                    tableHTML = "<table>";
                }
                newLines.push(line);
            }
        });
        if (inTable) {
            tableHTML += "</tbody></table>";
            newLines.push(tableHTML);
        }
        html = newLines.join("<br>");
    }

    prMarkdownBody.innerHTML = html;
    
    // Extract title if possible
    const match = markdown.match(/^# PR:\s*(.*)/i) || markdown.match(/^#\s*(.*)/);
    if (match) {
        prHeadlineTitle.innerText = match[1];
    } else {
        prHeadlineTitle.innerText = "Pull Request Draft Summary";
    }
}

// Helpers
function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
