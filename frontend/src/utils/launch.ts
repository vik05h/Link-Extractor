/**
 * What opens by itself after the splash. The full tour plays once, on a brand-new install,
 * which skips What's New because there is nothing earlier to compare with. After an update,
 * What's New opens once instead, and the tour stays on its ? button.
 */

export type LaunchScreen = 'tour' | 'whats-new' | 'none';

export interface LaunchState {
  /** The tour has already played here (le_tour_completed, set when it opens by itself, finishes or is skipped). */
  tourShown: boolean;
  /** What's New or the tour has already opened for this version. */
  seenThisVersion: boolean;
  /** An earlier version of the app has run here, so this launch is an update. */
  seenEarlierVersion: boolean;
}

export function chooseLaunchScreen({ tourShown, seenThisVersion, seenEarlierVersion }: LaunchState): LaunchScreen {
  if (seenThisVersion) return 'none';
  return tourShown || seenEarlierVersion ? 'whats-new' : 'tour';
}
