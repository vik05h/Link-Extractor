/**
 * The app's two voices: GenZ by default, and classic for anyone who switches it off in Settings.
 *
 * The voice covers the tour, the splash, success pop-ups, empty screens, the clipboard pop-up,
 * and the top of What's New. Errors, warnings, anything about updates, safety or deleting,
 * dialogs that ask for a choice, button labels, Settings and the Issue Center stay plain,
 * so they are written in place and not here. Classic lines keep what the app said before.
 */

import { derived, get, writable } from 'svelte/store';
// The extension lets Node's test runner load this module too.
import { BOOT_STATUS } from './boot.ts';

export type Voice = 'genz' | 'classic';

export const VOICE_KEY = 'le_voice';

const GENZ = {
  'tour.step': '{n} / {total}',
  'tour.welcome.title': 'Welcome in, bestie',
  'tour.welcome.body': "Paste a FitGirl link, get direct downloads. Here's the 30-second tour.",
  'tour.paste.title': 'Paste it, we got you',
  'tour.paste.body': "Drop a FitGirl game page here and hit Extract & Resolve. Copy one anywhere and we'll offer to grab it.",
  'tour.hub.title': 'The squad already did it',
  'tour.hub.body': 'Other users already resolved these. Instant Load gives you the links in 0 seconds.',
  'tour.stage.title': 'Let it cook',
  'tour.stage.body': 'Each block is one part of the game, and it lights up when its link is ready. The tabs show the links or the log.',
  'tour.filter.title': 'Gatekeep your SSD',
  'tour.filter.body': "Skip voice packs in languages you don't need, plus bonus extras. Less to download, same game.",
  'tour.send.title': 'Send it',
  'tour.send.body': 'Push every link to JDownloader in one click, or copy them, or export a file.',
  'tour.done.title': "You ate. Tour's over.",
  'tour.done.body': 'Past extractions live in the Vault, themes in Settings. Click ? to replay this anytime.',
  'tour.sampleStatus': 'Sample game for the tour. Nothing here downloads, promise.',
  'tour.tryIt': 'Go ahead, poke at it. Clicks inside the glow work.',

  'splash.starting': 'Waking up',
  'splash.connecting': 'Linking up with the engine',
  'splash.games': "Pulling the squad's games",
  'splash.covers': 'Loading the cover art',
  'splash.coversCount': 'Cover art {done} of {total}',
  'splash.ready': "We're so back",

  'toast.loadedParts': 'Got {count} parts for {title}. Zero wait, big W.',
  'toast.loadedFromVault': '{title} is back from the Vault.',
  'toast.copiedAll': "Copied {count} links. You're set.",
  'toast.pushed': 'Sent {count} links to JDownloader. Go off.',
  'toast.exported': 'Saved {file} to Downloads. Clean.',
  'toast.verified': 'All {count} parts verified ({size}). We cooked.',

  'hub.noMatch': 'Nothing matches that. Try another name.',
  'hub.offlineEmpty': 'The community list is offline rn. Try again in a bit.',
  'hub.empty': 'No games here yet. Be the first to drop one.',

  'vault.empty': "Vault's empty. Your extractions will live here.",

  'stage.emptyTitle': 'Nothing cooking yet',
  'stage.emptyBody': 'Paste a FitGirl link up top, or grab a game from the Hub.',

  'clipboard.title': 'Caught a FitGirl link in your clipboard',

  'whatsNew.firstRunTitle': 'NEW DROP: {version}',
  'whatsNew.firstRunIntro': "Here's what's new. The tour button is down there if you want it.",
  'whatsNew.title': "WHAT'S THE TEA",
  'whatsNew.intro': 'Every version and what changed, plus updates.',
} as const;

export type CopyKey = keyof typeof GENZ;

