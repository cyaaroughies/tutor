const chat = document.getElementById("chat");
const input = document.getElementById("input");
const send = document.getElementById("send");
const status = document.getElementById("status");

const messages = [
  { role: "system", content: "You are Mr. Botonic, a helpful tutor." }
];

function bubble(role, text) {
  const d = document.createElement("div");
  d.className = "bubble " + role;
  d.textContent = text;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}

async function health() {
  try {
    const r = await fetch("/api/health");
    const j = await r.json();
    status.textContent = j.status === "ok" ? "Online" : "Offline";
  } catch {
    status.textContent = "Offline";
  }
}

async function sendMsg() {
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  bubble("user", text);
  messages.push({ role: "user", content: text });

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages })
    });

    const j = await r.json();
    if (!r.ok) throw new Error(j.detail);

    bubble("assistant", j.reply);
    messages.push({ role: "assistant", content: j.reply });
  } catch (e) {
    bubble("assistant", "Error: " + e.message);
  }
}

send.onclick = sendMsg;
input.onkeydown = e => e.key === "Enter" && sendMsg();

health();
bubble("assistant", "Hi, I’m Mr. Botonic. What do you want to learn?");
