<script lang="ts">
  import type { PartItem } from '../types';
  import { playClickSound, playBypassSound } from '../utils/audio';

  export let parts: PartItem[] = [];
  export let onCopyUrl: (url: string, index: number) => void = () => {};

  let hoveredPart: PartItem | null = null;
  let mousePos = { x: 0, y: 0 };

  function handleMouseEnter(part: PartItem, e: MouseEvent) {
    hoveredPart = part;
    mousePos = { x: e.clientX, y: e.clientY };
  }

  function handleMouseMove(e: MouseEvent) {
    if (hoveredPart) {
      mousePos = { x: e.clientX, y: e.clientY };
    }
  }

  function handleMouseLeave() {
    hoveredPart = null;
  }

  function handleClick(part: PartItem) {
    const targetUrl = part.direct_url || part.url;
    if (targetUrl) {
      playClickSound();
      onCopyUrl(targetUrl, part.index);
    }
  }

  // Reactive counts
  $: totalCount = parts.length;
  $: resolvedCount = parts.filter(p => p.status === 'resolved').length;
  $: activeCount = parts.filter(p => p.status === 'decrypting').length;
  $: excludedCount = parts.filter(p => p.excluded).length;
</script>

<div class="mosaic-container" role="region" aria-label="Repack Defrag Matrix" on:mousemove={handleMouseMove}>
  <!-- Stats Header Pill -->
  <div class="mosaic-header">
    <div class="mosaic-title-group">
      <span class="matrix-label">REPACK DEFRAG MATRIX</span>
      <span class="matrix-stats">
        <strong class="resolved-stat">{resolvedCount}</strong> / {totalCount} Resolved
        {#if activeCount > 0}
          <span class="active-badge">• {activeCount} Decrypting</span>
        {/if}
        {#if excludedCount > 0}
          <span class="excluded-badge">• {excludedCount} Filtered Out</span>
        {/if}
      </span>
    </div>

    <div class="legend-group">
      <span class="legend-item"><span class="dot dot-pending"></span> Queued</span>
      <span class="legend-item"><span class="dot dot-decrypting"></span> Decrypting</span>
      <span class="legend-item"><span class="dot dot-resolved"></span> Verified</span>
      <span class="legend-item"><span class="dot dot-excluded"></span> Excluded</span>
    </div>
  </div>

  <!-- Interactive Matrix Grid -->
  <div class="mosaic-grid" role="group" aria-label="Defrag part blocks" on:mouseleave={handleMouseLeave}>
    {#each parts as part (part.index)}
      <!-- Part Block -->
      <button 
        type="button"
        class="mosaic-block {part.status}" 
        class:excluded={part.excluded}
        on:mouseenter={(e) => handleMouseEnter(part, e)}
        on:mouseleave={handleMouseLeave}
        on:click={() => handleClick(part)}
        title={`Part ${part.index}`}
      >
        <span class="block-number">{part.index}</span>
        {#if part.status === 'decrypting'}
          <span class="scanline"></span>
        {/if}
      </button>
    {/each}
  </div>

  <!-- Integrated Cyber HUD Inspector (No stuck floating tooltips) -->
  <div class="mosaic-hud-inspector glass-panel">
    {#if hoveredPart}
      <div class="hud-left">
        <span class="part-badge">Part #{hoveredPart.index}</span>
        <span class="status-indicator {hoveredPart.status}">
          {hoveredPart.status.toUpperCase()}
        </span>
        <span class="hud-filename" title={hoveredPart.filename || `Part ${hoveredPart.index}`}>
          {hoveredPart.filename || `Part ${hoveredPart.index}`}
        </span>
      </div>

      <div class="hud-right">
        <span class="meta-size">{hoveredPart.size || '1-Byte Range Pending'}</span>
        <span class="hud-hint">Click block to copy URL</span>
      </div>
    {:else}
      <div class="hud-idle">
        <span>Hover over any block in the matrix to inspect part filename and size. Click to copy direct link.</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .mosaic-container {
    position: relative;
    width: 100%;
    padding: 16px;
    background: var(--bg-surface);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
  }

  .mosaic-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .mosaic-title-group {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .matrix-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: var(--accent-primary);
  }

  .matrix-stats {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .resolved-stat {
    color: var(--accent-primary);
  }

  .active-badge {
    color: var(--accent-secondary);
    animation: pulse 1.2s infinite;
  }

  .excluded-badge {
    color: var(--text-muted);
  }

  .legend-group {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 11px;
    color: var(--text-muted);
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 2px;
  }

  .dot-pending { background: rgba(255, 255, 255, 0.15); }
  .dot-decrypting { background: var(--accent-secondary); box-shadow: 0 0 6px var(--accent-secondary); }
  .dot-resolved { background: var(--accent-primary); box-shadow: 0 0 6px var(--accent-primary); }
  .dot-excluded { background: rgba(255, 255, 255, 0.05); border: 1px dashed rgba(255, 255, 255, 0.3); }

  /* Mosaic Responsive Grid */
  .mosaic-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(36px, 1fr));
    gap: 6px;
    max-height: 280px;
    overflow-y: auto;
    padding-right: 4px;
  }

  .mosaic-block {
    position: relative;
    height: 36px;
    border-radius: 6px;
    border: 1px solid var(--border-subtle);
    background: rgba(255, 255, 255, 0.04);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    overflow: hidden;
    transition: transform 0.12s ease, border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
  }

  .mosaic-block:hover {
    transform: scale(1.12);
    z-index: 10;
    border-color: #ffffff;
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.3);
  }

  .block-number {
    font-size: 11px;
    font-family: var(--font-mono);
    font-weight: 600;
  }

  /* Block States */
  .mosaic-block.pending {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.1);
  }

  .mosaic-block.decrypting {
    background: rgba(6, 182, 212, 0.2);
    border-color: var(--accent-secondary);
    color: #ffffff;
    box-shadow: 0 0 10px rgba(6, 182, 212, 0.4);
    animation: decryptPulse 1.2s infinite alternate ease-in-out;
  }

  .mosaic-block.resolved {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: #060d17;
    font-weight: 700;
    box-shadow: 0 0 12px var(--accent-glow);
    animation: popIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .mosaic-block.failed {
    background: rgba(244, 63, 94, 0.25);
    border-color: var(--status-expired);
    color: #ffffff;
  }

  .mosaic-block.excluded {
    opacity: 0.35;
    background: transparent;
    border: 1px dashed rgba(255, 255, 255, 0.2);
    cursor: not-allowed;
  }

  .scanline {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: rgba(255, 255, 255, 0.8);
    box-shadow: 0 0 6px var(--accent-secondary);
    animation: scan 1s infinite linear;
  }

  @keyframes decryptPulse {
    from { opacity: 0.7; }
    to { opacity: 1; filter: brightness(1.2); }
  }

  @keyframes scan {
    0% { top: 0; }
    100% { top: 100%; }
  }

  @keyframes popIn {
    0% { transform: scale(0.8); }
    70% { transform: scale(1.15); }
    100% { transform: scale(1); }
  }

  /* Integrated Cyber HUD Inspector */
  .mosaic-hud-inspector {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 14px;
    background: rgba(10, 14, 22, 0.85);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    min-height: 42px;
    margin-top: 10px;
    font-size: 11px;
  }

  .hud-left {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 0;
  }

  .part-badge {
    font-weight: 700;
    color: var(--accent-primary);
    font-family: var(--font-mono);
  }

  .status-indicator {
    font-size: 9px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .status-indicator.resolved { color: var(--accent-primary); background: rgba(16, 185, 129, 0.2); }
  .status-indicator.decrypting { color: var(--accent-secondary); background: rgba(6, 182, 212, 0.2); }
  .status-indicator.pending { color: var(--text-muted); background: rgba(255, 255, 255, 0.05); }
  .status-indicator.failed { color: var(--status-expired); background: rgba(244, 63, 94, 0.2); }

  .hud-filename {
    color: var(--text-primary);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 460px;
  }

  .hud-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .meta-size {
    color: var(--accent-secondary);
    font-weight: 600;
    font-family: var(--font-mono);
  }

  .hud-hint {
    color: var(--text-muted);
    font-size: 10px;
  }

  .hud-idle {
    color: var(--text-muted);
    font-size: 11px;
    width: 100%;
    text-align: center;
  }
</style>
