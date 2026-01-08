# -*- coding: utf-8 -*-
import os
import datetime
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

# ---------- OpenAI (safe) ----------
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore

# ---------- Stripe (safe) ----------
try:
    import stripe  # type: ignore
except Exception:
    stripe = None  # type: ignore


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
IMG_PATH = BASE_DIR / "dr-botonic.png"

DAILY_LIMIT = int(os.getenv("BOTNOLOGY_DAILY_LIMIT", "20"))
daily_usage = defaultdict(int)


def today_str() -> str:
    return datetime.date.today().isoformat()


def client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def get_app_base(request: Optional[Request] = None) -> str:
    """
    Prefer APP_BASE_URL env (your Vercel setting). Fall back to request base url.
    """
    env_base = (os.getenv("APP_BASE_URL") or "").strip().rstrip("/")
    if env_base:
        return env_base
    if request is not None:
        # request.base_url includes trailing slash
        return str(request.base_url).rstrip("/")
    return "http://localhost:8000"


def stripe_ready() -> bool:
    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    return bool(stripe) and bool(key)


def stripe_price_map() -> Dict[str, str]:
    """
    Matches your Vercel env var names EXACTLY.
    """
    return {
        "pro": (os.getenv("STRIPE_PRICE_PRO") or "").strip(),
        "semi_pro": (os.getenv("STRIPE_PRICE_SEMI_PRO") or "").strip(),
        "yearly_pro": (os.getenv("STRIPE_PRICE_YEARLY_PRO") or "").strip(),
    }


def openai_client() -> Optional[Any]:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)


