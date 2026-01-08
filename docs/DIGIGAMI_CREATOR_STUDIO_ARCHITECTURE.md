# Digigami Creator Studio - Architecture Document

> Technical architecture for the digigami.me avatar creation platform and marketplace

**Version:** 1.0
**Date:** January 2026
**Author:** Anywave Creations

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Animation System](#animation-system)
4. [Avatar Generation Pipeline](#avatar-generation-pipeline)
5. [Creator Studio Features](#creator-studio-features)
6. [Marketplace Architecture](#marketplace-architecture)
7. [Technology Stack](#technology-stack)
8. [Data Models](#data-models)
9. [API Specifications](#api-specifications)
10. [Integration Points](#integration-points)

---

## Overview

### Vision

Digigami Creator Studio transforms users into stylized anime avatars inspired by Kingdom Hearts and Dark Cloud 2 aesthetics. The platform combines real-time AI style transfer with a comprehensive animation system and marketplace for avatar customization.

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      DIGIGAMI PLATFORM                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Landing Page   │  Creator Studio │       Marketplace           │
│  (digigami.me)  │                 │                             │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ - Avatar Demo   │ - Style Editor  │ - Asset Store               │
│ - Camera Capture│ - Animation     │ - Trading System            │
│ - Style Preview │ - Customization │ - Creator Profiles          │
│ - Onboarding    │ - Export Tools  │ - Collections               │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND SERVICES                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Style Transfer │  Animation      │       Asset                 │
│  Engine         │  Engine         │       Management            │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ - Face Detection│ - Keyframe      │ - Storage (S3/R2)           │
│ - Neural Style  │ - IK Solver     │ - CDN Distribution          │
│ - Expression    │ - Sprite Swap   │ - Version Control           │
│   Preservation  │ - State Machine │ - Licensing                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

---

## System Architecture

### High-Level Architecture

```
                                    ┌──────────────────┐
                                    │   CDN (Assets)   │
                                    └────────┬─────────┘
                                             │
┌──────────────┐    WebSocket    ┌───────────┴───────────┐
│   Browser    │◄───────────────►│    API Gateway        │
│   Client     │    REST API     │    (Load Balanced)    │
└──────────────┘                 └───────────┬───────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
           ┌────────▼────────┐    ┌──────────▼──────────┐   ┌────────▼────────┐
           │  Auth Service   │    │  Generation Service │   │  Asset Service  │
           │  (JWT/OAuth)    │    │  (Style Transfer)   │   │  (CRUD/Search)  │
           └─────────────────┘    └──────────┬──────────┘   └─────────────────┘
                                             │
                                    ┌────────▼────────┐
                                    │   GPU Workers   │
                                    │  (Inference)    │
                                    └─────────────────┘
```

### Client Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER CLIENT                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ UI Layer    │  │ State Mgmt  │  │ Service Layer       │  │
│  │             │  │             │  │                     │  │
│  │ - React/Vue │  │ - Zustand/  │  │ - WebSocket Client  │  │
│  │ - Canvas 2D │  │   Redux     │  │ - REST Client       │  │
│  │ - WebGL     │  │ - Local     │  │ - Camera Capture    │  │
│  │             │  │   Storage   │  │ - Animation Player  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   Core Modules                          ││
│  ├─────────────┬─────────────┬─────────────┬──────────────┤│
│  │ Camera      │ Animation   │ Avatar      │ Marketplace  ││
│  │ Module      │ Engine      │ Editor      │ Client       ││
│  └─────────────┴─────────────┴─────────────┴──────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Animation System

### Animation Architecture

The Digigami animation system draws inspiration from three proven implementations:

#### 1. Roblox-Inspired State Machine

```javascript
// Animation State Machine (inspired by Roblox humanoidAnimate)
class AvatarAnimationController {
    states = {
        idle: { animations: ['idle_1', 'idle_2', 'idle_3'], weights: [0.5, 0.3, 0.2] },
        walk: { animations: ['walk'], speed: 1.0 },
        run:  { animations: ['run'], speed: 1.5 },
        jump: { animations: ['jump'], priority: 'action' },
        emotes: {
            wave:  { animation: 'wave', duration: 2.0 },
            dance: { animations: ['dance_1', 'dance_2', 'dance_3'] },
            cheer: { animation: 'cheer', duration: 1.5 }
        }
    };

    currentState = 'idle';
    blendTime = 0.2; // seconds

    transition(newState, options = {}) {
        // Blend from current to new state
    }
}
```

**Supported Animation Categories:**
| Category | Animations | Use Case |
|----------|-----------|----------|
| Locomotion | idle, walk, run, climb, swim | Movement states |
| Actions | jump, fall, sit, land | Physical actions |
| Emotes | wave, point, dance (x9), laugh, cheer | Expression/social |
| Tools | toolnone, toolslash, toollunge | Item interactions |

#### 2. Unity 2D-Inspired Sprite System

```javascript
// Sprite Library System (inspired by Unity 2D Animation)
class SpriteLibrary {
    categories = {
        body: {
            default: 'body_base.png',
            muscular: 'body_muscular.png',
            slim: 'body_slim.png'
        },
        outfit: {
            casual: { torso: 'shirt_casual.png', legs: 'pants_casual.png' },
            formal: { torso: 'shirt_formal.png', legs: 'pants_formal.png' },
            armor:  { torso: 'armor_chest.png', legs: 'armor_legs.png' }
        },
        accessories: {
            none: null,
            glasses: 'glasses_round.png',
            hat: 'hat_cap.png',
            scarf: 'scarf_red.png'
        }
    };

    resolve(category, label) {
        return this.categories[category]?.[label];
    }

    swap(category, newLabel) {
        // Runtime sprite swapping for customization
    }
}
```

**Sprite Swap Features:**
- Category/Label organization for asset management
- Runtime swapping for live customization preview
- Variant libraries (base + DLC/seasonal content)
- Layered rendering with z-ordering

#### 3. Minecraft-Inspired Keyframe System

```javascript
// Keyframe Animation System (inspired by Minecraft client animation)
class KeyframeAnimation {
    static Interpolation = {
        LINEAR: (t, a, b) => a + (b - a) * t,
        CATMULLROM: (t, p0, p1, p2, p3) => {
            // Smooth cubic spline interpolation
            const t2 = t * t;
            const t3 = t2 * t;
            return 0.5 * (
                (2 * p1) +
                (-p0 + p2) * t +
                (2*p0 - 5*p1 + 4*p2 - p3) * t2 +
                (-p0 + 3*p1 - 3*p2 + p3) * t3
            );
        }
    };

    static Target = {
        POSITION: 'position',  // X, Y, Z offset
        ROTATION: 'rotation',  // Degrees converted to radians
        SCALE: 'scale'         // Multiplier from 1.0 base
    };
}

class AnimationDefinition {
    constructor(name, lengthInSeconds, looping = false) {
        this.name = name;
        this.length = lengthInSeconds;
        this.looping = looping;
        this.boneAnimations = new Map(); // bone name -> AnimationChannel[]
    }

    addChannel(boneName, target, keyframes) {
        if (!this.boneAnimations.has(boneName)) {
            this.boneAnimations.set(boneName, []);
        }
        this.boneAnimations.get(boneName).push({ target, keyframes });
    }
}

// Example: Idle breathing animation
const idleAnimation = new AnimationDefinition('idle', 3.0, true);
idleAnimation.addChannel('chest', 'scale', [
    { time: 0.0, value: [1.0, 1.0, 1.0], interpolation: 'CATMULLROM' },
    { time: 1.5, value: [1.02, 1.03, 1.02], interpolation: 'CATMULLROM' },
    { time: 3.0, value: [1.0, 1.0, 1.0], interpolation: 'CATMULLROM' }
]);
```

### Animation Player

```javascript
class DigigamiAnimationPlayer {
    constructor(avatar) {
        this.avatar = avatar;
        this.currentAnimation = null;
        this.elapsedTime = 0;
        this.speed = 1.0;
    }

    play(animationDef, options = {}) {
        this.currentAnimation = animationDef;
        this.elapsedTime = 0;
        this.speed = options.speed || 1.0;
        this.onComplete = options.onComplete;
    }

    update(deltaTime) {
        if (!this.currentAnimation) return;

        this.elapsedTime += deltaTime * this.speed;

        // Handle looping
        if (this.currentAnimation.looping) {
            this.elapsedTime %= this.currentAnimation.length;
        } else if (this.elapsedTime >= this.currentAnimation.length) {
            this.onComplete?.();
            return;
        }

        // Apply bone transformations
        for (const [boneName, channels] of this.currentAnimation.boneAnimations) {
            const bone = this.avatar.getBone(boneName);
            if (!bone) continue;

            for (const channel of channels) {
                const value = this.interpolateKeyframes(channel.keyframes, this.elapsedTime);
                this.applyTransform(bone, channel.target, value);
            }
        }
    }

    interpolateKeyframes(keyframes, time) {
        // Binary search for surrounding keyframes
        // Apply interpolation based on type
    }
}
```

### IK System (Inverse Kinematics)

```javascript
// 2D IK Solvers (inspired by Unity IKManager2D)
class IKSolver2D {
    static LIMB = 'limb';      // Two-bone solver (arms/legs)
    static CCD = 'ccd';        // Cyclic Coordinate Descent
    static FABRIK = 'fabrik';  // Forward And Backward Reaching

    constructor(type, chain) {
        this.type = type;
        this.chain = chain; // Array of bones from root to effector
        this.target = { x: 0, y: 0 };
        this.iterations = 10;
    }

    solve() {
        switch (this.type) {
            case IKSolver2D.LIMB:
                return this.solveLimb();
            case IKSolver2D.CCD:
                return this.solveCCD();
            case IKSolver2D.FABRIK:
                return this.solveFABRIK();
        }
    }

    solveFABRIK() {
        // Forward pass: move chain towards target
        // Backward pass: restore root position
        // Iterate until convergence
    }
}
```

---

## Avatar Generation Pipeline

### Style Transfer Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Camera    │────►│    Face     │────►│   Style     │────►│   Post      │
│   Capture   │     │  Detection  │     │  Transfer   │     │  Process    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
  Raw Image         Landmarks +          Stylized           Final Avatar
  (1280x960)        Bounding Box         Features           (512x512)
```

### Processing Stages

#### Stage 1: Face Detection & Landmark Extraction
```python
# Face detection pipeline
class FaceProcessor:
    def __init__(self):
        self.detector = MediaPipeFaceDetector()
        self.landmark_model = FaceLandmark478()

    def process(self, image):
        # Detect face bounding box
        faces = self.detector.detect(image)
        if not faces:
            raise NoFaceDetectedError()

        # Extract 478 facial landmarks
        landmarks = self.landmark_model.predict(image, faces[0])

        # Calculate expression parameters
        expression = self.extract_expression(landmarks)

        return {
            'bbox': faces[0],
            'landmarks': landmarks,
            'expression': expression,  # {smile, eyebrow_raise, eye_openness, ...}
            'head_pose': self.estimate_pose(landmarks)
        }
```

#### Stage 2: Style Transfer
```python
# Style transfer engine
class DigigamiStyleTransfer:
    STYLES = {
        'kingdom-hearts': 'models/kh_style_v2.pth',
        'dark-cloud': 'models/dc2_style_v1.pth',
        'ghibli': 'models/ghibli_style_v1.pth',
        'cel-shade': 'models/celshade_v1.pth'
    }

    def __init__(self, style='kingdom-hearts'):
        self.model = self.load_model(self.STYLES[style])
        self.expression_encoder = ExpressionEncoder()

    def generate(self, face_data, preserve_expression=True):
        # Encode expression if preserving
        if preserve_expression:
            expression_latent = self.expression_encoder.encode(face_data['expression'])

        # Generate stylized avatar
        avatar = self.model.generate(
            face_data['landmarks'],
            expression_latent if preserve_expression else None
        )

        return avatar
```

#### Stage 3: Post-Processing
```python
# Post-processing pipeline
class AvatarPostProcessor:
    def process(self, avatar, options):
        # Enhance details
        if options.get('enhance_details'):
            avatar = self.detail_enhancer.enhance(avatar)

        # Apply color adjustments
        avatar = self.color_correct(avatar, options.get('color_profile'))

        # Generate transparent background version
        avatar_transparent = self.remove_background(avatar)

        # Create multiple sizes
        outputs = {
            'full': avatar,
            'transparent': avatar_transparent,
            'thumbnail': self.resize(avatar, 128),
            'profile': self.resize(avatar, 256),
            'hd': self.resize(avatar, 1024)
        }

        return outputs
```

### WebSocket Protocol

```javascript
// Client -> Server Messages
{
    type: 'generate_avatar',
    sessionId: 'digi_abc123',
    image: 'data:image/jpeg;base64,...',
    style: 'kingdom-hearts',
    options: {
        preserveExpression: true,
        enhanceDetails: true,
        outputSize: 512
    }
}

// Server -> Client Messages
// Progress updates
{
    type: 'progress',
    percent: 50,
    stage: 'style_transfer',
    message: 'Applying Kingdom Hearts style...'
}

// Result
{
    type: 'result',
    success: true,
    avatarData: 'data:image/png;base64,...',
    avatarUrl: 'https://cdn.digigami.me/avatars/...',
    metadata: {
        style: 'kingdom-hearts',
        processingTime: 2340,
        model: 'digigami-v2'
    }
}
```

---

## Creator Studio Features

### Feature Matrix

| Feature | Description | Priority |
|---------|-------------|----------|
| **Avatar Editor** | Fine-tune generated avatars | P0 |
| **Animation Preview** | Test animations on avatar | P0 |
| **Sprite Customization** | Swap outfits/accessories | P1 |
| **Pose Editor** | IK-based pose creation | P1 |
| **Expression Editor** | Adjust facial expressions | P1 |
| **Animation Creator** | Keyframe animation tool | P2 |
| **Batch Export** | Multiple format export | P2 |

### Avatar Editor

```javascript
class AvatarEditor {
    constructor(canvas, avatar) {
        this.canvas = canvas;
        this.avatar = avatar;
        this.layers = new LayerManager();
        this.history = new UndoRedoStack();
    }

    // Color adjustments
    adjustColors(options) {
        const { hue, saturation, brightness, contrast } = options;
        this.avatar.applyColorFilter({ hue, saturation, brightness, contrast });
        this.history.push('colorAdjust', options);
    }

    // Part customization via sprite swap
    swapPart(category, variant) {
        this.avatar.spriteLibrary.swap(category, variant);
        this.history.push('swapPart', { category, variant });
    }

    // Accessory management
    addAccessory(accessory, position) {
        const layer = this.layers.create('accessory', accessory);
        layer.setPosition(position);
        this.history.push('addAccessory', { accessory, position });
    }

    // Export
    async export(format, options) {
        switch (format) {
            case 'png': return this.exportPNG(options);
            case 'svg': return this.exportSVG(options);
            case 'spritesheet': return this.exportSpritesheet(options);
            case 'spine': return this.exportSpine(options);
            case 'lottie': return this.exportLottie(options);
        }
    }
}
```

### Export Formats

| Format | Use Case | Includes Animation |
|--------|----------|-------------------|
| PNG | Static avatar, profile pics | No |
| PNG Sequence | Frame-by-frame animation | Yes |
| Spritesheet | Game engines, web | Yes |
| SVG | Scalable graphics | No |
| Spine JSON | Spine runtime integration | Yes |
| Lottie JSON | Web/mobile animation | Yes |
| GLTF | 3D viewers (future) | Yes |

---

## Marketplace Architecture

### Asset Types

```typescript
enum AssetType {
    AVATAR = 'avatar',           // Complete avatar
    OUTFIT = 'outfit',           // Clothing set
    ACCESSORY = 'accessory',     // Single accessory item
    ANIMATION = 'animation',     // Animation pack
    STYLE_PACK = 'style_pack',   // Style transfer model
    BACKGROUND = 'background',   // Scene backgrounds
    EFFECT = 'effect'            // Visual effects/particles
}

interface MarketplaceAsset {
    id: string;
    type: AssetType;
    name: string;
    description: string;
    creator: CreatorProfile;
    price: number;              // In platform currency
    currency: 'USD' | 'DIGI';   // Fiat or platform token
    preview: {
        thumbnail: string;
        images: string[];
        video?: string;
    };
    compatibility: string[];    // Compatible avatar styles
    downloads: number;
    rating: number;
    tags: string[];
    createdAt: Date;
    updatedAt: Date;
}
```

### Transaction Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Browse  │────►│  Preview │────►│ Purchase │────►│ Download │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │   Payment    │
                                 │   Gateway    │
                                 │ (Stripe/etc) │
                                 └──────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
             ┌──────────┐        ┌──────────┐        ┌──────────┐
             │ Platform │        │ Creator  │        │   Tax    │
             │   Fee    │        │ Payout   │        │ Reserve  │
             │  (15%)   │        │  (80%)   │        │   (5%)   │
             └──────────┘        └──────────┘        └──────────┘
```

### Creator Tools

```javascript
class CreatorDashboard {
    // Asset upload
    async uploadAsset(file, metadata) {
        const validated = await this.validateAsset(file, metadata.type);
        const processed = await this.processAsset(validated);
        const listing = await this.createListing(processed, metadata);
        return listing;
    }

    // Analytics
    getAnalytics(timeRange) {
        return {
            sales: this.getSalesData(timeRange),
            downloads: this.getDownloadData(timeRange),
            revenue: this.getRevenueData(timeRange),
            topAssets: this.getTopPerformers(timeRange),
            demographics: this.getBuyerDemographics(timeRange)
        };
    }

    // Payouts
    async requestPayout(amount, method) {
        const balance = await this.getAvailableBalance();
        if (amount > balance) throw new InsufficientBalanceError();
        return this.processPayout(amount, method);
    }
}
```

---

## Technology Stack

### Frontend

| Layer | Technology | Purpose |
|-------|------------|---------|
| Framework | React 18 / Next.js 14 | UI framework |
| State | Zustand | Global state management |
| Styling | Tailwind CSS | Utility-first CSS |
| Animation | Framer Motion | UI animations |
| Canvas | PixiJS / Fabric.js | 2D rendering |
| WebGL | Three.js (future) | 3D rendering |
| Real-time | Socket.io | WebSocket client |

### Backend

| Layer | Technology | Purpose |
|-------|------------|---------|
| API | Node.js / Fastify | REST API server |
| Real-time | Socket.io | WebSocket server |
| Queue | BullMQ / Redis | Job queue |
| Database | PostgreSQL | Primary data store |
| Cache | Redis | Session/cache |
| Search | Meilisearch | Asset search |
| Storage | Cloudflare R2 | Asset storage |
| CDN | Cloudflare | Asset delivery |

### AI/ML

| Component | Technology | Purpose |
|-----------|------------|---------|
| Inference | PyTorch | Model serving |
| Face Detection | MediaPipe | Landmark extraction |
| Style Transfer | Custom CNN | Avatar generation |
| GPU | NVIDIA A10G | Inference hardware |
| Orchestration | Ray Serve | Model scaling |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| Hosting | Vercel / Cloudflare | Frontend hosting |
| Compute | AWS EC2 / Lambda | Backend compute |
| GPU | RunPod / Lambda Labs | ML inference |
| Monitoring | Sentry | Error tracking |
| Analytics | PostHog | User analytics |
| CI/CD | GitHub Actions | Deployment |

---

## Data Models

### Core Entities

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    avatar_url TEXT,
    is_creator BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Avatars
CREATE TABLE avatars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    style VARCHAR(50) NOT NULL,
    base_image_url TEXT NOT NULL,
    sprite_library JSONB,
    customizations JSONB,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Animations
CREATE TABLE animations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'locomotion', 'emote', 'action'
    definition JSONB NOT NULL, -- Keyframe data
    duration_ms INTEGER NOT NULL,
    is_looping BOOLEAN DEFAULT FALSE,
    creator_id UUID REFERENCES users(id),
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Marketplace Assets
CREATE TABLE marketplace_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_cents INTEGER NOT NULL,
    preview_urls JSONB,
    asset_url TEXT NOT NULL,
    compatibility JSONB,
    downloads INTEGER DEFAULT 0,
    rating_avg DECIMAL(3,2),
    rating_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Purchases
CREATE TABLE purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    asset_id UUID REFERENCES marketplace_assets(id),
    price_cents INTEGER NOT NULL,
    payment_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Specifications

### REST Endpoints

```yaml
# Avatar API
POST   /api/avatars              # Create new avatar
GET    /api/avatars              # List user's avatars
GET    /api/avatars/:id          # Get avatar details
PATCH  /api/avatars/:id          # Update avatar
DELETE /api/avatars/:id          # Delete avatar
POST   /api/avatars/:id/export   # Export avatar

# Animation API
GET    /api/animations           # List available animations
GET    /api/animations/:id       # Get animation definition
POST   /api/animations           # Create custom animation (creators)

# Marketplace API
GET    /api/marketplace/assets   # Search/browse assets
GET    /api/marketplace/assets/:id  # Get asset details
POST   /api/marketplace/assets   # Create listing (creators)
POST   /api/marketplace/purchase # Purchase asset

# Generation API (WebSocket preferred)
POST   /api/generate             # Fallback REST generation
```

### WebSocket Events

```typescript
// Client -> Server
interface ClientEvents {
    'generate:start': { image: string; style: string; options: object };
    'generate:cancel': { sessionId: string };
    'animation:preview': { avatarId: string; animationId: string };
}

// Server -> Client
interface ServerEvents {
    'generate:progress': { percent: number; stage: string; message: string };
    'generate:complete': { success: boolean; avatarData?: string; error?: string };
    'animation:frame': { frameData: string };
}
```

---

## Integration Points

### External Services

| Service | Purpose | Integration |
|---------|---------|-------------|
| Stripe | Payments | API + Webhooks |
| Cloudflare | CDN/Storage | S3-compatible API |
| SendGrid | Email | SMTP/API |
| Discord | Community | OAuth + Bot |
| Roblox | Avatar export | UGC API (future) |

### Export Integrations

```javascript
// Platform export adapters
class ExportManager {
    adapters = {
        roblox: new RobloxExporter(),
        vrchat: new VRChatExporter(),
        discord: new DiscordExporter(),
        twitter: new TwitterExporter(),
        twitch: new TwitchExporter()
    };

    async exportTo(platform, avatar, options) {
        const adapter = this.adapters[platform];
        if (!adapter) throw new UnsupportedPlatformError(platform);

        const formatted = await adapter.format(avatar, options);
        return adapter.upload(formatted);
    }
}
```

---

## Appendix

### Reference Implementations

1. **Roblox Avatar System**
   - Location: `AppData/Local/Roblox/Versions/.../content/avatar/`
   - Key file: `humanoidR15AnimateLiveUpdates.lua`
   - Patterns: State machine, weighted animations, priority system

2. **Unity 2D Animation**
   - Location: `AppData/Local/Unity/cache/.../com.unity.2d.animation@9.1.0/`
   - Key features: SpriteSkin, IK solvers, Sprite Library
   - Patterns: Skeletal deformation, sprite swapping, pose tools

3. **Minecraft Animation**
   - Location: `MCreatorWorkspaces/.../net/minecraft/client/animation/`
   - Key files: `KeyframeAnimations.java`, `AnimationDefinition.java`
   - Patterns: Keyframe system, interpolation types, bone targeting

### Glossary

| Term | Definition |
|------|------------|
| **Keyframe** | A snapshot of animation values at a specific time |
| **IK** | Inverse Kinematics - calculating joint angles to reach a target |
| **Sprite Library** | Organized collection of swappable sprite assets |
| **Style Transfer** | AI technique to apply artistic style to images |
| **Rig** | Skeletal structure for animating characters |

---

*Document maintained by Anywave Creations. Last updated January 2026.*
