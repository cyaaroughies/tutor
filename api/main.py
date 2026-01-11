@app.get("/health")
async def health():
    return {"status": "ok"}

# Optional alias so local older frontend still works
@app.get("/api/health")
async def health_alias():
    return {"status": "ok"}


@app.post("/chat")
async def chat(payload: ChatRequest):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")

    model = payload.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    client = OpenAI(api_key=api_key)

    resp = client.chat.completions.create(
        model=model,
        messages=[m.model_dump() for m in payload.messages],
        temperature=0.6
    )
    return {"reply": resp.choices[0].message.content, "model": model}

# Optional alias
@app.post("/api/chat")
async def chat_alias(payload: ChatRequest):
    return await chat(payload)
