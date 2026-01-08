# -*- coding: utf-8 -*-
import os
import datetime
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import FileResponse, HTMLResponse

# ---------- OpenAI (safe import) ----------
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore

# ---------- Stripe (safe import) ----------
try:
    import stripe  # type: ignore
except Exception:
    stripe = None  # type: ignore


app = FastAPI()

# ---------------------------
# Paths
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # repo root (../)
IMG_PATH = BASE_DIR / "dr-botonic.png"

# ---------------------------
# Env
# ---------------------------
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

DAILY_LIMIT = int(os.getenv("BOTNOLOGY_DAILY_LIMIT", "50"))  # free preview cap (guest)
daily_usage: Dict[Tuple[str, str], int] = defaultdict(int)


def today_str() -> str:
    return datetime.date.today().isoformat()


def client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def get_app_base(request: Optional[Request] = None) -> str:
    env_base = (os.getenv("APP_BASE_URL") or "").strip().rstrip("/")
    if env_base:
        return env_base
    if request is not None:
        return str(request.base_url).rstrip("/")
    return "http://localhost:8000"


def stripe_ready() -> bool:
    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    return bool(stripe) and bool(key)


def stripe_price_map() -> Dict[str, str]:
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


# ---------------------------
# Supabase session validation
# ---------------------------
def supabase_configured() -> bool:
    return bool(SUPABASE_URL) and bool(SUPABASE_SERVICE_ROLE_KEY)


def try_require_user(authorization: str | None) -> Optional[Dict[str, Any]]:
    """
    Returns a user dict if:
      - Supabase env vars exist AND
      - Bearer token exists AND
      - Token validates with Supabase

    Returns None if not configured or no token.
    Raises 401 only if token exists but is invalid.
    """
    if not supabase_configured():
        return None

    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None

    r = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
        },
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session token")

    return r.json()


# ---------------------------
# Health
# ---------------------------
@app.get("/api/health")
@app.get("/health")
async def health():
    pm = stripe_price_map()
    return {
        "status": "ok",
        "stripe_ready": stripe_ready(),
        "stripe_imported": bool(stripe),
        "has_openai_key": bool((os.getenv("OPENAI_API_KEY") or "").strip()),
        "supabase_configured": supabase_configured(),
        "prices_present": {
            "pro": bool(pm.get("pro")),
            "semi_pro": bool(pm.get("semi_pro")),
            "yearly_pro": bool(pm.get("yearly_pro")),
        },
        "app_base_url": (os.getenv("APP_BASE_URL") or "").strip(),
    }


# ---------------------------
# Asset: Dr. Botonic image
# ---------------------------
@app.get("/dr-botonic.png")
async def dr_image():
    if IMG_PATH.exists():
        return FileResponse(str(IMG_PATH))
    raise HTTPException(status_code=404, detail="dr-botonic.png not found at repo root.")


# ---------------------------
# Chat request types
# ---------------------------
from pydantic import BaseModel


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    subject: Optional[str] = None
    history: Optional[List[ChatTurn]] = None
    context: Optional[Dict[str, Any]] = None


# ---------------------------
# Chat endpoint (ship-today mode)
# - If Supabase token provided and valid => user-based limits
# - Else => guest limits
# ---------------------------
@app.post("/api/chat")
async def chat(request: Request, payload: ChatRequest, authorization: str | None = Header(default=None)):
    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message is required")

    # Identify user (optional)
    user = try_require_user(authorization)  # may raise 401 if invalid token
    user_id = (user.get("id") if isinstance(user, dict) else None) or ""

    # Limits
    if user_id:
        key = (f"user:{user_id}", today_str())
    else:
        key = (f"guest:{client_id(request)}", today_str())

    if daily_usage[key] >= DAILY_LIMIT and not user_id:
        return {"reply": "You’ve reached today’s preview limit. Tuition plans unlock unlimited sessions."}
    daily_usage[key] += 1

    # Subject + context
    ctx = payload.context or {}
    subject = str(payload.subject or ctx.get("subject") or "General Study").strip() or "General Study"
    subj = subject.lower()

    focus = "You are a calm, professor-level academic tutor. Explain step-by-step and verify understanding."
    if any(k in subj for k in ["anatomy", "nursing", "medical", "musculoskeletal", "neuro"]):
        focus = "You are a highly competent anatomy/nursing tutor. Be clinically correct and explain structure–function clearly."

    project = str(ctx.get("project") or "").strip()
    folder = str(ctx.get("folder") or "").strip()
    plan = str(ctx.get("plan") or "").strip()

    context_line = ""
    if project or folder or plan:
        context_line = f"Context: project={project or '—'}, folder={folder or '—'}, plan={plan or '—'}."

    system_msg = f"You are Dr. Botonic. Subject: {subject}. {context_line} {focus} Keep answers crisp, structured, and actionable."

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_msg}]

    # History
    history = payload.history or []
    for t in history:
        if t.role in ("user", "assistant") and isinstance(t.content, str) and t.content.strip():
            messages.append({"role": t.role, "content": t.content.strip()})

    messages.append({"role": "user", "content": text})

    c = openai_client()
    if not c:
        return {"reply": f"Demo mode (OPENAI_API_KEY missing). You asked: “{text}”"}

    try:
        resp = c.chat.completions.create(
            model=(os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip(),
            messages=messages,
            max_tokens=600 if plan.upper() in ("PRO", "YEARLY_PRO") else 450,
            temperature=0.6,
        )
        reply = (resp.choices[0].message.content or "").strip()
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ---------------------------
# Stripe checkout
# ---------------------------
@app.post("/api/create-checkout-session")
@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    if not stripe_ready():
        raise HTTPException(status_code=500, detail="Stripe not configured (missing stripe lib or STRIPE_SECRET_KEY).")

    try:
        data = await request.json()
    except Exception:
        data = {}

    plan = (data.get("plan") or "").strip().lower()
    pm = stripe_price_map()

    if plan not in pm or not pm[plan] or not str(pm[plan]).startswith("price_"):
        raise HTTPException(status_code=400, detail="Invalid plan or missing Stripe price ID for this plan.")

    stripe.api_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    base = get_app_base(request)

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": pm[plan], "quantity": 1}],
            success_url=f"{base}/dashboard?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/pricing?checkout=cancel",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Optional: basic HTML root (only used if you route / to api)
@app.get("/_api_root", response_class=HTMLResponse)
async def api_root():
    return "<h1>API OK</h1><p>Use /api/health, /api/chat, /api/create-checkout-session</p>"
