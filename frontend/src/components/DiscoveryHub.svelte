<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, playBypassSound } from '../utils/audio';
  import { waitForBridge } from '../utils/bridgeReady';
  import type { GameRecord } from '../types';
  import { liquidGlass } from '../utils/liquidGlass';
  import { say } from '../utils/voice';

  export let games: GameRecord[] = [];
  export let isLoading: boolean = false;
  export let isOffline: boolean = false;
  export let onLoadRecord: (rec: GameRecord) => void = () => {};
  export let onReextract: (rec: GameRecord) => void = () => {};
  export let onPushJd2: (slug: string, title: string) => void = () => {};
  export let onGrab: (rec: GameRecord) => boolean = () => false;
  export let onRefresh: () => void = () => {};

  let searchQuery = '';
  let selectedFilter: 'all' | 'fresh' | 'aging' | 'expired' = 'all';
  let liveGamers = 1;
  let totalGrabs = 0;
  let heartbeatInterval: any = null;
  let floatingHeight = 62;

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

  let failedCovers = new Set<string>();

  function handleImageError(url: string) {
    failedCovers = new Set(failedCovers).add(url);
  }

  // Generated banners carry only the title, which the glass below already shows.
  function hasRealCover(url: string, failed: Set<string>): boolean {
    return /^https?:\/\//i.test(url) && !failed.has(url);
  }

  function fetchStats() {
    if (typeof window !== 'undefined' && (window as any).pywebview?.api) {
      // Ping presence with window-scoped session ID
      if ((window as any).pywebview.api.ping_presence) {
        (window as any).pywebview.api.ping_presence(sessionId).then((res: any) => {
          if (res && typeof res.live_gamers === 'number') {
            liveGamers = res.live_gamers;
          }
        }).catch(() => {});
      }

      // Query community stats
      if ((window as any).pywebview.api.get_community_stats) {
        (window as any).pywebview.api.get_community_stats().then((res: any) => {
          if (res) {
            if (typeof res.live_gamers === 'number') liveGamers = res.live_gamers;
            if (typeof res.total_grabs === 'number') totalGrabs = res.total_grabs;
          }
        }).catch(() => {});
      }
    }
  }

  let onStatsUpdatedHandler: any = null;

  onMount(() => {
    onStatsUpdatedHandler = (e: CustomEvent) => {
      if (e.detail) {
        if (typeof e.detail.live_gamers === 'number') liveGamers = e.detail.live_gamers;
        if (typeof e.detail.total_grabs === 'number') totalGrabs = e.detail.total_grabs;
      }
    };
    if (typeof window !== 'undefined') {
      window.addEventListener('community:stats_updated' as any, onStatsUpdatedHandler);
    }

    waitForBridge('ping_presence').then((ready) => {
      if (ready) {
        fetchStats();
      }
    });
    heartbeatInterval = setInterval(fetchStats, 45000);
  });

  onDestroy(() => {
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    if (typeof window !== 'undefined' && onStatsUpdatedHandler) {
      window.removeEventListener('community:stats_updated' as any, onStatsUpdatedHandler);
    }
  });

  function handleHealthCheck(rec: GameRecord, e: MouseEvent) {
    e.stopPropagation();
    rec.health_status = 'Checking...';
    rec.health_color = 'var(--accent-secondary)';
    games = [...games];

    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.get_game_urls) {
      (window as any).pywebview.api.get_game_urls(rec.slug).then((urls: string[]) => {
        if (!urls || urls.length === 0) {
          rec.health_status = 'No URLs';
          rec.health_color = 'var(--status-expired)';
          games = [...games];
          return;
        }
        if ((window as any).pywebview?.api?.check_health) {
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
        }
      });
    }
  }

  function handleCardPreview(rec: GameRecord) {
    playClickSound();
    // Looking at a game is not a grab.
    onLoadRecord(rec);
  }

  function showGrab(rec: GameRecord) {
    if (onGrab(rec)) {
      rec.used_count = (rec.used_count || 0) + 1;
      totalGrabs += 1;
      games = [...games];
    }
  }

  function handleInstantLoad(rec: GameRecord, e?: MouseEvent) {
    if (e) e.stopPropagation();
    playClickSound();
    showGrab(rec);
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
    showGrab(rec);
    onPushJd2(rec.slug, rec.title);
  }

  let filteredGames: GameRecord[] = [];

  $: filteredGames = games.filter(g => {
    const matchesSearch = !searchQuery || g.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = selectedFilter === 'all' || (g.freshness || 'fresh') === selectedFilter;
    return matchesSearch && matchesFilter;
  });
</script>