def page_shell(title: str, active: str, body_html: str, extra_head: str = "", extra_script: str = "") -> str:
    """
    active: "home" | "curriculum" | "pricing" | "dashboard"
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg0: #020708;
      --bg1: #04110b;
      --panel: rgba(5, 10, 8, 0.84);
      --gold: #c9a24a;
      --muted: rgba(231, 228, 218, 0.68);
      --text: #e7e4da;
      --border: rgba(201, 162, 74, 0.20);
      --success: #22c55e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; color: var(--text);
      font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif;
      background:
        radial-gradient(circle at 22% 20%, rgba(18, 69, 38, 0.45) 0, rgba(2, 7, 8, 0.92) 52%, #000 100%),
        radial-gradient(circle at 80% 25%, rgba(201, 162, 74, 0.10) 0, rgba(0,0,0,0) 50%),
        linear-gradient(140deg, var(--bg1), var(--bg0));
    }}
    .page {{ max-width: 1180px; margin: 0 auto; padding: 22px 14px 40px; }}
    .serif {{ font-family: Cinzel, Georgia, serif; letter-spacing: .06em; text-transform: uppercase; }}

    .nav {{
      display:flex; align-items:center; justify-content:space-between; gap:14px;
      padding: 10px 12px; border: 1px solid rgba(201,162,74,0.16);
      border-radius: 16px; background: linear-gradient(180deg, rgba(5,10,8,0.92), rgba(3,6,5,0.86));
      box-shadow: 0 20px 60px rgba(0,0,0,0.6); margin-bottom: 22px;
    }}
    .brand {{ display:flex; align-items:center; gap:12px; min-width: 240px; }}
    .crest {{
      width: 40px; height: 40px; border-radius: 999px;
      border: 1px solid rgba(201,162,74,0.35);
      display:flex; align-items:center; justify-content:center;
      color: var(--gold); background: rgba(3,6,5,0.9);
      box-shadow: 0 18px 40px rgba(0,0,0,0.7);
    }}
    .brand-title {{ font-size: 1.05rem; color: var(--gold); margin: 0; line-height: 1.0; }}
    .brand-sub {{ font-size: .78rem; color: var(--muted); margin-top: 3px; }}
    .nav-links {{ display:flex; gap: 16px; align-items:center; flex-wrap: wrap; justify-content: flex-end; }}
    .nav-links a {{
      color: var(--muted); text-decoration: none; font-size: .88rem;
      padding: 6px 8px; border-radius: 10px; border: 1px solid transparent;
    }}
    .nav-links a.active {{ color: var(--gold); border-color: rgba(201,162,74,0.25); background: rgba(201,162,74,0.06); }}
    .nav-links a:hover {{ color: var(--text); border-color: rgba(201,162,74,0.18); }}

    .btn {{
      border: 1px solid rgba(201,162,74,0.28);
      background: rgba(4, 7, 6, 0.90);
      color: var(--gold); padding: 8px 14px; border-radius: 999px;
      cursor: pointer; font-size: .88rem; text-decoration: none;
      display:inline-flex; align-items:center; gap: 8px;
    }}
    .btn-primary {{
      border: 1px solid rgba(201,162,74,0.40);
      background: linear-gradient(135deg, rgba(201,162,74,0.18), rgba(22,101,52,0.18));
      color: var(--gold); font-weight: 600; box-shadow: 0 14px 42px rgba(0,0,0,0.65);
    }}

    .grid-2 {{ display:grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.95fr); gap: 18px; }}
    .panel {{
      border: 1px solid rgba(201,162,74,0.22);
      border-radius: 20px;
      background: linear-gradient(180deg, rgba(6,10,8,0.82), rgba(2,6,5,0.90));
      box-shadow: 0 26px 80px rgba(0,0,0,0.68);
      overflow: hidden;
    }}
    .panel-inner {{ padding: 16px 16px 14px; }}

    .eyebrow {{
      display:inline-flex; gap: 10px; align-items:center; color: var(--muted);
      font-size: .84rem; padding: 7px 12px; border: 1px solid rgba(201,162,74,0.18);
      border-radius: 999px; background: rgba(3,6,5,0.65); margin-bottom: 14px;
    }}
    .dot {{
      width: 8px; height: 8px; border-radius: 999px;
      background: var(--success); box-shadow: 0 0 0 3px rgba(34,197,94,0.12);
    }}

    h1.hero {{ margin: 0 0 10px; font-size: clamp(2.1rem, 3.2vw, 3.0rem); line-height: 1.08; color: var(--gold); }}
    p.lead {{ margin: 0 0 14px; color: var(--muted); font-size: 1.0rem; line-height: 1.65; max-width: 52ch; }}

    .dr-card {{ display:grid; grid-template-columns: 90px minmax(0, 1fr); gap: 14px; align-items:center; padding: 14px 14px; }}
    .dr-avatar {{
      width: 86px; height: 86px; border-radius: 999px;
      border: 1px solid rgba(201,162,74,0.28);
      background-image: url("/dr-botonic.png");
      background-size: cover; background-position: center;
      box-shadow: 0 18px 44px rgba(0,0,0,0.8);
    }}

    .section-title {{ color: var(--gold); margin: 0 0 8px; font-size: 1.1rem; }}
    .section-sub {{ color: var(--muted); margin: 0 0 14px; line-height: 1.6; }}

    @media (max-width: 980px) {{
      .grid-2 {{ grid-template-columns: minmax(0, 1fr); }}
      .brand {{ min-width: unset; }}
    }}

    {extra_head}
  </style>
</head>
<body>
  <div class="page">
    <header class="nav">
      <div class="brand">
        <div class="crest serif">B</div>
        <div>
          <div class="brand-title serif">Botnology 101</div>
          <div class="brand-sub">Dr. Botonic • AI Learning Academy</div>
        </div>
      </div>

      <nav class="nav-links">
        <a href="/" class="{ 'active' if active=='home' else '' }">Home</a>
        <a href="/curriculum" class="{ 'active' if active=='curriculum' else '' }">Curriculum</a>
        <a href="/pricing" class="{ 'active' if active=='pricing' else '' }">Tuition</a>
        <a href="/dashboard" class="{ 'active' if active=='dashboard' else '' }">Dashboard</a>
        <button class="btn btn-primary" type="button" onclick="window.__scrollToTutor && window.__scrollToTutor();">Launch tutor</button>
      </nav>
    </header>

    {body_html}
  </div>

  <script>
    window.__scrollToTutor = function() {{
      var el = document.getElementById("tutor");
      if (el) el.scrollIntoView({{ behavior: "smooth", block: "center" }});
      var inp = document.getElementById("chat-input");
      if (inp) inp.focus();
    }};
    {extra_script}
  </script>
</body>
</html>
"""


