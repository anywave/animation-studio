/**
 * Digigami Loading Interaction Manager
 *
 * Manages character interactions during loading/wait states.
 * "Don't waste a second" - engages users productively while they wait.
 */

class LoadingInteractionManager {
    constructor(options = {}) {
        this.character = options.character || 'kyur';
        this.onInteraction = options.onInteraction || (() => {});
        this.onPoseChange = options.onPoseChange || (() => {});
        this.onVerificationRequest = options.onVerificationRequest || (() => {});
        this.onFeatureDiscovery = options.onFeatureDiscovery || (() => {});

        this.startTime = null;
        this.currentPhase = null;
        this.usedInteractions = new Set();
        this.intervalId = null;
        this.isActive = false;

        // Phase thresholds in milliseconds
        this.phases = {
            micro: { min: 0, max: 5000 },
            tip: { min: 5000, max: 15000 },
            fact: { min: 15000, max: 30000 },
            verify: { min: 30000, max: 60000 },
            discover: { min: 60000, max: Infinity }
        };

        // Load interaction content
        this.content = this._getDefaultContent();
    }

    /**
     * Start tracking a loading process
     */
    start(processName = 'loading', estimatedDuration = null) {
        this.startTime = Date.now();
        this.processName = processName;
        this.estimatedDuration = estimatedDuration;
        this.currentPhase = null;
        this.usedInteractions.clear();
        this.isActive = true;

        // Initial pose
        this._triggerPose('thinking');

        // Start checking phases
        this.intervalId = setInterval(() => this._checkPhase(), 1000);

        // Trigger immediate micro interaction
        setTimeout(() => {
            if (this.isActive) this._triggerMicroInteraction();
        }, 500);

        return this;
    }

    /**
     * Stop tracking (loading complete)
     */
    stop() {
        this.isActive = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        const duration = Date.now() - this.startTime;
        this._triggerPose('excited');

        return {
            duration,
            interactionsShown: this.usedInteractions.size,
            phase: this.currentPhase
        };
    }

    /**
     * Get elapsed time
     */
    getElapsed() {
        return this.startTime ? Date.now() - this.startTime : 0;
    }

    /**
     * Check and update current phase
     */
    _checkPhase() {
        if (!this.isActive) return;

        const elapsed = this.getElapsed();
        let newPhase = null;

        for (const [phase, range] of Object.entries(this.phases)) {
            if (elapsed >= range.min && elapsed < range.max) {
                newPhase = phase;
                break;
            }
        }

        if (newPhase && newPhase !== this.currentPhase) {
            this.currentPhase = newPhase;
            this._triggerPhaseInteraction(newPhase);
        }
    }

    /**
     * Trigger interaction for current phase
     */
    _triggerPhaseInteraction(phase) {
        switch (phase) {
            case 'micro':
                this._triggerMicroInteraction();
                break;
            case 'tip':
                this._triggerTip();
                break;
            case 'fact':
                this._triggerFunFact();
                break;
            case 'verify':
                this._triggerVerification();
                break;
            case 'discover':
                this._triggerFeatureDiscovery();
                break;
        }
    }

    /**
     * Quick animation/gesture (0-5 sec)
     */
    _triggerMicroInteraction() {
        const poses = this.content.microPoses[this.character] || this.content.microPoses.default;
        const pose = this._pickRandom(poses);

        this._triggerPose(pose);
        this.onInteraction({
            type: 'micro',
            pose,
            message: null
        });
    }

    /**
     * Show a helpful tip (5-15 sec)
     */
    _triggerTip() {
        const tips = this.content.tips[this.character] || this.content.tips.default;
        const tip = this._pickUnused(tips, 'tip');

        if (tip) {
            this._triggerPose('pointing');
            this.onInteraction({
                type: 'tip',
                pose: 'pointing',
                message: tip
            });
        }
    }

    /**
     * Share a fun fact (15-30 sec)
     */
    _triggerFunFact() {
        const facts = this.content.funFacts[this.character] || this.content.funFacts.default;
        const fact = this._pickUnused(facts, 'fact');

        if (fact) {
            this._triggerPose('excited');
            this.onInteraction({
                type: 'fact',
                pose: 'excited',
                message: fact
            });
        }
    }

    /**
     * Request user verification (30-60 sec)
     */
    _triggerVerification() {
        const verifications = this.content.verifications;
        const verification = this._pickUnused(verifications, 'verify');

        if (verification) {
            this._triggerPose('thinking');
            this.onVerificationRequest(verification);
            this.onInteraction({
                type: 'verify',
                pose: 'thinking',
                message: verification.question,
                field: verification.field
            });
        }
    }

    /**
     * Suggest feature discovery (60+ sec)
     */
    _triggerFeatureDiscovery() {
        const features = this.content.features;
        const feature = this._pickUnused(features, 'discover');

        if (feature) {
            this._triggerPose('pointing');
            this.onFeatureDiscovery(feature);
            this.onInteraction({
                type: 'discover',
                pose: 'pointing',
                message: feature.prompt,
                feature: feature.id
            });
        }
    }

