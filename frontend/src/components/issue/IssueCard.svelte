<script lang="ts">
  import Icon from '../icons/Icon.svelte';
  import { playClickSound } from '../../utils/audio';
  import type { IssueReport } from '../../types';

  export let report: IssueReport;
  export let isAdminMode: boolean = false;
  export let isUpvoted: boolean = false;
  export let onUpvote: (id: string) => void = () => {};
  export let onPreviewImage: (url: string) => void = () => {};
  export let onAdminSave: (id: string, status: string, remark: string) => Promise<void> | void = () => {};
  export let onAdminDelete: (id: string) => Promise<void> | void = () => {};

  let editingStatus: string = report.status || 'open';
  let editingRemark: string = report.admin_remark || '';
  let isSaving: boolean = false;
  let isDeleting: boolean = false;

  $: editingStatus = report.status || 'open';
  $: editingRemark = report.admin_remark || '';

  function formatDate(isoStr?: string): string {
    if (!isoStr) return 'Recently';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Recently';
    }
  }

  async function handleSaveClick() {
    isSaving = true;
    try {
      await onAdminSave(report.id, editingStatus, editingRemark);
    } finally {
      isSaving = false;
    }
  }

  async function handleDeleteClick() {
    if (confirm(`Are you sure you want to permanently delete this report?\n\nSubject: "${report.subject}"`)) {
      isDeleting = true;
      try {
        await onAdminDelete(report.id);
      } finally {
        isDeleting = false;
      }
    }
  }
</script>

