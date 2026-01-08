# Digigami Style Transfer Backend

Real-time avatar generation with Kingdom Hearts / Dark Cloud 2 style transfer.

## Features

- **Face Detection**: MediaPipe-powered facial landmark extraction
- **Style Transfer**: Neural network style transfer with anime aesthetics
- **Real-time WebSocket**: Progress updates during generation
- **Multiple Styles**: Kingdom Hearts, Dark Cloud 2, Ghibli, Cel Shade
- **Expression Preservation**: Maintains facial expressions in stylized output

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env as needed
```

### 3. Run Server

```bash
python run.py
```

Server starts at `ws://localhost:8765`

## API

### WebSocket Protocol

Connect to `ws://localhost:8765/ws` or `ws://localhost:8765/ws/{session_id}`

#### Client -> Server Messages

```json
// Generate avatar
{
    "type": "generate_avatar",
    "image": "data:image/jpeg;base64,...",
    "style": "kingdom-hearts",
    "options": {
        "preserveExpression": true,
        "enhanceDetails": true,
        "outputSize": 512
    }
}

// Cancel generation
{
    "type": "cancel_generation"
}

// Get available styles
{
    "type": "get_styles"
}
```

#### Server -> Client Messages

```json
// Progress update
{
    "type": "progress",
    "percent": 45,
    "stage": "styling",
    "message": "Applying Kingdom Hearts style..."
}

// Result
{
    "type": "result",
    "success": true,
    "avatarData": "data:image/png;base64,...",
    "metadata": {
        "style": "kingdom-hearts",
        "processingTime": 2340,
        "model": "digigami-v1"
    }
}

// Error
{
    "type": "error",
    "code": "NO_FACE_DETECTED",
    "message": "No face detected in image"
}
```

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/styles` | GET | List available styles |
| `/api/styles/{name}` | GET | Get style details |
| `/api/generate` | POST | Generate avatar (multipart form) |
| `/api/health` | GET | Detailed health status |

## Available Styles

| Style | Description |
|-------|-------------|
| `kingdom-hearts` | Vibrant anime style with soft shading |
| `dark-cloud` | Bold cel-shaded style |
| `ghibli` | Soft, painterly Ghibli-inspired |
| `cel-shade` | Maximum cel-shading with strong outlines |

## Architecture

```
digigami-backend/
├── src/
│   ├── api/
│   │   └── websocket_server.py  # WebSocket handler
│   ├── services/
│   │   ├── face_detector.py     # MediaPipe face detection
│   │   └── style_transfer.py    # Neural style transfer
│   ├── models/                  # Trained model weights
│   ├── config.py                # Configuration
│   └── main.py                  # FastAPI application
├── weights/                     # Model weight files
├── requirements.txt
└── run.py
```

## GPU Support

The backend automatically detects and uses CUDA if available. For CPU-only:

```bash
DIGIGAMI_DEVICE=cpu python run.py
```

## Development

```bash
# Run with auto-reload
DIGIGAMI_DEBUG=true python run.py

# Run tests
pytest
```

## License

Copyright 2026 Anywave Creations. All rights reserved.
