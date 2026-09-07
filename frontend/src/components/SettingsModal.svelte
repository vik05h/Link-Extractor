<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, toggleAudioMute, isAudioMuted } from '../utils/audio';
  import { waitForBridge } from '../utils/bridgeReady';
  import type { AppSettings } from '../types';

  export let isOpen: boolean = false;
  export let onClose: () => void = () => {};
  export let onThemeChange: (theme: string) => void = () => {};
  export let onCheckUpdates: () => void = () => {};
  export let onOpenTour: () => void = () => {};
  export let onOpenIssueCenter: () => void = () => {};
  export let currentVersion: string = 'v3.8.0';

  let currentTheme = 'cyber';
  let isCheckingUpdates = false;
  let concurrency = 3;
  let autoValidate = true;
  let jdPort = 9666;
  let autoUpload = true;
  let clipboardSentinel = true;
  let autoCrashReporting = true;
  let soundEnabled = true;

  // Slider interactive drag state
  let isSliderActive = false;

  onMount(() => {
    if (typeof window !== 'undefined') {
      currentTheme = localStorage.getItem('app_theme') || 'cyber';
      soundEnabled = !isAudioMuted();

      waitForBridge('get_settings').then((ready) => {
        if (ready && (window as any).pywebview?.api?.get_settings) {
          (window as any).pywebview.api.get_settings().then((s: AppSettings) => {
            if (s) {
              concurrency = s.concurrency || 3;
              autoValidate = s.auto_validate ?? true;
              jdPort = s.jd_port || 9666;
              autoUpload = s.community_auto_upload ?? true;
              clipboardSentinel = s.clipboard_sentinel_enabled ?? true;
              autoCrashReporting = s.auto_crash_reporting ?? true;
            }
          }).catch(() => {});
        }
      });
    }
  });

  function handleThemeSelect(t: string) {
    playClickSound();
    currentTheme = t;
    if (typeof window !== 'undefined') {
      localStorage.setItem('app_theme', t);
      document.documentElement.setAttribute('data-theme', t);
    }
    onThemeChange(t);
  }

  function handleCheckUpdates() {
    playClickSound();
    isCheckingUpdates = true;
    if (onCheckUpdates) {
      onCheckUpdates();
    }
    setTimeout(() => {
      isCheckingUpdates = false;
    }, 1500);
  }

  function handleSoundToggle() {
    playClickSound();
    soundEnabled = !soundEnabled;
    toggleAudioMute();
  }

  function handleConcurrencySelect(step: number) {
    if (concurrency !== step) {
      concurrency = step;
      playClickSound();
    }
  }

  function handleSliderInput(e: Event) {
    const target = e.target as HTMLInputElement;
    const val = parseInt(target.value, 10);
    if (val !== concurrency) {
      concurrency = val;
      playClickSound();
    }
  }

  function saveSettings() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.save_settings({
        concurrency,
        auto_validate: autoValidate,
        jd_port: jdPort,
        community_auto_upload: autoUpload,
        clipboard_sentinel_enabled: clipboardSentinel,
        auto_crash_reporting: autoCrashReporting
      }).then(() => {
        onClose();
      });
    } else {
      onClose();
    }
  }

  // Concurrency slider calculation (1 to 6)
  $: sliderPercent = ((concurrency - 1) / 5) * 100;
</script>

