import assert from 'node:assert/strict';
import { test } from 'node:test';
import { COPY, readVoice, splashLine, wording } from '../src/utils/voice.ts';

const saved = (value: string | null) => ({ getItem: () => value });

test('the GenZ voice is the default', () => {
  assert.equal(readVoice(null), 'genz');
  assert.equal(readVoice(saved(null)), 'genz');
});

test('a saved choice of classic wording is kept', () => {
  assert.equal(readVoice(saved('classic')), 'classic');
});

test('an unknown or unreadable saved value falls back to GenZ', () => {
  assert.equal(readVoice(saved('pirate')), 'genz');
  assert.equal(readVoice({ getItem: () => { throw new Error('storage blocked'); } }), 'genz');
});

test('classic wording keeps what the app said before, with names and numbers filled in', () => {
  assert.equal(wording('classic', 'toast.copiedAll', { count: 14 }), 'Copied all 14 direct links to clipboard!');
  assert.equal(wording('classic', 'toast.exported', { file: 'Neon_Drift.txt' }), 'Saved Neon_Drift.txt to Downloads!');
  assert.equal(wording('classic', 'vault.empty'), 'No saved extractions found in database.');
});

test('the tour opens with the GenZ title that was agreed', () => {
  assert.equal(wording('genz', 'tour.welcome.title'), 'Welcome in, bestie');
  assert.equal(wording('genz', 'tour.done.title'), "You ate. Tour's over.");
});

test('a GenZ success pop-up still says what happened', () => {
  assert.match(wording('genz', 'toast.pushed', { count: 14 }), /14/);
  assert.match(wording('genz', 'toast.exported', { file: 'Neon_Drift.txt' }), /Neon_Drift\.txt/);
});

test('a placeholder with no value stays visible instead of disappearing', () => {
  assert.match(wording('genz', 'toast.copiedAll'), /\{count\}/);
});

test('every line exists in both voices, and none is blank', () => {
  assert.deepEqual(Object.keys(COPY.classic).sort(), Object.keys(COPY.genz).sort());
  for (const table of [COPY.genz, COPY.classic]) {
    for (const [key, text] of Object.entries(table)) assert.ok(text.trim(), `${key} is blank`);
  }
});

test('both voices use the same placeholders in each line', () => {
  const holes = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
  for (const key of Object.keys(COPY.genz) as (keyof typeof COPY.genz)[]) {
    assert.deepEqual(holes(COPY.genz[key]), holes(COPY.classic[key]), key);
  }
});

test('the splash shows its steps in the chosen voice and keeps the cover count', () => {
  assert.equal(splashLine('classic', 'Loading covers 3 of 12'), 'Loading covers 3 of 12');
  assert.match(splashLine('genz', 'Loading covers 3 of 12'), /3 of 12/);
  assert.notEqual(splashLine('genz', 'Connecting'), 'Connecting');
  assert.equal(splashLine('classic', 'Connecting'), 'Connecting');
});

test('a splash step it does not know is shown as it came', () => {
  assert.equal(splashLine('genz', 'Something brand new'), 'Something brand new');
});
