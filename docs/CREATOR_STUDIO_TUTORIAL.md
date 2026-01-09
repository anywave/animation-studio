# Digigami Creator Studio Tutorial

> Complete guide to creating stylized anime avatars with the Digigami platform

**Version:** 1.0
**Date:** January 2026
**Author:** Anywave Creations

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Avatar Generation Pipeline](#avatar-generation-pipeline)
3. [Available Styles](#available-styles)
4. [Gesture & Animation System](#gesture--animation-system)
5. [Using Kyur Chat Assistant](#using-kyur-chat-assistant)
6. [WebSocket API Usage](#websocket-api-usage)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

1. **Backend Server** running on port `8765`
   ```bash
   cd D:/ANYWAVEREPO/animation-studio/digigami-backend
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8765 --reload
   ```

2. **Frontend** running on port `8080`
   ```bash
   cd D:/ANYWAVEREPO/animation-studio/digigami-landing
   # Use any static server (Python, http-server, etc.)
   python -m http.server 8080
   ```

3. **OA Assistant (Optional)** on port `5000`
   ```bash
   cd D:/ANYWAVEREPO/anywavecreations.com/.digigami-oa
   python app.py
   ```

### Quick Start

1. Open `http://localhost:8080` in your browser
2. Click "Create My Avatar" or use the camera capture
3. Select a style (Kingdom Hearts, Dark Cloud, Ghibli, or Cel-Shade)
4. Upload or capture a photo
5. Watch the real-time progress as your avatar is generated!

---

## Avatar Generation Pipeline

The generation process follows 6 stages:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Camera    │────►│    Face     │────►│   Style     │
│   Capture   │     │  Detection  │     │  Transfer   │
└─────────────┘     └─────────────┘     └─────────────┘
      5%                15-25%              45-75%

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Refining   │────►│ Finalizing  │────►│   Encode    │
│  Details    │     │   Avatar    │     │   Result    │
└─────────────┘     └─────────────┘     └─────────────┘
     75-85%             85-95%              95-100%
```

### Stage Details

| Stage | Progress | Description |
|-------|----------|-------------|
| **Decoding** | 5% | Base64 image decoded to numpy array |
| **Detecting** | 15-25% | Face detection via MediaPipe (optional) |
| **Preparing** | 35% | Image prepared for style transfer |
| **Styling** | 45-75% | VGG19 Neural Style Transfer with AdaIN |
| **Refining** | 75-85% | Detail enhancement and sharpening |
| **Encoding** | 95-100% | Final PNG/JPEG encoding |

### Face Detection Behavior

- **Human faces**: Full landmark extraction (478 points) + expression preservation
- **Non-human/anime images**: Bypasses face detection, uses full image for style transfer
- **No face found**: Logs warning, continues with full image

---

## Available Styles

### 1. Kingdom Hearts Style
```json
{
    "name": "Kingdom Hearts",
    "description": "Vibrant anime style with expressive eyes and dynamic hair",
    "color_profile": "saturated",
    "features": ["large_eyes", "stylized_hair", "soft_shading"]
}
```

### 2. Dark Cloud Style
```json
{
    "name": "Dark Cloud",
    "description": "Warm cel-shaded look with detailed clothing and accessories",
    "color_profile": "warm",
    "features": ["cel_shading", "detailed_outfit", "soft_lighting"]
}
```

### 3. Ghibli Style
```json
{
    "name": "Ghibli",
    "description": "Soft, dreamy aesthetics inspired by Studio Ghibli",
    "color_profile": "pastel",
    "features": ["soft_edges", "watercolor_feel", "natural_lighting"]
}
```

### 4. Cel-Shade Style
```json
{
    "name": "Cel-Shade",
    "description": "Bold outlines with flat colors for a graphic novel feel",
    "color_profile": "bold",
    "features": ["thick_outlines", "flat_colors", "high_contrast"]
}
```

---

## Gesture & Animation System

### Available Character Poses

#### Kyur (Main Avatar Guide)
| Pose | File | Use Case |
|------|------|----------|
| Default | `Kyur.png` | Neutral/idle state |
| Thinking | `Kyur2.png` | Processing/loading |
| Excited | `Kyur3.png` | Success/celebration |
| Pointing | `Kyur4.png` | Explaining/guiding |

#### Gwynn (5 poses)
- `Gwynn.png` - Default
- `Gwynn2.png`, `Gwynn3.png`, `Gwynn4.png` - Variants
- `Gwynn-Hades Mod.png` - Special variant

#### Yoroiche (6 poses)
- `Yoroiche.png` through `Yoroiche6.png`

#### Urahara (2 poses)
- `Urahara.png`, `Urahara2.png`

### Pose Mapping System

```javascript
// In kyur-chat.js
this.poseMap = {
    default: 0,      // Neutral/default pose
    thinking: 1,     // Processing/thinking pose
    excited: 2,      // Happy/success pose
    pointing: 3      // Explaining/guiding pose
};

// Usage
setKyurPose('excited');  // Switches to happy pose
setKyurPose('thinking'); // Shows thinking animation
```

### CSS Keyframe Animations

Available animations in `styles.css`:

```css
/* Sparkle effect for highlights */
@keyframes sparkle {
    0%, 100% { opacity: 0.3; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.2); }
}

/* Pulse for interactive elements */
@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.05); opacity: 0.8; }
}

/* Breathing animation for idle characters */
@keyframes character-breathe {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-5px); }
}

