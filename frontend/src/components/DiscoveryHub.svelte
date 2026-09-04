<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, playBypassSound } from '../utils/audio';
  import type { GameRecord } from '../types';

  export let games: GameRecord[] = [];
  export let isLoading: boolean = false;
  export let onLoadRecord: (rec: GameRecord) => void = () => {};
  export let onReextract: (rec: GameRecord) => void = () => {};
  export let onPushJd2: (slug: string, title: string) => void = () => {};
  export let onRefresh: () => void = () => {};

  let searchQuery = '';
  let selectedFilter: 'all' | 'fresh' | 'aging' | 'expired' = 'all';
  let liveGamers = 1;
  let totalGrabs = 0;
  let heartbeatInterval: any = null;

  // Generate unique session per window/instance using sessionStorage + high-entropy timestamp
  const sessionId = (typeof window !== 'undefined' && sessionStorage.getItem('le_window_session_id')) 
    || 'usr_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now().toString(36);
  if (typeof window !== 'undefined') {
    sessionStorage.setItem('le_window_session_id', sessionId);
  }

  // Format exact timestamp strictly using user system locale, clock, and timezone
  function formatUserDateTime(isoStr?: string, fallback?: string): string {
    if (!isoStr) return fallback || 'Recently';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return fallback || 'Recently';
      return d.toLocaleString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return fallback || 'Recently';
    }
  }

  // Calculate dynamic relative age from current system time
  function formatUserRelativeAge(isoStr?: string, fallback?: string): string {
    if (!isoStr) return fallback || 'recent';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return fallback || 'recent';
      const diffSecs = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
      if (diffSecs < 60) return 'Just now';
      if (diffSecs < 3600) {
        const mins = Math.floor(diffSecs / 60);
        return `${mins} min${mins !== 1 ? 's' : ''} ago`;
      }
      if (diffSecs < 86400) {
        const hrs = Math.floor(diffSecs / 3600);
        return `${hrs} hour${hrs !== 1 ? 's' : ''} ago`;
      }
      const days = Math.floor(diffSecs / 86400);
      return `${days} day${days !== 1 ? 's' : ''} ago`;
    } catch {
      return fallback || 'recent';
    }
  }

  function fetchStats() {
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      // Ping presence with window-scoped session ID
      (window as any).pywebview.api.ping_presence(sessionId).then((res: any) => {
        if (res && typeof res.live_gamers === 'number') {
          liveGamers = res.live_gamers;
        }
      }).catch(() => {});

      // Query community stats
      (window as any).pywebview.api.get_community_stats().then((res: any) => {
        if (res) {
          if (typeof res.live_gamers === 'number') liveGamers = res.live_gamers;
          if (typeof res.total_grabs === 'number') totalGrabs = res.total_grabs;
        }
      }).catch(() => {});
    }
  }

  onMount(() => {
    fetchStats();
    heartbeatInterval = setInterval(fetchStats, 45000);
  });

  onDestroy(() => {
    if (heartbeatInterval) clearInterval(heartbeatInterval);
  });

  function handleHealthCheck(rec: GameRecord, e: MouseEvent) {
    e.stopPropagation();
    rec.health_status = 'Checking...';
    rec.health_color = 'var(--accent-secondary)';
    games = [...games];

    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.get_game_urls(rec.slug).then((urls: string[]) => {
        if (!urls || urls.length === 0) {
          rec.health_status = 'No URLs';
          rec.health_color = 'var(--status-expired)';
          games = [...games];
          return;
        }
        (window as any).pywebview.api.check_health(urls[0]).then((res: any) => {
          if (res.is_alive) {
            rec.health_status = `Part 1 Live (${res.message})`;
            rec.health_color = 'var(--status-fresh)';
            playBypassSound();
          } else {
            rec.health_status = `Expired (${res.message})`;
            rec.health_color = 'var(--status-expired)';
          }
          games = [...games];
        });
      });
    }
  }

  function handleCardPreview(rec: GameRecord) {
    playClickSound();
    // Preview/load game into Stage without incrementing grab count
    onLoadRecord(rec);
  }

  function handleInstantLoad(rec: GameRecord, e?: MouseEvent) {
    if (e) e.stopPropagation();
    playClickSound();
    rec.used_count = (rec.used_count || 0) + 1;
    totalGrabs += 1;
    games = [...games];
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.track_game_usage(rec.slug).catch(() => {});
    }
    onLoadRecord(rec);
  }

  function handleReextract(rec: GameRecord, e?: MouseEvent) {
    if (e) e.stopPropagation();
    playClickSound();
    onReextract(rec);
  }

  function handleQuickPushJd(rec: GameRecord, e: MouseEvent) {
    e.stopPropagation();
    playClickSound();
    if (rec.freshness === 'expired') {
      onReextract(rec);
      return;
    }
    rec.used_count = (rec.used_count || 0) + 1;
    totalGrabs += 1;
    games = [...games];
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.track_game_usage(rec.slug).catch(() => {});
    }
    onPushJd2(rec.slug, rec.title);
  }

  let filteredGames: GameRecord[] = [];

  // Filtered games with client-side canonical deduplication to prevent ghost duplicates
  $: {
    const rawList = games.filter(g => {
      const matchesSearch = !searchQuery || g.title.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesFilter = selectedFilter === 'all' || (g.freshness || 'fresh') === selectedFilter;
      return matchesSearch && matchesFilter;
    });

    const seen = new Map<string, GameRecord>();
    for (const g of rawList) {
      const norm = g.title
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '')
        .replace(/(deluxeedition|completeedition|ultimateedition|bonusost|bonuscontent|repack|repak|v\d+.*)/g, '')
        .slice(0, 24);
      const key = norm.length > 5 ? `t:${norm}` : `s:${g.slug}`;
      if (!seen.has(key)) {
        seen.set(key, g);
      } else {
        const prev = seen.get(key)!;
        if ((g.timestamp_utc || '') > (prev.timestamp_utc || '')) {
          seen.set(key, g);
        }
      }
    }
    filteredGames = Array.from(seen.values());
  }
