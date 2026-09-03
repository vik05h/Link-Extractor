<script lang="ts">
  import DefragMosaic, { type PartItem } from './DefragMosaic.svelte';
  import SelectiveFilter from './SelectiveFilter.svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, playSuccessChime } from '../utils/audio';

  export let gameTitle: string = 'FitGirl Game Repack';
  export let coverUrl: string = '';
  export let sourceUrl: string = '';
  export let totalSizeStr: string = '0 B';
  export let isRunning: boolean = false;
  export let statusMessage: string = 'Ready';
  export let parts: PartItem[] = [];
  export let logs: string[] = [];

  export let onPushJd2: (urls: string[], title: string) => void = () => {};
  export let onExport: (format: 'txt' | 'json' | 'crawljob', urls: string[], title: string) => void = () => {};
  export let onCopyAll: (urls: string[]) => void = () => {};
  export let onCancel: () => void = () => {};

  let activeView: 'mosaic' | 'table' | 'log' = 'mosaic';
  let exportMenuOpen = false;

  function getActiveUrls(): string[] {
    return parts
      .filter(p => !p.excluded && (p.direct_url || p.url))
      .map(p => p.direct_url || p.url);
  }

  function handlePushJd2() {
    playClickSound();
    const urls = getActiveUrls();
    onPushJd2(urls, gameTitle);
  }

  function handleExport(format: 'txt' | 'json' | 'crawljob') {
    playClickSound();
    exportMenuOpen = false;
    const urls = getActiveUrls();
    onExport(format, urls, gameTitle);
  }

  function handleCopyAll() {
    playClickSound();
    const urls = getActiveUrls();
    onCopyAll(urls);
  }

  function handleCopySinglePart(url: string, index: number) {
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.copy_to_clipboard(url);
    } else {
      navigator.clipboard.writeText(url);
    }
  }

  $: resolvedPartsCount = parts.filter(p => p.status === 'resolved').length;
  $: activePartsCount = parts.filter(p => !p.excluded).length;
  $: hasParts = parts.length > 0;
</script>

