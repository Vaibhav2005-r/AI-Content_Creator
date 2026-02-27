from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class TranslationRequest(BaseModel):
    text: str
    source_language: str
    target_language: str
    tone: str = "neutral"

class TranslationResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """Translate text between Indian languages"""
    # MVP: Simple mock response
    translated = f"[{request.target_language}] {request.text}"
    return TranslationResponse(
        translated_text=translated,
        source_language=request.source_language,
        target_language=request.target_language
    )
