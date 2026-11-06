import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildDisplacementPixels, buildLensPixels, mapCacheKey } from '../src/utils/glassMap.ts';

const NEUTRAL = 128;

function pixel(data: Uint8ClampedArray, width: number, x: number, y: number) {
  const i = (y * width + x) * 4;
  return { r: data[i], g: data[i + 1], b: data[i + 2], a: data[i + 3] };
}

const map = { width: 200, height: 100, radius: 20, bezel: 16 };

test('produces one fully opaque RGBA pixel for every map position', () => {
  const data = buildDisplacementPixels(map);
  assert.equal(data.length, 200 * 100 * 4);
  assert.equal(pixel(data, 200, 100, 50).a, 255);
  assert.equal(pixel(data, 200, 0, 0).a, 255);
});

test('leaves the flat center of the glass undistorted', () => {
  const center = pixel(buildDisplacementPixels(map), 200, 100, 50);
  assert.equal(center.r, NEUTRAL);
  assert.equal(center.g, NEUTRAL);
});

test('bends the left and right edges toward the center', () => {
  const data = buildDisplacementPixels(map);
  assert.ok(pixel(data, 200, 1, 50).r > NEUTRAL, 'left edge samples further right');
  assert.ok(pixel(data, 200, 198, 50).r < NEUTRAL, 'right edge samples further left');
  assert.equal(pixel(data, 200, 1, 50).g, NEUTRAL);
});

test('bends the top and bottom edges toward the center', () => {
  const data = buildDisplacementPixels(map);
  assert.ok(pixel(data, 200, 100, 1).g > NEUTRAL, 'top edge samples further down');
  assert.ok(pixel(data, 200, 100, 98).g < NEUTRAL, 'bottom edge samples further up');
  assert.equal(pixel(data, 200, 100, 1).r, NEUTRAL);
});

test('bends the most at the very edge and fades out across the bezel', () => {
  const data = buildDisplacementPixels(map);
  const shiftAt = (x: number) => pixel(data, 200, x, 50).r - NEUTRAL;
  assert.ok(shiftAt(0) > shiftAt(4));
  assert.ok(shiftAt(4) > shiftAt(10));
  assert.equal(shiftAt(20), 0, 'past the bezel there is no bend');
});

test('bends rounded corners along the diagonal', () => {
  const data = buildDisplacementPixels(map);
  const corner = pixel(data, 200, 8, 8);
  assert.ok(corner.r > NEUTRAL);
  assert.ok(corner.g > NEUTRAL);
  assert.ok(Math.abs(corner.r - corner.g) <= 2, 'equal shift on both axes at a symmetric corner');
});

test('reaches around large corners that sit outside a thin bezel band', () => {
  const data = buildDisplacementPixels({ width: 300, height: 300, radius: 80, bezel: 10 });
  // On the corner's diagonal, the curve is about 23.4 px in from each side.
  const onCurve = pixel(data, 300, 26, 26);
  assert.ok(onCurve.r > NEUTRAL, 'the corner bends even though it is further in than the bezel');
});

test('treats the two halves of the glass as mirror images', () => {
  const data = buildDisplacementPixels(map);
  for (const [x, y] of [[0, 50], [5, 3], [12, 90], [40, 2]]) {
    const left = pixel(data, 200, x, y);
    const right = pixel(data, 200, 199 - x, y);
    assert.ok(Math.abs((left.r - NEUTRAL) + (right.r - NEUTRAL)) <= 1, `x mirror at ${x},${y}`);
    assert.ok(Math.abs(left.g - right.g) <= 1, `y match at ${x},${y}`);
  }
});

test('copes with a radius larger than half the element, as pill shapes have', () => {
  const data = buildDisplacementPixels({ width: 120, height: 40, radius: 999, bezel: 12 });
  assert.equal(data.length, 120 * 40 * 4);
  assert.ok(pixel(data, 120, 0, 20).r > NEUTRAL);
});

test('copes with a square-cornered element', () => {
  const data = buildDisplacementPixels({ width: 50, height: 50, radius: 0, bezel: 8 });
  assert.ok(pixel(data, 50, 0, 25).r > NEUTRAL);
  assert.equal(pixel(data, 50, 25, 25).r, NEUTRAL);
});

