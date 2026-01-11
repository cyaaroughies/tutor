import os
from typing import List, Literal

import anthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

def get_client() -> anthropic.Anthropic:
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise HTTPException(status_code=500, detail="Missing ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=key)

@app.post("/")
async def chat(req: ChatRequest):
    client = get_client()

    system_message = "You are Mr. Botonic, a helpful tutor. Keep answers clear and structured."

    msgs = []
    for m in req.messages:
        if m.role == "system":
            continue
        role = m.role if m.role in ("user", "assistant") else "user"
        msgs.append({"role": role, "content": m.content})

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_message,
            messages=msgs
        )
        reply = resp.content[0].text if resp.content else ""
        return {"reply": reply}
    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API error: {str(e)"
                            
