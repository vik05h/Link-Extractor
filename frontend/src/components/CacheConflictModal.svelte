<script lang="ts">
  import Icon from './icons/Icon.svelte';
  import { playClickSound } from '../utils/audio';

  export let isOpen: boolean = false;
  export let record: any = null;
  export let onSelectInstant: () => void = () => {};
  export let onSelectFresh: () => void = () => {};
  export let onClose: () => void = () => {};

  $: isExpired = !!(
    record?.is_expired || 
    record?.freshness === 'expired' || 
    (typeof record?.age_str === 'string' && (record.age_str.includes('day') || record.age_str.includes('week') || record.age_str.includes('month')))
  );

  function handleInstant() {
    playClickSound();
    onSelectInstant();
  }

  function handleFresh() {
    playClickSound();
    onSelectFresh();
  }

  function handleDismiss() {
    playClickSound();
    onClose();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!isOpen) return;
    if (e.key === 'Escape') {
      handleDismiss();
    } else if (e.key === '1') {
      handleInstant();
    } else if (e.key === '2') {
      handleFresh();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen && record}
  <div 
    class="modal-backdrop" 
    role="dialog" 
    aria-modal="true" 
    tabindex="-1"
    on:click={(e) => { if (e.target === e.currentTarget) handleDismiss(); }}
    on:keydown={(e) => e.key === 'Escape' && handleDismiss()}
  >
    <div class="modal-card glass-panel" role="document">
      <!-- Top Bar -->
      <div class="modal-header">
        <div class="modal-badge {isExpired ? 'badge-expired-warn' : ''}">
          <Icon name={isExpired ? "alert-triangle" : "shield-check"} size={14} color={isExpired ? "#ef4444" : "var(--accent-primary)"} />
          <span>{isExpired ? 'OUTDATED ARCHIVE DETECTED' : 'DATABASE ARCHIVE MATCH FOUND'}</span>
        </div>
        <button type="button" class="btn-close" on:click={handleDismiss} aria-label="Close dialog">
          <Icon name="close" size={16} />
        </button>
      </div>

      <!-- Game Showcase Banner -->
      <div class="game-showcase">
        {#if record.image_url}
          <img src={record.image_url} alt={record.title} class="showcase-cover" />
        {:else}
          <div class="showcase-cover-fallback">
            <Icon name="gamepad" size={28} color="var(--accent-primary)" />
          </div>
        {/if}

        <div class="showcase-details">
          <h2 class="showcase-title">{record.title || 'FitGirl Repack'}</h2>
          <div class="showcase-badges">
            <span class="meta-tag">
              <Icon name="package" size={12} />
              <span>{record.total_parts || (record.urls ? record.urls.length : 0)} Parts</span>
            </span>
            <span class="meta-tag">
              <Icon name="hard-drive" size={12} />
              <span>{record.total_size_str || '1-Byte Range Pending'}</span>
            </span>
            <span class="meta-tag age-tag {isExpired ? 'age-tag-expired' : ''}">
              <Icon name="clock" size={12} />
              <span>{record.age_str || 'Archived'} {isExpired ? '(Expired)' : ''}</span>
            </span>
            <span class="meta-tag source-tag">
              {record.source === 'history' ? 'Local History Archive' : 'Community Cloud Cache'}
            </span>
          </div>
        </div>
      </div>

      <!-- Prompt Subtitle -->
      <p class="prompt-text">
        {#if isExpired}
          The database contains cached links from <strong>{record.age_str || '2+ days ago'}</strong>. Because file hosters typically expire download mirrors after 24 hours, running a fresh extraction pass to update the database is strongly recommended:
        {:else}
          This title is already indexed in the database. Choose whether to load the pre-verified links instantly or run a fresh multi-tab resolution pass:
        {/if}
      </p>

      <!-- Comparison Decision Cards -->
      <div class="decision-grid">
        <!-- Option 1: Instant Links (0s wait) -->
        <div 
          class="decision-card instant-card {isExpired ? 'card-dimmed' : ''}" 
          role="button" 
          tabindex="0"
          on:click={handleInstant} 
          on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleInstant()}
        >
          <div class="card-accent-pill {isExpired ? 'expired-pill' : 'instant-pill'}">
            <Icon name={isExpired ? "clock" : "zap"} size={12} color={isExpired ? "#f59e0b" : "#10b981"} />
            <span>{isExpired ? 'OUTDATED (OFFLINE RISK)' : '0 SEC WAIT'}</span>
          </div>

          <div class="card-title">{isExpired ? 'Use Outdated Links' : 'Instant Links (0s)'}</div>
          <p class="card-desc">
            {isExpired 
              ? 'Attempt loading older mirrors into the extraction stage. Note: files may return HTTP 404 in JDownloader.' 
              : 'Load previously resolved and pre-verified download mirrors directly into the extraction stage with zero wait time.'}
          </p>

          <ul class="perk-list">
            {#if isExpired}
              <li>
                <Icon name="alert-triangle" size={12} color="#f59e0b" />
                <span style="color: #f59e0b;">Mirrors may be dead/offline</span>
              </li>
              <li>
                <Icon name="check-circle" size={12} color="#94a3b8" />
                <span>Instant Defrag Matrix population</span>
              </li>
            {:else}
              <li>
                <Icon name="check-circle" size={12} color="#10b981" />
                <span>Instant Defrag Matrix population</span>
              </li>
              <li>
                <Icon name="check-circle" size={12} color="#10b981" />
                <span>Ready for immediate JDownloader 2 push</span>
              </li>
              <li>
                <Icon name="check-circle" size={12} color="#10b981" />
                <span>Saves bandwidth and Cloudflare solve cycles</span>
              </li>
            {/if}
          </ul>

          <button type="button" class="btn-action {isExpired ? 'outdated-btn' : 'instant-btn'}">
            <Icon name={isExpired ? "clock" : "zap"} size={14} color={isExpired ? "inherit" : "#000"} />
            <span>{isExpired ? 'Use Outdated Links' : 'Use Instant Links'}</span>
          </button>
        </div>

        <!-- Option 2: Extract Fresh Links & Overwrite -->
        <div 
          class="decision-card fresh-card {isExpired ? 'card-recommended' : ''}" 
          role="button" 
          tabindex="0"
          on:click={handleFresh} 
          on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleFresh()}
        >
          <div class="card-accent-pill {isExpired ? 'recommended-pill' : 'fresh-pill'}">
            <Icon name="refresh" size={12} color={isExpired ? "#00f0a0" : "#06b6d4"} />
            <span>{isExpired ? 'RECOMMENDED (FRESH PASS)' : 'OVERWRITE DB'}</span>
          </div>

          <div class="card-title">Extract Fresh Links</div>
          <p class="card-desc">
            Re-run the headless browser pool, solve Turnstile tokens for every part, and update the database with the newest mirrors.
          </p>

          <ul class="perk-list">
            <li>
              <Icon name="check-circle" size={12} color={isExpired ? "#00f0a0" : "#06b6d4"} />
              <span>Re-verifies all active download mirrors</span>
            </li>
            <li>
              <Icon name="check-circle" size={12} color={isExpired ? "#00f0a0" : "#06b6d4"} />
              <span>Overwrites outdated links in the database</span>
            </li>
            <li>
              <Icon name="check-circle" size={12} color={isExpired ? "#00f0a0" : "#06b6d4"} />
              <span>Refreshes timestamp and updates community feed</span>
            </li>
          </ul>

          <button type="button" class="btn-action {isExpired ? 'recommended-btn' : 'fresh-btn'}">
            <Icon name="refresh" size={14} color={isExpired ? "#000" : "currentColor"} />
            <span>Re-extract & Overwrite</span>
          </button>
        </div>
      </div>

      <!-- Footer / Dismiss -->
      <div class="modal-footer">
        <button type="button" class="btn-cancel" on:click={handleDismiss}>
          Cancel and return to search
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
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
    animation: fadeIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .modal-card {
    width: 100%;
    max-width: 680px;
    background: linear-gradient(135deg, rgba(20, 24, 33, 0.94), rgba(12, 15, 22, 0.96));
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    box-shadow: 
      0 24px 64px -12px rgba(0, 0, 0, 0.8),
      0 0 40px rgba(16, 185, 129, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.15);
    padding: 1.5rem 1.75rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    animation: scaleUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .modal-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.65rem;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--accent-primary, #10b981);
    text-transform: uppercase;
  }

  .badge-expired-warn {
    background: rgba(239, 68, 68, 0.12);
    border-color: rgba(239, 68, 68, 0.35);
    color: #ef4444;
  }

  .btn-close {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary, #94a3b8);
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-close:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #fff;
  }

  /* Game Showcase */
  .game-showcase {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    padding: 0.85rem 1rem;
  }

  .showcase-cover {
    width: 64px;
    height: 84px;
    border-radius: 8px;
    object-fit: cover;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
    flex-shrink: 0;
  }

  .showcase-cover-fallback {
    width: 64px;
    height: 84px;
    border-radius: 8px;
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .showcase-details {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    min-width: 0;
  }

  .showcase-title {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: #f8fafc;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .showcase-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .meta-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.72rem;
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
  }

  .age-tag {
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.08);
    border-color: rgba(56, 189, 248, 0.2);
  }

  .age-tag-expired {
    color: #f87171;
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.3);
  }

  .source-tag {
    color: #a78bfa;
    background: rgba(167, 139, 250, 0.08);
    border-color: rgba(167, 139, 250, 0.2);
    font-weight: 600;
  }

  .prompt-text {
    margin: 0;
    font-size: 0.82rem;
    color: #cbd5e1;
    line-height: 1.45;
  }

  /* Decision Grid */
  .decision-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .decision-card {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 1.15rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    cursor: pointer;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    user-select: none;
  }

  .decision-card:hover {
    transform: translateY(-2px);
  }

  .card-dimmed {
    opacity: 0.85;
    border-color: rgba(255, 255, 255, 0.06);
  }

  .card-recommended {
    border-color: rgba(0, 240, 160, 0.45);
    background: linear-gradient(180deg, rgba(0, 240, 160, 0.09) 0%, rgba(255, 255, 255, 0.03) 100%);
    box-shadow: 0 8px 30px -6px rgba(0, 240, 160, 0.25);
  }

  .instant-card:hover {
    border-color: rgba(16, 185, 129, 0.45);
    background: linear-gradient(180deg, rgba(16, 185, 129, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
    box-shadow: 0 8px 24px -6px rgba(16, 185, 129, 0.2);
  }

  .fresh-card:hover {
    border-color: rgba(6, 182, 212, 0.45);
    background: linear-gradient(180deg, rgba(6, 182, 212, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
    box-shadow: 0 8px 24px -6px rgba(6, 182, 212, 0.2);
  }

  .card-accent-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    align-self: flex-start;
    padding: 0.2rem 0.5rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .instant-pill {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #10b981;
  }

  .fresh-pill {
    background: rgba(6, 182, 212, 0.12);
    border: 1px solid rgba(6, 182, 212, 0.3);
    color: #06b6d4;
  }

  .expired-pill {
    background: rgba(245, 158, 11, 0.14);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #f59e0b;
  }

  .recommended-pill {
    background: rgba(0, 240, 160, 0.15);
    border: 1px solid rgba(0, 240, 160, 0.4);
    color: #00f0a0;
  }

  .card-title {
    font-size: 0.98rem;
    font-weight: 700;
    color: #f1f5f9;
  }

  .card-desc {
    margin: 0;
    font-size: 0.74rem;
    color: #94a3b8;
    line-height: 1.4;
    flex-grow: 1;
  }

  .perk-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .perk-list li {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.7rem;
    color: #cbd5e1;
  }

  .btn-action {
    width: 100%;
    padding: 0.6rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    border: none;
    cursor: pointer;
    transition: all 0.18s ease;
  }

  .instant-btn {
    background: #10b981;
    color: #042f2e;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  }

  .instant-btn:hover {
    background: #34d399;
    box-shadow: 0 6px 18px rgba(16, 185, 129, 0.45);
  }

  .fresh-btn {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(6, 182, 212, 0.3);
    color: #38bdf8;
  }

  .fresh-btn:hover {
    background: rgba(6, 182, 212, 0.15);
    border-color: rgba(6, 182, 212, 0.5);
    color: #fff;
  }

  .outdated-btn {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #94a3b8;
  }

  .outdated-btn:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #f1f5f9;
  }

  .recommended-btn {
    background: #00f0a0;
    color: #002e1c;
    box-shadow: 0 4px 14px rgba(0, 240, 160, 0.35);
  }

  .recommended-btn:hover {
    background: #34d399;
    box-shadow: 0 6px 20px rgba(0, 240, 160, 0.5);
  }

  /* Footer */
  .modal-footer {
    display: flex;
    justify-content: center;
    padding-top: 0.25rem;
  }

  .btn-cancel {
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 0.74rem;
    cursor: pointer;
    text-decoration: underline;
    text-underline-offset: 3px;
    transition: color 0.18s ease;
  }

  .btn-cancel:hover {
    color: #cbd5e1;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes scaleUp {
    from { opacity: 0; transform: scale(0.96); }
    to { opacity: 1; transform: scale(1); }
  }

  @media (max-width: 600px) {
    .decision-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
