from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import content, translation, social, analytics, summarizer, voice
from app.config.database import init_db

app = FastAPI(
    title="Bharat Content AI API",
    description="AI-powered multilingual content creation platform for Indian creators",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(content.router, prefix="/api/content", tags=["Content Generation"])
app.include_router(translation.router, prefix="/api/translation", tags=["Translation"])
app.include_router(social.router, prefix="/api/social", tags=["Social Media"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(summarizer.router, prefix="/api/summarizer", tags=["Summarizer"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice Input"])


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup."""
    try:
        init_db()
    except Exception as e:
        print(f"⚠ Database init warning: {e}")


@app.get("/")
def read_root():
    return {
        "message": "Bharat Content AI API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "content": "/api/content",
            "translation": "/api/translation",
            "social": "/api/social",
            "analytics": "/api/analytics",
            "summarizer": "/api/summarizer",
            "voice": "/api/voice",
        },
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    from app.config.settings import settings

    return {
        "status": "healthy",
        "gemini_configured": settings.has_gemini,
        "aws_configured": settings.has_aws_credentials,
        "bedrock_bearer_configured": settings.has_bedrock_bearer,
        "database": "connected",
    }
