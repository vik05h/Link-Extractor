<script lang="ts">
  import { onMount, tick } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, playSuccessChime } from '../utils/audio';

  export let isOpen: boolean = false;
  export let onClose: () => void = () => {};

  interface TourStep {
    targetId: string;
    title: string;
    subtitle: string;
    description: string;
    position: 'bottom' | 'top' | 'right' | 'left';
    badge: string;
  }

  const STEPS: TourStep[] = [
    {
      targetId: 'tour-url-bar',
      badge: 'Step 1 of 5',
      title: 'Direct Link Resolver Cockpit',
      subtitle: 'Paste any FitGirl game page URL, Pastebin, or direct mirror',
      description: 'Paste your game URL here and click "Extract & Resolve". The multi-tab worker pool bypasses Cloudflare Turnstile captchas across all parts in parallel (~1.8s per part).',
      position: 'bottom'
    },
    {
      targetId: 'tour-discovery-hub',
      badge: 'Step 2 of 5',
      title: 'Pre-Fetched Community Vault',
      subtitle: 'Instant 0-second direct downloads shared by gamers',
      description: 'Browse popular games already verified and cached in the community cloud. Click "Instant Load (0s)" to populate all direct links without any waiting.',
      position: 'bottom'
    },
    {
      targetId: 'tour-game-stage',
      badge: 'Step 3 of 5',
      title: 'Defrag Matrix & Decryption Stage',
      subtitle: 'Real-time multi-part visualizer replacing static tables',
      description: 'Watch all archive parts decrypt in real time. Switch between the 8-bit Defrag Matrix, raw direct URLs table, and live telemetry terminal.',
      position: 'top'
    },
    {
      targetId: 'tour-quick-actions',
      badge: 'Step 4 of 5',
      title: 'One-Click Exporters & JD2 Push',
      subtitle: 'Direct link grabber and multi-format file exporters',
      description: 'Push all direct links straight into JDownloader 2 LinkGrabber with zero deep analysis prompts, or export as .txt, .json, and .crawljob files.',
      position: 'top'
    },
    {
      targetId: 'tour-sidebar-footer',
      badge: 'Step 5 of 5',
      title: 'Command Hub, Issues & Updates',
      subtitle: 'Themes, auto-updater, audio haptics & public issue center',
      description: 'Switch between 8 dynamic OLED themes, toggle synthesized gaming audio haptics, check updates, and report issues or view known bug fixes.',
      position: 'right'
    }
  ];

  let currentStepIndex: number = 0;
  let spotlightRect = { top: 0, left: 0, width: 0, height: 0, visible: false };
  let tooltipStyle = '';
  let windowWidth = 1180;
  let windowHeight = 840;

  $: currentStep = STEPS[currentStepIndex];

  async function updateSpotlight() {
    if (!isOpen) return;
    const step = STEPS[currentStepIndex];
    if (!step) return;
    await tick();

    const tooltipWidth = (currentStepIndex === 2 || currentStepIndex === 3) ? 440 : 380;
    const tooltipHeight = (currentStepIndex === 2 || currentStepIndex === 3) ? 410 : 240;

    const targetEl = document.getElementById(step.targetId);
    if (!targetEl) {
      spotlightRect = {
        top: Math.floor(windowHeight / 2 - 100),
        left: Math.floor(windowWidth / 2 - (tooltipWidth / 2)),
        width: tooltipWidth,
        height: 200,
        visible: false
      };
      tooltipStyle = `top: ${Math.max(20, Math.floor(windowHeight / 2 - (tooltipHeight / 2)))}px; left: ${Math.max(20, Math.floor(windowWidth / 2 - (tooltipWidth / 2)))}px;`;
      return;
    }

    targetEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });

    const rect = targetEl.getBoundingClientRect();
    const pad = 10;

    spotlightRect = {
      top: Math.max(0, rect.top - pad),
      left: Math.max(0, rect.left - pad),
      width: rect.width + pad * 2,
      height: rect.height + pad * 2,
      visible: true
    };

    let top = 0;
    let left = 0;

    if (step.position === 'bottom') {
      top = spotlightRect.top + spotlightRect.height + 16;
      left = spotlightRect.left + (spotlightRect.width / 2) - (tooltipWidth / 2);
    } else if (step.position === 'top') {
      top = spotlightRect.top - tooltipHeight - 16;
      left = spotlightRect.left + (spotlightRect.width / 2) - (tooltipWidth / 2);
    } else if (step.position === 'right') {
      top = spotlightRect.top + (spotlightRect.height / 2) - (tooltipHeight / 2);
      left = spotlightRect.left + spotlightRect.width + 18;
    } else {
      top = spotlightRect.top + (spotlightRect.height / 2) - (tooltipHeight / 2);
      left = spotlightRect.left - tooltipWidth - 18;
    }

    left = Math.max(16, Math.min(windowWidth - tooltipWidth - 20, left));
    top = Math.max(16, Math.min(windowHeight - tooltipHeight - 20, top));

    tooltipStyle = `top: ${top}px; left: ${left}px;`;
  }

  function goToStep(idx: number) {
    if (idx >= 0 && idx < STEPS.length) {
      playClickSound();
      currentStepIndex = idx;
      updateSpotlight();
    }
  }

  function handleNext(e?: MouseEvent | KeyboardEvent) {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    playClickSound();
    if (currentStepIndex < STEPS.length - 1) {
      currentStepIndex += 1;
      updateSpotlight();
    } else {
      handleFinish();
    }
  }

  function handlePrev(e?: MouseEvent | KeyboardEvent) {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    playClickSound();
    if (currentStepIndex > 0) {
      currentStepIndex -= 1;
      updateSpotlight();
    }
  }

  function handleFinish(e?: MouseEvent) {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    playSuccessChime();
    if (typeof window !== 'undefined') {
      localStorage.setItem('le_tour_completed', 'true');
      localStorage.setItem('le_first_run_v3.8.0', 'true');
    }
    onClose();
  }

  function handleSkip(e?: MouseEvent | KeyboardEvent) {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    playClickSound();
    if (typeof window !== 'undefined') {
      localStorage.setItem('le_tour_completed', 'true');
      localStorage.setItem('le_first_run_v3.8.0', 'true');
    }
    onClose();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!isOpen) return;
    if (e.key === 'ArrowRight' || e.key === 'Enter') {
      e.preventDefault();
      handleNext(e);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      handlePrev(e);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleSkip(e);
    }
  }

  let prevIsOpen = false;
  $: if (isOpen && !prevIsOpen) {
    prevIsOpen = true;
    currentStepIndex = 0;
    updateSpotlight();
  } else if (!isOpen && prevIsOpen) {
    prevIsOpen = false;
  }

  onMount(() => {
    window.addEventListener('resize', updateSpotlight);
    return () => {
      window.removeEventListener('resize', updateSpotlight);
    };
  });
