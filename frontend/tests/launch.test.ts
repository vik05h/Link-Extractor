import assert from 'node:assert/strict';
import { test } from 'node:test';
import { chooseLaunchScreen } from '../src/utils/launch.ts';

test('a brand-new install opens the tour, not What\'s New', () => {
  assert.equal(chooseLaunchScreen({ tourCompleted: false, seenThisVersion: false }), 'tour');
});

test('after an update, What\'s New opens and the tour does not play again', () => {
  assert.equal(chooseLaunchScreen({ tourCompleted: true, seenThisVersion: false }), 'whats-new');
});

test('once this version has been seen, nothing opens by itself', () => {
  assert.equal(chooseLaunchScreen({ tourCompleted: true, seenThisVersion: true }), 'none');
});

test('someone who never finished or skipped the tour still gets it', () => {
  assert.equal(chooseLaunchScreen({ tourCompleted: false, seenThisVersion: true }), 'tour');
});
