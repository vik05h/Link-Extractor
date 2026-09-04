<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, playSuccessChime } from '../utils/audio';
  import type { IssueReport } from '../types';

  import IssueCard from './issue/IssueCard.svelte';
  import SubmitReportForm from './issue/SubmitReportForm.svelte';
  import DuplicateInterceptModal from './issue/DuplicateInterceptModal.svelte';
  import AdminPinModal from './issue/AdminPinModal.svelte';
  import ImagePreviewModal from './issue/ImagePreviewModal.svelte';

  export let isOpen: boolean = false;
  export let onClose: () => void = () => {};
  export let onShowToast: (msg: string) => void = () => {};

  // View state: 'tracker' (Known Issues) or 'submit' (Submit Report)
  let activeTab: 'tracker' | 'submit' = 'tracker';

  // Public Reports Board State
  let reports: IssueReport[] = [];
  let isLoadingReports: boolean = false;
  let searchQuery: string = '';
  let statusFilter: 'all' | 'open' | 'investigating' | 'fixed' = 'all';

  // Admin Mode State
  let isAdminMode: boolean = false;
  let sessionAdminPin: string = '';
  let showPinModal: boolean = false;

  // Sub-modal states
  let duplicateModalOpen: boolean = false;
  let interceptedReport: IssueReport | null = null;
  let previewImageUrl: string = '';

  // Pending submission payload for force-create bypass
  let pendingReportPayload: { category: string; subject: string; description: string; screenshotData: string } | null = null;

  // Upvoted IDs (persisted locally so user doesn't spam)
  let upvotedIds: Set<string> = new Set();

  // Reference to submit form for pasting
  let submitFormRef: SubmitReportForm;
  let isSubmittingReport: boolean = false;

  onMount(() => {
    if (typeof window !== 'undefined') {
      const storedVotes = localStorage.getItem('le_upvoted_reports');
      if (storedVotes) {
        try {
          upvotedIds = new Set(JSON.parse(storedVotes));
        } catch {}
      }
    }
  });

  $: if (isOpen) {
    loadReports();
  }

  // Load public reports from Firebase via Bridge
  async function loadReports() {
    isLoadingReports = true;
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.get_all_reports) {
      try {
        const res = await (window as any).pywebview.api.get_all_reports();
        if (res && res.reports) {
          reports = res.reports;
        }
      } catch (err) {
        console.error('Failed to load reports:', err);
      } finally {
        isLoadingReports = false;
      }
    } else {
      isLoadingReports = false;
    }
  }

  // Filtered reports for Known Issues tab
  $: filteredReports = reports.filter(r => {
    const matchQuery = !searchQuery || 
      (r.subject || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.admin_remark || '').toLowerCase().includes(searchQuery.toLowerCase());

    const matchStatus = statusFilter === 'all' || (r.status || 'open').toLowerCase() === statusFilter;
    return matchQuery && matchStatus;
  });

  // Clipboard Paste listener (active only when modal is open and on submit tab)
  function handleWindowPaste(e: ClipboardEvent) {
    if (!isOpen || activeTab !== 'submit') return;
    submitFormRef?.handlePaste(e);
  }

  // Submit Report Handler (supports forceCreate to bypass duplicate intercept)
  async function handleSubmitReport(payload: { category: string; subject: string; description: string; screenshotData: string }, forceCreate: boolean = false) {
    isSubmittingReport = true;
    pendingReportPayload = payload;

    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.submit_report) {
      try {
        const res = await (window as any).pywebview.api.submit_report({
          subject: payload.subject,
          category: payload.category,
          description: payload.description,
          screenshot_data: payload.screenshotData,
          force_create: forceCreate
        });

        if (res.is_duplicate && res.record) {
          // Intercept duplicate!
          interceptedReport = res.record;
          duplicateModalOpen = true;
          upvotedIds.add(res.record.id);
          upvotedIds = new Set(upvotedIds);
          localStorage.setItem('le_upvoted_reports', JSON.stringify(Array.from(upvotedIds)));
          loadReports();
        } else if (res.success) {
          duplicateModalOpen = false;
          pendingReportPayload = null;
          playSuccessChime();
          onShowToast('Report submitted successfully! Thank you for helping improve Link Extractor.');
          submitFormRef?.resetForm();
          activeTab = 'tracker';
          loadReports();
        } else {
          onShowToast(res.message || 'Failed to submit report.');
        }
      } catch (err) {
        onShowToast('Error connecting to reporting server.');
      } finally {
        isSubmittingReport = false;
      }
    } else {
      isSubmittingReport = false;
      onShowToast('Reporting server bridge unavailable in preview mode.');
    }
  }

  // Force-create bypass when user explicitly chooses "Different Issue? Submit Anyway"
  function handleSubmitAnyway() {
    duplicateModalOpen = false;
    if (pendingReportPayload) {
      handleSubmitReport(pendingReportPayload, true);
    }
  }

  // Upvote an existing report (+1)
  async function handleUpvote(reportId: string) {
    if (upvotedIds.has(reportId)) return;

    upvotedIds.add(reportId);
    upvotedIds = new Set(upvotedIds);
    localStorage.setItem('le_upvoted_reports', JSON.stringify(Array.from(upvotedIds)));

    reports = reports.map(r => {
      if (r.id === reportId) {
        return { ...r, affected_users_count: (r.affected_users_count || 1) + 1 };
      }
      return r;
    });

    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.upvote_report) {
      (window as any).pywebview.api.upvote_report(reportId).catch(() => {});
    }
    onShowToast('Thanks! Your vote was added to this issue.');
  }

  function handleUpvoteExisting(id: string, matchedSubject: string) {
    handleUpvote(id);
    activeTab = 'tracker';
    searchQuery = matchedSubject;
  }

  // Admin Pin Authentication (Session-based, no hardcoded PIN in frontend)
  function handleAdminUnlockSuccess(pin: string) {
    isAdminMode = true;
    sessionAdminPin = pin;
    showPinModal = false;
    onShowToast('Admin Mode unlocked! You can now update ticket statuses and post official remarks.');
  }

  function handleExitAdminMode() {
    isAdminMode = false;
    sessionAdminPin = '';
    onShowToast('Admin Mode locked.');
  }

  // Admin Save Status & Remark
  async function handleAdminSave(reportId: string, newStatus: string, newRemark: string) {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.admin_update_report) {
      try {
        const res = await (window as any).pywebview.api.admin_update_report({
          report_id: reportId,
          status: newStatus,
          admin_remark: newRemark,
          admin_pin: sessionAdminPin
        });

        if (res && res.success) {
          playSuccessChime();
          onShowToast('Ticket updated successfully!');
          reports = reports.map(r => {
            if (r.id === reportId) {
              return { ...r, status: newStatus as any, admin_remark: newRemark };
            }
            return r;
          });
        } else {
          onShowToast(res?.message || 'Failed to update ticket.');
        }
      } catch (err) {
        onShowToast('Network error updating ticket.');
      }
    }
  }

  // Admin Delete Report
  async function handleAdminDelete(reportId: string) {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.admin_delete_report) {
      try {
        const res = await (window as any).pywebview.api.admin_delete_report({
          report_id: reportId,
          admin_pin: sessionAdminPin
        });

        if (res && res.success) {
          playSuccessChime();
          onShowToast('Report permanently deleted.');
          reports = reports.filter(r => r.id !== reportId);
        } else {
          onShowToast(res?.message || 'Failed to delete report.');
        }
      } catch (err) {
        onShowToast('Network error deleting report.');
      }
    }
  }

  function handleDuplicateViewInTracker(subjectText: string) {
    duplicateModalOpen = false;
    activeTab = 'tracker';
    searchQuery = subjectText;
  }
