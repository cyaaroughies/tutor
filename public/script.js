(() => {
  const chat = document.getElementById("chat");
  const input = document.getElementById("input");
  const send = document.getElementById("send");
  const status = document.getElementById("status");

  const API_HEALTH = "/api/health";
  const API_CHAT = "/api/chat";

  const messages = [
    { role: "system", content: "You are Mr. Botonic, a helpful tutor. Keep answers clear and structured." }
  ];

  function bubble(role, text) {
    const d = document.createElement("div");
    d.className = `bubble ${role}`;
    d.textContent = text;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
  }

  async function health() {
    try {
      const r = await fetch(API_HEALTH, { cache: "no-store" });
      const j = await r.json();
      if (status) status.textContent = j.status === "ok" ? "Online" : "Offline";
    } catch {
      if (status) status.textContent = "Offline";
    }
  }

  async function sendMsg() {
    const text = (input.value || "").trim();
    if (!text) return;

    input.value = "";
    input.focus();

    bubble("user", text);
    messages.push({ role: "user", content: text });

    send.disabled = true;

    try {
      const r = await fetch(API_CHAT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages })
      });

      const raw = await r.text();
      let data;
      try { data = JSON.parse(raw); } catch { data = null; }

      if (!r.ok) throw new Error(data?.detail || raw || "Request failed");

      const reply = data?.reply || "(no reply)";
      bubble("assistant", reply);
      messages.push({ role: "assistant", content: reply });
    } catch (e) {
      bubble("assistant", `Error: ${e.message}`);
    } finally {
      send.disabled = false;
      input.focus();
    }
  }

  send.addEventListener("click", sendMsg);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMsg();
  });

  health();
  bubble("assistant", "Hi — I’m Mr. Botonic. Ask me something.");
})();
