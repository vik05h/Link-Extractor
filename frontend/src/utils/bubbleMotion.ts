/**
 * How the glass bubble moves: a springy slide, a stretch that grows with speed, a swell
 * while it is held, and the rule that tells a click from a drag. No DOM, so it can be tested;
 * utils/glassBubble.ts applies it to the bars.
 */

export interface Spring {
  pos: number;
  vel: number;
}

/** Stiff enough to feel quick, damped just under critical so it settles with a small wobble. */
const STIFFNESS = 430;
const DAMPING = 27;
/** Critical damping: the quickest glide that never passes its target. Used with reduced motion. */
const CALM_DAMPING = 2 * Math.sqrt(STIFFNESS);
/** Long frames are split into short steps, so a slow PC cannot shake the spring loose. */
const MAX_STEP_S = 1 / 240;

const SETTLE_DISTANCE_PX = 0.05;
const SETTLE_SPEED_PX_S = 0.5;

/** The speed, in pixels per second, at which the bubble stretches the most. */
const FULL_STRETCH_SPEED = 2600;
export const MAX_STRETCH = 0.36;
/** Stretching along the path also thins the bubble across it, by this share of the stretch. */
const THINNING = 0.42;
/** How much bigger the bubble grows while it is held down. */
const SWELL = 0.13;

/** Past the first or last item, the bubble moves this share of the pointer's distance. */
const RUBBER_GIVE = 0.3;

/** A press has to travel this far along the bar before it counts as a drag. */
export const DRAG_START_PX = 6;

/** Moves the spring dt seconds toward target. `calm` glides there without the wobble. */
export function stepSpring(spring: Spring, target: number, dt: number, calm = false): Spring {
  let { pos, vel } = spring;
  const damping = calm ? CALM_DAMPING : DAMPING;
  const steps = Math.max(1, Math.ceil(dt / MAX_STEP_S));
  const h = dt / steps;
  for (let i = 0; i < steps; i++) {
    vel += (-STIFFNESS * (pos - target) - damping * vel) * h;
    pos += vel * h;
  }
  return { pos, vel };
}

export function isSettled(spring: Spring, target: number): boolean {
  return Math.abs(spring.pos - target) < SETTLE_DISTANCE_PX && Math.abs(spring.vel) < SETTLE_SPEED_PX_S;
}

export function stretchAt(velocity: number): number {
  return Math.min(Math.abs(velocity) / FULL_STRETCH_SPEED, 1) * MAX_STRETCH;
}

export function rubberBand(value: number, min: number, max: number): number {
  if (value < min) return min - (min - value) * RUBBER_GIVE;
  if (value > max) return max + (value - max) * RUBBER_GIVE;
  return value;
}

export function nearestIndex(centers: number[], point: number): number {
  let best = 0;
  for (let i = 1; i < centers.length; i++) {
    if (Math.abs(centers[i] - point) < Math.abs(centers[best] - point)) best = i;
  }
  return best;
}

/** One press on a bar. It stays a click unless the pointer travels DRAG_START_PX along the bar. */
export class Press {
  private readonly start: number;
  private dragging = false;

  constructor(start: number) {
    this.start = start;
  }

  /** 'started' is reported once, on the move that turns the press into a drag. */
  move(at: number): 'pending' | 'started' | 'dragging' {
    if (this.dragging) return 'dragging';
    if (Math.abs(at - this.start) < DRAG_START_PX) return 'pending';
    this.dragging = true;
    return 'started';
  }

  get isDrag(): boolean {
    return this.dragging;
  }
}

export interface BubbleFrameInput {
  axis: 'x' | 'y';
  /** Position along the bar. */
  pos: number;
  /** Position across the bar, which does not animate. */
  cross: number;
  /** From stretchAt(). */
  stretch: number;
  /** 0 at rest, 1 while held. */
  swell: number;
}

export interface BubbleFrame {
  x: number;
  y: number;
  scaleX: number;
  scaleY: number;
  /** 0 is the normal tinted bubble, 1 is clear glass. Moving and holding both clear it. */
  clear: number;
}

export function bubbleFrame({ axis, pos, cross, stretch, swell }: BubbleFrameInput): BubbleFrame {
  const grow = swell * SWELL;
  const along = 1 + stretch + grow;
  const across = 1 - stretch * THINNING + grow;
  const vertical = axis === 'y';
  return {
    x: vertical ? cross : pos,
    y: vertical ? pos : cross,
    scaleX: vertical ? across : along,
    scaleY: vertical ? along : across,
    clear: Math.min(1, stretch * 2.4 + swell * 0.7),
  };
}
