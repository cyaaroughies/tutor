# -*- coding: utf-8 -*-
import os
from typing import List, Literal, Optional
from pathlib import Path

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

app = FastAPI()

# ----------------------------
# Models
# ----------------------------
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None

# ----------------------------
# Health (support both paths)
# ----------------------------
@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# ----------------------------
# Chat (support both paths)
# ----------------------------
@app.post("/chat")
@app.post("/api/chat")
async def chat(payload: ChatRequest):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")

    if OpenAI is None:
        raise HTTPException(status_code=500, detail="OpenAI SDK missing. Check requirements.txt")

    model = (payload.model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()

    if not payload.messages or all(m.role != "user" for m in payload.messages):
        raise HTTPException(status_code=400, detail="Provide at least one user message")

    client = OpenAI(api_key=api_key)

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
# Stripe Checkout (support both paths)
# ----------------------------
@app.post("/create-checkout-session")
@app.post("/api/create-checkout-session")
async def create_checkout_session(req: Request):
    body = await req.json()
    plan = (body.get("plan") or "").strip().lower()
    if not plan:
        raise HTTPException(status_code=400, detail="Missing plan")

    stripe_secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not stripe_secret:
        raise HTTPException(status_code=500, detail="Missing STRIPE_SECRET_KEY")

    price_map = {
        "basic": os.getenv("STRIPE_PRICE_BASIC", "").strip(),
        "pro": os.getenv("STRIPE_PRICE_PRO", "").strip(),
    }
    price_id = price_map.get(plan, "")

    if not price_id or not price_id.startswith("price_"):
        raise HTTPException(status_code=400, detail="Invalid plan or missing Stripe price ID for this plan.")

    stripe.api_key = stripe_secret

    app_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if not app_base:
        app_base = "https://botnology101.com"

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{app_base}/dashboard.html?checkout=success",
            cancel_url=f"{app_base}/pricing.html?checkout=cancel",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------
# Static site (mount LAST so it can't hijack /api/*)
# ----------------------------
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
if PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")
