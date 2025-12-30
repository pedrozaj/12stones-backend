"""Job status endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.job import JobResponse

router = APIRouter()


@router.get("", response_model=list[JobResponse])
async def list_jobs(db: Session = Depends(get_db)):
    """List user's active jobs."""
    # TODO: Implement list jobs
    return []


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Get job status."""
    # TODO: Implement get job
    raise HTTPException(status_code=501, detail="Not implemented")
