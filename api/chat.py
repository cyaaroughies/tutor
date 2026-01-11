import os
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None

@app.post("/")
async def chat(payload: ChatRequest):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")

    model = (payload.model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()

    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    client = OpenAI(api_key=api_key)

    resp = client.chat.completions.create(
        model=model,
        messages=[m.model_dump() for m in payload.messages],
        temperature=0.6
    )

    reply = resp.choices[0].message.content or ""
    return {"reply": reply, "model": model}
