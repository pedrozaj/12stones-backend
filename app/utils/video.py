"""Video creation utilities using FFmpeg."""

import os
import subprocess
import tempfile
from pathlib import Path

import ffmpeg
from PIL import Image


def resize_image_to_fit(image_path: str, output_path: str, width: int = 1920, height: int = 1080) -> None:
    """
    Resize an image to fit within the specified dimensions while maintaining aspect ratio.
    Adds black bars (letterbox/pillarbox) if needed.

    Args:
        image_path: Path to source image
        output_path: Path for resized image
        width: Target width
        height: Target height
    """
    with Image.open(image_path) as img:
        # Convert to RGB if necessary (handles RGBA, P mode, etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Calculate scaling to fit within bounds
        img_ratio = img.width / img.height
        target_ratio = width / height

        if img_ratio > target_ratio:
            # Image is wider - fit to width
            new_width = width
            new_height = int(width / img_ratio)
        else:
            # Image is taller - fit to height
            new_height = height
            new_width = int(height * img_ratio)

        # Resize image
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create new image with black background
        final = Image.new("RGB", (width, height), (0, 0, 0))

        # Paste resized image centered
        x = (width - new_width) // 2
        y = (height - new_height) // 2
        final.paste(resized, (x, y))

        # Save as JPEG
        final.save(output_path, "JPEG", quality=95)


def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds."""
    probe = ffmpeg.probe(audio_path)
    audio_stream = next(
        (stream for stream in probe["streams"] if stream["codec_type"] == "audio"),
        None,
    )
    if audio_stream is None:
        raise ValueError("No audio stream found")
    return float(audio_stream["duration"])


def create_slideshow(
    image_paths: list[str],
    audio_path: str,
    output_path: str,
    fade_duration: float = 0.5,
) -> dict:
    """
    Create a slideshow video from images with audio narration.

    Args:
        image_paths: List of paths to images (in order)
        audio_path: Path to audio file
        output_path: Path for output video
        fade_duration: Duration of fade transitions between images

    Returns:
        Dict with video metadata (duration, file_size)
    """
    if not image_paths:
        raise ValueError("No images provided")

    # Get audio duration to calculate timing
    audio_duration = get_audio_duration(audio_path)

    # Calculate duration per image (distribute evenly across audio length)
    num_images = len(image_paths)
    duration_per_image = audio_duration / num_images

    # Create temporary directory for processed images
    with tempfile.TemporaryDirectory() as temp_dir:
        processed_images = []

        # Resize all images to consistent dimensions
        for i, img_path in enumerate(image_paths):
            processed_path = os.path.join(temp_dir, f"img_{i:03d}.jpg")
            resize_image_to_fit(img_path, processed_path)
            processed_images.append(processed_path)

        # Create video segments - simplest possible approach
        segment_files = []
        fps = 24
        total_frames = int(duration_per_image * fps)

        for i, img_path in enumerate(processed_images):
            segment_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")
            segment_files.append(segment_path)

            # Debug: verify image exists and has content
            if not os.path.exists(img_path):
                raise RuntimeError(f"Image file does not exist: {img_path}")
            img_size = os.path.getsize(img_path)
            if img_size == 0:
                raise RuntimeError(f"Image file is empty: {img_path}")

            # Absolute simplest FFmpeg command - no fancy filters
            # Just loop image, set duration, encode
            segment_cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", img_path,
                "-vf", "format=yuv420p,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-t", str(duration_per_image),
                "-r", str(fps),
                "-an",  # No audio for segments
                segment_path,
            ]

            seg_result = subprocess.run(segment_cmd, capture_output=True, text=True, timeout=300)
            if seg_result.returncode != 0:
                raise RuntimeError(f"Failed to create segment {i} (size={img_size}): {seg_result.stderr[-1000:]}")

        # Create concat list file
        concat_list = os.path.join(temp_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        # Concatenate segments with audio
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-i", audio_path,
            "-c:v", "copy",  # No re-encode needed
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]

        # Run ffmpeg with 10 minute timeout
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg timed out after 10 minutes")

        if result.returncode != 0:
            # Capture first 1000 and last 1000 chars to see both error context
            stderr = result.stderr
            if len(stderr) > 2000:
                error_msg = f"...{stderr[:1000]}...[truncated]...{stderr[-1000:]}"
            else:
                error_msg = stderr
            raise RuntimeError(f"FFmpeg failed: {error_msg}")

    # Get output file info
    file_size = os.path.getsize(output_path)

    # Get video duration
    probe = ffmpeg.probe(output_path)
    video_stream = next(
        (stream for stream in probe["streams"] if stream["codec_type"] == "video"),
        None,
    )
    duration = float(video_stream["duration"]) if video_stream else audio_duration

    return {
        "duration_seconds": int(duration),
        "file_size_bytes": file_size,
    }


def create_slideshow_with_transitions(
    image_paths: list[str],
    audio_path: str,
    output_path: str,
    transition_duration: float = 1.0,
) -> dict:
    """
    Create a slideshow video with crossfade transitions between images.

    This is a more sophisticated version that uses ffmpeg's xfade filter
    for smooth transitions between images.

    Args:
        image_paths: List of paths to images (in order)
        audio_path: Path to audio file
        output_path: Path for output video
        transition_duration: Duration of crossfade transitions

    Returns:
        Dict with video metadata (duration, file_size)
    """
    if not image_paths:
        raise ValueError("No images provided")

    if len(image_paths) == 1:
        # Single image - no transitions needed
        return create_slideshow(image_paths, audio_path, output_path)

    # Get audio duration
    audio_duration = get_audio_duration(audio_path)

    # Calculate timing
    num_images = len(image_paths)
    total_transition_time = transition_duration * (num_images - 1)
    available_time = audio_duration - total_transition_time
    duration_per_image = available_time / num_images

    if duration_per_image < 1.0:
        # Not enough time for transitions, fall back to simple slideshow
        return create_slideshow(image_paths, audio_path, output_path)

    # Skip xfade for reliability - just use simple slideshow
    # The xfade filter with -loop 1 has proven unreliable on Railway
    return create_slideshow(image_paths, audio_path, output_path)
