<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, playBypassSound } from '../utils/audio';
  import type { GameRecord } from '../types';

  export let games: GameRecord[] = [];
  export let isLoading: boolean = false;
  export let onLoadRecord: (rec: GameRecord) => void = () => {};
  export let onPushJd2: (slug: string, title: string) => void = () => {};
  export let onRefresh: () => void = () => {};

  let searchQuery = '';
  let selectedFilter: 'all' | 'fresh' | 'aging' | 'expired' = 'all';

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

  function handleInstantLoad(rec: GameRecord) {
    playClickSound();
    onLoadRecord(rec);
  }

  function handleQuickPushJd(rec: GameRecord, e: MouseEvent) {
    e.stopPropagation();
    playClickSound();
    onPushJd2(rec.slug, rec.title);
  }

  // Filtered games
  $: filteredGames = games.filter(g => {
    const matchesSearch = !searchQuery || g.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = selectedFilter === 'all' || (g.freshness || 'fresh') === selectedFilter;
    return matchesSearch && matchesFilter;
  });
</script>

<div class="discovery-hub-container">
  <!-- Hub Search & Filters Bar -->
  <div class="hub-header-bar glass-panel">
    <div class="search-box-wrapper">
      <span class="search-icon">
        <Icon name="search" size={15} color="var(--text-muted)" />
      </span>
      <input 
        type="text" 
        class="glass-input search-input" 
        placeholder="Search community pre-fetched repacks..."
        bind:value={searchQuery} 
      />
    </div>

    <div class="filter-chips-row">
      <button 
        type="button"
        class="filter-pill" 
        class:active={selectedFilter === 'all'}
        on:click={() => { selectedFilter = 'all'; playClickSound(); }}
      >
        All ({games.length})
      </button>
      <button 
        type="button"
        class="filter-pill" 
        class:active={selectedFilter === 'fresh'}
        on:click={() => { selectedFilter = 'fresh'; playClickSound(); }}
      >
        <span class="pill-dot dot-fresh"></span> Fresh
      </button>
      <button 
        type="button"
        class="filter-pill" 
        class:active={selectedFilter === 'aging'}
        on:click={() => { selectedFilter = 'aging'; playClickSound(); }}
      >
        <span class="pill-dot dot-aging"></span> Aging
      </button>
      <button 
        type="button"
        class="filter-pill" 
        class:active={selectedFilter === 'expired'}
        on:click={() => { selectedFilter = 'expired'; playClickSound(); }}
      >
        <span class="pill-dot dot-expired"></span> Expired
      </button>

      <button type="button" class="btn-icon" title="Refresh Community Feed" on:click={onRefresh}>
        <Icon name="refresh" size={15} />
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
          <div class="card-cover-container" on:click={() => handleInstantLoad(rec)}>
            {#if rec.image_url}
              <img src={rec.image_url} alt={rec.title} class="card-cover" loading="lazy" />
            {:else}
              <div class="card-cover-placeholder">
                <Icon name="gamepad" size={32} color="var(--accent-primary)" />
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
                {(rec.freshness || 'fresh').toUpperCase()} ({rec.age_str || 'recent'})
              </span>
              <span class="card-parts-count">{rec.total_parts} Parts</span>
            </div>

            <h3 class="card-title" title={rec.title} on:click={() => handleInstantLoad(rec)}>{rec.title}</h3>

            <div class="card-meta-bottom">
              <span class="card-time">
                <Icon name="clock" size={11} color="var(--text-muted)" />
                <span>{rec.local_time || 'Recently'}</span>
              </span>
              <strong class="card-size">{rec.total_size_str || '0 B'}</strong>
            </div>

            <div class="card-actions-row">
              <button 
                type="button"
                class="btn-primary btn-sm"
                on:click={() => handleInstantLoad(rec)}
              >
                <Icon name="bolt" size={13} color="#ffffff" strokeWidth={2.5} />
                <span>Instant Load (0s)</span>
              </button>

              <button 
                type="button"
                class="btn-secondary btn-sm"
                title="Push directly to JDownloader 2"
                on:click={(e) => handleQuickPushJd(rec, e)}
              >
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
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    grid-auto-rows: min-content;
    gap: 16px;
    flex: 1;
    overflow-y: auto;
    padding: 4px 6px 40px 2px;
    min-height: 0;
  }

  .game-poster-card {
    display: flex;
    flex-direction: column;
    min-height: 310px;
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
    height: 145px;
    min-height: 145px;
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
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 10px;
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
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
    width: 100%;
  }

  .card-meta-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .card-parts-count {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .card-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 35px;
  }

  .card-meta-bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: var(--text-secondary);
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
