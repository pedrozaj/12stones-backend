"""ElevenLabs API utilities for voice synthesis."""

from elevenlabs import ElevenLabs

from app.config import get_settings

settings = get_settings()

# Default voice ID - "Adam" from ElevenLabs
# TODO: Implement actual voice cloning to use user's custom voice
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam


def synthesize_speech(text: str, voice_id: str | None = None) -> bytes:
    """
    Generate speech audio from text using ElevenLabs.

    Args:
        text: The text to convert to speech
        voice_id: Optional ElevenLabs voice ID. Uses default if not provided.

    Returns:
        Audio bytes (MP3 format)
    """
    if not settings.elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY not configured")

    client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    # Use provided voice_id or fall back to default
    effective_voice_id = voice_id or DEFAULT_VOICE_ID

    # Generate audio using text-to-speech
    audio_generator = client.text_to_speech.convert(
        voice_id=effective_voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # Collect all chunks from the generator
    audio_bytes = b"".join(audio_generator)

    return audio_bytes


def get_available_voices() -> list[dict]:
    """
    Get list of available voices from ElevenLabs.

    Returns:
        List of voice objects with id, name, and other metadata
    """
    if not settings.elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY not configured")

    client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    voices = client.voices.get_all()

    return [
        {
            "id": voice.voice_id,
            "name": voice.name,
            "category": voice.category,
        }
        for voice in voices.voices
    ]
