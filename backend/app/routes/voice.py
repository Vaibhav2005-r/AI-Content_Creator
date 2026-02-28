from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from app.services.voice.processor import VoiceProcessor

router = APIRouter()
voice_processor = VoiceProcessor()


# ─── Endpoints ───────────────────────────────────

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("hindi"),
):
    """Convert speech to text using AWS Transcribe or mock fallback.

    Accepts audio files (WAV, MP3, etc.) and returns the transcribed text.
    Result is saved to the database.
    """
    # Validate file type
    allowed_types = [
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/mpeg", "audio/mp3", "audio/mp4",
        "audio/ogg", "audio/webm", "audio/flac",
        "application/octet-stream",  # fallback for unknown types
    ]
    if audio.content_type and audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {audio.content_type}. "
                   f"Supported: WAV, MP3, MP4, OGG, WebM, FLAC",
        )

    # Validate language
    if language not in VoiceProcessor.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {language}. "
                   f"Supported: {VoiceProcessor.SUPPORTED_LANGUAGES}",
        )

    try:
        audio_data = await audio.read()
        if not audio_data:
            raise HTTPException(status_code=400, detail="Audio file is empty")

        result = await voice_processor.transcribe(
            audio_data=audio_data,
            language=language,
        )
        return {"message": "Audio transcribed successfully", "transcription": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_transcription_history(limit: int = 50):
    """Get voice transcription history from the database."""
    history = await voice_processor.get_history(limit=limit)
    return {"transcriptions": history, "count": len(history)}


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages for voice transcription."""
    return {"languages": VoiceProcessor.SUPPORTED_LANGUAGES}
