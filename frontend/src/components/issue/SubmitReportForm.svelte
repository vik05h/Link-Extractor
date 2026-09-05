<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from '../icons/Icon.svelte';
  import { playClickSound, playSuccessChime } from '../../utils/audio';
  import type { IssueReport } from '../../types';

  export let reports: IssueReport[] = [];
  export let isSubmitting: boolean = false;
  export let onSubmit: (payload: { category: string; subject: string; description: string; screenshotData: string }) => void = () => {};
  export let onUpvoteExisting: (id: string, subject: string) => void = () => {};
  export let onShowToast: (msg: string) => void = () => {};
  export let onPreviewImage: (url: string) => void = () => {};

  interface CategoryOption {
    value: string;
    label: string;
    icon: string;
    color: string;
    description: string;
  }

  const CATEGORIES: CategoryOption[] = [
    { value: 'Bug Report', label: 'Bug Report', icon: 'bug', color: '#f43f5e', description: 'Application errors, UI glitches or crashes' },
    { value: 'Turnstile Bypass Failure', label: 'Turnstile Bypass Failure', icon: 'shield-check', color: '#f59e0b', description: 'Cloudflare captcha solve timeouts' },
    { value: 'Broken Direct Link', label: 'Broken Direct Link', icon: 'link', color: '#ef4444', description: 'Expired mirrors or 404 hoster errors' },
    { value: 'JDownloader 2 Push Error', label: 'JDownloader 2 Push Error', icon: 'bolt', color: '#38bdf8', description: 'Port 9666 LinkGrabber integration' },
    { value: 'Feature Suggestion', label: 'Feature Suggestion', icon: 'sparkles', color: '#00f0a0', description: 'New features, exporters or UI ideas' },
    { value: 'Other', label: 'Other', icon: 'help-circle', color: '#94a3b8', description: 'General questions or feedback' }
  ];

  let category: string = 'Bug Report';
  let isCategoryOpen: boolean = false;
  let subject: string = '';
  let description: string = '';
  let screenshotData: string = '';
  let liveMatches: IssueReport[] = [];
  let fileInputEl: HTMLInputElement;

  $: currentCategoryMeta = CATEGORIES.find(c => c.value === category) || CATEGORIES[0];

  function toggleCategoryDropdown(e: MouseEvent) {
    e.stopPropagation();
    playClickSound();
    isCategoryOpen = !isCategoryOpen;
  }

  function selectCategory(val: string) {
    category = val;
    playClickSound();
    isCategoryOpen = false;
  }

  onMount(() => {
    const handleGlobalClick = () => {
      if (isCategoryOpen) isCategoryOpen = false;
    };
    const handleKeydownWindow = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isCategoryOpen) {
        isCategoryOpen = false;
      }
    };
    window.addEventListener('click', handleGlobalClick);
    window.addEventListener('keydown', handleKeydownWindow);
    return () => {
      window.removeEventListener('click', handleGlobalClick);
      window.removeEventListener('keydown', handleKeydownWindow);
    };
  });

  // Live duplicate subject matching
  $: {
    const q = subject.trim().toLowerCase();
    if (q.length >= 4 && reports.length > 0) {
      const words = q.split(/\s+/).filter(w => w.length > 2);
      liveMatches = reports.filter(r => {
        const subj = (r.subject || '').toLowerCase();
        if (subj.includes(q) || q.includes(subj)) return true;
        const matches = words.filter(w => subj.includes(w));
        return matches.length >= 2 || (words.length === 1 && matches.length === 1);
      }).slice(0, 3);
    } else {
      liveMatches = [];
    }
  }

  // Handle Screenshot File Upload & Canvas Compression
  function handleFileSelected(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target && target.files && target.files[0]) {
      processImageFile(target.files[0]);
    }
  }

  function processImageFile(file: File) {
    if (!file.type.startsWith('image/')) {
      onShowToast('Please select a valid image file (PNG or JPG).');
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        // Compress image using canvas: max dimensions 1280x720, jpeg quality 0.82
        const maxW = 1280;
        const maxH = 720;
        let w = img.width;
        let h = img.height;

        if (w > maxW || h > maxH) {
          const ratio = Math.min(maxW / w, maxH / h);
          w = Math.floor(w * ratio);
          h = Math.floor(h * ratio);
        }

        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0, w, h);
          screenshotData = canvas.toDataURL('image/jpeg', 0.82);
          playSuccessChime();
          onShowToast('Screenshot attached and compressed!');
        }
      };
      img.src = event.target?.result as string;
    };
    reader.readAsDataURL(file);
  }

  // Window paste listener
  export function handlePaste(e: ClipboardEvent) {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const blob = items[i].getAsFile();
        if (blob) {
          e.preventDefault();
          processImageFile(blob);
          break;
        }
      }
    }
  }

  function handleFormSubmit() {
    if (!subject.trim()) {
      onShowToast('Please enter an issue subject.');
      return;
    }
    if (!description.trim()) {
      onShowToast('Please provide a description of the issue.');
      return;
    }

    playClickSound();
    onSubmit({
      category,
      subject: subject.trim(),
      description: description.trim(),
      screenshotData
    });
  }

  export function resetForm() {
    subject = '';
    description = '';
    screenshotData = '';
  }
