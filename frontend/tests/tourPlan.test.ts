import assert from 'node:assert/strict';
import { test } from 'node:test';
import { TOUR_STEPS, placeCard, unionRect } from '../src/utils/tourPlan.ts';
import { COPY } from '../src/utils/voice.ts';

const WINDOW = { width: 1200, height: 800 };
const CARD = { width: 400, height: 200 };

test('the tour has the seven agreed steps, in order', () => {
  assert.deepEqual(
    TOUR_STEPS.map((s) => s.id),
    ['welcome', 'paste', 'hub', 'stage', 'filter', 'send', 'done']
  );
});

test('every step has a title and a line in both voices', () => {
  for (const step of TOUR_STEPS) {
    for (const voice of ['genz', 'classic'] as const) {
      const table = COPY[voice] as Record<string, string>;
      assert.ok(table[`tour.${step.id}.title`], `${voice} title for ${step.id}`);
      assert.ok(table[`tour.${step.id}.body`], `${voice} body for ${step.id}`);
    }
  }
});

test('only the Stage and filter steps let clicks through to the app', () => {
  assert.deepEqual(TOUR_STEPS.filter((s) => s.interactive).map((s) => s.id), ['stage', 'filter']);
});

test('steps about the Stage open the Stage, and the Hub step opens the Hub', () => {
  const view = Object.fromEntries(TOUR_STEPS.map((s) => [s.id, s.view]));
  assert.equal(view.hub, 'community');
  assert.equal(view.stage, 'stage');
  assert.equal(view.filter, 'stage');
  assert.equal(view.send, 'stage');
});

test('with nothing to point at, the card sits in the middle of the window', () => {
  assert.deepEqual(placeCard(null, CARD, WINDOW, 'bottom'), { top: 300, left: 400 });
});

test('the card goes below its target, centered on it, when there is room', () => {
  const bar = { top: 20, left: 100, width: 1000, height: 70 };
  assert.deepEqual(placeCard(bar, CARD, WINDOW, 'bottom'), { top: 106, left: 400 });
});

test('with no room below, the card flips above its target', () => {
  const low = { top: 600, left: 100, width: 400, height: 150 };
  assert.deepEqual(placeCard(low, CARD, WINDOW, 'bottom'), { top: 384, left: 100 });
});

test('a card meant for the right flips left when the window edge is too close', () => {
  const nearEdge = { top: 300, left: 900, width: 200, height: 100 };
  assert.deepEqual(placeCard(nearEdge, { width: 300, height: 200 }, WINDOW, 'right'), { top: 250, left: 584 });
});

test('the card never leaves the window', () => {
  const corner = { top: 0, left: 0, width: 100, height: 40 };
  assert.deepEqual(placeCard(corner, { width: 300, height: 200 }, WINDOW, 'right'), { top: 16, left: 116 });
});

test('when no side has room, the card uses the roomiest side and stays on screen', () => {
  const huge = { top: 60, left: 100, width: 1000, height: 600 };
  assert.deepEqual(placeCard(huge, CARD, WINDOW, 'top'), { top: 584, left: 400 });
});

test('several targets are spotlit as one box around all of them', () => {
  const tabs = { top: 300, left: 100, width: 500, height: 36 };
  const grid = { top: 350, left: 90, width: 900, height: 280 };
  assert.deepEqual(unionRect([tabs, grid]), { top: 300, left: 90, width: 900, height: 330 });
  assert.equal(unionRect([]), null);
});
