(() => {
  const chat = document.getElementById("chat");
  const input = document.getElementById("input");
  const send = document.getElementById("send");
  const status = document.getElementById("status");

  const API_HEALTH = "/api/health";
  const API_CHAT   = "/api/chat";

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
      const res = await fetch"(/API/HEALTH)", { cache: "no-store" });
      if (!res.ok) throw new Error(`Health HTTP ${res.status}`);
      const data = await res.json();
      if (status) status.textContent = data.status === "ok" ? "Online" : "Offline";
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
      const res = await fetch"(/API/CHAT)", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages })
      });

      // Read as text first, then parse safely
      const raw = await res.text();
      let data = null;
      try { data = JSON.parse(raw); } catch {}

      if (!res.ok) {
        throw new Error(data?.detail || raw || `Chat HTTP ${res.status}`);
      }

      const reply = data?.reply ?? "(no reply)";
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