# ----------------------------
# Debug + Health (support both / and /api/)
# ----------------------------
@app.get("/stripe-debug")
@app.get("/api/stripe-debug")
def stripe_debug():
    pm = stripe_price_map()
    return {
        "stripe_imported": bool(stripe),
        "has_secret": bool((os.getenv("STRIPE_SECRET_KEY") or "").strip()),
        "pro": pm.get("pro", ""),
        "semi_pro": pm.get("semi_pro", ""),
        "yearly_pro": pm.get("yearly_pro", ""),
        "app_base_url": (os.getenv("APP_BASE_URL") or "").strip(),
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "openai_configured": bool((os.getenv("OPENAI_API_KEY") or "").strip()),
        "stripe_configured": stripe_ready(),
    }


# ----------------------------
# Asset
# ----------------------------
@app.get("/dr-botonic.png")
async def dr_image():
    if IMG_PATH.exists():
        return FileResponse(str(IMG_PATH))
    raise HTTPException(status_code=404, detail="dr-botonic.png not found (place it at project root).")


# ----------------------------
# Chat (simple)
# Accepts:
#   { "message": "...", "subject": "...", "history":[{role,content}] }
# ----------------------------
@app.post("/chat")
@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    text = str(data.get("message", "")).strip()
    subject = str(data.get("subject", "General Study")).strip() or "General Study"
    history = data.get("history", [])

    if not text:
        raise HTTPException(status_code=400, detail="Message is required")

    # Daily limit per client host (basic)
    cid = client_id(request)
    key = (cid, today_str())
    if daily_usage[key] >= DAILY_LIMIT:
        return {"reply": "You’ve reached today’s preview limit. Tuition plans unlock unlimited sessions."}
    daily_usage[key] += 1

    c = openai_client()
    if not c:
        return {"reply": f"Demo mode (OPENAI_API_KEY missing). You asked: “{text}”"}

    subj = subject.lower()
    focus = "You are a calm, professor-level academic tutor."
    if any(k in subj for k in ["anatomy", "nursing", "medical", "musculoskeletal", "neuro"]):
        focus = "You are a highly competent anatomy/nursing tutor. Be clinically correct and explain structure–function clearly."

    messages = [{"role": "system", "content": f"You are Dr. Botonic. Subject: {subject}. {focus} Explain step-by-step."}]

    if isinstance(history, list):
        for t in history:
            role = t.get("role")
            content = t.get("content")
            if role in ("user", "assistant") and isinstance(content, str):
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": text})

    try:
        resp = c.chat.completions.create(
            model=(os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip(),
            messages=messages,
            max_tokens=450,
            temperature=0.6,
        )
        reply = (resp.choices[0].message.content or "").strip()
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ----------------------------
# Stripe checkout
# Plans: pro | semi_pro | yearly_pro
# ----------------------------
@app.post("/create-checkout-session")
@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request):
    if not stripe_ready():
        raise HTTPException(status_code=500, detail="Stripe is not configured (missing stripe lib or STRIPE_SECRET_KEY).")

    try:
        data = await request.json()
    except Exception:
        data = {}

    plan = (data.get("plan") or "").strip().lower()
    pm = stripe_price_map()

    if plan not in pm or not pm[plan] or not pm[plan].startswith("price_"):
        raise HTTPException(status_code=400, detail="Invalid plan or missing Stripe price ID for this plan.")

    stripe.api_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    base = get_app_base(request)

    try:
       session = stripe.checkout.Session.create(
    mode="subscription",
    line_items=[{"price": pm[plan], "quantity": 1}],
    success_url=f"{base}/dashboard.html?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
    cancel_url=f"{base}/pricing.html?checkout=cancel",
)
return {"url": session.url}

        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------