test('copes with a bezel wider than the element', () => {
  const data = buildDisplacementPixels({ width: 10, height: 10, radius: 2, bezel: 50 });
  assert.equal(data.length, 10 * 10 * 4);
});

test('returns nothing to draw for an element with no size', () => {
  assert.equal(buildDisplacementPixels({ width: 0, height: 40, radius: 4, bezel: 8 }).length, 0);
  assert.equal(buildDisplacementPixels({ width: 40, height: 0, radius: 4, bezel: 8 }).length, 0);
});

test('stays fast enough for a full-window surface', () => {
  const started = performance.now();
  buildDisplacementPixels({ width: 1400, height: 900, radius: 24, bezel: 26 });
  assert.ok(performance.now() - started < 120, 'a resize must not stall the interface');
});

test('elements of the same shape share one cached map', () => {
  const key = mapCacheKey({ width: 300, height: 150, radius: 14, bezel: 12 }, 20);
  assert.equal(key, mapCacheKey({ width: 300, height: 150, radius: 14, bezel: 12 }, 20));
  assert.notEqual(key, mapCacheKey({ width: 301, height: 150, radius: 14, bezel: 12 }, 20));
  assert.notEqual(key, mapCacheKey({ width: 300, height: 150, radius: 14, bezel: 12 }, 24));
});

// ---------------------------------------------------------------- The lens a dragged bubble becomes

/** How far, in pixels, a lens pixel samples from, once the map is turned back into shifts. */
function lensShift(lens: { pixels: Uint8ClampedArray; scale: number }, width: number, x: number, y: number) {
  const p = pixel(lens.pixels, width, x, y);
  return { x: ((p.r - 127.5) / 255) * lens.scale, y: ((p.g - 127.5) / 255) * lens.scale };
}

const lensShape = { width: 120, height: 120, radius: 30, bezel: 10 };

test('a lens leaves its exact center where it is', () => {
  const lens = buildLensPixels(lensShape, 6, 1.25);
  const center = lensShift(lens, 120, 60, 60);
  assert.ok(Math.abs(center.x) < 0.6 && Math.abs(center.y) < 0.6);
});

test('a lens magnifies: points beside the center show what is closer to the middle', () => {
  const lens = buildLensPixels(lensShape, 6, 1.25);
  // A point 10.5 px right of center shows what sits 10.5 / 1.25 = 8.4 px right of it.
  assert.ok(Math.abs(lensShift(lens, 120, 70, 60).x - -2.1) < 0.35);
  assert.ok(Math.abs(lensShift(lens, 120, 49, 60).x - 2.1) < 0.35);
  assert.ok(Math.abs(lensShift(lens, 120, 60, 70).y - -2.1) < 0.35);
});

test('the rim of a lens still bends toward the middle, on top of the magnification', () => {
  const lens = buildLensPixels(lensShape, 6, 1.25);
  // The edge pixel's center sits 0.5 px in, so it gets 6 * (1 - 0.5 / 10) ^ 2.2 = 5.4 px of rim bend,
  // plus 59.5 * (1 - 1 / 1.25) = 11.9 px of magnification.
  assert.ok(Math.abs(lensShift(lens, 120, 0, 60).x - 17.3) < 0.6);
});

test('a lens with no zoom bends only at its rim, like any glass', () => {
  const lens = buildLensPixels(lensShape, 6, 1);
  assert.ok(Math.abs(lensShift(lens, 120, 75, 60).x) < 0.6, 'flat inside');
  assert.ok(lensShift(lens, 120, 0, 60).x > 5, 'left edge samples further right');
});

test('a lens map never clips, so its largest bend survives', () => {
  for (const [shape, rim] of [
    [{ width: 58, height: 58, radius: 19, bezel: 10 }, 7],
    [{ width: 150, height: 30, radius: 15, bezel: 10 }, 4],
  ] as const) {
    const { pixels } = buildLensPixels(shape, rim, 1.22);
    for (let i = 0; i < pixels.length; i += 4) {
      assert.ok(pixels[i] >= 1 && pixels[i] <= 254 && pixels[i + 1] >= 1 && pixels[i + 1] <= 254);
    }
  }
});
