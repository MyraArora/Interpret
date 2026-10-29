# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Interpret NVDA Backend")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class SpatialPayload(BaseModel):
    elements: list

@app.get("/")
def health_check():
    return {"status": "Interpret backend running"}

@app.post("/api/spatial-map")
async def generate_spatial_map(payload: SpatialPayload):
    if GROQ_API_KEY == "YOUR_ACTUAL_GROQ_KEY_HERE":
        raise HTTPException(status_code=400, detail="API key not set in local backend.")

    if not payload.elements:
        return {"overview": "No interactive screen elements detected in this window."}

    element_descriptions = []
    for item in payload.elements[:20]:
        name = item.get("name") or "unnamed"
        role = item.get("role") or "control"
        bounds = item.get("bounds", {})
        element_descriptions.append(
            f"- {role} '{name}' at bounding box left={bounds.get('left')}, top={bounds.get('top')}, width={bounds.get('width')}, height={bounds.get('height')}"
        )
    
    formatted_elements = "\n".join(element_descriptions)

    system_prompt = (
        "You are an expert spatial screen navigation assistant for a blind screen reader user. "
        "You will receive a list of visible UI elements with their bounding box positions (left, top, width, height) and names/roles. "
        "Provide a comprehensive, highly semantic 3 to 5 sentence description of what is actually on the screen. "
        "1. Identify the overarching context or purpose of the current window. "
        "2. Call out the 3 to 4 specific key interactive sections or major components visible (e.g., specific buttons, form inputs, navigation bars, or data panels) by their exact names. "
        "3. Provide clear, actionable spatial and keyboard navigation instructions on how to reach them. "
        "Do not give generic counts or vague placeholders. Be direct, semantic, and extremely practical."
        "CRITICAL RULES: "
        "- Output PLAIN TEXT ONLY. "
        "- NEVER use markdown formatting like asterisks (**), bolding, hashes (#), or bullet points. "
        "- Do not use conversational filler or internal reasoning tags."
    )

    user_prompt = f"Screen Elements:\n{formatted_elements}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openai/gpt-oss-20b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                timeout=20.0
            )
            
            if response.status_code != 200:
                print("Remote API Error Response:", response.text)
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
            data = response.json()
            
            # DEBUG PRINT: Look at this in your terminal window when you press NVDA+Shift+I!
            print("DEBUG RAW GROQ RESPONSE:", data)
            
            choices = data.get("choices", [])
            if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                content = choices[0]["message"]["content"].strip()
            else:
                content = ""
            
            if not content:
                primary_names = [item.get("name") for item in payload.elements if item.get("name")][:3]
                names_str = ", ".join(primary_names) if primary_names else "various interface controls"
                content = (
                    f"The window displays {len(payload.elements)} interactive controls, prominently featuring {names_str}. "
                    "Use Tab or object navigation to move through the layout from top to bottom."
                )
                
            return {"overview": content}

        except Exception as e:
            print(f"Backend Relay Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
import io
import base64
from PIL import Image

class VisionPayload(BaseModel):
    image_base64: str
    width: int
    height: int

@app.post("/api/multimodal-vision")
async def analyze_image_vision(payload: VisionPayload):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=400, detail="GROQ_API_KEY not found in environment variables.")

    try:
        # Reconstruct image from raw BGR bytes sent by NVDA and convert to JPEG bytes
        raw_bytes = base64.b64decode(payload.image_base64)
        image = Image.frombytes("RGB", (payload.width, payload.height), raw_bytes, "raw", "BGR", 0, 1)
        
        # Downscale for faster processing and optimal token limits
        image.thumbnail((1280, 1280))
        
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        jpeg_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image conversion error: {str(e)}")

    system_prompt = (
        "You are an expert vision assistant for a blind screen reader user. "
        "Analyze the provided image of a chart, graph, or graphical interface. "
        "If a single image is highlighted within the screen, focus on talking about it & explain everything worth knowing within it. "
        "Incase of a graph or chart, mention all important aspects for the user to fully understand it. "
        "Provide a concise, highly semantic summary in EXACTLY 2 to 3 short sentences: "
        "1. Identify the core type of graphic or chart and its primary subject. "
        "2. Call out key data points, trends, axes, or visual states. "
        "CRITICAL RULES: "
        "- Output PLAIN TEXT ONLY. "
        "- NEVER use markdown formatting like asterisks (**), bolding, hashes (#), or bullet points."
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen/qwen3.8-27b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe this visual interface or graph for a screen reader user."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{jpeg_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print("Vision API Error:", response.text)
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
            data = response.json()
            choices = data.get("choices", [])
            content = choices[0]["message"]["content"].strip() if choices and "message" in choices[0] else ""
            
            if not content:
                content = "The captured graphic displays visual data or UI elements without accessible text labels."
                
            return {"overview": content}

        except Exception as e:
            print(f"Vision Backend Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))