<script lang="ts">
  import { onMount } from 'svelte';
  import { APP_VERSION } from '../version';

  export let progress: number = 0;
  export let status: string = 'Starting up';
  export let exiting: boolean = false;
  export let onFinished: () => void = () => {};

  const MORPH_MS = 720;
  const CONTENT_FADE_MS = 170;
  const SCRIM_FADE_MS = 640;
  const LANDING_FADE_MS = 170;
  const GLASS_MORPH = 'cubic-bezier(0.3, 1.14, 0.42, 1)';
  const SETTLE = 'cubic-bezier(0.22, 1, 0.36, 1)';

  let card: HTMLElement;
  let content: HTMLElement;
  let scrim: HTMLElement;
  let logo: HTMLElement;
  let mounted = false;
  let started = false;

  onMount(() => {
    mounted = true;
  });

  $: if (mounted && exiting && !started) {
    started = true;
    // Whatever happens to the animation, the app must not stay behind the splash.
    playExit()
      .catch((error) => console.error('[Splash] Exit animation failed:', error))
      .finally(onFinished);
  }

  function fadeOut(node: HTMLElement, duration: number, delay = 0) {
    return node.animate([{ opacity: 1 }, { opacity: 0 }], { duration, delay, easing: 'ease-out', fill: 'forwards' }).finished;
  }

  /**
   * The little card turns into the app: it stretches into the URL bar while the logo
   * flies to the sidebar and the screen behind it clears, so nothing simply cuts away.
   */
  async function playExit() {
    const bar = document.getElementById('tour-url-bar');
    const barLogo = document.querySelector('.sidebar-logo-btn .logo-mark');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reduceMotion || !bar || !barLogo) {
      await Promise.all([fadeOut(scrim, 180), fadeOut(card, 180), fadeOut(logo, 180)]);
      return;
    }

    const from = card.getBoundingClientRect();
    const to = bar.getBoundingClientRect();
    const logoFrom = logo.getBoundingClientRect();
    const logoTo = barLogo.getBoundingClientRect();
    const toRadius = getComputedStyle(bar).borderTopLeftRadius;

    fadeOut(content, CONTENT_FADE_MS);
    fadeOut(scrim, SCRIM_FADE_MS, 60);

    const morph = card.animate(
      [
        { left: `${from.left}px`, top: `${from.top}px`, width: `${from.width}px`, height: `${from.height}px`, borderRadius: getComputedStyle(card).borderTopLeftRadius },
        { left: `${to.left}px`, top: `${to.top}px`, width: `${to.width}px`, height: `${to.height}px`, borderRadius: toRadius },
      ],
      { duration: MORPH_MS, easing: GLASS_MORPH, fill: 'forwards' }
    );

    const dx = logoTo.left + logoTo.width / 2 - (logoFrom.left + logoFrom.width / 2);
    const dy = logoTo.top + logoTo.height / 2 - (logoFrom.top + logoFrom.height / 2);
    const flight = logo.animate(
      [
        { transform: 'translate3d(0, 0, 0) scale(1)' },
        { transform: `translate3d(${dx}px, ${dy}px, 0) scale(${logoTo.width / logoFrom.width})` },
      ],
      { duration: MORPH_MS, easing: SETTLE, fill: 'forwards' }
    );

    await Promise.all([morph.finished, flight.finished]);
    await Promise.all([fadeOut(card, LANDING_FADE_MS), fadeOut(logo, LANDING_FADE_MS)]);
  }

  $: percent = Math.round(Math.min(1, Math.max(0, progress)) * 100);
</script>

<div class="splash-layer" role="status" aria-live="polite" aria-label="Loading Link Extractor">
  <div class="splash-scrim" bind:this={scrim}>
    <span class="splash-orb orb-one"></span>
    <span class="splash-orb orb-two"></span>
  </div>

  <div class="splash-card" bind:this={card}>
    <span class="splash-shine" aria-hidden="true"></span>
    <div class="splash-content" bind:this={content}>
      <div class="splash-logo-slot" aria-hidden="true"></div>
      <div class="splash-title">LINK EXTRACTOR</div>
      <div class="splash-status">{status}</div>
      <div class="splash-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={percent}>
        <div class="splash-fill" style="width: {percent}%"></div>
      </div>
      <div class="splash-foot">{APP_VERSION} by Vikash</div>
    </div>
  </div>

  <div class="splash-logo" bind:this={logo}>
    <span class="splash-ring" class:hidden={exiting} aria-hidden="true"></span>
    <img src="/favicon.svg" alt="" class="splash-logo-img" />
  </div>
