# Voice input processing service — wired to AWS Transcribe + Database

import asyncio
import io
import logging
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.aws_config import get_transcribe_client, get_s3_client, S3_BUCKET_NAME
from app.config.database import SessionLocal
from app.models.voice_input import VoiceInput, VoiceInputStatus

logger = logging.getLogger(__name__)


class VoiceProcessor:
    """Handles speech-to-text conversion for voice input.

    Backend priority:
      1. AWS Transcribe  (if AWS credentials are configured)
      2. Mock fallback   (local dev)

    All transcriptions are persisted to the database.
    """

    SUPPORTED_LANGUAGES = [
        "hindi", "tamil", "telugu", "bengali", "marathi",
        "gujarati", "kannada", "malayalam", "punjabi", "english",
    ]

    _TRANSCRIBE_LANG_CODES = {
        "hindi": "hi-IN", "tamil": "ta-IN", "telugu": "te-IN",
        "bengali": "bn-IN", "marathi": "mr-IN", "gujarati": "gu-IN",
        "kannada": "kn-IN", "malayalam": "ml-IN", "punjabi": "pa-IN",
        "english": "en-IN",
    }

    def __init__(self):
        pass

    # ─── Public Methods ──────────────────────────────

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hindi",
        user_id: int = 1,
    ) -> dict:
        """Convert audio to text and persist to database."""

        db: Session = SessionLocal()
        try:
            # Create a processing record in the database
            voice_input = VoiceInput(
                user_id=user_id,
                audio_file_url="",
                audio_format="wav",
                audio_size_bytes=len(audio_data),
                language_specified=language,
                status=VoiceInputStatus.PROCESSING,
            )
            db.add(voice_input)
            db.commit()
            db.refresh(voice_input)

            # Attempt transcription
            start_time = time.time()
            try:
                transcribed_text, s3_url, confidence = await self._call_stt(audio_data, language)
                processing_time = int((time.time() - start_time) * 1000)

                voice_input.transcribed_text = transcribed_text
                voice_input.language_detected = language
                voice_input.status = VoiceInputStatus.COMPLETED
                voice_input.processing_time_ms = processing_time
                voice_input.word_count = len(transcribed_text.split())
                voice_input.completed_at = datetime.utcnow()
                voice_input.audio_file_url = s3_url
                if confidence > 0:
                    voice_input.confidence_score = confidence
            except Exception as e:
                voice_input.status = VoiceInputStatus.FAILED
                voice_input.error_message = str(e)
                logger.error(f"Transcription failed: {e}")

            db.commit()
            db.refresh(voice_input)

            return {
                "id": voice_input.id,
                "text": voice_input.transcribed_text or "",
                "language": language,
                "status": voice_input.status.value,
                "duration_seconds": voice_input.audio_duration_seconds or 0.0,
                "confidence": voice_input.confidence_score or 0.0,
                "processing_time_ms": voice_input.processing_time_ms or 0,
                "created_at": voice_input.created_at.isoformat(),
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Database error in transcription: {e}")
            return {
                "id": 0,
                "text": self._mock_transcribe(language),
                "language": language,
                "status": "error",
                "duration_seconds": 0.0,
                "confidence": 0.0,
                "processing_time_ms": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
        finally:
            db.close()

    async def get_history(self, user_id: int = 1, limit: int = 50) -> list[dict]:
        """Return voice transcription history from the database, newest first."""
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(VoiceInput)
                .filter(VoiceInput.user_id == user_id)
                .order_by(VoiceInput.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "text": r.transcribed_text or "",
                    "language": r.language_detected or r.language_specified,
                    "status": r.status.value if r.status else "unknown",
                    "duration_seconds": r.audio_duration_seconds or 0.0,
                    "confidence": r.confidence_score or 0.0,
                    "word_count": r.word_count or 0,
                    "processing_time_ms": r.processing_time_ms or 0,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()

    # ─── STT Integration ─────────────────────────────

    async def _call_stt(self, audio_data: bytes, language: str) -> tuple[str, str, float]:
        """Returns (transcribed_text, s3_url, confidence)."""

        # 1️⃣  AWS Transcribe
        if settings.has_aws_credentials:
            return await self._transcribe_with_aws(audio_data, language)

        # 2️⃣  Mock
        return self._mock_transcribe(language), "", 0.0

    async def _transcribe_with_aws(self, audio_data: bytes, language: str) -> tuple[str, str, float]:
        """Use AWS Transcribe: upload to S3 → start job → poll → return transcript."""
        import requests as http_requests

        s3 = get_s3_client()
        transcribe = get_transcribe_client()

        job_name = f"voice-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        s3_key = f"voice-uploads/{job_name}.wav"

        s3.put_object(
            Bucket=S3_BUCKET_NAME, Key=s3_key,
            Body=audio_data, ContentType="audio/wav",
        )
        s3_url = f"s3://{S3_BUCKET_NAME}/{s3_key}"

        lang_code = self._TRANSCRIBE_LANG_CODES.get(language, "en-IN")
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": s3_url},
            MediaFormat="wav",
            LanguageCode=lang_code,
        )

        # Poll (max ~60s)
        for _ in range(30):
            await asyncio.sleep(2)
            status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            job = status["TranscriptionJob"]

            if job["TranscriptionJobStatus"] == "COMPLETED":
                transcript_uri = job["Transcript"]["TranscriptFileUri"]
                resp = http_requests.get(transcript_uri)
                data = resp.json()
                transcript = data["results"]["transcripts"][0]["transcript"]

                # Extract confidence from AWS Transcribe response
                items = data.get("results", {}).get("items", [])
                if items:
                    confidences = [
                        float(item["alternatives"][0].get("confidence", 0))
                        for item in items
                        if item.get("alternatives")
                        and item["alternatives"][0].get("confidence")
                    ]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                else:
                    avg_confidence = 0.0

                try:
                    s3.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                except Exception:
                    pass

                return transcript, s3_url, avg_confidence

            elif job["TranscriptionJobStatus"] == "FAILED":
                raise Exception(f"Transcribe failed: {job.get('FailureReason', 'Unknown')}")

        raise Exception("Transcribe job timed out")

    # ─── Mock ────────────────────────────────────────

    def _mock_transcribe(self, language: str) -> str:
        samples = {
            "hindi": "नमस्ते, यह एक परीक्षण ऑडियो है। कृपया इसे टेक्स्ट में बदलें।",
            "tamil": "வணக்கம், இது ஒரு சோதனை ஆடியோ. இதை உரையாக மாற்றவும்.",
            "telugu": "నమస్కారం, ఇది ఒక పరీక్ష ఆడియో. దయచేసి దీన్ని టెక్స్ట్‌గా మార్చండి.",
            "bengali": "নমস্কার, এটি একটি পরীক্ষামূলক অডিও। দয়া করে এটিকে টেক্সটে রূপান্তর করুন।",
            "english": "Hello, this is a test audio. Please convert this to text.",
        }
        return samples.get(language, samples["english"])
