import assert from 'node:assert/strict';
import { test } from 'node:test';
import { chooseLaunchScreen } from '../src/utils/launch.ts';

const fresh = { tourShown: false, seenThisVersion: false, seenEarlierVersion: false };

test('a brand-new install opens the tour, not What\'s New', () => {
  assert.equal(chooseLaunchScreen(fresh), 'tour');
});

test('after an update, What\'s New opens and the tour does not play again', () => {
  assert.equal(chooseLaunchScreen({ ...fresh, tourShown: true, seenEarlierVersion: true }), 'whats-new');
});

test('an update opens What\'s New even for someone who never finished the tour back then', () => {
  assert.equal(chooseLaunchScreen({ ...fresh, seenEarlierVersion: true }), 'whats-new');
});

test('once this version has been seen, nothing opens by itself', () => {
  assert.equal(chooseLaunchScreen({ tourShown: true, seenThisVersion: true, seenEarlierVersion: true }), 'none');
  assert.equal(chooseLaunchScreen({ ...fresh, seenThisVersion: true }), 'none');
});
