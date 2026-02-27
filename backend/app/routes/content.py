from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ContentRequest(BaseModel):
    prompt: str
    language: str = "hindi"
    tone: str = "casual"

class ContentResponse(BaseModel):
    content: str
    language: str

@router.post("/generate", response_model=ContentResponse)
async def generate_content(request: ContentRequest):
    """Generate content in specified Indian language"""
    # MVP: Simple mock response
    content = f"Generated content in {request.language}: {request.prompt}"
    return ContentResponse(content=content, language=request.language)
