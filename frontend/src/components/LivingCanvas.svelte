<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  export let coverUrl: string = '';
  export let theme: string = 'cyber';

  let canvasEl: HTMLCanvasElement;
  let animId: number;
  let dominantColor = '#10b981';
  let secondaryColor = '#06b6d4';

  interface Particle {
    x: number;
    y: number;
    vx: number;
    vy: number;
    size: number;
    alpha: number;
    maxAlpha: number;
  }

  let particles: Particle[] = [];

  function sampleImageColors(url: string) {
    if (!url) return;
    const img = new Image();
    img.crossOrigin = 'Anonymous';
    img.src = url;
    img.onload = () => {
      try {
        const offCanvas = document.createElement('canvas');
        const ctx = offCanvas.getContext('2d');
        if (!ctx) return;
        offCanvas.width = 16;
        offCanvas.height = 16;
        ctx.drawImage(img, 0, 0, 16, 16);
        const data = ctx.getImageData(0, 0, 16, 16).data;
        
        let r1 = 0, g1 = 0, b1 = 0, count = 0;
        for (let i = 0; i < data.length; i += 16) {
          r1 += data[i];
          g1 += data[i + 1];
          b1 += data[i + 2];
          count++;
        }
        r1 = Math.min(240, Math.floor((r1 / count) * 1.2));
        g1 = Math.min(240, Math.floor((g1 / count) * 1.2));
        b1 = Math.min(240, Math.floor((b1 / count) * 1.2));

        dominantColor = `rgb(${r1}, ${g1}, ${b1})`;
        secondaryColor = `rgba(${Math.max(20, r1 - 40)}, ${Math.min(255, g1 + 30)}, ${Math.min(255, b1 + 60)}, 0.8)`;

        document.documentElement.style.setProperty('--adaptive-color', dominantColor);
        document.documentElement.style.setProperty('--adaptive-sec', secondaryColor);
        document.documentElement.style.setProperty('--adaptive-glow', `rgba(${r1}, ${g1}, ${b1}, 0.35)`);
      } catch (err) {
        // Fallback to theme defaults
      }
    };
  }

  $: if (coverUrl) {
    sampleImageColors(coverUrl);
  }

  function initParticles(width: number, height: number) {
    particles = [];
    const count = Math.floor((width * height) / 35000);
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: -0.2 - Math.random() * 0.5,
        size: 1 + Math.random() * 2.5,
        alpha: Math.random() * 0.6,
        maxAlpha: 0.3 + Math.random() * 0.4
      });
    }
  }

  function render() {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext('2d');
    if (!ctx) return;

    const w = canvasEl.width;
    const h = canvasEl.height;

    ctx.clearRect(0, 0, w, h);

    // Render subtle atmospheric floating particles
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;

      if (p.y < -10) {
        p.y = h + 10;
        p.x = Math.random() * w;
      }
      if (p.x < -10) p.x = w + 10;
      if (p.x > w + 10) p.x = -10;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = dominantColor;
      ctx.globalAlpha = p.alpha;
      ctx.shadowBlur = 8;
      ctx.shadowColor = dominantColor;
      ctx.fill();
    }
    ctx.globalAlpha = 1.0;
    ctx.shadowBlur = 0;

    animId = requestAnimationFrame(render);
  }

  function handleResize() {
    if (!canvasEl) return;
    canvasEl.width = window.innerWidth;
    canvasEl.height = window.innerHeight;
    initParticles(canvasEl.width, canvasEl.height);
  }

  onMount(() => {
    handleResize();
    window.addEventListener('resize', handleResize);
    animId = requestAnimationFrame(render);
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
    }
  });
</script>

<div class="living-canvas-root">
  <!-- Dynamic Ambient Mesh Glow -->
  <div 
    class="ambient-mesh" 
    style="
      --dom: {dominantColor}; 
      --sec: {secondaryColor};
      background: radial-gradient(circle at 18% 22%, var(--dom) 0%, transparent 45%),
                  radial-gradient(circle at 82% 78%, var(--sec) 0%, transparent 48%),
                  radial-gradient(circle at 50% 50%, rgba(10, 12, 18, 0.95) 0%, rgba(5, 6, 9, 1) 100%);
    "
  ></div>

  <!-- Particle Canvas -->
  <canvas bind:this={canvasEl} class="particle-canvas"></canvas>

  <!-- Fine Noise / Scanline Texture -->
  <div class="vignette-overlay"></div>
</div>

<style>
  .living-canvas-root {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
  }

  .ambient-mesh {
    position: absolute;
    inset: -20px;
    opacity: 0.28;
    filter: blur(60px);
    transition: all 1.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .particle-canvas {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .vignette-overlay {
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at center, transparent 40%, rgba(0, 0, 0, 0.65) 100%);
  }
</style>
