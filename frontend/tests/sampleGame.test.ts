import assert from 'node:assert/strict';
import { test } from 'node:test';
import { classifyPart } from '../src/utils/partCategory.ts';
import { advanceSample, createSampleGame } from '../src/utils/sampleGame.ts';
import type { PartItem } from '../src/types.ts';

const count = (parts: PartItem[], status: PartItem['status']) => parts.filter((p) => p.status === status).length;

test('the English voice pack counts as part of the game', () => {
  assert.equal(classifyPart('fg-selective-english.bin'), 'core');
});

test('voice packs in other languages are language packs', () => {
  assert.equal(classifyPart('fg-selective-french.bin'), 'language');
});

test('optional, bonus and soundtrack files are extras', () => {
  assert.equal(classifyPart('fg-optional-bonus-content.bin'), 'optional');
  assert.equal(classifyPart('Game_OST_soundtrack.rar'), 'optional');
});

test('ordinary archive parts are part of the game', () => {
  assert.equal(classifyPart('Game_--_fitgirl-repacks.site_--_.part01.rar'), 'core');
  assert.equal(classifyPart(''), 'core');
});

test('the sample game has the language packs and the bonus pack the filter step shows', () => {
  const { parts } = createSampleGame();
  assert.equal(parts.filter((p) => classifyPart(p.filename || '') === 'language').length, 6);
  assert.equal(parts.filter((p) => classifyPart(p.filename || '') === 'optional').length, 1);
});

test('the sample game has no real links, so nothing can be downloaded from it', () => {
  for (const part of createSampleGame().parts) {
    assert.doesNotMatch(part.url, /^https?:/i);
    assert.doesNotMatch(part.direct_url || '', /^https?:/i);
  }
});

test('the sample starts part-way through, so the Defrag Matrix has something to show', () => {
  const { parts } = createSampleGame();
  assert.ok(count(parts, 'resolved') > 0);
  assert.ok(count(parts, 'decrypting') > 0);
  assert.ok(count(parts, 'pending') > 0);
});

test('each tick finishes one part and starts the next', () => {
  const before = createSampleGame().parts;
  const after = advanceSample(before);
  assert.equal(count(after, 'resolved'), count(before, 'resolved') + 1);
  assert.equal(count(after, 'decrypting'), count(before, 'decrypting'));
  assert.equal(count(after, 'pending'), count(before, 'pending') - 1);
});

test('once every part has resolved, ticking changes nothing', () => {
  let parts = createSampleGame().parts;
  for (let i = 0; i < parts.length + 5; i++) parts = advanceSample(parts);
  assert.equal(count(parts, 'resolved'), parts.length);
  assert.deepEqual(advanceSample(parts), parts);
});

test('a tick leaves the parts it was given untouched', () => {
  const before = createSampleGame().parts;
  const snapshot = JSON.stringify(before);
  advanceSample(before);
  assert.equal(JSON.stringify(before), snapshot);
});
