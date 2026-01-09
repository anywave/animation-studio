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
        this.inputMode = 'camera'; // 'camera', 'upload', or 'kyur'
        this.uploadedImageData = null;
        this.selectedKyurImage = null;

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
            galleryTrack: document.getElementById('gallery-track'),
            // New elements for upload/kyur modes
            modeBtns: document.querySelectorAll('.mode-btn'),
            cameraContainer: document.getElementById('camera-container'),
            uploadContainer: document.getElementById('upload-container'),
            kyurSelector: document.getElementById('kyur-selector'),
            uploadDropzone: document.getElementById('upload-dropzone'),
            fileInput: document.getElementById('file-input'),
            browseBtn: document.getElementById('browse-btn'),
            uploadPreview: document.getElementById('upload-preview'),
            previewImage: document.getElementById('preview-image'),
            removePreview: document.getElementById('remove-preview'),
            generateFromUpload: document.getElementById('generate-from-upload'),
            kyurOptions: document.querySelectorAll('.kyur-option'),
            generateFromKyur: document.getElementById('generate-from-kyur')
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

        // Input mode toggle
        this.elements.modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchInputMode(btn.dataset.mode);
            });
        });

        // File upload - browse button
        if (this.elements.browseBtn) {
            this.elements.browseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.elements.fileInput?.click();
            });
        }

        // File upload - dropzone click
        if (this.elements.uploadDropzone) {
            this.elements.uploadDropzone.addEventListener('click', (e) => {
                if (e.target === this.elements.uploadDropzone ||
                    e.target.closest('.dropzone-content')) {
                    this.elements.fileInput?.click();
                }
            });

            // Drag and drop
            this.elements.uploadDropzone.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.elements.uploadDropzone.classList.add('drag-over');
            });

            this.elements.uploadDropzone.addEventListener('dragleave', () => {
                this.elements.uploadDropzone.classList.remove('drag-over');
            });

            this.elements.uploadDropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                this.elements.uploadDropzone.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFileSelect(files[0]);
                }
            });
        }

        // File input change
        if (this.elements.fileInput) {
            this.elements.fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileSelect(e.target.files[0]);
                }
            });
        }

        // Remove preview button
        if (this.elements.removePreview) {
            this.elements.removePreview.addEventListener('click', () => {
                this.clearUploadPreview();
            });
        }

        // Generate from upload button
        if (this.elements.generateFromUpload) {
            this.elements.generateFromUpload.addEventListener('click', () => {
                if (this.uploadedImageData) {
                    this.handleCapture(this.uploadedImageData);
                }
            });
        }

        // Kyur option selection
        this.elements.kyurOptions.forEach(option => {
            option.addEventListener('click', () => {
                this.selectKyurOption(option);
            });
        });

        // Generate from Kyur button
        if (this.elements.generateFromKyur) {
            this.elements.generateFromKyur.addEventListener('click', () => {
                this.generateFromKyurImage();
            });
        }
    }

    /**
     * Switch between camera, upload, and kyur input modes
     */
    switchInputMode(mode) {
        this.inputMode = mode;

        // Update button active states
        this.elements.modeBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Show/hide containers
        if (this.elements.cameraContainer) {
            this.elements.cameraContainer.style.display = mode === 'camera' ? 'flex' : 'none';
        }
        if (this.elements.uploadContainer) {
            this.elements.uploadContainer.style.display = mode === 'upload' ? 'flex' : 'none';
        }
        if (this.elements.kyurSelector) {
            this.elements.kyurSelector.style.display = mode === 'kyur' ? 'block' : 'none';
        }

        // Stop camera when not in camera mode
        if (mode !== 'camera') {
            this.camera?.stop();
        } else {
            // Restart camera when switching back
            this.camera?.start();
        }

        console.log('Switched to input mode:', mode);
    }

    /**
     * Handle file selection from upload
     */
    handleFileSelect(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.uploadedImageData = e.target.result;

            // Show preview
            if (this.elements.previewImage) {
                this.elements.previewImage.src = this.uploadedImageData;
            }
            if (this.elements.uploadPreview) {
                this.elements.uploadPreview.style.display = 'flex';
            }
            document.querySelector('.dropzone-content')?.style.setProperty('display', 'none');

            // Enable generate button
            if (this.elements.generateFromUpload) {
                this.elements.generateFromUpload.disabled = false;
            }
        };
        reader.readAsDataURL(file);
    }

    /**
     * Clear upload preview
     */
    clearUploadPreview() {
        this.uploadedImageData = null;

        if (this.elements.uploadPreview) {
            this.elements.uploadPreview.style.display = 'none';
        }
        if (this.elements.previewImage) {
            this.elements.previewImage.src = '';
        }
        document.querySelector('.dropzone-content')?.style.setProperty('display', 'block');

        if (this.elements.generateFromUpload) {
            this.elements.generateFromUpload.disabled = true;
        }
        if (this.elements.fileInput) {
            this.elements.fileInput.value = '';
        }
    }

    /**
     * Select a Kyur reference option
     */
    selectKyurOption(option) {
        // Remove previous selection
        this.elements.kyurOptions.forEach(opt => {
            opt.classList.remove('selected');
        });

        // Mark new selection
        option.classList.add('selected');
        this.selectedKyurImage = option.dataset.src;

        // Enable generate button
        if (this.elements.generateFromKyur) {
            this.elements.generateFromKyur.disabled = false;
        }

        console.log('Selected Kyur image:', this.selectedKyurImage);
    }

    /**
     * Generate avatar from selected Kyur image
     */
    async generateFromKyurImage() {
        if (!this.selectedKyurImage) {
            alert('Please select a Kyur pose first');
            return;
        }

        // Load the Kyur image and convert to base64
        try {
            const response = await fetch(this.selectedKyurImage);
            const blob = await response.blob();
            const reader = new FileReader();

            reader.onload = (e) => {
                const imageData = e.target.result;
                this.handleCapture(imageData);
            };

            reader.readAsDataURL(blob);
        } catch (error) {
            console.error('Error loading Kyur image:', error);
            alert('Failed to load the selected image. Please try again.');
        }
    }

    /**
     * Open creation modal (supports camera, upload, and kyur modes)
     */
    async openCameraModal() {
        // Show modal
        this.elements.modal?.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Reset UI
        this.hideProgress();
        this.hideResult();

        // Check camera support and adjust initial mode
        if (!CameraCapture.isSupported()) {
            console.warn('Camera not supported, defaulting to upload mode');
            this.switchInputMode('upload');
        } else if (this.inputMode === 'camera') {
            // Initialize and start camera only if in camera mode
            if (this.camera.init()) {
                this.camera.on('capture', (imageData) => {
                    this.handleCapture(imageData);
                });
                await this.camera.start();
            }
        }
    }

    /**
     * Close creation modal and cleanup
     */
    closeCameraModal() {
        this.elements.modal?.classList.remove('active');
        document.body.style.overflow = '';

        // Stop camera
        this.camera?.stop();

        // Reset state
        this.isGenerating = false;

        // Clear upload preview
        this.clearUploadPreview();

        // Clear Kyur selection
        this.elements.kyurOptions.forEach(opt => opt.classList.remove('selected'));
        this.selectedKyurImage = null;
        if (this.elements.generateFromKyur) {
            this.elements.generateFromKyur.disabled = true;
        }
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
     * Set up character pose showcase
     */
    setupPoseShowcase() {
        const showcase = document.getElementById('character-showcase');
        if (!showcase) return;

        const characters = showcase.querySelectorAll('.showcase-character');
        const dots = showcase.querySelectorAll('.pose-dot');

        // Click handler for pose navigation dots
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                this.setActivePose(index);
            });
        });

        // Store references
        this.poseElements = { characters, dots };
        this.currentPose = 0;
    }

    /**
     * Set active pose by index
     */
    setActivePose(index) {
        if (!this.poseElements) return;

        const { characters, dots } = this.poseElements;

        // Update characters
        characters.forEach((char, i) => {
            char.classList.toggle('active', i === index);
        });

        // Update dots
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === index);
        });

        this.currentPose = index;
    }

    /**
     * Cycle to next pose
     */
    nextPose() {
        if (!this.poseElements) return;
        const nextIndex = (this.currentPose + 1) % this.poseElements.characters.length;
        this.setActivePose(nextIndex);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.digigamiApp = new DigigamiApp();

    // Set up pose showcase after app init
    window.digigamiApp.setupPoseShowcase();
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

// Auto-cycle through poses every 4 seconds
setInterval(() => {
    if (window.digigamiApp) {
        window.digigamiApp.nextPose();
    }
}, 4000);

// =============================================================================
// LEARN SECTION - Parameter Sliders
// =============================================================================

function initParameterSliders() {
    const sliders = {
        'slider-temp': { display: 'param-temp', decimals: 1 },
        'slider-topp': { display: 'param-topp', decimals: 2 },
        'slider-topk': { display: 'param-topk', decimals: 0 },
        'slider-maxtkn': { display: 'param-maxtkn', decimals: 0 }
    };
    
    Object.keys(sliders).forEach(sliderId => {
        const slider = document.getElementById(sliderId);
        const config = sliders[sliderId];
        
        if (slider) {
            slider.addEventListener('input', (e) => {
                const display = document.getElementById(config.display);
                if (display) {
                    display.textContent = parseFloat(e.target.value).toFixed(config.decimals);
                }
            });
        }
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    initParameterSliders();
});
