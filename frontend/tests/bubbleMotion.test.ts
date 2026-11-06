import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  DRAG_START_PX,
  MAX_STRETCH,
  Press,
  bubbleFrame,
  isSettled,
  nearestIndex,
  rubberBand,
  stepSpring,
  stretchAt,
  type Spring,
} from '../src/utils/bubbleMotion.ts';

function run(target: number, seconds: number, dt: number) {
  let spring: Spring = { pos: 0, vel: 0 };
  let highest = 0;
  for (let t = 0; t < seconds; t += dt) {
    spring = stepSpring(spring, target, dt);
    highest = Math.max(highest, spring.pos);
  }
  return { spring, highest };
}

test('the bubble comes to rest on the item it was sent to', () => {
  const { spring } = run(64, 2, 1 / 60);
  assert.ok(Math.abs(spring.pos - 64) < 0.05);
  assert.ok(isSettled(spring, 64));
});

test('it overshoots a little before settling, which is what makes it feel liquid', () => {
  const { highest } = run(100, 2, 1 / 60);
  assert.ok(highest > 100, 'goes past the target');
  assert.ok(highest < 115, 'but only a little');
});

test('it still settles when a slow PC delivers long frames', () => {
  const { spring } = run(64, 3, 1 / 12);
  assert.ok(Number.isFinite(spring.pos));
  assert.ok(Math.abs(spring.pos - 64) < 0.05);
});

test('with reduced motion the bubble still glides, but never overshoots', () => {
  let spring: Spring = { pos: 0, vel: 0 };
  let highest = 0;
  for (let t = 0; t < 2; t += 1 / 60) {
    spring = stepSpring(spring, 100, 1 / 60, true);
    highest = Math.max(highest, spring.pos);
  }
  assert.ok(highest <= 100, 'no wobble past the target');
  assert.ok(Math.abs(spring.pos - 100) < 0.05, 'and it still arrives');
  const firstFrame = stepSpring({ pos: 0, vel: 0 }, 100, 1 / 60, true);
  assert.ok(firstFrame.pos > 0 && firstFrame.pos < 100, 'it moves rather than jumping');
});

test('a moving bubble is not yet settled', () => {
  assert.equal(isSettled({ pos: 64, vel: 300 }, 64), false);
  assert.equal(isSettled({ pos: 40, vel: 0 }, 64), false);
});

test('the bubble is round at rest and stretches more the faster it moves', () => {
  assert.equal(stretchAt(0), 0);
  assert.ok(stretchAt(400) > 0);
  assert.ok(stretchAt(1500) > stretchAt(400));
  assert.equal(stretchAt(-1500), stretchAt(1500), 'direction does not matter');
  assert.equal(stretchAt(1_000_000), MAX_STRETCH, 'it never stretches without limit');
});

test('between the first and last item the bubble follows the pointer exactly', () => {
  assert.equal(rubberBand(50, 0, 100), 50);
  assert.equal(rubberBand(0, 0, 100), 0);
  assert.equal(rubberBand(100, 0, 100), 100);
});

test('past either end the bubble gives only a little, like a rubber band', () => {
  assert.equal(rubberBand(130, 0, 100), 109);
  assert.equal(rubberBand(-20, 0, 100), -6);
});

test('letting go lands on the closest item', () => {
  const centers = [24, 88, 152];
  assert.equal(nearestIndex(centers, 100), 1);
  assert.equal(nearestIndex(centers, 130), 2);
  assert.equal(nearestIndex(centers, -50), 0);
  assert.equal(nearestIndex(centers, 400), 2);
});

test('a press that never moves far is a click', () => {
  const press = new Press(100);
  assert.equal(press.move(103), 'pending');
  assert.equal(press.move(97), 'pending');
  assert.equal(press.isDrag, false);
});

test('moving past the threshold starts a drag, and reports the start once', () => {
  const press = new Press(100);
  assert.equal(press.move(100 + DRAG_START_PX - 0.5), 'pending');
  assert.equal(press.move(100 + DRAG_START_PX), 'started');
  assert.equal(press.move(140), 'dragging');
  assert.equal(press.isDrag, true);
});

test('a drag stays a drag even if the pointer comes back to where it started', () => {
  const press = new Press(100);
  press.move(90);
  assert.equal(press.move(100), 'dragging');
  assert.equal(press.isDrag, true);
});

test('a vertical bubble in motion grows taller and narrower', () => {
  const frame = bubbleFrame({ axis: 'y', pos: 80, cross: 7, stretch: 0.3, swell: 0 });
  assert.ok(frame.scaleY > 1);
  assert.ok(frame.scaleX < 1);
  assert.equal(frame.x, 7);
  assert.equal(frame.y, 80);
});

test('a horizontal bubble in motion grows wider and shorter', () => {
  const frame = bubbleFrame({ axis: 'x', pos: 120, cross: 3, stretch: 0.3, swell: 0 });
  assert.ok(frame.scaleX > 1);
  assert.ok(frame.scaleY < 1);
  assert.equal(frame.x, 120);
  assert.equal(frame.y, 3);
});

test('at rest the bubble is its normal size and fully tinted', () => {
  const frame = bubbleFrame({ axis: 'y', pos: 0, cross: 0, stretch: 0, swell: 0 });
  assert.equal(frame.scaleX, 1);
  assert.equal(frame.scaleY, 1);
  assert.equal(frame.clear, 0);
});

test('holding the bubble down swells it evenly and makes it clearer', () => {
  const frame = bubbleFrame({ axis: 'x', pos: 0, cross: 0, stretch: 0, swell: 1 });
  assert.ok(frame.scaleX > 1);
  assert.equal(frame.scaleX, frame.scaleY);
  assert.ok(frame.clear > 0);
  assert.ok(frame.clear <= 1);
});
