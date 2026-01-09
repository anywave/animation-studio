"""
Digigami 3D Generation Service

Supports multiple 3D generation backends:
- Tripo3D API (best for stylized characters)
- Meshy API (alternative)
- Local InstantMesh (future - requires GPU)

Multi-view pipeline for character reference sheets.
"""

import asyncio
import aiohttp
import base64
import io
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class Generation3DBackend(Enum):
    """Available 3D generation backends"""
    TRIPO3D = "tripo3d"
    MESHY = "meshy"
    MAKERGRID = "makergrid"  # Friend's platform - makergrid.ai
    LOCAL = "local"  # Future: InstantMesh/Wonder3D


class Generation3DStatus(Enum):
    """Status of 3D generation task"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Generation3DResult:
    """Result of 3D generation"""
    task_id: str
    status: Generation3DStatus
    progress: float = 0.0
    model_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    glb_data: Optional[bytes] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiViewInput:
    """Multi-view input for character generation"""
    front: Optional[Image.Image] = None
    side: Optional[Image.Image] = None
    back: Optional[Image.Image] = None
    front_3quarter: Optional[Image.Image] = None
    back_3quarter: Optional[Image.Image] = None


class Tripo3DClient:
    """Client for Tripo3D API - optimized for anime/stylized characters"""

    BASE_URL = "https://api.tripo3d.ai/v2/openapi"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _image_to_base64(self, img: Image.Image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string"""
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def generate_from_image(
        self,
        image: Image.Image,
        model_type: str = "default",
        texture_quality: str = "high"
    ) -> str:
        """Start single-image 3D generation, returns task_id"""
        session = await self._get_session()

        # Convert image to base64
        image_b64 = self._image_to_base64(image)

        payload = {
            "type": "image_to_model",
            "file": {
                "type": "png",
                "data": image_b64
            },
            "model_version": model_type,
            "texture_quality": texture_quality
        }

        async with session.post(f"{self.BASE_URL}/task", json=payload) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Tripo3D API error: {error}")

            result = await resp.json()
            return result["data"]["task_id"]

    async def generate_from_multiview(
        self,
        views: MultiViewInput,
        model_type: str = "default"
    ) -> str:
        """Start multi-view 3D generation, returns task_id"""
        session = await self._get_session()

        # Build multi-view payload
        images = {}
        if views.front:
            images["front"] = self._image_to_base64(views.front)
        if views.side:
            images["left"] = self._image_to_base64(views.side)
        if views.back:
            images["back"] = self._image_to_base64(views.back)

        if len(images) < 2:
            raise ValueError("Multi-view generation requires at least 2 views")

        payload = {
            "type": "multiview_to_model",
            "files": [
                {"type": "png", "data": data, "view": view}
                for view, data in images.items()
            ],
            "model_version": model_type
        }

        async with session.post(f"{self.BASE_URL}/task", json=payload) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Tripo3D multiview API error: {error}")

            result = await resp.json()
            return result["data"]["task_id"]

    async def get_task_status(self, task_id: str) -> Generation3DResult:
        """Check task status and get result"""
        session = await self._get_session()

        async with session.get(f"{self.BASE_URL}/task/{task_id}") as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Tripo3D status error: {error}")

            data = (await resp.json())["data"]
            status_map = {
                "queued": Generation3DStatus.PENDING,
                "running": Generation3DStatus.PROCESSING,
                "success": Generation3DStatus.COMPLETED,
                "failed": Generation3DStatus.FAILED
            }

            return Generation3DResult(
                task_id=task_id,
                status=status_map.get(data["status"], Generation3DStatus.PENDING),
                progress=data.get("progress", 0) * 100,
                model_url=data.get("output", {}).get("model"),
                thumbnail_url=data.get("output", {}).get("rendered_image"),
                error=data.get("error_message")
            )

    async def download_model(self, model_url: str) -> bytes:
        """Download GLB model from URL"""
        session = await self._get_session()

        async with session.get(model_url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download model: {resp.status}")
            return await resp.read()


class MakerGridClient:
    """
    Client for MakerGrid API - friend's platform at makergrid.ai

    Production API: https://makergrid.pythonanywhere.com
    Endpoints (from Blender plugin source):
    - POST /api/accounts/blender/login/ (username/password -> {access, refresh, user})
    - POST /api/makers/image-to-model/ (FormData with 'image' key)
    - POST /api/makers/check-task-status/{task_id}/ (poll for completion)
    - Model download: /media/{stored_path}
    """

    BASE_URL = "https://makergrid.pythonanywhere.com"

    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # MakerGrid uses Bearer token + optional refresh_token cookie
            cookies = {}
            if self.refresh_token:
                cookies["refresh_token"] = self.refresh_token

            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                cookies=cookies if cookies else None
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @staticmethod
    async def login(username: str, password: str) -> dict:
        """
        Login to MakerGrid and get access/refresh tokens.

        Returns:
            dict with 'access', 'refresh', and 'user' keys
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MakerGridClient.BASE_URL}/api/accounts/blender/login/",
                data={"username": username, "password": password}
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"MakerGrid login failed ({resp.status}): {error}")

                data = await resp.json()
                return {
                    "access": data.get("access"),
                    "refresh": data.get("refresh"),
                    "user": data.get("user", {})
                }

    async def generate_from_image(
        self,
        image: Image.Image,
        **kwargs  # Future: style, complexity, optimize_printing
    ) -> str:
        """Start image-to-3D generation, returns task_id"""
        session = await self._get_session()

        # Convert image to bytes for FormData upload
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        image_bytes = buffer.getvalue()

        # Create FormData with image
        data = aiohttp.FormData()
        data.add_field(
            "image",
            image_bytes,
            filename="input.png",
            content_type="image/png"
        )

        async with session.post(
            f"{self.BASE_URL}/api/makers/image-to-model/",
            data=data
        ) as resp:
            if resp.status not in (200, 201, 202):
                error = await resp.text()
                raise Exception(f"MakerGrid API error ({resp.status}): {error}")

            result = await resp.json()
            task_id = result.get("task_id") or result.get("id")

            if not task_id:
                raise Exception(f"No task_id in MakerGrid response: {result}")

            return task_id

    async def get_task_status(self, task_id: str) -> Generation3DResult:
        """Check task status and get result"""
        session = await self._get_session()

        # Endpoint from Blender plugin: /api/makers/check-task-status/{task_id}/
        async with session.post(
            f"{self.BASE_URL}/api/makers/check-task-status/{task_id}/",
            json={"task_id": task_id}
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"MakerGrid status error ({resp.status}): {error}")

            data = await resp.json()

            # Map MakerGrid status to our status
            mg_status = data.get("status", "").lower()
            status_map = {
                "pending": Generation3DStatus.PENDING,
                "queued": Generation3DStatus.PENDING,
                "processing": Generation3DStatus.PROCESSING,
                "running": Generation3DStatus.PROCESSING,
                "completed": Generation3DStatus.COMPLETED,
                "success": Generation3DStatus.COMPLETED,
                "failed": Generation3DStatus.FAILED,
                "error": Generation3DStatus.FAILED
            }

            status = status_map.get(mg_status, Generation3DStatus.PENDING)

            # Build model URL from stored_path
            stored_path = data.get("stored_path")
            model_url = f"{self.BASE_URL}/media/{stored_path}" if stored_path else None

            # Get thumbnail/preview
            thumbnail_url = data.get("preview_image_url")
            if thumbnail_url and not thumbnail_url.startswith("http"):
                thumbnail_url = f"{self.BASE_URL}{thumbnail_url}"

            return Generation3DResult(
                task_id=task_id,
                status=status,
                progress=data.get("progress", 0) if status == Generation3DStatus.PROCESSING else (100 if status == Generation3DStatus.COMPLETED else 0),
                model_url=model_url,
                thumbnail_url=thumbnail_url,
                error=data.get("error") or data.get("error_message"),
                metadata={
                    "color_video": data.get("color_video"),
                    "gaussian": data.get("gaussian"),
                    "stored_path": stored_path
                }
            )

    async def download_model(self, model_url: str) -> bytes:
        """Download GLB/OBJ model from MakerGrid"""
        session = await self._get_session()

        async with session.get(model_url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download model from MakerGrid: {resp.status}")
            return await resp.read()


class MeshyClient:
    """Client for Meshy API - alternative 3D generation backend"""

    BASE_URL = "https://api.meshy.ai/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def generate_from_image(
        self,
        image: Image.Image,
        art_style: str = "cartoon",
        topology: str = "quad"
    ) -> str:
        """Start image-to-3D generation, returns task_id"""
        session = await self._get_session()

        # Convert image to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        payload = {
            "image_url": f"data:image/png;base64,{image_b64}",
            "art_style": art_style,
            "topology": topology,
            "target_polycount": 30000
        }

        async with session.post(f"{self.BASE_URL}/image-to-3d", json=payload) as resp:
            if resp.status not in (200, 202):
                error = await resp.text()
                raise Exception(f"Meshy API error: {error}")

            result = await resp.json()
            return result["result"]

    async def get_task_status(self, task_id: str) -> Generation3DResult:
        """Check task status"""
        session = await self._get_session()

        async with session.get(f"{self.BASE_URL}/image-to-3d/{task_id}") as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Meshy status error: {error}")

            data = await resp.json()
            status_map = {
                "PENDING": Generation3DStatus.PENDING,
                "IN_PROGRESS": Generation3DStatus.PROCESSING,
                "SUCCEEDED": Generation3DStatus.COMPLETED,
                "FAILED": Generation3DStatus.FAILED
            }

            return Generation3DResult(
                task_id=task_id,
                status=status_map.get(data["status"], Generation3DStatus.PENDING),
                progress=data.get("progress", 0),
                model_url=data.get("model_urls", {}).get("glb"),
                thumbnail_url=data.get("thumbnail_url"),
                error=data.get("error_message")
            )

    async def download_model(self, model_url: str) -> bytes:
        """Download GLB model"""
        session = await self._get_session()
        async with session.get(model_url) as resp:
            return await resp.read()


class Generation3DService:
    """
    Main 3D generation service with multi-backend support.

    Handles:
    - Single image to 3D conversion
    - Multi-view character reconstruction
    - Progress tracking and callbacks
    - Model download and caching
    """

    def __init__(
        self,
        tripo3d_api_key: Optional[str] = None,
        meshy_api_key: Optional[str] = None,
        makergrid_token: Optional[str] = None,
        default_backend: Generation3DBackend = Generation3DBackend.TRIPO3D,
        output_dir: Optional[Path] = None
    ):
        self.tripo3d_client = Tripo3DClient(tripo3d_api_key) if tripo3d_api_key else None
        self.meshy_client = MeshyClient(meshy_api_key) if meshy_api_key else None
        self.makergrid_client = MakerGridClient(makergrid_token) if makergrid_token else None
        self.default_backend = default_backend
        self.output_dir = output_dir or Path("outputs/3d")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Active tasks tracking
        self._active_tasks: Dict[str, Dict[str, Any]] = {}

    async def close(self):
        """Cleanup resources"""
        if self.tripo3d_client:
            await self.tripo3d_client.close()
        if self.meshy_client:
            await self.meshy_client.close()
        if self.makergrid_client:
            await self.makergrid_client.close()

    def _get_client(self, backend: Optional[Generation3DBackend] = None):
        """Get appropriate client for backend"""
        backend = backend or self.default_backend

        if backend == Generation3DBackend.TRIPO3D:
            if not self.tripo3d_client:
                raise ValueError("Tripo3D API key not configured")
            return self.tripo3d_client
        elif backend == Generation3DBackend.MESHY:
            if not self.meshy_client:
                raise ValueError("Meshy API key not configured")
            return self.meshy_client
        elif backend == Generation3DBackend.MAKERGRID:
            if not self.makergrid_client:
                raise ValueError("MakerGrid access token not configured")
            return self.makergrid_client
        else:
            raise ValueError(f"Unsupported backend: {backend}")

    async def generate_from_image(
        self,
        image: Image.Image,
        backend: Optional[Generation3DBackend] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        **kwargs
    ) -> Generation3DResult:
        """
        Generate 3D model from single image.

        Args:
            image: Input image (PIL Image)
            backend: Which backend to use
            progress_callback: Called with (progress%, status_message)
            **kwargs: Backend-specific options

        Returns:
            Generation3DResult with model data
        """
        client = self._get_client(backend)

        if progress_callback:
            progress_callback(0, "Starting 3D generation...")

        # Start generation
        task_id = await client.generate_from_image(image, **kwargs)
        logger.info(f"Started 3D generation task: {task_id}")

        # Track task
        self._active_tasks[task_id] = {
            "backend": backend or self.default_backend,
            "started": asyncio.get_event_loop().time()
        }

        # Poll for completion
        result = await self._wait_for_completion(
            client, task_id, progress_callback
        )

        # Download model if successful
        if result.status == Generation3DStatus.COMPLETED and result.model_url:
            if progress_callback:
                progress_callback(95, "Downloading model...")

            result.glb_data = await client.download_model(result.model_url)

            # Save to output dir
            output_path = self.output_dir / f"{task_id}.glb"
            output_path.write_bytes(result.glb_data)
            result.metadata["local_path"] = str(output_path)

        if progress_callback:
            progress_callback(100, "Complete!")

        # Cleanup tracking
        del self._active_tasks[task_id]

        return result

    async def generate_from_multiview(
        self,
        views: MultiViewInput,
        backend: Optional[Generation3DBackend] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        **kwargs
    ) -> Generation3DResult:
        """
        Generate 3D model from multiple character views.

        Best results with front + side + back views.

        Args:
            views: MultiViewInput with character poses
            backend: Which backend to use (Tripo3D recommended for multiview)
            progress_callback: Progress updates

        Returns:
            Generation3DResult with model data
        """
        # Currently only Tripo3D supports native multiview
        backend = backend or Generation3DBackend.TRIPO3D

        if backend != Generation3DBackend.TRIPO3D:
            logger.warning("Multi-view only supported by Tripo3D, falling back")
            backend = Generation3DBackend.TRIPO3D

        client = self._get_client(backend)

        if not isinstance(client, Tripo3DClient):
            raise ValueError("Multi-view requires Tripo3D backend")

        if progress_callback:
            progress_callback(0, "Starting multi-view 3D generation...")

        # Start generation
        task_id = await client.generate_from_multiview(views, **kwargs)
        logger.info(f"Started multi-view 3D generation task: {task_id}")

        # Track and wait
        self._active_tasks[task_id] = {
            "backend": backend,
            "multiview": True
        }

        result = await self._wait_for_completion(
            client, task_id, progress_callback
        )

        # Download if successful
        if result.status == Generation3DStatus.COMPLETED and result.model_url:
            if progress_callback:
                progress_callback(95, "Downloading model...")

            result.glb_data = await client.download_model(result.model_url)

            output_path = self.output_dir / f"{task_id}_multiview.glb"
            output_path.write_bytes(result.glb_data)
            result.metadata["local_path"] = str(output_path)

        if progress_callback:
            progress_callback(100, "Complete!")

        del self._active_tasks[task_id]

        return result

    async def _wait_for_completion(
        self,
        client,
        task_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        poll_interval: float = 3.0,
        timeout: float = 600.0  # 10 minutes
    ) -> Generation3DResult:
        """Poll task until completion or timeout"""
        start_time = asyncio.get_event_loop().time()

        while True:
            result = await client.get_task_status(task_id)

            if progress_callback:
                status_msg = f"Generating 3D model ({result.status.value})..."
                progress_callback(min(90, result.progress), status_msg)

            if result.status == Generation3DStatus.COMPLETED:
                return result

            if result.status == Generation3DStatus.FAILED:
                logger.error(f"3D generation failed: {result.error}")
                return result

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                result.status = Generation3DStatus.FAILED
                result.error = "Generation timeout"
                return result

            await asyncio.sleep(poll_interval)

    async def generate_character_from_poses(
        self,
        poses_dir: Path,
        character_name: str = "character",
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Generation3DResult:
        """
        Generate 3D character from isolated pose directory.

        Expects files like:
        - {name}-front.png or {name}-front-apple.png
        - {name}-side.png
        - {name}-back.png

        Args:
            poses_dir: Directory containing isolated poses
            character_name: Character name prefix (e.g., "kyur")
            progress_callback: Progress updates

        Returns:
            Generation3DResult with character model
        """
        if progress_callback:
            progress_callback(0, "Loading character poses...")

        # Find pose files
        views = MultiViewInput()

        # Look for front view
        front_patterns = [
            f"{character_name}-front.png",
            f"{character_name}-front-apple.png",
            f"{character_name}-default.png"
        ]
        for pattern in front_patterns:
            path = poses_dir / pattern
            if path.exists():
                views.front = Image.open(path).convert("RGBA")
                logger.info(f"Loaded front view: {path}")
                break

        # Look for side view
        side_patterns = [
            f"{character_name}-side.png",
            f"{character_name}-side-2.png"
        ]
        for pattern in side_patterns:
            path = poses_dir / pattern
            if path.exists():
                views.side = Image.open(path).convert("RGBA")
                logger.info(f"Loaded side view: {path}")
                break

        # Look for back view
        back_patterns = [
            f"{character_name}-back.png",
            f"{character_name}-back-apple.png",
            f"{character_name}-back-apple-2.png"
        ]
        for pattern in back_patterns:
            path = poses_dir / pattern
            if path.exists():
                views.back = Image.open(path).convert("RGBA")
                logger.info(f"Loaded back view: {path}")
                break

        # Look for 3/4 views (optional, enhances quality)
        quarter_front = poses_dir / f"{character_name}-front-3quarter.png"
        if quarter_front.exists():
            views.front_3quarter = Image.open(quarter_front).convert("RGBA")

        quarter_back = poses_dir / f"{character_name}-back-3quarter.png"
        if quarter_back.exists():
            views.back_3quarter = Image.open(quarter_back).convert("RGBA")

        # Validate we have enough views
        view_count = sum([
            views.front is not None,
            views.side is not None,
            views.back is not None
        ])

        if view_count < 2:
            raise ValueError(
                f"Need at least 2 views for multi-view generation, found {view_count}. "
                f"Expected files like {character_name}-front.png, {character_name}-side.png"
            )

        if progress_callback:
            progress_callback(10, f"Found {view_count} views, starting generation...")

        # Generate 3D model
        return await self.generate_from_multiview(
            views,
            progress_callback=lambda p, m: progress_callback(10 + p * 0.9, m) if progress_callback else None
        )

    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get currently running generation tasks"""
        return self._active_tasks.copy()


# Factory function for easy initialization
def create_3d_service(
    tripo3d_key: Optional[str] = None,
    meshy_key: Optional[str] = None,
    makergrid_token: Optional[str] = None,
    output_dir: Optional[str] = None,
    default_backend: Optional[str] = None
) -> Generation3DService:
    """
    Create 3D generation service with available backends.

    Reads API keys from environment if not provided:
    - DIGIGAMI_TRIPO3D_API_KEY
    - DIGIGAMI_MESHY_API_KEY
    - DIGIGAMI_MAKERGRID_TOKEN
    """
    import os

    tripo3d_key = tripo3d_key or os.getenv("DIGIGAMI_TRIPO3D_API_KEY")
    meshy_key = meshy_key or os.getenv("DIGIGAMI_MESHY_API_KEY")
    makergrid_token = makergrid_token or os.getenv("DIGIGAMI_MAKERGRID_TOKEN")

    if not tripo3d_key and not meshy_key and not makergrid_token:
        logger.warning(
            "No 3D API keys configured. Set DIGIGAMI_TRIPO3D_API_KEY, "
            "DIGIGAMI_MESHY_API_KEY, or DIGIGAMI_MAKERGRID_TOKEN environment variable."
        )

    # Determine default backend - prioritize MakerGrid (friend's platform), then Tripo3D
    if default_backend:
        backend = Generation3DBackend(default_backend.lower())
    elif makergrid_token:
        backend = Generation3DBackend.MAKERGRID
    elif tripo3d_key:
        backend = Generation3DBackend.TRIPO3D
    else:
        backend = Generation3DBackend.MESHY

    return Generation3DService(
        tripo3d_api_key=tripo3d_key,
        meshy_api_key=meshy_key,
        makergrid_token=makergrid_token,
        default_backend=backend,
        output_dir=Path(output_dir) if output_dir else None
    )
