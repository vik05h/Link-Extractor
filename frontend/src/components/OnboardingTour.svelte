<script lang="ts">
  /**
   * The onboarding tour: seven short steps that walk through the real app. It opens the views
   * it talks about (MainApp shows a sample game on the Stage meanwhile), spotlights the part
   * it describes, and on the Stage and filter steps lets clicks through to try them.
   * Steps and card placement live in utils/tourPlan.ts, the wording in utils/voice.ts.
   */
  import { onDestroy, onMount, tick } from 'svelte';
  import { liquidGlass } from '../utils/liquidGlass';
  import { FIRST_RUN_KEY } from '../version';
  import { TOUR_STEPS, placeCard, unionRect, type Rect, type TourStep } from '../utils/tourPlan';
  import { say, type CopyKey } from '../utils/voice';
  import { playClickSound, playSuccessChime } from '../utils/audio';
  import Icon from './icons/Icon.svelte';
  import BrandLogo from './BrandLogo.svelte';

  export let isOpen: boolean = false;
  export let onClose: () => void = () => {};
  /** Asks MainApp to open the view a step talks about. */
  export let onView: (view: 'community' | 'stage') => void = () => {};

  /** Room between the spotlight's edge and what it frames. */
  const SPOT_PAD = 10;
  /** Layout can shift under the tour, like Hub cards arriving, so it is measured again this often. */
  const REMEASURE_MS = 500;

  let index = 0;
  let spot: Rect | null = null;
  let cardTop = 0;
  let cardLeft = 0;
  let card: HTMLElement | undefined;
  let primaryButton: HTMLButtonElement | undefined;
  let windowWidth = 1180;
  let windowHeight = 840;
  let remeasureTimer: ReturnType<typeof setInterval> | null = null;
  let layoutToken = 0;

  $: step = TOUR_STEPS[index];
  $: isLast = index === TOUR_STEPS.length - 1;

  function wordingFor(current: TourStep, part: 'title' | 'body'): CopyKey {
    return `tour.${current.id}.${part}` as CopyKey;
  }

  const nextFrame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

  function visible(selectors: string[] = []): HTMLElement[] {
    return selectors
      .map((selector) => document.querySelector<HTMLElement>(selector))
      .filter((el): el is HTMLElement => !!el && el.getClientRects().length > 0);
  }

  function padded(rect: Rect): Rect {
    const top = Math.max(4, rect.top - SPOT_PAD);
    const left = Math.max(4, rect.left - SPOT_PAD);
    const bottom = Math.min(windowHeight - 4, rect.top + rect.height + SPOT_PAD);
    const right = Math.min(windowWidth - 4, rect.left + rect.width + SPOT_PAD);
    return { top, left, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
  }

  const same = (a: Rect | null, b: Rect | null) =>
    a === b || (!!a && !!b && Math.abs(a.top - b.top) < 1 && Math.abs(a.left - b.left) < 1 && Math.abs(a.width - b.width) < 1 && Math.abs(a.height - b.height) < 1);

  /** Spotlights this step's targets and places the card beside them. Scrolls them into view only when asked. */
  async function layout(scrollIntoView: boolean) {
    const token = ++layoutToken;
    await tick();
    await nextFrame();
    await nextFrame();
    if (!isOpen || token !== layoutToken) return;

    let targets = visible(step.targets);
    if (targets.length === 0) targets = visible(step.fallback);
    if (scrollIntoView && targets[0]) targets[0].scrollIntoView({ block: 'nearest', inline: 'nearest' });

    const union = unionRect(targets.map((el) => {
      const r = el.getBoundingClientRect();
      return { top: r.top, left: r.left, width: r.width, height: r.height };
    }));
    const nextSpot = union ? padded(union) : null;
    if (!same(nextSpot, spot)) spot = nextSpot;

    const size = { width: card?.offsetWidth || 380, height: card?.offsetHeight || 230 };
    const place = placeCard(spot, size, { width: windowWidth, height: windowHeight }, step.side);
    if (place.top !== cardTop) cardTop = place.top;
    if (place.left !== cardLeft) cardLeft = place.left;
  }

  async function goTo(next: number) {
    if (next < 0 || next >= TOUR_STEPS.length) return;
    index = next;
    const view = TOUR_STEPS[next].view;
    if (view) onView(view);
    await layout(true);
    primaryButton?.focus({ preventScroll: true });
  }

  function handleNext() {
    playClickSound();
    if (isLast) finish(true);
    else goTo(index + 1);
  }

  function handleBack() {
    playClickSound();
    goTo(index - 1);
  }

  function finish(completed: boolean) {
    if (completed) playSuccessChime();
    else playClickSound();
    try {
      localStorage.setItem('le_tour_completed', 'true');
      localStorage.setItem(FIRST_RUN_KEY, 'true');
    } catch {}
    onClose();
  }

  /** Keeps Tab inside the card, so the keyboard cannot wander into the app behind the dim. */
  function trapFocus(e: KeyboardEvent) {
    if (!card) return;
    const focusable = [...card.querySelectorAll<HTMLElement>('button:not([disabled])')];
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const inside = card.contains(document.activeElement);
    if (e.shiftKey && (document.activeElement === first || !inside)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (document.activeElement === last || !inside)) {
      e.preventDefault();
      first.focus();
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!isOpen) return;
    const target = e.target as HTMLElement | null;
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      finish(false);
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      handleNext();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      if (index > 0) handleBack();
    } else if (e.key === 'Enter' && !(target instanceof HTMLButtonElement)) {
      e.preventDefault();
      handleNext();
    } else if (e.key === 'Tab') {
      trapFocus(e);
    }
  }

  let wasOpen = false;
  $: if (isOpen && !wasOpen) {
    wasOpen = true;
    spot = null;
    goTo(0);
    remeasureTimer = setInterval(() => layout(false), REMEASURE_MS);
  } else if (!isOpen && wasOpen) {
    wasOpen = false;
    if (remeasureTimer) clearInterval(remeasureTimer);
    remeasureTimer = null;
  }

  function handleResize() {
    if (isOpen) layout(false);
  }

  onMount(() => {
    window.addEventListener('resize', handleResize);
  });

  onDestroy(() => {
    if (typeof window === 'undefined') return;
    window.removeEventListener('resize', handleResize);
    if (remeasureTimer) clearInterval(remeasureTimer);
  });

  $: holeStyle = spot
    ? `top: ${spot.top}px; left: ${spot.left}px; width: ${spot.width}px; height: ${spot.height}px;`
    : `top: ${windowHeight / 2}px; left: ${windowWidth / 2}px; width: 0px; height: 0px;`;
