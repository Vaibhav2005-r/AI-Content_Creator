from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.content_generation.generator import ContentGenerationService

router = APIRouter()
content_service = ContentGenerationService()


# ─── Request / Response Models ───────────────────

class ContentRequest(BaseModel):
    prompt: str
    language: str = "hindi"
    tone: str = "casual"
    content_type: str = "social_post"
    max_length: int = 500
    model_preference: str = "balanced"


# ─── Endpoints ───────────────────────────────────

@router.post("/generate")
async def generate_content(request: ContentRequest):
    """Generate content using Google Gemini, AWS Bedrock, or mock fallback.

    Content is automatically saved to the database and model usage is logged.
    """
    try:
        result = await content_service.generate(
            prompt=request.prompt,
            language=request.language,
            tone=request.tone,
            content_type=request.content_type,
            max_length=request.max_length,
            model_preference=request.model_preference,
        )
        return {"message": "Content generated successfully", "content": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_content_history(limit: int = 50):
    """Get content generation history from the database."""
    history = await content_service.get_history(limit=limit)
    return {"history": history, "count": len(history)}


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages for content generation."""
    return {"languages": content_service.get_supported_languages()}


@router.get("/tones")
async def get_supported_tones():
    """Get list of supported tones for content generation."""
    return {"tones": content_service.get_supported_tones()}


@router.get("/models")
async def get_available_models():
    """Get list of available AI models."""
    return {"models": content_service.get_available_models()}
