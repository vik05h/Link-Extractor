// banner.ts — Procedural SVG Banner Generator for Repacks

export function generateProceduralBannerSvg(title: string): string {
  const clean = (title || 'FitGirl Repack')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .slice(0, 36);

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 215" width="460" height="215">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#09121a"/>
      <stop offset="50%" stop-color="#0c252a"/>
      <stop offset="100%" stop-color="#050a0e"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <rect x="20" y="20" width="80" height="22" rx="4" fill="rgba(0, 240, 160, 0.15)" stroke="#00f0a0" stroke-width="1"/>
  <text x="60" y="35" fill="#00f0a0" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle" letter-spacing="1">FITGIRL</text>
  <text x="230" y="115" fill="#ffffff" font-size="18" font-family="sans-serif" font-weight="bold" text-anchor="middle">${clean}</text>
  <text x="230" y="145" fill="rgba(255,255,255,0.6)" font-size="11" font-family="sans-serif" text-anchor="middle">VERIFIED ARCHIVE REPACK</text>
</svg>`;

  return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
}