/* Typing indicator */
@keyframes typingBounce {
    0%, 80%, 100% { transform: translateY(0); }
    40% { transform: translateY(-6px); }
}
```

### Animation State Machine (Roblox-inspired)

```javascript
// Animation categories and states
const animationStates = {
    locomotion: {
        idle: { animations: ['idle_1', 'idle_2'], weights: [0.7, 0.3] },
        walk: { animation: 'walk', speed: 1.0 },
        run:  { animation: 'run', speed: 1.5 },
        jump: { animation: 'jump', priority: 'action' }
    },
    emotes: {
        wave:  { animation: 'wave', duration: 2.0 },
        dance: { animations: ['dance_1', 'dance_2', 'dance_3'] },
        cheer: { animation: 'cheer', duration: 1.5 }
    },
    actions: {
        sit: { animation: 'sit' },
        land: { animation: 'land', duration: 0.5 }
    }
};
```

### Keyframe Animation System (Minecraft-inspired)

```javascript
// Example: Idle breathing animation
const idleAnimation = new AnimationDefinition('idle', 3.0, true);
idleAnimation.addChannel('chest', 'scale', [
    { time: 0.0, value: [1.0, 1.0, 1.0], interpolation: 'CATMULLROM' },
    { time: 1.5, value: [1.02, 1.03, 1.02], interpolation: 'CATMULLROM' },
    { time: 3.0, value: [1.0, 1.0, 1.0], interpolation: 'CATMULLROM' }
]);
```

### IK Solvers (Inverse Kinematics)

```javascript
// Available IK solver types
const IK_TYPES = {
    LIMB: 'limb',      // Two-bone solver (arms/legs)
    CCD: 'ccd',        // Cyclic Coordinate Descent
    FABRIK: 'fabrik'   // Forward And Backward Reaching
};

