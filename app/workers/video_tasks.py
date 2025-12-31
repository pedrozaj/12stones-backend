"""Video rendering tasks."""

import os
import tempfile
from datetime import datetime
from uuid import UUID

from app.database import SessionLocal
from app.models.content import ContentItem
from app.models.narrative import Narrative
from app.models.video import Video, VideoStatus
from app.utils.elevenlabs import synthesize_speech
from app.utils.storage import get_file_from_r2, upload_file_to_r2
from app.utils.video import create_slideshow_with_transitions
from app.workers.celery_app import celery_app


def update_video_progress(db, video: Video, progress: int, stage: str) -> None:
    """Update video progress in database."""
    video.render_progress = progress
    db.commit()


@celery_app.task(bind=True, name="video:render")
def render_video(self, video_id: str):
    """
    Render final video from narrative and content.

    Stages:
    - 0-30%: Generate audio narration via ElevenLabs
    - 30-40%: Download content images from R2
    - 40-90%: Create video with FFmpeg
    - 90-100%: Upload final video to R2
    """
    db = SessionLocal()

    try:
        # Get video record
        video = db.query(Video).filter(Video.id == UUID(video_id)).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        # Update status to rendering
        video.status = VideoStatus.RENDERING
        video.render_started_at = datetime.utcnow()
        db.commit()

        self.update_state(state="PROGRESS", meta={"progress": 0, "stage": "preparing"})
        update_video_progress(db, video, 0, "preparing")

        # Get narrative
        narrative = db.query(Narrative).filter(Narrative.id == video.narrative_id).first()
        if not narrative:
            raise ValueError(f"Narrative not found: {video.narrative_id}")

        # Get content items for the project that are included in narrative
        content_items = db.query(ContentItem).filter(
            ContentItem.project_id == video.project_id,
            ContentItem.deleted_at.is_(None),
            ContentItem.included_in_narrative == True,
        ).order_by(
            ContentItem.narrative_order.asc().nullslast(),
            ContentItem.taken_at.asc().nullslast(),
            ContentItem.created_at.asc(),
        ).all()

        if not content_items:
            raise ValueError("No content items found for video")

        # Create temp directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Stage 1: Generate audio narration (0-30%)
            self.update_state(state="PROGRESS", meta={"progress": 5, "stage": "generating_audio"})
            update_video_progress(db, video, 5, "generating_audio")

            # Use narrative script text for audio
            script_text = narrative.script_text

            # Get voice ID from voice profile if available
            voice_id = None
            if video.voice_profile_id:
                from app.models.voice import VoiceProfile
                voice_profile = db.query(VoiceProfile).filter(
                    VoiceProfile.id == video.voice_profile_id
                ).first()
                if voice_profile and voice_profile.elevenlabs_voice_id:
                    voice_id = voice_profile.elevenlabs_voice_id

            # Generate speech audio
            audio_bytes = synthesize_speech(script_text, voice_id)

            # Save audio to temp file
            audio_path = os.path.join(temp_dir, "narration.mp3")
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            self.update_state(state="PROGRESS", meta={"progress": 25, "stage": "audio_complete"})
            update_video_progress(db, video, 25, "audio_complete")

            # Upload audio to R2 for reference
            audio_r2_key = upload_file_to_r2(
                audio_bytes,
                f"narration_{video_id}.mp3",
                "audio/mpeg",
                folder="narrations",
            )
            video.narration_r2_key = audio_r2_key
            db.commit()

            self.update_state(state="PROGRESS", meta={"progress": 30, "stage": "downloading_content"})
            update_video_progress(db, video, 30, "downloading_content")

            # Stage 2: Download content images from R2 (30-40%)
            image_paths = []
            total_items = len(content_items)

            for i, item in enumerate(content_items):
                # Only use photos for slideshow (skip videos for now)
                if item.type.value != "photo":
                    continue

                # Download image from R2
                try:
                    image_data = get_file_from_r2(item.r2_key)
                    image_path = os.path.join(temp_dir, f"content_{i}.jpg")
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                    image_paths.append(image_path)
                except Exception as e:
                    # Log error but continue with other images
                    print(f"Failed to download image {item.r2_key}: {e}")
                    continue

                # Update progress (30-40%)
                progress = 30 + int((i / total_items) * 10)
                self.update_state(state="PROGRESS", meta={"progress": progress, "stage": "downloading_content"})
                update_video_progress(db, video, progress, "downloading_content")

            if not image_paths:
                raise ValueError("No images could be downloaded for video")

            self.update_state(state="PROGRESS", meta={"progress": 40, "stage": "rendering_video"})
            update_video_progress(db, video, 40, "rendering_video")

            # Stage 3: Create video with FFmpeg (40-90%)
            output_path = os.path.join(temp_dir, "output.mp4")

            # Create slideshow with transitions
            video_result = create_slideshow_with_transitions(
                image_paths=image_paths,
                audio_path=audio_path,
                output_path=output_path,
                transition_duration=1.0,
            )

            self.update_state(state="PROGRESS", meta={"progress": 85, "stage": "video_complete"})
            update_video_progress(db, video, 85, "video_complete")

            # Stage 4: Upload video to R2 (90-100%)
            self.update_state(state="PROGRESS", meta={"progress": 90, "stage": "uploading"})
            update_video_progress(db, video, 90, "uploading")

            with open(output_path, "rb") as f:
                video_bytes = f.read()

            video_r2_key = upload_file_to_r2(
                video_bytes,
                f"video_{video_id}.mp4",
                "video/mp4",
                folder="videos",
            )

            # Update video record with results
            video.r2_key = video_r2_key
            video.duration_seconds = video_result["duration_seconds"]
            video.file_size_bytes = video_result["file_size_bytes"]
            video.status = VideoStatus.COMPLETED
            video.render_completed_at = datetime.utcnow()
            video.render_progress = 100
            db.commit()

            self.update_state(state="PROGRESS", meta={"progress": 100, "stage": "complete"})

            return {
                "status": "completed",
                "video_id": video_id,
                "r2_key": video_r2_key,
                "duration_seconds": video_result["duration_seconds"],
                "file_size_bytes": video_result["file_size_bytes"],
            }

    except Exception as e:
        # Update video status to failed
        try:
            video = db.query(Video).filter(Video.id == UUID(video_id)).first()
            if video:
                video.status = VideoStatus.FAILED
                video.error_message = str(e)
                db.commit()
        except Exception:
            pass

        raise

    finally:
        db.close()


@celery_app.task(bind=True, name="video:generate_thumbnail")
def generate_thumbnail(self, video_id: str, video_url: str):
    """Generate thumbnail from video."""
    # TODO: Extract frame from video for thumbnail
    # 1. Download video (or use temp file from render)
    # 2. Extract frame at ~10% duration
    # 3. Resize to thumbnail dimensions
    # 4. Upload to R2
    # 5. Update video record

    return {"status": "completed", "video_id": video_id}
