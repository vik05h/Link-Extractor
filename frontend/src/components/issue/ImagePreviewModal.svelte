<script lang="ts">
  import Icon from '../icons/Icon.svelte';

  export let imageUrl: string = '';
  export let onClose: () => void = () => {};
</script>

{#if imageUrl}
  <div 
    class="modal-backdrop image-backdrop" 
    on:click={(e) => { if (e.target === e.currentTarget) onClose(); }} 
    on:keydown={(e) => { if (e.key === 'Escape') onClose(); }}
    role="dialog"
    aria-modal="true"
    aria-label="Screenshot Evidence Preview"
    tabindex="-1"
  >
    <div 
      class="image-modal-card" 
    >
      <div class="image-modal-header">
        <span>Screenshot Evidence</span>
        <button type="button" class="btn-close" on:click={onClose} aria-label="Close screenshot preview">
          <Icon name="close" size={16} />
        </button>
      </div>
      <img src={imageUrl} alt="Enlarged screenshot" class="full-img" />
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 8700;
    background: rgba(0, 0, 0, 0.92);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: fadeIn 0.2s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .image-modal-card {
    max-width: 90vw;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    border-radius: 14px;
    overflow: hidden;
    background: #0d111a;
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 32px 64px rgba(0, 0, 0, 0.9);
  }

  .image-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    color: #ffffff;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .btn-close {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 4px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }
  .btn-close:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.1);
  }

  .full-img {
    max-width: 100%;
    max-height: calc(90vh - 50px);
    object-fit: contain;
  }
</style>