<div class="discovery-hub-container" style="--hub-float-height: {floatingHeight}px">
  <div class="hub-floating-stack" bind:clientHeight={floatingHeight}>
  <!-- Hub Search & Filters Bar -->
  <div class="hub-header-bar glass-panel" id="tour-discovery-hub" use:liquidGlass>
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

  {#if isOffline}
    <div class="hub-offline-banner glass-panel" role="status" use:liquidGlass>
      <Icon name="alert-triangle" size={14} color="var(--status-aging)" />
      <span>Could not reach the community database. {games.length > 0 ? 'Showing the last saved list.' : ''}</span>
    </div>
  {/if}
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
      <span class="empty-msg">
        {#if games.length > 0}
          {$say('hub.noMatch')}
        {:else if isOffline}
          {$say('hub.offlineEmpty')}
        {:else}
          {$say('hub.empty')}
        {/if}
      </span>
      <button 
        type="button" 
        class="btn-retry-fetch" 
        on:click={() => { onRefresh(); fetchStats(); }}
      >
        <Icon name="refresh" size={14} />
        <span>Retry Fetch</span>
      </button>
    </div>
  {:else}
    <div class="games-poster-grid">
      {#each filteredGames as rec, index (rec.slug)}
        <div class="game-poster-card" id={index === 0 ? 'tour-hub-card' : undefined} style="--card-index: {Math.min(index, 11)}">
          <!-- Poster Image -->
          <div class="card-cover-container">
            <button 
              type="button" 
              class="card-cover-action" 
              on:click={() => handleCardPreview(rec)}
              aria-label="Preview {rec.title}"
            >
              {#if hasRealCover(rec.image_url, failedCovers)}
                <img
                  src={rec.image_url}
                  alt={rec.title}
                  class="card-cover"
                  loading="lazy"
                  on:error={() => handleImageError(rec.image_url)}
                />
              {:else}
                <div class="card-cover-placeholder">
                  <Icon name="gamepad" size={36} color="var(--accent-primary)" />
                </div>
              {/if}
            </button>

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
                style="color: {rec.health_color || 'rgba(255, 255, 255, 0.94)'};"
                on:click={(e) => handleHealthCheck(rec, e)}
              >
                <Icon name="shield-check" size={12} color="currentColor" />
                <span>{rec.health_status || '1-Click Health Check'}</span>
              </button>
            </div>
          </div>

          <!-- Card Content Body -->
          <div class="card-body" use:liquidGlass={{ bezel: 14, strength: 22 }}>
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
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  /* These float above the grid, so game art passes through the glass as it scrolls. */
  .hub-floating-stack {
    position: absolute;
    top: var(--deck-offset);
    left: 0;
    right: 6px;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .hub-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    padding: 10px 14px;
    flex-wrap: wrap;
    border-radius: 18px;
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
    font-family: var(--font-display);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--accent-primary);
    background: rgba(0, 240, 160, 0.08);
    border: 1px solid rgba(0, 240, 160, 0.25);
    letter-spacing: 0.06em;
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
    font-family: var(--font-display);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
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
    padding: 3px 9px;
    border-radius: 12px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: #ffffff;
    background: var(--glass-sheen), var(--glass-tint-clear);
    backdrop-filter: var(--glass-backdrop-clear);
    box-shadow: var(--glass-chip-highlight), 0 0 0 1px rgba(255, 255, 255, 0.14), 0 2px 8px rgba(0, 0, 0, 0.4);
    z-index: 2;
    letter-spacing: 0.02em;
  }

  .filter-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 20px;
    font-family: var(--font-display);
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: rgba(255, 255, 255, 0.78);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.11), rgba(255, 255, 255, 0.035));
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: var(--glass-chip-highlight);
    cursor: pointer;
    transition: transform 0.35s var(--glass-spring), background 0.2s ease, color 0.2s ease;
  }

  .filter-pill:hover {
    color: var(--text-primary);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.07));
    transform: scale(1.04);
  }

  .filter-pill:active {
    transform: scale(0.96);
  }

  .filter-pill.active {
    color: #ffffff;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.04) 50%),
      var(--accent-gradient);
    border-color: transparent;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5), 0 6px 16px -6px var(--accent-primary);
  }

  .pill-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .dot-fresh { background: var(--status-fresh); }
  .dot-aging { background: var(--status-aging); }
  .dot-expired { background: var(--status-expired); }

  /* Poster Grid: scrolls the full height, with its first row starting below the floating bars. */
  .games-poster-grid {
    --grid-top: calc(var(--deck-offset) + var(--hub-float-height) + 12px);
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
    grid-auto-rows: min-content;
    gap: 18px;
    height: 100%;
    overflow-y: auto;
    padding: var(--grid-top) 6px 40px 2px;
    scroll-padding-top: var(--grid-top);
  }

  /* The art fills the whole card, and the details float on it as glass. */
  .game-poster-card {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    min-height: 348px;
    overflow: hidden;
    cursor: pointer;
    background: #0b0e14;
    border-radius: 20px;
    text-align: left;
    padding: 8px;
    box-shadow: var(--glass-shadow), 0 0 0 1px rgba(255, 255, 255, 0.09);
    content-visibility: auto;
    contain-intrinsic-size: auto 348px;
    transition: transform 0.4s var(--glass-spring), box-shadow 0.25s ease;
  }

  .game-poster-card:hover {
    transform: translate3d(0, -4px, 0) scale(1.012);
    box-shadow:
      0 20px 40px -14px rgba(0, 0, 0, 0.7),
      0 0 0 1px rgba(255, 255, 255, 0.24),
      0 0 26px -6px var(--accent-glow);
  }

  /* Returning to the Hub or changing a filter should feel instant, and only the first screen needs this. */
  .game-poster-card:nth-child(-n + 24) {
    animation: cardEntrance 0.34s var(--glass-settle) backwards;
    animation-delay: calc(var(--card-index) * 16ms);
  }

  /* At startup the cards wait for the splash to hand over. This ends before .is-revealing does. */
  :global(.app-layout-root.is-revealing) .game-poster-card:nth-child(-n + 24) {
    animation-duration: 0.62s;
    animation-delay: calc(0.3s + var(--card-index) * 45ms);
  }

  :global(.app-layout-root.is-booting) .game-poster-card {
    animation: none;
  }

  @keyframes cardEntrance {
    from {
      opacity: 0;
      transform: translate3d(0, 26px, 0) scale(0.965);
    }
  }

  .card-cover-container {
    position: absolute;
    inset: 0;
    overflow: hidden;
    background: #0b0e14;
  }

  .card-cover-action {
    display: block;
    width: 100%;
    height: 100%;
    padding: 0;
    margin: 0;
    border: none;
    background: transparent;
    cursor: pointer;
    text-align: inherit;
  }

  .card-cover {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 18%;
    transition: transform 0.6s var(--glass-settle);
  }

  .game-poster-card:hover .card-cover {
    transform: scale(1.06);
  }

  .card-cover-placeholder {
    width: 100%;
    height: 100%;
    padding-bottom: 168px;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
      radial-gradient(circle at 30% 20%, color-mix(in srgb, var(--accent-primary) 34%, transparent), transparent 60%),
      radial-gradient(circle at 75% 60%, color-mix(in srgb, var(--accent-secondary) 26%, transparent), transparent 60%);
  }

  .card-cover-overlay {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    justify-content: flex-end;
  }

  .btn-health-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border: 0;
    border-radius: 12px;
    font-size: 10.5px;
    font-weight: 700;
    background: var(--glass-sheen), var(--glass-tint-clear);
    backdrop-filter: var(--glass-backdrop-clear);
    box-shadow: var(--glass-chip-highlight), 0 0 0 1px rgba(255, 255, 255, 0.14), 0 2px 8px rgba(0, 0, 0, 0.4);
    cursor: pointer;
    transition: transform 0.35s var(--glass-spring), filter 0.2s ease;
  }

  .btn-health-pill:hover {
    transform: scale(1.05);
    filter: brightness(1.2);
  }

  .card-body {
    /* Darker than the bars, because this glass often sits on bright art and carries small text. */
    --glass-backdrop: blur(10px) saturate(170%) brightness(0.56);
    position: relative;
    z-index: 1;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
    border-radius: 14px;
    background: var(--glass-sheen), var(--glass-tint);
    backdrop-filter: var(--glass-backdrop);
    box-shadow:
      0 0 0 1px rgba(255, 255, 255, 0.13),
      inset 0 1px 1px rgba(255, 255, 255, 0.28),
      0 8px 20px -10px rgba(0, 0, 0, 0.7);
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
    color: rgba(255, 255, 255, 0.72);
    font-family: var(--font-mono);
  }

  .card-title {
    font-family: var(--font-display);
    font-size: 13.5px;
    font-weight: 700;
    letter-spacing: 0.015em;
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
    color: rgba(255, 255, 255, 0.78);
  }

  .card-time {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .card-size-wrapper {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .card-size {
    font-family: var(--font-mono);
    font-size: 11.5px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--accent-primary);
  }

  .card-actions-row {
    display: flex;
    gap: 6px;
    margin-top: 4px;
  }

  .card-actions-row :global(.btn-primary) {
    flex: 1;
    white-space: nowrap;
  }

  .card-actions-row :global(.btn-secondary) {
    flex: 0 0 auto;
    padding: 6px 13px;
  }

  .btn-sm {
    padding: 6px 10px;
    font-family: var(--font-display);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
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

  .hub-loading {
    margin-top: calc(var(--deck-offset) + var(--hub-float-height) + 12px);
    padding: 40px;
    text-align: center;
    color: var(--text-secondary);
  }

  .hub-offline-banner {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    font-size: 0.8rem;
    color: var(--text-secondary);
  }

  .hub-empty {
    margin-top: calc(var(--deck-offset) + var(--hub-float-height) + 12px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 48px 24px;
    text-align: center;
    color: var(--text-secondary);
  }

  .empty-msg {
    font-size: 0.95rem;
    color: var(--text-secondary);
  }

  .btn-retry-fetch {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 18px;
    border-radius: 9999px;
    background: rgba(0, 240, 160, 0.1);
    border: 1px solid rgba(0, 240, 160, 0.35);
    color: var(--accent-primary);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-retry-fetch:hover {
    background: rgba(0, 240, 160, 0.2);
    border-color: var(--accent-primary);
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(0, 240, 160, 0.2);
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
