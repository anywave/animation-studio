/**
 * Digigami Shield - Frontend Integration
 * 
 * WebSocket client for real-time Shield attack events
 * Integrates with the Digigami landing page
 */

(function() {
    'use strict';

    // Configuration
    const SHIELD_WS_URL = window.SHIELD_WS_URL || 'wss://api.digigami.ai';
    const SHIELD_NAMESPACE = '/shield';
    const MAX_ATTACK_ITEMS = 20;
    const DEMO_MODE = true; // Set to false when backend is live

    // DOM Elements
    let shieldOrb, shieldBlocked, shieldRate, shieldSources, attackList;
    let socket = null;
    let stats = {
        blocked: 0,
        total: 0,
        sources: 7
    };

    // Initialize Shield UI
    function initShield() {
        // Get DOM elements
        shieldOrb = document.getElementById('shield-orb');
        shieldBlocked = document.getElementById('shield-blocked');
        shieldRate = document.getElementById('shield-rate');
        shieldSources = document.getElementById('shield-sources');
        attackList = document.getElementById('attack-list');

        if (!attackList) {
            console.log('Shield section not found, skipping initialization');
            return;
        }

        // Update initial stats
        updateStats();

        // Start WebSocket connection or demo mode
        if (DEMO_MODE) {
            startDemoMode();
        } else {
            connectWebSocket();
        }

        console.log('🛡️ Digigami Shield initialized');
    }

    // Connect to Shield WebSocket
    function connectWebSocket() {
        // Check if socket.io is loaded
        if (typeof io === 'undefined') {
            console.warn('Socket.IO not loaded, running in demo mode');
            startDemoMode();
            return;
        }

        try {
            socket = io(SHIELD_WS_URL, {
                path: '/socket.io',
                transports: ['websocket'],
                namespace: SHIELD_NAMESPACE
            });

            socket.on('connect', () => {
                console.log('🛡️ Shield WebSocket connected');
                setOrbStatus('ACTIVE', 'connected');
            });

            socket.on('disconnect', () => {
                console.log('🛡️ Shield WebSocket disconnected');
                setOrbStatus('OFFLINE', 'disconnected');
            });

            // Listen for attack events
            socket.on('attack', (data) => {
                handleAttackEvent(data);
            });

            // Listen for stats updates
            socket.on('stats', (data) => {
                stats.blocked = data.blocked_count || 0;
                stats.total = data.total_requests || 0;
                stats.sources = data.sources_count || 7;
                updateStats();
            });

        } catch (e) {
            console.error('Shield WebSocket error:', e);
            startDemoMode();
        }
    }

    // Handle incoming attack event
    function handleAttackEvent(data) {
        stats.blocked++;
        stats.total++;
        updateStats();

        // Add attack item to feed
        addAttackItem({
            domain: data.domain || 'unknown',
            category: data.category || 'AD',
            timestamp: new Date()
        });

        // Pulse the orb
        pulseOrb();
    }

    // Add attack item to the feed
    function addAttackItem(attack) {
        if (!attackList) return;

        // Remove placeholder if present
        const placeholder = attackList.querySelector('.placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // Create attack item
        const item = document.createElement('div');
        item.className = 'attack-item';
        item.innerHTML = `
            <span class="attack-icon">🚫</span>
            <span class="attack-text">${truncateDomain(attack.domain)}</span>
            <span class="attack-category ${attack.category.toLowerCase()}">${attack.category}</span>
        `;

        // Insert at top
        attackList.insertBefore(item, attackList.firstChild);

        // Limit items
        while (attackList.children.length > MAX_ATTACK_ITEMS) {
            attackList.removeChild(attackList.lastChild);
        }
    }

    // Update stats display
    function updateStats() {
        if (shieldBlocked) {
            shieldBlocked.textContent = formatNumber(stats.blocked);
        }
        if (shieldRate && stats.total > 0) {
            const rate = Math.round((stats.blocked / stats.total) * 100);
            shieldRate.textContent = rate + '%';
        }
        if (shieldSources) {
            shieldSources.textContent = stats.sources;
        }
    }

    // Set orb status
    function setOrbStatus(status, state) {
        if (!shieldOrb) return;

        const statusEl = shieldOrb.querySelector('.orb-status');
        if (statusEl) {
            statusEl.textContent = status;
        }

        shieldOrb.className = 'shield-orb ' + state;
    }

    // Pulse effect on orb
    function pulseOrb() {
        if (!shieldOrb) return;
        
        const core = shieldOrb.querySelector('.orb-core');
        if (core) {
            core.style.animation = 'none';
            setTimeout(() => {
                core.style.animation = 'pulse-core 2s ease-in-out infinite';
            }, 10);
        }
    }

    // Truncate long domain names
    function truncateDomain(domain) {
        if (domain.length > 35) {
            return domain.substring(0, 32) + '...';
        }
        return domain;
    }

    // Format large numbers
    function formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    // Demo mode - simulate attacks
    function startDemoMode() {
        console.log('🛡️ Shield running in demo mode');

        const demoDomains = [
            { domain: 'ads.doubleclick.net', category: 'AD' },
            { domain: 'tracking.facebook.com', category: 'TRACKER' },
            { domain: 'malware-host.evil.com', category: 'MALWARE' },
            { domain: 'coinhive.com', category: 'CRYPTO' },
            { domain: 'analytics.google.com', category: 'TRACKER' },
            { domain: 'pagead2.googlesyndication.com', category: 'AD' },
            { domain: 'pixel.facebook.com', category: 'TRACKER' },
            { domain: 'adservice.google.com', category: 'AD' },
            { domain: 'connect.facebook.net', category: 'TRACKER' },
            { domain: 'cryptoloot.pro', category: 'CRYPTO' },
            { domain: 'pubads.g.doubleclick.net', category: 'AD' },
            { domain: 'bat.bing.com', category: 'TRACKER' },
            { domain: 'malicious-download.xyz', category: 'MALWARE' },
            { domain: 'ad.turn.com', category: 'AD' },
            { domain: 'cdn.miner.rocks', category: 'CRYPTO' }
        ];

        // Initial demo data
        stats.blocked = 1247;
        stats.total = 4892;
        updateStats();

        // Simulate periodic attacks
        function simulateAttack() {
            const attack = demoDomains[Math.floor(Math.random() * demoDomains.length)];
            handleAttackEvent(attack);
        }

        // Random interval between 2-8 seconds
        function scheduleNext() {
            const delay = 2000 + Math.random() * 6000;
            setTimeout(() => {
                simulateAttack();
                scheduleNext();
            }, delay);
        }

        // Start simulation after a short delay
        setTimeout(() => {
            simulateAttack();
            scheduleNext();
        }, 1500);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initShield);
    } else {
        initShield();
    }

    // Expose for external use
    window.DigigamiShield = {
        connect: connectWebSocket,
        addAttack: handleAttackEvent,
        updateStats: updateStats
    };

})();
