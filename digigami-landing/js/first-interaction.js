/**
 * First Interaction - Emoji Selection Integration
 * Extends KyurChat with first interaction emoji selection flow
 */

(function() {
    // Wait for KyurChat to be defined
    const waitForKyurChat = setInterval(() => {
        if (typeof KyurChat === 'undefined') return;
        clearInterval(waitForKyurChat);

        // Add new properties
        const originalInit = KyurChat.prototype.init;
        KyurChat.prototype.init = async function() {
            this.firstInteractionComplete = false;
            this.selectedEmoji = null;
            this.awaitingEmoji = false;
            return originalInit.call(this);
        };

        // Override sendMessage
        const originalSendMessage = KyurChat.prototype.sendMessage;

        KyurChat.prototype.sendMessage = async function() {
            const text = this.elements.input.value.trim();
            if (!text || this.isTyping) return;

            // Check if first interaction (and API available)
            if (!this.firstInteractionComplete && this.apiAvailable) {
                this.addMessage(text, 'user');
                this.elements.input.value = '';
                this.elements.sendBtn.disabled = true;
                this.elements.suggestions.innerHTML = '';

                this.isTyping = true;
                this.showTypingIndicator();

                try {
                    const response = await fetch(this.options.apiEndpoint + '/first-interaction', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: this.sessionId,
                            message: text
                        })
                    });

                    const data = await response.json();
                    this.hideTypingIndicator();

                    if (data.intercept) {
                        // Show emoji selection prompt
                        this.addMessage(data.response, 'kyur');
                        this.showEmojiSelector(data.emoji_options);
                        this.awaitingEmoji = true;
                    } else if (data.emoji) {
                        // Emoji was selected
                        this.firstInteractionComplete = true;
                        this.selectedEmoji = data.emoji;
                        this.awaitingEmoji = false;
                        this.addMessage(data.emoji + ' - Wonderful choice! That emoji will become your Digital Twin\'s icon. Now, let me help you...', 'kyur');

                        // Answer the original question
                        if (data.original_message) {
                            setTimeout(() => {
                                this.elements.input.value = data.original_message;
                                this.firstInteractionComplete = true;
                                originalSendMessage.call(this);
                            }, 1500);
                        }
                    } else {
                        this.firstInteractionComplete = true;
                    }

                } catch (error) {
                    console.error('[KyurChat] First interaction error:', error);
                    this.hideTypingIndicator();
                    this.firstInteractionComplete = true;
                    this.elements.input.value = text;
                    originalSendMessage.call(this);
                }

                this.isTyping = false;
                return;
            }

            // Normal message flow
            return originalSendMessage.call(this);
        };

        KyurChat.prototype.showEmojiSelector = function(options) {
            // Create inline emoji grid
            const emojiContainer = document.createElement('div');
            emojiContainer.className = 'emoji-selector-inline';

            let gridHTML = '<div class="emoji-grid-inline">';
            options.forEach(function(opt) {
                gridHTML += '<button class="emoji-btn-inline" data-emoji="' + opt.emoji + '" data-name="' + opt.name + '">';
                gridHTML += '<span class="emoji-char">' + opt.emoji + '</span>';
                gridHTML += '<span class="emoji-label">' + opt.meaning + '</span>';
                gridHTML += '</button>';
            });
            gridHTML += '</div>';

            emojiContainer.innerHTML = gridHTML;
            this.elements.messages.appendChild(emojiContainer);
            this.scrollToBottom();

            // Handle selection
            const self = this;
            emojiContainer.querySelectorAll('.emoji-btn-inline').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    const emoji = btn.dataset.emoji;
                    self.selectEmoji(emoji);
                    emojiContainer.remove();
                });
            });

            // Inject styles
            if (!document.getElementById('emoji-inline-styles')) {
                const styles = document.createElement('style');
                styles.id = 'emoji-inline-styles';
                styles.textContent = [
                    '.emoji-selector-inline { padding: 8px; margin: 8px 0; }',
                    '.emoji-grid-inline { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }',
                    '.emoji-btn-inline { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 6px; background: rgba(107, 92, 231, 0.15); border: 2px solid transparent; border-radius: 12px; cursor: pointer; transition: all 0.2s; }',
                    '.emoji-btn-inline:hover { background: rgba(107, 92, 231, 0.3); border-color: rgba(107, 92, 231, 0.5); transform: scale(1.05); }',
                    '.emoji-char { font-size: 24px; }',
                    '.emoji-label { font-size: 9px; color: rgba(255,255,255,0.6); text-align: center; }'
                ].join('\n');
                document.head.appendChild(styles);
            }
        };

        KyurChat.prototype.selectEmoji = function(emoji) {
            this.elements.input.value = emoji;
            this.sendMessage();
        };

        console.log('[FirstInteraction] Emoji flow extension loaded');
    }, 100);
})();
