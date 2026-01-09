/**
 * Digigami - WebSocket Client for Avatar Generation
 * Handles real-time communication with the style transfer backend
 */

class DigigamiWebSocket {
    constructor(options = {}) {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.sessionId = null;

        this.config = {
            url: options.url || 'ws://localhost:8765',
            autoReconnect: options.autoReconnect !== false,
            debug: options.debug || false
        };

        this.callbacks = {
            onConnect: null,
            onDisconnect: null,
            onError: null,
            onProgress: null,
            onResult: null,
            onStatusUpdate: null
        };

        this.statusElement = document.getElementById('ws-status');
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        return new Promise((resolve, reject) => {
            try {
                this.updateStatusUI('connecting');
                this.log('Connecting to:', this.config.url);

                this.socket = new WebSocket(this.config.url);

                this.socket.onopen = () => {
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this.sessionId = this.generateSessionId();
                    this.updateStatusUI('connected');
                    this.log('Connected, session:', this.sessionId);

                    // Send handshake
                    this.send('handshake', { sessionId: this.sessionId });

                    if (this.callbacks.onConnect) {
                        this.callbacks.onConnect(this.sessionId);
                    }
                    resolve(this.sessionId);
                };

                this.socket.onclose = (event) => {
                    this.isConnected = false;
                    this.updateStatusUI('disconnected');
                    this.log('Disconnected:', event.code, event.reason);

                    if (this.callbacks.onDisconnect) {
                        this.callbacks.onDisconnect(event);
                    }

                    // Auto reconnect
                    if (this.config.autoReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.scheduleReconnect();
                    }
                };

                this.socket.onerror = (error) => {
                    this.updateStatusUI('error');
                    this.log('Error:', error);

                    if (this.callbacks.onError) {
                        this.callbacks.onError(error);
                    }
                    reject(error);
                };

                this.socket.onmessage = (event) => {
                    this.handleMessage(event);
                };

            } catch (error) {
                this.updateStatusUI('error');
                reject(error);
            }
        });
    }

    /**
     * Handle incoming messages
     */
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.log('Received:', data.type, data);

            switch (data.type) {
                case 'handshake_ack':
                    this.log('Handshake acknowledged');
                    break;

                case 'progress':
                    if (this.callbacks.onProgress) {
                        this.callbacks.onProgress({
                            percent: data.percent || 0,
                            stage: data.stage || 'Processing',
                            message: data.message || ''
                        });
                    }
                    break;

                case 'result':
                    if (this.callbacks.onResult) {
                        this.callbacks.onResult({
                            success: data.success,
                            avatarUrl: data.avatarUrl,
                            avatarData: data.avatarData,
                            metadata: data.metadata || {}
                        });
                    }
                    break;

                case 'error':
                    if (this.callbacks.onError) {
                        this.callbacks.onError({
                            code: data.code,
                            message: data.message
                        });
                    }
                    break;

                case 'status':
                    if (this.callbacks.onStatusUpdate) {
                        this.callbacks.onStatusUpdate(data);
                    }
                    break;

                default:
                    this.log('Unknown message type:', data.type);
            }

        } catch (error) {
            this.log('Message parse error:', error);
        }
    }

    /**
     * Send message to server
     */
    send(type, payload = {}) {
        if (!this.isConnected || !this.socket) {
            this.log('Cannot send - not connected');
            return false;
        }

        const message = JSON.stringify({
            type,
            sessionId: this.sessionId,
            timestamp: Date.now(),
            ...payload
        });

        this.socket.send(message);
        this.log('Sent:', type, payload);
        return true;
    }

    /**
     * Request avatar generation
     */
    generateAvatar(imageData, options = {}) {
        return this.send('generate_avatar', {
            image: imageData,
            style: options.style || 'kingdom-hearts',
            options: {
                preserveExpression: options.preserveExpression !== false,
                enhanceDetails: options.enhanceDetails !== false,
                outputSize: options.outputSize || 512
            }
        });
    }

    /**
     * Cancel ongoing generation
     */
    cancelGeneration() {
        return this.send('cancel_generation');
    }

    /**
     * Request style list
     */
    requestStyles() {
        return this.send('get_styles');
    }

    /**
     * Disconnect from server
     */
    disconnect() {
        this.config.autoReconnect = false;
        if (this.socket) {
            this.socket.close(1000, 'Client disconnect');
        }
        this.isConnected = false;
        this.updateStatusUI('disconnected');
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * this.reconnectAttempts;

        this.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        this.updateStatusUI('reconnecting');

        setTimeout(() => {
            this.connect().catch(() => {
                // Reconnect failed, will retry if attempts remain
            });
        }, delay);
    }

    /**
     * Update status UI element
     */
    updateStatusUI(status) {
        if (!this.statusElement) return;

        const textEl = this.statusElement.querySelector('.ws-text');
        this.statusElement.className = 'ws-status';

        switch (status) {
            case 'connecting':
                if (textEl) textEl.textContent = 'Connecting...';
                break;
            case 'connected':
                this.statusElement.classList.add('connected');
                if (textEl) textEl.textContent = 'Connected';
                break;
            case 'disconnected':
                if (textEl) textEl.textContent = 'Disconnected';
                break;
            case 'reconnecting':
                if (textEl) textEl.textContent = `Reconnecting (${this.reconnectAttempts})...`;
                break;
            case 'error':
                this.statusElement.classList.add('error');
                if (textEl) textEl.textContent = 'Connection error';
                break;
        }
    }

    /**
     * Generate unique session ID
     */
    generateSessionId() {
        return 'digi_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Set callback handlers
     */
    on(event, callback) {
        const callbackName = `on${event.charAt(0).toUpperCase() + event.slice(1)}`;
        if (this.callbacks.hasOwnProperty(callbackName)) {
            this.callbacks[callbackName] = callback;
        }
        return this;
    }

    /**
     * Debug logging
     */
    log(...args) {
        if (this.config.debug) {
            console.log('[Digigami WS]', ...args);
        }
    }

    /**
     * Check WebSocket support
     */
    static isSupported() {
        return 'WebSocket' in window;
    }
}

