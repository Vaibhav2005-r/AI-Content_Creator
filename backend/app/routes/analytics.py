from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.analytics.tracker import AnalyticsService

router = APIRouter()
analytics_service = AnalyticsService()


# ─── Request Models ──────────────────────────────

class TrackEventRequest(BaseModel):
    event_type: str
    metadata: dict | None = None


# ─── Endpoints ───────────────────────────────────

@router.post("/track")
async def track_event(request: TrackEventRequest):
    """Record an analytics event."""
    if request.event_type not in AnalyticsService.EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type. Must be one of: {AnalyticsService.EVENT_TYPES}",
        )

    event = await analytics_service.track_event(
        event_type=request.event_type,
        metadata=request.metadata,
    )
    return {"message": "Event tracked", "event": event}


@router.get("/dashboard")
async def get_dashboard():
    """Get analytics dashboard summary."""
    dashboard = await analytics_service.get_dashboard()
    return dashboard


@router.get("/events")
async def get_events(event_type: Optional[str] = None, limit: int = 50):
    """Get analytics events, optionally filtered by type."""
    events = await analytics_service.get_events(event_type=event_type, limit=limit)
    return {"events": events, "count": len(events)}


@router.get("/stats")
async def get_content_stats():
    """Get aggregated content-creation statistics."""
    stats = await analytics_service.get_content_stats()
    return stats
