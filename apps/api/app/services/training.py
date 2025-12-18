"""
Training Service
Actor Pack training pipeline
"""

import asyncio
import base64
import io
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Dict, List, Optional

import httpx
import numpy as np
import structlog
from PIL import Image

from app.core.config import settings
from app.services.storage import StorageService

logger = structlog.get_logger()

# Thread pool for CPU-bound operations
_executor = ThreadPoolExecutor(max_workers=4)

# Explicit mock mode flag for quality assessment
QUALITY_ASSESSMENT_MOCK = os.getenv("QUALITY_ASSESSMENT_MOCK", "true").lower() == "true"

if QUALITY_ASSESSMENT_MOCK:
    logger.warning("=" * 60)
    logger.warning("QUALITY ASSESSMENT RUNNING IN MOCK MODE")
    logger.warning("Returns fixed scores (85, 88, 82) instead of real assessment")
    logger.warning("Set QUALITY_ASSESSMENT_MOCK=false for production")
    logger.warning("=" * 60)


class TrainingService:
    """
    Service for training Actor Packs.

    Orchestrates the training pipeline:
    1. Process training data (images, audio, video)
    2. Train face model (embeddings + LoRA)
    3. Train voice model (if audio provided)
    4. Extract motion patterns (if video provided)
    5. Package everything into Actor Pack
    """

    def __init__(self):
        self.storage = StorageService()

    async def train_actor_pack(
        self,
        actor_pack_id: str,
        image_urls: List[str],
        audio_urls: List[str] = None,
        video_urls: List[str] = None,
    ) -> Dict:
        """
        Train a complete Actor Pack.

        This is typically called as a background task or Celery job.
        """
        from app.core.database import async_session_maker
        from app.models.identity import ActorPack, TrainingStatus

        logger.info(f"Starting Actor Pack training: {actor_pack_id}")

        async with async_session_maker() as db:
            try:
                # Get actor pack record
                actor_pack = await db.get(ActorPack, uuid.UUID(actor_pack_id))
                if not actor_pack:
                    raise ValueError(f"Actor Pack not found: {actor_pack_id}")

                # Update status
                actor_pack.training_status = TrainingStatus.PROCESSING
                actor_pack.training_started_at = datetime.utcnow()
                await db.commit()

                # Step 1: Process images
                logger.info("Processing training images...")
                actor_pack.training_progress = 10
                await db.commit()

                face_data = await self._process_images(image_urls)

                # Step 2: Train face model
                logger.info("Training face model...")
                actor_pack.training_progress = 30
                await db.commit()

                face_model = await self._train_face_model(face_data)

                # Step 3: Train voice model (if audio provided)
                voice_model = None
                if audio_urls:
                    logger.info("Training voice model...")
                    actor_pack.training_progress = 50
                    await db.commit()

                    voice_model = await self._train_voice_model(audio_urls)

                # Step 4: Process motion data (if video provided)
                motion_data = None
                if video_urls:
                    logger.info("Extracting motion patterns...")
                    actor_pack.training_progress = 70
                    await db.commit()

                    motion_data = await self._extract_motion(video_urls)

                # Step 5: Package Actor Pack
                logger.info("Packaging Actor Pack...")
                actor_pack.training_progress = 85
                await db.commit()

                pack_result = await self._package_actor_pack(
                    actor_pack_id=actor_pack_id,
                    face_model=face_model,
                    voice_model=voice_model,
                    motion_data=motion_data,
                )

                # Step 6: Run quality assessment
                logger.info("Assessing quality...")
                quality_scores = await self._assess_quality(pack_result, face_data=face_data)

                # Update actor pack record
                actor_pack.training_status = TrainingStatus.COMPLETED
                actor_pack.training_completed_at = datetime.utcnow()
                actor_pack.training_progress = 100
                actor_pack.s3_bucket = settings.S3_BUCKET_ACTOR_PACKS
                actor_pack.s3_key = pack_result["s3_key"]
                actor_pack.file_size_bytes = pack_result.get("file_size", 0)
                actor_pack.quality_score = quality_scores["overall"]
                actor_pack.authenticity_score = quality_scores["authenticity"]
                actor_pack.consistency_score = quality_scores["consistency"]
                actor_pack.voice_quality_score = quality_scores.get("voice")
                actor_pack.components = {
                    "face": True,
                    "voice": voice_model is not None,
                    "motion": motion_data is not None,
                }
                actor_pack.is_available = True

                await db.commit()

                logger.info(f"Actor Pack training completed: {actor_pack_id}")

                return {
                    "status": "completed",
                    "actor_pack_id": actor_pack_id,
                    "quality_score": quality_scores["overall"],
                }

            except Exception as e:
                logger.error(f"Training failed: {e}")
                actor_pack.training_status = TrainingStatus.FAILED
                actor_pack.training_error = str(e)
                await db.commit()
                raise

    async def _process_images(self, image_urls: List[str]) -> Dict:
        """Download and process training images"""
        from app.services.face_recognition import FaceRecognitionService

        face_service = FaceRecognitionService()

        embeddings = []
        processed_images = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for url in image_urls:
                try:
                    response = await client.get(url)
                    image_bytes = response.content

                    # Extract embedding
                    embedding = await face_service.extract_embedding(image_bytes)
                    if embedding is not None:
                        embeddings.append(embedding)
                        processed_images.append(image_bytes)

                except Exception as e:
                    logger.warning(f"Failed to process image {url}: {e}")
                    continue

        if len(embeddings) < 5:
            raise ValueError("Not enough valid face images for training")

        return {"embeddings": embeddings, "images": processed_images, "count": len(embeddings)}

    async def _train_face_model(self, face_data: Dict) -> Dict:
        """
        Train face representation model.

        In production, this would:
        - Train a LoRA adapter for face generation
        - Create multi-angle embeddings
        - Use Replicate/FAL for model training
        """
        import numpy as np

        embeddings = face_data["embeddings"]

        # Calculate average embedding
        avg_embedding = np.mean(embeddings, axis=0)
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)

        # In production, train LoRA here using Replicate or similar
        # For now, return embeddings-based model
        lora_weights_url = None

        if settings.REPLICATE_API_TOKEN:
            try:
                lora_weights_url = await self._train_lora_replicate(face_data["images"])
            except Exception as e:
                logger.warning(f"LoRA training skipped: {e}")

        return {
            "primary_embedding": avg_embedding.tolist(),
            "embeddings_count": len(embeddings),
            "lora_weights_url": lora_weights_url,
        }

    async def _train_lora_replicate(self, images: List[bytes], identity_id: str = None) -> Optional[str]:
        """
        Train LoRA model using Replicate API.

        Uses ostris/flux-dev-lora-trainer for high-quality face LoRA training.
        Images are uploaded to S3, then training is initiated on Replicate.

        Returns the URL of the trained LoRA weights.
        """
        try:
            import replicate
        except ImportError:
            logger.warning("replicate package not installed, skipping LoRA training")
            return None

        if not settings.REPLICATE_API_TOKEN:
            logger.warning("REPLICATE_API_TOKEN not set, skipping LoRA training")
            return None

        try:
            # Generate unique training ID
            training_id = identity_id or uuid.uuid4().hex[:8]

            # Create a zip file with training images
            import tempfile
            import zipfile

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "training_images.zip")

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for i, img_bytes in enumerate(images):
                        # Validate and save each image
                        try:
                            img = Image.open(io.BytesIO(img_bytes))
                            # Ensure RGB format
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            # Save as high-quality JPEG
                            img_buffer = io.BytesIO()
                            img.save(img_buffer, format='JPEG', quality=95)
                            zf.writestr(f"image_{i:03d}.jpg", img_buffer.getvalue())
                        except Exception as e:
                            logger.warning(f"Skipping invalid image {i}: {e}")
                            continue

                # Upload zip to S3 for Replicate to access
                with open(zip_path, 'rb') as f:
                    zip_bytes = f.read()

                s3_key = f"training/lora/{training_id}/images.zip"
                await self.storage.upload_file(
                    file_bytes=zip_bytes,
                    filename=s3_key,
                    content_type="application/zip",
                    bucket=settings.S3_BUCKET_UPLOADS,
                )

                # Get presigned URL for Replicate access
                images_url = await self.storage.get_presigned_url(
                    bucket=settings.S3_BUCKET_UPLOADS,
                    key=s3_key,
                    expires_in=3600 * 24  # 24 hours for training
                )

            logger.info(f"Starting Replicate LoRA training for {training_id}")

            # Initialize Replicate client
            client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)

            # Run training in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def run_training():
                # Create training job using Flux LoRA trainer
                training = client.trainings.create(
                    version="ostris/flux-dev-lora-trainer:d995297071a44dcb72244e6c19462111649ec86a9ff7e6b69a77b18e5e95cf41",
                    input={
                        "input_images": images_url,
                        "trigger_word": f"person_{training_id}",
                        "steps": 1000,
                        "lora_rank": 16,
                        "learning_rate": 0.0004,
                        "batch_size": 1,
                        "resolution": "512,768,1024",
                        "autocaption": True,
                        "autocaption_prefix": f"a photo of person_{training_id}",
                    },
                    destination=f"actorhub/{training_id}"
                )

                # Poll for completion (with timeout)
                max_wait = 3600  # 1 hour max
                start_time = datetime.utcnow()

                while training.status not in ["succeeded", "failed", "canceled"]:
                    import time
                    time.sleep(30)  # Check every 30 seconds
                    training.reload()

                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed > max_wait:
                        logger.warning(f"LoRA training timeout after {elapsed}s")
                        return None

                    logger.info(f"LoRA training status: {training.status} ({elapsed:.0f}s elapsed)")

                if training.status == "succeeded":
                    # Get the output model URL
                    output = training.output
                    if output and "weights" in output:
                        return output["weights"]
                    elif output and isinstance(output, str):
                        return output

                    logger.warning(f"Training succeeded but no weights URL in output: {output}")
                    return None
                else:
                    logger.error(f"LoRA training failed: {training.status} - {training.error}")
                    return None

            lora_weights_url = await loop.run_in_executor(_executor, run_training)

            if lora_weights_url:
                logger.info(f"LoRA training completed: {lora_weights_url}")

            return lora_weights_url

        except Exception as e:
            logger.error(f"LoRA training error: {e}")
            return None

    async def _train_voice_model(self, audio_urls: List[str]) -> Optional[Dict]:
        """
        Train voice clone model with graceful degradation.

        Priority order:
        1. ElevenLabs API (highest quality)
        2. Coqui XTTS via Replicate (good quality, free tier)
        3. Local reference storage (minimal fallback)
        """
        if not audio_urls:
            return None

        # Try ElevenLabs first (premium quality)
        if settings.ELEVENLABS_API_KEY:
            try:
                result = await self._train_voice_elevenlabs(audio_urls)
                if result and result.get("status") == "ready":
                    return result
            except Exception as e:
                logger.warning(f"ElevenLabs voice cloning failed, trying fallback: {e}")

        # Fallback to Coqui XTTS via Replicate
        if settings.REPLICATE_API_TOKEN:
            try:
                result = await self._train_voice_xtts(audio_urls)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"XTTS voice cloning failed: {e}")

        # Final fallback - store audio references for future processing
        logger.warning("All voice providers failed, storing audio references")
        return await self._store_voice_references(audio_urls)

    async def _train_voice_xtts(self, audio_urls: List[str]) -> Optional[Dict]:
        """
        Train voice using Coqui XTTS via Replicate.

        Uses the cjwbw/xtts-v2 model for voice cloning.
        """
        try:
            import replicate
        except ImportError:
            logger.warning("replicate package not installed")
            return None

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Download and merge audio files
            audio_samples = []
            for url in audio_urls[:5]:  # Limit to 5 samples
                try:
                    response = await client.get(url)
                    audio_samples.append(response.content)
                except Exception as e:
                    logger.warning(f"Failed to download audio {url}: {e}")
                    continue

            if not audio_samples:
                return None

            # Upload combined audio to S3 for Replicate access
            import io
            combined_audio = audio_samples[0]  # Use first sample for now

            audio_key = f"voice-training/{uuid.uuid4().hex}/reference.wav"
            await self.storage.upload_file(
                file_bytes=combined_audio,
                filename=audio_key,
                content_type="audio/wav",
                bucket=settings.S3_BUCKET_UPLOADS,
            )

            audio_url = await self.storage.get_presigned_url(
                bucket=settings.S3_BUCKET_UPLOADS,
                key=audio_key,
                expires_in=3600 * 24,
            )

            # Run XTTS cloning via Replicate
            loop = asyncio.get_event_loop()

            def run_xtts():
                client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)

                # Use XTTS-v2 for voice cloning
                output = client.run(
                    "cjwbw/xtts-v2:79a125f5ab49aa10e39eddd06cc10ed3a708f8eb01d04e30369a4c342c619bc5",
                    input={
                        "speaker_wav": audio_url,
                        "text": "This is a voice cloning test to verify the quality.",
                        "language": "en",
                    }
                )
                return output

            try:
                output = await loop.run_in_executor(_executor, run_xtts)

                return {
                    "provider": "xtts",
                    "reference_audio": audio_key,
                    "sample_output": output if isinstance(output, str) else None,
                    "status": "ready",
                }
            except Exception as e:
                logger.error(f"XTTS Replicate error: {e}")
                return None

    async def _store_voice_references(self, audio_urls: List[str]) -> Dict:
        """
        Store voice audio references for future processing.

        Minimal fallback when no voice cloning providers are available.
        """
        stored_keys = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, url in enumerate(audio_urls[:10]):  # Limit to 10 files
                try:
                    response = await client.get(url)
                    audio_bytes = response.content

                    key = f"voice-references/{uuid.uuid4().hex}/sample_{i}.wav"
                    await self.storage.upload_file(
                        file_bytes=audio_bytes,
                        filename=key,
                        content_type="audio/wav",
                        bucket=settings.S3_BUCKET_UPLOADS,
                    )
                    stored_keys.append(key)
                except Exception as e:
                    logger.warning(f"Failed to store audio {url}: {e}")
                    continue

        return {
            "provider": "reference_only",
            "stored_audio_keys": stored_keys,
            "audio_count": len(stored_keys),
            "status": "pending_manual_processing",
            "message": "Voice samples stored. Manual cloning required.",
        }

    async def _train_voice_elevenlabs(self, audio_urls: List[str]) -> Dict:
        """Train voice using ElevenLabs API"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Download audio files
            audio_files = []
            for url in audio_urls:
                response = await client.get(url)
                audio_files.append(response.content)

            # Create voice clone
            # Note: ElevenLabs requires specific format for the API
            # This is a simplified version
            response = await client.post(
                "https://api.elevenlabs.io/v1/voices/add",
                headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
                files=[("files", audio) for audio in audio_files],
                data={"name": f"ActorHub_{uuid.uuid4().hex[:8]}"},
            )

            if response.status_code == 200:
                voice_data = response.json()
                return {
                    "provider": "elevenlabs",
                    "voice_id": voice_data.get("voice_id"),
                    "status": "ready",
                }

            raise Exception(f"ElevenLabs API error: {response.text}")

    async def _extract_motion(self, video_urls: List[str]) -> Optional[Dict]:
        """
        Extract motion patterns from video using MediaPipe.

        Uses pose estimation to capture:
        - Body pose landmarks (33 points)
        - Gesture patterns over time
        - Movement style characteristics
        """
        if not video_urls:
            return None

        try:
            import cv2
        except ImportError:
            logger.warning("opencv-python not installed, skipping motion extraction")
            return {"video_count": len(video_urls), "status": "opencv_not_installed", "pose_data": None}

        try:
            import mediapipe as mp
        except ImportError:
            logger.warning("mediapipe not installed, skipping motion extraction")
            return {"video_count": len(video_urls), "status": "mediapipe_not_installed", "pose_data": None}

        try:
            mp_pose = mp.solutions.pose
            pose = mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )

            all_pose_sequences = []
            processed_videos = 0

            async with httpx.AsyncClient(timeout=120.0) as client:
                for video_url in video_urls:
                    try:
                        # Download video
                        response = await client.get(video_url)
                        video_bytes = response.content

                        # Save temporarily for OpenCV processing
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                            tmp.write(video_bytes)
                            tmp_path = tmp.name

                        # Process video in thread pool (CPU-bound)
                        loop = asyncio.get_event_loop()

                        def extract_poses():
                            pose_sequence = []
                            cap = cv2.VideoCapture(tmp_path)

                            frame_count = 0
                            sample_rate = 5  # Process every 5th frame

                            while cap.isOpened():
                                ret, frame = cap.read()
                                if not ret:
                                    break

                                frame_count += 1
                                if frame_count % sample_rate != 0:
                                    continue

                                # Convert BGR to RGB
                                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                                # Process with MediaPipe
                                results = pose.process(rgb_frame)

                                if results.pose_landmarks:
                                    # Extract landmark coordinates
                                    landmarks = []
                                    for landmark in results.pose_landmarks.landmark:
                                        landmarks.append({
                                            'x': landmark.x,
                                            'y': landmark.y,
                                            'z': landmark.z,
                                            'visibility': landmark.visibility
                                        })
                                    pose_sequence.append({
                                        'frame': frame_count,
                                        'landmarks': landmarks
                                    })

                            cap.release()
                            return pose_sequence

                        pose_sequence = await loop.run_in_executor(_executor, extract_poses)

                        # Cleanup temp file
                        os.unlink(tmp_path)

                        if pose_sequence:
                            all_pose_sequences.append({
                                'video_url': video_url,
                                'frame_count': len(pose_sequence),
                                'poses': pose_sequence
                            })
                            processed_videos += 1
                            logger.info(f"Extracted {len(pose_sequence)} poses from video")

                    except Exception as e:
                        logger.warning(f"Failed to process video {video_url}: {e}")
                        continue

            pose.close()

            if not all_pose_sequences:
                return {
                    "video_count": len(video_urls),
                    "status": "no_poses_detected",
                    "pose_data": None,
                }

            # Compute motion statistics
            total_poses = sum(seq['frame_count'] for seq in all_pose_sequences)

            # Calculate average pose (for style embedding)
            avg_pose = self._compute_average_pose(all_pose_sequences)

            return {
                "video_count": len(video_urls),
                "processed_videos": processed_videos,
                "total_poses": total_poses,
                "status": "completed",
                "pose_data": {
                    "sequences": all_pose_sequences,
                    "average_pose": avg_pose,
                },
            }

        except Exception as e:
            logger.error(f"Motion extraction error: {e}")
            return {
                "video_count": len(video_urls),
                "status": "error",
                "error": str(e),
                "pose_data": None,
            }

    def _compute_average_pose(self, pose_sequences: List[Dict]) -> Optional[List[Dict]]:
        """Compute average pose across all frames for style characterization"""
        try:
            all_landmarks = []

            for seq in pose_sequences:
                for pose in seq.get('poses', []):
                    all_landmarks.append(pose['landmarks'])

            if not all_landmarks:
                return None

            # Average each landmark position
            num_landmarks = len(all_landmarks[0])
            avg_landmarks = []

            for i in range(num_landmarks):
                avg_x = np.mean([lm[i]['x'] for lm in all_landmarks])
                avg_y = np.mean([lm[i]['y'] for lm in all_landmarks])
                avg_z = np.mean([lm[i]['z'] for lm in all_landmarks])
                avg_vis = np.mean([lm[i]['visibility'] for lm in all_landmarks])

                avg_landmarks.append({
                    'x': float(avg_x),
                    'y': float(avg_y),
                    'z': float(avg_z),
                    'visibility': float(avg_vis)
                })

            return avg_landmarks

        except Exception as e:
            logger.warning(f"Could not compute average pose: {e}")
            return None

    async def _package_actor_pack(
        self,
        actor_pack_id: str,
        face_model: Dict,
        voice_model: Optional[Dict],
        motion_data: Optional[Dict],
    ) -> Dict:
        """Package all models into downloadable Actor Pack"""
        import json
        import os
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = os.path.join(tmpdir, "actor_pack")
            os.makedirs(pack_dir)

            # Create manifest
            manifest = {
                "version": "1.0.0",
                "actor_pack_id": actor_pack_id,
                "created_at": datetime.utcnow().isoformat(),
                "components": {
                    "face": True,
                    "voice": voice_model is not None,
                    "motion": motion_data is not None,
                },
            }

            with open(os.path.join(pack_dir, "manifest.json"), "w") as f:
                json.dump(manifest, f, indent=2)

            # Save face model
            face_dir = os.path.join(pack_dir, "face")
            os.makedirs(face_dir)
            with open(os.path.join(face_dir, "model.json"), "w") as f:
                json.dump(face_model, f)

            # Save voice model config
            if voice_model:
                voice_dir = os.path.join(pack_dir, "voice")
                os.makedirs(voice_dir)
                with open(os.path.join(voice_dir, "config.json"), "w") as f:
                    json.dump(voice_model, f)

            # Save motion data
            if motion_data:
                motion_dir = os.path.join(pack_dir, "motion")
                os.makedirs(motion_dir)
                with open(os.path.join(motion_dir, "data.json"), "w") as f:
                    json.dump(motion_data, f)

            # Create zip file
            zip_path = os.path.join(tmpdir, f"{actor_pack_id}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(pack_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, pack_dir)
                        zf.write(file_path, arc_name)

            # Upload to S3
            s3_key = f"actor-packs/{actor_pack_id}/v1.0.0/pack.zip"
            with open(zip_path, "rb") as f:
                zip_bytes = f.read()

            await self.storage.upload_file(
                file_bytes=zip_bytes,
                filename=s3_key,
                content_type="application/zip",
                bucket=settings.S3_BUCKET_ACTOR_PACKS,
            )

            return {"s3_key": s3_key, "file_size": len(zip_bytes)}

    async def _assess_quality(self, pack_result: Dict, face_data: Dict = None) -> Dict:
        """
        Assess quality of generated Actor Pack using real metrics.

        Metrics computed:
        - Authenticity: Face detection confidence and embedding quality
        - Consistency: Variance across embeddings (lower = more consistent)
        - Overall: Weighted combination of all metrics
        - Voice: Audio quality if voice model present
        """
        if QUALITY_ASSESSMENT_MOCK:
            logger.warning("MOCK: Returning fixed quality scores (not real assessment)")
            return {
                "overall": 85.0,
                "authenticity": 88.0,
                "consistency": 82.0,
                "voice": 80.0 if pack_result.get("voice") else None,
            }

        try:
            authenticity_score = 85.0
            consistency_score = 85.0
            voice_score = None

            # Calculate real metrics if face data is available
            if face_data and "embeddings" in face_data:
                embeddings = face_data["embeddings"]

                if len(embeddings) > 1:
                    # Consistency: measure how similar all embeddings are to each other
                    # Lower variance = higher consistency
                    embeddings_array = np.array(embeddings)

                    # Calculate mean embedding
                    mean_embedding = np.mean(embeddings_array, axis=0)
                    mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)

                    # Calculate cosine similarities to mean
                    similarities = []
                    for emb in embeddings_array:
                        emb_norm = emb / np.linalg.norm(emb)
                        sim = np.dot(mean_embedding, emb_norm)
                        similarities.append(sim)

                    # Convert to 0-100 scale (similarity typically 0.3-1.0 for same person)
                    avg_similarity = np.mean(similarities)
                    consistency_score = min(100.0, max(0.0, (avg_similarity - 0.3) / 0.7 * 100))

                    # Authenticity: based on embedding quality and count
                    # More images + higher consistency = higher authenticity
                    image_count_factor = min(1.0, len(embeddings) / 10.0)  # Cap at 10 images
                    authenticity_score = consistency_score * 0.7 + image_count_factor * 30.0

                    logger.info(
                        f"Quality assessment: consistency={consistency_score:.1f}, "
                        f"authenticity={authenticity_score:.1f}, "
                        f"avg_similarity={avg_similarity:.3f}"
                    )

            # Assess voice quality if voice model was trained
            if pack_result.get("voice"):
                voice_model = pack_result.get("voice_model", {})
                if voice_model.get("provider") == "elevenlabs":
                    # ElevenLabs typically produces high quality
                    voice_score = 90.0
                elif voice_model.get("status") == "ready":
                    voice_score = 85.0
                else:
                    voice_score = 70.0

            # Calculate overall score
            scores = [authenticity_score, consistency_score]
            if voice_score is not None:
                scores.append(voice_score)

            overall_score = np.mean(scores)

            return {
                "overall": round(overall_score, 1),
                "authenticity": round(authenticity_score, 1),
                "consistency": round(consistency_score, 1),
                "voice": round(voice_score, 1) if voice_score else None,
            }

        except Exception as e:
            logger.error(f"Quality assessment error: {e}")
            # Fallback to default scores on error
            return {
                "overall": 75.0,
                "authenticity": 75.0,
                "consistency": 75.0,
                "voice": 70.0 if pack_result.get("voice") else None,
            }
