/**
 * Digigami Sprite Animator
 *
 * Renders animated sprites from spritesheets during loading states.
 * Uses the TexturePacker-format JSON metadata.
 */

class SpriteAnimator {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        this.fps = options.fps || 8;
        this.scale = options.scale || 1;
        this.onLoad = options.onLoad || (() => {});

        this.spritesheet = null;
        this.metadata = null;
        this.frames = [];
        this.currentFrameIndex = 0;
        this.animationId = null;
        this.lastFrameTime = 0;
        this.frameInterval = 1000 / this.fps;

        this.currentAnimation = null;
        this.isPlaying = false;
        this.loop = true;
    }

    /**
     * Load a character's spritesheet
     */
    async load(character, basePath = '../characters-reference/spritesheets') {
        const jsonPath = `${basePath}/${character}_spritesheet.json`;
        const imagePath = `${basePath}/${character}_spritesheet.png`;

        console.log('Loading JSON from:', jsonPath);
        console.log('Loading image from:', imagePath);

        try {
            // Load JSON metadata
            const response = await fetch(jsonPath);
            if (!response.ok) throw new Error(`Failed to load ${jsonPath}: ${response.status}`);
            this.metadata = await response.json();
            console.log('JSON loaded, frames:', Object.keys(this.metadata.frames).length);

            // Load spritesheet image
            this.spritesheet = new Image();
            console.log('Loading spritesheet image (this may take a moment for large files)...');

            await new Promise((resolve, reject) => {
                this.spritesheet.onload = () => {
                    console.log('Image loaded:', this.spritesheet.width, 'x', this.spritesheet.height);
                    resolve();
                };
                this.spritesheet.onerror = (e) => {
                    console.error('Image load error:', e);
                    reject(e);
                };
                this.spritesheet.src = imagePath;
            });

            // Parse frames
            this.frames = Object.entries(this.metadata.frames).map(([name, data]) => ({
                name,
                ...data.frame,
                sourceSize: data.sourceSize,
                spriteSourceSize: data.spriteSourceSize
            }));
            console.log('Parsed frames:', this.frames.length);

            // Set canvas size based on first frame
            if (this.frames.length > 0) {
                const firstFrame = this.frames[0];
                this.canvas.width = firstFrame.sourceSize.w * this.scale;
                this.canvas.height = firstFrame.sourceSize.h * this.scale;
                console.log('Canvas size set to:', this.canvas.width, 'x', this.canvas.height);
            }

            this.onLoad(this.metadata);
            return true;

        } catch (error) {
            console.error('Failed to load spritesheet:', error);
            return false;
        }
    }

    /**
     * Get available animations from metadata
     */
    getAnimations() {
        if (!this.metadata?.animations) return {};
        return this.metadata.animations;
    }

    /**
     * Get all frame names
     */
    getFrameNames() {
        return this.frames.map(f => f.name);
    }

    /**
     * Play a named animation sequence
     */
    playAnimation(animationName, loop = true) {
        const animations = this.getAnimations();
        if (!animations[animationName]) {
            console.warn(`Animation "${animationName}" not found`);
            return;
        }

        this.currentAnimation = animations[animationName];
        this.currentFrameIndex = 0;
        this.loop = loop;
        this.play();
    }

    /**
     * Play through all frames (turnaround)
     */
    playAll(loop = true) {
        this.currentAnimation = this.frames.map(f => f.name);
        this.currentFrameIndex = 0;
        this.loop = loop;
        this.play();
    }

    /**
     * Play specific frames by name
     */
    playFrames(frameNames, loop = true) {
        this.currentAnimation = frameNames;
        this.currentFrameIndex = 0;
        this.loop = loop;
        this.play();
    }

    /**
     * Show a single frame
     */
    showFrame(frameName) {
        this.stop();
        const frame = this.frames.find(f => f.name === frameName);
        if (frame) {
            this._renderFrame(frame);
        }
    }

    /**
     * Start animation playback
     */
    play() {
        if (this.isPlaying) return;
        this.isPlaying = true;
        this.lastFrameTime = performance.now();
        this._animate();
    }

    /**
     * Pause animation
     */
    pause() {
        this.isPlaying = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        // Re-render current frame to ensure it's displayed
        if (this.currentAnimation && this.currentAnimation.length > 0) {
            const frameName = this.currentAnimation[this.currentFrameIndex];
            const frame = this.frames.find(f => f.name === frameName);
            if (frame) this._renderFrame(frame);
        }
    }

    /**
     * Stop and reset animation
     */
    stop() {
        this.pause();
        this.currentFrameIndex = 0;
        if (this.currentAnimation && this.currentAnimation.length > 0) {
            const frameName = this.currentAnimation[0];
            const frame = this.frames.find(f => f.name === frameName);
            if (frame) this._renderFrame(frame);
        }
    }

    /**
     * Set playback speed
     */
    setFPS(fps) {
        this.fps = fps;
        this.frameInterval = 1000 / fps;
    }

    /**
     * Main animation loop
     */
    _animate() {
        if (!this.isPlaying) return;

        const now = performance.now();
        const elapsed = now - this.lastFrameTime;

        if (elapsed >= this.frameInterval) {
            this.lastFrameTime = now - (elapsed % this.frameInterval);
            this._nextFrame();
        }

        this.animationId = requestAnimationFrame(() => this._animate());
    }

    /**
     * Advance to next frame
     */
    _nextFrame() {
        if (!this.currentAnimation || this.currentAnimation.length === 0) return;

        const frameName = this.currentAnimation[this.currentFrameIndex];
        const frame = this.frames.find(f => f.name === frameName);

        if (frame) {
            this._renderFrame(frame);
        }

        this.currentFrameIndex++;
        if (this.currentFrameIndex >= this.currentAnimation.length) {
            if (this.loop) {
                this.currentFrameIndex = 0;
            } else {
                this.pause();
            }
        }
    }

    /**
     * Render a single frame to canvas
     */
    _renderFrame(frame) {
        if (!this.spritesheet || !this.spritesheet.complete) {
            console.warn('Spritesheet not loaded');
            return;
        }

        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // For trimmed sprites, we need to position correctly within the original source size
        const destX = (frame.spriteSourceSize?.x || 0) * this.scale;
        const destY = (frame.spriteSourceSize?.y || 0) * this.scale;
        const destW = (frame.spriteSourceSize?.w || frame.w) * this.scale;
        const destH = (frame.spriteSourceSize?.h || frame.h) * this.scale;

        // Draw frame from spritesheet
        this.ctx.drawImage(
            this.spritesheet,
            frame.x, frame.y, frame.w, frame.h,  // Source rectangle from atlas
            destX, destY, destW, destH  // Destination on canvas
        );
    }

    /**
     * Resize canvas and redraw
     */
    resize(scale) {
        this.scale = scale;
        if (this.frames.length > 0) {
            const firstFrame = this.frames[0];
            this.canvas.width = firstFrame.sourceSize.w * this.scale;
            this.canvas.height = firstFrame.sourceSize.h * this.scale;
        }
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SpriteAnimator;
}
if (typeof window !== 'undefined') {
    window.SpriteAnimator = SpriteAnimator;
}