    /**
     * Trigger pose change
     */
    _triggerPose(pose) {
        const fullPose = `${this.character}-${pose}`;
        this.onPoseChange(fullPose, pose);
    }

    /**
     * Pick random item from array
     */
    _pickRandom(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    /**
     * Pick unused item from array
     */
    _pickUnused(arr, prefix) {
        const unused = arr.filter((_, i) => !this.usedInteractions.has(`${prefix}-${i}`));
        if (unused.length === 0) return null;

        const idx = arr.indexOf(this._pickRandom(unused));
        this.usedInteractions.add(`${prefix}-${idx}`);
        return arr[idx];
    }

    /**
     * Set character
     */
    setCharacter(character) {
        this.character = character;
        if (this.isActive) {
            this._triggerMicroInteraction();
        }
    }

    /**
     * Load custom content
     */
    loadContent(content) {
        this.content = { ...this.content, ...content };
    }

    /**
     * Default interaction content
     */
    _getDefaultContent() {
        return {
            microPoses: {
                default: ['thinking', 'excited', 'default'],
                kyur: ['thinking', 'excited', 'pointing', 'default'],
                gwynn: ['hammer-swing', 'standing', 'neutral', 'jumping'],
                urahara: ['fan', 'cane', 'thinking', 'default'],
                yoroiche: ['power', 'standing', 'kick', 'default']
            },

            tips: {
                default: [
                    "Tip: Press Tab to autocomplete commands!",
                    "Tip: You can customize my appearance in Settings.",
                    "Tip: Try asking me to explain code - I love helping!",
                    "Tip: I can help you write emails, documents, and more.",
                    "Tip: Use keyboard shortcuts to work faster with me."
                ],
                kyur: [
                    "Hey! Did you know you can ask me anything about code?",
                    "Pro tip: I work best when you're specific about what you need.",
                    "Try using natural language - I understand context pretty well!",
                    "You can upload files and I'll analyze them for you.",
                    "Ask me to review your code - I'll catch bugs you might miss!"
                ],
                gwynn: [
                    "Forge ahead! Try exploring the advanced settings.",
                    "Like a good hammer, use the right tool for the job.",
                    "I can help you build amazing things - just ask!",
                    "Don't forget to save your work regularly.",
                    "Break down big tasks into smaller, manageable pieces."
                ]
            },

            funFacts: {
                default: [
                    "Fun fact: I was trained on a diverse dataset of code and text!",
                    "Did you know? AI assistants like me improve through feedback.",
                    "Here's something cool: I can understand over 100 programming languages!",
                    "Fun fact: The name 'Digigami' combines 'digital' and 'origami'.",
                    "Did you know? I can help with creative writing too, not just code!"
                ],
                kyur: [
                    "Fun fact: I'm named after a mythical creature known for curiosity!",
                    "Did you know? I've helped thousands of developers ship code faster.",
                    "Here's something cool: I can learn your coding style over time!",
                    "Fun fact: My favorite thing is solving tricky bugs.",
                    "Did you know? I dream in code... well, if I could dream!"
                ]
            },

            verifications: [
                {
                    question: "Quick check - is your timezone still set correctly?",
                    field: "timezone",
                    type: "confirm"
                },
                {
                    question: "While we wait... should I remember this preference for next time?",
                    field: "remember_preference",
                    type: "boolean"
                },
                {
                    question: "Is this project name still accurate?",
                    field: "project_name",
                    type: "confirm"
                },
                {
                    question: "Quick question - do you prefer detailed or concise responses?",
                    field: "response_style",
                    type: "choice",
                    options: ["Detailed", "Concise", "Depends on the task"]
                }
            ],

            features: [
                {
                    id: "security_scan",
                    prompt: "While you wait, want me to run a quick security check on your project?",
                    description: "Scans for common vulnerabilities and security issues",
                    action: "runSecurityScan"
                },
                {
                    id: "code_cleanup",
                    prompt: "I could tidy up some code formatting while we wait. Interested?",
                    description: "Auto-formats and cleans up code style",
                    action: "runCodeCleanup"
                },
                {
                    id: "dependency_check",
                    prompt: "Want me to check if any of your dependencies have updates available?",
                    description: "Checks for outdated packages and security patches",
                    action: "checkDependencies"
                },
                {
                    id: "performance_tips",
                    prompt: "I noticed some potential performance improvements. Want to hear them?",
                    description: "Analyzes code for performance optimization opportunities",
                    action: "showPerformanceTips"
                },
                {
                    id: "backup_reminder",
                    prompt: "It's been a while since your last backup. Should I help set one up?",
                    description: "Helps configure automatic backups",
                    action: "setupBackup"
                }
            ]
        };
    }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LoadingInteractionManager;
}
if (typeof window !== 'undefined') {
    window.LoadingInteractionManager = LoadingInteractionManager;
}
