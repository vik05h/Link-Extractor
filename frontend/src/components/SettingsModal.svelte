<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, toggleAudioMute, isAudioMuted } from '../utils/audio';
  import type { AppSettings } from '../types';

  export let isOpen: boolean = false;
  export let onClose: () => void = () => {};
  export let onThemeChange: (theme: string) => void = () => {};
  export let onCheckUpdates: () => void = () => {};
  export let currentVersion: string = 'v4.0.0';

  let currentTheme = 'cyber';
  let isCheckingUpdates = false;
  let concurrency = 3;
  let autoValidate = true;
  let jdPort = 9666;
  let autoUpload = true;
  let clipboardSentinel = true;
  let soundEnabled = true;

  onMount(() => {
    if (typeof window !== 'undefined') {
      currentTheme = localStorage.getItem('app_theme') || 'cyber';
      soundEnabled = !isAudioMuted();

      if ((window as any).pywebview) {
        (window as any).pywebview.api.get_settings().then((s: AppSettings) => {
          if (s) {
            concurrency = s.concurrency || 3;
            autoValidate = s.auto_validate ?? true;
            jdPort = s.jd_port || 9666;
            autoUpload = s.community_auto_upload ?? true;
            clipboardSentinel = s.clipboard_sentinel_enabled ?? true;
          }
        });
      }
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

  function saveSettings() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.save_settings({
        concurrency,
        auto_validate: autoValidate,
        jd_port: jdPort,
        community_auto_upload: autoUpload,
        clipboard_sentinel_enabled: clipboardSentinel
      }).then(() => {
        onClose();
      });
    } else {
      onClose();
    }
  }
</script>

{#if isOpen}
  <div class="modal-backdrop" on:click={onClose} role="dialog" aria-modal="true">
    <div class="modal-card glass-panel" on:click|stopPropagation role="document">
      <div class="modal-header">
        <div class="modal-title">
          <Icon name="settings" size={16} color="var(--accent-primary)" />
          <span>ENGINE & UI CONFIGURATION</span>
        </div>
        <button type="button" class="btn-close" on:click={onClose} aria-label="Close dialog">
          <Icon name="close" size={16} />
        </button>
      </div>

      <div class="modal-body">
        <!-- Theme Selector -->
        <div class="setting-group">
          <span class="setting-label">VISUAL THEME & PALETTE</span>
          <div class="theme-options-grid">
            <button 
              type="button"
              class="theme-card" 
              class:selected={currentTheme === 'cyber'}
              on:click={() => handleThemeSelect('cyber')}
            >
              <div class="theme-swatch cyber-swatch"></div>
              <div class="theme-name">Cyber-Dark</div>
              <div class="theme-desc">Neon Emerald & OLED Black</div>
            </button>

            <button 
              type="button"
              class="theme-card" 
              class:selected={currentTheme === 'steam'}
              on:click={() => handleThemeSelect('steam')}
            >
              <div class="theme-swatch steam-swatch"></div>
              <div class="theme-name">Steam Slate</div>
              <div class="theme-desc">Obsidian & Electric Blue</div>
            </button>

            <button 
              type="button"
              class="theme-card" 
              class:selected={currentTheme === 'adaptive'}
              on:click={() => handleThemeSelect('adaptive')}
            >
              <div class="theme-swatch adaptive-swatch"></div>
              <div class="theme-name">Dynamic Adaptive</div>
              <div class="theme-desc">Samples Active Game Art</div>
            </button>
          </div>
        </div>

        <!-- Concurrency Slider -->
        <div class="setting-group">
          <div class="setting-row">
            <div>
              <label for="concurrency-slider" class="setting-label">PLAYWRIGHT WORKER POOL</label>
              <div class="setting-subtext">Number of parallel browser tabs solving Cloudflare Turnstile</div>
            </div>
            <span class="setting-val-badge">{concurrency} Tabs</span>
          </div>
          <input 
            id="concurrency-slider"
            type="range" 
            min="1" 
            max="6" 
            step="1" 
            bind:value={concurrency}
            class="range-slider"
          />
        </div>

        <!-- Switches -->
        <div class="setting-group">
          <span class="setting-label">INTEGRATIONS & HAPTICS</span>

          <label class="setting-toggle-row" for="auto-validate-toggle">
            <div>
              <div class="toggle-title">Instant 1-Byte Size Validation</div>
              <div class="setting-subtext">Rapidly aggregates exact repack sizes via HTTP Range requests</div>
            </div>
            <input id="auto-validate-toggle" type="checkbox" bind:checked={autoValidate} class="toggle-checkbox" />
          </label>

          <label class="setting-toggle-row" for="clipboard-sentinel-toggle">
            <div>
              <div class="toggle-title">Clipboard Sentinel</div>
              <div class="setting-subtext">Background desktop notification when copying FitGirl links</div>
            </div>
            <input id="clipboard-sentinel-toggle" type="checkbox" bind:checked={clipboardSentinel} class="toggle-checkbox" />
          </label>

          <label class="setting-toggle-row" for="audio-haptics-toggle">
            <div>
              <div class="toggle-title">Gaming Audio Haptics</div>
              <div class="setting-subtext">Subtle synthesized micro-sounds on Turnstile resolution & completion</div>
            </div>
            <input id="audio-haptics-toggle" type="checkbox" checked={soundEnabled} on:change={handleSoundToggle} class="toggle-checkbox" />
          </label>

          <label class="setting-toggle-row" for="auto-upload-toggle">
            <div>
              <div class="toggle-title">Auto-Publish to Community Cloud</div>
              <div class="setting-subtext">Share resolved links anonymously to save time for other gamers</div>
            </div>
            <input id="auto-upload-toggle" type="checkbox" bind:checked={autoUpload} class="toggle-checkbox" />
          </label>

          <div class="setting-toggle-row">
            <div>
              <label for="jd-port-input" class="toggle-title">JDownloader 2 FlashGot Port</label>
              <div class="setting-subtext">Default local port is 9666</div>
            </div>
            <input 
              id="jd-port-input"
              type="number" 
              bind:value={jdPort} 
              class="glass-input port-input" 
              style="width: 90px;" 
            />
          </div>
        </div>

        <!-- Version & Updates Card -->
        <div class="setting-group">
          <span class="setting-label">VERSION & UPDATES</span>
          <div class="version-card glass-panel">
            <div class="version-meta">
              <div class="version-name-row">
                <span class="app-title">Link Extractor</span>
                <span class="badge-ver">{currentVersion}</span>
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
        </div>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn-primary" on:click={saveSettings}>
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
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }

  .modal-card {
    width: 580px;
    max-width: 95%;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    background: rgba(14, 18, 27, 0.96);
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .modal-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--accent-primary);
  }

  .btn-close {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .btn-close:hover {
    color: var(--text-primary);
  }

  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .setting-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .setting-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--accent-primary);
    letter-spacing: 0.8px;
  }

  .setting-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .setting-subtext {
    font-size: 11px;
    color: var(--text-muted);
  }

  .setting-val-badge {
    font-size: 11px;
    font-weight: 700;
    color: var(--accent-secondary);
    background: rgba(6, 182, 212, 0.15);
    padding: 3px 8px;
    border-radius: 6px;
  }

  /* Theme Cards */
  .theme-options-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
  }

  .theme-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 12px;
    border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .theme-card:hover {
    background: rgba(255, 255, 255, 0.08);
  }

  .theme-card.selected {
    border-color: var(--accent-primary);
    background: rgba(16, 185, 129, 0.12);
    box-shadow: 0 0 14px var(--accent-glow);
  }

  .theme-swatch {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    margin-bottom: 8px;
  }

  .cyber-swatch { background: linear-gradient(135deg, #10b981, #06b6d4); }
  .steam-swatch { background: linear-gradient(135deg, #38bdf8, #1b2838); }
  .adaptive-swatch { background: conic-gradient(#f43f5e, #eab308, #10b981, #06b6d4, #8b5cf6, #f43f5e); }

  .theme-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .theme-desc {
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 2px;
  }

  .range-slider {
    width: 100%;
    accent-color: var(--accent-primary);
    margin-top: 6px;
  }

  .setting-toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    cursor: pointer;
  }

  .toggle-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .toggle-checkbox {
    width: 18px;
    height: 18px;
    accent-color: var(--accent-primary);
    cursor: pointer;
  }

  .port-input {
    text-align: center;
    font-family: var(--font-mono);
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    padding: 16px 20px;
    border-top: 1px solid var(--border-subtle);
  }

  /* Version & Updates Card */
  .version-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 14px;
    background: rgba(255, 255, 255, 0.03);
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
  }

  .app-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .badge-ver {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-primary);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .version-author {
    font-size: 11px;
    color: var(--text-muted);
  }

  .btn-check-updates {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11.5px;
    padding: 7px 12px;
    white-space: nowrap;
    border-radius: 6px;
  }

  .spin {
    display: inline-flex;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
