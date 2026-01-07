# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---- Safe imports ----
try:
    import stripe  # type: ignore
except Exception:
    stripe = None  # type: ignore

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
ASSETS_DIR = PUBLIC_DIR / "assets"
BOTONIC_PNG = ASSETS_DIR / "botonic.png"


def env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def stripe_ready() -> bool:
    return bool(stripe) and bool(env("STRIPE_SECRET_KEY"))


def stripe_prices() -> Dict[str, str]:
    # Matches YOUR Vercel env vars
    return {
        "pro": env("STRIPE_PRICE_PRO"),
        "semi_pro": env("STRIPE_PRICE_SEMI_PRO"),
        "yearly_pro": env("STRIPE_PRICE_YEARLY_PRO"),
    }


def get_app_base(request: Optional[Request] = None) -> str:
    base = env("APP_BASE_URL").rstrip("/")
    if base:
        return base
    if request is not None:
        return str(request.base_url).rstrip("/")
    return "http://localhost:8000"


def openai_client() -> Optional[Any]:
    if OpenAI is None:
        return None
    key = env("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)


# ----------------------------
# HEALTH + DEBUG (support both)
# ----------------------------
@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "openai_configured": bool(env("OPENAI_API_KEY")) and OpenAI is not None,
        "stripe_configured": stripe_ready(),
        "public_dir": str(PUBLIC_DIR),
    }


@app.get("/stripe-debug")
@app.get("/api/stripe-debug")
def stripe_debug():
    pm = stripe_prices()
    return {
        "stripe_imported": bool(stripe),
        "has_secret": bool(env("STRIPE_SECRET_KEY")),
        "prices": pm,
        "app_base_url": env("APP_BASE_URL"),
    }


# ----------------------------
# ASSET: Dr. Botonic avatar
# ----------------------------
@app.get("/assets/botonic.png")
def botonic_png():
    if BOTONIC_PNG.exists():
        return FileResponse(str(BOTONIC_PNG))
    raise HTTPException(status_code=404, detail="Missing public/assets/botonic.png")


# ----------------------------
# CHAT
# Expected body:
# { "messages":[{"role":"user","content":"hi"}], "model":"gpt-4o-mini" }
# ----------------------------
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None


@app.post("/chat")
@app.post("/api/chat")
def chat(payload: ChatRequest):
    client = openai_client()
    if client is None:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY or OpenAI SDK not installed.")

    model = (payload.model or env("OPENAI_MODEL") or "gpt-4o-mini").strip()

    if not payload.messages or all(m.role != "user" for m in payload.messages):
        raise HTTPException(status_code=400, detail="Provide at least one user message")

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[m.model_dump() for m in payload.messages],
            temperature=0.6,
        )
        reply = resp.choices[0].message.content or ""
        return {"reply": reply, "model": model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ----------------------------
# STRIPE CHECKOUT
# Expected body:
# { "plan": "pro" | "semi_pro" | "yearly_pro" }
# Returns:
# { "url": "https://checkout.stripe.com/..." }
# ----------------------------
@app.post("/create-checkout-session")
@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request):
    if not stripe_ready():
        raise HTTPException(status_code=500, detail="Stripe not configured (missing stripe lib or STRIPE_SECRET_KEY).")

    data: Dict[str, Any] = {}
    try:
        data = await request.json()
    except Exception:
        pass

    plan = str(data.get("plan") or "").strip().lower()
    pm = stripe_prices()
    price_id = pm.get(plan, "")

    if not price_id or not price_id.startswith("price_"):
        raise HTTPException(status_code=400, detail="Invalid plan or missing Stripe price ID for this plan.")

    stripe.api_key = env("STRIPE_SECRET_KEY")
    base = get_app_base(request)

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{base}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/?checkout=cancel",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------
# STATIC SITE (MOUNT LAST)
# ----------------------------
if PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")
