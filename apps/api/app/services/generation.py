"""
Content Generation Service
Generate AI content using trained Actor Packs

Features:
- Face generation using trained LoRA models
- Voice synthesis using ElevenLabs
- Job queue for async processing
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

import httpx
import structlog

from app.core.config import settings
from app.core.resilience import CircuitBreaker, CircuitBreakerConfig
from app.services.storage import StorageService

logger = structlog.get_logger()

# Circuit breakers
_replicate_circuit = CircuitBreaker(
    "replicate_gen",
    CircuitBreakerConfig(failure_threshold=3, timeout=60.0, success_threshold=2)
)
_elevenlabs_circuit = CircuitBreaker(
    "elevenlabs_gen",
    CircuitBreakerConfig(failure_threshold=3, timeout=60.0, success_threshold=2)
)

# Thread pool for sync operations
_executor = ThreadPoolExecutor(max_workers=4)

# Timeout configuration - from settings
GENERATION_TIMEOUT = settings.GENERATION_TIMEOUT


class GenerationService:
    """
    Service for generating AI content using Actor Packs.

    Supports:
    - Face image generation (using trained LoRA)
    - Voice synthesis (using ElevenLabs cloned voice)
    - Motion video (future)
    """

    def __init__(self):
        self.storage = StorageService()

    async def generate_face_image(
        self,
        lora_model_url: str,
        prompt: str,
        negative_prompt: str = "",
        num_outputs: int = 1,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 30,
    ) -> Dict:
        """
        Generate face image using trained LoRA model.

        Uses Replicate's SDXL with LoRA for face generation.
        """
        if not settings.REPLICATE_API_TOKEN:
            raise Exception("Replicate API not configured")

        if not _replicate_circuit.can_execute():
            raise Exception("Replicate service temporarily unavailable")

        try:
            import replicate
        except ImportError:
            raise Exception("replicate package not installed")

        try:
            loop = asyncio.get_event_loop()

            def run_generation():
                client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)

                # Use SDXL with LoRA weights
                output = client.run(
                    "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                    input={
                        "prompt": f"photo of a person, {prompt}, high quality, detailed face, 8k",
                        "negative_prompt": f"blurry, low quality, distorted, {negative_prompt}",
                        "num_outputs": num_outputs,
                        "guidance_scale": guidance_scale,
                        "num_inference_steps": num_inference_steps,
                        "lora_scale": 0.8,
                        "lora_url": lora_model_url,
                    }
                )
                return output

            output = await loop.run_in_executor(_executor, run_generation)
            _replicate_circuit.record_success()

            # Output is a list of image URLs
            image_urls = list(output) if output else []

            # Download and store images
            stored_urls = []
            async with httpx.AsyncClient(timeout=60.0) as client:
                for i, url in enumerate(image_urls):
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            key = f"generated/{uuid.uuid4().hex}/face_{i}.png"
                            stored_url = await self.storage.upload_file(
                                file_bytes=response.content,
                                filename=key,
                                content_type="image/png",
                            )
                            stored_urls.append(stored_url)
                    except Exception as e:
                        logger.warning(f"Failed to store generated image: {e}")

            return {
                "status": "completed",
                "type": "face",
                "outputs": stored_urls or image_urls,
                "count": len(stored_urls or image_urls),
            }

        except Exception as e:
            _replicate_circuit.record_failure()
            logger.error(f"Face generation failed: {e}")
            raise

    async def generate_voice(
        self,
        voice_id: str,
        text: str,
        voice_provider: str = "elevenlabs",
        model_id: str = "eleven_multilingual_v2",
    ) -> Dict:
        """
        Generate voice using cloned voice model.

        Supports ElevenLabs and XTTS providers.
        """
        if voice_provider == "elevenlabs":
            return await self._generate_voice_elevenlabs(voice_id, text, model_id)
        elif voice_provider == "xtts":
            return await self._generate_voice_xtts(voice_id, text)
        else:
            raise Exception(f"Unknown voice provider: {voice_provider}")

    async def _generate_voice_elevenlabs(
        self,
        voice_id: str,
        text: str,
        model_id: str = "eleven_multilingual_v2",
    ) -> Dict:
        """Generate voice using ElevenLabs API"""
        if not settings.ELEVENLABS_API_KEY:
            raise Exception("ElevenLabs API not configured")

        if not _elevenlabs_circuit.can_execute():
            raise Exception("ElevenLabs service temporarily unavailable")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": settings.ELEVENLABS_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": model_id,
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        }
                    }
                )

                if response.status_code == 200:
                    _elevenlabs_circuit.record_success()

                    # Store audio file
                    key = f"generated/{uuid.uuid4().hex}/voice.mp3"
                    stored_url = await self.storage.upload_file(
                        file_bytes=response.content,
                        filename=key,
                        content_type="audio/mpeg",
                    )

                    return {
                        "status": "completed",
                        "type": "voice",
                        "output_url": stored_url,
                        "duration_estimate": len(text) / 15,  # ~15 chars per second
                    }
                else:
                    _elevenlabs_circuit.record_failure()
                    raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

        except Exception as e:
            _elevenlabs_circuit.record_failure()
            logger.error(f"Voice generation failed: {e}")
            raise

    async def _generate_voice_xtts(
        self,
        reference_audio_key: str,
        text: str,
    ) -> Dict:
        """Generate voice using XTTS via Replicate"""
        if not settings.REPLICATE_API_TOKEN:
            raise Exception("Replicate API not configured")

        try:
            import replicate
        except ImportError:
            raise Exception("replicate package not installed")

        # Get presigned URL for reference audio
        reference_url = await self.storage.generate_presigned_url(
            bucket=settings.S3_BUCKET_UPLOADS,
            key=reference_audio_key,
            expires_in=3600,
        )

        try:
            loop = asyncio.get_event_loop()

            def run_xtts():
                client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
                output = client.run(
                    "lucataco/xtts-v2:684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e",
                    input={
                        "speaker_wav": reference_url,
                        "text": text,
                        "language": "en",
                    }
                )
                return output

            output = await loop.run_in_executor(_executor, run_xtts)

            # Output is an audio URL
            if output:
                # Download and store
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(output)
                    if response.status_code == 200:
                        key = f"generated/{uuid.uuid4().hex}/voice.wav"
                        stored_url = await self.storage.upload_file(
                            file_bytes=response.content,
                            filename=key,
                            content_type="audio/wav",
                        )
                        return {
                            "status": "completed",
                            "type": "voice",
                            "output_url": stored_url,
                        }

            raise Exception("XTTS returned no output")

        except Exception as e:
            logger.error(f"XTTS generation failed: {e}")
            raise


# Singleton instance
_generation_service: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
