fetch("/api/create-checkout-session", ...)

const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const statusEl = document.getElementById("status");

const messages = [
  { role: "system", content: "You are Mr. Botonic, a helpful tutor. Keep answers clear and structured." }
];

function addBubble(role, text) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function healthCheck() {
  try {
    const r = await fetch("/api/health");
    const j = await r.json();
    statusEl.textContent = j.status === "ok" ? "Online" : "Degraded";
  } catch {
    statusEl.textContent = "Offline";
  }
}

async function send() {
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = "";
  addBubble("user", text);
  messages.push({ role: "user", content: text });

  sendBtn.disabled = true;

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages })
    });

    const data = await r.json();
    if (!r.ok) throw new Error(data?.detail || "Request failed");

    addBubble("assistant", data.reply || "(no reply)");
    messages.push({ role: "assistant", content: data.reply || "" });
  } catch (e) {
    addBubble("assistant", `Error: ${e.message}`);
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

sendBtn.addEventListener("click", send);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});

healthCheck();
addBubble("assistant", "Hey — I’m Mr. Botonic. Ask me something and I’ll help you crush it.");
