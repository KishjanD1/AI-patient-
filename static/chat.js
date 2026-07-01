let patientId = sessionStorage.getItem("patientId");

window.onload = function() {
    if (!patientId) {
        document.getElementById("login-overlay").style.display = "flex";
        document.getElementById("app-layout").style.display = "none";
    } else {
        document.getElementById("login-overlay").style.display = "none";
        document.getElementById("app-layout").style.display = "flex";
        pollObservability();
    }
};

function handleLogin() {
    const inputId = document.getElementById("login-id").value.trim();
    if (!inputId) return;
    patientId = inputId;
    sessionStorage.setItem("patientId", patientId);
    
    document.getElementById("login-overlay").style.display = "none";
    document.getElementById("app-layout").style.display = "flex";
    
    pollObservability();
}

function logout() {
    sessionStorage.removeItem("patientId");
    window.location.reload();
}
const input = document.getElementById("message-input");
const messagesDiv = document.getElementById("chat-messages");

input.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

function appendMessage(text, sender) {
    const div = document.createElement("div");
    div.className = `message ${sender}`;
    div.innerText = text;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

let typingIndicator = null;

function showTypingIndicator() {
    typingIndicator = document.createElement("div");
    typingIndicator.className = "typing-indicator";
    typingIndicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    messagesDiv.appendChild(typingIndicator);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function removeTypingIndicator() {
    if (typingIndicator && typingIndicator.parentNode === messagesDiv) {
        messagesDiv.removeChild(typingIndicator);
        typingIndicator = null;
    }
}

async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    
    appendMessage(text, "user");
    input.value = "";
    
    showTypingIndicator();
    
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ patient_id: patientId, message: text })
        });
        const data = await response.json();
        
        removeTypingIndicator();
        
        if (response.ok) {
            appendMessage(data.reply, "bot");
        } else {
            appendMessage(`Error: ${JSON.stringify(data.detail)}`, "bot");
        }
    } catch (e) {
        removeTypingIndicator();
        appendMessage("Network error. Please try again.", "bot");
    }
}

// Realtime Observability Polling
async function pollObservability() {
    if (!patientId) return;
    try {
        const logRes = await fetch(`/api/logs?patient_id=${encodeURIComponent(patientId)}`);
        if (logRes.ok) {
            const logData = await logRes.json();
            const logOutput = document.getElementById("log-output");
            if (logOutput && logData.logs !== logOutput.innerText) {
                logOutput.innerText = logData.logs;
                logOutput.scrollTop = logOutput.scrollHeight;
            }
        }
        
        const dbRes = await fetch(`/api/db_state?patient_id=${encodeURIComponent(patientId)}`);
        if (dbRes.ok) {
            const dbData = await dbRes.json();
            const dbOutput = document.getElementById("db-output");
            if (dbOutput) {
                dbOutput.innerText = JSON.stringify(dbData, null, 2);
            }
        }
    } catch (e) {
        // ignore polling errors
    }
}

setInterval(pollObservability, 2000);
