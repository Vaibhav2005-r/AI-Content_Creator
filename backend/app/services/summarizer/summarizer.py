# Content summarizer service — wired to Gemini / Bedrock + Database

import json
import logging
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.database import SessionLocal
from app.models.content import Content, ContentType, ContentStatus, ToneType

logger = logging.getLogger(__name__)


class SummarizerService:
    """Summarises long-form content and extracts key points.

    Backend priority:
      1. Google Gemini  (if GEMINI_API_KEY is set)
      2. AWS Bedrock    (if credentials / bearer token are available)
      3. Mock fallback  (local dev)

    Summaries are persisted to the database as Content rows with type=ARTICLE.
    """

    def __init__(self):
        pass

    # ─── Public Methods ──────────────────────────────

    async def summarize(
        self,
        text: str,
        language: str = "english",
        max_length: int = 200,
        output_format: str = "paragraph",
        user_id: int = 1,
    ) -> dict:
        """Summarise the given text and extract key points."""

        start_time = time.time()
        summary, key_points = await self._call_ai(text, language, max_length, output_format)
        gen_time = int((time.time() - start_time) * 1000)

        # ── Persist to database ──────────────────────
        db: Session = SessionLocal()
        try:
            content_obj = Content(
                user_id=user_id,
                original_prompt=f"[SUMMARIZE] {text[:200]}...",
                generated_content=summary,
                content_type=ContentType.ARTICLE,
                status=ContentStatus.GENERATED,
                language=language,
                tone=ToneType.PROFESSIONAL,
                model_used="summarizer",
                generation_time_ms=gen_time,
                word_count=len(summary.split()),
                character_count=len(summary),
                keywords=key_points,  # Store key points in keywords JSON field
            )
            db.add(content_obj)
            db.commit()
            db.refresh(content_obj)

            return {
                "id": content_obj.id,
                "summary": summary,
                "key_points": key_points,
                "original_length": len(text.split()),
                "summary_length": len(summary.split()),
                "language": language,
                "generation_time_ms": gen_time,
                "created_at": content_obj.created_at.isoformat(),
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Database error saving summary: {e}")
            return {
                "id": 0,
                "summary": summary,
                "key_points": key_points,
                "original_length": len(text.split()),
                "summary_length": len(summary.split()),
                "language": language,
                "generation_time_ms": gen_time,
                "created_at": datetime.utcnow().isoformat(),
            }
        finally:
            db.close()

    async def get_history(self, user_id: int = 1, limit: int = 50) -> list[dict]:
        """Return summarization history from the database."""
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(Content)
                .filter(
                    Content.user_id == user_id,
                    Content.original_prompt.like("[SUMMARIZE]%"),
                )
                .order_by(Content.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "summary": r.generated_content,
                    "key_points": r.keywords or [],
                    "summary_length": r.word_count or 0,
                    "language": r.language,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()

    # ─── AI Integration ──────────────────────────────

    async def _call_ai(
        self, text, language, max_length, output_format
    ) -> tuple[str, list[str]]:

        # 1️⃣  Gemini
        if settings.has_gemini:
            try:
                return self._summarize_with_gemini(text, language, max_length, output_format)
            except Exception as e:
                logger.warning(f"Gemini summarization failed: {e}")

        # 2️⃣  Bedrock
        if settings.has_bedrock_bearer or settings.has_aws_credentials:
            try:
                return self._summarize_with_bedrock(text, language, max_length, output_format)
            except Exception as e:
                logger.warning(f"Bedrock summarization failed: {e}")

        # 3️⃣  Mock
        return self._mock_summarize(text)

    def _summarize_with_gemini(self, text, language, max_length, output_format):
        from app.services.content_generation.gemini_service import GeminiContentGenerator
        fmt = "bullet points" if output_format == "bullet_points" else "a concise paragraph"
        prompt = (
            f"Summarize in {language} in {fmt}. Max {max_length} words. "
            f'Extract 3-5 key points.\nReturn JSON: {{"summary": "...", "key_points": ["..."]}}\n\n'
            f"Text:\n{text}"
        )
        gen = GeminiContentGenerator()
        result = gen.generate_content(prompt=prompt, language=language, tone="professional",
                                       content_type="article", max_tokens=max_length * 3)
        return self._parse_json_response(result["content"])

    def _summarize_with_bedrock(self, text, language, max_length, output_format):
        from app.services.content_generation.bedrock_service import BedrockContentGenerator
        fmt = "bullet points" if output_format == "bullet_points" else "a concise paragraph"
        prompt = (
            f"Summarize in {language} in {fmt}. Max {max_length} words. "
            f'Extract 3-5 key points.\nReturn JSON: {{"summary": "...", "key_points": ["..."]}}\n\n'
            f"Text:\n{text}"
        )
        gen = BedrockContentGenerator()
        result = gen.generate_content(prompt=prompt, language=language, tone="professional",
                                       content_type="article")
        return self._parse_json_response(result["content"])

    def _parse_json_response(self, content: str) -> tuple[str, list[str]]:
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            data = json.loads(content.strip())
            return data.get("summary", content), data.get("key_points", [])
        except (json.JSONDecodeError, IndexError):
            return content, []

    def _mock_summarize(self, text: str) -> tuple[str, list[str]]:
        words = text.split()
        total = len(words)
        cut = min(50, max(10, total // 4))
        summary = " ".join(words[:cut])
        if cut < total:
            summary += "..."
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        key_points = sentences[:min(5, len(sentences))]
        if not key_points:
            key_points = ["Content provided for summarisation"]
        return summary, key_points
