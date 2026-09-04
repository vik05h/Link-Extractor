<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, playSuccessChime } from '../utils/audio';

  export let isOpen: boolean = false;
  export let releaseInfo: any = null;
  export let isFrozen: boolean = false;
  export let currentVersion: string = 'v3.8.0';
  export let onClose: () => void = () => {};
  export let onShowToast: (msg: string) => void = () => {};

  let step: 'prompt' | 'downloading' | 'ready' | 'error' = 'prompt';
  let percent: number = 0;
  let downloadedStr: string = '0 MB';
  let totalStr: string = '68 MB';
  let speedStr: string = 'Connecting...';
  let errorMessage: string = '';
  let autoRestartCountdown: number = 3;
  let countdownTimer: any = null;

  function resetState() {
    step = 'prompt';
    percent = 0;
    downloadedStr = '0 MB';
    totalStr = '68 MB';
    speedStr = 'Connecting...';
    errorMessage = '';
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }

  $: if (!isOpen) {
    resetState();
  }

  onMount(() => {
    function onProgress(e: CustomEvent) {
      const d = e.detail;
      if (d) {
        step = 'downloading';
        percent = d.percent || 0;
        downloadedStr = d.downloaded_str || '0 MB';
        totalStr = d.total_str || 'Unknown';
        speedStr = d.speed_str || 'Downloading...';
      }
    }

    function onComplete(e: CustomEvent) {
      const d = e.detail;
      step = 'ready';
      playSuccessChime();
      onShowToast('Update downloaded successfully!');
      
      if (isFrozen) {
        autoRestartCountdown = 3;
        countdownTimer = setInterval(() => {
          autoRestartCountdown -= 1;
          if (autoRestartCountdown <= 0) {
            clearInterval(countdownTimer);
            countdownTimer = null;
            applyRestart();
          }
        }, 1000);
      }
    }

    function onCancelled() {
      resetState();
      onShowToast('Update download cancelled.');
    }

    function onError(e: CustomEvent) {
      step = 'error';
      errorMessage = e.detail?.error || 'Download failed. Please check your internet connection.';
    }

    window.addEventListener('updater:progress' as any, onProgress);
    window.addEventListener('updater:download_complete' as any, onComplete);
    window.addEventListener('updater:download_cancelled' as any, onCancelled);
    window.addEventListener('updater:error' as any, onError);

    return () => {
      window.removeEventListener('updater:progress' as any, onProgress);
      window.removeEventListener('updater:download_complete' as any, onComplete);
      window.removeEventListener('updater:download_cancelled' as any, onCancelled);
      window.removeEventListener('updater:error' as any, onError);
      if (countdownTimer) clearInterval(countdownTimer);
    };
  });

  function startDownload() {
    playClickSound();
    step = 'downloading';
    percent = 1;
    speedStr = 'Starting download...';
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.start_update_download) {
      const url = releaseInfo?.download_url || '';
      (window as any).pywebview.api.start_update_download(url);
    }
  }

  function cancelDownload() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.cancel_update_download) {
      (window as any).pywebview.api.cancel_update_download();
    }
    resetState();
  }

  function applyRestart() {
    playClickSound();
    if (countdownTimer) clearInterval(countdownTimer);
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.apply_update_and_restart) {
      (window as any).pywebview.api.apply_update_and_restart();
    }
  }

  function launchDownloaded() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.launch_downloaded_binary) {
      (window as any).pywebview.api.launch_downloaded_binary();
    }
    onClose();
  }

  function openUpdatesFolder() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.open_updates_folder) {
      (window as any).pywebview.api.open_updates_folder();
    }
  }

  function openReleasePage() {
    playClickSound();
    const url = releaseInfo?.html_url || 'https://github.com/vik05h/Link-Extractor/releases';
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.open_external_url) {
      (window as any).pywebview.api.open_external_url(url);
    } else {
      window.open(url, '_blank');
    }
  }

  function formatBody(bodyText: string): string {
    if (!bodyText) return 'No release highlights provided.';
    return bodyText
      .replace(/^### (.*$)/gim, '<strong>$1</strong>')
      .replace(/^## (.*$)/gim, '<strong>$1</strong>')
      .replace(/^\* (.*$)/gim, '• $1')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  }
</script>

{#if isOpen}
  <div 
    class="modal-backdrop" 
    role="dialog" 
    aria-modal="true"
    on:keydown={(e) => e.key === 'Escape' && step !== 'downloading' && onClose()}
  >
    <div class="modal-card glass-panel" role="document">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-left">
          <div class="header-icon-halo">
            <Icon name="bolt" size={18} color="var(--accent-primary)" />
          </div>
          <div>
            <div class="modal-title">IN-APP AUTOMATIC UPDATER</div>
            <div class="modal-subtitle">Direct standalone update via GitHub Releases</div>
          </div>
        </div>

        {#if step !== 'downloading'}
          <button type="button" class="btn-close" aria-label="Close dialog" on:click={onClose}>
            <Icon name="close" size={16} />
          </button>
        {/if}
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        {#if step === 'prompt'}
          <!-- Version Comparison Banner -->
          <div class="version-banner glass-card">
            <div class="version-badge-group">
              <span class="badge badge-tag current-tag">Current: {currentVersion}</span>
              <span class="arrow-indicator">→</span>
              <span class="badge badge-tag latest-tag">Latest: {releaseInfo?.latest_version || 'v4.0.0'}</span>
            </div>
            <div class="release-name">{releaseInfo?.name || 'New Release Available'}</div>
          </div>

          <!-- Release Notes / Highlights Container -->
          <div class="highlights-box">
            <div class="highlights-header">
              <Icon name="sparkles" size={14} color="var(--accent-primary)" />
              <span>RELEASE HIGHLIGHTS & CHANGELOG</span>
            </div>
            <div class="highlights-scroll font-mono">
              {@html formatBody(releaseInfo?.body || '')}
            </div>
          </div>

          <!-- Metadata Pill Row -->
          <div class="meta-row">
            <div class="meta-pill">
              <Icon name="package" size={13} color="var(--text-muted)" />
              <span>Size: <strong>{releaseInfo?.asset_size ? `${(releaseInfo.asset_size / 1048576).toFixed(1)} MB` : '~65 MB'}</strong></span>
            </div>
            <div class="meta-pill">
              <Icon name="hard-drive" size={13} color="var(--text-muted)" />
              <span>Type: <strong>{isFrozen ? 'Windows Standalone .exe' : 'Development Mode'}</strong></span>
            </div>
            <button type="button" class="btn-text-link" on:click={openReleasePage}>
              <Icon name="external-link" size={12} />
              <span>View on GitHub</span>
            </button>
          </div>

        {:else if step === 'downloading'}
          <!-- Active Download HUD -->
          <div class="download-hud glass-card">
            <div class="hud-top-row">
              <div class="hud-status-indicator">
                <span class="spin-radar"></span>
                <span>DOWNLOADING UPDATE BINARY...</span>
              </div>
              <div class="hud-percent font-mono">{percent.toFixed(0)}%</div>
            </div>

            <!-- Progress Bar -->
            <div class="progress-bar-track">
              <div class="progress-bar-fill" style="width: {percent}%;">
                <div class="progress-bar-head"></div>
              </div>
            </div>

            <!-- Download Stats Row -->
            <div class="hud-stats-row font-mono">
              <span>{downloadedStr} / {totalStr}</span>
              <span class="hud-speed">{speedStr}</span>
            </div>
          </div>

        {:else if step === 'ready'}
          <!-- Ready / Restart State -->
          <div class="ready-banner glass-card">
            <div class="ready-icon-halo">
              <Icon name="check-circle" size={36} color="var(--status-fresh)" />
            </div>
            <h3>Update Downloaded & Verified!</h3>
            {#if isFrozen}
              <p class="ready-subtext">
                The new version is ready. Restarting application in <strong class="accent-text">{autoRestartCountdown}s</strong> to apply update...
              </p>
            {:else}
              <p class="ready-subtext">
                The standalone executable has been downloaded to your persistent updates folder. You can launch it directly or continue developing.
              </p>
            {/if}
          </div>

        {:else if step === 'error'}
          <!-- Error State -->
          <div class="error-banner glass-card">
            <div class="error-icon-halo">
              <Icon name="alert-triangle" size={32} color="var(--status-expired)" />
            </div>
            <h3>Update Failed</h3>
            <p class="error-subtext">{errorMessage}</p>
          </div>
        {/if}
      </div>

      <!-- Modal Footer Controls -->
      <div class="modal-footer">
        {#if step === 'prompt'}
          <button type="button" class="btn-secondary" on:click={onClose}>
            <span>Remind Me Later</span>
          </button>
          <button type="button" class="btn-primary btn-glow" on:click={startDownload}>
            <Icon name="download" size={16} />
            <span>Update Now (1-Click)</span>
          </button>

        {:else if step === 'downloading'}
          <button type="button" class="btn-secondary btn-cancel" on:click={cancelDownload}>
            <Icon name="close" size={14} color="var(--status-expired)" />
            <span>Cancel Download</span>
          </button>

        {:else if step === 'ready'}
          {#if isFrozen}
            <button type="button" class="btn-primary btn-glow" on:click={applyRestart}>
              <Icon name="refresh" size={16} />
              <span>Restart Now</span>
            </button>
          {:else}
            <button type="button" class="btn-secondary" on:click={openUpdatesFolder}>
              <Icon name="package" size={15} />
              <span>Open Folder</span>
            </button>
            <button type="button" class="btn-primary" on:click={launchDownloaded}>
              <Icon name="bolt" size={15} />
              <span>Launch New Binary</span>
            </button>
            <button type="button" class="btn-secondary" on:click={onClose}>
              <span>Close</span>
            </button>
          {/if}

        {:else if step === 'error'}
          <button type="button" class="btn-secondary" on:click={openReleasePage}>
            <Icon name="external-link" size={14} />
            <span>GitHub Releases</span>
          </button>
          <button type="button" class="btn-primary" on:click={startDownload}>
            <Icon name="refresh" size={15} />
            <span>Retry Download</span>
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 10000;
    background: rgba(4, 6, 10, 0.75);
    backdrop-filter: blur(14px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: fadeIn 0.2s ease-out;
  }

  .modal-card {
    width: 560px;
    max-width: 95vw;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-hover);
    border-radius: var(--radius-lg);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px var(--accent-glow);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: scaleIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-icon-halo {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-title {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.8px;
    color: var(--text-primary);
  }

  .modal-subtitle {
    font-size: 11px;
    color: var(--text-muted);
  }

  .btn-close {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 6px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .btn-close:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.08);
  }

  .modal-body {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* Version Banner */
  .version-banner {
    padding: 14px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .version-badge-group {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .badge-tag {
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
    border-radius: 6px;
  }

  .current-tag {
    background: rgba(255, 255, 255, 0.06);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
  }

  .latest-tag {
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-primary);
    border: 1px solid rgba(16, 185, 129, 0.4);
    box-shadow: 0 0 10px var(--accent-glow);
  }

  .arrow-indicator {
    color: var(--text-muted);
    font-size: 12px;
  }

  .release-name {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
  }

  /* Highlights Box */
  .highlights-box {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .highlights-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
    color: var(--accent-primary);
  }

  .highlights-scroll {
    max-height: 140px;
    overflow-y: auto;
    padding: 12px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    font-size: 11.5px;
    line-height: 1.6;
    color: var(--text-secondary);
    white-space: pre-line;
  }

  /* Metadata Row */
  .meta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
    font-size: 11.5px;
  }

  .meta-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--text-secondary);
  }

  .meta-pill strong {
    color: var(--text-primary);
  }

  .btn-text-link {
    background: transparent;
    border: none;
    color: var(--accent-primary);
    font-size: 11.5px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .btn-text-link:hover {
    color: #ffffff;
  }

  /* Download HUD */
  .download-hud {
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-hover);
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .hud-top-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .hud-status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.6px;
    color: var(--accent-primary);
  }

  .spin-radar {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent-primary);
    box-shadow: 0 0 10px var(--accent-primary);
    animation: radarPulse 1.2s infinite;
  }

  .hud-percent {
    font-size: 20px;
    font-weight: 800;
    color: var(--text-primary);
  }

  .progress-bar-track {
    width: 100%;
    height: 10px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    overflow: hidden;
    position: relative;
  }

  .progress-bar-fill {
    height: 100%;
    background: var(--accent-gradient);
    border-radius: 6px;
    position: relative;
    transition: width 0.2s ease-out;
    box-shadow: 0 0 16px var(--accent-glow);
  }

  .progress-bar-head {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: #ffffff;
    box-shadow: 0 0 8px #ffffff;
  }

  .hud-stats-row {
    display: flex;
    justify-content: space-between;
    font-size: 11.5px;
    color: var(--text-secondary);
  }

  .hud-speed {
    color: var(--accent-secondary);
    font-weight: 600;
  }

  /* Ready & Error Banners */
  .ready-banner, .error-banner {
    padding: 24px 20px;
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 10px;
  }

  .ready-banner {
    background: rgba(16, 185, 129, 0.05);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .error-banner {
    background: rgba(244, 63, 94, 0.05);
    border: 1px solid rgba(244, 63, 94, 0.3);
  }

  .ready-icon-halo, .error-icon-halo {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ready-icon-halo {
    background: rgba(16, 185, 129, 0.12);
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
  }

  .error-icon-halo {
    background: rgba(244, 63, 94, 0.12);
    box-shadow: 0 0 20px rgba(244, 63, 94, 0.3);
  }

  .ready-subtext, .error-subtext {
    font-size: 12.5px;
    color: var(--text-secondary);
    max-width: 420px;
    line-height: 1.5;
  }

  .accent-text {
    color: var(--accent-primary);
  }

  /* Modal Footer */
  .modal-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    padding: 16px 20px;
    border-top: 1px solid var(--border-subtle);
    background: rgba(0, 0, 0, 0.2);
  }

  .btn-glow {
    box-shadow: 0 0 16px var(--accent-glow);
  }

  .btn-cancel {
    border-color: rgba(244, 63, 94, 0.3);
    color: var(--status-expired);
  }

  .btn-cancel:hover {
    background: rgba(244, 63, 94, 0.12);
  }

  @keyframes radarPulse {
    0% { transform: scale(0.9); opacity: 0.6; }
    50% { transform: scale(1.3); opacity: 1; }
    100% { transform: scale(0.9); opacity: 0.6; }
  }

  @keyframes scaleIn {
    from { transform: scale(0.95); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>
