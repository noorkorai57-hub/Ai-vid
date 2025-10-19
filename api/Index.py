# main.py

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

# --- Configuration ---
VIDEO_API_BASE_URL = "https://yabes-api.pages.dev/api/ai/video/v2"

# --- Initialize FastAPI App ---
app = FastAPI(
    title="Text-to-Video Veo3 API",
    description="Generate Veo3 videos from text prompts.",
    version="1.0.0"
)

# --- Pydantic Models ---
class Text2VideoRequest(BaseModel):
    prompt: str = Field(..., example="A futuristic city with flying cars and neon lights")
    max_wait_seconds: int = Field(default=60, example=60)  # Max wait for video generation

# --- API Endpoints ---
@app.post("/api/text-to-video")
async def generate_text_to_video(request_data: Text2VideoRequest):
    """
    Generate a video from a text prompt using Veo3 API.
    Returns video URL once ready.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Step 1: Create video generation task
            create_url = f"{VIDEO_API_BASE_URL}?action=create&prompt={request_data.prompt}"
            create_resp = await client.get(create_url)
            create_resp.raise_for_status()
            create_data = create_resp.json()

            if "taskId" not in create_data:
                raise HTTPException(status_code=500, detail="Failed to create video task")

            task_id = create_data["taskId"]

            # Step 2: Poll for status until completed or timeout
            import asyncio
            status_url = f"{VIDEO_API_BASE_URL}?action=status&taskId={task_id}"
            interval = 2  # seconds
            attempts = request_data.max_wait_seconds // interval

            for _ in range(attempts):
                await asyncio.sleep(interval)
                status_resp = await client.get(status_url)
                status_resp.raise_for_status()
                status_data = status_resp.json()

                if status_data.get("status") == "completed":
                    video_url = status_data.get("videoUrl")
                    if not video_url:
                        raise HTTPException(status_code=500, detail="Video URL missing")
                    return {"status": "completed", "video_url": video_url}

            # If we reach here, video is still processing
            return {"status": "processing", "message": "Video is still generating. Try again later."}

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"External API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