</script>

<svelte:window on:keydown={handleKeydown} bind:innerWidth={windowWidth} bind:innerHeight={windowHeight} />

{#if isOpen}
  <!-- Catches clicks behind the tour. On hands-on steps it leaves a hole over the spotlight. -->
  {#if spot && step.interactive}
    <div class="tour-block" style="top: 0; left: 0; right: 0; height: {spot.top}px;" aria-hidden="true"></div>
    <div class="tour-block" style="top: {spot.top + spot.height}px; left: 0; right: 0; bottom: 0;" aria-hidden="true"></div>
    <div class="tour-block" style="top: {spot.top}px; left: 0; width: {spot.left}px; height: {spot.height}px;" aria-hidden="true"></div>
    <div class="tour-block" style="top: {spot.top}px; left: {spot.left + spot.width}px; right: 0; height: {spot.height}px;" aria-hidden="true"></div>
  {:else}
    <div class="tour-block" style="inset: 0;" aria-hidden="true"></div>
  {/if}

  <!-- The dim around the spotlight is one huge shadow, so the hole can glide between steps. -->
  <div class="tour-spot" class:is-empty={!spot} class:is-hands-on={step.interactive} style={holeStyle} aria-hidden="true"></div>

  <div
    class="tour-card glass-panel glass-thick"
    class:is-welcome={step.id === 'welcome'}
    bind:this={card}
    use:liquidGlass={{ style: 'thick' }}
    style="top: {cardTop}px; left: {cardLeft}px;"
    role="dialog"
    aria-modal="true"
    aria-labelledby="tour-title"
    aria-describedby="tour-body"
  >
    {#if step.id === 'welcome'}
      <div class="tour-logo"><BrandLogo /></div>
    {/if}

    <div class="tour-card-header">
      <span class="tour-step-badge">
        <Icon name="sparkles" size={12} color="var(--accent-primary)" />
        <span>{$say('tour.step', { n: index + 1, total: TOUR_STEPS.length })}</span>
      </span>
      <button type="button" class="tour-close" title="{$say('tour.skip')} (Esc)" aria-label={$say('tour.skip')} on:click={() => finish(false)}>
        <Icon name="close" size={14} />
      </button>
    </div>

    {#key index}
      <div class="tour-copy">
        <h3 id="tour-title" class="tour-title">{$say(wordingFor(step, 'title'))}</h3>
        <p id="tour-body" class="tour-body">{$say(wordingFor(step, 'body'))}</p>
        {#if step.interactive}
          <p class="tour-try">
            <Icon name="zap" size={12} color="var(--accent-primary)" />
            <span>{$say('tour.tryIt')}</span>
          </p>
        {/if}
      </div>
    {/key}

    <div class="tour-card-footer">
      <div class="tour-dots">
        {#each TOUR_STEPS as s, i (s.id)}
          <button
            type="button"
            class="tour-dot"
            class:is-current={i === index}
            class:is-done={i < index}
            aria-label="Step {i + 1}"
            aria-current={i === index ? 'step' : undefined}
            on:click={() => { if (i !== index) { playClickSound(); goTo(i); } }}
          ></button>
        {/each}
      </div>

      <div class="tour-buttons">
        {#if index === 0}
          <button type="button" class="btn-secondary btn-sm" on:click={() => finish(false)}>
            <span>{$say('tour.skip')}</span>
          </button>
        {:else}
          <button type="button" class="btn-secondary btn-sm" on:click={handleBack}>
            <Icon name="arrow-left" size={12} />
            <span>{$say('tour.back')}</span>
          </button>
        {/if}
        <button type="button" class="btn-primary btn-sm tour-next" bind:this={primaryButton} on:click={handleNext}>
          {#if isLast}
            <Icon name="check" size={13} color="#ffffff" strokeWidth={2.5} />
            <span>{$say('tour.finish')}</span>
          {:else}
            <span>{$say('tour.next')}</span>
            <Icon name="arrow-right" size={12} color="#ffffff" />
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .tour-block {
    position: fixed;
    z-index: 10000;
    background: transparent;
    cursor: default;
  }

  /* A lighter dim than before, so the app stays visible around the part being explained. */
  .tour-spot {
    position: fixed;
    z-index: 10001;
    pointer-events: none;
    border-radius: 18px;
    box-shadow:
      0 0 0 2px color-mix(in srgb, var(--accent-primary) 85%, #ffffff),
      0 0 26px 4px var(--accent-glow),
      0 0 0 200vmax rgba(3, 6, 12, 0.62);
    transition:
      top 0.45s var(--glass-settle),
      left 0.45s var(--glass-settle),
      width 0.45s var(--glass-settle),
      height 0.45s var(--glass-settle),
      box-shadow 0.3s ease;
    animation: tourSpotIn 0.3s ease-out both;
  }

  .tour-spot.is-empty {
    box-shadow: 0 0 0 200vmax rgba(3, 6, 12, 0.66);
  }

  .tour-spot.is-hands-on {
    animation: tourSpotIn 0.3s ease-out both, tourHandsOn 2.2s ease-in-out 0.3s infinite;
  }

  @keyframes tourSpotIn {
    from {
      opacity: 0;
    }
  }

  /* A slow breathing glow says "you can click in here". */
  @keyframes tourHandsOn {
    50% {
      box-shadow:
        0 0 0 2px color-mix(in srgb, var(--accent-secondary) 85%, #ffffff),
        0 0 38px 8px var(--accent-glow),
        0 0 0 200vmax rgba(3, 6, 12, 0.62);
    }
  }

  .tour-card {
    position: fixed;
    z-index: 10010;
    width: 380px;
    padding: 18px 20px 16px;
    border-radius: 20px;
    transition:
      top 0.45s var(--glass-settle),
      left 0.45s var(--glass-settle);
    animation: tourCardIn 0.36s var(--glass-spring) both;
  }

  .tour-card.is-welcome {
    width: 400px;
  }

  @keyframes tourCardIn {
    from {
      opacity: 0;
      transform: scale(0.94) translateY(8px);
    }
  }

  .tour-logo {
    width: 52px;
    height: 52px;
    margin: 2px 0 12px;
    filter: drop-shadow(0 0 14px var(--accent-glow));
  }

  .tour-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .tour-step-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--accent-primary) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--accent-primary) 34%, transparent);
    color: var(--accent-primary);
    font-family: var(--font-display);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .tour-close {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 5px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    transition: color 0.15s ease, background 0.15s ease;
  }

  .tour-close:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.08);
  }

  .tour-copy {
    animation: tourCopyIn 0.32s var(--glass-settle) both;
  }

  @keyframes tourCopyIn {
    from {
      opacity: 0;
      transform: translateY(5px);
    }
  }

  .tour-title {
    margin: 0 0 6px;
    font-family: var(--font-display);
    font-size: 1.2rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.01em;
  }

  .tour-body {
    margin: 0 0 12px;
    font-size: 0.88rem;
    line-height: 1.55;
    color: var(--text-secondary);
  }

  .tour-try {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: -2px 0 12px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--accent-primary);
  }

  .tour-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .tour-dots {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tour-dot {
    width: 7px;
    height: 7px;
    padding: 0;
    border: none;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.2);
    cursor: pointer;
    transition: width 0.3s var(--glass-spring), background 0.2s ease;
  }

  .tour-dot:hover {
    background: rgba(255, 255, 255, 0.45);
  }

  .tour-dot.is-done {
    background: color-mix(in srgb, var(--accent-primary) 65%, transparent);
  }

  .tour-dot.is-current {
    width: 20px;
    background: var(--accent-primary);
    box-shadow: 0 0 8px var(--accent-primary);
    cursor: default;
  }

  .tour-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .tour-buttons button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .tour-next {
    min-width: 88px;
    justify-content: center;
  }

  @media (prefers-reduced-motion: reduce) {
    .tour-spot,
    .tour-card {
      transition: none;
    }

    .tour-spot,
    .tour-spot.is-hands-on,
    .tour-card,
    .tour-copy {
      animation: none;
    }
  }
</style>