</div>

<style>
  .splash-layer {
    --card-width: 288px;
    --card-height: 204px;
    --logo-size: 56px;
    position: fixed;
    inset: 0;
    z-index: 100000;
    pointer-events: none;
  }

  .splash-scrim {
    position: absolute;
    inset: 0;
    overflow: hidden;
    background: var(--bg-base);
  }

  .splash-orb {
    position: absolute;
    width: 460px;
    height: 460px;
    border-radius: 50%;
    filter: blur(70px);
    opacity: 0.5;
  }

  .orb-one {
    top: calc(50% - 330px);
    left: calc(50% - 380px);
    background: var(--accent-primary);
    animation: splashDriftOne 7s ease-in-out infinite alternate;
  }

  .orb-two {
    top: calc(50% - 130px);
    left: calc(50% - 80px);
    background: var(--accent-secondary);
    animation: splashDriftTwo 8s ease-in-out infinite alternate;
  }

  @keyframes splashDriftOne {
    to {
      transform: translate3d(90px, 50px, 0) scale(1.12);
    }
  }

  @keyframes splashDriftTwo {
    to {
      transform: translate3d(-90px, -40px, 0) scale(0.92);
    }
  }

  .splash-card {
    position: fixed;
    left: calc(50% - var(--card-width) / 2);
    top: calc(50% - var(--card-height) / 2);
    width: var(--card-width);
    height: var(--card-height);
    overflow: hidden;
    border-radius: 24px;
    background: var(--glass-sheen), var(--glass-tint-clear);
    backdrop-filter: blur(16px) saturate(190%) brightness(0.92);
    box-shadow:
      var(--glass-shadow-lg),
      inset 0 0 0 1px rgba(255, 255, 255, 0.12),
      inset 0 1px 1px rgba(255, 255, 255, 0.5);
  }

  /* A band of light passing over the glass while it works. */
  .splash-shine {
    position: absolute;
    top: -40%;
    bottom: -40%;
    left: -60%;
    width: 42%;
    transform: rotate(18deg);
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.16), transparent);
    animation: splashShine 2.6s ease-in-out infinite;
  }

  @keyframes splashShine {
    0%,
    30% {
      left: -60%;
    }
    100% {
      left: 130%;
    }
  }

  .splash-content {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: var(--card-height);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px 26px 16px;
  }

  .splash-logo-slot {
    width: var(--logo-size);
    height: var(--logo-size);
    flex-shrink: 0;
    margin-bottom: 12px;
  }

  .splash-title {
    font-family: var(--font-brand);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.2em;
    color: var(--text-primary);
  }

  .splash-status {
    margin-top: 5px;
    font-family: var(--font-display);
    font-size: 11.5px;
    color: rgba(255, 255, 255, 0.72);
  }

  .splash-track {
    width: 100%;
    height: 4px;
    margin-top: 12px;
    overflow: hidden;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.12);
    box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.35);
  }

  .splash-fill {
    height: 100%;
    border-radius: 4px;
    background: var(--accent-gradient);
    box-shadow: 0 0 10px var(--accent-primary);
    transition: width 0.45s var(--glass-settle);
  }

  .splash-foot {
    margin-top: auto;
    font-family: var(--font-mono);
    font-size: 9.5px;
    letter-spacing: 0.04em;
    color: rgba(255, 255, 255, 0.45);
  }

  /* The logo sits outside the card so it can keep flying after the card has gone. */
  .splash-logo {
    position: fixed;
    left: calc(50% - var(--logo-size) / 2);
    top: calc(50% - var(--card-height) / 2 + 20px);
    width: var(--logo-size);
    height: var(--logo-size);
    transform-origin: center;
  }

  .splash-logo-img {
    position: relative;
    display: block;
    width: 100%;
    height: 100%;
    border-radius: 17px;
    object-fit: cover;
    box-shadow:
      inset 0 1px 1px rgba(255, 255, 255, 0.4),
      0 0 26px var(--accent-glow);
    animation: splashBreathe 1.8s ease-in-out infinite alternate;
  }

  @keyframes splashBreathe {
    to {
      transform: scale(1.045);
    }
  }

  .splash-ring {
    position: absolute;
    padding: 2px;
    background: conic-gradient(from 0deg, transparent 0 58%, var(--accent-secondary) 82%, var(--accent-primary) 100%);
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    animation: splashSpin 1.25s linear infinite;
    transition: opacity 0.15s ease;
    inset: -7px;
    border-radius: 50%;
  }

  .splash-ring.hidden {
    opacity: 0;
  }

  @keyframes splashSpin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
