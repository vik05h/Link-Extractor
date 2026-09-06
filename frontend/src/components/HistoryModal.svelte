<script lang="ts">
  import Icon from './icons/Icon.svelte';
  import { playClickSound } from '../utils/audio';
  import type { HistoryRecord } from '../types';

  export let isOpen: boolean = false;
  export let onClose: () => void = () => {};
  export let onLoadHistoryItem: (rec: HistoryRecord) => void = () => {};
  export let onPushJd2: (urls: string[], title: string) => void = () => {};

  let records: HistoryRecord[] = [];
  let searchQuery: string = '';
  let isLoading = false;

  export function loadHistory() {
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      isLoading = true;
      (window as any).pywebview.api.get_history().then((data: HistoryRecord[]) => {
        records = data || [];
        isLoading = false;
      });
    }
  }

  $: if (isOpen) {
    loadHistory();
  }

  function handleDelete(id: number, e: MouseEvent) {
    e.stopPropagation();
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.delete_history_item(id).then(() => {
        records = records.filter(r => r.id !== id);
      });
    }
  }

  function handleSelect(rec: any) {
    playClickSound();
    onClose();
    onLoadHistoryItem(rec);
  }

  function handlePush(rec: any, e: MouseEvent) {
    e.stopPropagation();
    playClickSound();
    onPushJd2(rec.resolved_links || [], rec.game_title);
  }

  $: filteredRecords = records.filter(r => 
    !searchQuery || r.game_title.toLowerCase().includes(searchQuery.toLowerCase())
  );
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
      <div class="modal-header">
        <div class="modal-title">
          <Icon name="history" size={16} color="var(--accent-primary)" />
          <span>EXTRACTION VAULT ARCHIVE</span>
        </div>
        <button type="button" class="btn-close" on:click={onClose} aria-label="Close dialog">
          <Icon name="close" size={16} />
        </button>
      </div>

      <div class="modal-search">
        <input 
          type="text" 
          class="glass-input" 
          placeholder="Search saved repacks in SQLite history..." 
          bind:value={searchQuery}
        />
      </div>

      <div class="modal-body">
        {#if isLoading}
          <div class="loading-state">Loading history...</div>
        {:else if filteredRecords.length === 0}
          <div class="empty-state">No saved extractions found in database.</div>
        {:else}
          <div class="records-list">
            {#each filteredRecords as r (r.id)}
              <div class="history-item glass-card">
                <button 
                  type="button" 
                  class="history-info-btn" 
                  on:click={() => handleSelect(r)}
                  title="Load {r.game_title} into resolver"
                >
                  <div class="history-title">{r.game_title}</div>
                  <div class="history-meta">
                    <span>{r.parts_count} Parts</span>
                    <span>•</span>
                    <span class="meta-size">{r.total_size || '0 B'}</span>
                    <span>•</span>
                    <span>{r.created_at || 'Recently'}</span>
                  </div>
                </button>

                <div class="history-actions">
                  <button 
                    type="button" 
                    class="btn-secondary btn-sm"
                    title="Push directly to JDownloader 2"
                    on:click={(e) => handlePush(r, e)}
                  >
                    <span>Push JD2</span>
                  </button>
                  <button 
                    type="button" 
                    class="btn-icon-sm btn-delete"
                    title="Delete record from SQLite"
                    on:click={(e) => handleDelete(r.id, e)}
                  >
                    <Icon name="trash" size={14} />
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    animation: backdropFadeIn 0.22s ease-out;
  }

  .modal-card {
    width: 600px;
    max-width: 95%;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    background: rgba(14, 18, 27, 0.96);
    box-shadow: 0 24px 48px rgba(0, 0, 0, 0.8), 0 0 24px rgba(0, 0, 0, 0.5);
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
      transform: scale(0.94) translateY(8px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
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
    font-family: var(--font-display);
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
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

  .modal-search {
    padding: 12px 20px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
  }

  .records-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .history-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 14px;
    cursor: pointer;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    text-align: left;
    width: 100%;
  }

  .history-item:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: var(--accent-primary);
  }

  .history-info-btn {
    flex: 1;
    min-width: 0;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    text-align: left;
    cursor: pointer;
    color: inherit;
    font-family: inherit;
  }

  .history-title {
    font-family: var(--font-display);
    font-size: 13.5px;
    font-weight: 700;
    letter-spacing: 0.015em;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .history-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .meta-size {
    color: var(--accent-primary);
    font-weight: 600;
  }

  .history-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .btn-secondary.btn-sm {
    height: 30px;
    padding: 0 12px;
    font-size: 12px;
    font-weight: 600;
  }

  .btn-delete {
    width: 30px;
    height: 30px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .btn-delete:hover {
    background: rgba(244, 63, 94, 0.14);
    border-color: rgba(244, 63, 94, 0.45);
    color: #f43f5e;
    box-shadow: 0 0 12px rgba(244, 63, 94, 0.25);
    transform: scale(1.05);
  }

  .btn-delete:active {
    transform: scale(0.95);
  }

  .loading-state, .empty-state {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
  }
</style>
