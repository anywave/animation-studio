/**
 * Digigami - Main Application Controller
 * Coordinates camera, websocket, and UI interactions
 */

class DigigamiApp {
    constructor() {
        this.camera = null;
        this.websocket = null;
        this.selectedStyle = 'kingdom-hearts';
        this.isGenerating = false;

        this.elements = {
            modal: document.getElementById('camera-modal'),
            modalClose: document.getElementById('modal-close'),
            startCameraBtn: document.getElementById('start-camera-btn'),
            ctaCameraBtn: document.getElementById('cta-camera-btn'),
            captureBtn: document.getElementById('capture-btn'),
            styleOptions: document.querySelectorAll('.style-option'),
            progressSection: document.getElementById('generation-progress'),
            progressBar: document.getElementById('progress-bar'),
            progressPercent: document.getElementById('progress-percent'),
            progressText: document.getElementById('progress-text'),
            resultSection: document.getElementById('result-preview'),
            originalPhoto: document.getElementById('original-photo'),
            generatedAvatar: document.getElementById('generated-avatar'),
            retryBtn: document.getElementById('retry-btn'),
            downloadBtn: document.getElementById('download-btn'),
            galleryTrack: document.getElementById('gallery-track')
        };

        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('Digigami App initializing...');

        // Initialize camera system
        this.camera = new CameraCapture();

        // Try real WebSocket connection first, fall back to mock
        this.websocket = new DigigamiWebSocket({
            url: 'ws://localhost:8765/ws',
            debug: true
        });

        // Set up WebSocket callbacks
        this.setupWebSocketCallbacks();

        // Set up UI event handlers
        this.setupEventHandlers();

        // Connect to WebSocket server
        try {
            await this.websocket.connect();
            console.log('Connected to style transfer backend');
        } catch (error) {
            console.warn('Backend unavailable, falling back to mock mode');
            this.websocket = new DigigamiWebSocketMock({ debug: true });
            this.setupWebSocketCallbacks();
            await this.websocket.connect();
        }

        // Duplicate gallery items for infinite scroll effect
        this.setupGalleryScroll();

        console.log('Digigami App ready');
    }

    /**
     * Set up WebSocket callbacks
     */
    setupWebSocketCallbacks() {
        this.websocket
            .on('connect', (sessionId) => {
                console.log('Connected with session:', sessionId);
            })
            .on('progress', (data) => {
                this.updateProgress(data.percent, data.stage, data.message);
            })
            .on('result', (data) => {
                this.handleGenerationResult(data);
            })
            .on('error', (error) => {
                this.handleGenerationError(error);
            });
    }

