<script lang="ts">
  export let coverUrl: string = '';
  export let theme: string = 'cyber';

  let dominantColor = '#10b981';
  let secondaryColor = '#06b6d4';

  function setPalette(r1: number, g1: number, b1: number, r2?: number, g2?: number, b2?: number) {
    dominantColor = `rgb(${r1}, ${g1}, ${b1})`;
    const sR = r2 !== undefined ? r2 : Math.max(15, Math.min(255, Math.floor(r1 * 0.7 + 30)));
    const sG = g2 !== undefined ? g2 : Math.max(15, Math.min(255, Math.floor(g1 * 0.8 + 40)));
    const sB = b2 !== undefined ? b2 : Math.max(15, Math.min(255, Math.floor(b1 * 1.2 + 50)));
    secondaryColor = `rgb(${sR}, ${sG}, ${sB})`;

    if (typeof document !== 'undefined') {
      document.documentElement.style.setProperty('--adaptive-color', dominantColor);
      document.documentElement.style.setProperty('--adaptive-sec', secondaryColor);
      document.documentElement.style.setProperty('--adaptive-glow', `rgba(${r1}, ${g1}, ${b1}, 0.35)`);
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

  function sampleImageColors(url: string) {
    if (!url) {
      // Default vibrant Dynamic Adaptive palette (Electric Violet to Cyan)
      setPalette(168, 85, 247, 6, 182, 212);
      return;
    }

    const img = new Image();
    img.crossOrigin = 'Anonymous';
    img.src = url;
    img.onload = () => {
      try {
        const offCanvas = document.createElement('canvas');
        const ctx = offCanvas.getContext('2d', { willReadFrequently: true });
        if (!ctx) {
          deriveHashPalette(url);
          return;
        }
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
        r1 = Math.min(245, Math.max(30, Math.floor((r1 / count) * 1.3)));
        g1 = Math.min(245, Math.max(30, Math.floor((g1 / count) * 1.3)));
        b1 = Math.min(245, Math.max(30, Math.floor((b1 / count) * 1.3)));
        setPalette(r1, g1, b1);
      } catch (err) {
        deriveHashPalette(url);
      }
    };
    img.onerror = () => {
      deriveHashPalette(url);
    };
  }

  $: if (theme === 'adaptive') {
    sampleImageColors(coverUrl);
  } else if (theme === 'steam') {
    setPalette(56, 189, 248, 99, 102, 241);
  } else {
    // Default cyber
    setPalette(16, 185, 129, 6, 182, 212);
  }
</script>

<div class="living-canvas-root">
  <!-- Dynamic Ambient Mesh Glow -->
  <div 
    class="ambient-mesh" 
    style="
      --dom: {dominantColor}; 
      --sec: {secondaryColor};
      background: radial-gradient(circle at 18% 22%, var(--dom) 0%, transparent 50%),
                  radial-gradient(circle at 82% 78%, var(--sec) 0%, transparent 52%),
                  radial-gradient(circle at 50% 50%, rgba(8, 10, 14, 0.95) 0%, rgba(4, 5, 8, 1) 100%);
    "
  ></div>

  <!-- Smooth Vignette Overlay (Zero floating particles) -->
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
    inset: -30px;
    opacity: 0.32;
    filter: blur(70px);
    transition: all 1.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .vignette-overlay {
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at center, transparent 35%, rgba(0, 0, 0, 0.7) 100%);
  }
</style>
