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


def test_single_image_to_video(image_path: str, output_path: str, duration: float = 3.0) -> dict:
    """
    Test different FFmpeg approaches to create video from a single image.
    Returns the method that worked.
    """
    methods = []

    # Method 1: Using lavfi color source + overlay (most reliable)
    method1_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1920x1080:d={duration}:r=24",
        "-i", image_path,
        "-filter_complex", "[0:v][1:v]overlay=(W-w)/2:(H-h)/2",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        output_path,
    ]
    methods.append(("lavfi_overlay", method1_cmd))

    # Method 2: Using image2 with framerate
    method2_cmd = [
        "ffmpeg", "-y",
        "-framerate", "24",
        "-t", str(duration),
        "-i", image_path,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-vf", "fps=24",
        output_path,
    ]
    methods.append(("image2_framerate", method2_cmd))

    # Method 3: Using loop with -t
    method3_cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-r", "24",
        output_path,
    ]
    methods.append(("loop_t", method3_cmd))

    # Method 4: Using movie filter
    method4_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"movie={image_path}:loop=0,setpts=N/24/TB,trim=duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        output_path,
    ]
    methods.append(("movie_filter", method4_cmd))

    results = []
    for name, cmd in methods:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                results.append({
                    "method": name,
                    "success": True,
                    "file_size": os.path.getsize(output_path),
                })
                # Clean up for next test
                os.remove(output_path)
            else:
                results.append({
                    "method": name,
                    "success": False,
                    "error": result.stderr[-500:] if result.stderr else "Empty output",
                })
        except Exception as e:
            results.append({
                "method": name,
                "success": False,
                "error": str(e),
            })

    return {"methods_tested": results}


def test_basic_ffmpeg() -> dict:
    """Test if FFmpeg can create any video at all using testsrc."""
    results = []

    with tempfile.TemporaryDirectory() as temp_dir:
        # Test 1: Very short duration with libx264
        output1 = os.path.join(temp_dir, "test1.mp4")
        cmd1 = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=0.5:size=320x240:rate=10",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            output1,
        ]
        r1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=30)
        results.append({
            "test": "libx264_short",
            "success": r1.returncode == 0 and os.path.exists(output1) and os.path.getsize(output1) > 100,
            "file_size": os.path.getsize(output1) if os.path.exists(output1) else 0,
            "stderr_tail": r1.stderr[-200:] if r1.stderr else "",
        })

        # Test 2: Using mpeg4 codec (simpler)
        output2 = os.path.join(temp_dir, "test2.mp4")
        cmd2 = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=0.5:size=320x240:rate=10",
            "-c:v", "mpeg4",
            "-q:v", "5",
            output2,
        ]
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
        results.append({
            "test": "mpeg4_short",
            "success": r2.returncode == 0 and os.path.exists(output2) and os.path.getsize(output2) > 100,
            "file_size": os.path.getsize(output2) if os.path.exists(output2) else 0,
            "stderr_tail": r2.stderr[-200:] if r2.stderr else "",
        })

        # Test 3: Using rawvideo (no encoding)
        output3 = os.path.join(temp_dir, "test3.yuv")
        cmd3 = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=0.1:size=320x240:rate=10",
            "-c:v", "rawvideo",
            "-pix_fmt", "yuv420p",
            output3,
        ]
        r3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=30)
        results.append({
            "test": "rawvideo",
            "success": r3.returncode == 0 and os.path.exists(output3) and os.path.getsize(output3) > 100,
            "file_size": os.path.getsize(output3) if os.path.exists(output3) else 0,
            "stderr_tail": r3.stderr[-200:] if r3.stderr else "",
        })

        # Test 4: JPEG image input with loop
        img_test = os.path.join(temp_dir, "test_img.jpg")
        output4 = os.path.join(temp_dir, "test4.mp4")
        # Create a simple test image
        from PIL import Image as PILImage
        test_img = PILImage.new("RGB", (320, 240), (255, 0, 0))
        test_img.save(img_test, "JPEG", quality=95)

        cmd4 = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", "10",
            "-i", img_test,
            "-t", "0.5",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            output4,
        ]
        r4 = subprocess.run(cmd4, capture_output=True, text=True, timeout=30)
        results.append({
            "test": "jpeg_loop",
            "success": r4.returncode == 0 and os.path.exists(output4) and os.path.getsize(output4) > 100,
            "file_size": os.path.getsize(output4) if os.path.exists(output4) else 0,
            "stderr_tail": r4.stderr[-300:] if r4.stderr else "",
            "img_size": os.path.getsize(img_test),
            "cmd": " ".join(cmd4),
        })

        # Test 5: JPEG image input WITHOUT loop (single frame)
        output5 = os.path.join(temp_dir, "test5.mp4")
        cmd5 = [
            "ffmpeg", "-y",
            "-i", img_test,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            output5,
        ]
        r5 = subprocess.run(cmd5, capture_output=True, text=True, timeout=30)
        results.append({
            "test": "jpeg_single_frame",
            "success": r5.returncode == 0 and os.path.exists(output5) and os.path.getsize(output5) > 100,
            "file_size": os.path.getsize(output5) if os.path.exists(output5) else 0,
            "stderr_tail": r5.stderr[-300:] if r5.stderr else "",
        })

        # Test 6: Get FFmpeg version
        version_result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        version_info = version_result.stdout.split("\n")[0] if version_result.stdout else "unknown"

    return {
        "tests": results,
        "ffmpeg_version": version_info,
        "any_success": any(r["success"] for r in results),
    }


def test_ffmpeg_slideshow() -> dict:
    """
    Test the full create_slideshow function with multiple images.

    Returns:
        Dict with test results
    """
    from app.utils.video import create_slideshow

    # First test basic FFmpeg
    basic_test = test_basic_ffmpeg()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test images
        image_paths = create_test_images(temp_dir, count=3)
        output_path = os.path.join(temp_dir, "test_video.mp4")

        # Create silent audio (9 seconds, 3 per image)
        audio_path = os.path.join(temp_dir, "test_audio.aac")
        create_silent_audio(audio_path, duration=9.0)

        try:
            # Run the actual create_slideshow function
            result = create_slideshow(
                image_paths=image_paths,
                audio_path=audio_path,
                output_path=output_path,
            )

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return {
                    "success": True,
                    "basic_ffmpeg_test": basic_test,
                    "duration_seconds": result["duration_seconds"],
                    "file_size_bytes": result["file_size_bytes"],
                    "message": "FFmpeg slideshow creation working correctly!",
                }
            else:
                return {
                    "success": False,
                    "basic_ffmpeg_test": basic_test,
                    "message": "Video file was not created or is empty",
                }

        except Exception as e:
            return {
                "success": False,
                "basic_ffmpeg_test": basic_test,
                "error": str(e),
                "message": "FFmpeg slideshow creation failed",
            }


if __name__ == "__main__":
    result = test_ffmpeg_slideshow()
    print(f"\nFinal result: {result}")
