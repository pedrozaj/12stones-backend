"""Test FFmpeg video creation in isolation (no ElevenLabs dependency)."""

import os
import tempfile
import subprocess
from pathlib import Path

from PIL import Image


def create_test_images(temp_dir: str, count: int = 3) -> list[str]:
    """Create simple test images with different colors."""
    colors = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
    ]

    image_paths = []
    for i in range(count):
        color = colors[i % len(colors)]
        img = Image.new("RGB", (1920, 1080), color)

        # Add some text to identify the image
        path = os.path.join(temp_dir, f"test_image_{i}.jpg")
        img.save(path, "JPEG", quality=95)
        image_paths.append(path)
        print(f"Created test image {i}: {path} ({os.path.getsize(path)} bytes)")

    return image_paths


def create_silent_audio(output_path: str, duration: float = 10.0) -> None:
    """Create a silent audio file using FFmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:a", "aac",
        "-b:a", "192k",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create silent audio: {result.stderr}")

    print(f"Created silent audio: {output_path} ({os.path.getsize(output_path)} bytes)")


def test_ffmpeg_slideshow() -> dict:
    """
    Test the FFmpeg slideshow creation in isolation.

    Returns:
        Dict with test results
    """
    from app.utils.video import create_slideshow

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp directory: {temp_dir}")

        # Create test images
        print("\n=== Creating test images ===")
        image_paths = create_test_images(temp_dir, count=3)

        # Create silent audio (10 seconds)
        print("\n=== Creating silent audio ===")
        audio_path = os.path.join(temp_dir, "test_audio.aac")
        create_silent_audio(audio_path, duration=10.0)

        # Create output path
        output_path = os.path.join(temp_dir, "test_video.mp4")

        # Run slideshow creation
        print("\n=== Running create_slideshow ===")
        try:
            result = create_slideshow(
                image_paths=image_paths,
                audio_path=audio_path,
                output_path=output_path,
            )

            print(f"\n=== SUCCESS ===")
            print(f"Video created: {output_path}")
            print(f"Duration: {result['duration_seconds']} seconds")
            print(f"File size: {result['file_size_bytes']} bytes")

            # Verify the video exists and has content
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return {
                    "success": True,
                    "duration_seconds": result["duration_seconds"],
                    "file_size_bytes": result["file_size_bytes"],
                    "message": "FFmpeg slideshow creation working correctly!",
                }
            else:
                return {
                    "success": False,
                    "message": "Video file was not created or is empty",
                }

        except Exception as e:
            print(f"\n=== FAILED ===")
            print(f"Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "FFmpeg slideshow creation failed",
            }


if __name__ == "__main__":
    result = test_ffmpeg_slideshow()
    print(f"\nFinal result: {result}")
