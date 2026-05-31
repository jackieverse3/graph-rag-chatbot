const  BACKEND_API = "http://127.0.0.1:8000";

// Element Selectors
const buildBtn = document.getElementById("build-btn");
const buildStatus = document.getElementById("build-status");
const askBtn = document.getElementById("ask-btn");
const clearBtn = document.getElementById("clear-btn"); // Expansion Selector
const questionInput= document.getElementById("question-input");
const nodeCountEl = document.getElementById("node-count");
const relCountEl = document.getElementById("rel-count");
const refreshStatsBtn = document.getElementById("refresh-stats-btn");
const traceLogEl = document.getElementById("trace-log");
const historyContainer = document.getElementById("history-container");

const loadingIndicator = document.getElementById("loading");
const resultsArea = document.getElementById("results-area");
const answerText = document.getElementById("answer-text");
const contextText = document.getElementById("context-text");
const copyBtn = document.getElementById("copy-btn");
const visualContextList = document.getElementById("latency-badge");
const latencyBadge = document.getElementById("latency-badge");
// Expansion Selector

const corpusToggle = document.getElementById("corpus-toggle");
const corpusContentWrapper = document.getElementById("corpus-content-wrapper");
const corpusArrow = document.getElementById("corpus-arrow");

// Helper to escape HTML characters
function excapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g,"&#039;")
}

// 1.Trace Logger Console system
function addTrace(message, type="system") {
    const time = new Date().toLocaleDateString([], {hour: '2-digit',minute:'2-digit',
        second:'2-digit'
    });
    const line = document.createElement("div");
    line.className = `log-line ${type}`;
    line.innerHTML = `<span>[${time}] ${escapeHtml(message)}</span>`;
    traceLogEl.appendChild(line);
    traceLogEl.scrollTop = traceLogEl.scrollHeight;
}

// 2. Query execution metrics from Neo4j
async function updateDatabaseStats() {
    addTrace("Quering database node & relationship metrics ...", "system");
    try {
        const response = await fetch(`${BACKEND_API}/stats`);
        const data = await response.json();

        if(response.ok){
            nodeCountEl.textContent= data.nodes;
            relCountEl.textContent = data.relationships;
            addTrace(`Stats updated successfully. Active nodes:${data.nodes}, Active relationships:
                ${data.relationships}`,"database");
            } else {
                addTrace(`Stats fetch failed: ${data.error||"Unknown server error"}`,"error");

            }
        } catch (err) {
            addTrace("Stats network error. Verify backend port connection status.", "error");
        }
    }

    // 3. Grounded Answer Typewriter Effect
    async function Typewriter(element, text, speed = 12) {
        element.textContent = "";
        for (let i = 0; i < text.length ; i++) {
            element.textContent += text.charAt(i);
            await new Promise(resolve => setTimeout(resolve,speed));
        }
    }

    // 4. Visual context triples mapper
    function renderVisualContext(rawContext){
        visualContextList.innerHTML= "";

        // Clean and split lines of raw context
        const lines = rawContext.split ("\n")
        .map(line => line.trim())
        .filter(line=>line !== "");

        if(lines.length ==0 || 
            rawContext.toLowerCase().includes("no facts")) {
                visualContextList.innerHTML = `<div class="empty-context">
                No overlapping paths found in Neo4j for this query target.</div>`;
                return;
            }

            addTrace(`Parsing and visualizing ${lines.length} relational
                triples... `, "info");

                lines.forEach(line => {
                    // Find the UPPERCASE relationship identifier (e.g., FOUNDED, DEVELOPED)

                    const match = line.match(/\s([A-Z_]{2,})\s/);

                    if (match) {
                        const relation = match[1];
                        const index = line.indexOf(relation);
                        const source = line.("substring(0,index).trim();
                        const target  = line.substring(index + relation.length).trim();

                        const card = document.createElement("div");
                        card.className = "triple-card";
                        card.innerHTML= `
                        <span class="node source" title="${escapeHtml(source)}">${escapeHtml(source)}</span>
                        <span class = "edge-line">
                        <span class = "edge-label">${escapeHtml(relation)}</span>
                        </span>
                        <span class = "node target" 
                        title = "${escapeHtml(target)}">${escapeHtml(target)}</span>`;
                        visualContextList.appendChild(card);
                    } else {
                        const fallbackCard = document.createElement("div");
                        fallbackCard.className="empty-context";
                        fallbackCard.textContent= line;
                        visualContextList.appendChild(fallbackCard);
                    }
                    }
                );}
// 5. Suggestion & Search Bookmarks History Manager
const STORAGE_KEY = "graph-rag_bookmarks";
const MAX_BOOKMARKS = 5;

function getBookmarks () {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY))  || [];
    } catch {
        return [];
    }
    }
}

function saveBookmark(question) {
    let bookmarks = getBookmarks();

    bookmarks = bookmarks.filter(q=> q.toLowerCase() !== question.toLowerCase());
    bookmarks.unshift(question);

    if(bookmarks.length > MAX_BOOKMARKS) {
        bookmarks.pop();
    }
    localStorage.setItem(STORAGE_KEY,JSON.stringify(bookmarks));
    renderBookmarks();
}
function renderBookmarks() {
    historyContainer.innerHTML = "";
    const bookmarks = getBookmarks();
    
    if (bookmarks.length === 0) {
        historyContainer.classList.add("hidden");
        return;
    }
    
    historyContainer.classList.remove("hidden");
    bookmarks.forEach(question => {
        const pill = document.createElement("button");
        pill.className = "history-pill";
        pill.textContent = question;
        pill.addEventListener("click", () => {
            questionInput.value = question;
            addTrace(`Selected bookmark: "${question}"`, "info");
            handleQuery();
        });
        historyContainer.appendChild(pill);
    });
}

