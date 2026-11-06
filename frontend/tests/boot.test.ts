import assert from 'node:assert/strict';
import { test } from 'node:test';
import { pickCovers, runBoot, type BootDeps } from '../src/utils/boot.ts';

const FAST = { minMs: 0, maxMs: 1000, coverCount: 3, perImageMs: 200, syncWaitMs: 200, bridgeWaitMs: 200 };
const never = <T>() => new Promise<T>(() => {});

function game(n: number) {
  return { image_url: `https://example.com/${n}.jpg` };
}

function fakeDeps(overrides: Partial<BootDeps> = {}): BootDeps & { loaded: string[]; steps: string[] } {
  const loaded: string[] = [];
  const steps: string[] = [];
  return {
    loaded,
    steps,
    waitForBridge: async () => {
      steps.push('bridge');
      return true;
    },
    loadFeed: async () => {
      steps.push('feed');
      return { games: [game(1), game(2)], syncing: false };
    },
    waitForSync: async () => {
      steps.push('sync');
      return { games: [game(1), game(2)], syncing: false };
    },
    preloadImage: async (url: string) => {
      loaded.push(url);
    },
    ...overrides,
  };
}

function record() {
  const seen: { progress: number; status: string }[] = [];
  return { seen, onProgress: (progress: number, status: string) => seen.push({ progress, status }) };
}

test('waits for the bridge, then the games, then their covers', async () => {
  const deps = fakeDeps();
  const { onProgress } = record();
  await runBoot(deps, onProgress, FAST);
  assert.deepEqual(deps.steps, ['bridge', 'feed']);
  assert.deepEqual(deps.loaded, ['https://example.com/1.jpg', 'https://example.com/2.jpg']);
});

test('progress only moves forward and ends at 100%', async () => {
  const { seen, onProgress } = record();
  await runBoot(fakeDeps(), onProgress, FAST);
  const values = seen.map((step) => step.progress);
  assert.deepEqual(values, [...values].sort((a, b) => a - b));
  assert.equal(values.at(-1), 1);
});

test('counts covers as they load so the user sees real progress', async () => {
  const { seen, onProgress } = record();
  await runBoot(fakeDeps(), onProgress, FAST);
  assert.ok(seen.some((step) => step.status.includes('1 of 2')));
  assert.ok(seen.some((step) => step.status.includes('2 of 2')));
});

test('waits for a running sync so the first screen shows current games', async () => {
  const fresh = [game(7), game(8)];
  const deps = fakeDeps({
    loadFeed: async () => ({ games: [game(1)], syncing: true }),
    waitForSync: async () => ({ games: fresh, syncing: false }),
  });
  await runBoot(deps, record().onProgress, FAST);
  assert.deepEqual(deps.loaded, ['https://example.com/7.jpg', 'https://example.com/8.jpg']);
});

test('a sync that never ends falls back to the games already known', async () => {
  const deps = fakeDeps({
    loadFeed: async () => ({ games: [game(1)], syncing: true }),
    waitForSync: () => never(),
  });
  const started = Date.now();
  await runBoot(deps, record().onProgress, FAST);
  assert.deepEqual(deps.loaded, ['https://example.com/1.jpg']);
  assert.ok(Date.now() - started < 800);
});

test('a sync that fails still finishes', async () => {
  const deps = fakeDeps({
    loadFeed: async () => ({ games: [], syncing: true }),
    waitForSync: async () => {
      throw new Error('offline');
    },
  });
  await runBoot(deps, record().onProgress, FAST);
  assert.deepEqual(deps.loaded, []);
});

test('only loads as many covers as the first screen shows', async () => {
  const deps = fakeDeps({ loadFeed: async () => ({ games: [1, 2, 3, 4, 5, 6].map(game), syncing: false }) });
  await runBoot(deps, record().onProgress, FAST);
  assert.equal(deps.loaded.length, 3);
});

test('one cover that never loads does not hold up the others or the app', async () => {
  const deps = fakeDeps({
    loadFeed: async () => ({ games: [game(1), game(2)], syncing: false }),
    preloadImage: (url: string) => {
      if (url.endsWith('1.jpg')) return never();
      deps.loaded.push(url);
      return Promise.resolve();
    },
  });
  const started = Date.now();
  await runBoot(deps, record().onProgress, FAST);
  assert.deepEqual(deps.loaded, ['https://example.com/2.jpg']);
  assert.ok(Date.now() - started < 800);
});

test('a cover that fails to load is skipped', async () => {
  const { seen, onProgress } = record();
  const deps = fakeDeps({ preloadImage: () => Promise.reject(new Error('404')) });
  await runBoot(deps, onProgress, FAST);
  assert.equal(seen.at(-1)?.progress, 1);
});

test('a bridge that never arrives cannot hold the app on the splash', async () => {
  const deps = fakeDeps({ waitForBridge: () => never() });
  const started = Date.now();
  await runBoot(deps, record().onProgress, { ...FAST, maxMs: 150 });
  assert.ok(Date.now() - started < 600);
});

test('no bridge means no attempt to load games', async () => {
  const deps = fakeDeps({ waitForBridge: async () => false });
  const { seen, onProgress } = record();
  await runBoot(deps, onProgress, FAST);
  assert.deepEqual(deps.steps, []);
  assert.equal(seen.at(-1)?.progress, 1);
});

test('a crash in any step still ends the boot and never rejects', async () => {
  const deps = fakeDeps({
    loadFeed: async () => {
      throw new Error('boom');
    },
  });
  const { seen, onProgress } = record();
  await runBoot(deps, onProgress, FAST);
  assert.equal(seen.at(-1)?.progress, 1);
});

test('the hard limit wins even if everything hangs', async () => {
  const deps = fakeDeps({ loadFeed: () => never() });
  const started = Date.now();
  await runBoot(deps, record().onProgress, { ...FAST, maxMs: 120 });
  assert.ok(Date.now() - started < 500);
});

test('stays on screen long enough to read on a fast machine', async () => {
  const started = Date.now();
  await runBoot(fakeDeps(), record().onProgress, { ...FAST, minMs: 150 });
  assert.ok(Date.now() - started >= 140);
});

test('progress after the hard limit is ignored so the bar cannot jump back', async () => {
  let finishCover: () => void = () => {};
  const deps = fakeDeps({ preloadImage: () => new Promise<void>((resolve) => (finishCover = resolve)) });
  const { seen, onProgress } = record();
  await runBoot(deps, onProgress, { ...FAST, maxMs: 60, perImageMs: 500 });
  const count = seen.length;
  finishCover();
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(seen.length, count);
});

test('only real web images are preloaded', () => {
  const games = [
    { image_url: 'https://example.com/a.jpg' },
    { image_url: 'http://example.com/b.jpg' },
    { image_url: 'data:image/svg+xml;utf8,%3Csvg%3E' },
    { image_url: '' },
    {},
    { image_url: 'https://example.com/a.jpg' },
  ];
  assert.deepEqual(pickCovers(games, 10), ['https://example.com/a.jpg', 'http://example.com/b.jpg']);
});
