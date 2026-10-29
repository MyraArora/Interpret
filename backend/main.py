# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os

app = FastAPI(title="Interpret NVDA Backend")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class SpatialPayload(BaseModel):
    elements: list

@app.get("/")
def health_check():
    return {"status": "Interpret backend running"}

# Ensure this matches the full path: /api/spatial-map
@app.post("/api/spatial-map")
async def generate_spatial_map(payload: SpatialPayload):
    if GROQ_API_KEY == "YOUR_ACTUAL_GROQ_OR_GEMINI_KEY_HERE":
        raise HTTPException(status_code=400, detail="API key not set in local backend.")

    system_prompt = (
        "You are a spatial screen navigation assistant for blind screen reader users. "
        "You will receive a list of UI elements with screen bounding boxes (left, top, width, height). "
        "Synthesize a clear, 2 to 5 sentence holistic overview of the screen layout. "
        "Identify the 3 to 4 main interactive regions and give concise spatial instructions."
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                },
                json={
                    "model": "openai/gpt-oss-20b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"UI Elements Data: {payload.elements[:25]}"}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 200
                },
                timeout=15.0
            )
            
            if response.status_code != 200:
                print("Remote API Error Response:", response.text)
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
            data = response.json()
            return {"overview": data["choices"][0]["message"]["content"].strip()}

        except Exception as e:
            print(f"Backend Relay Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))