// 6. Action: Execute Document parsing sequence
buildBtn.addEventListener("click", async () => {
    addTrace("Initiating graph builder task from sample text file...", "info");
    buildStatus.textContent = "Asking LLM to extract entities and relations. Please wait...";
    buildStatus.className = "status-msg"; 
    buildStatus.classList.remove("hidden");
    buildBtn.disabled = true;

    try {
        const response = await fetch(`${BACKEND_API}/build-graph`, {
            method: "POST"
        });
        const data = await response.json();

        if (response.ok) {
            buildStatus.textContent = data.message;
            buildStatus.className = "status-msg success";
            addTrace("Extraction complete. Graph constructed and written inside Neo4j database.", "database");
            await updateDatabaseStats();
        } else {
            buildStatus.textContent = `Error: ${data.detail || "Database process execution failed."}`;
            buildStatus.className = "status-msg error";
            addTrace(`Graph construction failed: ${data.detail || "Server error"}`, "error");
        }
    } catch (err) {
        console.error(err);
        buildStatus.textContent = "Network error. Make sure your Python server is running.";
        buildStatus.className = "status-msg error";
        addTrace("Network communication error during builder command execution.", "error");
    } finally {
        buildBtn.disabled = false;
    }
});

// 7. Action: Execute query execution tasks
async function handleQuery() {
    const question = questionInput.value.trim();
    if (!question) {
        alert("Please enter a question first.");
        return;
    }

    addTrace(`Executing User Query: "${question}"`, "info");
    askBtn.disabled = true;
    clearBtn.disabled = true;
    loadingIndicator.classList.remove("hidden");
    resultsArea.classList.add("hidden");
    latencyBadge.classList.add("hidden");

    // EXPANSION: Start performance timer
    const startTime = performance.now();

    try {
        addTrace("Step 1: Extracting entity nodes from query syntax...", "info");
        const response = await fetch(`${BACKEND_API}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ question: question })
        });
        const data = await response.json();

        if (response.ok) {
            // EXPANSION: End performance timer and compute latency in seconds
            const endTime = performance.now();
            const latencySeconds = ((endTime - startTime) / 1000).toFixed(2);
            latencyBadge.textContent = `Latency: ${latencySeconds}s`;
            latencyBadge.classList.remove("hidden");

            addTrace("Step 2: Path-matching entities and pulling facts from Neo4j...", "database");
            addTrace(`Step 3: Grounded answer generated in ${latencySeconds} seconds.`, "info");
            
            // Build the dynamic layouts
            contextText.textContent = data.context;
            renderVisualContext(data.context);
            
            // Unveil results wrapper
            resultsArea.classList.remove("hidden");
            
            // Run typing visualizer for output grounded answer
            await typeWriter(answerText, data.answer, 10);
            
            // Save bookmark history on success
            saveBookmark(question);
            addTrace("Grounded response processed and displayed.", "system");
        } else {
            addTrace(`Execution failed: ${data.detail || "Processing error"}`, "error");
            alert(`Error: ${data.detail || "Query execution failed."}`);
        }
    } catch (err) {
        console.error(err);
        addTrace("Failed to complete query. Ensure web API is reachable.", "error");
        alert("Network error occurred. Ensure the FastAPI application backend is online.");
    } finally {
        askBtn.disabled = false;
        clearBtn.disabled = false;
        loadingIndicator.classList.add("hidden");
    }
}

// 8. Copy to Clipboard Utility
copyBtn.addEventListener("click", () => {
    const answer = answerText.textContent;
    if (!answer) return;
    
    navigator.clipboard.writeText(answer)
        .then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = "Copied!";
            copyBtn.classList.add("btn-primary");
            copyBtn.classList.remove("btn-secondary");
            
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.classList.add("btn-secondary");
                copyBtn.classList.remove("btn-primary");
            }, 1500);
            addTrace("Response copied to system clipboard.", "system");
        })
        .catch(err => {
            console.error("Clipboard copy failed", err);
        });
});

// EXPANSION: 9. Active Source Text accordion toggle logic
corpusToggle.addEventListener("click", () => {
    const isCollapsed = corpusContentWrapper.classList.toggle("collapsed");
    corpusArrow.classList.toggle("collapsed", isCollapsed);
    addTrace(`Source corpus view ${isCollapsed ? 'collapsed' : 'expanded'}.`, "system");
});

// Expansion 10. Clear UI Sandbox canvas logic.
clearBtn.addEventListener("click", () => {
    questionInput.value="";
    resultsArea.classList.add("hidden");
    latencyBadge.classList.add("hidden");
    answerText.textContent="";
    contextText.textContent="";
    visualContextList.innerHTML="";
    addTrace("Workspace cleared. Terminal canvas reset.","system");

});
refreshStatsBtn.addEventListener("click",updateDatabaseStats);

//Bootstrap initialization on windor trigger
window.addEventListener("DOMContentLoaded", ()=> {
    updateDatabaseStats();
    renderBookmarks();
})
