import os
from typing import List, Literal, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from openai import OpenAI

app = FastAPI()

# ---------- Models ----------
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None

# ---------- Health ----------
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# ---------- Chat ----------
@app.post("/api/chat")
async def chat(payload: ChatRequest):
    api_key = os.getenv("OPENAI_API_KEY")
print("DEBUG KEY FROM ENV:", api_key)
api_key = (api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")

    model = payload.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    client = OpenAI(api_key=api_key)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[m.model_dump() for m in payload.messages],
            temperature=0.6
        )
        return {
            "reply": resp.choices[0].message.content,
            "model": model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Serve frontend locally ----------
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
if PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")
