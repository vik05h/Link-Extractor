<script lang="ts">
  import Icon from '../icons/Icon.svelte';
  import { playSuccessChime } from '../../utils/audio';

  export let isOpen: boolean = false;
  export let onClose: () => void = () => {};
  export let onSuccess: (pin: string) => void = () => {};

  let keyInput: string = '';
  let keyError: string = '';
  let isVerifying: boolean = false;

  function focusKeyInput(el: HTMLElement) {
    setTimeout(() => el.focus(), 60);
  }

  async function verifyAdminKey() {
    const candidate = keyInput.trim();
    if (!candidate) {
      keyError = 'Please paste the admin key.';
      return;
    }

    isVerifying = true;
    keyError = '';

    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.verify_admin_key) {
      try {
        const res = await (window as any).pywebview.api.verify_admin_key(candidate);
        if (res && res.success) {
          playSuccessChime();
          keyError = '';
          keyInput = '';
          onSuccess(candidate);
        } else {
          keyError = res?.message || 'The database did not accept this key.';
        }
      } catch (err) {
        keyError = 'Authentication service unavailable.';
      } finally {
        isVerifying = false;
      }
    } else {
      // Standalone browser preview mode without pywebview bridge
      keyError = 'Admin authorization requires running inside the Link Extractor application.';
      isVerifying = false;
    }
  }

  $: if (!isOpen) {
    keyInput = '';
    keyError = '';
    isVerifying = false;
  }
</script>

{#if isOpen}
  <div 
    class="modal-backdrop sub-backdrop" 
    on:click={(e) => { if (e.target === e.currentTarget) onClose(); }} 
    on:keydown={(e) => { if (e.key === 'Escape') onClose(); }}
    role="dialog"
    aria-modal="true"
    aria-label="Admin Key Dialog"
    tabindex="-1"
  >
    <div 
      class="modal-card pin-card glass-panel" 
    >
      <div class="pin-header">
        <Icon name="lock" size={20} color="var(--accent-primary)" />
        <h3 id="admin-pin-title">ADMIN MODE UNLOCK</h3>
      </div>
      <p class="pin-subtext">Paste the Firebase database secret. The database itself checks it on every change, and it is kept only until you lock Admin Mode or close the app.</p>

      <form on:submit|preventDefault={verifyAdminKey}>
        <input 
          use:focusKeyInput
          type="password" 
          class="glass-input pin-input" 
          placeholder="Paste admin key..."
          bind:value={keyInput}
        />

        {#if keyError}
          <div class="pin-error">{keyError}</div>
        {/if}

        <div class="pin-actions">
          <button type="button" class="btn-secondary btn-sm" on:click={onClose}>
            Cancel
          </button>
          <button type="submit" class="btn-primary btn-sm" disabled={isVerifying}>
            {isVerifying ? 'Verifying...' : 'Unlock Admin Mode'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 8600;
    background: rgba(4, 7, 13, 0.9);
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

  .pin-card {
    width: 100%;
    max-width: 380px;
    padding: 22px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    border-radius: 18px;
    background: rgba(13, 17, 26, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 32px 64px rgba(0, 0, 0, 0.8), 0 0 32px rgba(0, 240, 160, 0.15);
    animation: popIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes popIn {
    from {
      opacity: 0;
      transform: scale(0.92);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .pin-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .pin-header h3 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 700;
    color: #ffffff;
  }
  .pin-subtext {
    margin: 0 0 8px 0;
    font-size: 0.78rem;
    color: var(--text-secondary);
  }
  .pin-input {
    width: 100%;
    margin-bottom: 8px;
  }
  .pin-error {
    font-size: 0.76rem;
    color: var(--status-expired);
    margin-bottom: 8px;
  }
  .pin-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
</style>