<div class="report-card glass-panel" class:card-fixed={report.status === 'fixed'}>
  <!-- Card Header -->
  <div class="card-top-row">
    <div class="card-title-group">
      <span class="category-tag">{report.category || 'Bug Report'}</span>
      <h3 class="card-subject">{report.subject}</h3>
    </div>

    <div class="card-status-group">
      <span class="status-pill status-{report.status || 'open'}">
        {report.status === 'fixed' ? 'FIXED' : (report.status === 'investigating' ? 'INVESTIGATING' : 'OPEN')}
      </span>
    </div>
  </div>

  <!-- Card Meta Info -->
  <div class="card-meta-row">
    <span class="meta-item">
      <Icon name="clock" size={12} color="var(--text-muted)" />
      <span>{formatDate(report.created_at)}</span>
    </span>

    <span class="meta-item affected-badge" title="Number of gamers who reported or voted for this issue">
      <Icon name="zap" size={12} color="#00f0a0" />
      <span>{report.affected_users_count || 1} {report.affected_users_count === 1 ? 'Gamer' : 'Gamers'} Affected</span>
    </span>

    {#if report.app_version}
      <span class="meta-item version-tag">{report.app_version}</span>
    {/if}
  </div>

  <!-- Description -->
  <p class="card-desc">{report.description}</p>

  <!-- Screenshot Thumbnail Preview -->
  {#if report.screenshot_data}
    <div class="screenshot-thumb-wrapper">
      <button 
        type="button" 
        class="thumb-btn"
        on:click={() => onPreviewImage(report.screenshot_data || '')}
        aria-label="View full screenshot evidence"
      >
        <img src={report.screenshot_data} alt="Screenshot evidence" class="thumb-img" />
        <span class="thumb-overlay">
          <Icon name="image" size={14} color="#ffffff" />
          <span>View Full Screenshot</span>
        </span>
      </button>
    </div>
  {/if}

  <!-- Official Admin Remark Callout -->
  {#if report.admin_remark}
    <div class="admin-remark-callout">
      <div class="remark-header">
        <Icon name="shield-check" size={14} color="#00f0a0" />
        <span>OFFICIAL ADMIN FIX GUIDANCE:</span>
      </div>
      <p class="remark-body">{report.admin_remark}</p>
    </div>
  {/if}

  <!-- Card Footer Actions -->
  <div class="card-actions-bar">
    <button 
      type="button" 
      class="btn-vote"
      class:voted={isUpvoted}
      disabled={isUpvoted}
      on:click={() => { playClickSound(); onUpvote(report.id); }}
      aria-label={isUpvoted ? 'Voted' : 'I have this issue too'}
    >
      <Icon name="thumbs-up" size={13} color={isUpvoted ? '#00f0a0' : 'currentColor'} />
      <span>{isUpvoted ? 'Voted' : 'I have this issue too (+1)'}</span>
    </button>
  </div>

  <!-- Admin Tools Panel (when unlocked) -->
  {#if isAdminMode}
    <div class="admin-tools-panel">
      <div class="admin-panel-top">
        <div class="admin-panel-title">
          <Icon name="settings" size={13} color="var(--accent-primary)" />
          <span>ADMIN EDIT: {report.id}</span>
        </div>
        <button 
          type="button" 
          class="btn-delete-report"
          title="Delete this ticket permanently"
          disabled={isDeleting}
          on:click={handleDeleteClick}
        >
          <Icon name="trash" size={12} color="#f43f5e" />
          <span>{isDeleting ? 'Deleting...' : 'Delete Report'}</span>
        </button>
      </div>

      <div class="admin-edit-grid">
        <div>
          <label for="status-select-{report.id}" class="admin-label">Status</label>
          <select 
            id="status-select-{report.id}"
            class="glass-input admin-select"
            bind:value={editingStatus}
          >
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="fixed">Fixed</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <div class="admin-remark-field">
          <label for="remark-input-{report.id}" class="admin-label">Official Fix Guidance / Remark</label>
          <input 
            id="remark-input-{report.id}"
            type="text" 
            class="glass-input admin-text"
            placeholder="e.g. Fixed in v3.8.0, or workaround: disable VPN..."
            bind:value={editingRemark}
          />
        </div>

        <button 
          type="button" 
          class="btn-primary btn-sm btn-save-admin"
          disabled={isSaving}
          on:click={handleSaveClick}
        >
          <Icon name="check" size={13} color="#ffffff" strokeWidth={2.5} />
          <span>{isSaving ? 'Saving...' : 'Save'}</span>
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .report-card {
    padding: 16px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: border-color 0.2s ease;
  }
  .report-card:hover {
    border-color: rgba(255, 255, 255, 0.15);
  }
  .report-card.card-fixed {
    border-left: 3px solid #00f0a0;
  }

  .card-top-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .card-title-group {
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

  .card-subject {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 700;
    color: #ffffff;
  }

  .status-pill {
    padding: 3px 9px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.04em;
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

  .card-meta-row {
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 0.76rem;
    color: var(--text-muted);
  }

  .meta-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .affected-badge {
    color: var(--text-secondary);
    font-weight: 600;
  }

  .version-tag {
    background: rgba(255, 255, 255, 0.05);
    padding: 1px 6px;
    border-radius: 4px;
  }

  .card-desc {
    margin: 4px 0 0 0;
    font-size: 0.84rem;
    line-height: 1.5;
    color: var(--text-secondary);
    white-space: pre-wrap;
  }

  /* Screenshot thumbnail */
  .screenshot-thumb-wrapper {
    margin-top: 4px;
  }
  .thumb-btn {
    position: relative;
    width: 140px;
    height: 75px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.15);
    background: #000;
    cursor: pointer;
    padding: 0;
  }
  .thumb-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .thumb-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    font-size: 0.7rem;
    color: #fff;
    opacity: 0;
    transition: opacity 0.2s;
  }
  .thumb-btn:hover .thumb-overlay {
    opacity: 1;
  }

  /* Admin Remark Callout */
  .admin-remark-callout {
    padding: 10px 14px;
    border-radius: 10px;
    background: rgba(0, 240, 160, 0.08);
    border: 1px solid rgba(0, 240, 160, 0.25);
    box-shadow: 0 0 16px rgba(0, 240, 160, 0.08);
  }
  .remark-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #00f0a0;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }
  .remark-body {
    margin: 0;
    font-size: 0.82rem;
    line-height: 1.45;
    color: #ffffff;
  }

  .card-actions-bar {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-top: 6px;
  }

  .btn-vote {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: var(--text-secondary);
    transition: all 0.2s ease;
  }
  .btn-vote:hover:not(:disabled) {
    background: rgba(0, 240, 160, 0.15);
    border-color: rgba(0, 240, 160, 0.3);
    color: #ffffff;
  }
  .btn-vote.voted {
    background: rgba(0, 240, 160, 0.15);
    border-color: rgba(0, 240, 160, 0.4);
    color: #00f0a0;
    cursor: default;
  }

  /* Admin Tools Panel */
  .admin-tools-panel {
    margin-top: 8px;
    padding: 12px;
    border-radius: 10px;
    background: rgba(0, 0, 0, 0.4);
    border: 1px dashed rgba(0, 240, 160, 0.3);
  }
  .admin-panel-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }
  .admin-panel-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--accent-primary);
  }
  .btn-delete-report {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    color: #f43f5e;
    background: rgba(244, 63, 94, 0.1);
    border: 1px solid rgba(244, 63, 94, 0.28);
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .btn-delete-report:hover:not(:disabled) {
    background: rgba(244, 63, 94, 0.22);
    border-color: rgba(244, 63, 94, 0.55);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(244, 63, 94, 0.25);
  }
  .btn-delete-report:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .admin-edit-grid {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    flex-wrap: wrap;
  }
  .admin-label {
    display: block;
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-bottom: 4px;
  }
  .admin-select {
    padding: 6px 10px;
    font-size: 0.8rem;
    width: 140px;
  }
  .admin-remark-field {
    flex: 1;
    min-width: 260px;
  }
  .admin-text {
    width: 100%;
    padding: 6px 10px;
    font-size: 0.8rem;
  }
  .btn-save-admin {
    padding: 6px 14px;
  }
</style>
