/**
 * The glass bubble that rides over a bar's selected item, like the tab bars on iOS 26.
 *
 * Click an item and the bubble springs across, stretching as it goes. Press anywhere on the
 * bar and drag, and it follows the pointer, swells into a magnifying lens, and lands on the
 * nearest item when you let go. A press that does not travel DRAG_START_PX is a plain click.
 * Arrow keys move it too. With reduced motion, it glides without the wobble, the stretch or the swell.
 *
 * Items are the bar's descendants marked data-bubble-item, in order. The bubble lives in `host`,
 * not inside the bar: the bar's own backdrop-filter would stop it seeing anything past the bar.
 * The motion rules are in bubbleMotion.ts, the material in liquidGlass.ts and styles/glass.css.
 */

import { Press, bubbleFrame, isSettled, nearestIndex, rubberBand, stepSpring, stretchAt, type Spring } from './bubbleMotion';
import { liquidGlass } from './liquidGlass';

export interface GlassBubbleOptions {
  axis: 'x' | 'y';
  /** Index of the selected item, or -1 to hide the bubble. */
  selected: number;
  /** Called for clicks, drops and arrow keys, even on the item already selected. */
  onSelect: (index: number) => void;
  /** Selector for the positioned ancestor the bubble is placed in. */
  host: string;
  /** Modifier class that sizes and stacks this bubble, like glass-bubble--nav. */
  variant: string;
  /** A fixed square bubble. Without it, the bubble takes each item's size plus `pad` along the bar. */
  size?: number;
  pad?: number;
}

/** How much the lens magnifies while dragging. */
const LENS_ZOOM = 1.22;
/** A click makes the bubble swell briefly as it sets off. */
const SWELL_PULSE_MS = 140;
/** The swell runs on the same spring as the slide, scaled up so its settle check is fine-grained. */
const SWELL_FULL = 100;

interface Slot {
  along: number;
  across: number;
  width: number;
  height: number;
}

