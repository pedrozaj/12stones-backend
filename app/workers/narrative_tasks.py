"""Narrative generation tasks."""

from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="narrative:generate")
def generate_narrative(self, project_id: str, tone: str = "reflective"):
    """Generate a narrative script from project content."""
    self.update_state(state="PROGRESS", meta={"progress": 0})

    # TODO: Implement narrative generation
    # 1. Get all content items with analysis
    # 2. Build context for LLM
    # 3. Call Claude API with narrative prompt
    # 4. Parse response into scenes
    # 5. Create narrative record

    self.update_state(state="PROGRESS", meta={"progress": 50})

    # TODO: Continue with scene mapping
    # 6. Map scenes to content items
    # 7. Calculate durations
    # 8. Update narrative with scenes

    self.update_state(state="PROGRESS", meta={"progress": 100})
    return {"status": "completed", "project_id": project_id}
