/**
 * What happens behind the startup splash: connect to Python, load the community
 * games, then load the covers the first screen shows, reporting real progress.
 *
 * The one rule is that this always ends. A slow network, a dead image host or a
 * crash can shorten what gets preloaded, but it can never hold the app on the splash.
 */

export interface CoverSource {
  image_url?: string;
}

export interface FeedSnapshot {
  games?: CoverSource[];
  syncing?: boolean;
}

export interface BootDeps {
  waitForBridge(): Promise<boolean>;
  /** The games known right now. syncing means a newer list is on its way. */
  loadFeed(): Promise<FeedSnapshot | null>;
  /** Resolves with the new list when the running sync ends. */
  waitForSync(): Promise<FeedSnapshot | null>;
  preloadImage(url: string): Promise<unknown>;
}

export interface BootOptions {
  /** Shortest time on screen, so a fast machine does not get a flash. */
  minMs: number;
  /** Longest time on screen, whatever else is happening. */
  maxMs: number;
  /** Covers to load up front: about what the first screen shows. */
  coverCount: number;
  perImageMs: number;
  syncWaitMs: number;
  bridgeWaitMs: number;
}

export const DEFAULT_BOOT_OPTIONS: BootOptions = {
  minMs: 1400,
  maxMs: 7000,
  coverCount: 12,
  perImageMs: 2500,
  syncWaitMs: 4000,
  bridgeWaitMs: 5000,
};

type Report = (progress: number, status: string) => void;

/** The steps the splash reports, in plain words. utils/voice.ts gives each one the chosen voice. */
export const BOOT_STATUS = {
  starting: 'Starting up',
  connecting: 'Connecting',
  games: 'Loading community games',
  covers: 'Loading covers',
  ready: 'Ready',
} as const;

const COVERS_START = 0.55;
const COVERS_RANGE = 0.42;

/** Resolves with the promise's result, or with the fallback once time runs out. */
function withinTime<T>(work: Promise<T>, ms: number, fallback: T): Promise<T> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(fallback), ms);
    const finish = (value: T) => {
      clearTimeout(timer);
      resolve(value);
    };
    work.then(finish, () => finish(fallback));
  });
}

export function pickCovers(games: CoverSource[], count: number): string[] {
  const urls = games
    .map((game) => game.image_url || '')
    .filter((url) => /^https?:\/\//i.test(url));
  return [...new Set(urls)].slice(0, count);
}

async function loadEverything(deps: BootDeps, report: Report, options: BootOptions): Promise<void> {
  report(0.12, BOOT_STATUS.connecting);
  const ready = await withinTime(deps.waitForBridge(), options.bridgeWaitMs, false);
  if (!ready) return;

  report(0.3, BOOT_STATUS.games);
  let feed = await deps.loadFeed();
  if (feed?.syncing) {
    const synced = await withinTime(deps.waitForSync(), options.syncWaitMs, null);
    if (synced?.games) feed = synced;
  }

  const covers = pickCovers(feed?.games || [], options.coverCount);
  if (covers.length === 0) return;

  report(COVERS_START, BOOT_STATUS.covers);
  let done = 0;
  await Promise.all(
    covers.map(async (url) => {
      await withinTime(Promise.resolve().then(() => deps.preloadImage(url)), options.perImageMs, undefined);
      done += 1;
      report(COVERS_START + (COVERS_RANGE * done) / covers.length, `${BOOT_STATUS.covers} ${done} of ${covers.length}`);
    })
  );
}

export async function runBoot(deps: BootDeps, onProgress: Report, options: Partial<BootOptions> = {}): Promise<void> {
  const settings = { ...DEFAULT_BOOT_OPTIONS, ...options };
  const started = Date.now();
  let open = true;
  let furthest = 0;

  const report: Report = (progress, status) => {
    if (!open || progress < furthest) return;
    furthest = progress;
    onProgress(progress, status);
  };

  report(0.05, BOOT_STATUS.starting);
  const work = loadEverything(deps, report, settings).catch((error) => {
    console.error('[Boot] Startup step failed:', error);
  });
  await withinTime(work, settings.maxMs, undefined);

  const remaining = settings.minMs - (Date.now() - started);
  if (remaining > 0) {
    await new Promise((resolve) => setTimeout(resolve, remaining));
  }
  open = false;
  onProgress(1, BOOT_STATUS.ready);
}