</script>

<div class="discovery-hub-container">
  <!-- Hub Search & Filters Bar -->
  <div class="hub-header-bar glass-panel">
    <div class="search-box-wrapper">
      <span class="search-icon">
        <Icon name="search" size={16} color="var(--text-muted)" />
      </span>
      <input 
        type="text" 
        class="glass-input search-input" 
        placeholder="Search community pre-fetched repacks..." 
        bind:value={searchQuery} 
      />
    </div>

    <div class="filter-chips-row">
      <!-- Live Gamers Pulse Badge -->
      <div class="live-pulse-badge" title="{liveGamers} active gamers currently connected">
        <span class="pulse-radar-dot">
          <span class="radar-wave"></span>
        </span>
        <span class="live-count-text">{liveGamers} {liveGamers === 1 ? 'Gamer' : 'Gamers'} Online</span>
      </div>

      {#if totalGrabs > 0}
        <div class="total-grabs-badge" title="Total repacks grabbed by community">
          <Icon name="zap" size={12} color="var(--accent-primary)" />
          <span>{totalGrabs} {totalGrabs === 1 ? 'Grab' : 'Grabs'}</span>
        </div>
      {/if}

      <button 
        type="button"
        class="filter-pill" 
        class:active={selectedFilter === 'all'}
        on:click={() => { selectedFilter = 'all'; playClickSound(); }}
      >
        <Icon name="layers" size={13} />
        <span>All ({games.length})</span>
      </button>
      <button 
        type="button"
        class="filter-pill" 
        class:active={selectedFilter === 'fresh'}
        on:click={() => { selectedFilter = 'fresh'; playClickSound(); }}
      >
        <span class="pill-dot dot-fresh"></span>
        <span>Fresh</span>
      </button>
      <button 
        type="button"
        class="filter-pill" 
        class:active={selectedFilter === 'aging'}
        on:click={() => { selectedFilter = 'aging'; playClickSound(); }}
      >
        <span class="pill-dot dot-aging"></span>
        <span>Aging</span>
      </button>
      <button 
        type="button"
        class="filter-pill" 
        class:active={selectedFilter === 'expired'}
        on:click={() => { selectedFilter = 'expired'; playClickSound(); }}
      >
        <span class="pill-dot dot-expired"></span>
        <span>Expired</span>
      </button>

      <button type="button" class="btn-icon" title="Refresh Community Feed" on:click={() => { onRefresh(); fetchStats(); }}>
        <Icon name="refresh" size={16} />
      </button>
    </div>
  </div>

  <!-- Cards Poster Grid -->
  {#if isLoading}
    <div class="hub-loading glass-panel">
      <div class="dino-loader-banner">
        <span class="loading-spin">
          <Icon name="refresh" size={18} color="var(--accent-primary)" />
        </span>
        <span>QUERYING COMMUNITY CLOUD CACHE...</span>
      </div>
    </div>
  {:else if filteredGames.length === 0}
    <div class="hub-empty glass-panel">
      <span>No community repacks found matching your search.</span>
    </div>
  {:else}
    <div class="games-poster-grid">
      {#each filteredGames as rec (rec.slug)}
        <div class="game-poster-card glass-card">
          <!-- Poster Image -->
          <div 
            class="card-cover-container" 
            role="button" 
            tabindex="0"
            on:click={() => handleCardPreview(rec)}
            on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleCardPreview(rec)}
          >
            {#if rec.image_url}
              <img src={rec.image_url} alt={rec.title} class="card-cover" loading="lazy" />
            {:else}
              <div class="card-cover-placeholder">
                <Icon name="gamepad" size={36} color="var(--accent-primary)" />
              </div>
            {/if}

            <!-- Floating Grabs Badge on Cover -->
            {#if rec.used_count && rec.used_count > 0}
              <div class="card-cover-grabs-pill" title="Community Downloads">
                <Icon name="zap" size={11} color="#00f0a0" strokeWidth={2.5} />
                <span>{rec.used_count} {rec.used_count === 1 ? 'grab' : 'grabs'}</span>
              </div>
            {/if}

            <div class="card-cover-overlay">
              <button 
                type="button" 
                class="btn-health-pill" 
                style="color: {rec.health_color || 'var(--text-secondary)'};"
                on:click={(e) => handleHealthCheck(rec, e)}
              >
                <Icon name="shield-check" size={12} color="currentColor" />
                <span>{rec.health_status || '1-Click Health Check'}</span>
              </button>
            </div>
          </div>

          <!-- Card Content Body -->
          <div class="card-body">
            <div class="card-meta-top">
              <span class="badge badge-{rec.freshness || 'fresh'}">
                {(rec.freshness || 'fresh').toUpperCase()} ({formatUserRelativeAge(rec.timestamp_utc, rec.age_str)})
              </span>
              <span class="card-parts-count">
                <Icon name="package" size={12} color="var(--text-muted)" />
                <span>{rec.total_parts} Parts</span>
              </span>
            </div>

            <h3 class="card-title">
              <button 
                type="button" 
                class="card-title-btn" 
                title={rec.title} 
                on:click={() => handleCardPreview(rec)}
              >
                {rec.title}
              </button>
            </h3>

            <div class="card-meta-bottom">
              <span class="card-time">
                <Icon name="clock" size={12} color="var(--text-muted)" />
                <span>{formatUserDateTime(rec.timestamp_utc, rec.local_time)}</span>
              </span>
              <div class="card-size-wrapper">
                <Icon name="hard-drive" size={12} color="var(--accent-primary)" />
                <strong class="card-size">{rec.total_size_str || '0 B'}</strong>
              </div>
            </div>

            <div class="card-actions-row">
              {#if rec.freshness === 'expired'}
                <button 
                  type="button"
                  class="btn-primary btn-sm btn-reextract"
                  title="Cached links are outdated ({formatUserRelativeAge(rec.timestamp_utc, rec.age_str)}). Click to resolve fresh mirrors."
                  on:click={(e) => handleReextract(rec, e)}
                >
                  <Icon name="refresh" size={13} color="#002e1c" strokeWidth={2.4} />
                  <span>Extract Fresh</span>
                </button>
              {:else}
                <button 
                  type="button"
                  class="btn-primary btn-sm"
                  on:click={(e) => handleInstantLoad(rec, e)}
                >
                  <Icon name="zap" size={14} color="#ffffff" strokeWidth={2.5} />
                  <span>Instant Load (0s)</span>
                </button>
              {/if}

              <button 
                type="button"
                class="btn-secondary btn-sm"
                title={rec.freshness === 'expired' ? 'Links are expired. Click to re-extract fresh mirrors before pushing to JD2' : 'Push directly to JDownloader 2'}
                on:click={(e) => handleQuickPushJd(rec, e)}
              >
                <Icon name="external-link" size={13} />
                <span>JD2</span>
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .discovery-hub-container {
    display: flex;
    flex-direction: column;
    gap: 14px;
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .hub-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    padding: 12px 16px;
    flex-wrap: wrap;
  }

  .search-box-wrapper {
    position: relative;
    flex: 1;
    min-width: 260px;
  }

  .search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
  }

  .search-input {
    padding-left: 36px;
  }

  .filter-chips-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  /* Live Pulse Badge & Radar Wave */
  .live-pulse-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 11px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    color: var(--accent-primary);
    background: rgba(0, 240, 160, 0.08);
    border: 1px solid rgba(0, 240, 160, 0.25);
    letter-spacing: 0.3px;
    user-select: none;
  }

  .pulse-radar-dot {
    position: relative;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent-primary);
    display: inline-block;
  }

  .radar-wave {
    position: absolute;
    top: -2px;
    left: -2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 1.5px solid var(--accent-primary);
    opacity: 0.8;
    animation: radarRipple 1.8s infinite cubic-bezier(0.215, 0.61, 0.355, 1);
  }

  @keyframes radarRipple {
    0% {
      transform: scale(0.6);
      opacity: 1;
    }
    100% {
      transform: scale(2.4);
      opacity: 0;
    }
  }

  .total-grabs-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .card-cover-grabs-pill {
    position: absolute;
    top: 8px;
    left: 8px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 700;
    color: #ffffff;
    background: rgba(10, 14, 22, 0.85);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid rgba(0, 240, 160, 0.4);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
    z-index: 2;
    letter-spacing: 0.2px;
  }

  .filter-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .filter-pill:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.1);
  }

  .filter-pill.active {
    color: #ffffff;
    background: var(--accent-gradient);
    border-color: transparent;
    box-shadow: 0 0 12px var(--accent-glow);
  }

  .pill-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .dot-fresh { background: var(--status-fresh); }
  .dot-aging { background: var(--status-aging); }
  .dot-expired { background: var(--status-expired); }

  /* Poster Grid */
  .games-poster-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
    grid-auto-rows: min-content;
    gap: 18px;
    flex: 1;
    overflow-y: auto;
    padding: 4px 6px 40px 2px;
    min-height: 0;
  }

  .game-poster-card {
    display: flex;
    flex-direction: column;
    min-height: 330px;
    height: auto;
    overflow: hidden;
    cursor: pointer;
    background: var(--bg-surface);
    border-radius: var(--radius-md);
    text-align: left;
    padding: 0;
    border: 1px solid var(--border-subtle);
    flex-shrink: 0;
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .game-poster-card:hover {
    transform: translateY(-3px);
    border-color: var(--accent-primary);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5), 0 0 12px var(--accent-glow);
  }

  .card-cover-container {
    position: relative;
    width: 100%;
    height: 160px;
    min-height: 160px;
    background: rgba(0, 0, 0, 0.4);
    overflow: hidden;
    flex-shrink: 0;
  }

  .card-cover {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s ease;
  }

  .game-poster-card:hover .card-cover {
    transform: scale(1.05);
  }

  .card-cover-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(16, 185, 129, 0.05);
  }

  .card-cover-overlay {
    position: absolute;
    bottom: 8px;
    left: 8px;
    right: 8px;
    display: flex;
    justify-content: flex-end;
  }

  .btn-health-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 9px;
    border-radius: 12px;
    font-size: 10.5px;
    font-weight: 700;
    background: rgba(10, 12, 18, 0.9);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-health-pill:hover {
    border-color: #ffffff;
    filter: brightness(1.2);
  }

  .card-body {
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 9px;
    flex: 1;
    width: 100%;
  }

  .card-meta-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .card-parts-count {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11.5px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .card-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 38px;
    margin: 0;
  }

  .card-title-btn {
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    font: inherit;
    font-size: inherit;
    font-weight: inherit;
    color: inherit;
    text-align: left;
    cursor: pointer;
    width: 100%;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    transition: color 0.18s ease;
  }

  .card-title-btn:hover {
    color: var(--accent-primary);
  }

  .card-meta-bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11.5px;
    color: var(--text-secondary);
  }

  .card-time {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .card-size-wrapper {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .card-time {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .card-size {
    color: var(--accent-primary);
  }

  .card-actions-row {
    display: flex;
    gap: 6px;
    margin-top: 4px;
  }

  .btn-sm {
    padding: 6px 10px;
    font-size: 11px;
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }

  .btn-reextract {
    background: linear-gradient(135deg, #00f0a0, #06b6d4) !important;
    color: #002e1c !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(0, 240, 160, 0.25) !important;
  }

  .btn-reextract:hover {
    background: linear-gradient(135deg, #34d399, #38bdf8) !important;
    box-shadow: 0 6px 18px rgba(0, 240, 160, 0.45) !important;
    transform: translateY(-1px);
  }

  .hub-loading, .hub-empty {
    padding: 40px;
    text-align: center;
    color: var(--text-secondary);
  }

  .dino-loader-banner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: var(--accent-primary);
  }

  .loading-spin {
    display: flex;
    animation: spin 1s infinite linear;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