// Usage
const armIK = new IKSolver2D(IK_TYPES.LIMB, ['shoulder', 'elbow', 'hand']);
armIK.setTarget(targetPosition);
armIK.solve();
```

---

## Using Kyur Chat Assistant

### Initialization

The Kyur chat widget initializes automatically:

```javascript
// Automatic initialization in kyur-chat.js
document.addEventListener('DOMContentLoaded', () => {
    window.kyurChat = new KyurChat({
        apiEndpoint: 'http://localhost:5000/api/v1/digigami',
        debug: true,
        autoGreet: true
    });
});
```

### Chat Features

1. **Auto-greeting**: Shows after 3 seconds of inactivity
2. **Pose reactions**: Kyur changes pose based on conversation
3. **Suggestion chips**: Quick-reply buttons
4. **RAG-powered responses**: Contextual answers from documentation

### Pose Reaction Rules

```javascript
// In sendMessage() after receiving response
if (response.includes('!') || response.includes('amazing')) {
    setKyurPose('excited');
} else if (response.includes('?') || response.includes('tip')) {
    setKyurPose('pointing');
} else {
    setKyurPose('default');
}
```

---

## WebSocket API Usage

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8765/ws?session=YOUR_SESSION_ID');

ws.onopen = () => {
    console.log('Connected to Digigami backend');
};
```

### Generate Avatar Request

```javascript
// Send generation request
ws.send(JSON.stringify({
    type: 'generate_avatar',
    image: 'data:image/jpeg;base64,...', // Base64 image
    style: 'kingdom-hearts',
    options: {
        strength: 0.8,
        preserveExpression: true,
        enhanceDetails: true
    }
}));
```

### Handle Progress Updates

```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
        case 'progress':
            console.log(`${data.percent}% - ${data.message}`);
            updateProgressBar(data.percent);
            break;

        case 'result':
            if (data.success) {
                displayAvatar(data.avatarData);
                console.log('Processing time:', data.metadata.processingTime, 'ms');
            } else {
                console.error('Generation failed:', data.error);
            }
            break;

        case 'error':
            console.error(`Error ${data.code}: ${data.message}`);
            break;
    }
};
```

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `handshake` | Client→Server | Initial connection |
| `handshake_ack` | Server→Client | Connection confirmed |
| `generate_avatar` | Client→Server | Start generation |
| `progress` | Server→Client | Progress update |
| `result` | Server→Client | Generation result |
| `cancel_generation` | Client→Server | Cancel ongoing |
| `get_styles` | Client→Server | List available styles |
| `styles` | Server→Client | Style list response |
| `ping` | Client→Server | Health check |
| `pong` | Server→Client | Health response |

---

## Troubleshooting

### Common Issues

#### "No face detected" Warning
**Cause**: MediaPipe trained on human faces only
**Solution**: System now automatically uses full image when no face is found

#### WebSocket Connection Failed
```bash
# Check if backend is running
curl http://localhost:8765/health

# Restart backend
cd D:/ANYWAVEREPO/animation-studio/digigami-backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8765 --reload
```

#### Style Transfer Returns Black Image
**Cause**: GPU memory issue or model not loaded
**Solution**: Check backend logs for model loading errors

#### Slow Generation
**Cause**: Running on CPU instead of GPU
**Solution**: Install CUDA and PyTorch GPU version, or reduce image size

### Debug Mode

Enable debug logging:

```javascript
// In kyur-chat.js
window.kyurChat = new KyurChat({
    debug: true  // Enables console logging
});
```

```python
# In backend - set log level
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Backend Logs Location

```
D:/ANYWAVEREPO/animation-studio/digigami-backend/logs/
```

---

## File Locations

| Component | Path |
|-----------|------|
| Backend Server | `digigami-backend/src/main.py` |
| WebSocket Handler | `digigami-backend/src/api/websocket_server.py` |
| Style Transfer | `digigami-backend/src/services/style_transfer.py` |
| Face Detection | `digigami-backend/src/services/face_detector.py` |
| Frontend Main | `digigami-landing/index.html` |
| Kyur Chat | `digigami-landing/js/kyur-chat.js` |
| WebSocket Client | `digigami-landing/js/websocket.js` |
| Character Assets | `digigami-landing/assets/characters-reference/` |
| Architecture Doc | `docs/DIGIGAMI_CREATOR_STUDIO_ARCHITECTURE.md` |

---

*Tutorial maintained by Anywave Creations. Last updated January 2026.*
