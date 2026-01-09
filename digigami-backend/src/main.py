"""
Digigami Backend - Main Application
FastAPI server with WebSocket support for real-time avatar generation
"""
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional, List
from pathlib import Path
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn

from .config import settings, STYLE_CONFIGS
from .api.websocket_server import handle_websocket, generator
from .services import create_3d_service, Generation3DBackend, Generation3DStatus

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global 3D service instance
gen3d_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global gen3d_service

    logger.info("Starting Digigami Backend...")
    logger.info(f"Device: {settings.device}")
    logger.info(f"Available styles: {list(STYLE_CONFIGS.keys())}")

    # Initialize 3D generation service
    if settings.tripo3d_api_key or settings.meshy_api_key:
        gen3d_service = create_3d_service(
            tripo3d_key=settings.tripo3d_api_key,
            meshy_key=settings.meshy_api_key,
            output_dir=settings.gen3d_output_dir
        )
        logger.info(f"3D Generation service initialized (backend: {settings.gen3d_default_backend})")
    else:
        logger.warning("3D Generation disabled - no API keys configured")

    yield

    # Cleanup
    if gen3d_service:
        await gen3d_service.close()
    logger.info("Shutting down Digigami Backend...")


# Create FastAPI app
app = FastAPI(
    title="Digigami API",
    description="Avatar generation API with Kingdom Hearts / Dark Cloud 2 style transfer",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REST Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Digigami API",
        "version": "1.0.0",
        "status": "healthy",
        "device": settings.device
    }


@app.get("/api/styles")
async def get_styles():
    """Get available avatar styles"""
    return {
        "styles": STYLE_CONFIGS,
        "default": settings.default_style
    }


@app.get("/api/styles/{style_name}")
async def get_style(style_name: str):
    """Get specific style configuration"""
    if style_name not in STYLE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Style '{style_name}' not found")
    return STYLE_CONFIGS[style_name]


@app.post("/api/generate")
async def generate_avatar(
    image: UploadFile = File(...),
    style: str = Form(default="kingdom-hearts"),
    preserve_expression: bool = Form(default=True),
    enhance_details: bool = Form(default=True),
    output_size: int = Form(default=512)
):
    """
    REST endpoint for avatar generation (fallback for non-WebSocket clients)

    Note: WebSocket is preferred for real-time progress updates
    """
    if style not in STYLE_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Invalid style: {style}")

    # Read image
    contents = await image.read()
    import base64
    image_data = base64.b64encode(contents).decode('utf-8')

    # Generate avatar
    async def noop_progress(*args):
        pass

    result = await generator.generate(
        session_id=f"rest_{uuid.uuid4().hex[:8]}",
        image_data=image_data,
        style=style,
        options={
            "preserveExpression": preserve_expression,
            "enhanceDetails": enhance_details,
            "outputSize": output_size
        },
        progress_callback=noop_progress
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

    return result


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    import torch
    return {
        "status": "healthy",
        "device": settings.device,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "styles_loaded": len(STYLE_CONFIGS),
        "gen3d_enabled": gen3d_service is not None
    }


# ============================================================================
# 3D Generation Endpoints
# ============================================================================

# Store for tracking async 3D generation tasks
_gen3d_tasks = {}


@app.get("/api/3d/status")
async def get_3d_status():
    """Check if 3D generation is available"""
    return {
        "enabled": gen3d_service is not None,
        "backends": {
            "tripo3d": bool(settings.tripo3d_api_key),
            "meshy": bool(settings.meshy_api_key)
        },
        "default_backend": settings.gen3d_default_backend,
        "active_tasks": len(_gen3d_tasks)
    }


@app.post("/api/3d/generate")
async def generate_3d_from_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    backend: Optional[str] = Form(default=None)
):
    """
    Generate 3D model from a single image.

    Returns a task_id that can be used to poll for status.
    """
    if not gen3d_service:
        raise HTTPException(status_code=503, detail="3D generation service not configured")

    # Read image
    import base64
    from PIL import Image
    import io

    contents = await image.read()
    img = Image.open(io.BytesIO(contents)).convert("RGBA")

    # Generate task ID
    task_id = f"gen3d_{uuid.uuid4().hex[:12]}"

    # Parse backend
    gen_backend = None
    if backend:
        try:
            gen_backend = Generation3DBackend(backend.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid backend: {backend}")

    # Start background task
    _gen3d_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Starting generation..."
    }

    async def run_generation():
        try:
            def progress_cb(progress: float, message: str):
                _gen3d_tasks[task_id]["progress"] = progress
                _gen3d_tasks[task_id]["message"] = message
                _gen3d_tasks[task_id]["status"] = "processing"

            result = await gen3d_service.generate_from_image(
                img,
                backend=gen_backend,
                progress_callback=progress_cb
            )

            _gen3d_tasks[task_id]["status"] = result.status.value
            _gen3d_tasks[task_id]["progress"] = 100
            _gen3d_tasks[task_id]["result"] = {
                "model_url": result.model_url,
                "thumbnail_url": result.thumbnail_url,
                "local_path": result.metadata.get("local_path"),
                "error": result.error
            }
        except Exception as e:
            logger.error(f"3D generation error: {e}")
            _gen3d_tasks[task_id]["status"] = "failed"
            _gen3d_tasks[task_id]["error"] = str(e)

    background_tasks.add_task(run_generation)

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Generation started"
    }