</script>

<svelte:window on:keydown={handleKeydown} bind:innerWidth={windowWidth} bind:innerHeight={windowHeight} />

{#if isOpen}
  <!-- Full-Screen Transparent Input Shield (absorbs any clicks outside the card so they never hit background app UI) -->
  <div 
    class="tour-shield" 
    on:click|stopPropagation={() => {}} 
    aria-hidden="true"
  ></div>

  <!-- 4-Quadrant Deep 18px Gaussian Blurred Backdrop (Physical Cutout - Zero Blur Over Target) -->
  {#if spotlightRect.visible}
    <!-- Top Curtain -->
    <div 
      class="tour-quad-dim" 
      style="top: 0; left: 0; width: 100%; height: {Math.max(0, spotlightRect.top)}px;"
      on:click|stopPropagation={() => {}}
    ></div>
    <!-- Bottom Curtain -->
    <div 
      class="tour-quad-dim" 
      style="top: {spotlightRect.top + spotlightRect.height}px; left: 0; width: 100%; height: {Math.max(0, windowHeight - (spotlightRect.top + spotlightRect.height))}px;"
      on:click|stopPropagation={() => {}}
    ></div>
    <!-- Left Curtain -->
    <div 
      class="tour-quad-dim" 
      style="top: {spotlightRect.top}px; left: 0; width: {Math.max(0, spotlightRect.left)}px; height: {spotlightRect.height}px;"
      on:click|stopPropagation={() => {}}
    ></div>
    <!-- Right Curtain -->
    <div 
      class="tour-quad-dim" 
      style="top: {spotlightRect.top}px; left: {spotlightRect.left + spotlightRect.width}px; width: {Math.max(0, windowWidth - (spotlightRect.left + spotlightRect.width))}px; height: {spotlightRect.height}px;"
      on:click|stopPropagation={() => {}}
    ></div>
  {:else}
    <!-- Full Screen Dim when no target element is present -->
    <div 
      class="tour-quad-dim" 
      style="top: 0; left: 0; width: 100%; height: 100%;"
      on:click|stopPropagation={() => {}}
    ></div>
  {/if}

  {#if spotlightRect.visible}
    <div 
      class="spotlight-box"
      style="
        top: {spotlightRect.top}px; 
        left: {spotlightRect.left}px; 
        width: {spotlightRect.width}px; 
        height: {spotlightRect.height}px;
      "
      on:click|stopPropagation={() => {}}
    >
      <div class="spotlight-beacon-corner top-left"></div>
      <div class="spotlight-beacon-corner top-right"></div>
      <div class="spotlight-beacon-corner bottom-left"></div>
      <div class="spotlight-beacon-corner bottom-right"></div>
    </div>
  {/if}

  <!-- Interactive Tour Card Tooltip (Fixed Top-Level Element with Independent DirectComposition Hit-Testing) -->
  <div 
    class="tour-card glass-panel" 
    class:wide-card={currentStepIndex === 2 || currentStepIndex === 3}
    style={tooltipStyle} 
    role="dialog"
    aria-modal="true"
    aria-label="Onboarding Tour"
    tabindex="-1"
    on:click|stopPropagation={() => {}}
    on:keydown|stopPropagation={() => {}}
  >
    <div class="tour-card-header">
      <div class="tour-step-badge">
        <Icon name="sparkles" size={13} color="var(--accent-primary)" />
        <span>{currentStep.badge}</span>
      </div>
      <button type="button" class="btn-skip-icon" on:click|stopPropagation={handleSkip} title="Skip Tour (Esc)" aria-label="Skip tour">
        <Icon name="close" size={14} />
      </button>
    </div>

      <div class="tour-card-body">
        <h3 class="tour-title">{currentStep.title}</h3>
        <p class="tour-subtitle">{currentStep.subtitle}</p>
        <p class="tour-desc">{currentStep.description}</p>

        <!-- Step 3 Interactive Mini Screen: Defrag Matrix Visualizer -->
        {#if currentStepIndex === 2}
          <div class="mini-hud-screen mini-screen-defrag">
            <div class="mini-hud-top">
              <div class="mini-hud-title-col">
                <div class="mini-hud-pulse-tag">
                  <span class="pulse-radar"></span>
                  <span>PARALLEL WORKER POOL</span>
                </div>
                <span class="mini-hud-game-name">Ghost of Tsushima: Director's Cut (Part 4/14)</span>
              </div>
              <div class="mini-hud-speed-badge font-mono">~1.8s/part</div>
            </div>

            <!-- Mini 14-Block Defrag Grid -->
            <div class="mini-defrag-grid">
              {#each Array(14) as _, i}
                <div 
                  class="mini-defrag-block"
                  class:done={i < 8}
                  class:decrypting={i === 8}
                  class:queued={i > 8}
                  title="Part {i + 1}"
                >
                  <span class="mini-block-num">{i + 1}</span>
                  {#if i < 8}
                    <span class="block-check">✓</span>
                  {:else if i === 8}
                    <span class="block-pulse-dot"></span>
                  {/if}
                </div>
              {/each}
            </div>

            <!-- Mini Telemetry Footer -->
            <div class="mini-hud-footer">
              <div class="mini-hud-stat">
                <Icon name="check-circle" size={12} color="#00f0a0" />
                <span>8/14 Resolved</span>
              </div>
              <div class="mini-hud-stat font-mono">
                <Icon name="shield-check" size={12} color="#38bdf8" />
                <span>Turnstile Token OK</span>
              </div>
              <div class="mini-hud-stat font-mono">
                <span>61.2 GB</span>
              </div>
            </div>
          </div>
        {/if}

        <!-- Step 4 Interactive Mini Screen: One-Click Exporters & JD2 Push HUD -->
        {#if currentStepIndex === 3}
          <div class="mini-hud-screen mini-screen-exporters">
            <div class="mini-hud-top">
              <div class="mini-hud-pulse-tag">
                <Icon name="zap" size={12} color="#00f0a0" />
                <span>INSTANT EXPORT LAUNCHPAD</span>
              </div>
              <div class="mini-jd2-status">
                <span class="jd2-dot online"></span>
                <span>Port 9666 • JD2 Connected</span>
              </div>
            </div>

            <!-- Mock JD2 1-Click Push Button -->
            <div class="mini-jd2-push-banner">
              <div class="mini-jd2-btn">
                <div class="mini-jd2-icon-halo">
                  <Icon name="bolt" size={16} color="#ffffff" strokeWidth={2.5} />
                </div>
                <div class="mini-jd2-btn-text">
                  <span class="mini-btn-primary-title">Push 14 Parts to JDownloader 2</span>
                  <span class="mini-btn-sub">Direct FlashGot LinkGrabber</span>
                </div>
              </div>
            </div>

            <!-- Export Format Pills -->
            <div class="mini-export-pills-row">
              <div class="mini-format-pill pill-crawljob">
                <Icon name="package" size={11} />
                <span>.crawljob</span>
              </div>
              <div class="mini-format-pill">
                <Icon name="table" size={11} />
                <span>.txt Links</span>
              </div>
              <div class="mini-format-pill">
                <Icon name="grid" size={11} />
                <span>.json Data</span>
              </div>
              <div class="mini-format-pill pill-copy">
                <Icon name="copy" size={11} />
                <span>Copy All</span>
              </div>
            </div>

            <!-- Fragment Callout -->
            <div class="mini-fragment-notice">
              <Icon name="shield-check" size={11} color="#00f0a0" />
              <span>Appends <code>#filename.rar</code> to bypass JD2 Deep Link Analysis</span>
            </div>
          </div>
        {/if}
      </div>

      <div class="tour-card-footer">
        <div class="tour-dots-indicator">
          {#each STEPS as _, idx}
            <button 
              type="button" 
              class="dot" 
              class:active={idx === currentStepIndex}
              class:completed={idx < currentStepIndex}
              on:click|stopPropagation={() => goToStep(idx)}
              title="Step {idx + 1}"
              aria-label="Step {idx + 1}"
            ></button>
          {/each}
        </div>

        <div class="tour-buttons-row">
          <button 
            type="button" 
            class="btn-secondary btn-sm btn-tour-prev"
            disabled={currentStepIndex === 0}
            on:click|stopPropagation={handlePrev}
            aria-label="Previous step"
          >
            <Icon name="arrow-left" size={12} />
            <span>Back</span>
          </button>

          {#if currentStepIndex < STEPS.length - 1}
            <button 
              type="button" 
              class="btn-primary btn-sm btn-tour-next"
              on:click|stopPropagation={handleNext}
              aria-label="Next step"
            >
              <span>Next</span>
              <Icon name="arrow-right" size={12} color="#ffffff" />
            </button>
          {:else}
            <button 
              type="button" 
              class="btn-primary btn-sm btn-finish"
              on:click|stopPropagation={handleFinish}
              aria-label="Complete tour and get started"
            >
              <Icon name="check" size={13} color="#ffffff" strokeWidth={2.5} />
              <span>Get Started</span>
            </button>
          {/if}
        </div>
      </div>
    </div>
{/if}

<style>
  /* Full-Screen Input Shield to absorb clicks outside the card so they never hit the app underneath */
  .tour-shield {
    position: fixed;
    inset: 0;
    z-index: 10000;
    background: rgba(0, 0, 0, 0.001);
    pointer-events: auto;
    cursor: default;
  }

  .tour-quad-dim {
    position: fixed;
    border: none;
    padding: 0;
    margin: 0;
    background: rgba(3, 6, 12, 0.84);
    backdrop-filter: blur(18px) saturate(180%);
    -webkit-backdrop-filter: blur(18px) saturate(180%);
    pointer-events: auto;
    cursor: default;
    z-index: 10001;
    transition: 
      top 0.35s cubic-bezier(0.16, 1, 0.3, 1),
      left 0.35s cubic-bezier(0.16, 1, 0.3, 1),
      width 0.35s cubic-bezier(0.16, 1, 0.3, 1),
      height 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes tourFadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  /* Glowing ambient focus aura around spotlight box */
  .spotlight-box {
    position: fixed;
    pointer-events: auto;
    cursor: default;
    border-radius: 12px;
    border: 2px solid var(--accent-primary);
    box-shadow: 
      0 0 35px rgba(0, 240, 160, 0.5),
      0 0 12px rgba(0, 240, 160, 0.8),
      inset 0 0 16px rgba(0, 240, 160, 0.3);
    filter: drop-shadow(0 0 10px rgba(0, 240, 160, 0.45));
    transition: 
      top 0.35s cubic-bezier(0.16, 1, 0.3, 1),
      left 0.35s cubic-bezier(0.16, 1, 0.3, 1),
      width 0.35s cubic-bezier(0.16, 1, 0.3, 1),
      height 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    z-index: 10002;
    animation: spotlightPulse 2s infinite ease-in-out;
  }

  @keyframes spotlightPulse {
    0%, 100% {
      border-color: var(--accent-primary);
      box-shadow: 
        0 0 30px rgba(0, 240, 160, 0.45),
        0 0 10px rgba(0, 240, 160, 0.7),
        inset 0 0 16px rgba(0, 240, 160, 0.25);
    }
    50% {
      border-color: var(--accent-secondary);
      box-shadow: 
        0 0 45px rgba(6, 182, 212, 0.55),
        0 0 16px rgba(6, 182, 212, 0.85),
        inset 0 0 22px rgba(6, 182, 212, 0.35);
    }
  }

  .spotlight-beacon-corner {
    position: absolute;
    width: 8px;
    height: 8px;
    border-color: #ffffff;
    border-style: solid;
  }
  .spotlight-beacon-corner.top-left {
    top: -2px; left: -2px;
    border-width: 2px 0 0 2px;
    border-top-left-radius: 4px;
  }
  .spotlight-beacon-corner.top-right {
    top: -2px; right: -2px;
    border-width: 2px 2px 0 0;
    border-top-right-radius: 4px;
  }
  .spotlight-beacon-corner.bottom-left {
    bottom: -2px; left: -2px;
    border-width: 0 0 2px 2px;
    border-bottom-left-radius: 4px;
  }
  .spotlight-beacon-corner.bottom-right {
    bottom: -2px; right: -2px;
    border-width: 0 2px 2px 0;
    border-bottom-right-radius: 4px;
  }

  /* Frosted acrylic blur box */
  .tour-card {
    position: fixed !important;
    pointer-events: auto !important;
    width: 390px;
    padding: 20px;
    border-radius: 18px;
    background: rgba(13, 17, 26, 0.96) !important;
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.16);
    box-shadow: 
      0 28px 56px rgba(0, 0, 0, 0.9), 
      0 0 32px rgba(0, 240, 160, 0.22),
      inset 0 1px 0 rgba(255, 255, 255, 0.12);
    z-index: 10010 !important;
    cursor: default;
    isolation: isolate;
    transition: 
      top 0.35s cubic-bezier(0.16, 1, 0.3, 1),
      left 0.35s cubic-bezier(0.16, 1, 0.3, 1),
      width 0.3s ease;
    animation: cardPopIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .tour-card.wide-card {
    width: 440px;
  }

  @keyframes cardPopIn {
    from {
      opacity: 0;
      transform: scale(0.92) translateY(8px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  .tour-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .tour-step-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 9px;
    border-radius: 20px;
    background: rgba(0, 240, 160, 0.12);
    border: 1px solid rgba(0, 240, 160, 0.3);
    color: var(--accent-primary);
    font-family: var(--font-display);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .btn-skip-icon {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer !important;
    pointer-events: auto !important;
    padding: 4px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s, background 0.15s;
  }
  .btn-skip-icon:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.08);
  }

  .tour-title {
    margin: 0 0 4px 0;
    font-family: var(--font-display);
    font-size: 1.08rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.015em;
  }

  .tour-subtitle {
    margin: 0 0 10px 0;
    font-size: 0.78rem;
    color: var(--accent-primary);
    font-weight: 500;
  }

  .tour-desc {
    margin: 0 0 14px 0;
    font-size: 0.84rem;
    line-height: 1.5;
    color: var(--text-secondary);
  }

  /* Mini Preview HUD Screens */
  .mini-hud-screen {
    margin-bottom: 16px;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.4);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mini-hud-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
  }

  .mini-hud-title-col {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .mini-hud-pulse-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: #00f0a0;
  }

  .pulse-radar {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #00f0a0;
    box-shadow: 0 0 8px #00f0a0;
    animation: radarPulse 1.4s ease-in-out infinite;
  }

  @keyframes radarPulse {
    0%, 100% { transform: scale(0.9); opacity: 0.7; }
    50% { transform: scale(1.3); opacity: 1; }
  }

  .mini-hud-game-name {
    font-size: 0.76rem;
    color: #ffffff;
    font-weight: 600;
  }

  .mini-hud-speed-badge {
    font-size: 0.7rem;
    padding: 2px 7px;
    border-radius: 6px;
    background: rgba(0, 240, 160, 0.12);
    border: 1px solid rgba(0, 240, 160, 0.3);
    color: #00f0a0;
    white-space: nowrap;
  }

  /* Mini Defrag Grid */
  .mini-defrag-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 5px;
  }

  .mini-defrag-block {
    position: relative;
    height: 28px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.68rem;
    font-weight: 700;
    color: var(--text-muted);
    transition: all 0.2s ease;
  }

  .mini-defrag-block.done {
    background: rgba(0, 240, 160, 0.18);
    border-color: rgba(0, 240, 160, 0.45);
    color: #00f0a0;
    box-shadow: 0 0 10px rgba(0, 240, 160, 0.2);
  }

  .block-check {
    font-size: 0.65rem;
    margin-left: 2px;
    color: #00f0a0;
  }

  .mini-defrag-block.decrypting {
    background: rgba(245, 158, 11, 0.2);
    border-color: rgba(245, 158, 11, 0.6);
    color: #f59e0b;
    box-shadow: 0 0 12px rgba(245, 158, 11, 0.35);
    animation: decryptPulse 1.2s ease-in-out infinite;
  }

  @keyframes decryptPulse {
    0%, 100% { border-color: rgba(245, 158, 11, 0.6); }
    50% { border-color: #00f0a0; box-shadow: 0 0 14px rgba(0, 240, 160, 0.4); color: #00f0a0; }
  }

  .block-pulse-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #f59e0b;
    margin-left: 2px;
  }

  .mini-hud-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.72rem;
    color: var(--text-muted);
    padding-top: 4px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }

  .mini-hud-stat {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  /* Exporters Launchpad HUD */
  .mini-jd2-status {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.7rem;
    color: #38bdf8;
  }

  .jd2-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 6px #38bdf8;
  }

  .mini-jd2-push-banner {
    padding: 2px;
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(0, 240, 160, 0.3), rgba(56, 189, 248, 0.2));
  }

  .mini-jd2-btn {
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(13, 17, 26, 0.94);
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .mini-jd2-icon-halo {
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: rgba(0, 240, 160, 0.15);
    border: 1px solid rgba(0, 240, 160, 0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .mini-jd2-btn-text {
    display: flex;
    flex-direction: column;
  }

  .mini-btn-primary-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: #ffffff;
  }

  .mini-btn-sub {
    font-size: 0.68rem;
    color: #00f0a0;
  }

  .mini-export-pills-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .mini-format-pill {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 5px 6px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 0.7rem;
    color: var(--text-secondary);
    font-weight: 600;
  }

  .mini-format-pill.pill-crawljob {
    background: rgba(0, 240, 160, 0.1);
    border-color: rgba(0, 240, 160, 0.25);
    color: #00f0a0;
  }

  .mini-format-pill.pill-copy {
    color: #ffffff;
  }

  .mini-fragment-notice {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  .mini-fragment-notice code {
    font-family: monospace;
    color: #00f0a0;
    background: rgba(0, 240, 160, 0.1);
    padding: 1px 4px;
    border-radius: 4px;
  }

  /* Footer controls */
  .tour-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 14px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .tour-dots-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    border: none;
    padding: 0;
    margin: 0;
    cursor: pointer !important;
    pointer-events: auto !important;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .dot:hover {
    background: rgba(255, 255, 255, 0.5);
    transform: scale(1.2);
  }

  .dot.active {
    width: 22px;
    border-radius: 4px;
    background: var(--accent-primary);
    box-shadow: 0 0 8px var(--accent-primary);
    cursor: default !important;
    transform: none;
  }

  .dot.completed {
    background: rgba(0, 240, 160, 0.6);
  }

  .tour-buttons-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .tour-buttons-row button {
    position: relative;
    pointer-events: auto !important;
    cursor: pointer !important;
    user-select: none;
    transition: all 0.15s ease;
  }

  .tour-buttons-row button * {
    pointer-events: none;
  }

  .btn-skip-icon * {
    pointer-events: none;
  }

  .tour-buttons-row button:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    pointer-events: none;
    transform: none !important;
    filter: none !important;
    box-shadow: none !important;
  }

  .btn-tour-next {
    min-width: 84px;
  }

  .btn-tour-prev {
    min-width: 76px;
  }

  .btn-finish {
    background: linear-gradient(135deg, #00f0a0, #00b875);
    border: none;
    box-shadow: 0 0 14px rgba(0, 240, 160, 0.4);
    min-width: 110px;
  }
</style>
