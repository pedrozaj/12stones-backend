"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, content, jobs, narratives, projects, social, videos, voice

settings = get_settings()

app = FastAPI(
    title="12 Stones API",
    description="AI Life Narrative Video Generator",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3002",
        "https://12stones-frontend.vercel.app",
    ],
    allow_origin_regex=r"https://12stones-frontend.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(social.router, prefix="/api/social", tags=["Social Connections"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(content.router, prefix="/api/projects/{project_id}/content", tags=["Content"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(
    narratives.router, prefix="/api/projects/{project_id}/narratives", tags=["Narratives"]
)
app.include_router(videos.router, prefix="/api/projects/{project_id}/videos", tags=["Videos"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "12stones-api"}


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "0.1.0",
    }