# Pages
# ----------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    body = """
    <main class="grid-2">
      <section class="panel">
        <div class="panel-inner">
          <div class="eyebrow"><span class="dot"></span> Private AI tutoring • Available 24/7</div>
          <h1 class="hero serif">BOTNOLOGY 101<br/>DR. BOTONIC</h1>
          <p class="lead">
            Professor-level tutoring with a premium, student-safe experience. Pick a subject and get step-by-step clarity.
          </p>
          <div style="display:flex; gap:10px; flex-wrap:wrap; margin: 14px 0 8px;">
            <button class="btn btn-primary" type="button" onclick="window.__scrollToTutor()">Start a trial session</button>
            <a class="btn" href="/pricing">View tuition</a>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="dr-card">
          <div class="dr-avatar"></div>
          <div>
            <div class="section-title serif" style="margin:0;">Dr. Botonic</div>
            <div class="section-sub" style="margin:6px 0 0;">Ask clearly. Think slowly. Leave smarter than you arrived.</div>
          </div>
        </div>

        <div class="panel-inner" id="tutor">
          <div class="section-title serif" style="margin:0 0 8px;">Tutor Console</div>
          <div class="section-sub" style="margin:0 0 10px;">Type a question and Dr. Botonic will walk you through it.</div>

          <div id="chat-messages" style="border:1px solid rgba(201,162,74,0.16); background:rgba(2,6,5,0.75); border-radius:16px; padding:12px; height:320px; overflow:auto;"></div>

          <div style="display:flex; gap:10px; margin-top:10px;">
            <input id="chat-input" style="flex:1; border-radius:999px; border:1px solid rgba(201,162,74,0.20); background:rgba(2,6,5,0.82); color:var(--text); padding:10px 12px; outline:none;" placeholder="Ask your first question..." />
            <button class="btn btn-primary" id="chat-send" type="button">Send</button>
          </div>

          <div style="color:var(--muted); font-size:.80rem; margin-top:8px;">
            Preview limit: {DAILY_LIMIT} questions/day per network/device.
          </div>
        </div>
      </section>
    </main>
    """

    script = r"""
      let history = [];

      function append(sender, text, who){
        const box = document.getElementById("chat-messages");
        if(!box) return;
        const row = document.createElement("div");
        row.style.marginBottom = "10px";
        row.style.textAlign = (who==="me") ? "right" : "left";
        const b = document.createElement("div");
        b.style.display = "inline-block";
        b.style.borderRadius = "14px";
        b.style.padding = "9px 11px";
        b.style.border = "1px solid rgba(201,162,74,0.14)";
        b.style.background = (who==="me") ? "rgba(30,64,175,0.55)" : "rgba(22,101,52,0.45)";
        const s = document.createElement("div");
        s.style.fontSize = ".72rem";
        s.style.opacity = ".78";
        s.textContent = sender;
        const c = document.createElement("div");
        c.textContent = text;
        b.appendChild(s); b.appendChild(c);
        row.appendChild(b);
        box.appendChild(row);
        box.scrollTop = box.scrollHeight;
      }

      async function send(){
        const input = document.getElementById("chat-input");
        const btn = document.getElementById("chat-send");
        const text = (input.value||"").trim();
        if(!text) return;

        append("You", text, "me");
        history.push({role:"user", content:text});
        input.value = "";
        btn.disabled = true;

        try{
          // Use /api/chat to match Vercel routing
          const res = await fetch("/api/chat", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({message:text, subject:"General Study", history})
          });
          const data = await res.json().catch(()=>({}));
          if(!res.ok){
            append("Dr. Botonic", "Error: " + (data.detail || "Request failed"), "bot");
          } else {
            const reply = data.reply || "No reply received.";
            append("Dr. Botonic", reply, "bot");
            history.push({role:"assistant", content:reply});
          }
        } catch(e){
          append("Dr. Botonic", "Network error talking to the tutor engine.", "bot");
        }
        btn.disabled = false;
        input.focus();
      }

      const btn = document.getElementById("chat-send");
      const inp = document.getElementById("chat-input");
      if(btn) btn.addEventListener("click", send);
      if(inp) inp.addEventListener("keydown", (e)=>{ if(e.key==="Enter"){ e.preventDefault(); send(); }});
    """
    return page_shell("Botnology 101 • Dr. Botonic", "home", body, extra_script=script)


@app.get("/curriculum", response_class=HTMLResponse)
async def curriculum():
    body = """
    <section class="panel">
      <div class="panel-inner">
        <div class="section-title serif">Curriculum</div>
        <div class="section-sub">
          Keep it clean and expandable. Add modules as you build.
        </div>
        <div style="display:grid; gap:12px;">
          <div style="border:1px solid rgba(201,162,74,0.18); background:rgba(2,6,5,0.68); border-radius:16px; padding:14px;">
            <strong style="color:var(--gold);">Anatomy Foundations</strong>
            <div style="color:var(--muted); margin-top:6px; line-height:1.6;">Planes, terms, tissue types, and the “how to study anatomy” method.</div>
          </div>
          <div style="border:1px solid rgba(201,162,74,0.18); background:rgba(2,6,5,0.68); border-radius:16px; padding:14px;">
            <strong style="color:var(--gold);">Musculoskeletal</strong>
            <div style="color:var(--muted); margin-top:6px; line-height:1.6;">Structure → function → common injuries and symptoms.</div>
          </div>
          <div style="border:1px solid rgba(201,162,74,0.18); background:rgba(2,6,5,0.68); border-radius:16px; padding:14px;">
            <strong style="color:var(--gold);">NCLEX / TEAS drills</strong>
            <div style="color:var(--muted); margin-top:6px; line-height:1.6;">Scenario questions, rationales, and spaced repetition.</div>
          </div>
        </div>
      </div>
    </section>
    """
    return page_shell("Botnology 101 • Curriculum", "curriculum", body)


@app.get("/pricing", response_class=HTMLResponse)
async def pricing():
    body = """
    <section class="panel">
      <div class="panel-inner">
        <div class="section-title serif">Tuition Plans</div>
        <div class="section-sub">Secure checkout powered by Stripe • Cancel anytime</div>

        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-top: 12px;">
          <div style="border:1px solid rgba(201,162,74,0.18); background:rgba(2,6,5,0.68); border-radius:16px; padding:14px; display:flex; flex-direction:column;">
            <div class="serif" style="color:var(--gold); font-size:1.05rem;">PRO</div>
            <div style="font-size:1.6rem; font-weight:700; margin:8px 0 6px; color:var(--text);">$29 <span style="font-size:.8rem; color:var(--muted); font-weight:400;">/ month</span></div>
            <div style="color:var(--muted); line-height:1.6; font-size:.9rem; margin-bottom:12px;">Ideal for students who want consistent academic support.</div>
            <button class="btn btn-primary" onclick="startCheckout('pro')">Select Pro</button>
          </div>

          <div style="border:1px solid rgba(22,101,52,0.65); background:rgba(2,6,5,0.68); border-radius:16px; padding:14px; display:flex; flex-direction:column;">
            <div class="serif" style="color:var(--gold); font-size:1.05rem;">SEMI-PRO</div>
            <div style="font-size:1.6rem; font-weight:700; margin:8px 0 6px; color:var(--text);">$149 <span style="font-size:.8rem; color:var(--muted); font-weight:400;">/ 6 months</span></div>
            <div style="color:var(--muted); line-height:1.6; font-size:.9rem; margin-bottom:12px;">Designed for exam cycles and anatomy-heavy programs.</div>
            <button class="btn btn-primary" onclick="startCheckout('semi_pro')">Select Semi-Pro</button>
          </div>

          <div style="border:1px solid rgba(201,162,74,0.18); background:rgba(2,6,5,0.68); border-radius:16px; padding:14px; display:flex; flex-direction:column;">
            <div class="serif" style="color:var(--gold); font-size:1.05rem;">YEARLY PRO</div>
            <div style="font-size:1.6rem; font-weight:700; margin:8px 0 6px; color:var(--text);">$249 <span style="font-size:.8rem; color:var(--muted); font-weight:400;">/ year</span></div>
            <div style="color:var(--muted); line-height:1.6; font-size:.9rem; margin-bottom:12px;">Best value for full academic year coverage.</div>
            <button class="btn btn-primary" onclick="startCheckout('yearly_pro')">Select Yearly</button>
          </div>
        </div>
      </div>
    </section>
    """

    script = r"""
      async function startCheckout(planKey){
        try{
          fetch("/api/create-checkout-session", {
            method:"POST",
            headers:{ "Content-Type":"application/json" },
            body: JSON.stringify({ plan: planKey })
          });
          const data = await res.json().catch(()=>({}));
          if(!res.ok){
            alert("Checkout error: " + (data.detail || "Unable to start checkout"));
            return;
          }
          if(data.url){
            window.location.href = data.url;
          } else {
            alert("No checkout URL returned.");
          }
        } catch(e){
          alert("Network error starting checkout.");
        }
      }
    """
    return page_shell("Botnology 101 • Tuition Plans", "pricing", body, extra_script=script)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    body = """
    <section class="panel">
      <div class="panel-inner">
        <div class="section-title serif">Student Dashboard</div>
        <div class="section-sub">Placeholder dashboard. Next step is real auth + saved projects.</div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <a class="btn btn-primary" href="/pricing">Manage tuition</a>
          <a class="btn" href="/">Back home</a>
        </div>
      </div>
    </section>
    """
    return page_shell("Botnology 101 • Dashboard", "dashboard", body)
    
