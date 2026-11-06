/**
 * The math behind Liquid Glass refraction.
 *
 * Real glass bends light most at its curved rim and not at all across its flat
 * center. This builds that shape as a displacement map for feDisplacementMap: the
 * red channel moves pixels sideways, the green channel moves them up and down, and
 * 128 means no movement. Every edge pulls toward the center, like a convex lens.
 */

export interface GlassMapShape {
  width: number;
  height: number;
  radius: number;
  /** How far in from the edge the glass stays curved, in pixels. */
  bezel: number;
}

const NEUTRAL = 128;
const RANGE = 127;
const NEUTRAL_OPAQUE_PIXEL = 0xff808080;

/** How sharply the bend fades across the bezel. Higher keeps it closer to the rim. */
const FALLOFF = 2.2;

/** A rounded corner's curve sits this share of its radius further in than the straight edges. */
const CORNER_REACH = 0.3;

export function mapCacheKey(shape: GlassMapShape, strength: number): string {
  return `${shape.width}x${shape.height}:${shape.radius}:${shape.bezel}:${strength}`;
}

export function buildDisplacementPixels({ width, height, radius, bezel }: GlassMapShape): Uint8ClampedArray {
  const w = Math.round(width);
  const h = Math.round(height);
  if (w <= 0 || h <= 0) return new Uint8ClampedArray(0);

  const data = new Uint8ClampedArray(w * h * 4);
  new Uint32Array(data.buffer).fill(NEUTRAL_OPAQUE_PIXEL);

  const halfW = w / 2;
  const halfH = h / 2;
  const r = Math.min(Math.max(radius, 0), halfW, halfH);
  const curve = Math.max(bezel, 1);
  const innerW = halfW - r;
  const innerH = halfH - r;

  function bend(x: number, y: number): void {
    const px = x + 0.5 - halfW;
    const py = y + 0.5 - halfH;
    const qx = Math.abs(px) - innerW;
    const qy = Math.abs(py) - innerH;

    let nx = 0;
    let ny = 0;
    let fromEdge: number;
    if (qx > 0 && qy > 0) {
      const length = Math.hypot(qx, qy);
      fromEdge = r - length;
      nx = qx / length;
      ny = qy / length;
    } else if (qx > qy) {
      fromEdge = r - qx;
      nx = 1;
    } else {
      fromEdge = r - qy;
      ny = 1;
    }
    if (fromEdge >= curve) return;

    const amount = Math.pow(1 - Math.max(fromEdge, 0) / curve, FALLOFF);
    const i = (y * w + x) * 4;
    data[i] = NEUTRAL - Math.sign(px) * nx * amount * RANGE;
    data[i + 1] = NEUTRAL - Math.sign(py) * ny * amount * RANGE;
  }

  // Only the band near the edges can bend, so the flat middle is skipped entirely.
  const band = Math.ceil(curve + r * CORNER_REACH);
  for (let y = 0; y < h; y++) {
    if (y < band || y >= h - band || band * 2 >= w) {
      for (let x = 0; x < w; x++) bend(x, y);
    } else {
      for (let x = 0; x < band; x++) bend(x, y);
      for (let x = w - band; x < w; x++) bend(x, y);
    }
  }
  return data;
}