export function glassBubble(bar: HTMLElement, initial: GlassBubbleOptions) {
  let options = initial;
  const host = bar.closest<HTMLElement>(options.host) ?? bar.parentElement ?? bar;
  const bubble = document.createElement('div');
  bubble.className = `glass-bubble ${options.variant}`;
  bubble.setAttribute('aria-hidden', 'true');
  host.appendChild(bubble);
  const glass = liquidGlass(bubble, { style: 'bubble' });

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let slide: Spring = { pos: 0, vel: 0 };
  let swell: Spring = { pos: 0, vel: 0 };
  let target = 0;
  let swellTarget = 0;
  let across = 0;
  let shownIndex = -1;
  let placed = false;
  let frame = 0;
  let lastTime = 0;
  let pulseTimer: ReturnType<typeof setTimeout> | null = null;
  let press: { id: number; tracker: Press } | null = null;
  let swallowClick = false;

  const vertical = () => options.axis === 'y';
  const items = () => [...bar.querySelectorAll<HTMLElement>('[data-bubble-item]')];
  const pointerAlong = (e: PointerEvent | MouseEvent) => (vertical() ? e.clientY : e.clientX);
  const centerOf = (el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    return vertical() ? r.top + r.height / 2 : r.left + r.width / 2;
  };
  /** Where the host's padding box starts on screen, which is where the bubble's 0,0 is. */
  const origin = () => {
    const r = host.getBoundingClientRect();
    return { x: r.left + host.clientLeft, y: r.top + host.clientTop };
  };

  function slotOf(index: number): Slot | null {
    const item = items()[index];
    if (!item) return null;
    const r = item.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return null;
    const pad = options.pad ?? 0;
    const width = options.size ?? (vertical() ? r.width : r.width + pad);
    const height = options.size ?? (vertical() ? r.height + pad : r.height);
    const o = origin();
    const left = r.left - o.x + (r.width - width) / 2;
    const top = r.top - o.y + (r.height - height) / 2;
    return vertical() ? { along: top, across: left, width, height } : { along: left, across: top, width, height };
  }

  function render(): void {
    const f = bubbleFrame({
      axis: options.axis,
      pos: slide.pos,
      cross: across,
      stretch: reduceMotion ? 0 : stretchAt(slide.vel),
      swell: swell.pos / SWELL_FULL,
    });
    bubble.style.transform = `translate3d(${f.x}px, ${f.y}px, 0) scale(${f.scaleX.toFixed(4)}, ${f.scaleY.toFixed(4)})`;
    bubble.style.setProperty('--bubble-clear', f.clear.toFixed(3));
  }

  function tick(now: number): void {
    const dt = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;
    slide = stepSpring(slide, target, dt, reduceMotion);
    swell = stepSpring(swell, swellTarget, dt);
    if (isSettled(slide, target) && isSettled(swell, swellTarget)) {
      slide = { pos: target, vel: 0 };
      swell = { pos: swellTarget, vel: 0 };
      frame = 0;
      render();
      return;
    }
    render();
    frame = requestAnimationFrame(tick);
  }

  function animate(): void {
    if (frame) return;
    lastTime = performance.now();
    frame = requestAnimationFrame(tick);
  }

  function setSize(slot: Slot): void {
    bubble.style.width = `${slot.width}px`;
    bubble.style.height = `${slot.height}px`;
  }

  function moveTo(index: number, instant: boolean): void {
    shownIndex = index;
    const slot = slotOf(index);
    if (!slot) {
      bubble.style.opacity = '0';
      return;
    }
    bubble.style.opacity = '';
    setSize(slot);
    target = slot.along;
    across = slot.across;
    if (instant || !placed) {
      placed = true;
      slide = { pos: target, vel: 0 };
      render();
      return;
    }
    if (!reduceMotion) {
      swellTarget = SWELL_FULL;
      if (pulseTimer) clearTimeout(pulseTimer);
      pulseTimer = setTimeout(() => {
        if (!press) swellTarget = 0;
        animate();
      }, SWELL_PULSE_MS);
    }
    animate();
  }

  function hold(on: boolean): void {
    swellTarget = on && !reduceMotion ? SWELL_FULL : 0;
    animate();
  }

  function choose(index: number): void {
    moveTo(index, false);
    options.onSelect(index);
  }

  /** While dragging, the bubble's middle sits under the pointer, taking the nearest item's size. */
  function follow(pointer: number): void {
    const list = items();
    if (list.length === 0) return;
    const centers = list.map(centerOf);
    const nearest = nearestIndex(centers, pointer);
    list.forEach((el, i) => el.classList.toggle('is-peek', i === nearest));
    const slot = slotOf(nearest);
    if (!slot) return;
    setSize(slot);
    const o = origin();
    const half = (vertical() ? slot.height : slot.width) / 2;
    target = rubberBand(pointer, centers[0], centers[centers.length - 1]) - (vertical() ? o.y : o.x) - half;
    animate();
  }

  function endDrag(): void {
    bar.classList.remove('is-dragging');
    items().forEach((el) => el.classList.remove('is-peek'));
    glass.update({ style: 'bubble' });
  }

  function onPointerDown(e: PointerEvent): void {
    if (e.button !== 0 || !e.isPrimary) return;
    press = { id: e.pointerId, tracker: new Press(pointerAlong(e)) };
    const item = (e.target as Element).closest<HTMLElement>('[data-bubble-item]');
    if (item && items().indexOf(item) === options.selected) hold(true);
  }

  function onPointerMove(e: PointerEvent): void {
    if (!press || e.pointerId !== press.id) return;
    const state = press.tracker.move(pointerAlong(e));
    if (state === 'pending') return;
    if (state === 'started') {
      bar.setPointerCapture(e.pointerId);
      bar.classList.add('is-dragging');
      hold(true);
      glass.update({ style: 'bubble', magnify: LENS_ZOOM });
    }
    follow(pointerAlong(e));
  }

  function finish(e: PointerEvent, cancelled: boolean): void {
    if (!press || e.pointerId !== press.id) return;
    const dragged = press.tracker.isDrag;
    press = null;
    hold(false);
    if (!dragged) return;
    endDrag();
    // The click that follows a drag belongs to the drag.
    swallowClick = true;
    setTimeout(() => {
      swallowClick = false;
    }, 0);
    choose(cancelled ? options.selected : nearestIndex(items().map(centerOf), pointerAlong(e)));
  }

  const onPointerUp = (e: PointerEvent) => finish(e, false);
  const onPointerCancel = (e: PointerEvent) => finish(e, true);

  function onClick(e: MouseEvent): void {
    if (swallowClick) {
      swallowClick = false;
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    const item = (e.target as Element).closest<HTMLElement>('[data-bubble-item]');
    const index = item ? items().indexOf(item) : -1;
    if (index !== -1) choose(index);
  }

  function onKeyDown(e: KeyboardEvent): void {
    const back = vertical() ? 'ArrowUp' : 'ArrowLeft';
    const ahead = vertical() ? 'ArrowDown' : 'ArrowRight';
    if (e.key !== back && e.key !== ahead) return;
    const list = items();
    const from = list.indexOf(e.target as HTMLElement);
    if (from === -1) return;
    // Handled here, so a page-level shortcut on the same key does not also fire.
    e.preventDefault();
    e.stopPropagation();
    const index = (from + (e.key === ahead ? 1 : -1) + list.length) % list.length;
    list[index].focus();
    choose(index);
  }

  // Sizes change when fonts load, labels change, or the window is resized.
  const observer = new ResizeObserver(() => {
    if (!press?.tracker.isDrag) moveTo(options.selected, true);
  });
  observer.observe(bar);
  observer.observe(host);
  items().forEach((el) => observer.observe(el));

  bar.addEventListener('pointerdown', onPointerDown);
  bar.addEventListener('pointermove', onPointerMove);
  // A press can end anywhere, even off the bar, and it must always let the bubble go.
  window.addEventListener('pointerup', onPointerUp);
  window.addEventListener('pointercancel', onPointerCancel);
  bar.addEventListener('click', onClick);
  bar.addEventListener('keydown', onKeyDown);

  return {
    update(next: GlassBubbleOptions) {
      options = next;
      if (options.selected !== shownIndex && !press?.tracker.isDrag) moveTo(options.selected, false);
    },
    destroy() {
      if (frame) cancelAnimationFrame(frame);
      if (pulseTimer) clearTimeout(pulseTimer);
      observer.disconnect();
      bar.removeEventListener('pointerdown', onPointerDown);
      bar.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('pointercancel', onPointerCancel);
      bar.removeEventListener('click', onClick);
      bar.removeEventListener('keydown', onKeyDown);
      glass.destroy();
      bubble.remove();
    },
  };
}
