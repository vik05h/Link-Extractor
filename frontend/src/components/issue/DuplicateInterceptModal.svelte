<script lang="ts">
  import Icon from '../icons/Icon.svelte';
  import type { IssueReport } from '../../types';

  export let isOpen: boolean = false;
  export let report: IssueReport | null = null;
  export let onClose: () => void = () => {};
  export let onViewInTracker: (subject: string) => void = () => {};
</script>

{#if isOpen && report}
  <div 
    class="modal-backdrop sub-backdrop" 
    on:click={(e) => { if (e.target === e.currentTarget) onClose(); }} 
    on:keydown={(e) => { if (e.key === 'Escape') onClose(); }}
    role="dialog"
    aria-modal="true"
    aria-label="Duplicate Issue Intercept"
    tabindex="-1"
  >
    <div 
      class="modal-card duplicate-card glass-panel" 
    >
      <div class="dup-header">
        <div class="dup-icon-halo">
          <Icon name="sparkles" size={24} color="#f59e0b" />
        </div>
        <div>
          <h3 id="dup-modal-title">THIS ISSUE IS ALREADY IN THE REPORT LOGS</h3>
          <p>We detected an identical issue already submitted by the community.</p>
        </div>
      </div>

      <div class="dup-body glass-panel">
        <div class="dup-subject-row">
          <span class="category-tag">{report.category || 'Bug Report'}</span>
          <span class="dup-title">{report.subject}</span>
          <span class="status-pill status-{report.status || 'open'}">
            {report.status?.toUpperCase() || 'OPEN'}
          </span>
        </div>

        <p class="dup-desc">{report.description}</p>

        {#if report.admin_remark}
          <div class="admin-remark-callout">
            <div class="remark-header">
              <Icon name="shield-check" size={14} color="#00f0a0" />
              <span>OFFICIAL ADMIN FIX GUIDANCE:</span>
            </div>
            <p class="remark-body">{report.admin_remark}</p>
          </div>
        {/if}

        <div class="dup-stat-badge">
          <Icon name="zap" size={13} color="#00f0a0" />
          <span>We've automatically added your vote (+1)! Total affected: {report.affected_users_count || 2} gamers.</span>
        </div>
      </div>

      <div class="dup-footer">
        <button 
          type="button" 
          class="btn-primary" 
          on:click={() => onViewInTracker(report?.subject || '')}
        >
          <span>View in Known Issues Tracker</span>
        </button>
      </div>
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

  .duplicate-card {
    width: 100%;
    max-width: 580px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    border-radius: 20px;
    background: rgba(13, 17, 26, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 32px 64px rgba(0, 0, 0, 0.8), 0 0 32px rgba(245, 158, 11, 0.15);
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

  .dup-header {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .dup-icon-halo {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .dup-header h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 700;
    color: #ffffff;
  }
  .dup-header p {
    margin: 2px 0 0 0;
    font-size: 0.78rem;
    color: var(--text-secondary);
  }

  .dup-body {
    padding: 16px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .dup-subject-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .category-tag {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-secondary);
    text-transform: uppercase;
  }

  .dup-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: #ffffff;
    flex: 1;
  }

  .status-pill {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.68rem;
    font-weight: 700;
  }
  .status-pill.status-fixed {
    background: rgba(0, 240, 160, 0.15);
    border: 1px solid rgba(0, 240, 160, 0.4);
    color: #00f0a0;
  }
  .status-pill.status-investigating {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.4);
    color: #f59e0b;
  }
  .status-pill.status-open {
    background: rgba(14, 165, 233, 0.15);
    border: 1px solid rgba(14, 165, 233, 0.4);
    color: #38bdf8;
  }

  .dup-desc {
    margin: 0;
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.45;
  }

  .admin-remark-callout {
    padding: 10px 14px;
    border-radius: 10px;
    background: rgba(0, 240, 160, 0.08);
    border: 1px solid rgba(0, 240, 160, 0.25);
    margin-top: 6px;
  }
  .remark-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #00f0a0;
    margin-bottom: 4px;
  }
  .remark-body {
    margin: 0;
    font-size: 0.82rem;
    line-height: 1.45;
    color: #ffffff;
  }

  .dup-stat-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #00f0a0;
    margin-top: 4px;
  }

  .dup-footer {
    display: flex;
    justify-content: flex-end;
  }
</style>
