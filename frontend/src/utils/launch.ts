/**
 * What opens by itself after the splash. A new install gets the tour and skips What's New,
 * which only means something to people who used an earlier version. After an update,
 * What's New opens once, and the tour stays on its button instead of playing again.
 */

export type LaunchScreen = 'tour' | 'whats-new' | 'none';

export interface LaunchState {
  /** Set when the tour is finished or skipped. */
  tourCompleted: boolean;
  /** Set once What's New, or the tour, has been shown for this version. */
  seenThisVersion: boolean;
}

export function chooseLaunchScreen({ tourCompleted, seenThisVersion }: LaunchState): LaunchScreen {
  if (!tourCompleted) return 'tour';
  return seenThisVersion ? 'none' : 'whats-new';
}
