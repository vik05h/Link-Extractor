<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  export let coverUrl: string = '';
  export let theme: string = 'cyber';
  export let activeView: string = 'community';

  // Dual Cross-Fading Ambient Buffers for authentic YouTube Ambient Dissolve
  let activeBuffer = 0;
  let buffer0 = {
    dom: 'rgb(16, 185, 129)',
    sec: 'rgb(6, 182, 212)',
    opacity: 1
  };
  let buffer1 = {
    dom: 'rgb(16, 185, 129)',
    sec: 'rgb(6, 182, 212)',
    opacity: 0
  };

  // Smooth RAF RGB Lerp variables for CSS variables on the UI
  let currentR1 = 16, currentG1 = 185, currentB1 = 129;
  let currentR2 = 6, currentG2 = 182, currentB2 = 212;
  let targetR1 = 16, targetG1 = 185, targetB1 = 129;
  let targetR2 = 6, targetG2 = 182, targetB2 = 212;
  let lerpRafId: number | null = null;

  function stepRgbLerp() {
    // Soft exponential ease factor (~1.8s gradual glide across 60fps)
    const ease = 0.042;
    currentR1 += (targetR1 - currentR1) * ease;
    currentG1 += (targetG1 - currentG1) * ease;
    currentB1 += (targetB1 - currentB1) * ease;

    currentR2 += (targetR2 - currentR2) * ease;
    currentG2 += (targetG2 - currentG2) * ease;
    currentB2 += (targetB2 - currentB2) * ease;

    const r1 = Math.round(currentR1);
    const g1 = Math.round(currentG1);
    const b1 = Math.round(currentB1);

    const r2 = Math.round(currentR2);
    const g2 = Math.round(currentG2);
    const b2 = Math.round(currentB2);

    if (typeof document !== 'undefined') {
      document.documentElement.style.setProperty('--adaptive-color', `rgb(${r1}, ${g1}, ${b1})`);
      document.documentElement.style.setProperty('--adaptive-sec', `rgb(${r2}, ${g2}, ${b2})`);
      document.documentElement.style.setProperty('--adaptive-glow', `rgba(${r1}, ${g1}, ${b1}, 0.35)`);
    }

    const diff = Math.abs(targetR1 - currentR1) + Math.abs(targetG1 - currentG1) + Math.abs(targetB1 - currentB1);
    if (diff > 0.8 && typeof window !== 'undefined') {
      lerpRafId = requestAnimationFrame(stepRgbLerp);
    } else {
      lerpRafId = null;
    }
  }

  function setPalette(r1: number, g1: number, b1: number, r2?: number, g2?: number, b2?: number) {
    const sR = r2 !== undefined ? r2 : Math.max(15, Math.min(255, Math.floor(r1 * 0.7 + 35)));
    const sG = g2 !== undefined ? g2 : Math.max(15, Math.min(255, Math.floor(g1 * 0.85 + 40)));
    const sB = b2 !== undefined ? b2 : Math.max(15, Math.min(255, Math.floor(b1 * 1.25 + 50)));

    // Target colors for the soft RAF lerp loop
    targetR1 = r1; targetG1 = g1; targetB1 = b1;
    targetR2 = sR; targetG2 = sG; targetB2 = sB;

    if (typeof window !== 'undefined' && !lerpRafId) {
      lerpRafId = requestAnimationFrame(stepRgbLerp);
    }

    const domStr = `rgb(${r1}, ${g1}, ${b1})`;
    const secStr = `rgb(${sR}, ${sG}, ${sB})`;

    // Swap and cross-fade the dual ambient layers
    if (activeBuffer === 0) {
      buffer1 = { dom: domStr, sec: secStr, opacity: 1 };
      buffer0 = { ...buffer0, opacity: 0 };
      activeBuffer = 1;
    } else {
      buffer0 = { dom: domStr, sec: secStr, opacity: 1 };
      buffer1 = { ...buffer1, opacity: 0 };
      activeBuffer = 0;
    }
  }

  function deriveHashPalette(seedStr: string) {
    let hash = 0;
    for (let i = 0; i < seedStr.length; i++) {
      hash = (hash << 5) - hash + seedStr.charCodeAt(i);
      hash |= 0;
    }
    const hue1 = Math.abs(hash) % 360;
    const hue2 = (hue1 + 50) % 360;

    function hslToRgb(h: number, s: number, l: number) {
      const c = (1 - Math.abs(2 * l - 1)) * s;
      const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
      const m = l - c / 2;
      let r = 0, g = 0, b = 0;
      if (h < 60) { r = c; g = x; }
      else if (h < 120) { r = x; g = c; }
      else if (h < 180) { g = c; b = x; }
      else if (h < 240) { g = x; b = c; }
      else if (h < 300) { r = x; b = c; }
      else { r = c; b = x; }
      return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
    }

    const [r1, g1, b1] = hslToRgb(hue1, 0.88, 0.54);
    const [r2, g2, b2] = hslToRgb(hue2, 0.82, 0.50);
    setPalette(r1, g1, b1, r2, g2, b2);
  }

  function resolvePalette(url: string) {
    if (!url) {
      setPalette(16, 185, 129, 6, 182, 212);
      return;
    }

    // First try Python Backend RPC (bypasses browser CORS completely)
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.extract_game_palette) {
      (window as any).pywebview.api.extract_game_palette(url)
        .then((pal: any) => {
          if (pal && pal.primary) {
            setPalette(
              pal.primary[0], pal.primary[1], pal.primary[2],
              pal.secondary[0], pal.secondary[1], pal.secondary[2]
            );
          } else {
            deriveHashPalette(url);
          }
        })
        .catch(() => {
          deriveHashPalette(url);
        });
      return;
    }

    // Fallback: browser canvas or deterministic hash
    const img = new Image();
    img.crossOrigin = 'Anonymous';
    img.src = url;
    img.onload = () => {
      try {
        const offCanvas = document.createElement('canvas');
        const ctx = offCanvas.getContext('2d', { willReadFrequently: true });
        if (!ctx) { deriveHashPalette(url); return; }
        offCanvas.width = 16;
        offCanvas.height = 16;
        ctx.drawImage(img, 0, 0, 16, 16);
        const data = ctx.getImageData(0, 0, 16, 16).data;
        let r1 = 0, g1 = 0, b1 = 0, count = 0;
        for (let i = 0; i < data.length; i += 16) {
          r1 += data[i]; g1 += data[i + 1]; b1 += data[i + 2]; count++;
        }
        r1 = Math.min(245, Math.max(35, Math.floor((r1 / count) * 1.3)));
        g1 = Math.min(245, Math.max(35, Math.floor((g1 / count) * 1.3)));
        b1 = Math.min(245, Math.max(35, Math.floor((b1 / count) * 1.3)));
        setPalette(r1, g1, b1);
      } catch {
        deriveHashPalette(url);
      }
    };
    img.onerror = () => {
      deriveHashPalette(url);
    };
  }

  // Reactive Theme & View Binding
  $: {
    if (activeView === 'stage' && coverUrl) {
      // Always adapt dynamically to active game cover on Stage (YouTube video ambient mode)
      resolvePalette(coverUrl);
    } else if (theme === 'steam') {
      setPalette(56, 189, 248, 99, 102, 241);
    } else {
      // Smoothly return to default Cyber-Dark when in Community Hub or no active game
      setPalette(16, 185, 129, 6, 182, 212);
    }
  }

  onDestroy(() => {
    if (lerpRafId && typeof window !== 'undefined') {
      cancelAnimationFrame(lerpRafId);
    }
  });
