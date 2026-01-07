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
    const r = await fetch("/health", { cache: "no-store" });
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
    const r = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages })
    });

    const raw = await r.text();               // <- don’t assume JSON
    let data = {};
    try { data = JSON.parse(raw || "{}"); } catch {}

    if (!r.ok) {
      const detail = data.detail || raw || `HTTP ${r.status}`;
      throw new Error(detail);
    }

    const reply = data.reply || "(no reply)";
    addBubble("assistant", reply);
    messages.push({ role: "assistant", content: reply });
  } catch (e) {
    addBubble("assistant", `Error: ${e.message || e}`);
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
