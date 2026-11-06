/**
 * Liquid Glass for WebView2, the same material as Expo's GlassView.
 *
 * Chromium can run an SVG filter on what sits behind an element, so glass here
 * really refracts. Each surface gets a displacement map shaped to its own size and
 * corners (see glassMap.ts). The look itself lives in styles/glass.css.
 *
 * One rule to design around: an element only sees through to the page if no ancestor
 * has backdrop-filter, filter, opacity below 1, or a mask. Otherwise it only sees
 * inside that ancestor, so glass nested in glass gets no refraction.
 */

import { buildDisplacementPixels, buildLensPixels, mapCacheKey, type GlassMapShape } from './glassMap';

export type GlassStyle = 'regular' | 'clear' | 'thick' | 'bubble';

export interface LiquidGlassOptions {
  /**
   * regular reads well over anything, clear shows more of what is behind, thick is for long text,
   * and bubble is the see-through lens over a bar's selected item.
   */
  style?: GlassStyle;
  bezel?: number;
  /** Largest bend at the rim, in pixels. */
  strength?: number;
  /** Above 1, the glass becomes a lens that magnifies what is behind it by this much. */
  magnify?: number;
}

interface SharedFilter {
  id: string;
  uses: number;
  element: SVGFilterElement;
}

const SVG_NS = 'http://www.w3.org/2000/svg';
const STORAGE_KEY = 'le_glass_refraction';
const RESIZE_SETTLE_MS = 60;

const STYLE_DEFAULTS: Record<GlassStyle, { bezel: number; strength: number; backdrop: string }> = {
  regular: { bezel: 20, strength: 26, backdrop: '--glass-backdrop' },
  clear: { bezel: 16, strength: 22, backdrop: '--glass-backdrop-clear' },
  thick: { bezel: 26, strength: 30, backdrop: '--glass-backdrop-thick' },
  bubble: { bezel: 12, strength: 11, backdrop: '--glass-backdrop-bubble' },
};

/**
 * A short bubble sits right over its own label, so its rim bends less, or the edges pull in
 * copies of the text. These cap the bend at a share of the bubble's height.
 */
const BUBBLE_RIM_PER_HEIGHT = 0.18;
const LENS_RIM_PER_HEIGHT = 0.12;

const filters = new Map<string, SharedFilter>();
const surfaces = new Set<() => void>();
let defs: SVGDefsElement | null = null;
let nextId = 0;
let refractionOn = true;

function filterDefs(): SVGDefsElement {
  if (!defs) {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('width', '0');
    svg.setAttribute('height', '0');
    svg.style.position = 'absolute';
    defs = document.createElementNS(SVG_NS, 'defs');
    svg.appendChild(defs);
    document.body.appendChild(svg);
  }
  return defs;
}

function renderMap(shape: GlassMapShape, pixels: Uint8ClampedArray): string {
  const canvas = document.createElement('canvas');
  canvas.width = shape.width;
  canvas.height = shape.height;
  canvas.getContext('2d')?.putImageData(new ImageData(pixels as Uint8ClampedArray<ArrayBuffer>, shape.width, shape.height), 0, 0);
  return canvas.toDataURL('image/png');
}

/** Surfaces of the same shape share one filter, so hundreds of game cards cost one map. */
function acquireFilter(key: string, shape: GlassMapShape, build: () => { pixels: Uint8ClampedArray; scale: number }): SharedFilter {
  const existing = filters.get(key);
  if (existing) {
    existing.uses += 1;
    return existing;
  }

  const { pixels, scale } = build();
  const id = `liquid-glass-${++nextId}`;
  const element = document.createElementNS(SVG_NS, 'filter');
  element.setAttribute('id', id);
  element.setAttribute('color-interpolation-filters', 'sRGB');
  element.setAttribute('x', '0');
  element.setAttribute('y', '0');
  element.setAttribute('width', '100%');
  element.setAttribute('height', '100%');

  const image = document.createElementNS(SVG_NS, 'feImage');
  image.setAttribute('href', renderMap(shape, pixels));
  image.setAttribute('x', '0');
  image.setAttribute('y', '0');
  image.setAttribute('width', String(shape.width));
  image.setAttribute('height', String(shape.height));
  image.setAttribute('preserveAspectRatio', 'none');
  image.setAttribute('result', 'map');

  const displace = document.createElementNS(SVG_NS, 'feDisplacementMap');
  displace.setAttribute('in', 'SourceGraphic');
  displace.setAttribute('in2', 'map');
  displace.setAttribute('scale', scale.toFixed(2));
  displace.setAttribute('xChannelSelector', 'R');
  displace.setAttribute('yChannelSelector', 'G');

  element.append(image, displace);
  filterDefs().appendChild(element);

  const filter = { id, uses: 1, element };
  filters.set(key, filter);
  return filter;
}

function releaseFilter(key: string): void {
  const filter = filters.get(key);
  if (!filter) return;
  filter.uses -= 1;
  if (filter.uses <= 0) {
    filter.element.remove();
    filters.delete(key);
  }
}

