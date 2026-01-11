from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Literal
import os
import anthropic

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    client = get_client()

    system_message = "You are Mr. Botonic, a helpful tutor. Keep answers clear and structured."

    api_messages = []
    for m in req.messages:
        if m.role == "system":
            continue
        api_messages.append({"role": m.role, "content": m.content})

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_message,
            messages=api_messages,
        )
        reply = resp.content[0].text if resp.content else ""
        return {"reply": reply}
    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API error: {str(e)}")