</script>

<div class="submit-viewport">
  <div class="submit-form-container">
    <!-- Category & Subject -->
    <div class="form-row-grid">
      <div class="form-group" style="flex: 0 0 220px; position: relative;">
        <label for="report-category" class="form-label">CATEGORY</label>
        <div class="custom-dropdown-wrap">
          <button 
            type="button" 
            id="report-category"
            class="custom-dropdown-btn glass-input"
            class:is-active={isCategoryOpen}
            on:click={toggleCategoryDropdown}
            aria-haspopup="listbox"
            aria-expanded={isCategoryOpen}
          >
            <div class="dropdown-selected-wrap">
              <span class="category-icon-tag" style="color: {currentCategoryMeta.color};">
                <Icon name={currentCategoryMeta.icon} size={14} color={currentCategoryMeta.color} />
              </span>
              <span class="selected-label">{currentCategoryMeta.label}</span>
            </div>
            <span class="dropdown-chevron" class:rotate={isCategoryOpen}>
              <Icon name="chevron-down" size={13} color="var(--text-muted)" />
            </span>
          </button>

          {#if isCategoryOpen}
            <div 
              class="custom-dropdown-menu glass-panel" 
              role="listbox"
              on:click|stopPropagation={() => {}}
            >
              {#each CATEGORIES as opt}
                <button 
                  type="button" 
                  class="custom-dropdown-item"
                  class:selected={category === opt.value}
                  role="option"
                  aria-selected={category === opt.value}
                  on:click|stopPropagation={() => selectCategory(opt.value)}
                >
                  <div class="item-icon-col" style="color: {opt.color};">
                    <Icon name={opt.icon} size={14} color={opt.color} />
                  </div>
                  <div class="item-text-col">
                    <div class="item-title">{opt.label}</div>
                    <div class="item-desc">{opt.description}</div>
                  </div>
                  {#if category === opt.value}
                    <div class="item-check">
                      <Icon name="check" size={13} color="var(--accent-primary)" strokeWidth={2.5} />
                    </div>
                  {/if}
                </button>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="form-group" style="flex: 1; position: relative;">
        <label for="report-subject" class="form-label">ISSUE SUBJECT / GAME NAME</label>
        <input 
          id="report-subject"
          type="text" 
          class="glass-input" 
          placeholder="e.g. Part 4 failing Cloudflare Turnstile on Black Myth: Wukong..."
          bind:value={subject}
          maxlength="150"
        />

        <!-- Live Duplicate Suggestions Dropdown -->
        {#if liveMatches.length > 0}
          <div class="live-matches-dropdown glass-panel">
            <div class="matches-header">
              <Icon name="sparkles" size={12} color="#f59e0b" />
              <span>SIMILAR ISSUES ALREADY IN REPORT LOGS:</span>
            </div>
            {#each liveMatches as m}
              <div class="match-item">
                <div class="match-title-row">
                  <span class="match-title">{m.subject}</span>
                  <span class="status-pill status-{m.status || 'open'}">{m.status?.toUpperCase() || 'OPEN'}</span>
                </div>
                {#if m.admin_remark}
                  <div class="match-remark">Fix: {m.admin_remark}</div>
                {/if}
                <div class="match-footer">
                  <span>{m.affected_users_count || 1} gamers affected</span>
                  <button 
                    type="button" 
                    class="btn-vote-sm"
                    on:click={() => onUpvoteExisting(m.id, m.subject)}
                  >
                    +1 I have this too
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Description Body -->
    <div class="form-group">
      <label for="report-desc" class="form-label">DETAILED DESCRIPTION / STEPS TO REPRODUCE</label>
      <textarea 
        id="report-desc"
        class="glass-input desc-textarea" 
        placeholder="Describe what happened, what game/pastebin URL you were extracting, and any error message displayed in the terminal..."
        bind:value={description}
        rows="4"
      ></textarea>
    </div>

    <!-- Screenshot Attachment & Clipboard Paste Zone -->
    <div class="form-group">
      <div class="screenshot-header-row">
        <span class="form-label">SCREENSHOT ATTACHMENT</span>
        <span class="paste-hint">💡 Tip: Press Ctrl+V anywhere in this window to paste a copied screenshot</span>
      </div>

      {#if screenshotData}
        <div class="screenshot-preview-card glass-panel">
          <img src={screenshotData} alt="Attached preview" class="preview-img" />
          <div class="preview-actions">
            <button type="button" class="btn-secondary btn-sm" on:click={() => onPreviewImage(screenshotData)}>
              <Icon name="image" size={13} />
              <span>Expand</span>
            </button>
            <button type="button" class="btn-secondary btn-sm btn-remove-img" on:click={() => screenshotData = ''}>
              <Icon name="trash" size={13} color="var(--status-expired)" />
              <span>Remove</span>
            </button>
          </div>
        </div>
      {:else}
        <div 
          class="dropzone-box"
          on:click={() => fileInputEl?.click()}
          on:keydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputEl?.click(); } }}
          role="button"
          tabindex="0"
          aria-label="Click or drop file to upload screenshot"
        >
          <Icon name="image" size={32} color="var(--accent-primary)" />
          <div class="dropzone-text">
            <strong>Click to browse image or drag & drop file here</strong>
            <span>Supports PNG, JPG, WebP • Auto-compressed for lightweight cloud storage</span>
          </div>
        </div>
      {/if}

      <input 
        bind:this={fileInputEl}
        type="file" 
        accept="image/*" 
        style="display: none;" 
        on:change={handleFileSelected}
      />
    </div>

    <!-- Telemetry Notice & Submit Row -->
    <div class="submit-footer-row">
      <div class="telemetry-pill">
        <Icon name="shield-check" size={13} color="#00f0a0" />
        <span>Non-sensitive diagnostic telemetry (v3.8.0, Windows) will be included.</span>
      </div>

      <button 
        type="button" 
        class="btn-primary btn-submit-report"
        disabled={isSubmitting || !subject.trim() || !description.trim()}
        on:click={handleFormSubmit}
      >
        <Icon name="bolt" size={15} color="#ffffff" strokeWidth={2.5} />
        <span>{isSubmitting ? 'Verifying & Submitting...' : 'Submit Report'}</span>
      </button>
    </div>
  </div>
</div>

<style>
  .submit-viewport {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }
  .submit-form-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .form-row-grid {
    display: flex;
    gap: 14px;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .form-label {
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
  }

  .desc-textarea {
    resize: vertical;
    font-size: 0.88rem;
    line-height: 1.5;
  }

  /* Custom Dropdown Styling */
  .custom-dropdown-wrap {
    position: relative;
    width: 100%;
  }

  .custom-dropdown-btn {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 9px 12px;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .custom-dropdown-btn.is-active {
    border-color: var(--accent-primary);
    box-shadow: 0 0 12px rgba(0, 240, 160, 0.25);
  }

  .dropdown-selected-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .category-icon-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .selected-label {
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .dropdown-chevron {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .dropdown-chevron.rotate {
    transform: rotate(180deg);
  }

  .custom-dropdown-menu {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    width: 290px;
    z-index: 100;
    padding: 6px;
    border-radius: 12px;
    background: rgba(13, 17, 26, 0.98);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.16);
    box-shadow: 
      0 20px 48px rgba(0, 0, 0, 0.85),
      0 0 24px rgba(0, 240, 160, 0.15);
    display: flex;
    flex-direction: column;
    gap: 2px;
    transform-origin: top left;
    animation: dropdownSlideDown 0.22s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  .custom-dropdown-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 10px;
    border-radius: 8px;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s ease, transform 0.1s ease;
    width: 100%;
  }

  .custom-dropdown-item:hover {
    background: rgba(255, 255, 255, 0.06);
    transform: translateX(2px);
  }

  .custom-dropdown-item.selected {
    background: rgba(0, 240, 160, 0.12);
  }

  .item-icon-col {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding-top: 2px;
    flex-shrink: 0;
  }

  .item-text-col {
    display: flex;
    flex-direction: column;
    gap: 1px;
    flex: 1;
    min-width: 0;
  }

  .item-title {
    font-size: 0.82rem;
    font-weight: 600;
    color: #ffffff;
    line-height: 1.25;
  }

  .item-desc {
    font-size: 0.7rem;
    color: var(--text-muted);
    line-height: 1.3;
  }

  .item-check {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-left: auto;
    padding-top: 2px;
    flex-shrink: 0;
  }

  @keyframes dropdownSlideDown {
    from {
      opacity: 0;
      transform: translateY(-8px) scale(0.97);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  /* Live duplicate suggestions dropdown */
  .live-matches-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 10;
    margin-top: 6px;
    padding: 12px;
    border-radius: 12px;
    background: rgba(18, 24, 38, 0.98);
    border: 1px solid rgba(245, 158, 11, 0.4);
    box-shadow: 0 16px 32px rgba(0, 0, 0, 0.7);
    display: flex;
    flex-direction: column;
    gap: 10px;
    transform-origin: top center;
    animation: dropdownSlideDown 0.22s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  .matches-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #f59e0b;
    letter-spacing: 0.05em;
  }
  .match-item {
    padding: 8px 10px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .match-title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .match-title {
    font-size: 0.84rem;
    font-weight: 600;
    color: #ffffff;
  }
  .status-pill {
    padding: 2px 7px;
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
  .match-remark {
    font-size: 0.76rem;
    color: #00f0a0;
  }
  .match-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.72rem;
    color: var(--text-muted);
    padding-top: 4px;
  }
  .btn-vote-sm {
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    background: rgba(0, 240, 160, 0.15);
    border: 1px solid rgba(0, 240, 160, 0.3);
    color: #00f0a0;
    cursor: pointer;
  }

  /* Screenshot drag & drop */
  .screenshot-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .paste-hint {
    font-size: 0.72rem;
    color: var(--accent-primary);
  }
  .dropzone-box {
    padding: 20px;
    border-radius: 12px;
    border: 2px dashed rgba(255, 255, 255, 0.15);
    background: rgba(255, 255, 255, 0.02);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .dropzone-box:hover {
    border-color: var(--accent-primary);
    background: rgba(0, 240, 160, 0.04);
  }
  .dropzone-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .dropzone-text strong {
    font-size: 0.85rem;
    color: #ffffff;
  }
  .dropzone-text span {
    font-size: 0.74rem;
    color: var(--text-muted);
  }

  .screenshot-preview-card {
    position: relative;
    padding: 10px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .preview-img {
    max-width: 220px;
    max-height: 120px;
    border-radius: 8px;
    object-fit: cover;
  }
  .preview-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .submit-footer-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }
  .telemetry-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.76rem;
    color: var(--text-muted);
  }
  .btn-submit-report {
    padding: 10px 22px;
    font-size: 0.9rem;
    font-weight: 700;
  }
</style>
