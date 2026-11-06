<script lang="ts">
  /**
   * The Link Extractor logo, "Bolt Tray", drawn inline so it takes the theme's colors.
   * public/favicon.svg is the same drawing in the default colors, for the window, taskbar
   * and .exe icons, so change both together.
   */
  let { size = '100%' }: { size?: number | string } = $props();

  // Two logos can be on screen at once during startup, so every id is unique to this one.
  const uid = $props.id();
  const ref = (name: string) => `${uid}-${name}`;
</script>

<svg class="brand-logo" viewBox="0 0 512 512" width={size} height={size} aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id={ref('tile')} x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1c2738" />
      <stop offset="1" stop-color="#060a11" />
    </linearGradient>
    <radialGradient id={ref('tint')} cx="0.28" cy="0.18" r="0.95">
      <stop offset="0" class="paint-primary" stop-opacity="0.24" />
      <stop offset="1" class="paint-secondary" stop-opacity="0" />
    </radialGradient>
    <linearGradient id={ref('rim')} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.62" />
      <stop offset="0.3" stop-color="#ffffff" stop-opacity="0.12" />
      <stop offset="0.75" stop-color="#ffffff" stop-opacity="0.04" />
      <stop offset="1" stop-color="#ffffff" stop-opacity="0.22" />
    </linearGradient>
    <linearGradient id={ref('mark')} gradientUnits="userSpaceOnUse" x1="170" y1="60" x2="350" y2="455">
      <stop offset="0" class="paint-light" />
      <stop offset="0.45" class="paint-primary" />
      <stop offset="1" class="paint-secondary" />
    </linearGradient>
    <linearGradient id={ref('shine')} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.5" />
      <stop offset="0.48" stop-color="#ffffff" stop-opacity="0" />
    </linearGradient>
    <filter id={ref('glow')} x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="20" />
    </filter>
    <g id={ref('shapes')}>
      <path
        d="M 301.13 73.65 Q 304 62 297.68 72.20 L 186.32 251.80 Q 180 262 192.00 262.00 L 246.00 262.00 Q 258 262 255.21 273.67 L 228.79 384.33 Q 226 396 232.23 385.75 L 343.77 202.25 Q 350 192 338.00 192.00 L 284.00 192.00 Q 272 192 274.87 180.35 Z"
        stroke="none"
      />
      <path
        d="M 128 350 L 128 398 Q 128 434 164 434 L 348 434 Q 384 434 384 398 L 384 350"
        fill="none"
        stroke-width="36"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </g>
  </defs>
  <rect x="24" y="24" width="464" height="464" rx="108" fill="url(#{ref('tile')})" />
  <rect x="24" y="24" width="464" height="464" rx="108" fill="url(#{ref('tint')})" />
  <use href="#{ref('shapes')}" class="glow" opacity="0.55" filter="url(#{ref('glow')})" />
  <use href="#{ref('shapes')}" fill="url(#{ref('mark')})" stroke="url(#{ref('mark')})" />
  <use href="#{ref('shapes')}" fill="url(#{ref('shine')})" stroke="url(#{ref('shine')})" />
  <rect x="25.5" y="25.5" width="461" height="461" rx="106.5" fill="none" stroke="url(#{ref('rim')})" stroke-width="3" />
</svg>

<style>
  .brand-logo {
    --logo-primary: var(--accent-primary, #10b981);
    --logo-secondary: var(--accent-secondary, #06b6d4);
    --logo-light: color-mix(in srgb, var(--logo-primary) 55%, #ffffff);
    display: block;
  }

  /* A lighter shade of the same hue, like the default logo's mint highlight. */
  @supports (color: oklch(from red l c h)) {
    .brand-logo {
      --logo-light: oklch(from var(--logo-primary) calc(l + 0.18) c h);
    }
  }

  .paint-light {
    stop-color: var(--logo-light);
  }

  .paint-primary {
    stop-color: var(--logo-primary);
  }

  .paint-secondary {
    stop-color: var(--logo-secondary);
  }

  .glow {
    fill: var(--logo-primary);
    stroke: var(--logo-primary);
  }
</style>