</script>

<div class="living-canvas-root">
  <!-- YouTube Ambient Buffer 0 -->
  <div 
    class="ambient-mesh youtube-ambient buffer-layer" 
    style="
      opacity: {buffer0.opacity * 0.38};
      background: radial-gradient(circle at 25% 25%, {buffer0.dom} 0%, transparent 52%),
                  radial-gradient(circle at 78% 75%, {buffer0.sec} 0%, transparent 54%),
                  radial-gradient(circle at 50% 50%, rgba(8, 10, 14, 0.95) 0%, rgba(4, 5, 8, 1) 100%);
    "
  ></div>

  <!-- YouTube Ambient Buffer 1 (Cross-fades over Buffer 0) -->
  <div 
    class="ambient-mesh youtube-ambient buffer-layer" 
    style="
      opacity: {buffer1.opacity * 0.38};
      background: radial-gradient(circle at 25% 25%, {buffer1.dom} 0%, transparent 52%),
                  radial-gradient(circle at 78% 75%, {buffer1.sec} 0%, transparent 54%),
                  radial-gradient(circle at 50% 50%, rgba(8, 10, 14, 0.95) 0%, rgba(4, 5, 8, 1) 100%);
    "
  ></div>

  <!-- Secondary Drift Pulse Layer for Depth Bloom -->
  <div 
    class="ambient-mesh ambient-pulse-layer"
    style="
      background: radial-gradient(circle at 50% 35%, var(--adaptive-color, #10b981) 0%, transparent 60%);
    "
  ></div>

  <!-- Soft Vignette Overlay -->
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

  /* Dual Buffer Cross-Fading Layers for True YouTube Ambient Dissolve */
  .ambient-mesh {
    position: absolute;
    inset: -60px;
    filter: blur(95px);
    transform-origin: center center;
    transition: opacity 2.2s cubic-bezier(0.25, 1, 0.5, 1);
    will-change: transform, opacity;
  }

  .buffer-layer {
    transition: opacity 2.2s cubic-bezier(0.25, 1, 0.5, 1);
  }

  /* YouTube-Style Ambient Video Lighting Breathing Motion */
  .youtube-ambient {
    animation: youtubeAmbientMotion 22s ease-in-out infinite alternate;
  }

  .ambient-pulse-layer {
    opacity: 0.16;
    filter: blur(110px);
    animation: youtubeSecondaryFloat 28s ease-in-out infinite alternate-reverse;
  }

  @keyframes youtubeAmbientMotion {
    0% {
      transform: scale(1) translate(0, 0);
    }
    50% {
      transform: scale(1.06) translate(-18px, 12px);
    }
    100% {
      transform: scale(0.97) translate(18px, -12px);
    }
  }

  @keyframes youtubeSecondaryFloat {
    0% {
      transform: scale(0.96) translate(12px, -8px);
    }
    50% {
      transform: scale(1.05) translate(-12px, 16px);
    }
    100% {
      transform: scale(1) translate(0, 0);
    }
  }

  .vignette-overlay {
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at center, transparent 32%, rgba(0, 0, 0, 0.76) 100%);
  }
</style>