    /**
     * Set up UI event handlers
     */
    setupEventHandlers() {
        // Open camera modal buttons
        [this.elements.startCameraBtn, this.elements.ctaCameraBtn].forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => this.openCameraModal());
            }
        });

        // Close modal
        if (this.elements.modalClose) {
            this.elements.modalClose.addEventListener('click', () => this.closeCameraModal());
        }

        // Modal backdrop click to close
        if (this.elements.modal) {
            this.elements.modal.querySelector('.modal-backdrop')?.addEventListener('click', () => {
                this.closeCameraModal();
            });
        }

        // Style selection
        this.elements.styleOptions.forEach(option => {
            option.addEventListener('click', () => {
                this.selectStyle(option.dataset.style);
            });
        });

        // Retry button
        if (this.elements.retryBtn) {
            this.elements.retryBtn.addEventListener('click', () => this.resetCapture());
        }

        // Download button
        if (this.elements.downloadBtn) {
            this.elements.downloadBtn.addEventListener('click', () => this.downloadAvatar());
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.elements.modal?.classList.contains('active')) {
                this.closeCameraModal();
            }
        });

        // Smooth scroll for nav links
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

    /**
     * Open camera modal and start camera
     */
    async openCameraModal() {
        if (!CameraCapture.isSupported()) {
            alert('Camera is not supported in your browser. Please try Chrome, Firefox, or Safari.');
            return;
        }

        // Show modal
        this.elements.modal?.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Reset UI
        this.hideProgress();
        this.hideResult();

        // Initialize and start camera
        if (this.camera.init()) {
            this.camera.on('capture', (imageData) => {
                this.handleCapture(imageData);
            });

            await this.camera.start();
        }
    }

    /**
     * Close camera modal and stop camera
     */
    closeCameraModal() {
        this.elements.modal?.classList.remove('active');
        document.body.style.overflow = '';

        // Stop camera
        this.camera.stop();

        // Reset state
        this.isGenerating = false;
    }

    /**
     * Select avatar style
     */
    selectStyle(style) {
        this.selectedStyle = style;

        // Update UI
        this.elements.styleOptions.forEach(option => {
            option.classList.toggle('active', option.dataset.style === style);
        });

        console.log('Selected style:', style);
    }

    /**
     * Handle photo capture
     */
    handleCapture(imageData) {
        console.log('Photo captured, starting generation...');

        // Show original photo
        if (this.elements.originalPhoto) {
            this.elements.originalPhoto.src = imageData;
        }

        // Stop camera during processing
        this.camera.stop();

        // Show progress UI
        this.showProgress();

        // Start avatar generation
        this.isGenerating = true;
        this.websocket.generateAvatar(imageData, {
            style: this.selectedStyle,
            preserveExpression: true,
            enhanceDetails: true,
            outputSize: 512
        });
    }

    /**
     * Update progress display
     */
    updateProgress(percent, stage, message) {
        if (this.elements.progressPercent) {
            this.elements.progressPercent.textContent = `${percent}%`;
        }

        if (this.elements.progressText) {
            this.elements.progressText.textContent = message || stage;
        }

        if (this.elements.progressBar) {
            // SVG circle progress (circumference = 2 * PI * 45 = ~283)
            const circumference = 283;
            const offset = circumference - (percent / 100) * circumference;
            this.elements.progressBar.style.strokeDashoffset = offset;
        }
    }

    /**
     * Handle successful generation result
     */
    handleGenerationResult(data) {
        console.log('Generation complete:', data);
        this.isGenerating = false;

        if (data.success) {
            // Show generated avatar
            if (this.elements.generatedAvatar) {
                this.elements.generatedAvatar.src = data.avatarData || data.avatarUrl;
            }

            // Hide progress, show result
            this.hideProgress();
            this.showResult();
        } else {
            this.handleGenerationError({ message: 'Generation failed' });
        }
    }

    /**
     * Handle generation error
     */
    handleGenerationError(error) {
        console.error('Generation error:', error);
        this.isGenerating = false;

        // Show error in progress text
        if (this.elements.progressText) {
            this.elements.progressText.textContent = error.message || 'An error occurred';
            this.elements.progressText.style.color = '#ef4444';
        }

        // Allow retry after a moment
        setTimeout(() => {
            this.resetCapture();
        }, 2000);
    }

    /**
     * Show progress section
     */
    showProgress() {
        if (this.elements.progressSection) {
            this.elements.progressSection.style.display = 'block';
        }
        this.updateProgress(0, 'Starting', 'Initializing...');

        // Hide camera controls during generation
        const cameraContainer = document.querySelector('.camera-container');
        if (cameraContainer) cameraContainer.style.display = 'none';
    }

    /**
     * Hide progress section
     */
    hideProgress() {
        if (this.elements.progressSection) {
            this.elements.progressSection.style.display = 'none';
        }
    }

    /**
     * Show result section
     */
    showResult() {
        if (this.elements.resultSection) {
            this.elements.resultSection.style.display = 'block';
        }
    }

    /**
     * Hide result section
     */
    hideResult() {
        if (this.elements.resultSection) {
            this.elements.resultSection.style.display = 'none';
        }
    }

    /**
     * Reset capture to try again
     */
    resetCapture() {
        this.hideProgress();
        this.hideResult();

        // Reset progress text color
        if (this.elements.progressText) {
            this.elements.progressText.style.color = '';
        }

        // Show camera and restart
        const cameraContainer = document.querySelector('.camera-container');
        if (cameraContainer) cameraContainer.style.display = 'flex';

        this.camera.init();
        this.camera.on('capture', (imageData) => {
            this.handleCapture(imageData);
        });
        this.camera.start();
    }

    /**
     * Download generated avatar
     */
    downloadAvatar() {
        const avatarSrc = this.elements.generatedAvatar?.src;
        if (!avatarSrc) return;

        const link = document.createElement('a');
        link.href = avatarSrc;
        link.download = `digigami-avatar-${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        console.log('Avatar downloaded');
    }

    /**
     * Set up infinite gallery scroll
     */
    setupGalleryScroll() {
        const track = this.elements.galleryTrack;
        if (!track) return;

        // Clone items for seamless loop
        const items = track.innerHTML;
        track.innerHTML = items + items;
    }

    /**
     * Update character preview in hero section
     */
    updateHeroPreview(index) {
        const characters = [
            'assets/characters-reference/Gwynn.png',
            'assets/characters-reference/Kyur.png',
            'assets/characters-reference/Urahara.png',
            'assets/characters-reference/Yoroiche.png'
        ];

        const preview = document.getElementById('preview-character');
        if (preview && characters[index]) {
            preview.style.opacity = 0;
            setTimeout(() => {
                preview.src = characters[index];
                preview.style.opacity = 1;
            }, 300);
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.digigamiApp = new DigigamiApp();
});

// Add progress gradient SVG definition
document.addEventListener('DOMContentLoaded', () => {
    const svgDefs = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svgDefs.innerHTML = `
        <defs>
            <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#6B5CE7"/>
                <stop offset="50%" style="stop-color:#00D9FF"/>
                <stop offset="100%" style="stop-color:#FF6B35"/>
            </linearGradient>
        </defs>
    `;
    svgDefs.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;';
    document.body.insertBefore(svgDefs, document.body.firstChild);
});

// Cycle hero character preview
let heroCharacterIndex = 0;
setInterval(() => {
    if (window.digigamiApp) {
        heroCharacterIndex = (heroCharacterIndex + 1) % 4;
        window.digigamiApp.updateHeroPreview(heroCharacterIndex);
    }
}, 5000);
