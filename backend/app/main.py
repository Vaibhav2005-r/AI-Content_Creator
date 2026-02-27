from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import content, translation

app = FastAPI(title="Bharat Content AI API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(translation.router, prefix="/api/translation", tags=["translation"])

@app.get("/")
def read_root():
    return {"message": "Bharat Content AI API", "status": "running"}
