"""FastAPI application entry point."""

import os
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, content, instagram_import, jobs, narratives, projects, social, videos, voice
from app.utils.storage import configure_r2_cors

# Import all models to ensure they're registered with Base
from app.models import user, project, content as content_model, voice as voice_model  # noqa: F401
from app.models import narrative, video, social as social_model, job  # noqa: F401

settings = get_settings()

# Global reference to worker process
_worker_process = None


def start_celery_worker():
    """Start Celery worker in a subprocess."""
    global _worker_process
    # Only start if not in development mode and Redis is configured
    if not settings.redis_url:
        print("REDIS_URL not configured, skipping Celery worker")
        return

    print("Starting Celery worker in background...")
    _worker_process = subprocess.Popen(
        [
            "celery",
            "-A", "app.workers.celery_app",
            "worker",
            "-l", "info",
            "-Q", "content,voice,narrative,video",
            "-c", "1",  # Single worker to reduce memory
            "-P", "solo",  # Solo pool to minimize memory usage
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"Celery worker started with PID {_worker_process.pid}")


def stop_celery_worker():
    """Stop the Celery worker subprocess."""
    global _worker_process
    if _worker_process:
        print("Stopping Celery worker...")
        _worker_process.terminate()
        _worker_process.wait(timeout=10)
        _worker_process = None
        print("Celery worker stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup and configure R2 CORS."""
    Base.metadata.create_all(bind=engine)
    # Configure CORS on R2 bucket for direct uploads
    configure_r2_cors()
    # Start Celery worker in background (for Railway single-service deployment)
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        start_celery_worker()
    yield
    # Cleanup
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        stop_celery_worker()

app = FastAPI(
    title="12 Stones API",
    description="AI Life Narrative Video Generator",
    version="0.1.0",
    lifespan=lifespan,
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
        "https://12stones-frontend-bv7bcbsbe-joeys-projects-7189f482.vercel.app",
        "https://12stones-frontend-njdzq017r-joeys-projects-7189f482.vercel.app",
        "https://12stones-frontend-73bvfgz25-joeys-projects-7189f482.vercel.app",
        "https://12stones-frontend-h4bgxt07p-joeys-projects-7189f482.vercel.app",
        "https://12stones-frontend-dwfs7pzjp-joeys-projects-7189f482.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(social.router, prefix="/api/social", tags=["Social Connections"])
app.include_router(
    instagram_import.router, prefix="/api/import/instagram", tags=["Instagram Import"]
)
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


@app.post("/debug/test-ffmpeg")
async def debug_test_ffmpeg():
    """
    Test FFmpeg video creation in isolation.

    Creates test images + silent audio, runs FFmpeg slideshow creation,
    and returns success/failure status.
    """
    from app.utils.test_ffmpeg import test_ffmpeg_slideshow
    return test_ffmpeg_slideshow()
