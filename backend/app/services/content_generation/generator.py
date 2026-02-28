# AI content generation service — wired to Gemini / Bedrock + Database

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.aws_config import get_recommended_model, BEDROCK_MODELS, MODEL_SPECS
from app.config.database import SessionLocal
from app.models.content import Content, ContentType, ContentStatus, ToneType
from app.models.ai_model_config import ModelUsageLog

logger = logging.getLogger(__name__)


class ContentGenerationService:
    """Generates AI-powered content in multiple Indian languages.

    Automatically picks the best available backend:
      1. Google Gemini (if GEMINI_API_KEY is set)
      2. AWS Bedrock  (if AWS credentials / bearer token are set)
      3. Mock fallback (for local development without keys)

    All generated content is persisted to the database.
    """

    SUPPORTED_LANGUAGES = {
        "english": "English",
        "hindi": "हिंदी",
        "tamil": "தமிழ்",
        "telugu": "తెలుగు",
        "bengali": "বাংলা",
        "marathi": "मराठी",
        "gujarati": "ગુજરાતી",
        "kannada": "ಕನ್ನಡ",
        "malayalam": "മലയാളം",
        "punjabi": "ਪੰਜਾਬੀ",
    }

    TONE_INSTRUCTIONS = {
        "casual": "Use a casual, friendly, and conversational tone",
        "formal": "Use a formal, professional, and polished tone",
        "professional": "Use a business-professional tone suitable for LinkedIn",
        "humorous": "Use a humorous, witty, and entertaining tone",
        "inspirational": "Use an inspirational and motivational tone",
    }

    # Map string tones to enum values (graceful fallback)
    _TONE_ENUM_MAP = {
        "casual": ToneType.CASUAL,
        "formal": ToneType.FORMAL,
        "professional": ToneType.PROFESSIONAL,
        "humorous": ToneType.HUMOROUS,
        "inspirational": ToneType.INSPIRATIONAL,
        "friendly": ToneType.FRIENDLY,
        "educational": ToneType.EDUCATIONAL,
    }

    _CONTENT_TYPE_MAP = {
        "social_post": ContentType.SOCIAL_POST,
        "blog": ContentType.BLOG,
        "article": ContentType.ARTICLE,
        "caption": ContentType.CAPTION,
        "script": ContentType.SCRIPT,
        "email": ContentType.EMAIL,
        "ad_copy": ContentType.AD_COPY,
    }

    def __init__(self):
        pass

    # ─── Public Methods ──────────────────────────────

    async def generate(
        self,
        prompt: str,
        language: str = "hindi",
        tone: str = "casual",
        content_type: str = "social_post",
        max_length: int = 500,
        model_preference: str = "balanced",
        user_id: int = 1,
    ) -> dict:
        """Generate content for the given prompt in the target language & tone."""

        generated = await self._call_ai(
            prompt, language, tone, content_type, max_length, model_preference
        )

        # ── Persist to database ──────────────────────
        db: Session = SessionLocal()
        try:
            content_obj = Content(
                user_id=user_id,
                original_prompt=prompt,
                generated_content=generated["content"],
                content_type=self._CONTENT_TYPE_MAP.get(content_type, ContentType.SOCIAL_POST),
                status=ContentStatus.GENERATED,
                language=language,
                tone=self._TONE_ENUM_MAP.get(tone, ToneType.CASUAL),
                model_used=generated.get("model_name", "mock"),
                bedrock_model_id=generated.get("model_used"),
                generation_time_ms=generated.get("generation_time_ms", 0),
                word_count=len(generated["content"].split()),
                character_count=len(generated["content"]),
            )
            db.add(content_obj)
            db.commit()
            db.refresh(content_obj)

            # Log model usage
            usage_log = ModelUsageLog(
                model_config_id=None,
                model_name=generated.get("model_name", "mock"),
                user_id=user_id,
                request_type="generation",
                input_tokens=generated.get("input_tokens", 0),
                output_tokens=generated.get("output_tokens", 0),
                total_tokens=generated.get("input_tokens", 0) + generated.get("output_tokens", 0),
                latency_ms=generated.get("generation_time_ms", 0),
                success=True,
            )
            db.add(usage_log)
            db.commit()

            result = {
                "id": content_obj.id,
                "content": content_obj.generated_content,
                "language": content_obj.language,
                "tone": tone,
                "content_type": content_type,
                "word_count": content_obj.word_count,
                "model_used": generated.get("model_used", "mock"),
                "model_name": generated.get("model_name", "Mock Generator"),
                "generation_time_ms": generated.get("generation_time_ms", 0),
                "created_at": content_obj.created_at.isoformat(),
                "prompt": prompt,
            }
            return result

        except Exception as e:
            db.rollback()
            logger.error(f"Database error saving content: {e}")
            # Return result without DB id as fallback
            return {
                "id": 0,
                "content": generated["content"],
                "language": language,
                "tone": tone,
                "content_type": content_type,
                "word_count": len(generated["content"].split()),
                "model_used": generated.get("model_used", "mock"),
                "model_name": generated.get("model_name", "Mock Generator"),
                "generation_time_ms": generated.get("generation_time_ms", 0),
                "created_at": datetime.utcnow().isoformat(),
                "prompt": prompt,
            }
        finally:
            db.close()

    async def get_history(self, user_id: int = 1, limit: int = 50) -> list[dict]:
        """Return content generation history from the database, newest first."""
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(Content)
                .filter(Content.user_id == user_id)
                .order_by(Content.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "content": r.generated_content,
                    "language": r.language,
                    "tone": r.tone.value if r.tone else "casual",
                    "content_type": r.content_type.value if r.content_type else "social_post",
                    "word_count": r.word_count,
                    "model_used": r.bedrock_model_id or r.model_used,
                    "model_name": r.model_used,
                    "generation_time_ms": r.generation_time_ms or 0,
                    "created_at": r.created_at.isoformat(),
                    "prompt": r.original_prompt,
                }
                for r in rows
            ]
        finally:
            db.close()

    def get_supported_languages(self) -> dict:
        return self.SUPPORTED_LANGUAGES

    def get_supported_tones(self) -> dict:
        return self.TONE_INSTRUCTIONS

    def get_available_models(self) -> dict:
        return BEDROCK_MODELS

    # ─── AI Integration ──────────────────────────────

    async def _call_ai(
        self, prompt, language, tone, content_type, max_length, model_preference
    ) -> dict:
        # 1️⃣  Gemini
        if settings.has_gemini:
            return self._generate_with_gemini(prompt, language, tone, content_type, max_length)

        # 2️⃣  Bedrock
        if settings.has_bedrock_bearer or settings.has_aws_credentials:
            return self._generate_with_bedrock(
                prompt, language, tone, content_type, max_length, model_preference
            )

        # 3️⃣  Mock
        logger.warning("No AI API key configured — returning mock content.")
        return {
            "content": self._mock_generate(prompt, language),
            "model_used": "mock",
            "model_name": "Mock Generator",
            "generation_time_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def _generate_with_gemini(self, prompt, language, tone, content_type, max_length):
        from app.services.content_generation.gemini_service import GeminiContentGenerator
        gen = GeminiContentGenerator()
        return gen.generate_content(
            prompt=prompt, language=language, tone=tone,
            content_type=content_type, max_tokens=max_length * 2,
        )

    def _generate_with_bedrock(self, prompt, language, tone, content_type, max_length, pref):
        from app.services.content_generation.bedrock_service import BedrockContentGenerator
        gen = BedrockContentGenerator()
        return gen.generate_content(
            prompt=prompt, language=language, tone=tone,
            content_type=content_type, model_preference=pref, max_tokens=max_length * 2,
        )

    # ─── Mock ────────────────────────────────────────

    def _mock_generate(self, prompt: str, language: str) -> str:
        templates = {
            "hindi": (
                f"🌟 {prompt}\n\n"
                f"नमस्ते दोस्तों! आज हम बात करेंगे '{prompt}' के बारे में। "
                f"यह एक बहुत ही महत्वपूर्ण विषय है। "
                f"अपने विचार कमेंट में जरूर बताएं! 💬\n\n"
                f"#भारत #हिंदी #ContentCreator"
            ),
            "tamil": (
                f"🌟 {prompt}\n\n"
                f"வணக்கம் நண்பர்களே! இன்று '{prompt}' பற்றி பேசுவோம். "
                f"உங்கள் கருத்துக்களை பகிருங்கள்! 💬\n\n"
                f"#தமிழ் #ContentCreator"
            ),
        }
        default = (
            f"🌟 {prompt}\n\n"
            f"Hey everyone! Let's talk about '{prompt}'. "
            f"Share your thoughts! 💬\n\n#India #ContentCreator"
        )
        return templates.get(language, default)
