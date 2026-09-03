<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import LivingCanvas from './LivingCanvas.svelte';
  import GameStage from './GameStage.svelte';
  import DiscoveryHub, { type GameRecord } from './DiscoveryHub.svelte';
  import SettingsModal from './SettingsModal.svelte';
  import HistoryModal from './HistoryModal.svelte';
  import ClipboardSentinel from './ClipboardSentinel.svelte';
  import Icon from './icons/Icon.svelte';
  import type { PartItem } from './DefragMosaic.svelte';
  import { playClickSound, playSuccessChime, toggleAudioMute, isAudioMuted } from '../utils/audio';

  // Navigation View: 'community' or 'stage'
  let currentView: 'community' | 'stage' = 'community';

  // Active Game State
  let gameTitle = 'FitGirl Game Repack';
  let coverUrl = '';
  let sourceUrl = '';
  let totalSizeStr = '0 B';
  let isRunning = false;
  let statusMessage = 'Paste any FitGirl URL or click a Community Repack to begin.';
  let parts: PartItem[] = [];
  let logs: string[] = ['[System] Link Extractor v4.0 Turbo Engine initialized.'];

  // Community Feed State
  let communityGames: GameRecord[] = [];
  let isCommunityLoading = false;

  // Modals & Sound
  let settingsOpen = false;
  let historyOpen = false;
  let audioMuted = false;
  let currentTheme = 'cyber';

  // URL Input
  let inputUrl = '';
  let detectedType = '';
  let urlInputEl: HTMLInputElement;

  // Toast Notification
  let toastMessage = '';
  let toastTimeout: any = null;

  function showToast(msg: string) {
    toastMessage = msg;
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => { toastMessage = ''; }, 4000);
  }

  // Handle URL change
  function handleUrlInput() {
    const raw = inputUrl.trim();
    if (!raw) {
      detectedType = '';
      return;
    }
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.detect_url(raw).then((res: any) => {
        detectedType = res.url_type || '';
      });
    }
  }

  // Start Extraction
  function startExtraction(urlToExtract?: string) {
    const target = (urlToExtract || inputUrl).trim();
    if (!target) {
      showToast('Please paste a valid FitGirl game or pastebin URL.');
      return;
    }

    playClickSound();
    isRunning = true;
    currentView = 'stage';
    sourceUrl = target;
    statusMessage = 'Connecting to high-speed resolution pool...';
    parts = [];
    logs = [`[Pipeline] Starting multi-tab extraction for: ${target}`];

    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.start_extraction(target);
    }
  }

  function handleCancelExtraction() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.cancel_pipeline();
    }
  }

  // Load Community Record directly into Stage
  function handleLoadCommunityRecord(rec: GameRecord) {
    gameTitle = rec.title;
    coverUrl = rec.image_url;
    sourceUrl = rec.source_url;
    totalSizeStr = rec.total_size_str;
    currentView = 'stage';
    statusMessage = 'Loaded instant pre-fetched direct links from Community Cache!';

    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.get_game_urls(rec.slug).then((urls: string[]) => {
        parts = (urls || []).map((u, i) => ({
          index: i + 1,
          url: u,
          direct_url: u,
          filename: u.includes('#') ? u.split('#').pop() : `Part ${i + 1}`,
          status: 'resolved',
          size: rec.total_size_str
        }));
        logs = [`[Community] Loaded ${urls.length} verified direct links for ${rec.title}`];
        showToast(`Loaded ${rec.title} with 0s wait!`);
      });
    }
  }

  // Load History Item directly into Stage
  function handleLoadHistoryRecord(rec: any) {
    gameTitle = rec.game_title;
    coverUrl = '';
    sourceUrl = rec.source_url;
    totalSizeStr = rec.total_size || '0 B';
    currentView = 'stage';
    statusMessage = 'Loaded from local SQLite archive';

    parts = (rec.resolved_links || []).map((u: string, i: number) => ({
      index: i + 1,
      url: u,
      direct_url: u,
      filename: u.includes('#') ? u.split('#').pop() : `Part ${i + 1}`,
      status: 'resolved',
      size: rec.total_size || ''
    }));
    logs = [`[Archive] Loaded ${rec.resolved_links.length} links for ${rec.game_title}`];
    showToast(`Loaded ${rec.game_title} from History!`);
  }

  // Push to JDownloader 2
  function handlePushToJd2(urls: string[], title: string) {
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.push_to_jd2(urls, title, sourceUrl).then((res: any) => {
        showToast(res.message || 'Pushed to JDownloader 2!');
      });
    }
  }

  // Export URLs
  function handleExport(format: 'txt' | 'json' | 'crawljob', urls: string[], title: string) {
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.export_urls(format, urls, title, totalSizeStr).then((res: any) => {
        showToast(res.message || 'Export complete!');
      });
    }
  }

  // Copy all direct URLs
  function handleCopyAll(urls: string[]) {
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.copy_to_clipboard(urls.join('\n')).then(() => {
        showToast(`Copied all ${urls.length} direct links to clipboard!`);
      });
    }
  }

  // Refresh Community Feed
  function refreshCommunity() {
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      isCommunityLoading = true;
      (window as any).pywebview.api.get_community_feed().then((data: GameRecord[]) => {
        communityGames = data || [];
        isCommunityLoading = false;
      });
    }
  }

  // Global Keyboard Shortcuts
  function handleGlobalKeydown(e: KeyboardEvent) {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      if (e.key === 'Escape') {
        settingsOpen = false;
        historyOpen = false;
      }
      return;
    }

    if (e.key === 'Escape') {
      settingsOpen = false;
      historyOpen = false;
    } else if ((e.ctrlKey || e.metaKey) && e.key === '1') {
      e.preventDefault();
      currentView = 'community';
    } else if ((e.ctrlKey || e.metaKey) && e.key === '2') {
      e.preventDefault();
      currentView = 'stage';
    } else if ((e.ctrlKey || e.metaKey) && e.key === '3') {
      e.preventDefault();
      historyOpen = true;
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'j') {
      e.preventDefault();
      if (parts.length > 0) {
        const resolved = parts.filter(p => !p.excluded && (p.direct_url || p.url)).map(p => p.direct_url || p.url);
        handlePushToJd2(resolved, gameTitle);
      }
    }
  }

  // Python Event Listeners
  function setupEventListeners() {
    window.addEventListener('pipeline:status' as any, (e: CustomEvent) => {
      if (e.detail?.message) {
        statusMessage = e.detail.message;
        logs = [...logs, `[Status] ${e.detail.message}`];
      }
    });

    window.addEventListener('pipeline:game_meta' as any, (e: CustomEvent) => {
      if (e.detail?.title) gameTitle = e.detail.title;
      if (e.detail?.image_url) coverUrl = e.detail.image_url;
      logs = [...logs, `[Meta] Detected: ${e.detail.title} (${e.detail.parts_count} parts)`];
    });

    window.addEventListener('pipeline:init_parts' as any, (e: CustomEvent) => {
      if (e.detail) {
        parts = e.detail;
      }
    });

    window.addEventListener('pipeline:part_update' as any, (e: CustomEvent) => {
      const p = e.detail;
      if (!p) return;
      
      // Update matching part by part_name or index
      parts = parts.map(item => {
        if (p.part_name && item.filename === p.part_name) {
          return {
            ...item,
            status: p.status === 'resolved' ? 'resolved' : (p.status === 'failed' ? 'failed' : 'decrypting'),
            direct_url: p.direct_url || item.direct_url
          };
        }
        return item;
      });
      logs = [...logs, `[Worker] ${p.part_name || 'Part'}: ${p.status?.toUpperCase()} (${p.avg_speed || ''} | ETA: ${p.eta || ''})`];
    });

    window.addEventListener('pipeline:val_update' as any, (e: CustomEvent) => {
      const v = e.detail;
      if (v) {
        logs = [...logs, `[Validator] Verified: ${v.current}/${v.total} (${v.size})`];
      }
    });

    window.addEventListener('pipeline:complete' as any, (e: CustomEvent) => {
      const d = e.detail;
      isRunning = false;
      statusMessage = `Verified 100% of parts (${d.total_size_str})! Direct links ready.`;
      if (d.total_size_str) totalSizeStr = d.total_size_str;
      logs = [...logs, `[Complete] Verified ${d.parts_count} direct download URLs! Total Repack Size: ${d.total_size_str}`];
      playSuccessChime();
      showToast(`100% Verified! ${d.parts_count} parts ready (${d.total_size_str})`);
    });

    window.addEventListener('pipeline:cancelled' as any, () => {
      isRunning = false;
      statusMessage = 'Extraction cancelled.';
      logs = [...logs, `[Cancelled] Stopped by user.`];
      showToast('Extraction cancelled.');
    });

    window.addEventListener('pipeline:error' as any, (e: CustomEvent) => {
      isRunning = false;
      statusMessage = `Error: ${e.detail?.message || 'Failed'}`;
      logs = [...logs, `[Error] ${e.detail?.message}`];
      showToast(`Error: ${e.detail?.message}`);
    });
  }

  onMount(() => {
    if (typeof window !== 'undefined') {
      currentTheme = localStorage.getItem('app_theme') || 'cyber';
      document.documentElement.setAttribute('data-theme', currentTheme);
      audioMuted = isAudioMuted();

      setupEventListeners();
      window.addEventListener('keydown', handleGlobalKeydown);

      const checkBridge = setInterval(() => {
        if ((window as any).pywebview && (window as any).pywebview.api) {
          clearInterval(checkBridge);
          refreshCommunity();
        }
      }, 100);
    }
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', handleGlobalKeydown);
    }
  });
