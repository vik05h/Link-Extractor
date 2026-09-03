<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import type { PartItem } from './DefragMosaic.svelte';

  export let parts: PartItem[] = [];
  const dispatch = createEventDispatcher();

  let keepOnlyEnglish = true;
  let excludeBonuses = false;

  // Classify a filename
  export function classifyPart(filename: string): 'core' | 'language' | 'optional' {
    const fn = (filename || '').toLowerCase();
    if (fn.includes('fg-selective-english') || fn.includes('selective-english')) {
      return 'core'; // English is treated as core for English users
    }
    if (fn.includes('fg-selective-') || fn.includes('selective-')) {
      return 'language';
    }
    if (fn.includes('fg-optional-') || fn.includes('optional-') || fn.includes('soundtrack') || fn.includes('bonus')) {
      return 'optional';
    }
    return 'core';
  }

  function applyFilter() {
    let updatedParts = parts.map(p => {
      const cat = classifyPart(p.filename || '');
      p.category = cat;
      let isExcluded = false;

      if (cat === 'language' && keepOnlyEnglish) {
        isExcluded = true;
      }
      if (cat === 'optional' && excludeBonuses) {
        isExcluded = true;
      }

      p.excluded = isExcluded;
      return p;
    });

    dispatch('filterChange', {
      parts: updatedParts,
      activeParts: updatedParts.filter(p => !p.excluded)
    });
  }

  // Count categories
  $: languagePacksCount = parts.filter(p => classifyPart(p.filename || '') === 'language').length;
  $: bonusPacksCount = parts.filter(p => classifyPart(p.filename || '') === 'optional').length;
  $: hasFilterableParts = languagePacksCount > 0 || bonusPacksCount > 0;
</script>

{#if hasFilterableParts}
  <div class="selective-filter-bar glass-panel">
    <div class="filter-heading">
      <Icon name="filter" size={14} color="var(--accent-primary)" />
      <span class="filter-label">BANDWIDTH SAVER & SELECTIVE DOWNLOAD:</span>
    </div>

    <div class="filter-chips">
      {#if languagePacksCount > 0}
        <button 
          type="button"
          class="filter-chip" 
          class:active={keepOnlyEnglish}
          on:click={() => { keepOnlyEnglish = !keepOnlyEnglish; applyFilter(); }}
        >
          <span class="chip-status">
            {#if keepOnlyEnglish}
              <Icon name="check" size={12} color="var(--accent-primary)" />
            {:else}
              <span class="chip-circle"></span>
            {/if}
          </span>
          <span>English Only (Skip {languagePacksCount} non-English dubs)</span>
        </button>
      {/if}

      {#if bonusPacksCount > 0}
        <button 
          type="button"
          class="filter-chip" 
          class:active={excludeBonuses}
          on:click={() => { excludeBonuses = !excludeBonuses; applyFilter(); }}
        >
          <span class="chip-status">
            {#if excludeBonuses}
              <Icon name="check" size={12} color="var(--accent-primary)" />
            {:else}
              <span class="chip-circle"></span>
            {/if}
          </span>
          <span>Skip {bonusPacksCount} Bonus/4K Packs</span>
        </button>
      {/if}
    </div>
  </div>
{/if}

<style>
  .selective-filter-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    padding: 10px 16px;
    background: rgba(16, 22, 34, 0.7);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: var(--radius-sm);
    margin-bottom: 12px;
  }

  .filter-heading {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    color: var(--accent-primary);
    letter-spacing: 0.5px;
  }

  .filter-chips {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--border-subtle);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .filter-chip:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: var(--border-hover);
    color: var(--text-primary);
  }

  .filter-chip.active {
    background: rgba(16, 185, 129, 0.18);
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }

  .chip-status {
    font-family: var(--font-mono);
    font-weight: 700;
  }
</style>
