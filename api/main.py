import os
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

app = FastAPI()


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None


@app.get("/api/health")
async def health():
    return {"status": "ok"}


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