@app.post("/api/3d/generate-multiview")
async def generate_3d_from_multiview(
    background_tasks: BackgroundTasks,
    front: Optional[UploadFile] = File(default=None),
    side: Optional[UploadFile] = File(default=None),
    back: Optional[UploadFile] = File(default=None)
):
    """
    Generate 3D model from multiple character views.

    Requires at least 2 views (front+side or front+back recommended).
    """
    if not gen3d_service:
        raise HTTPException(status_code=503, detail="3D generation service not configured")

    from PIL import Image
    from .services import MultiViewInput
    import io

    views = MultiViewInput()

    # Load provided views
    if front:
        contents = await front.read()
        views.front = Image.open(io.BytesIO(contents)).convert("RGBA")
    if side:
        contents = await side.read()
        views.side = Image.open(io.BytesIO(contents)).convert("RGBA")
    if back:
        contents = await back.read()
        views.back = Image.open(io.BytesIO(contents)).convert("RGBA")

    # Validate
    view_count = sum([views.front is not None, views.side is not None, views.back is not None])
    if view_count < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Multi-view generation requires at least 2 views, got {view_count}"
        )

    # Generate task ID
    task_id = f"gen3d_mv_{uuid.uuid4().hex[:12]}"

    _gen3d_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Starting multi-view generation...",
        "views": view_count
    }

    async def run_multiview_generation():
        try:
            def progress_cb(progress: float, message: str):
                _gen3d_tasks[task_id]["progress"] = progress
                _gen3d_tasks[task_id]["message"] = message
                _gen3d_tasks[task_id]["status"] = "processing"

            result = await gen3d_service.generate_from_multiview(
                views,
                progress_callback=progress_cb
            )

            _gen3d_tasks[task_id]["status"] = result.status.value
            _gen3d_tasks[task_id]["progress"] = 100
            _gen3d_tasks[task_id]["result"] = {
                "model_url": result.model_url,
                "thumbnail_url": result.thumbnail_url,
                "local_path": result.metadata.get("local_path"),
                "error": result.error
            }
        except Exception as e:
            logger.error(f"3D multi-view generation error: {e}")
            _gen3d_tasks[task_id]["status"] = "failed"
            _gen3d_tasks[task_id]["error"] = str(e)

    background_tasks.add_task(run_multiview_generation)

    return {
        "task_id": task_id,
        "status": "pending",
        "views": view_count,
        "message": "Multi-view generation started"
    }


@app.post("/api/3d/generate-character")
async def generate_3d_character(
    background_tasks: BackgroundTasks,
    poses_dir: str = Form(...),
    character_name: str = Form(default="kyur")
):
    """
    Generate 3D character from a directory of isolated poses.

    Expects the directory to contain files like:
    - {character_name}-front.png
    - {character_name}-side.png
    - {character_name}-back.png
    """
    if not gen3d_service:
        raise HTTPException(status_code=503, detail="3D generation service not configured")

    poses_path = Path(poses_dir)
    if not poses_path.exists():
        raise HTTPException(status_code=404, detail=f"Poses directory not found: {poses_dir}")

    # Generate task ID
    task_id = f"gen3d_char_{uuid.uuid4().hex[:12]}"

    _gen3d_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": f"Starting {character_name} character generation...",
        "character": character_name
    }

    async def run_character_generation():
        try:
            def progress_cb(progress: float, message: str):
                _gen3d_tasks[task_id]["progress"] = progress
                _gen3d_tasks[task_id]["message"] = message
                _gen3d_tasks[task_id]["status"] = "processing"

            result = await gen3d_service.generate_character_from_poses(
                poses_path,
                character_name=character_name,
                progress_callback=progress_cb
            )

            _gen3d_tasks[task_id]["status"] = result.status.value
            _gen3d_tasks[task_id]["progress"] = 100
            _gen3d_tasks[task_id]["result"] = {
                "model_url": result.model_url,
                "thumbnail_url": result.thumbnail_url,
                "local_path": result.metadata.get("local_path"),
                "error": result.error
            }
        except Exception as e:
            logger.error(f"3D character generation error: {e}")
            _gen3d_tasks[task_id]["status"] = "failed"
            _gen3d_tasks[task_id]["error"] = str(e)

    background_tasks.add_task(run_character_generation)

    return {
        "task_id": task_id,
        "status": "pending",
        "character": character_name,
        "message": f"Character generation started for {character_name}"
    }


@app.get("/api/3d/task/{task_id}")
async def get_3d_task_status(task_id: str):
    """Get status of a 3D generation task"""
    if task_id not in _gen3d_tasks:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return {
        "task_id": task_id,
        **_gen3d_tasks[task_id]
    }


@app.get("/api/3d/download/{task_id}")
async def download_3d_model(task_id: str):
    """Download generated 3D model (GLB format)"""
    if task_id not in _gen3d_tasks:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    task = _gen3d_tasks[task_id]

    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Task not completed: {task.get('status')}")

    local_path = task.get("result", {}).get("local_path")
    if not local_path or not Path(local_path).exists():
        raise HTTPException(status_code=404, detail="Model file not found")

    return FileResponse(
        local_path,
        media_type="model/gltf-binary",
        filename=f"{task_id}.glb"
    )


@app.get("/api/3d/tasks")
async def list_3d_tasks():
    """List all 3D generation tasks"""
    return {
        "tasks": [
            {"task_id": tid, **data}
            for tid, data in _gen3d_tasks.items()
        ],
        "count": len(_gen3d_tasks)
    }


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time avatar generation"""
    # Generate session ID
    session_id = f"digi_{uuid.uuid4().hex[:12]}"
    await handle_websocket(websocket, session_id)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint_with_session(websocket: WebSocket, session_id: str):
    """WebSocket endpoint with custom session ID"""
    await handle_websocket(websocket, session_id)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the server"""
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )


if __name__ == "__main__":
    main()
