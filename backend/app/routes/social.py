from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.social_media.scheduler import SocialMediaScheduler

router = APIRouter()
scheduler = SocialMediaScheduler()


# ─── Request / Response Models ───────────────────

class SchedulePostRequest(BaseModel):
    content: str
    platforms: list[str]
    scheduled_time: str
    language: str = "english"


class PublishRequest(BaseModel):
    post_id: int


# ─── Endpoints ───────────────────────────────────

@router.post("/schedule")
async def schedule_post(request: SchedulePostRequest):
    """Schedule a post for future publishing across platforms."""
    try:
        post = await scheduler.schedule_post(
            content=request.content,
            platforms=request.platforms,
            scheduled_time=request.scheduled_time,
            language=request.language,
        )
        return {"message": "Post scheduled successfully", "post": post}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts")
async def get_scheduled_posts(status: str | None = None):
    """Get all scheduled posts, optionally filtered by status."""
    posts = await scheduler.get_scheduled_posts(status=status)
    return {"posts": posts, "count": len(posts)}


@router.get("/posts/{post_id}")
async def get_post(post_id: int):
    """Get a single post by ID."""
    post = await scheduler.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/publish")
async def publish_post(request: PublishRequest):
    """Publish a scheduled post immediately."""
    post = await scheduler.publish_post(request.post_id)
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found or not in 'scheduled' status",
        )
    return {"message": "Post published successfully", "post": post}


@router.post("/cancel/{post_id}")
async def cancel_post(post_id: int):
    """Cancel a scheduled post."""
    post = await scheduler.cancel_post(post_id)
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found or not in 'scheduled' status",
        )
    return {"message": "Post cancelled", "post": post}


@router.get("/platforms")
async def get_supported_platforms():
    """Get list of supported social media platforms."""
    return {
        "platforms": SocialMediaScheduler.SUPPORTED_PLATFORMS,
        "statuses": SocialMediaScheduler.POST_STATUSES,
    }
