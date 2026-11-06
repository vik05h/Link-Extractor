/**
 * The made-up game the tour shows on the Stage, so every step points at something real
 * without touching the network. It only ever lives in memory: its links are sample:// links,
 * and while the tour is open the Stage's buttons do nothing, so it is never pushed,
 * copied, exported, saved to the Vault or shared to the Hub.
 */

import type { PartItem } from '../types';

export const SAMPLE_TITLE = 'Touch Grass Simulator';

const CORE_PARTS = 64;
const LANGUAGES = ['french', 'german', 'spanish', 'italian', 'russian', 'japanese'];
const STARTS_RESOLVED = 44;
const STARTS_RESOLVING = 3;

export interface SampleGame {
  title: string;
  coverUrl: string;
  totalSizeStr: string;
  parts: PartItem[];
  logs: string[];
}

const COVER_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 400">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#bae6fd"/></linearGradient>
<linearGradient id="grass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4ade80"/><stop offset="1" stop-color="#15803d"/></linearGradient>
</defs>
<rect width="300" height="400" fill="url(#sky)"/>
<circle cx="74" cy="82" r="34" fill="#fde047"/>
<circle cx="74" cy="82" r="48" fill="#fde047" opacity="0.25"/>
<path d="M0 252 Q 75 226 150 246 T 300 238 V 400 H 0 Z" fill="url(#grass)"/>
<path d="M28 268 l7 -24 l7 24 M96 258 l5 -18 l5 18 M168 262 l6 -22 l6 22 M240 256 l6 -24 l6 24" stroke="#166534" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
<text x="150" y="330" text-anchor="middle" font-family="Arial Black, Arial, sans-serif" font-weight="900" font-size="34" fill="#ffffff" stroke="#14532d" stroke-width="3" paint-order="stroke">TOUCH GRASS</text>
<text x="150" y="366" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" font-size="20" letter-spacing="6" fill="#f0fdf4">SIMULATOR</text>
</svg>`;

function partFiles(): { name: string; size: string }[] {
  const core = Array.from({ length: CORE_PARTS }, (_, i) => ({
    name: `Touch_Grass_Simulator_--_fitgirl-repacks.site_--_.part${String(i + 1).padStart(3, '0')}.rar`,
    size: '500 MB',
  }));
  return [
    ...core,
    { name: 'fg-selective-english.bin', size: '600 MB' },
    ...LANGUAGES.map((language) => ({ name: `fg-selective-${language}.bin`, size: '150 MB' })),
    { name: 'fg-optional-bonus-artbook.bin', size: '700 MB' },
  ];
}

function sampleLink(index: number, filename: string): string {
  return `sample://touch-grass-simulator/${index}#${filename}`;
}

export function createSampleGame(): SampleGame {
  const parts: PartItem[] = partFiles().map(({ name, size }, i) => {
    const status: PartItem['status'] =
      i < STARTS_RESOLVED ? 'resolved' : i < STARTS_RESOLVED + STARTS_RESOLVING ? 'decrypting' : 'pending';
    return {
      index: i + 1,
      url: `sample://touch-grass-simulator/${i + 1}`,
      direct_url: status === 'resolved' ? sampleLink(i + 1, name) : '',
      filename: name,
      size,
      status,
    };
  });
  return {
    title: SAMPLE_TITLE,
    coverUrl: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(COVER_SVG)}`,
    totalSizeStr: '34.2 GB',
    parts,
    logs: [
      '[Tour] Sample game loaded. Nothing here is downloaded.',
      ...parts
        .filter((p) => p.status === 'resolved')
        .slice(0, 12)
        .map((p) => `[Worker] ${p.filename}: RESOLVED (${(1.4 + (p.index % 6) / 10).toFixed(1)}s)`),
    ],
  };
}

/** One tick of pretend progress: the first part being resolved finishes, and the next one starts. */
export function advanceSample(parts: PartItem[]): PartItem[] {
  const finishing = parts.findIndex((p) => p.status === 'decrypting');
  const starting = parts.findIndex((p) => p.status === 'pending');
  if (finishing === -1 && starting === -1) return parts;
  return parts.map((part, i) => {
    if (i === finishing) return { ...part, status: 'resolved', direct_url: sampleLink(part.index, part.filename || '') };
    if (i === starting) return { ...part, status: 'decrypting' };
    return part;
  });
}
