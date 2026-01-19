/**
 * Digigami Character 3D Animator
 *
 * Three.js-based 3D character viewer with skeletal animation.
 * Mirrors SpriteAnimator.js API for drop-in replacement.
 *
 * Requires Three.js v0.160+ with GLTFLoader and DRACOLoader
 */

class Character3DAnimator {
    constructor(container, options = {}) {
        this.container = container;

        // Options
        this.fps = options.fps || 30;
        this.crossfadeDuration = options.crossfadeDuration || 0.3;
        this.onLoad = options.onLoad || (() => {});
        this.onError = options.onError || ((err) => console.error(err));

        // Three.js components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.model = null;
        this.mixer = null;
        this.clock = null;

        // Animation state
        this.animations = {};
        this.currentAction = null;
        this.currentAnimation = null;
        this.isPlaying = false;
        this.loop = true;
        this.animationId = null;

        // Performance settings
        this.pixelRatio = Math.min(window.devicePixelRatio, 2);

        this._initScene();
    }

    /**
     * Initialize Three.js scene
     */
    _initScene() {
        // Check for Three.js
        if (typeof THREE === 'undefined') {
            console.error('Three.js not loaded. Add Three.js CDN to your page.');
            return;
        }

        // Scene with transparent background
        this.scene = new THREE.Scene();

        // Camera - orthographic for 2D-like presentation
        const aspect = this.container.clientWidth / this.container.clientHeight;
        const frustumSize = 2;
        this.camera = new THREE.OrthographicCamera(
            -frustumSize * aspect / 2,
            frustumSize * aspect / 2,
            frustumSize / 2,
            -frustumSize / 2,
            0.1,
            100
        );
        this.camera.position.set(0, 1, 5);
        this.camera.lookAt(0, 1, 0);

        // Renderer with transparency
        this.renderer = new THREE.WebGLRenderer({
            alpha: true,
            antialias: true,
            powerPreference: 'low-power'
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(this.pixelRatio);
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.container.appendChild(this.renderer.domElement);

        // Lighting - soft ambient + directional
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 10, 7.5);
        this.scene.add(directionalLight);

        // Clock for animation timing
        this.clock = new THREE.Clock();

        // Handle resize
        this._boundResize = this._handleResize.bind(this);
        window.addEventListener('resize', this._boundResize);
    }

    /**
     * Load a character's animated GLB model
     */
    async load(character, basePath = '../characters-reference/3d_output/web') {
        const glbPath = `${basePath}/${character}-animated.glb`;

        console.log('Loading 3D model from:', glbPath);

        try {
            // Check for GLTFLoader
            if (typeof THREE.GLTFLoader === 'undefined') {
                // Try to use module version
                if (typeof GLTFLoader !== 'undefined') {
                    THREE.GLTFLoader = GLTFLoader;
                } else {
                    throw new Error('GLTFLoader not available. Include three/addons/loaders/GLTFLoader.js');
                }
            }

            const loader = new THREE.GLTFLoader();

            // Set up Draco decoder if available
            if (typeof THREE.DRACOLoader !== 'undefined' || typeof DRACOLoader !== 'undefined') {
                const dracoLoader = new (THREE.DRACOLoader || DRACOLoader)();
                dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
                loader.setDRACOLoader(dracoLoader);
            }

            // Load the model
            const gltf = await new Promise((resolve, reject) => {
                loader.load(
                    glbPath,
                    resolve,
                    (progress) => {
                        const percent = (progress.loaded / progress.total * 100).toFixed(0);
                        console.log(`Loading: ${percent}%`);
                    },
                    reject
                );
            });

            console.log('Model loaded:', gltf);

            // Remove old model if exists
            if (this.model) {
                this.scene.remove(this.model);
                this._disposeObject(this.model);
            }

            this.model = gltf.scene;
            this.scene.add(this.model);

            // Center and scale model
            this._fitModelToView();

            // Set up animation mixer
            this.mixer = new THREE.AnimationMixer(this.model);

            // Store animations by name
            this.animations = {};
            gltf.animations.forEach(clip => {
                console.log(`Animation found: ${clip.name} (${clip.duration.toFixed(2)}s)`);
                this.animations[clip.name.toLowerCase()] = clip;
            });

            // Render initial frame
            this.renderer.render(this.scene, this.camera);

            // Callback with metadata
            this.onLoad({
                animations: Object.keys(this.animations),
                model: this.model,
                meta: {
                    format: 'glb',
                    animationCount: gltf.animations.length
                }
            });

            return true;

        } catch (error) {
            console.error('Failed to load 3D model:', error);
            this.onError(error);
            return false;
        }
    }

    /**
     * Fit model to camera view
     */
    _fitModelToView() {
        if (!this.model) return;

        const box = new THREE.Box3().setFromObject(this.model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        // Center model
        this.model.position.x = -center.x;
        this.model.position.y = -box.min.y;
        this.model.position.z = -center.z;

        // Adjust camera to fit
        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.top - this.camera.bottom;
        const scale = fov / maxDim * 0.8;

        this.model.scale.setScalar(scale);
    }

    /**
     * Get available animation names
     */
    getAnimations() {
        return this.animations;
    }

    /**
     * Get animation names as array
     */
    getFrameNames() {
        return Object.keys(this.animations);
    }

    /**
     * Play a named animation
     */
    playAnimation(animationName, loop = true) {
        const normalizedName = animationName.toLowerCase();
        const clip = this.animations[normalizedName];

        if (!clip) {
            console.warn(`Animation "${animationName}" not found. Available:`, Object.keys(this.animations));
            return;
        }

        this.loop = loop;
        this.currentAnimation = normalizedName;

        const newAction = this.mixer.clipAction(clip);
        newAction.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, loop ? Infinity : 1);
        newAction.clampWhenFinished = !loop;

        // Crossfade from current action
        if (this.currentAction && this.currentAction !== newAction) {
            newAction.reset();
            newAction.play();
            this.currentAction.crossFadeTo(newAction, this.crossfadeDuration, true);
        } else {
            newAction.reset();
            newAction.play();
        }

        this.currentAction = newAction;
        this.play();
    }

    /**
     * Play all animations in sequence (for testing)
     */
    playAll(loop = true) {
        const names = Object.keys(this.animations);
        if (names.length > 0) {
            this.playAnimation(names[0], loop);
        }
    }

    /**
     * Show a specific animation frame (first frame, paused)
     */
    showFrame(animationName) {
        const normalizedName = animationName.toLowerCase();
        const clip = this.animations[normalizedName];

        if (!clip) {
            console.warn(`Animation "${animationName}" not found`);
            return;
        }

        this.currentAnimation = normalizedName;

        const action = this.mixer.clipAction(clip);
        action.reset();
        action.play();
        action.paused = true;
        action.time = 0;

        if (this.currentAction && this.currentAction !== action) {
            this.currentAction.stop();
        }
        this.currentAction = action;

        // Update mixer and render
        this.mixer.update(0);
        this.renderer.render(this.scene, this.camera);
    }

    /**
     * Start animation playback
     */
    play() {
        if (this.isPlaying) return;

        this.isPlaying = true;
        this.clock.start();

        if (this.currentAction) {
            this.currentAction.paused = false;
        }

        this._animate();
    }

    /**
     * Pause animation
     */
    pause() {
        this.isPlaying = false;

        if (this.currentAction) {
            this.currentAction.paused = true;
        }

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        // Render current state
        this.renderer.render(this.scene, this.camera);
    }

    /**
     * Stop and reset animation
     */
    stop() {
        this.pause();

        if (this.currentAction) {
            this.currentAction.reset();
            this.currentAction.time = 0;
            this.mixer.update(0);
            this.renderer.render(this.scene, this.camera);
        }
    }

    /**
     * Set animation speed (maps to Three.js timeScale)
     */
    setFPS(fps) {
        this.fps = fps;
        // Adjust mixer timeScale relative to 30fps base
        if (this.mixer) {
            this.mixer.timeScale = fps / 30;
        }
    }

    /**
     * Main animation loop
     */
    _animate() {
        if (!this.isPlaying) return;

        const delta = this.clock.getDelta();

        if (this.mixer) {
            this.mixer.update(delta);
        }

        this.renderer.render(this.scene, this.camera);

        this.animationId = requestAnimationFrame(() => this._animate());
    }

    /**
     * Handle window resize
     */
    _handleResize() {
        if (!this.container || !this.camera || !this.renderer) return;

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        const aspect = width / height;
        const frustumSize = 2;

        this.camera.left = -frustumSize * aspect / 2;
        this.camera.right = frustumSize * aspect / 2;
        this.camera.top = frustumSize / 2;
        this.camera.bottom = -frustumSize / 2;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
        this.renderer.render(this.scene, this.camera);
    }

    /**
     * Resize container (API compatibility with SpriteAnimator)
     */
    resize(scale) {
        // For 3D, we adjust camera zoom instead of canvas size
        if (this.camera) {
            this.camera.zoom = scale;
            this.camera.updateProjectionMatrix();
            this.renderer.render(this.scene, this.camera);
        }
    }

    /**
     * Clean up resources
     */
    dispose() {
        this.stop();

        window.removeEventListener('resize', this._boundResize);

        if (this.mixer) {
            this.mixer.stopAllAction();
            this.mixer = null;
        }

        if (this.model) {
            this.scene.remove(this.model);
            this._disposeObject(this.model);
            this.model = null;
        }

        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
            this.renderer = null;
        }

        this.scene = null;
        this.camera = null;
        this.animations = {};
    }

    /**
     * Recursively dispose of Three.js objects
     */
    _disposeObject(obj) {
        if (!obj) return;

        if (obj.geometry) {
            obj.geometry.dispose();
        }

        if (obj.material) {
            if (Array.isArray(obj.material)) {
                obj.material.forEach(m => this._disposeMaterial(m));
            } else {
                this._disposeMaterial(obj.material);
            }
        }

        if (obj.children) {
            obj.children.forEach(child => this._disposeObject(child));
        }
    }

    /**
     * Dispose of material and its textures
     */
    _disposeMaterial(material) {
        if (!material) return;

        Object.keys(material).forEach(key => {
            const value = material[key];
            if (value && typeof value.dispose === 'function') {
                value.dispose();
            }
        });

        material.dispose();
    }

    /**
     * Check if WebGL is available
     */
    static isSupported() {
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
    module.exports = Character3DAnimator;
}
if (typeof window !== 'undefined') {
    window.Character3DAnimator = Character3DAnimator;
}
