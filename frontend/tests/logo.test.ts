import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

// The logo is drawn twice: public/favicon.svg feeds the icons, and BrandLogo.svelte draws it
// in the theme's colors inside the app. Both must stay the same drawing.
const favicon = readFileSync(new URL('../public/favicon.svg', import.meta.url), 'utf8');
const component = readFileSync(new URL('../src/components/BrandLogo.svelte', import.meta.url), 'utf8');

const paths = (svg: string) => [...svg.matchAll(/\sd="([^"]+)"/g)].map((m) => m[1].replace(/\s+/g, ' ').trim());
const tiles = (svg: string) => [...svg.matchAll(/<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="([\d.]+)"/g)].map((m) => m.slice(1).join(','));

test('the in-app logo draws the same shapes as the icon file', () => {
  assert.equal(paths(favicon).length, 2, 'a bolt and a tray');
  assert.deepEqual(paths(component), paths(favicon));
});

test('the in-app logo sits on the same glass tile as the icon file', () => {
  assert.ok(tiles(favicon).length >= 2);
  assert.deepEqual(tiles(component), tiles(favicon));
});
