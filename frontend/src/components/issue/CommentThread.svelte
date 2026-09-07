<script lang="ts">
  import Icon from '../icons/Icon.svelte';
  import { playClickSound, playSuccessChime } from '../../utils/audio';
  import type { IssueComment } from '../../types';

  export let reportId: string;
  export let comments: IssueComment[] = [];
  export let isAdminMode: boolean = false;
  export let isReporter: boolean = false;
  export let sessionAdminPin: string = '';
  export let engineLogs: string[] = [];
  export let onPreviewImage: (url: string) => void = () => {};
  export let onAddComment: (payload: any) => Promise<void> | void = () => {};
  export let onDeleteComment: (reportId: string, commentId: string) => Promise<void> | void = () => {};
  export let onShowToast: (msg: string) => void = () => {};

  let replyText: string = '';
  let replyScreenshot: string = '';
  let isPosting: boolean = false;
  let isDeletingId: string = '';
  let fileInputEl: HTMLInputElement;

  function formatDate(isoStr?: string): string {
    if (!isoStr) return 'Recently';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Recently';
    }
  }

  // Handle attaching recent engine telemetry logs
  function handleAttachLogs() {
    playClickSound();
    if (!engineLogs || engineLogs.length === 0) {
      onShowToast('No active engine logs available in current session.');
      return;
    }
    // Take last 12 log lines for concise diagnostic signal
    const relevantLogs = engineLogs.slice(-12).join('\n');
    const logSnippet = `\n\n--- [Attached Engine Telemetry Logs] ---\n${relevantLogs}\n--------------------------------------`;
    replyText = (replyText ? replyText.trim() + '\n' : '') + logSnippet;
    onShowToast('Attached recent telemetry logs to reply.');
  }

  // Handle image upload and compression via canvas
  function processImageFile(file: File) {
    if (!file.type.startsWith('image/')) {
      onShowToast('Please select a valid image file (PNG, JPG, WebP).');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        let width = img.width;
        let height = img.height;
        // Limit max dimensions for cloud storage efficiency
        if (width > 1280 || height > 720) {
          const ratio = Math.min(1280 / width, 720 / height);
          width = Math.floor(width * ratio);
          height = Math.floor(height * ratio);
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height);
          replyScreenshot = canvas.toDataURL('image/jpeg', 0.82);
          playClickSound();
          onShowToast('Screenshot attached!');
        }
      };
      img.src = e.target?.result as string;
    };
    reader.readAsDataURL(file);
  }

  function handleFileChange(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target && target.files && target.files[0]) {
      processImageFile(target.files[0]);
    }
  }

  function handlePaste(e: ClipboardEvent) {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          e.preventDefault();
          processImageFile(file);
          break;
        }
      }
    }
  }

  async function handlePostComment() {
    const cleanText = replyText.trim();
    if (!cleanText && !replyScreenshot) {
      onShowToast('Please enter a comment or attach an image.');
      return;
    }

    isPosting = true;
    try {
      const authorType = isAdminMode ? 'admin' : (isReporter ? 'reporter' : 'gamer');
      await onAddComment({
        report_id: reportId,
        text: cleanText,
        author_type: authorType,
        author_name: isAdminMode ? 'Official Admin' : (isReporter ? 'Original Reporter' : 'Community Gamer'),
        screenshot_data: replyScreenshot,
        admin_pin: isAdminMode ? sessionAdminPin : undefined
      });
      replyText = '';
      replyScreenshot = '';
      playSuccessChime();
    } finally {
      isPosting = false;
    }
  }

  async function handleDeleteComment(commentId: string) {
    if (!confirm('Are you sure you want to delete this reply?')) return;
    isDeletingId = commentId;
    try {
      await onDeleteComment(reportId, commentId);
    } finally {
      isDeletingId = '';
    }
  }
</script>