const CLASSIC: Record<CopyKey, string> = {
  'tour.step': 'Step {n} of {total}',
  'tour.welcome.title': 'Welcome to Link Extractor',
  'tour.welcome.body': 'Paste a FitGirl link and get direct download links. This quick tour shows you around.',
  'tour.paste.title': 'Paste a link',
  'tour.paste.body': 'Paste a FitGirl game page here and click Extract & Resolve. If you copy a FitGirl link anywhere, the app offers to resolve it.',
  'tour.hub.title': 'Community Hub',
  'tour.hub.body': 'Other users have already resolved these games. Instant Load gives you their links right away.',
  'tour.stage.title': 'Watch the parts resolve',
  'tour.stage.body': 'Each block is one part of the game. It lights up when its link is ready. Use the tabs to see the links or the log.',
  'tour.filter.title': 'Skip what you do not need',
  'tour.filter.body': 'Leave out voice packs in other languages and bonus extras. You download less and get the same game.',
  'tour.send.title': 'Send the links',
  'tour.send.body': 'Push every link to JDownloader in one click, copy them, or export them to a file.',
  'tour.done.title': 'You are all set',
  'tour.done.body': 'Past extractions are in the Vault and themes are in Settings. Click ? to see this tour again.',
  'tour.sampleStatus': 'Sample game for the tour. Nothing here is downloaded.',
  'tour.tryIt': 'Try it: clicks inside the highlighted area work.',

  'splash.starting': 'Starting up',
  'splash.connecting': 'Connecting',
  'splash.games': 'Loading community games',
  'splash.covers': 'Loading covers',
  'splash.coversCount': 'Loading covers {done} of {total}',
  'splash.ready': 'Ready',

  'toast.loadedParts': 'Loaded {count} parts for {title} with 0s wait!',
  'toast.loadedFromVault': 'Loaded {title} from History!',
  'toast.copiedAll': 'Copied all {count} direct links to clipboard!',
  'toast.pushed': 'Pushed {count} links to JDownloader 2!',
  'toast.exported': 'Saved {file} to Downloads!',
  'toast.verified': '100% Verified! {count} parts ready ({size})',

  'hub.noMatch': 'No community repacks found matching your search.',
  'hub.offlineEmpty': 'The community list is not available right now.',
  'hub.empty': 'No community repacks yet.',

  'vault.empty': 'No saved extractions found in database.',

  'stage.emptyTitle': 'Cockpit Ready',
  'stage.emptyBody': 'Paste a FitGirl game URL in the bar above or choose a pre-fetched game from the Community Hub.',

  'clipboard.title': 'FitGirl Repack Link Detected in Clipboard!',

  'whatsNew.firstRunTitle': 'WELCOME TO LINK EXTRACTOR {version}',
  'whatsNew.firstRunIntro': 'Explore new features, highlights & quick interactive tutorial',
  'whatsNew.title': "WHAT'S NEW & UPDATES",
  'whatsNew.intro': 'Version comparison, release highlights & auto-updater',
};

export const COPY: Readonly<Record<Voice, Readonly<Record<CopyKey, string>>>> = { genz: GENZ, classic: CLASSIC };

export type Params = Record<string, string | number>;

/** The line for `key` in `voice`. A {name} with no value stays visible, so a gap shows up in testing. */
export function wording(voice: Voice, key: CopyKey, params: Params = {}): string {
  return COPY[voice][key].replace(/\{(\w+)\}/g, (hole, name: string) => (name in params ? String(params[name]) : hole));
}

/** The voice saved in Settings: GenZ unless someone chose classic. */
export function readVoice(storage: Pick<Storage, 'getItem'> | null): Voice {
  try {
    return storage?.getItem(VOICE_KEY) === 'classic' ? 'classic' : 'genz';
  } catch {
    return 'genz';
  }
}

const SPLASH_STEPS: Record<string, CopyKey> = {
  [BOOT_STATUS.starting]: 'splash.starting',
  [BOOT_STATUS.connecting]: 'splash.connecting',
  [BOOT_STATUS.games]: 'splash.games',
  [BOOT_STATUS.covers]: 'splash.covers',
  [BOOT_STATUS.ready]: 'splash.ready',
};

/** utils/boot.ts reports its steps in plain words from BOOT_STATUS. This says them in the chosen voice. */
export function splashLine(voice: Voice, status: string): string {
  const prefix = `${BOOT_STATUS.covers} `;
  const count = status.startsWith(prefix) ? /^(\d+) of (\d+)$/.exec(status.slice(prefix.length)) : null;
  if (count) return wording(voice, 'splash.coversCount', { done: count[1], total: count[2] });
  return SPLASH_STEPS[status] ? wording(voice, SPLASH_STEPS[status]) : status;
}

function browserStorage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** The current voice. Components read it as $voice, or through $say. */
export const voice = writable<Voice>(readVoice(browserStorage()));

export function setVoice(next: Voice): void {
  voice.set(next);
  try {
    browserStorage()?.setItem(VOICE_KEY, next);
  } catch {}
}

/** For templates: {$say('hub.empty')} updates when the voice changes. */
export const say = derived(voice, ($voice) => (key: CopyKey, params?: Params) => wording($voice, key, params));

/** For code that builds a message once, like a pop-up. */
export function sayNow(key: CopyKey, params?: Params): string {
  return wording(get(voice), key, params);
}
