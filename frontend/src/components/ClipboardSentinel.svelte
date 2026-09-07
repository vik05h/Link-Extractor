<script lang="ts">
  import Icon from './icons/Icon.svelte';
  import { onMount, onDestroy } from 'svelte';
  import { playBypassSound, playClickSound } from '../utils/audio';
  import type { DetectedClip } from '../types';

  export let onResolveUrl: (url: string) => void = () => {};

  let detectedItem: DetectedClip | null = null;
  let autoDismissTimeout: any = null;

  function handleClipboardEvent(e: CustomEvent<DetectedClip>) {
    if (!e.detail || !e.detail.url) return;
    detectedItem = e.detail;
    playBypassSound();

    if (autoDismissTimeout) clearTimeout(autoDismissTimeout);
    autoDismissTimeout = setTimeout(() => {
      detectedItem = null;
    }, 12000);
  }

  function handleResolve() {
    if (detectedItem) {
      playClickSound();
      const url = detectedItem.url;
      detectedItem = null;
      onResolveUrl(url);
    }
  }

  function handleDismiss() {
    detectedItem = null;
  }

  onMount(() => {
    window.addEventListener('clipboard:detected' as any, handleClipboardEvent);
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('clipboard:detected' as any, handleClipboardEvent);
    }
  });
</script>

{#if detectedItem}
  <div class="sentinel-toast glass-panel">
    <div class="toast-indicator">
      <Icon name="bolt" size={20} color="var(--accent-primary)" strokeWidth={2.5} />
    </div>
    <div class="toast-content">
      <div class="toast-title">FitGirl Repack Link Detected in Clipboard!</div>
      <div class="toast-url" title={detectedItem.url}>{detectedItem.url}</div>
    </div>
    <div class="toast-actions">
      <button type="button" class="btn-primary btn-toast" on:click={handleResolve}>
        Resolve Now
      </button>
      <button type="button" class="btn-icon-toast" on:click={handleDismiss} aria-label="Dismiss notification">
        <Icon name="close" size={14} />
      </button>
    </div>
  </div>
{/if}

<style>
  .sentinel-toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 9999;
    width: 420px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: rgba(16, 22, 34, 0.95);
    border: 1px solid var(--accent-primary);
    box-shadow: 0 10px 32px rgba(0, 0, 0, 0.6), 0 0 20px var(--accent-glow);
    border-radius: var(--radius-md);
    animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .toast-indicator {
    font-size: 20px;
    color: var(--accent-primary);
  }

  .toast-content {
    flex: 1;
    min-width: 0;
  }

  .toast-title {
    font-size: 12px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .toast-url {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .toast-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .btn-toast {
    padding: 6px 12px;
    font-size: 11px;
  }

  .btn-icon-toast {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 14px;
    padding: 4px;
  }

  .btn-icon-toast:hover {
    color: var(--text-primary);
  }

  @keyframes slideUp {
    from { transform: translateY(100%); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
</style>
