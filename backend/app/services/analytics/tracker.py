# Analytics tracking service — wired to CloudWatch + Database

import logging
import time
from datetime import datetime, date

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config.settings import settings
from app.config.aws_config import get_cloudwatch_client, CLOUDWATCH_LOG_GROUP
from app.config.database import SessionLocal
from app.models.analytics import Analytics, ContentPerformance
from app.models.content import Content
from app.models.post import Post, PostStatus
from app.models.translation import Translation

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Tracks content performance and engagement metrics.

    Stores analytics in the database and optionally pushes to CloudWatch.
    """

    EVENT_TYPES = [
        "content_generated",
        "content_translated",
        "content_summarized",
        "post_scheduled",
        "post_published",
        "voice_transcribed",
    ]

    def __init__(self):
        pass

    # ─── Public Methods ──────────────────────────────

    async def track_event(
        self,
        event_type: str,
        metadata: dict | None = None,
        user_id: int = 1,
    ) -> dict:
        """
        Record an analytics event. Updates the daily Analytics row
        and optionally pushes to CloudWatch.
        """
        db: Session = SessionLocal()
        try:
            today = date.today()

            # Get or create today's analytics row for this user
            analytics = (
                db.query(Analytics)
                .filter(Analytics.user_id == user_id, Analytics.date == today)
                .first()
            )

            if not analytics:
                analytics = Analytics(user_id=user_id, date=today)
                db.add(analytics)
                db.flush()

            # Increment the right counter
            if event_type == "content_generated":
                analytics.content_generated = (analytics.content_generated or 0) + 1
            elif event_type == "content_translated":
                analytics.translations_made = (analytics.translations_made or 0) + 1
            elif event_type == "content_summarized":
                # Tracked under content_generated (summarization is a form of generation)
                analytics.content_generated = (analytics.content_generated or 0) + 1
            elif event_type == "post_scheduled":
                analytics.posts_scheduled = (analytics.posts_scheduled or 0) + 1
            elif event_type == "post_published":
                analytics.posts_published = (analytics.posts_published or 0) + 1
            elif event_type == "voice_transcribed":
                # Tracked under total_api_calls (no dedicated column)
                pass

            analytics.total_api_calls = (analytics.total_api_calls or 0) + 1

            # Update language usage
            meta = metadata or {}
            lang = meta.get("language")
            if lang:
                usage = analytics.language_usage or {}
                usage[lang] = usage.get(lang, 0) + 1
                analytics.language_usage = usage

            # Update content type usage
            ctype = meta.get("content_type")
            if ctype:
                ct_usage = analytics.content_type_usage or {}
                ct_usage[ctype] = ct_usage.get(ctype, 0) + 1
                analytics.content_type_usage = ct_usage

            db.commit()
            db.refresh(analytics)

            event = {
                "id": analytics.id,
                "event_type": event_type,
                "metadata": meta,
                "created_at": datetime.utcnow().isoformat(),
            }

            # Push to CloudWatch
            if settings.has_aws_credentials:
                try:
                    self._log_to_cloudwatch(event)
                except Exception as e:
                    logger.warning(f"CloudWatch logging failed: {e}")

            return event

        except Exception as e:
            db.rollback()
            logger.error(f"Analytics tracking error: {e}")
            return {
                "id": 0,
                "event_type": event_type,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }
        finally:
            db.close()

    async def get_dashboard(self, user_id: int = 1) -> dict:
        """Return an analytics dashboard from the database."""
        db: Session = SessionLocal()
        try:
            # Aggregate stats from Analytics table
            totals = (
                db.query(
                    func.sum(Analytics.content_generated).label("total_generated"),
                    func.sum(Analytics.translations_made).label("total_translated"),
                    func.sum(Analytics.posts_scheduled).label("total_scheduled"),
                    func.sum(Analytics.posts_published).label("total_published"),
                    func.sum(Analytics.total_api_calls).label("total_api_calls"),
                )
                .filter(Analytics.user_id == user_id)
                .first()
            )

            # Content count from the contents table
            content_count = db.query(func.count(Content.id)).filter(
                Content.user_id == user_id
            ).scalar()

            # Post count by status
            posts_by_status = {}
            for status in PostStatus:
                count = db.query(func.count(Post.id)).filter(
                    Post.user_id == user_id, Post.status == status
                ).scalar()
                if count > 0:
                    posts_by_status[status.value] = count

            # Language breakdown from Contents
            lang_rows = (
                db.query(Content.language, func.count(Content.id))
                .filter(Content.user_id == user_id)
                .group_by(Content.language)
                .all()
            )
            language_breakdown = {row[0]: row[1] for row in lang_rows}

            # Recent analytics rows
            recent = (
                db.query(Analytics)
                .filter(Analytics.user_id == user_id)
                .order_by(Analytics.date.desc())
                .limit(7)
                .all()
            )
            recent_days = [
                {
                    "date": r.date.isoformat(),
                    "content_generated": r.content_generated or 0,
                    "translations_made": r.translations_made or 0,
                    "posts_published": r.posts_published or 0,
                    "api_calls": r.total_api_calls or 0,
                }
                for r in recent
            ]

            return {
                "total_content": content_count or 0,
                "total_generated": totals.total_generated or 0 if totals else 0,
                "total_translated": totals.total_translated or 0 if totals else 0,
                "total_scheduled": totals.total_scheduled or 0 if totals else 0,
                "total_published": totals.total_published or 0 if totals else 0,
                "total_api_calls": totals.total_api_calls or 0 if totals else 0,
                "posts_by_status": posts_by_status,
                "language_breakdown": language_breakdown,
                "recent_days": recent_days,
            }
        finally:
            db.close()

    async def get_events(
        self, event_type: str | None = None, user_id: int = 1, limit: int = 30
    ) -> list[dict]:
        """Get analytics rows from the database."""
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(Analytics)
                .filter(Analytics.user_id == user_id)
                .order_by(Analytics.date.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "date": r.date.isoformat(),
                    "content_generated": r.content_generated or 0,
                    "translations_made": r.translations_made or 0,
                    "posts_scheduled": r.posts_scheduled or 0,
                    "posts_published": r.posts_published or 0,
                    "total_api_calls": r.total_api_calls or 0,
                    "language_usage": r.language_usage,
                }
                for r in rows
            ]
        finally:
            db.close()

    async def get_content_stats(self, user_id: int = 1) -> dict:
        """Get aggregated content-creation statistics from the database."""
        db: Session = SessionLocal()
        try:
            content_count = db.query(func.count(Content.id)).filter(
                Content.user_id == user_id
            ).scalar()

            translation_count = db.query(func.count(Translation.id)).scalar()

            published_posts = db.query(func.count(Post.id)).filter(
                Post.user_id == user_id, Post.status == PostStatus.PUBLISHED
            ).scalar()

            scheduled_posts = db.query(func.count(Post.id)).filter(
                Post.user_id == user_id, Post.status == PostStatus.SCHEDULED
            ).scalar()

            return {
                "total_content": content_count or 0,
                "total_translations": translation_count or 0,
                "total_published": published_posts or 0,
                "total_scheduled": scheduled_posts or 0,
            }
        finally:
            db.close()

    # ─── CloudWatch ──────────────────────────────────

    def _log_to_cloudwatch(self, event: dict) -> None:
        import json
        client = get_cloudwatch_client()
        log_stream = f"analytics-{date.today().isoformat()}"

        try:
            client.create_log_group(logGroupName=CLOUDWATCH_LOG_GROUP)
        except Exception:
            pass
        try:
            client.create_log_stream(
                logGroupName=CLOUDWATCH_LOG_GROUP, logStreamName=log_stream
            )
        except Exception:
            pass

        client.put_log_events(
            logGroupName=CLOUDWATCH_LOG_GROUP,
            logStreamName=log_stream,
            logEvents=[{
                "timestamp": int(time.time() * 1000),
                "message": json.dumps(event),
            }],
        )
