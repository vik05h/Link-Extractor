/**
 * The onboarding tour's steps and where its card goes. The wording lives in utils/voice.ts
 * under tour.<id>.title and tour.<id>.body. No DOM here, so placement can be tested.
 */

export type Side = 'top' | 'bottom' | 'left' | 'right';
export type TourStepId = 'welcome' | 'paste' | 'hub' | 'stage' | 'filter' | 'send' | 'done';

export interface TourStep {
  id: TourStepId;
  /** The view this step needs open, or null to leave the view as it is. */
  view: 'community' | 'stage' | null;
  /** Spotlit together. If none of them is on screen, `fallback` is tried, then the card sits in the middle. */
  targets: string[];
  fallback?: string[];
  /** Clicks inside the spotlight reach the app, so people can try it on the sample game. */
  interactive: boolean;
  /** Where the card goes if there is room. */
  side: Side;
}

export const TOUR_STEPS: readonly TourStep[] = [
  { id: 'welcome', view: null, targets: [], interactive: false, side: 'bottom' },
  { id: 'paste', view: null, targets: ['#tour-url-bar'], interactive: false, side: 'bottom' },
  { id: 'hub', view: 'community', targets: ['#tour-hub-card'], fallback: ['#tour-discovery-hub'], interactive: false, side: 'right' },
  // The tabs plus whichever view is showing, so the spotlight follows someone trying the tabs.
  { id: 'stage', view: 'stage', targets: ['#tour-stage-tabs', '#tour-stage-view > :first-child'], interactive: true, side: 'top' },
  { id: 'filter', view: 'stage', targets: ['#tour-filter'], interactive: true, side: 'bottom' },
  { id: 'send', view: 'stage', targets: ['#tour-quick-actions'], interactive: false, side: 'bottom' },
  { id: 'done', view: null, targets: ['#tour-nav-vault', '#tour-sidebar-footer'], interactive: false, side: 'right' },
];

export interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface Size {
  width: number;
  height: number;
}

/** Space between the card and what it points at. */
const GAP = 16;
/** The card keeps this far from the window's edges. */
const MARGIN = 16;

const OPPOSITE: Record<Side, Side> = { top: 'bottom', bottom: 'top', left: 'right', right: 'left' };

export function unionRect(rects: Rect[]): Rect | null {
  if (rects.length === 0) return null;
  const top = Math.min(...rects.map((r) => r.top));
  const left = Math.min(...rects.map((r) => r.left));
  const bottom = Math.max(...rects.map((r) => r.top + r.height));
  const right = Math.max(...rects.map((r) => r.left + r.width));
  return { top, left, width: right - left, height: bottom - top };
}

function roomOn(side: Side, target: Rect, viewport: Size): number {
  if (side === 'bottom') return viewport.height - MARGIN - (target.top + target.height + GAP);
  if (side === 'top') return target.top - GAP - MARGIN;
  if (side === 'right') return viewport.width - MARGIN - (target.left + target.width + GAP);
  return target.left - GAP - MARGIN;
}

function needOn(side: Side, card: Size): number {
  return side === 'top' || side === 'bottom' ? card.height : card.width;
}

function chooseSide(target: Rect, card: Size, viewport: Size, prefer: Side): Side {
  const order: Side[] = [prefer, OPPOSITE[prefer], ...(['bottom', 'top', 'right', 'left'] as Side[])];
  const fitting = order.find((side) => roomOn(side, target, viewport) >= needOn(side, card));
  if (fitting) return fitting;
  // Nothing fits: take the side that comes closest, and let the card overlap the target.
  return order.reduce((best, side) =>
    roomOn(side, target, viewport) / needOn(side, card) > roomOn(best, target, viewport) / needOn(best, card) ? side : best
  );
}

/** Where the tour card's top-left corner goes, always fully inside the window. */
export function placeCard(target: Rect | null, card: Size, viewport: Size, prefer: Side): { top: number; left: number } {
  let top: number;
  let left: number;
  if (!target) {
    top = (viewport.height - card.height) / 2;
    left = (viewport.width - card.width) / 2;
  } else {
    const side = chooseSide(target, card, viewport, prefer);
    const centerX = target.left + target.width / 2 - card.width / 2;
    const centerY = target.top + target.height / 2 - card.height / 2;
    if (side === 'bottom') [top, left] = [target.top + target.height + GAP, centerX];
    else if (side === 'top') [top, left] = [target.top - GAP - card.height, centerX];
    else if (side === 'right') [top, left] = [centerY, target.left + target.width + GAP];
    else [top, left] = [centerY, target.left - GAP - card.width];
  }
  const clamp = (value: number, max: number) => Math.round(Math.min(Math.max(value, MARGIN), Math.max(MARGIN, max)));
  return {
    top: clamp(top, viewport.height - MARGIN - card.height),
    left: clamp(left, viewport.width - MARGIN - card.width),
  };
}