<div class="game-stage-container">
  <!-- Top Hero Header -->
  <div class="stage-hero glass-panel">
    <div class="hero-cover-wrapper">
      {#if coverUrl}
        <img src={coverUrl} alt={gameTitle} class="hero-cover" />
      {:else}
        <div class="hero-cover-placeholder">
          <Icon name="gamepad" size={32} color="var(--accent-primary)" />
        </div>
      {/if}
    </div>

    <div class="hero-details">
      <div class="hero-top-meta">
        <span class="badge badge-fresh">
          <Icon name="bolt" size={12} color="var(--accent-primary)" />
          <span>TURBO RESOLVER</span>
        </span>
        {#if isRunning}
          <span class="badge badge-aging animate-pulse">
            <span>SOLVING TURNSTILE IN PARALLEL</span>
          </span>
        {/if}
      </div>

      <h1 class="hero-title" title={gameTitle}>{gameTitle}</h1>

      <div class="hero-badges">
        <span class="meta-pill">
          <Icon name="grid" size={13} color="var(--accent-primary)" />
          <span><strong>{resolvedPartsCount}</strong> / {parts.length} Parts Resolved</span>
        </span>
        <span class="meta-pill size-pill">
          <span>Total Size: <strong>{totalSizeStr}</strong></span>
        </span>
        <span class="meta-status">
          {statusMessage}
        </span>
      </div>
    </div>
  </div>

  <!-- Selective Filter Bar -->
  <SelectiveFilter 
    {parts} 
    on:filterChange={(e) => { parts = e.detail.parts; }} 
  />

  <!-- View Switcher Tabs -->
  <div class="stage-tabs-row">
    <div class="segmented-tabs">
      <button 
        type="button"
        class="tab-btn" 
        class:active={activeView === 'mosaic'}
        on:click={() => { activeView = 'mosaic'; playClickSound(); }}
      >
        <Icon name="grid" size={14} />
        <span>Defrag Matrix</span>
      </button>
      <button 
        type="button"
        class="tab-btn" 
        class:active={activeView === 'table'}
        on:click={() => { activeView = 'table'; playClickSound(); }}
      >
        <Icon name="table" size={14} />
        <span>Direct URLs Table ({activePartsCount})</span>
      </button>
      <button 
        type="button"
        class="tab-btn" 
        class:active={activeView === 'log'}
        on:click={() => { activeView = 'log'; playClickSound(); }}
      >
        <Icon name="terminal" size={14} />
        <span>Telemetry & Terminal ({logs.length})</span>
      </button>
    </div>

    <!-- Quick Action Launcher Buttons -->
    <div class="stage-actions">
      {#if isRunning}
        <button type="button" class="btn-secondary btn-cancel" on:click={onCancel}>
          <Icon name="close" size={14} color="var(--status-expired)" />
          <span>Stop Extraction</span>
        </button>
      {:else}
        <button 
          type="button" 
          class="btn-primary" 
          disabled={!hasParts}
          on:click={handlePushJd2}
        >
          <Icon name="bolt" size={15} color="#ffffff" strokeWidth={2.5} />
          <span>Push to JD2 LinkGrabber</span>
        </button>

        <button 
          type="button" 
          class="btn-secondary" 
          disabled={!hasParts}
          on:click={handleCopyAll}
        >
          <Icon name="copy" size={14} />
          <span>Copy All URLs</span>
        </button>

        <div class="export-dropdown-wrapper">
          <button 
            type="button" 
            class="btn-icon" 
            title="Export Direct URLs"
            disabled={!hasParts}
            on:click={() => exportMenuOpen = !exportMenuOpen}
          >
            <Icon name="download" size={16} />
          </button>

          {#if exportMenuOpen}
            <div class="export-menu glass-panel">
              <button type="button" class="export-item" on:click={() => handleExport('txt')}>
                Export as .txt
              </button>
              <button type="button" class="export-item" on:click={() => handleExport('json')}>
                Export as .json
              </button>
              <button type="button" class="export-item" on:click={() => handleExport('crawljob')}>
                Export as JDownloader .crawljob
              </button>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <!-- Tab Contents -->
  <div class="stage-view-body">
    {#if !hasParts && !isRunning}
      <!-- Empty Stage Placeholder -->
      <div class="empty-stage-cockpit glass-panel">
        <div class="cockpit-icon-halo">
          <Icon name="gamepad" size={42} color="var(--accent-primary)" strokeWidth={1.5} />
        </div>
        <h3>Cockpit Ready</h3>
        <p>Paste a FitGirl game URL in the bar above or choose a pre-fetched game from the Community Hub.</p>
      </div>
    {:else if activeView === 'mosaic'}
      <DefragMosaic {parts} onCopyUrl={handleCopySinglePart} />
    {:else if activeView === 'table'}
      <!-- Direct URLs Data Table -->
      <div class="urls-table-container glass-panel">
        <table class="urls-table">
          <thead>
            <tr>
              <th style="width: 50px;">#</th>
              <th>Part Filename</th>
              <th style="width: 120px;">Size</th>
              <th style="width: 110px;">Status</th>
              <th style="width: 70px;">Action</th>
            </tr>
          </thead>
          <tbody>
            {#each parts as p (p.index)}
              <tr class:excluded-row={p.excluded}>
                <td class="font-mono">#{p.index}</td>
                <td class="filename-cell" title={p.filename}>
                  {p.filename || `Part ${p.index}`}
                </td>
                <td class="font-mono">{p.size || '1-Byte Range Pending'}</td>
                <td>
                  <span class="table-status {p.status}">
                    {p.status.toUpperCase()}
                  </span>
                </td>
                <td>
                  <button 
                    type="button"
                    class="btn-icon-sm" 
                    title="Copy Link"
                    on:click={() => handleCopySinglePart(p.direct_url || p.url, p.index)}
                  >
                    <Icon name="copy" size={13} />
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <!-- Telemetry Terminal Log -->
      <div class="terminal-log-container glass-panel">
        <div class="terminal-header">
          <div class="terminal-title">
            <Icon name="terminal" size={14} color="var(--accent-secondary)" />
            <span>REAL-TIME ENGINE TELEMETRY</span>
          </div>
          <span>{logs.length} EVENTS</span>
        </div>
        <div class="terminal-scroll">
          {#each logs as logLine}
            <div class="log-entry font-mono">{logLine}</div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .game-stage-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
  }

  /* Hero Banner */
  .stage-hero {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 16px 20px;
    background: var(--bg-surface);
  }

  .hero-cover-wrapper {
    flex-shrink: 0;
    width: 80px;
    height: 105px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    background: rgba(255, 255, 255, 0.05);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    border: 1px solid var(--border-subtle);
  }

  .hero-cover {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .hero-cover-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(16, 185, 129, 0.08);
  }

  .hero-details {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .hero-top-meta {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .hero-title {
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .hero-badges {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .meta-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--border-subtle);
  }

  .meta-pill strong {
    color: var(--accent-primary);
  }

  .size-pill strong {
    color: var(--accent-secondary);
  }

  .meta-status {
    color: var(--text-muted);
  }

  /* Segmented View Row */
  .stage-tabs-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .segmented-tabs {
    display: flex;
    align-items: center;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 3px;
    gap: 2px;
  }

  .tab-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .tab-btn:hover {
    color: var(--text-primary);
  }

  .tab-btn.active {
    color: #ffffff;
    background: var(--accent-gradient);
    box-shadow: 0 0 12px var(--accent-glow);
  }

  /* Action Buttons */
  .stage-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    position: relative;
  }

  .btn-cancel {
    color: var(--status-expired);
    border-color: rgba(244, 63, 94, 0.3);
  }

  .btn-cancel:hover {
    background: rgba(244, 63, 94, 0.15);
  }

  .export-dropdown-wrapper {
    position: relative;
  }

  .export-menu {
    position: absolute;
    right: 0;
    top: calc(100% + 6px);
    z-index: 50;
    width: 220px;
    padding: 6px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    box-shadow: var(--shadow-md);
  }

  .export-item {
    text-align: left;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    color: var(--text-primary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .export-item:hover {
    background: var(--bg-surface-hover);
    color: var(--accent-primary);
  }

  /* Empty Cockpit */
  .empty-stage-cockpit {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    text-align: center;
    gap: 12px;
  }

  .cockpit-icon-halo {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 4px;
  }

  .empty-stage-cockpit h3 {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .empty-stage-cockpit p {
    font-size: 12px;
    color: var(--text-muted);
    max-width: 440px;
  }

  /* Table View */
  .urls-table-container {
    max-height: 320px;
    overflow-y: auto;
    background: var(--bg-surface);
  }

  .urls-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  .urls-table th {
    text-align: left;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border-subtle);
    color: var(--text-muted);
    font-weight: 600;
  }

  .urls-table td {
    padding: 8px 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    color: var(--text-secondary);
  }

  .urls-table tr:hover td {
    background: rgba(255, 255, 255, 0.02);
  }

  .filename-cell {
    color: var(--text-primary);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 380px;
  }

  .excluded-row {
    opacity: 0.35;
    text-decoration: line-through;
  }

  .table-status {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .table-status.resolved { color: var(--accent-primary); background: rgba(16, 185, 129, 0.15); }
  .table-status.decrypting { color: var(--accent-secondary); background: rgba(6, 182, 212, 0.15); }
  .table-status.pending { color: var(--text-muted); }

  .btn-icon-sm {
    width: 28px;
    height: 28px;
    border-radius: 4px;
    background: transparent;
    border: 1px solid var(--border-subtle);
    color: var(--text-secondary);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .btn-icon-sm:hover {
    background: var(--bg-surface-hover);
    color: var(--accent-primary);
  }

  /* Telemetry Log */
  .terminal-log-container {
    max-height: 320px;
    padding: 12px;
    background: rgba(8, 10, 15, 0.9);
  }

  .terminal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    font-weight: 700;
    color: var(--accent-secondary);
    margin-bottom: 8px;
    letter-spacing: 0.8px;
  }

  .terminal-title {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .terminal-scroll {
    max-height: 270px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .log-entry {
    font-size: 11px;
    color: #94a3b8;
    line-height: 1.4;
  }
</style>