// Fallback mock for development without server
class DigigamiWebSocketMock extends DigigamiWebSocket {
    connect() {
        return new Promise((resolve) => {
            this.isConnected = true;
            this.sessionId = this.generateSessionId();
            this.updateStatusUI('connected');
            this.log('Mock connected, session:', this.sessionId);

            if (this.callbacks.onConnect) {
                this.callbacks.onConnect(this.sessionId);
            }
            resolve(this.sessionId);
        });
    }

    generateAvatar(imageData, options = {}) {
        this.log('Mock generating avatar with style:', options.style);

        // Simulate progress
        const stages = [
            { percent: 10, stage: 'Analyzing features', message: 'Detecting facial landmarks...' },
            { percent: 30, stage: 'Extracting style', message: 'Processing style parameters...' },
            { percent: 50, stage: 'Generating base', message: 'Creating base avatar...' },
            { percent: 70, stage: 'Applying style', message: 'Applying anime style transfer...' },
            { percent: 90, stage: 'Refining details', message: 'Adding final touches...' },
            { percent: 100, stage: 'Complete', message: 'Avatar generated!' }
        ];

        let stageIndex = 0;
        const progressInterval = setInterval(() => {
            if (stageIndex < stages.length) {
                if (this.callbacks.onProgress) {
                    this.callbacks.onProgress(stages[stageIndex]);
                }
                stageIndex++;
            } else {
                clearInterval(progressInterval);

                // Return mock result (use the input image for demo)
                setTimeout(() => {
                    if (this.callbacks.onResult) {
                        this.callbacks.onResult({
                            success: true,
                            avatarData: imageData, // In real impl, this would be transformed
                            metadata: {
                                style: options.style,
                                processingTime: 3000,
                                model: 'digigami-v1-mock'
                            }
                        });
                    }
                }, 500);
            }
        }, 500);

        return true;
    }

    disconnect() {
        this.isConnected = false;
        this.updateStatusUI('disconnected');
    }
}

// Export for use
window.DigigamiWebSocket = DigigamiWebSocket;
window.DigigamiWebSocketMock = DigigamiWebSocketMock;
