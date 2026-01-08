/**
 * Digigami - Camera Capture System
 * Handles webcam access, photo capture, and preview functionality
 */

class CameraCapture {
    constructor() {
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.stream = null;
        this.isReady = false;
        this.capturedImage = null;

        this.config = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 960 },
                facingMode: 'user'
            }
        };

        this.elements = {
            video: null,
            canvas: null,
            captureBtn: null,
            status: null,
            modal: null
        };

        this.callbacks = {
            onCapture: null,
            onError: null,
            onReady: null
        };
    }

    /**
     * Initialize camera system with element references
     */
    init(elements = {}) {
        this.elements = {
            video: elements.video || document.getElementById('camera-feed'),
            canvas: elements.canvas || document.getElementById('capture-canvas'),
            captureBtn: elements.captureBtn || document.getElementById('capture-btn'),
            status: elements.status || document.getElementById('camera-status'),
            modal: elements.modal || document.getElementById('camera-modal')
        };

        if (!this.elements.video || !this.elements.canvas) {
            console.error('Camera elements not found');
            return false;
        }

        this.canvas = this.elements.canvas;
        this.ctx = this.canvas.getContext('2d');
        this.video = this.elements.video;

        // Bind capture button
        if (this.elements.captureBtn) {
            this.elements.captureBtn.addEventListener('click', () => this.capture());
        }

        return true;
    }

    /**
     * Start camera stream
     */
    async start() {
        try {
            this.updateStatus('Requesting camera access...', 'loading');

            // Check for camera support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Camera not supported in this browser');
            }

            // Request camera access
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: this.config.video,
                audio: false
            });

            // Attach stream to video element
            this.video.srcObject = this.stream;

            // Wait for video to be ready
            await new Promise((resolve, reject) => {
                this.video.onloadedmetadata = () => {
                    this.video.play()
                        .then(resolve)
                        .catch(reject);
                };
                this.video.onerror = reject;
            });

            // Set canvas dimensions to match video
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;

            this.isReady = true;
            this.updateStatus('Camera ready', 'ready');

            // Enable capture button
            if (this.elements.captureBtn) {
                this.elements.captureBtn.disabled = false;
            }

            if (this.callbacks.onReady) {
                this.callbacks.onReady();
            }

            return true;

        } catch (error) {
            console.error('Camera error:', error);
            this.handleError(error);
            return false;
        }
    }

    /**
     * Stop camera stream
     */
    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.video) {
            this.video.srcObject = null;
        }

        this.isReady = false;

        if (this.elements.captureBtn) {
            this.elements.captureBtn.disabled = true;
        }
    }

    /**
     * Capture current frame
     */
    capture() {
        if (!this.isReady) {
            console.warn('Camera not ready');
            return null;
        }

        // Draw current frame to canvas
        this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

        // Get image data
        this.capturedImage = this.canvas.toDataURL('image/jpeg', 0.9);

        // Flash effect
        this.flashEffect();

        // Trigger callback
        if (this.callbacks.onCapture) {
            this.callbacks.onCapture(this.capturedImage);
        }

        return this.capturedImage;
    }

    /**
     * Get captured image as blob
     */
    async getCapturedBlob() {
        if (!this.capturedImage) return null;

        return new Promise((resolve) => {
            this.canvas.toBlob((blob) => {
                resolve(blob);
            }, 'image/jpeg', 0.9);
        });
    }

    /**
     * Camera flash effect
     */
    flashEffect() {
        const flash = document.createElement('div');
        flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: white;
            opacity: 0.8;
            z-index: 9999;
            pointer-events: none;
            animation: flash 0.3s ease-out forwards;
        `;

        // Add flash animation if not exists
        if (!document.getElementById('flash-style')) {
            const style = document.createElement('style');
            style.id = 'flash-style';
            style.textContent = `
                @keyframes flash {
                    0% { opacity: 0.8; }
                    100% { opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(flash);
        setTimeout(() => flash.remove(), 300);
    }

    /**
     * Update status display
     */
    updateStatus(message, state = 'loading') {
        if (!this.elements.status) return;

        const statusText = this.elements.status.querySelector('span:last-child');
        if (statusText) {
            statusText.textContent = message;
        }

        this.elements.status.className = 'camera-status';
        if (state === 'ready') {
            this.elements.status.classList.add('ready');
        } else if (state === 'error') {
            this.elements.status.classList.add('error');
        }
    }

    /**
     * Handle camera errors
     */
    handleError(error) {
        let message = 'Camera error';

        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            message = 'Camera access denied. Please allow camera permissions.';
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            message = 'No camera found. Please connect a camera.';
        } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
            message = 'Camera is in use by another app.';
        } else if (error.name === 'OverconstrainedError') {
            message = 'Camera resolution not supported.';
        } else {
            message = error.message || 'Unknown camera error';
        }

        this.updateStatus(message, 'error');

        if (this.callbacks.onError) {
            this.callbacks.onError(message, error);
        }
    }

    /**
     * Set callback handlers
     */
    on(event, callback) {
        if (this.callbacks.hasOwnProperty(`on${event.charAt(0).toUpperCase() + event.slice(1)}`)) {
            this.callbacks[`on${event.charAt(0).toUpperCase() + event.slice(1)}`] = callback;
        }
        return this;
    }

    /**
     * Check if camera is supported
     */
    static isSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    /**
     * List available cameras
     */
    static async listCameras() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
            return [];
        }

        const devices = await navigator.mediaDevices.enumerateDevices();
        return devices.filter(device => device.kind === 'videoinput');
    }
}

// Export for use
window.CameraCapture = CameraCapture;
