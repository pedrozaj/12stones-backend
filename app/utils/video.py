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

        # Simple approach: create video files for each image, then concat with protocol
        # This uses much less memory than filter_complex concat
        segment_files = []

        for i, img_path in enumerate(processed_images):
            segment_path = os.path.join(temp_dir, f"segment_{i:03d}.ts")
            segment_files.append(segment_path)

            # Create a video segment from this image
            segment_cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", img_path,
                "-t", str(duration_per_image),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "stillimage",
                "-pix_fmt", "yuv420p",
                "-r", "24",
                "-f", "mpegts",
                segment_path,
            ]

            seg_result = subprocess.run(segment_cmd, capture_output=True, text=True, timeout=120)
            if seg_result.returncode != 0:
                raise RuntimeError(f"Failed to create segment {i}: {seg_result.stderr[-500:]}")

        # Concatenate all segments with audio
        concat_input = "concat:" + "|".join(segment_files)

        cmd = [
            "ffmpeg", "-y",
            "-i", concat_input,
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
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

    with tempfile.TemporaryDirectory() as temp_dir:
        # Resize all images
        processed_images = []
        for i, img_path in enumerate(image_paths):
            processed_path = os.path.join(temp_dir, f"img_{i:03d}.jpg")
            resize_image_to_fit(img_path, processed_path)
            processed_images.append(processed_path)

        # Build complex filter for xfade transitions
        inputs = []
        filter_parts = []

        # Create input streams for each image
        for i, img_path in enumerate(processed_images):
            inputs.extend(["-loop", "1", "-t", str(duration_per_image + transition_duration), "-i", img_path])

        # Add audio input
        inputs.extend(["-i", audio_path])

        # Build xfade filter chain
        current_stream = "[0:v]"
        for i in range(1, num_images):
            next_stream = f"[{i}:v]"
            offset = duration_per_image * i
            out_stream = f"[v{i}]" if i < num_images - 1 else "[vout]"
            filter_parts.append(
                f"{current_stream}{next_stream}xfade=transition=fade:duration={transition_duration}:offset={offset}{out_stream}"
            )
            current_stream = out_stream

        filter_complex = ";".join(filter_parts)

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", f"{num_images}:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # Fall back to simple slideshow if transitions fail
            return create_slideshow(image_paths, audio_path, output_path)

    # Get output file info
    file_size = os.path.getsize(output_path)
    probe = ffmpeg.probe(output_path)
    video_stream = next(
        (s for s in probe["streams"] if s["codec_type"] == "video"),
        None,
    )
    duration = float(video_stream["duration"]) if video_stream else audio_duration

    return {
        "duration_seconds": int(duration),
        "file_size_bytes": file_size,
    }