<div class="comment-thread-drawer glass-panel">
  <div class="drawer-header">
    <div class="drawer-title">
      <Icon name="message-square" size={13} color="var(--accent-secondary)" />
      <span>COMMUNITY DISCUSSION & UPDATES ({comments.length})</span>
    </div>
    {#if isReporter}
      <span class="reporter-indicator-badge">
        <Icon name="shield-check" size={11} color="#00f0a0" />
        <span>You are the Author</span>
      </span>
    {/if}
  </div>

  <!-- Comments Stream -->
  <div class="comments-list">
    {#if comments.length === 0}
      <div class="empty-comments">
        <Icon name="message-square" size={24} color="var(--text-muted)" />
        <p>No replies yet. Confirm this fix, share workarounds, or attach your diagnostic error logs below.</p>
      </div>
    {:else}
      {#each comments as comment (comment.id)}
        <div class="comment-item" class:is-admin-comment={comment.author_type === 'admin'}>
          <div class="comment-header-row">
            <div class="author-meta-group">
              {#if comment.author_type === 'admin'}
                <span class="badge-author badge-admin">
                  <Icon name="shield-check" size={11} color="#00f0a0" />
                  <span>OFFICIAL ADMIN</span>
                </span>
              {:else if comment.author_type === 'reporter'}
                <span class="badge-author badge-reporter">
                  <Icon name="zap" size={11} color="#00f0a0" />
                  <span>ORIGINAL REPORTER</span>
                </span>
              {:else}
                <span class="badge-author badge-gamer">
                  <span>GAMER</span>
                </span>
              {/if}

              <span class="comment-time">{formatDate(comment.created_at)}</span>

              {#if comment.app_version}
                <span class="comment-ver-tag">{comment.app_version}</span>
              {/if}
            </div>

            {#if isAdminMode}
              <button 
                type="button"
                class="btn-delete-comment"
                title="Delete comment (Admin only)"
                disabled={isDeletingId === comment.id}
                on:click={() => handleDeleteComment(comment.id)}
              >
                <Icon name="trash" size={12} color="#f43f5e" />
              </button>
            {/if}
          </div>

          <!-- Comment Body -->
          <div class="comment-body">
            {#each comment.text.split('\n') as line}
              {#if line.startsWith('---') || line.startsWith('[') && line.includes(']')}
                <div class="log-line font-mono">{line}</div>
              {:else if line.trim()}
                <p class="comment-p">{line}</p>
              {:else}
                <div class="comment-spacing"></div>
              {/if}
            {/each}
          </div>

          <!-- Attached Screenshot in Comment -->
          {#if comment.screenshot_data}
            <div class="comment-screenshot-thumb">
              <button 
                type="button" 
                class="thumb-img-btn"
                on:click={() => onPreviewImage(comment.screenshot_data || '')}
                title="Click to view full screenshot evidence"
              >
                <img src={comment.screenshot_data} alt="Attached reply screenshot" class="comment-img" />
                <span class="thumb-hover-overlay">
                  <Icon name="image" size={12} color="#ffffff" />
                  <span>View Full Screenshot</span>
                </span>
              </button>
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  <!-- Reply Composer Box -->
  <div class="reply-composer glass-panel">
    <div class="composer-toolbar">
      <span class="composer-label">ADD FOLLOW-UP REPLY:</span>

      <div class="toolbar-actions">
        <button 
          type="button" 
          class="btn-toolbar-tool"
          title="Attach recent session error & engine logs"
          on:click={handleAttachLogs}
        >
          <Icon name="terminal" size={12} color="var(--accent-secondary)" />
          <span>Attach Engine Logs</span>
        </button>

        <button 
          type="button" 
          class="btn-toolbar-tool"
          title="Browse and attach image screenshot"
          on:click={() => fileInputEl?.click()}
        >
          <Icon name="image" size={12} color="var(--accent-primary)" />
          <span>Attach Image</span>
        </button>
        <input 
          bind:this={fileInputEl}
          type="file" 
          accept="image/*" 
          style="display: none;" 
          on:change={handleFileChange}
        />
      </div>
    </div>

    <!-- Attached Image Preview in Composer -->
    {#if replyScreenshot}
      <div class="reply-image-preview">
        <img src={replyScreenshot} alt="Attached preview" class="preview-tiny-img" />
        <div class="preview-btns">
          <button type="button" class="btn-sm-tool" on:click={() => onPreviewImage(replyScreenshot)}>
            <Icon name="image" size={11} />
            <span>Expand</span>
          </button>
          <button type="button" class="btn-sm-tool btn-remove" on:click={() => replyScreenshot = ''}>
            <Icon name="close" size={11} color="#f43f5e" />
            <span>Remove</span>
          </button>
        </div>
      </div>
    {/if}

    <textarea 
      class="reply-textarea glass-input" 
      rows="3"
      placeholder="Write a reply, test result, or follow-up note... (Paste Ctrl+V for screenshot)"
      bind:value={replyText}
      on:paste={handlePaste}
    ></textarea>

    <div class="composer-footer">
      <div class="composer-identity">
        {#if isAdminMode}
          <span class="identity-badge admin">
            <Icon name="shield-check" size={11} color="#00f0a0" />
            <span>Posting as Admin</span>
          </span>
        {:else if isReporter}
          <span class="identity-badge reporter">
            <Icon name="zap" size={11} color="#00f0a0" />
            <span>Posting as Original Reporter</span>
          </span>
        {:else}
          <span class="identity-badge gamer">
            <span>Posting as Community Gamer</span>
          </span>
        {/if}
      </div>

      <button 
        type="button" 
        class="btn-primary btn-post-reply"
        disabled={isPosting || (!replyText.trim() && !replyScreenshot)}
        on:click={handlePostComment}
      >
        <Icon name="send" size={13} color="#ffffff" />
        <span>{isPosting ? 'Posting...' : 'Post Reply'}</span>
      </button>
    </div>
  </div>
</div>

<style>
  .comment-thread-drawer {
    margin-top: 14px;
    padding: 14px;
    background: rgba(6, 8, 14, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .drawer-title {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 11px;
    font-weight: 700;
    color: var(--accent-secondary);
    letter-spacing: 0.8px;
  }

  .reporter-indicator-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    font-weight: 600;
    color: #00f0a0;
    background: rgba(0, 240, 160, 0.08);
    border: 1px solid rgba(0, 240, 160, 0.2);
    padding: 2px 7px;
    border-radius: var(--radius-xs);
  }

  /* Comments List */
  .comments-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 380px;
    overflow-y: auto;
    padding-right: 4px;
  }

  .empty-comments {
    padding: 24px 12px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    color: var(--text-muted);
    font-size: 11.5px;
  }

  .empty-comments p {
    max-width: 360px;
    line-height: 1.4;
  }

  .comment-item {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    transition: background var(--transition-fast);
  }

  .comment-item.is-admin-comment {
    background: rgba(0, 240, 160, 0.03);
    border-color: rgba(0, 240, 160, 0.15);
  }

  .comment-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .author-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .badge-author {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .badge-admin {
    color: #00f0a0;
    background: rgba(0, 240, 160, 0.15);
    border: 1px solid rgba(0, 240, 160, 0.3);
  }

  .badge-reporter {
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.3);
  }

  .badge-gamer {
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .comment-time {
    font-size: 10.5px;
    color: var(--text-muted);
  }

  .comment-ver-tag {
    font-size: 9.5px;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.03);
    padding: 1px 5px;
    border-radius: 3px;
    font-family: var(--font-mono);
  }

  .btn-delete-comment {
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 3px;
    opacity: 0.6;
    transition: opacity var(--transition-fast);
  }

  .btn-delete-comment:hover {
    opacity: 1;
    background: rgba(244, 63, 94, 0.15);
  }

  .comment-body {
    font-size: 11.5px;
    color: var(--text-primary);
    line-height: 1.45;
  }

  .comment-p {
    margin: 0;
    word-break: break-word;
  }

  .comment-spacing {
    height: 4px;
  }

  .log-line {
    font-size: 10.5px;
    color: #38bdf8;
    background: rgba(0, 0, 0, 0.3);
    padding: 2px 6px;
    border-radius: 3px;
    margin: 2px 0;
    word-break: break-all;
  }

  .comment-screenshot-thumb {
    margin-top: 4px;
  }

  .thumb-img-btn {
    position: relative;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: var(--radius-xs);
    overflow: hidden;
    max-width: 140px;
    max-height: 85px;
    cursor: pointer;
    background: transparent;
    padding: 0;
    display: block;
  }

  .comment-img {
    width: 100%;
    height: auto;
    display: block;
    object-fit: cover;
  }

  .thumb-hover-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    font-size: 9px;
    color: #ffffff;
    opacity: 0;
    transition: opacity var(--transition-fast);
  }

  .thumb-img-btn:hover .thumb-hover-overlay {
    opacity: 1;
  }

  /* Reply Composer */
  .reply-composer {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .composer-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 6px;
  }

  .composer-label {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-muted);
    letter-spacing: 0.6px;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .btn-toolbar-tool {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: var(--text-secondary);
    border-radius: var(--radius-xs);
    padding: 3px 8px;
    font-size: 10.5px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .btn-toolbar-tool:hover {
    background: rgba(255, 255, 255, 0.09);
    color: var(--text-primary);
  }

  .reply-image-preview {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: rgba(0, 0, 0, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: var(--radius-xs);
    padding: 4px 8px;
    width: fit-content;
  }

  .preview-tiny-img {
    width: 38px;
    height: 26px;
    object-fit: cover;
    border-radius: 2px;
  }

  .preview-btns {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .btn-sm-tool {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-secondary);
    border-radius: 3px;
    padding: 2px 6px;
    font-size: 9.5px;
    cursor: pointer;
  }

  .btn-sm-tool.btn-remove:hover {
    color: #f43f5e;
    border-color: rgba(244, 63, 94, 0.3);
  }

  .reply-textarea {
    width: 100%;
    resize: vertical;
    min-height: 54px;
    font-size: 11.5px;
    font-family: inherit;
    line-height: 1.4;
    padding: 8px 10px;
    box-sizing: border-box;
  }

  .composer-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .identity-badge {
    font-size: 10px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .identity-badge.admin {
    color: #00f0a0;
  }

  .identity-badge.reporter {
    color: #38bdf8;
  }

  .identity-badge.gamer {
    color: var(--text-muted);
  }

  .btn-post-reply {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 600;
    border-radius: var(--radius-xs);
  }
</style>
