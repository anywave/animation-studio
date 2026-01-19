/**
 * Digigami Animated Character Loader
 *
 * Smart loader with WebGL capability detection.
 * Attempts 3D loading first, falls back to sprites on failure.
 * Provides unified API regardless of rendering method.
 */

class AnimatedCharacterLoader {
    constructor(container, options = {}) {
        this.container = container;

        // Options
        this.prefer3D = options.prefer3D !== false;
        this.fps = options.fps || 8;
        this.scale = options.scale || 1;
        this.onLoad = options.onLoad || (() => {});
        this.onError = options.onError || ((err) => console.error(err));
        this.onFallback = options.onFallback || (() => {});

        // State
        this.animator = null;
        this.animatorType = null;
        this.character = null;
        this.isLoaded = false;

        // Phase to animation mapping for 3D
        this.phaseAnimationMap = {
            'idle': 'idle',
            'thinking': 'thinking',
            'excited': 'excited',
            'pointing': 'pointing',
            'wave': 'wave',
            // Default fallbacks
            'default': 'idle',
            'front': 'idle'
        };
    }

    /**
     * Load a character with automatic fallback
     */
    async load(character, options = {}) {
        this.character = character;

        const basePath3D = options.basePath3D || '../characters-reference/3d_output/web';
        const basePathSprite = options.basePathSprite || '../characters-reference/spritesheets';

        // Try 3D first if preferred and supported
        if (this.prefer3D && this._isWebGLSupported()) {
            console.log('Attempting 3D animation loading...');

            try {
                const success = await this._load3D(character, basePath3D);
                if (success) {
                    console.log('3D animation loaded successfully');
                    return true;
                }
            } catch (error) {
                console.warn('3D loading failed, falling back to sprites:', error);
            }
        }

        // Fallback to sprites
        console.log('Loading sprite animation...');
        this.onFallback();

        try {
            const success = await this._loadSprite(character, basePathSprite);
            if (success) {
                console.log('Sprite animation loaded successfully');
                return true;
            }
        } catch (error) {
            console.error('Sprite loading also failed:', error);
            this.onError(error);
        }

        return false;
    }

    /**
     * Load 3D animated model
     */
    async _load3D(character, basePath) {
        // Check if Character3DAnimator is available
        if (typeof Character3DAnimator === 'undefined') {
            throw new Error('Character3DAnimator not loaded');
        }

        // Create 3D animator
        this.animator = new Character3DAnimator(this.container, {
            fps: this.fps,
            onLoad: (metadata) => {
                this.isLoaded = true;
                this.animatorType = '3d';
                this.onLoad({
                    type: '3d',
                    ...metadata
                });
            },
            onError: this.onError
        });

        return await this.animator.load(character, basePath);
    }

    /**
     * Load sprite animation
     */
    async _loadSprite(character, basePath) {
        // Check if SpriteAnimator is available
        if (typeof SpriteAnimator === 'undefined') {
            throw new Error('SpriteAnimator not loaded');
        }

        // Create canvas if container doesn't have one
        let canvas = this.container.querySelector('canvas');
        if (!canvas) {
            canvas = document.createElement('canvas');
            this.container.appendChild(canvas);
        }

        // Create sprite animator
        this.animator = new SpriteAnimator(canvas, {
            fps: this.fps,
            scale: this.scale,
            onLoad: (metadata) => {
                this.isLoaded = true;
                this.animatorType = 'sprite';
                this.onLoad({
                    type: 'sprite',
                    ...metadata
                });
            }
        });

        return await this.animator.load(character, basePath);
    }

    /**
     * Play animation by pose/phase name
     * Handles mapping between 3D animation names and sprite frame names
     */
    playPose(poseName, loop = true) {
        if (!this.animator || !this.isLoaded) {
            console.warn('Animator not ready');
            return;
        }

        if (this.animatorType === '3d') {
            // Map pose to 3D animation name
            const animName = this.phaseAnimationMap[poseName] || poseName;
            this.animator.playAnimation(animName, loop);
        } else {
            // For sprites, try to find matching frame
            const frameNames = this.animator.getFrameNames();
            const matchingFrame = frameNames.find(f =>
                f.toLowerCase().includes(poseName.toLowerCase())
            );

            if (matchingFrame) {
                this.animator.showFrame(matchingFrame);
            } else {
                console.warn(`No frame found for pose: ${poseName}`);
            }
        }
    }

    /**
     * Play specific animation (direct pass-through)
     */
    playAnimation(name, loop = true) {
        if (!this.animator || !this.isLoaded) return;

        if (this.animatorType === '3d') {
            this.animator.playAnimation(name, loop);
        } else {
            this.animator.playAnimation(name, loop);
        }
    }

    /**
     * Play all animations/frames
     */
    playAll(loop = true) {
        if (!this.animator || !this.isLoaded) return;
        this.animator.playAll(loop);
    }

    /**
     * Show specific frame/pose
     */
    showFrame(name) {
        if (!this.animator || !this.isLoaded) return;
        this.animator.showFrame(name);
    }

    /**
     * Start playback
     */
    play() {
        if (!this.animator || !this.isLoaded) return;
        this.animator.play();
    }

    /**
     * Pause playback
     */
    pause() {
        if (!this.animator || !this.isLoaded) return;
        this.animator.pause();
    }

    /**
     * Stop and reset
     */
    stop() {
        if (!this.animator || !this.isLoaded) return;
        this.animator.stop();
    }

    /**
     * Set FPS
     */
    setFPS(fps) {
        this.fps = fps;
        if (this.animator) {
            this.animator.setFPS(fps);
        }
    }

    /**
     * Resize
     */
    resize(scale) {
        this.scale = scale;
        if (this.animator) {
            this.animator.resize(scale);
        }
    }

    /**
     * Get animator type ('3d' or 'sprite')
     */
    getType() {
        return this.animatorType;
    }

    /**
     * Check if using 3D
     */
    is3D() {
        return this.animatorType === '3d';
    }

    /**
     * Get available animations/frames
     */
    getAnimations() {
        if (!this.animator || !this.isLoaded) return {};

        if (this.animatorType === '3d') {
            return this.animator.getAnimations();
        } else {
            return this.animator.getAnimations();
        }
    }

    /**
     * Get animation/frame names
     */
    getFrameNames() {
        if (!this.animator || !this.isLoaded) return [];
        return this.animator.getFrameNames();
    }

    /**
     * Clean up all resources
     */
    dispose() {
        if (this.animator) {
            if (typeof this.animator.dispose === 'function') {
                this.animator.dispose();
            }
            this.animator = null;
        }

        this.isLoaded = false;
        this.animatorType = null;
    }

    /**
     * Check WebGL support
     */
    _isWebGLSupported() {
        try {
            const canvas = document.createElement('canvas');
            return !!(
                window.WebGLRenderingContext &&
                (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
            );
        } catch (e) {
            return false;
        }
    }

    /**
     * Static method to check WebGL support
     */
    static isWebGLSupported() {
        try {
            const canvas = document.createElement('canvas');
            return !!(
                window.WebGLRenderingContext &&
                (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
            );
        } catch (e) {
            return false;
        }
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AnimatedCharacterLoader;
}
if (typeof window !== 'undefined') {
    window.AnimatedCharacterLoader = AnimatedCharacterLoader;
}