/** Svelte action: use:liquidGlass makes an element refract what scrolls behind it. */
export function liquidGlass(node: HTMLElement, options: LiquidGlassOptions = {}) {
  let current = options;
  let activeKey: string | null = null;
  let filterId = '';
  let timer: ReturnType<typeof setTimeout> | null = null;

  function clear(): void {
    if (activeKey) releaseFilter(activeKey);
    activeKey = null;
    node.style.removeProperty('backdrop-filter');
  }

  function apply(): void {
    timer = null;
    const width = node.offsetWidth;
    const height = node.offsetHeight;
    if (!refractionOn || width === 0 || height === 0) {
      clear();
      return;
    }

    const style = current.style || 'regular';
    const defaults = STYLE_DEFAULTS[style];
    const isBubble = style === 'bubble';
    const strength = Math.min(current.strength ?? defaults.strength, isBubble ? Math.round(height * BUBBLE_RIM_PER_HEIGHT) : Infinity);
    const shape: GlassMapShape = {
      width,
      height,
      radius: parseFloat(getComputedStyle(node).borderTopLeftRadius) || 0,
      bezel: Math.min(current.bezel ?? defaults.bezel, Math.floor(Math.min(width, height) / (isBubble ? 3 : 2))),
    };

    const zoom = (current.magnify ?? 1) > 1 ? (current.magnify as number) : 0;
    const key = zoom ? `lens:${mapCacheKey(shape, strength)}:${zoom}` : mapCacheKey(shape, strength);
    if (key !== activeKey) {
      const filter = acquireFilter(key, shape, () => {
        if (!zoom) {
          // The filter moves pixels by scale * (channel - 0.5), so the full bend needs twice the strength.
          return { pixels: buildDisplacementPixels(shape), scale: strength * 2 };
        }
        const rim = Math.min(strength, Math.round(height * LENS_RIM_PER_HEIGHT));
        return buildLensPixels({ ...shape, bezel: Math.min(shape.bezel, Math.floor(height / 3)) }, rim, zoom);
      });
      if (activeKey) releaseFilter(activeKey);
      activeKey = key;
      filterId = filter.id;
    }
    node.style.backdropFilter = `url(#${filterId}) var(${defaults.backdrop})`;
  }

  function schedule(): void {
    if (timer === null) timer = setTimeout(apply, RESIZE_SETTLE_MS);
  }

  function applyNow(): void {
    if (timer !== null) clearTimeout(timer);
    apply();
  }

  // The first callback arrives when the element is first laid out, which keeps
  // cards that are still far off screen from doing any work.
  const observer = new ResizeObserver(schedule);
  observer.observe(node);
  surfaces.add(apply);

  return {
    // A deliberate change, like a bubble turning into a lens, shows at once.
    update(next: LiquidGlassOptions = {}) {
      current = next;
      applyNow();
    },
    destroy() {
      observer.disconnect();
      surfaces.delete(apply);
      if (timer !== null) clearTimeout(timer);
      if (activeKey) releaseFilter(activeKey);
    },
  };
}

// ---------------------------------------------------------------- Refraction on and off

function storedChoice(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function applyRefraction(on: boolean): void {
  document.documentElement.dataset.glass = on ? 'full' : 'lite';
  if (on === refractionOn) return;
  refractionOn = on;
  surfaces.forEach((refresh) => refresh());
}

export function isRefractionOn(): boolean {
  return refractionOn;
}

/** The choice from Settings. It is remembered and overrides the automatic check below. */
export function setRefractionChoice(on: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off');
  } catch {}
  applyRefraction(on);
}

const SLOW_FRAME_MS = 28;
const SAMPLE_FRAMES = 90;

/** On a PC that cannot keep up, drop to plain frosted glass for this session. */
export function watchGlassPerformance(): void {
  if (!refractionOn || storedChoice() === 'on') return;

  let frames = 0;
  let started = 0;
  function tick(now: number): void {
    if (document.hidden) return;
    if (frames === 0) started = now;
    frames += 1;
    if (frames <= SAMPLE_FRAMES) {
      requestAnimationFrame(tick);
    } else if ((now - started) / SAMPLE_FRAMES > SLOW_FRAME_MS) {
      console.warn('[Glass] Slow rendering detected, switching to frosted glass for this session.');
      applyRefraction(false);
    }
  }
  requestAnimationFrame(tick);
}

// ---------------------------------------------------------------- The highlight that follows the pointer

const INTERACTIVE_GLASS = '.glass-panel, .glass-card, .left-sidebar, .game-poster-card, .btn-primary';

function trackPointer(): void {
  let latest: PointerEvent | null = null;
  let frame = 0;
  let lit: HTMLElement | null = null;

  function flush(): void {
    frame = 0;
    if (!latest) return;
    const target = latest.target instanceof Element ? latest.target.closest<HTMLElement>(INTERACTIVE_GLASS) : null;
    if (target !== lit) {
      lit?.style.removeProperty('--glass-glare');
      lit = target;
    }
    if (target) {
      const box = target.getBoundingClientRect();
      target.style.setProperty('--glass-x', `${latest.clientX - box.left}px`);
      target.style.setProperty('--glass-y', `${latest.clientY - box.top}px`);
      target.style.setProperty('--glass-glare', '1');
    }
  }

  window.addEventListener(
    'pointermove',
    (event) => {
      latest = event;
      if (!frame) frame = requestAnimationFrame(flush);
    },
    { passive: true }
  );

  document.documentElement.addEventListener('pointerleave', () => {
    latest = null;
    lit?.style.removeProperty('--glass-glare');
    lit = null;
  });
}

/** Call once when the app starts. */
export function initLiquidGlass(): void {
  const prefersLess = window.matchMedia('(prefers-reduced-transparency: reduce)').matches;
  applyRefraction(storedChoice() !== 'off' && !prefersLess);
  trackPointer();
}
