"""
Digigami Backend - Main Application
FastAPI server with WebSocket support for real-time avatar generation
"""
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings, STYLE_CONFIGS
from .api.websocket_server import handle_websocket, generator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Digigami Backend...")
    logger.info(f"Device: {settings.device}")
    logger.info(f"Available styles: {list(STYLE_CONFIGS.keys())}")
    yield
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
        "styles_loaded": len(STYLE_CONFIGS)
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
