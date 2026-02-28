from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.summarizer.summarizer import SummarizerService

router = APIRouter()
summarizer_service = SummarizerService()


# ─── Request / Response Models ───────────────────

class SummarizeRequest(BaseModel):
    text: str
    language: str = "english"
    max_length: int = 200
    output_format: str = "paragraph"  # "paragraph" or "bullet_points"


# ─── Endpoints ───────────────────────────────────

@router.post("/summarize")
async def summarize_text(request: SummarizeRequest):
    """Summarise long-form content and extract key points.

    Uses Gemini / Bedrock / mock fallback. Result is saved to the database.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        result = await summarizer_service.summarize(
            text=request.text,
            language=request.language,
            max_length=request.max_length,
            output_format=request.output_format,
        )
        return {"message": "Content summarized successfully", "summary": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_summarization_history(limit: int = 50):
    """Get summarization history from the database."""
    history = await summarizer_service.get_history(limit=limit)
    return {"summaries": history, "count": len(history)}
