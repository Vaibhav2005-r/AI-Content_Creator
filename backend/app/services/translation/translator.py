# Translation service — wired to AWS Translate / Gemini / Bedrock + Database

import logging
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.aws_config import (
    get_translate_client,
    SUPPORTED_LANGUAGES as AWS_LANG_CODES,
)
from app.config.database import SessionLocal
from app.models.translation import Translation, TranslationMethod

logger = logging.getLogger(__name__)


class TranslationService:
    """Translates content between Indian languages with tone adjustment.

    Backend priority:
      1. AWS Translate  (if AWS credentials are configured)
      2. Google Gemini  (if GEMINI_API_KEY is set)
      3. Mock fallback  (local dev)

    All translations are persisted to the database.
    """

    SUPPORTED_LANGUAGES = {
        "english": "English",
        "hindi": "हिंदी (Hindi)",
        "tamil": "தமிழ் (Tamil)",
        "telugu": "తెలుగు (Telugu)",
        "bengali": "বাংলা (Bengali)",
        "marathi": "मराठी (Marathi)",
        "gujarati": "ગુજરાતી (Gujarati)",
        "kannada": "ಕನ್ನಡ (Kannada)",
        "malayalam": "മലയാളം (Malayalam)",
        "punjabi": "ਪੰਜਾਬੀ (Punjabi)",
        "urdu": "اردو (Urdu)",
    }

    SUPPORTED_TONES = ["neutral", "formal", "casual", "professional", "friendly"]

    def __init__(self):
        pass

    # ─── Public Methods ──────────────────────────────

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        tone: str = "neutral",
        content_id: int | None = None,
        user_id: int = 1,
    ) -> dict:
        """Translate text from source to target language with tone adjustment."""

        start_time = time.time()
        translated_text, method_used = await self._call_translation(
            text, source_language, target_language, tone
        )
        translation_time = int((time.time() - start_time) * 1000)

        # ── Persist to database ──────────────────────
        db: Session = SessionLocal()
        try:
            trans_obj = Translation(
                content_id=content_id,
                source_text=text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language,
                method=method_used,
                translation_time_ms=translation_time,
                tone_preserved=tone,
                source_char_count=len(text),
                target_char_count=len(translated_text),
            )
            db.add(trans_obj)
            db.commit()
            db.refresh(trans_obj)

            return {
                "id": trans_obj.id,
                "translated_text": translated_text,
                "source_language": source_language,
                "target_language": target_language,
                "tone": tone,
                "original_text": text,
                "method": method_used.value,
                "translation_time_ms": translation_time,
                "created_at": trans_obj.created_at.isoformat(),
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Database error saving translation: {e}")
            return {
                "id": 0,
                "translated_text": translated_text,
                "source_language": source_language,
                "target_language": target_language,
                "tone": tone,
                "original_text": text,
                "method": method_used.value,
                "translation_time_ms": translation_time,
                "created_at": datetime.utcnow().isoformat(),
            }
        finally:
            db.close()

    def get_supported_languages(self) -> list[dict]:
        return [
            {"code": code, "name": name}
            for code, name in self.SUPPORTED_LANGUAGES.items()
        ]

    async def get_history(self, limit: int = 50) -> list[dict]:
        """Return translation history from the database, newest first."""
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(Translation)
                .order_by(Translation.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "translated_text": r.translated_text,
                    "source_language": r.source_language,
                    "target_language": r.target_language,
                    "tone": r.tone_preserved or "neutral",
                    "original_text": r.source_text,
                    "method": r.method.value if r.method else "mock",
                    "translation_time_ms": r.translation_time_ms or 0,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()

    # ─── Backend Router ──────────────────────────────

    async def _call_translation(
        self, text, source_language, target_language, tone
    ) -> tuple[str, TranslationMethod]:
        """Route to the best available translation backend."""

        # 1️⃣  AWS Translate
        if settings.has_aws_credentials:
            try:
                result = self._translate_with_aws(text, source_language, target_language)
                return result, TranslationMethod.AWS_TRANSLATE
            except Exception as e:
                logger.warning(f"AWS Translate failed: {e}")

        # 2️⃣  Gemini
        if settings.has_gemini:
            try:
                result = self._translate_with_gemini(text, source_language, target_language, tone)
                return result, TranslationMethod.GOOGLE_TRANSLATE
            except Exception as e:
                logger.warning(f"Gemini translation failed: {e}")

        # 3️⃣  Bedrock
        if settings.has_bedrock_bearer or settings.has_aws_credentials:
            try:
                result = self._translate_with_bedrock(text, source_language, target_language, tone)
                return result, TranslationMethod.CUSTOM_MODEL
            except Exception as e:
                logger.warning(f"Bedrock translation failed: {e}")

        # 4️⃣  Mock
        return self._mock_translate(text, target_language), TranslationMethod.CUSTOM_MODEL

    # ── AWS Translate ────────────────────────────────
    def _translate_with_aws(self, text, source_language, target_language):
        client = get_translate_client()
        src_code = AWS_LANG_CODES.get(source_language, "en")
        tgt_code = AWS_LANG_CODES.get(target_language, "hi")
        response = client.translate_text(
            Text=text, SourceLanguageCode=src_code, TargetLanguageCode=tgt_code,
        )
        return response["TranslatedText"]

    # ── Gemini ───────────────────────────────────────
    def _translate_with_gemini(self, text, source_language, target_language, tone):
        from app.services.content_generation.gemini_service import GeminiContentGenerator
        src_name = self.SUPPORTED_LANGUAGES.get(source_language, source_language)
        tgt_name = self.SUPPORTED_LANGUAGES.get(target_language, target_language)
        prompt = (
            f"Translate from {src_name} to {tgt_name}. Use a {tone} tone. "
            f"Return ONLY the translated text.\n\n{text}"
        )
        gen = GeminiContentGenerator()
        result = gen.generate_content(prompt=prompt, language=target_language, tone=tone,
                                       content_type="caption", max_tokens=len(text.split()) * 3)
        return result["content"]

    # ── Bedrock ──────────────────────────────────────
    def _translate_with_bedrock(self, text, source_language, target_language, tone):
        from app.services.content_generation.bedrock_service import BedrockContentGenerator
        src_name = self.SUPPORTED_LANGUAGES.get(source_language, source_language)
        tgt_name = self.SUPPORTED_LANGUAGES.get(target_language, target_language)
        prompt = (
            f"Translate from {src_name} to {tgt_name}. Use a {tone} tone. "
            f"Return ONLY the translated text.\n\n{text}"
        )
        gen = BedrockContentGenerator()
        result = gen.generate_content(prompt=prompt, language=target_language, tone=tone,
                                       content_type="caption")
        return result["content"]

    # ── Mock ─────────────────────────────────────────
    def _mock_translate(self, text, target_language):
        labels = {
            "hindi": "🇮🇳 [हिंदी अनुवाद]", "tamil": "🇮🇳 [தமிழ் மொழிபெயர்ப்பு]",
            "telugu": "🇮🇳 [తెలుగు అనువాదం]", "bengali": "🇮🇳 [বাংলা অনুবাদ]",
            "marathi": "🇮🇳 [मराठी भाषांतर]", "english": "🇮🇳 [English Translation]",
        }
        label = labels.get(target_language, f"[{target_language}]")
        return f"{label}: {text}"
