/**
 * Kyur Chat Widget - Digigami OA Integration
 * Brings Kyur to life as an interactive conversational avatar
 */

class KyurChat {
    constructor(options = {}) {
        this.options = {
            apiEndpoint: options.apiEndpoint || 'http://localhost:5000/api/v1/digigami',
            containerId: options.containerId || 'kyur-chat-container',
            characterShowcase: options.characterShowcase || 'character-showcase',
            autoGreet: options.autoGreet !== false,
            debug: options.debug || false
        };

        this.isOpen = false;
        this.isTyping = false;
        this.sessionId = this.generateSessionId();
        this.messageHistory = [];
        this.apiAvailable = false;
        this.kyurProfile = null;

        // Pose mapping for emotional responses
        this.poseMap = {
            default: 0,      // Kyur.png - neutral/default
            thinking: 1,     // Kyur2.png - processing/thinking
            excited: 2,      // Kyur3.png - happy/success
            pointing: 3      // Kyur4.png - explaining/guiding
        };

        this.init();
    }

    log(...args) {
        if (this.options.debug) {
            console.log('[KyurChat]', ...args);
        }
    }

    generateSessionId() {
        return 'kyur_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    }

    async init() {
        this.log('Initializing Kyur Chat...');

        // Create chat UI
        this.createChatUI();

        // Check API status
        await this.checkApiStatus();

        // Set up event listeners
        this.setupEventListeners();

        // Auto-greet after a delay
        if (this.options.autoGreet) {
            setTimeout(() => {
                if (!this.isOpen) {
                    this.showGreetingBubble();
                }
            }, 3000);
        }

        this.log('Kyur Chat initialized');
    }

    async checkApiStatus() {
        try {
            const response = await fetch(`${this.options.apiEndpoint}/status`, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.apiAvailable = true;
                this.kyurProfile = {
                    name: data.name,
                    role: data.role,
                    version: data.version
                };
                this.log('API connected:', data);
                this.updateConnectionStatus(true);
            }
        } catch (error) {
            this.log('API unavailable, using offline mode:', error.message);
            this.apiAvailable = false;
            this.updateConnectionStatus(false);
        }
    }

    createChatUI() {
        // Chat toggle button (floating)
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'kyur-chat-toggle';
        toggleBtn.className = 'kyur-chat-toggle';
        toggleBtn.innerHTML = `
            <span class="toggle-icon">💬</span>
            <span class="toggle-text">Chat with Kyur</span>
        `;
        toggleBtn.setAttribute('aria-label', 'Open chat with Kyur');

        // Chat panel
        const chatPanel = document.createElement('div');
        chatPanel.id = 'kyur-chat-panel';
        chatPanel.className = 'kyur-chat-panel';
        chatPanel.innerHTML = `
            <div class="kyur-chat-header">
                <div class="kyur-avatar-mini">
                    <img src="assets/characters-reference/Kyur.png" alt="Kyur">
                </div>
                <div class="kyur-info">
                    <span class="kyur-name">Kyur</span>
                    <span class="kyur-status">
                        <span class="status-dot"></span>
                        <span class="status-text">Connecting...</span>
                    </span>
                </div>
                <button class="kyur-chat-close" aria-label="Close chat">&times;</button>
            </div>
            <div class="kyur-chat-messages" id="kyur-messages"></div>
            <div class="kyur-chat-input-area">
                <div class="kyur-suggestions" id="kyur-suggestions"></div>
                <div class="kyur-input-row">
                    <input type="text" id="kyur-input" placeholder="Ask Kyur anything..." autocomplete="off">
                    <button id="kyur-send" class="kyur-send-btn" disabled>
                        <span>↑</span>
                    </button>
                </div>
            </div>
        `;

        // Greeting bubble (shows before chat is opened)
        const greetingBubble = document.createElement('div');
        greetingBubble.id = 'kyur-greeting';
        greetingBubble.className = 'kyur-greeting-bubble';
        greetingBubble.innerHTML = `
            <p>Hey! Need help creating your avatar? I'm Kyur!</p>
            <button class="greeting-dismiss">&times;</button>
        `;

        // Add to DOM
        document.body.appendChild(toggleBtn);
        document.body.appendChild(chatPanel);
        document.body.appendChild(greetingBubble);

        // Store references
        this.elements = {
            toggle: toggleBtn,
            panel: chatPanel,
            greeting: greetingBubble,
            messages: document.getElementById('kyur-messages'),
            input: document.getElementById('kyur-input'),
            sendBtn: document.getElementById('kyur-send'),
            suggestions: document.getElementById('kyur-suggestions'),
            closeBtn: chatPanel.querySelector('.kyur-chat-close'),
            statusDot: chatPanel.querySelector('.status-dot'),
            statusText: chatPanel.querySelector('.status-text')
        };

        // Inject styles
        this.injectStyles();
    }

    injectStyles() {
        const styles = document.createElement('style');
        styles.textContent = `
            /* Kyur Chat Toggle Button */
            .kyur-chat-toggle {
                position: fixed;
                bottom: 24px;
                right: 24px;
                background: linear-gradient(135deg, var(--color-primary, #6B5CE7) 0%, var(--color-accent, #00D9FF) 100%);
                color: white;
                border: none;
                border-radius: 50px;
                padding: 12px 20px;
                font-family: 'Quicksand', sans-serif;
                font-weight: 600;
                font-size: 14px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 4px 20px rgba(107, 92, 231, 0.4);
                transition: all 0.3s ease;
                z-index: 1000;
            }

            .kyur-chat-toggle:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 30px rgba(107, 92, 231, 0.5);
            }

            .kyur-chat-toggle .toggle-icon {
                font-size: 18px;
            }

            .kyur-chat-toggle.chat-open {
                opacity: 0;
                pointer-events: none;
            }

            /* Chat Panel */
            .kyur-chat-panel {
                position: fixed;
                bottom: 24px;
                right: 24px;
                width: 380px;
                max-width: calc(100vw - 48px);
                height: 520px;
                max-height: calc(100vh - 100px);
                background: rgba(20, 27, 45, 0.98);
                border-radius: 20px;
                border: 1px solid rgba(107, 92, 231, 0.3);
                box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                overflow: hidden;
                z-index: 1001;
                opacity: 0;
                transform: translateY(20px) scale(0.95);
                pointer-events: none;
                transition: all 0.3s ease;
            }

            .kyur-chat-panel.open {
                opacity: 1;
                transform: translateY(0) scale(1);
                pointer-events: auto;
            }

            /* Chat Header */
            .kyur-chat-header {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 16px;
                background: rgba(30, 39, 66, 0.8);
                border-bottom: 1px solid rgba(107, 92, 231, 0.2);
            }

            .kyur-avatar-mini {
                width: 44px;
                height: 44px;
                border-radius: 50%;
                overflow: hidden;
                background: linear-gradient(135deg, #1a1f35, #252d44);
                border: 2px solid rgba(107, 92, 231, 0.5);
            }

            .kyur-avatar-mini img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                object-position: top center;
            }

            .kyur-info {
                flex: 1;
            }

            .kyur-name {
                display: block;
                font-family: 'Righteous', cursive;
                font-size: 16px;
                color: white;
            }

            .kyur-status {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.6);
            }

            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #fbbf24;
            }

            .status-dot.online {
                background: #10b981;
            }

            .status-dot.offline {
                background: #ef4444;
            }

            .kyur-chat-close {
                background: none;
                border: none;
                color: rgba(255, 255, 255, 0.6);
                font-size: 24px;
                cursor: pointer;
                padding: 4px 8px;
                transition: color 0.2s;
            }

            .kyur-chat-close:hover {
                color: white;
            }

            /* Messages Area */
            .kyur-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .kyur-message {
                max-width: 85%;
                padding: 12px 16px;
                border-radius: 16px;
                font-size: 14px;
                line-height: 1.5;
                animation: messageIn 0.3s ease;
            }

            @keyframes messageIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .kyur-message.kyur {
                align-self: flex-start;
                background: rgba(107, 92, 231, 0.2);
                border: 1px solid rgba(107, 92, 231, 0.3);
                color: white;
            }

            .kyur-message.user {
                align-self: flex-end;
                background: linear-gradient(135deg, var(--color-primary, #6B5CE7), var(--color-accent, #00D9FF));
                color: white;
            }

            .kyur-message.typing {
                display: flex;
                gap: 4px;
                padding: 16px 20px;
            }

            .typing-dot {
                width: 8px;
                height: 8px;
                background: rgba(255, 255, 255, 0.5);
                border-radius: 50%;
                animation: typingBounce 1.4s infinite ease-in-out;
            }

            .typing-dot:nth-child(1) { animation-delay: 0s; }
            .typing-dot:nth-child(2) { animation-delay: 0.2s; }
            .typing-dot:nth-child(3) { animation-delay: 0.4s; }

            @keyframes typingBounce {
                0%, 80%, 100% { transform: translateY(0); }
                40% { transform: translateY(-6px); }
            }

            /* Input Area */
            .kyur-chat-input-area {
                padding: 12px 16px 16px;
                background: rgba(30, 39, 66, 0.5);
                border-top: 1px solid rgba(107, 92, 231, 0.2);
            }

            .kyur-suggestions {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 12px;
            }

            .kyur-suggestion {
                background: rgba(107, 92, 231, 0.15);
                border: 1px solid rgba(107, 92, 231, 0.3);
                border-radius: 20px;
                padding: 6px 12px;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.8);
                cursor: pointer;
                transition: all 0.2s;
            }

            .kyur-suggestion:hover {
                background: rgba(107, 92, 231, 0.3);
                color: white;
            }

            .kyur-input-row {
                display: flex;
                gap: 8px;
            }

            #kyur-input {
                flex: 1;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(107, 92, 231, 0.3);
                border-radius: 24px;
                padding: 12px 16px;
                font-size: 14px;
                color: white;
                outline: none;
                transition: border-color 0.2s;
            }

            #kyur-input:focus {
                border-color: rgba(107, 92, 231, 0.6);
            }

            #kyur-input::placeholder {
                color: rgba(255, 255, 255, 0.4);
            }

            .kyur-send-btn {
                width: 44px;
                height: 44px;
                border-radius: 50%;
                background: linear-gradient(135deg, var(--color-primary, #6B5CE7), var(--color-accent, #00D9FF));
                border: none;
                color: white;
                font-size: 18px;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .kyur-send-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .kyur-send-btn:not(:disabled):hover {
                transform: scale(1.05);
            }

            /* Greeting Bubble */
            .kyur-greeting-bubble {
                position: fixed;
                bottom: 90px;
                right: 24px;
                background: rgba(20, 27, 45, 0.98);
                border: 1px solid rgba(107, 92, 231, 0.3);
                border-radius: 16px;
                padding: 12px 16px;
                max-width: 260px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
                z-index: 999;
                opacity: 0;
                transform: translateY(10px);
                pointer-events: none;
                transition: all 0.3s ease;
            }

            .kyur-greeting-bubble.visible {
                opacity: 1;
                transform: translateY(0);
                pointer-events: auto;
            }

            .kyur-greeting-bubble p {
                color: white;
                font-size: 14px;
                margin: 0;
                padding-right: 20px;
            }

            .greeting-dismiss {
                position: absolute;
                top: 8px;
                right: 8px;
                background: none;
                border: none;
                color: rgba(255, 255, 255, 0.5);
                cursor: pointer;
                font-size: 16px;
            }

            /* Message sources */
            .message-sources {
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                font-size: 11px;
                color: rgba(255, 255, 255, 0.5);
            }

            .message-sources summary {
                cursor: pointer;
            }

            /* Mobile adjustments */
            @media (max-width: 480px) {
                .kyur-chat-panel {
                    width: calc(100vw - 16px);
                    height: calc(100vh - 80px);
                    bottom: 8px;
                    right: 8px;
                    border-radius: 16px;
                }

                .kyur-chat-toggle .toggle-text {
                    display: none;
                }
            }
        `;
        document.head.appendChild(styles);
    }

    setupEventListeners() {
        // Toggle chat
        this.elements.toggle.addEventListener('click', () => this.openChat());
        this.elements.closeBtn.addEventListener('click', () => this.closeChat());

        // Dismiss greeting
        this.elements.greeting.querySelector('.greeting-dismiss').addEventListener('click', () => {
            this.hideGreetingBubble();
        });

        // Click greeting to open chat
        this.elements.greeting.addEventListener('click', (e) => {
            if (!e.target.classList.contains('greeting-dismiss')) {
                this.hideGreetingBubble();
                this.openChat();
            }
        });

        // Send message
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
        this.elements.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Enable/disable send button based on input
        this.elements.input.addEventListener('input', () => {
            this.elements.sendBtn.disabled = !this.elements.input.value.trim();
        });

        // Close on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeChat();
            }
        });
    }

    updateConnectionStatus(online) {
        this.elements.statusDot.classList.toggle('online', online);
        this.elements.statusDot.classList.toggle('offline', !online);
        this.elements.statusText.textContent = online ? 'Online' : 'Offline mode';
    }

    showGreetingBubble() {
        this.elements.greeting.classList.add('visible');

        // Auto-hide after 10 seconds
        setTimeout(() => {
            this.hideGreetingBubble();
        }, 10000);
    }

    hideGreetingBubble() {
        this.elements.greeting.classList.remove('visible');
    }

    openChat() {
        this.isOpen = true;
        this.elements.panel.classList.add('open');
        this.elements.toggle.classList.add('chat-open');
        this.hideGreetingBubble();

        // Show welcome message if first time
        if (this.messageHistory.length === 0) {
            this.showWelcomeMessage();
        }

        // Focus input
        setTimeout(() => {
            this.elements.input.focus();
        }, 300);

        // Change Kyur's pose to excited when chat opens
        this.setKyurPose('excited');
    }

    closeChat() {
        this.isOpen = false;
        this.elements.panel.classList.remove('open');
        this.elements.toggle.classList.remove('chat-open');

        // Return to default pose
        this.setKyurPose('default');
    }

    showWelcomeMessage() {
        const greeting = this.kyurProfile?.greeting ||
            "Hey there! I'm Kyur, your Digigami guide! Ready to create something amazing? I'm here to help transform you into a stunning anime-style avatar. What kind of look are you going for?";

        this.addMessage(greeting, 'kyur');

        // Show suggestions
        this.showSuggestions([
            "How does it work?",
            "Show me the styles",
            "Tips for best results"
        ]);
    }

    showSuggestions(suggestions) {
        this.elements.suggestions.innerHTML = suggestions.map(s =>
            `<button class="kyur-suggestion">${s}</button>`
        ).join('');

        this.elements.suggestions.querySelectorAll('.kyur-suggestion').forEach(btn => {
            btn.addEventListener('click', () => {
                this.elements.input.value = btn.textContent;
                this.sendMessage();
            });
        });
    }

    addMessage(text, sender, sources = null) {
        const messageEl = document.createElement('div');
        messageEl.className = `kyur-message ${sender}`;
        messageEl.innerHTML = this.formatMessage(text);

        if (sources && sources.length > 0) {
            const sourcesHtml = `
                <details class="message-sources">
                    <summary>${sources.length} source${sources.length > 1 ? 's' : ''}</summary>
                    <ul>
                        ${sources.map(s => `<li>${s.title || s}</li>`).join('')}
                    </ul>
                </details>
            `;
            messageEl.innerHTML += sourcesHtml;
        }

        this.elements.messages.appendChild(messageEl);
        this.scrollToBottom();

        this.messageHistory.push({ text, sender, timestamp: Date.now() });
    }

    formatMessage(text) {
        // Simple markdown-like formatting
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        const typingEl = document.createElement('div');
        typingEl.className = 'kyur-message kyur typing';
        typingEl.id = 'kyur-typing';
        typingEl.innerHTML = `
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        `;
        this.elements.messages.appendChild(typingEl);
        this.scrollToBottom();

        // Set thinking pose
        this.setKyurPose('thinking');
    }

    hideTypingIndicator() {
        const typing = document.getElementById('kyur-typing');
        if (typing) typing.remove();
    }

    scrollToBottom() {
        this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
    }

    async sendMessage() {
        const text = this.elements.input.value.trim();
        if (!text || this.isTyping) return;

        // Add user message
        this.addMessage(text, 'user');
        this.elements.input.value = '';
        this.elements.sendBtn.disabled = true;

        // Clear suggestions
        this.elements.suggestions.innerHTML = '';

        // Show typing indicator
        this.isTyping = true;
        this.showTypingIndicator();

        try {
            let response;

            if (this.apiAvailable) {
                response = await this.fetchApiResponse(text);
            } else {
                response = this.getOfflineResponse(text);
            }

            this.hideTypingIndicator();
            this.addMessage(response.text, 'kyur', response.sources);

            // Set appropriate pose based on response
            if (response.text.includes('!') || response.text.includes('amazing') || response.text.includes('awesome')) {
                this.setKyurPose('excited');
            } else if (response.text.includes('?') || response.text.includes('tip') || response.text.includes('try')) {
                this.setKyurPose('pointing');
            } else {
                this.setKyurPose('default');
            }

            // Show follow-up suggestions if available
            if (response.suggestions) {
                this.showSuggestions(response.suggestions);
            }

        } catch (error) {
            this.log('Error sending message:', error);
            this.hideTypingIndicator();
            this.addMessage("Oops! I had trouble connecting. Let me try again in a moment.", 'kyur');
            this.setKyurPose('default');
        }

        this.isTyping = false;
    }

    async fetchApiResponse(message) {
        const response = await fetch(`${this.options.apiEndpoint}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId,
                include_sources: true
            })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        return {
            text: data.response,
            sources: data.sources || [],
            suggestions: this.generateSuggestions(message, data.response)
        };
    }

    getOfflineResponse(message) {
        // Offline response logic for demo/fallback
        const lowerMsg = message.toLowerCase();

        const responses = {
            'how': {
                text: "Great question! Here's how Digigami works:\n\n1. **Capture** - Use your camera to take a photo\n2. **Choose Style** - Pick from Vibrant Anime, Warm Cel-shade, Ghibli, or Bold Cel-shade\n3. **Transform** - Our AI converts your photo into a stylized avatar\n4. **Download** - Save your unique Digigami!\n\nReady to try it? Click the 'Create My Avatar' button!",
                suggestions: ["Tell me about the styles", "Tips for photos", "Can I customize it?"]
            },
            'style': {
                text: "We have 4 amazing art styles:\n\n**Vibrant Anime** - Expressive eyes, dynamic hair, and bold colors\n\n**Warm Cel-shade** - Soft lighting with detailed clothing and warm tones\n\n**Ghibli** - Soft, dreamy aesthetics with gentle colors\n\n**Bold Cel-shade** - Strong outlines with flat colors for a graphic novel feel\n\nWhich one catches your eye?",
                suggestions: ["Vibrant Anime style", "Warm Cel-shade", "Try Ghibli"]
            },
            'tip': {
                text: "Here are my top tips for amazing results:\n\n1. **Good lighting** - Face a window or soft light source\n2. **Neutral expression** - Or smile if you want that captured!\n3. **Face the camera** - Look directly at the lens\n4. **Plain background** - Helps the AI focus on you\n\nThe better your photo, the better your Digigami!",
                suggestions: ["Start creating!", "What styles are there?", "How does it work?"]
            },
            'default': {
                text: "I'm here to help you create your perfect Digigami avatar! You can ask me about:\n\n- How the transformation works\n- The different art styles available\n- Tips for getting the best results\n- Customization options\n\nWhat would you like to know?",
                suggestions: ["How does it work?", "Show me styles", "Tips please!"]
            }
        };

        // Match response
        for (const [key, data] of Object.entries(responses)) {
            if (key !== 'default' && lowerMsg.includes(key)) {
                return data;
            }
        }

        return responses.default;
    }

    generateSuggestions(userMessage, response) {
        // Generate contextual follow-up suggestions
        const suggestions = [];

        if (response.toLowerCase().includes('style')) {
            suggestions.push("Tell me more about styles");
        }
        if (response.toLowerCase().includes('photo') || response.toLowerCase().includes('camera')) {
            suggestions.push("Tips for best photos");
        }
        if (!suggestions.length) {
            suggestions.push("How do I start?", "What can you help with?");
        }

        return suggestions.slice(0, 3);
    }

    setKyurPose(pose) {
        // Update the main character showcase to match Kyur's emotional state
        const showcase = document.getElementById(this.options.characterShowcase);
        if (!showcase || !window.digigamiApp) return;

        const poseIndex = this.poseMap[pose] ?? 0;

        // Use the app's pose system
        if (window.digigamiApp.setActivePose) {
            window.digigamiApp.setActivePose(poseIndex);
        }
    }
}

// Initialize Kyur Chat when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for main app to initialize
    setTimeout(() => {
        window.kyurChat = new KyurChat({
            debug: true,
            autoGreet: true
        });
    }, 1000);
});
