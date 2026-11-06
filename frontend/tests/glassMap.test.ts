import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildDisplacementPixels, mapCacheKey } from '../src/utils/glassMap.ts';

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