</script>

<div class="app-layout-root">
  <!-- Living Canvas Ambient Color Bleed Background -->
  <LivingCanvas {coverUrl} theme={currentTheme} />

  <!-- Hidden SVG Filter for Apple Liquid Glass Refraction Effect -->
  <svg style="position: absolute; width: 0; height: 0; pointer-events: none;" aria-hidden="true">
    <defs>
      <filter id="apple-liquid-glass" color-interpolation-filters="sRGB">
        <feGaussianBlur in="SourceGraphic" stdDeviation="0.4" result="blurred" />
        <feTurbulence type="fractalNoise" baseFrequency="0.035 0.035" numOctaves="2" result="noise" />
        <feDisplacementMap in="blurred" in2="noise" scale="4" xChannelSelector="R" yChannelSelector="G" result="displaced" />
        <feBlend in="SourceGraphic" in2="displaced" mode="normal" />
      </filter>
    </defs>
  </svg>

  <!-- Left Apple Liquid Glass Sidebar -->
  <aside class="left-sidebar liquid-glass">
    <!-- Brand Logo -->
    <button 
      type="button" 
      class="sidebar-logo-btn" 
      title="Link Extractor v4.0"
      on:click={() => { currentView = 'community'; playClickSound(); }}
    >
      <div class="logo-mark">
        <Icon name="bolt" size={18} color="#ffffff" strokeWidth={2.5} />
      </div>
    </button>

    <!-- Navigation Icon Group -->
    <nav class="sidebar-nav">
      <button 
        type="button"
        class="sidebar-item" 
        class:active={currentView === 'community'}
        title="Community Hub (Ctrl+1)"
        on:click={() => { currentView = 'community'; playClickSound(); }}
      >
        <Icon name="globe" size={20} />
        <span class="nav-label">Hub</span>
      </button>

      <button 
        type="button"
        class="sidebar-item" 
        class:active={currentView === 'stage'}
        title="Active Game Stage (Ctrl+2)"
        on:click={() => { currentView = 'stage'; playClickSound(); }}
      >
        <Icon name="gamepad" size={20} />
        <span class="nav-label">Stage</span>
      </button>

      <button 
        type="button"
        class="sidebar-item" 
        title="Extraction Vault / History (Ctrl+3)"
        on:click={() => { historyOpen = true; playClickSound(); }}
      >
        <Icon name="history" size={20} />
        <span class="nav-label">Vault</span>
      </button>
    </nav>

    <!-- Bottom Utility Controls -->
    <div class="sidebar-footer">
      <button 
        type="button"
        class="sidebar-icon-btn" 
        title={audioMuted ? 'Unmute Audio Haptics' : 'Mute Audio Haptics'}
        on:click={() => { audioMuted = toggleAudioMute(); }}
      >
        <Icon name={audioMuted ? 'volume-x' : 'volume'} size={18} />
      </button>

      <button 
        type="button"
        class="sidebar-icon-btn" 
        title="Settings & Themes"
        on:click={() => { settingsOpen = true; playClickSound(); }}
      >
        <Icon name="settings" size={18} />
      </button>
    </div>
  </aside>

  <!-- Main Viewport Area -->
  <div class="main-viewport">
    <!-- Top Command Deck (URL Input Bar) -->
    <header class="top-command-deck glass-panel">
      <div class="input-field-container">
        <span class="input-leading-icon">
          <Icon name="link" size={16} color="var(--text-muted)" />
        </span>

        <input 
          bind:this={urlInputEl}
          type="text" 
          class="url-input-box" 
          placeholder="Paste FitGirl game page URL, pastebin mirror, or direct FuckingFast link..." 
          bind:value={inputUrl}
          on:input={handleUrlInput}
          on:keydown={(e) => { if (e.key === 'Enter') startExtraction(); }}
        />

        {#if detectedType}
          <div class="inline-detected-chip">
            <span class="chip-pulse"></span>
            <span>{detectedType.replace('fitgirl_', '').replace('_', ' ').toUpperCase()}</span>
          </div>
        {/if}
      </div>

      <button 
        type="button" 
        class="btn-primary btn-resolve"
        disabled={isRunning}
        on:click={() => startExtraction()}
      >
        <Icon name="bolt" size={16} color="#ffffff" strokeWidth={2.5} />
        <span>{isRunning ? 'Resolving Parts...' : 'Extract & Resolve'}</span>
      </button>
    </header>

    <!-- Active Screen Body -->
    <main class="active-screen-body">
      {#if currentView === 'stage'}
        <GameStage 
          {gameTitle}
          {coverUrl}
          {sourceUrl}
          {totalSizeStr}
          {isRunning}
          {statusMessage}
          {parts}
          {logs}
          onPushJd2={handlePushToJd2}
          onExport={handleExport}
          onCopyAll={handleCopyAll}
          onCancel={handleCancelExtraction}
        />
      {:else}
        <DiscoveryHub 
          games={communityGames}
          isLoading={isCommunityLoading}
          onLoadRecord={handleLoadCommunityRecord}
          onPushJd2={(slug, title) => {
            if (typeof window !== 'undefined' && (window as any).pywebview) {
              (window as any).pywebview.api.get_game_urls(slug).then((urls: string[]) => {
                handlePushToJd2(urls, title);
              });
            }
          }}
          onRefresh={refreshCommunity}
        />
      {/if}
    </main>
  </div>

  <!-- Global Toast Notification -->
  {#if toastMessage}
    <div class="app-toast glass-panel">
      <Icon name="sparkles" size={16} color="var(--accent-primary)" />
      <span>{toastMessage}</span>
    </div>
  {/if}

  <!-- Background Clipboard Sentinel -->
  <ClipboardSentinel onResolveUrl={(url) => { inputUrl = url; startExtraction(url); }} />

  <!-- Modals -->
  <HistoryModal 
    isOpen={historyOpen}
    onClose={() => historyOpen = false}
    onLoadHistoryItem={handleLoadHistoryRecord}
    onPushJd2={handlePushToJd2}
  />

  <SettingsModal 
    isOpen={settingsOpen}
    onClose={() => settingsOpen = false}
    onThemeChange={(t) => currentTheme = t}
  />
</div>

<style>
  .app-layout-root {
    position: relative;
    width: 100vw;
    height: 100vh;
    display: flex;
    overflow: hidden;
    background: var(--bg-base);
  }

  /* Apple Liquid Glass Navbar (Refraction + Specular Caustics) */
  .left-sidebar.liquid-glass {
    position: relative;
    z-index: 100;
    width: 72px;
    height: calc(100vh - 24px);
    margin: 12px 0 12px 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    padding: 18px 0;
    border-radius: 24px;
    flex-shrink: 0;

    /* Liquid Glass Core: Translucent multi-stop gradient + heavy blur */
    background: linear-gradient(
      140deg,
      rgba(255, 255, 255, 0.12) 0%,
      rgba(255, 255, 255, 0.03) 40%,
      rgba(10, 14, 24, 0.55) 100%
    );
    backdrop-filter: blur(36px) saturate(220%) contrast(106%);
    -webkit-backdrop-filter: blur(36px) saturate(220%) contrast(106%);
    border: 1px solid rgba(255, 255, 255, 0.22);

    /* Apple Specular Edge Highlights (Snell-Descartes Refraction Simulation) */
    box-shadow: 
      inset 0 1.5px 1.5px 0 rgba(255, 255, 255, 0.65),
      inset 0 0 20px 0 rgba(255, 255, 255, 0.05),
      inset 0 -1.5px 1px 0 rgba(0, 0, 0, 0.5),
      0 20px 40px -15px rgba(0, 0, 0, 0.8),
      0 0 30px -5px rgba(16, 185, 129, 0.2);
    overflow: hidden;
  }

  /* Liquid Glass Curved Specular Lip (Upper Refractive Curve) */
  .left-sidebar.liquid-glass::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 45%;
    background: linear-gradient(
      180deg, 
      rgba(255, 255, 255, 0.25) 0%, 
      rgba(255, 255, 255, 0.06) 50%, 
      rgba(255, 255, 255, 0) 100%
    );
    border-top-left-radius: 24px;
    border-top-right-radius: 24px;
    pointer-events: none;
    z-index: 1;
  }

  /* Liquid Glass Caustic Radial Sheen */
  .left-sidebar.liquid-glass::after {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 24px;
    background: radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.15), transparent 70%);
    pointer-events: none;
    z-index: 1;
  }

  .sidebar-logo-btn {
    position: relative;
    z-index: 2;
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 0;
  }

  .logo-mark {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: var(--accent-gradient);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 
      inset 0 1px 1px rgba(255, 255, 255, 0.6),
      0 0 20px var(--accent-glow);
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), filter 0.2s ease;
  }

  .sidebar-logo-btn:hover .logo-mark {
    transform: scale(1.1);
    filter: brightness(1.18);
  }

  .sidebar-nav {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: 16px;
    align-items: center;
  }

  .sidebar-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    gap: 3px;
  }

  .sidebar-item:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.25);
    transform: scale(1.05);
  }

  .sidebar-item.active {
    color: #ffffff;
    background: var(--accent-gradient);
    border-color: rgba(255, 255, 255, 0.4);
    box-shadow: 
      inset 0 1px 1px rgba(255, 255, 255, 0.6),
      0 0 18px var(--accent-glow);
    transform: scale(1.06);
  }

  .nav-label {
    font-size: 10px;
    font-weight: 600;
  }

  .sidebar-footer {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }

  .sidebar-icon-btn {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .sidebar-icon-btn:hover {
    color: var(--text-primary);
    background: var(--bg-surface-hover);
    border-color: var(--border-hover);
  }

  /* Main Viewport */
  .main-viewport {
    position: relative;
    z-index: 10;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    height: 100vh;
    padding: 12px 16px 16px 14px;
    overflow: hidden;
  }

  /* Top Command Deck */
  .top-command-deck {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    background: var(--bg-surface);
    border-radius: var(--radius-md);
    margin-bottom: 12px;
    flex-shrink: 0;
  }

  .input-field-container {
    position: relative;
    flex: 1;
    display: flex;
    align-items: center;
    background: rgba(10, 12, 18, 0.7);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 0 12px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .input-field-container:focus-within {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 2px var(--accent-glow);
  }

  .input-leading-icon {
    display: flex;
    align-items: center;
    margin-right: 10px;
  }

  .url-input-box {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: 13px;
    padding: 10px 0;
  }

  .url-input-box::placeholder {
    color: var(--text-muted);
    font-family: var(--font-sans);
    font-size: 12px;
  }

  /* Clean Inline Chip (No Text Overlap) */
  .inline-detected-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px;
    border-radius: 6px;
    background: rgba(6, 182, 212, 0.15);
    border: 1px solid rgba(6, 182, 212, 0.35);
    color: var(--accent-secondary);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    white-space: nowrap;
    margin-left: 8px;
    flex-shrink: 0;
  }

  .chip-pulse {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-secondary);
    box-shadow: 0 0 6px var(--accent-secondary);
  }

  .btn-resolve {
    flex-shrink: 0;
    padding: 10px 20px;
  }

  /* Active Screen Body */
  .active-screen-body {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    display: flex;
  }

  /* Toast */
  .app-toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 99999;
    padding: 10px 20px;
    background: rgba(14, 18, 27, 0.95);
    border: 1px solid var(--accent-primary);
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 16px var(--accent-glow);
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