{#if isOpen}
  <div 
    class="modal-backdrop" 
    on:click|self={onClose} 
    on:keydown={(e) => e.key === 'Escape' && onClose()} 
    role="dialog" 
    aria-modal="true" 
    tabindex="-1"
  >
    <div class="modal-card glass-panel" role="document">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="modal-title-wrapper">
          <div class="modal-icon-badge">
            <Icon name="settings" size={18} color="var(--accent-primary)" />
          </div>
          <div class="modal-title-text">
            <div class="modal-title">ENGINE & UI CONFIGURATION</div>
            <div class="modal-subtitle">Preferences, Parallelism & Community Synchronization</div>
          </div>
        </div>
        <button type="button" class="btn-close" on:click={onClose} aria-label="Close dialog">
          <Icon name="close" size={16} />
        </button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        <!-- Visual Theme & Palette -->
        <div class="setting-section">
          <div class="section-header">
            <Icon name="sparkles" size={14} color="var(--accent-primary)" />
            <span class="setting-label">VISUAL THEME & PALETTE</span>
          </div>

          <div class="theme-options-grid">
            <!-- Cyber Dark -->
            <button 
              type="button"
              class="theme-card" 
              class:selected={currentTheme === 'cyber'}
              on:click={() => handleThemeSelect('cyber')}
            >
              {#if currentTheme === 'cyber'}
                <div class="theme-active-indicator">
                  <Icon name="check" size={11} color="#ffffff" strokeWidth={3} />
                </div>
              {/if}
              <div class="theme-swatch-wrapper">
                <div class="theme-swatch cyber-swatch"></div>
              </div>
              <div class="theme-name">Cyber-Dark</div>
              <div class="theme-desc">Neon Emerald & OLED Black</div>
            </button>

            <!-- Steam Slate -->
            <button 
              type="button"
              class="theme-card" 
              class:selected={currentTheme === 'steam'}
              on:click={() => handleThemeSelect('steam')}
            >
              {#if currentTheme === 'steam'}
                <div class="theme-active-indicator">
                  <Icon name="check" size={11} color="#ffffff" strokeWidth={3} />
                </div>
              {/if}
              <div class="theme-swatch-wrapper">
                <div class="theme-swatch steam-swatch"></div>
              </div>
              <div class="theme-name">Steam Slate</div>
              <div class="theme-desc">Obsidian & Electric Blue</div>
            </button>

            <!-- Dynamic Adaptive -->
            <button 
              type="button"
              class="theme-card" 
              class:selected={currentTheme === 'adaptive'}
              on:click={() => handleThemeSelect('adaptive')}
            >
              {#if currentTheme === 'adaptive'}
                <div class="theme-active-indicator">
                  <Icon name="check" size={11} color="#ffffff" strokeWidth={3} />
                </div>
              {/if}
              <div class="theme-swatch-wrapper">
                <div class="theme-swatch adaptive-swatch"></div>
              </div>
              <div class="theme-name">Dynamic Adaptive</div>
              <div class="theme-desc">Samples Active Game Art</div>
            </button>
          </div>
        </div>

        <!-- Playwright Worker Pool with Animated Slider -->
        <div class="setting-section">
          <div class="section-header-between">
            <div class="section-header-left">
              <Icon name="zap" size={14} color="var(--accent-primary)" />
              <div>
                <span class="setting-label">PLAYWRIGHT WORKER POOL</span>
                <div class="setting-subtext">Number of parallel browser tabs solving Cloudflare Turnstile</div>
              </div>
            </div>
            <div class="concurrency-badge">
              <span class="pulse-dot"></span>
              <span>{concurrency} {concurrency === 1 ? 'Tab' : 'Tabs'}</span>
            </div>
          </div>

          <!-- Animated Slider Module -->
          <div class="animated-slider-card glass-panel" class:dragging={isSliderActive}>
            <div class="slider-track-wrap">
              <!-- Floating Tooltip with Smooth Gliding Animation -->
              <div 
                class="slider-floating-tooltip" 
                style="left: {sliderPercent}%;"
              >
                <div class="tooltip-bubble">
                  <Icon name="zap" size={11} color="var(--accent-primary)" strokeWidth={2.5} />
                  <span>{concurrency} {concurrency === 1 ? 'Tab' : 'Tabs'}</span>
                </div>
                <div class="tooltip-caret"></div>
              </div>

              <!-- Visual Track -->
              <div class="slider-track-bar">
                <!-- Glowing Shimmer Fill Bar with Linear Shimmer Animation -->
                <div 
                  class="slider-track-fill" 
                  style="width: {sliderPercent}%;"
                >
                  <div class="shimmer-wave"></div>
                  <div class="fill-lead-glow"></div>
                </div>

                <!-- Animated Thumb -->
                <div 
                  class="slider-thumb-render" 
                  style="left: {sliderPercent}%;"
                >
                  <div class="thumb-halo"></div>
                  <div class="thumb-core"></div>
                </div>
              </div>

              <!-- Native Range Input Overlay (Accessible, Drag & Arrow-Key Capable) -->
              <input 
                id="concurrency-slider"
                type="range" 
                min="1" 
                max="6" 
                step="1" 
                value={concurrency}
                on:input={handleSliderInput}
                on:mousedown={() => isSliderActive = true}
                on:mouseup={() => isSliderActive = false}
                on:touchstart={() => isSliderActive = true}
                on:touchend={() => isSliderActive = false}
                class="slider-native-input"
                aria-label="Playwright Worker Pool Concurrency"
              />
            </div>

            <!-- Stepped Pip Points (1 to 6) -->
            <div class="slider-pips-row">
              {#each [1, 2, 3, 4, 5, 6] as step}
                <button 
                  type="button" 
                  class="slider-pip-btn" 
                  class:active={step <= concurrency}
                  class:current={step === concurrency}
                  on:click={() => handleConcurrencySelect(step)}
                  title="{step} parallel solver tabs"
                >
                  <div class="pip-dot"></div>
                  <span class="pip-label">{step}</span>
                </button>
              {/each}
            </div>

            <!-- Dynamic Performance Mode Intelligence Banner -->
            <div class="slider-tier-info">
              {#if concurrency <= 2}
                <div class="tier-pill tier-eco">
                  <Icon name="bolt" size={12} color="#10b981" />
                  <span class="tier-title">ECO FOOTPRINT</span>
                </div>
                <span class="tier-desc">Minimal CPU and RAM usage. Recommended for laptops and background resolution.</span>
              {:else if concurrency <= 4}
                <div class="tier-pill tier-balanced">
                  <Icon name="zap" size={12} color="#06b6d4" />
                  <span class="tier-title">BALANCED CORE</span>
                </div>
                <span class="tier-desc">Optimal Turnstile solve throughput and system stability. (Recommended)</span>
              {:else}
                <div class="tier-pill tier-turbo">
                  <Icon name="sparkles" size={12} color="#f59e0b" />
                  <span class="tier-title">TURBO HYPER-SPEED</span>
                </div>
                <span class="tier-desc">Max concurrency. Demands capable multi-core CPU and fast broadband connection.</span>
              {/if}
            </div>
          </div>
        </div>

        <!-- Integrations & Haptics with Modern Switches -->
        <div class="setting-section">
          <div class="section-header">
            <Icon name="bolt" size={14} color="var(--accent-primary)" />
            <span class="setting-label">INTEGRATIONS & HAPTICS</span>
          </div>

          <div class="toggles-list">
            <!-- 1-Byte Size Validation -->
            <div 
              class="toggle-card glass-panel" 
              on:click={() => { autoValidate = !autoValidate; playClickSound(); }}
              role="button"
              tabindex="0"
              on:keydown={(e) => (e.key === ' ' || e.key === 'Enter') && (autoValidate = !autoValidate, playClickSound())}
            >
              <div class="toggle-card-left">
                <div class="toggle-icon-wrap" class:active={autoValidate}>
                  <Icon name="hard-drive" size={16} color={autoValidate ? 'var(--accent-primary)' : 'var(--text-muted)'} />
                </div>
                <div class="toggle-content">
                  <div class="toggle-title">Instant 1-Byte Size Validation</div>
                  <div class="setting-subtext">Rapidly aggregates exact repack sizes via HTTP Range requests without downloading files</div>
                </div>
              </div>
              <div class="cyber-switch" class:checked={autoValidate}>
                <div class="switch-track">
                  <div class="switch-thumb"></div>
                </div>
              </div>
            </div>

            <!-- Clipboard Sentinel -->
            <div 
              class="toggle-card glass-panel" 
              on:click={() => { clipboardSentinel = !clipboardSentinel; playClickSound(); }}
              role="button"
              tabindex="0"
              on:keydown={(e) => (e.key === ' ' || e.key === 'Enter') && (clipboardSentinel = !clipboardSentinel, playClickSound())}
            >
              <div class="toggle-card-left">
                <div class="toggle-icon-wrap" class:active={clipboardSentinel}>
                  <Icon name="copy" size={16} color={clipboardSentinel ? 'var(--accent-primary)' : 'var(--text-muted)'} />
                </div>
                <div class="toggle-content">
                  <div class="toggle-title">Clipboard Sentinel</div>
                  <div class="setting-subtext">Background notification when copying FitGirl repack URLs to clipboard for 1-click grab</div>
                </div>
              </div>
              <div class="cyber-switch" class:checked={clipboardSentinel}>
                <div class="switch-track">
                  <div class="switch-thumb"></div>
                </div>
              </div>
            </div>

            <!-- Gaming Audio Haptics -->
            <div 
              class="toggle-card glass-panel" 
              on:click={handleSoundToggle}
              role="button"
              tabindex="0"
              on:keydown={(e) => (e.key === ' ' || e.key === 'Enter') && handleSoundToggle()}
            >
              <div class="toggle-card-left">
                <div class="toggle-icon-wrap" class:active={soundEnabled}>
                  <Icon name={soundEnabled ? 'volume' : 'volume-x'} size={16} color={soundEnabled ? 'var(--accent-primary)' : 'var(--text-muted)'} />
                </div>
                <div class="toggle-content">
                  <div class="toggle-title">Gaming Audio Haptics</div>
                  <div class="setting-subtext">Subtle synthesized micro-sounds on Turnstile bypass, link resolution & completion</div>
                </div>
              </div>
              <div class="cyber-switch" class:checked={soundEnabled}>
                <div class="switch-track">
                  <div class="switch-thumb"></div>
                </div>
              </div>
            </div>

            <!-- Auto-Publish to Community Cloud -->
            <div 
              class="toggle-card glass-panel" 
              on:click={() => { autoUpload = !autoUpload; playClickSound(); }}
              role="button"
              tabindex="0"
              on:keydown={(e) => (e.key === ' ' || e.key === 'Enter') && (autoUpload = !autoUpload, playClickSound())}
            >
              <div class="toggle-card-left">
                <div class="toggle-icon-wrap" class:active={autoUpload}>
                  <Icon name="globe" size={16} color={autoUpload ? 'var(--accent-primary)' : 'var(--text-muted)'} />
                </div>
                <div class="toggle-content">
                  <div class="toggle-title">Auto-Publish to Community Cloud</div>
                  <div class="setting-subtext">Share resolved direct links anonymously to eliminate solver wait time for other gamers</div>
                </div>
              </div>
              <div class="cyber-switch" class:checked={autoUpload}>
                <div class="switch-track">
                  <div class="switch-thumb"></div>
                </div>
              </div>
            </div>

            <!-- Anonymous Crash Diagnostics -->
            <div 
              class="toggle-card glass-panel" 
              on:click={() => { autoCrashReporting = !autoCrashReporting; playClickSound(); }}
              role="button"
              tabindex="0"
              on:keydown={(e) => (e.key === ' ' || e.key === 'Enter') && (autoCrashReporting = !autoCrashReporting, playClickSound())}
            >
              <div class="toggle-card-left">
                <div class="toggle-icon-wrap" class:active={autoCrashReporting}>
                  <Icon name="shield-check" size={16} color={autoCrashReporting ? 'var(--accent-primary)' : 'var(--text-muted)'} />
                </div>
                <div class="toggle-content">
                  <div class="toggle-title">Anonymous Crash Diagnostics</div>
                  <div class="setting-subtext">Transmits sanitized error traces to expedite bug fixes and maintain Turnstile compatibility</div>
                </div>
              </div>
              <div class="cyber-switch" class:checked={autoCrashReporting}>
                <div class="switch-track">
                  <div class="switch-thumb"></div>
                </div>
              </div>
            </div>

            <!-- JDownloader 2 FlashGot Port Integration -->
            <div class="toggle-card glass-panel jd-port-card">
              <div class="toggle-card-left">
                <div class="toggle-icon-wrap active">
                  <Icon name="download" size={16} color="var(--accent-primary)" />
                </div>
                <div class="toggle-content">
                  <div class="toggle-title">JDownloader 2 FlashGot Port</div>
                  <div class="setting-subtext">Local HTTP API port for 1-click LinkGrabber push (default: 9666)</div>
                </div>
              </div>
              <div class="port-control-right">
                <span class="port-prefix-label">PORT:</span>
                <input 
                  id="jd-port-input"
                  type="number" 
                  bind:value={jdPort} 
                  class="glass-input port-input" 
                  min="1024"
                  max="65535"
                />
                {#if jdPort !== 9666}
                  <button 
                    type="button" 
                    class="btn-reset-port" 
                    on:click={() => { jdPort = 9666; playClickSound(); }}
                    title="Reset to standard default port 9666"
                  >
                    Reset
                  </button>
                {/if}
              </div>
            </div>
          </div>
        </div>

        <!-- Version & Community Card -->
        <div class="setting-section">
          <div class="section-header">
            <Icon name="package" size={14} color="var(--accent-primary)" />
            <span class="setting-label">VERSION & COMMUNITY</span>
          </div>

          <div class="version-card glass-panel">
            <div class="version-meta">
              <div class="version-name-row">
                <span class="app-title">Link Extractor</span>
                <span class="badge-ver">{currentVersion}</span>
                <span class="engine-status-pill">
                  <span class="pulse-dot"></span>
                  <span>HYPER ENGINE ONLINE</span>
                </span>
              </div>
              <div class="version-author">Author: Vikash (@vik05h) • PolyForm Noncommercial 1.0.0</div>
            </div>

            <button 
              type="button" 
              class="btn-secondary btn-check-updates"
              disabled={isCheckingUpdates}
              on:click={handleCheckUpdates}
            >
              <span class:spin={isCheckingUpdates}>
                <Icon name="refresh" size={14} color="var(--accent-primary)" />
              </span>
              <span>{isCheckingUpdates ? 'Checking GitHub...' : 'Check for Updates'}</span>
            </button>
          </div>

          <div class="community-actions-row">
            <button 
              type="button" 
              class="btn-secondary tour-btn"
              on:click={() => { onClose(); onOpenTour(); }}
            >
              <Icon name="help-circle" size={14} color="var(--accent-secondary)" />
              <span>Replay Guided Tour</span>
            </button>
            <button 
              type="button" 
              class="btn-secondary issue-btn"
              on:click={() => { onClose(); onOpenIssueCenter(); }}
            >
              <Icon name="bug" size={14} color="#f43f5e" />
              <span>Community Issue Center</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        <button type="button" class="btn-secondary btn-footer-cancel" on:click={onClose}>
          <span>Cancel</span>
        </button>
        <button type="button" class="btn-primary btn-footer-save" on:click={saveSettings}>
          <Icon name="check" size={15} color="#ffffff" strokeWidth={2.5} />
          <span>Save Settings</span>
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(4, 7, 12, 0.82);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    animation: backdropFadeIn 0.22s ease-out;
  }

  .modal-card {
    width: 620px;
    max-width: 95%;
    max-height: 88vh;
    display: flex;
    flex-direction: column;
    background: rgba(11, 15, 25, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 32px 64px -12px rgba(0, 0, 0, 0.85), 0 0 36px var(--accent-glow);
    border-radius: var(--radius-lg);
    overflow: hidden;
    animation: modalScaleIn 0.28s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes backdropFadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes modalScaleIn {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(10px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  /* Modal Header */
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 22px;
    border-bottom: 1px solid var(--border-subtle);
    background: rgba(255, 255, 255, 0.02);
  }

  .modal-title-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .modal-icon-badge {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 14px var(--accent-glow);
  }

  .modal-title-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .modal-title {
    font-family: var(--font-display);
    font-size: 13.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-primary);
  }

  .modal-subtitle {
    font-size: 11px;
    color: var(--text-muted);
  }

  .btn-close {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle);
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }

  .btn-close:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.1);
    transform: rotate(90deg);
  }

  /* Modal Body */
  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 22px;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .modal-body::-webkit-scrollbar {
    width: 6px;
  }
  .modal-body::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 3px;
  }
  .modal-body::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
  }
  .modal-body::-webkit-scrollbar-thumb:hover {
    background: var(--accent-primary);
  }

  .setting-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .section-header-between {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .section-header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .setting-label {
    font-family: var(--font-display);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--accent-primary);
    letter-spacing: 0.08em;
  }

  .setting-subtext {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.35;
  }

  /* Theme Cards */
  .theme-options-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  .theme-card {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 14px 12px;
    border-radius: var(--radius-md);
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    overflow: hidden;
  }

  .theme-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: transparent;
    transition: background 0.2s;
  }

  .theme-card:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.18);
    transform: translateY(-2px);
  }

  .theme-card.selected {
    border-color: var(--accent-primary);
    background: rgba(16, 185, 129, 0.08);
    box-shadow: 0 0 20px var(--accent-glow);
  }

  .theme-card.selected::before {
    background: var(--accent-primary);
    box-shadow: 0 0 8px var(--accent-primary);
  }

  .theme-active-indicator {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--accent-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 10px var(--accent-primary);
    animation: scaleInCheck 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes scaleInCheck {
    from { transform: scale(0); }
    to { transform: scale(1); }
  }

  .theme-swatch-wrapper {
    position: relative;
    width: 36px;
    height: 36px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .theme-swatch {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    box-shadow: 0 0 12px rgba(0, 0, 0, 0.5);
    transition: transform 0.2s ease;
  }

  .theme-card:hover .theme-swatch {
    transform: scale(1.1);
  }

  .cyber-swatch { 
    background: linear-gradient(135deg, #10b981, #06b6d4); 
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
  }
  .steam-swatch { 
    background: linear-gradient(135deg, #38bdf8, #1b2838); 
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
  }
  .adaptive-swatch { 
    background: conic-gradient(#f43f5e, #eab308, #10b981, #06b6d4, #8b5cf6, #f43f5e); 
    animation: chromaSpin 8s linear infinite;
    box-shadow: 0 0 14px rgba(244, 63, 94, 0.3);
  }

  @keyframes chromaSpin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .theme-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .theme-desc {
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 3px;
    line-height: 1.25;
  }

  /* Concurrency Header Badge */
  .concurrency-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-mono);
    font-size: 11.5px;
    font-weight: 700;
    color: var(--accent-primary);
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.25);
    padding: 3px 10px;
    border-radius: 20px;
    box-shadow: 0 0 12px var(--accent-glow);
  }

  .pulse-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-primary);
    box-shadow: 0 0 8px var(--accent-primary);
    animation: livePulse 1.8s ease-in-out infinite;
  }

  @keyframes livePulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.85); }
  }

  /* ========================================================
     ANIMATED SLIDER MODULE
     ======================================================== */
  .animated-slider-card {
    padding: 24px 18px 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .animated-slider-card:hover, .animated-slider-card.dragging {
    border-color: rgba(255, 255, 255, 0.15);
  }

  .slider-track-wrap {
    position: relative;
    width: 100%;
    height: 32px;
    display: flex;
    align-items: center;
  }

  /* Floating Tooltip with Smooth Gliding Animation */
  .slider-floating-tooltip {
    position: absolute;
    top: -12px;
    transform: translate(-50%, -100%);
    pointer-events: none;
    z-index: 10;
    transition: left 0.22s cubic-bezier(0.34, 1.45, 0.64, 1);
    animation: tooltipBob 2.5s ease-in-out infinite;
  }

  @keyframes tooltipBob {
    0%, 100% { transform: translate(-50%, -100%) translateY(0); }
    50% { transform: translate(-50%, -100%) translateY(-3px); }
  }

  .tooltip-bubble {
    display: flex;
    align-items: center;
    gap: 5px;
    background: rgba(14, 19, 29, 0.95);
    border: 1px solid var(--accent-primary);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6), 0 0 12px var(--accent-glow);
    padding: 3px 9px;
    border-radius: 12px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    color: var(--accent-primary);
    white-space: nowrap;
  }

  .tooltip-caret {
    width: 0;
    height: 0;
    margin: 0 auto;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid var(--accent-primary);
  }

  /* Base Track Bar */
  .slider-track-bar {
    position: relative;
    width: 100%;
    height: 8px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.6);
    overflow: visible;
  }

  /* Shimmer Fill Bar */
  .slider-track-fill {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(
      90deg, 
      var(--accent-primary) 0%, 
      var(--accent-secondary) 50%, 
      var(--accent-primary) 100%
    );
    background-size: 200% 100%;
    animation: trackShimmer 3s linear infinite;
    box-shadow: 0 0 14px var(--accent-glow);
    transition: width 0.22s cubic-bezier(0.34, 1.45, 0.64, 1);
  }

  @keyframes trackShimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .fill-lead-glow {
    position: absolute;
    top: -2px;
    right: -2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #ffffff;
    filter: blur(1px);
    opacity: 0.8;
  }

  /* Rendered Thumb with Pulsing Halo */
  .slider-thumb-render {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 22px;
    height: 22px;
    pointer-events: none;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: left 0.22s cubic-bezier(0.34, 1.45, 0.64, 1);
  }

  .thumb-halo {
    position: absolute;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--accent-glow);
    animation: thumbPulse 2s ease-in-out infinite;
  }

  @keyframes thumbPulse {
    0%, 100% {
      transform: scale(0.9);
      opacity: 0.6;
    }
    50% {
      transform: scale(1.3);
      opacity: 0.2;
    }
  }

  .thumb-core {
    position: relative;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #ffffff;
    border: 3px solid var(--accent-primary);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6), 0 0 14px var(--accent-primary);
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .animated-slider-card:hover .thumb-core,
  .animated-slider-card.dragging .thumb-core {
    transform: scale(1.15);
  }

  /* Native Range Input (Transparent, accessible layer on top) */
  .slider-native-input {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
    z-index: 20;
    margin: 0;
  }

  /* Stepped Pip Markers (1 to 6) */
  .slider-pips-row {
    display: flex;
    justify-content: space-between;
    padding: 0 4px;
    position: relative;
  }

  .slider-pip-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 2px 8px;
    transition: all 0.2s ease;
  }

  .pip-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.18);
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .slider-pip-btn.active .pip-dot {
    background: var(--accent-primary);
    box-shadow: 0 0 8px var(--accent-primary);
  }

  .slider-pip-btn.current .pip-dot {
    transform: scale(1.35);
    background: #ffffff;
    border: 2px solid var(--accent-primary);
    box-shadow: 0 0 12px var(--accent-primary);
  }

  .pip-label {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    transition: color 0.2s ease;
  }

  .slider-pip-btn.active .pip-label {
    color: var(--text-primary);
  }

  .slider-pip-btn.current .pip-label {
    color: var(--accent-primary);
    font-weight: 700;
  }

  .slider-pip-btn:hover .pip-dot {
    transform: scale(1.2);
  }

  /* Performance Tier Intelligence Info */
  .slider-tier-info {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    font-size: 11px;
  }

  .tier-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 700;
    white-space: nowrap;
    letter-spacing: 0.04em;
  }

  .tier-eco {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .tier-balanced {
    background: rgba(6, 182, 212, 0.15);
    color: #06b6d4;
    border: 1px solid rgba(6, 182, 212, 0.3);
  }

  .tier-turbo {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .tier-desc {
    color: var(--text-muted);
    font-size: 11px;
    line-height: 1.35;
  }

  /* ========================================================
     MODERN CYBER TOGGLE SWITCHES
     ======================================================== */
  .toggles-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .toggle-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 14px;
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .toggle-card:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.14);
  }

  .toggle-card-left {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    padding-right: 14px;
  }

  .toggle-icon-wrap {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.2s ease;
  }

  .toggle-icon-wrap.active {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.25);
    box-shadow: 0 0 10px var(--accent-glow);
  }

  .toggle-content {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .toggle-title {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-primary);
  }

  /* Cyber Pill Switch */
  .cyber-switch {
    width: 44px;
    height: 24px;
    position: relative;
    cursor: pointer;
    flex-shrink: 0;
  }

  .switch-track {
    width: 100%;
    height: 100%;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.14);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
  }

  .cyber-switch.checked .switch-track {
    background: var(--accent-gradient);
    border-color: var(--accent-primary);
    box-shadow: 0 0 12px var(--accent-glow);
  }

  .switch-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #ffffff;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.5);
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), width 0.15s ease;
  }

  .cyber-switch.checked .switch-thumb {
    transform: translateX(20px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6), 0 0 6px rgba(255, 255, 255, 0.8);
  }

  /* JDownloader 2 Port Module */
  .jd-port-card {
    cursor: default;
  }

  .port-control-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .port-prefix-label {
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 700;
    color: var(--text-muted);
  }

  .port-input {
    width: 84px;
    text-align: center;
    font-family: var(--font-mono);
    font-size: 12px;
    padding: 6px 8px;
  }

  .btn-reset-port {
    font-size: 10.5px;
    font-weight: 600;
    padding: 4px 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-subtle);
    border-radius: 4px;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-reset-port:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.1);
  }

  /* Version & Updates Card */
  .version-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 16px;
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    gap: 12px;
  }

  .version-meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .version-name-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .app-title {
    font-size: 13.5px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .badge-ver {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-primary);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .engine-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--accent-secondary);
    background: rgba(6, 182, 212, 0.12);
    border: 1px solid rgba(6, 182, 212, 0.25);
    padding: 2px 7px;
    border-radius: 4px;
  }

  .version-author {
    font-size: 11px;
    color: var(--text-muted);
  }

  .btn-check-updates {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 11.5px;
    padding: 8px 14px;
    white-space: nowrap;
    border-radius: 6px;
    cursor: pointer;
  }

  .spin {
    display: inline-flex;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .community-actions-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .community-actions-row .btn-secondary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    font-size: 12px;
    padding: 9px 14px;
    border-radius: 6px;
    cursor: pointer;
  }

  /* Modal Footer */
  .modal-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 10px;
    padding: 16px 22px;
    border-top: 1px solid var(--border-subtle);
    background: rgba(255, 255, 255, 0.01);
  }

  .btn-footer-cancel {
    padding: 9px 18px;
    font-size: 12.5px;
    border-radius: var(--radius-sm);
    cursor: pointer;
  }

  .btn-footer-save {
    padding: 9px 20px;
    font-size: 12.5px;
    border-radius: var(--radius-sm);
    box-shadow: 0 0 16px var(--accent-glow);
    cursor: pointer;
  }
</style>
