/**
 * Digigami - Magical Particle Background
 * Creates floating sparkle particles for magical effect
 */

class ParticleSystem {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.mouseX = 0;
        this.mouseY = 0;
        this.animationId = null;

        this.config = {
            particleCount: 80,
            colors: [
                'rgba(107, 92, 231, 0.6)',   // Primary purple
                'rgba(0, 217, 255, 0.6)',    // Magic cyan
                'rgba(255, 107, 53, 0.4)',   // Accent orange
                'rgba(255, 215, 0, 0.5)',    // Gold
                'rgba(255, 255, 255, 0.4)'   // White sparkle
            ],
            minSize: 2,
            maxSize: 6,
            minSpeed: 0.2,
            maxSpeed: 0.8,
            mouseInfluence: 100,
            mouseRepelStrength: 0.5
        };

        this.init();
    }

    init() {
        // Create canvas
        const container = document.getElementById('particles-bg');
        if (!container) return;

        this.canvas = document.createElement('canvas');
        this.canvas.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        `;
        container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        // Set canvas size
        this.resize();

        // Create particles
        this.createParticles();

        // Event listeners
        window.addEventListener('resize', () => this.resize());
        document.addEventListener('mousemove', (e) => {
            this.mouseX = e.clientX;
            this.mouseY = e.clientY;
        });

        // Start animation
        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    createParticles() {
        this.particles = [];
        for (let i = 0; i < this.config.particleCount; i++) {
            this.particles.push(this.createParticle());
        }
    }

    createParticle(x, y) {
        const { colors, minSize, maxSize, minSpeed, maxSpeed } = this.config;
        return {
            x: x ?? Math.random() * this.canvas.width,
            y: y ?? Math.random() * this.canvas.height,
            size: Math.random() * (maxSize - minSize) + minSize,
            color: colors[Math.floor(Math.random() * colors.length)],
            speedX: (Math.random() - 0.5) * (maxSpeed - minSpeed) + minSpeed,
            speedY: (Math.random() - 0.5) * (maxSpeed - minSpeed) + minSpeed,
            opacity: Math.random() * 0.5 + 0.3,
            pulse: Math.random() * Math.PI * 2,
            pulseSpeed: Math.random() * 0.02 + 0.01
        };
    }

    updateParticle(particle) {
        const { mouseInfluence, mouseRepelStrength } = this.config;

        // Base movement
        particle.x += particle.speedX;
        particle.y += particle.speedY;

        // Mouse interaction - gentle repel
        const dx = particle.x - this.mouseX;
        const dy = particle.y - this.mouseY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < mouseInfluence && distance > 0) {
            const force = (mouseInfluence - distance) / mouseInfluence;
            particle.x += (dx / distance) * force * mouseRepelStrength;
            particle.y += (dy / distance) * force * mouseRepelStrength;
        }

        // Pulse effect
        particle.pulse += particle.pulseSpeed;
        particle.currentOpacity = particle.opacity + Math.sin(particle.pulse) * 0.2;

        // Wrap around edges
        if (particle.x < -10) particle.x = this.canvas.width + 10;
        if (particle.x > this.canvas.width + 10) particle.x = -10;
        if (particle.y < -10) particle.y = this.canvas.height + 10;
        if (particle.y > this.canvas.height + 10) particle.y = -10;
    }

    drawParticle(particle) {
        const { ctx } = this;
        const size = particle.size + Math.sin(particle.pulse) * 1;

        // Draw glow
        const gradient = ctx.createRadialGradient(
            particle.x, particle.y, 0,
            particle.x, particle.y, size * 2
        );
        gradient.addColorStop(0, particle.color);
        gradient.addColorStop(1, 'transparent');

        ctx.globalAlpha = particle.currentOpacity;
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, size * 2, 0, Math.PI * 2);
        ctx.fill();

        // Draw core
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, size * 0.5, 0, Math.PI * 2);
        ctx.fill();

        ctx.globalAlpha = 1;
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw gradient background
        const bgGradient = this.ctx.createLinearGradient(0, 0, 0, this.canvas.height);
        bgGradient.addColorStop(0, '#0A0E1A');
        bgGradient.addColorStop(0.5, '#141B2D');
        bgGradient.addColorStop(1, '#1E2742');
        this.ctx.fillStyle = bgGradient;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Update and draw particles
        for (const particle of this.particles) {
            this.updateParticle(particle);
            this.drawParticle(particle);
        }

        this.animationId = requestAnimationFrame(() => this.animate());
    }

    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.particleSystem = new ParticleSystem();
});
