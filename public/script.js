(() => {
  const chat = document.getElementById("chat");
  const input = document.getElementById("input");
  const send = document.getElementById("send");
  const status = document.getElementById("status");

  if (!chat || !input || !send) {
    console.error("Missing required DOM nodes", { chat, input, send });
    return;
  }

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
      const r = await fetch("/api/health");
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
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages })
      });

      const raw = await r.text();
      let data;
      try { data = JSON.parse(raw); } catch { data = null; }

      if (!r.ok) {
        const detail = data?.detail || raw || "Request failed";
        throw new Error(detail);
      }

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

  // Events
  send.addEventListener("click", sendMsg);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMsg();
  });

  // Make sure input is actually usable
  input.disabled = false;
  input.readOnly = false;
  input.tabIndex = 0;

  health();
  bubble("assistant", "Hi — I’m Mr. Botonic. Ask me something.");
})();