</script>

<svelte:window on:paste={handleWindowPaste} />

{#if isOpen}
  <div 
    class="modal-backdrop" 
    on:click={(e) => { if (e.target === e.currentTarget) onClose(); }} 
    on:keydown={(e) => { if (e.key === 'Escape') onClose(); }}
    role="dialog" 
    aria-modal="true" 
    aria-label="Community Issue Center"
    tabindex="-1"
  >
    <div 
      class="modal-card glass-panel" 
    >
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="modal-title-row">
          <div class="modal-icon-halo">
            <Icon name="bug" size={18} color="var(--accent-primary)" />
          </div>
          <div>
            <h2 id="main-issue-modal-title" class="modal-title">COMMUNITY ISSUE CENTER & BUG TRACKER</h2>
            <p class="modal-subtitle">Public bug tracking, live duplicate prevention & official fix guidance</p>
          </div>
        </div>

        <div class="header-actions">
          {#if isAdminMode}
            <button 
              type="button" 
              class="btn-admin-badge unlocked" 
              title="Admin Mode Active (Click to lock)"
              on:click={handleExitAdminMode}
            >
              <Icon name="unlock" size={13} color="#00f0a0" />
              <span>ADMIN MODE</span>
            </button>
          {:else}
            <button 
              type="button" 
              class="btn-admin-badge locked" 
              title="Unlock Admin Tools (Vikash only)"
              on:click={() => showPinModal = true}
            >
              <Icon name="lock" size={13} />
              <span>Admin</span>
            </button>
          {/if}

          <button type="button" class="btn-close" on:click={onClose} aria-label="Close dialog">
            <Icon name="close" size={16} />
          </button>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="tabs-header-bar">
        <button 
          type="button" 
          class="tab-nav-btn" 
          class:active={activeTab === 'tracker'}
          on:click={() => { activeTab = 'tracker'; playClickSound(); loadReports(); }}
        >
          <Icon name="grid" size={14} />
          <span>Known Issues & Fixes ({reports.length})</span>
        </button>

        <button 
          type="button" 
          class="tab-nav-btn" 
          class:active={activeTab === 'submit'}
          on:click={() => { activeTab = 'submit'; playClickSound(); }}
        >
          <Icon name="bolt" size={14} />
          <span>Submit a Report</span>
        </button>
      </div>

      <!-- Tab 1: Known Issues & Public Board -->
      {#if activeTab === 'tracker'}
        <div class="tracker-viewport">
          <!-- Filter Controls Bar -->
          <div class="filter-controls-row">
            <div class="search-box">
              <Icon name="search" size={14} color="var(--text-muted)" />
              <input 
                type="text" 
                class="glass-input search-input" 
                placeholder="Search issues by keyword, title, or fix advice..."
                bind:value={searchQuery}
              />
            </div>

            <div class="status-pills-group">
              <button 
                type="button" 
                class="pill-btn" 
                class:active={statusFilter === 'all'}
                on:click={() => statusFilter = 'all'}
              >
                All ({reports.length})
              </button>

              <button 
                type="button" 
                class="pill-btn pill-open" 
                class:active={statusFilter === 'open'}
                on:click={() => statusFilter = 'open'}
              >
                Open ({reports.filter(r => (r.status || 'open') === 'open').length})
              </button>

              <button 
                type="button" 
                class="pill-btn pill-investigating" 
                class:active={statusFilter === 'investigating'}
                on:click={() => statusFilter = 'investigating'}
              >
                Investigating ({reports.filter(r => r.status === 'investigating').length})
              </button>

              <button 
                type="button" 
                class="pill-btn pill-fixed" 
                class:active={statusFilter === 'fixed'}
                on:click={() => statusFilter = 'fixed'}
              >
                Fixed ({reports.filter(r => r.status === 'fixed').length})
              </button>

              <button 
                type="button" 
                class="btn-icon-refresh" 
                title="Refresh issues list"
                aria-label="Refresh issues list"
                on:click={loadReports}
              >
                <Icon name="refresh" size={14} />
              </button>
            </div>
          </div>

          <!-- Reports List -->
          <div class="reports-scroll-list">
            {#if isLoadingReports}
              <div class="empty-state">
                <div class="spinner"></div>
                <p>Querying Firebase bug tracker...</p>
              </div>
            {:else if filteredReports.length === 0}
              <div class="empty-state">
                <Icon name="shield-check" size={32} color="var(--accent-primary)" />
                <h4>No Issues Found</h4>
                <p>{searchQuery ? 'No reports match your search query.' : 'There are currently no active bug reports in this category!'}</p>
              </div>
            {:else}
              {#each filteredReports as r (r.id)}
                <IssueCard 
                  report={r}
                  isAdminMode={isAdminMode}
                  isUpvoted={upvotedIds.has(r.id)}
                  onUpvote={handleUpvote}
                  onPreviewImage={(url) => previewImageUrl = url}
                  onAdminSave={handleAdminSave}
                  onAdminDelete={handleAdminDelete}
                />
              {/each}
            {/if}
          </div>
        </div>
      {/if}

      <!-- Tab 2: Submit a Report -->
      {#if activeTab === 'submit'}
        <SubmitReportForm 
          bind:this={submitFormRef}
          reports={reports}
          isSubmitting={isSubmittingReport}
          onSubmit={handleSubmitReport}
          onUpvoteExisting={handleUpvoteExisting}
          onShowToast={onShowToast}
          onPreviewImage={(url) => previewImageUrl = url}
        />
      {/if}
    </div>
  </div>
{/if}

<!-- Pre-Submit Duplicate Intercept Modal -->
<DuplicateInterceptModal 
  isOpen={duplicateModalOpen}
  report={interceptedReport}
  onClose={() => duplicateModalOpen = false}
  onViewInTracker={handleDuplicateViewInTracker}
  onSubmitAnyway={handleSubmitAnyway}
/>

<!-- Admin Secret PIN Modal -->
<AdminPinModal 
  isOpen={showPinModal}
  onClose={() => showPinModal = false}
  onSuccess={handleAdminUnlockSuccess}
/>

<!-- Large Screenshot Preview Modal -->
<ImagePreviewModal 
  imageUrl={previewImageUrl}
  onClose={() => previewImageUrl = ''}
/>

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 8500;
    background: rgba(4, 7, 13, 0.82);
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

  .modal-card {
    width: 100%;
    max-width: 860px;
    max-height: 88vh;
    display: flex;
    flex-direction: column;
    border-radius: 20px;
    background: rgba(13, 17, 26, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 32px 64px rgba(0, 0, 0, 0.8), 0 0 32px rgba(0, 240, 160, 0.15);
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .modal-title-row {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .modal-icon-halo {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: rgba(0, 240, 160, 0.1);
    border: 1px solid rgba(0, 240, 160, 0.25);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-title {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.02em;
  }

  .modal-subtitle {
    margin: 2px 0 0 0;
    font-size: 0.78rem;
    color: var(--text-secondary);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .btn-admin-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .btn-admin-badge.locked {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: var(--text-muted);
  }
  .btn-admin-badge.locked:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
  }
  .btn-admin-badge.unlocked {
    background: rgba(0, 240, 160, 0.15);
    border: 1px solid rgba(0, 240, 160, 0.4);
    color: #00f0a0;
  }

  .btn-close {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 6px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }
  .btn-close:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.1);
  }

  /* Tabs Bar */
  .tabs-header-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 24px;
    background: rgba(0, 0, 0, 0.2);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .tab-nav-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 10px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-secondary);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .tab-nav-btn:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.05);
  }
  .tab-nav-btn.active {
    color: #ffffff;
    background: rgba(0, 240, 160, 0.12);
    border-color: rgba(0, 240, 160, 0.3);
  }

  /* Known Issues Viewport */
  .tracker-viewport {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 18px 24px;
    gap: 14px;
  }

  .filter-controls-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }

  .search-box {
    position: relative;
    flex: 1;
    min-width: 240px;
    display: flex;
    align-items: center;
  }
  .search-box :global(.svg-icon) {
    position: absolute;
    left: 12px;
    pointer-events: none;
  }
  .search-input {
    width: 100%;
    padding-left: 36px;
    font-size: 0.85rem;
  }

  .status-pills-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .pill-btn {
    padding: 5px 12px;
    border-radius: 16px;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-secondary);
    transition: all 0.2s ease;
  }
  .pill-btn:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.2);
  }
  .pill-btn.active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: #002e1c;
    font-weight: 700;
  }

  .btn-icon-refresh {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-secondary);
    padding: 6px;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }
  .btn-icon-refresh:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.12);
  }

  .reports-scroll-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding-right: 4px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    gap: 8px;
    color: var(--text-muted);
  }
  .empty-state h4 {
    margin: 0;
    font-size: 0.95rem;
    color: #ffffff;
  }
  .empty-state p {
    margin: 0;
    font-size: 0.82rem;
  }

  .spinner {
    width: 24px;
    height: 24px;
    border: 2px solid rgba(0, 240, 160, 0.2);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
