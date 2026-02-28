from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.translation.translator import TranslationService

router = APIRouter()
translation_service = TranslationService()


# ─── Request / Response Models ───────────────────

class TranslationRequest(BaseModel):
    text: str
    source_language: str
    target_language: str
    tone: str = "neutral"


class TranslationResponse(BaseModel):
    id: int
    translated_text: str
    source_language: str
    target_language: str
    tone: str
    original_text: str
    created_at: str


# ─── Endpoints ───────────────────────────────────

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """Translate text between Indian languages using AWS Translate / Gemini / Bedrock."""
    try:
        result = await translation_service.translate(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            tone=request.tone,
        )
        return TranslationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages for translation."""
    return {
        "languages": translation_service.get_supported_languages(),
        "tones": TranslationService.SUPPORTED_TONES,
    }


@router.get("/history")
async def get_translation_history():
    """Get translation history."""
    history = await translation_service.get_history()
    return {"translations": history, "count": len(history)}
