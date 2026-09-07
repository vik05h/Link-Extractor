<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Icon from './icons/Icon.svelte';
  import { playClickSound, playSuccessChime } from '../utils/audio';

  export let isOpen: boolean = false;
  export let releaseInfo: any = null;
  export let isFrozen: boolean = false;
  export let currentVersion: string = 'v3.8.1';
  export let isFirstRun: boolean = false;
  export let onClose: () => void = () => {};
  export let onStartTour: (() => void) | undefined = undefined;
  export let onShowToast: (msg: string) => void = () => {};

  let step: 'overview' | 'downloading' | 'ready' | 'error' = 'overview';
  let percent: number = 0;
  let downloadedStr: string = '0 MB';
  let totalStr: string = '68 MB';
  let speedStr: string = 'Connecting...';
  let errorMessage: string = '';
  let autoRestartCountdown: number = 3;
  let countdownTimer: any = null;

  // Version Timeline & Changelogs
  let changelogs: any[] = [];
  let selectedVersionIndex: number = 0;
  let isChecking: boolean = false;

  const FALLBACK_CHANGELOGS = [
    {
      version: 'v3.8.1',
      title: 'Community Discussion Threads, Release Update Auto-Popup & Cyber Concurrency Slider',
      is_current: true,
      previous_version: 'v3.8.0',
      highlights: [
        'Interactive Community Discussion Thread drawer on Issue Center tickets with badge attribution (Official Admin, Original Reporter, Community Gamer).',
        'One-click Engine Telemetry Log dumping directly into discussion replies for rapid collaborative bug diagnosis.',
        'Full screenshot attachment pipeline supporting file dropzone, file picker, and clipboard Ctrl+V pasting with client-side canvas compression.',
        'Administrative comment moderation and ticket status management protected by secure passkey authorization.',
        'Automatic release update popup notification on startup with session-based dismissal suppression to prevent repetitive popups.',
        'Cyberpunk animated concurrency slider in Settings with glowing thumb halo and tactile stepped performance tiers (Eco, Balanced, Turbo).'
      ],
      bug_fixes: [
        'Fixed terminal hanging and application freeze when clicking Telemetry & Terminal tab by virtualizing log stream updates.',
        'Resolved content.d.ts type generation issue by configuring glob paths in tsconfig.json.',
        'Fixed comment normalization and timestamp sorting across Firebase Realtime Database and local JSON cache.',
        'Enforced constant-time cryptographic verification for Admin passkey authentication in AppData.'
      ]
    },
    {
      version: 'v3.8.0',
      title: 'Next-Gen Gaming Hub UI/UX Overhaul, Live Guided Tour & Community Issue Center',
      is_current: false,
      previous_version: 'v3.5.0',
      highlights: [
        'Complete architectural migration from legacy Flet UI to hardware-accelerated desktop web architecture powered by Astro, Svelte, and Windows native WebView2.',
        'Interactive Live In-App Guided Tour actively spotlighting the URL bar, Community Vault, Defrag Stage, and Quick Actions with step-by-step onboarding.',
        'Community Issue Center featuring public issue tracking, smart duplicate prevention with affected-user count incrementing, and passkey-protected Admin remarks.',
        'Automated Firebase Crash Log capture intercepting unhandled Python and JavaScript errors with in-memory deduplication.',
        'Living Canvas dynamic ambient backlighting with mathematical vibrancy boosting extracting dominant colors from game cover art.',
        'Interactive Defrag Mosaic visualizer for real-time multi-part status tracking replacing static data tables.',
        'In-app automatic updater with live download speed HUD, percentage tracking, and detached Windows restart script.',
        'Multi-tier authoritative game artwork cascade extracting high-resolution FitGirl covers with procedural neon SVG fallback.',
        'Automated Pastebin metadata resolution extracting game names from archive filenames with FitGirl site search.',
        'Live concurrent gamer presence pulse indicator powered by zero-cost lightweight Firebase REST heartbeats.',
        'Selective Repack Filter saving tens of gigabytes by filtering optional language and bonus packs.',
        'Background Clipboard Sentinel auto-detecting copied FitGirl links and Web Audio API synthesized gaming sound haptics.'
      ],
      bug_fixes: [
        'Completely eliminated legacy Flet runtime thread blocking, socket buffering, and window focus stealing.',
        'Fixed ambient mode text darkness with mathematical vibrancy boosting in HLS color space.',
        'Fixed 0 B repack size aggregation by aligning validator progress callback signature.',
        'Fixed Steam store 404 artwork failure on recent releases with authoritative FitGirl page parser.',
        'Fixed duplicate cache freshness logic ensuring cached mirrors older than 24 hours trigger fresh extractions.'
      ]
    },
    {
      version: 'v3.5.0',
      title: 'Interactive Live In-App Guided Tour, Spotlight Highlighting & Rebranding (Legacy Flet UI)',
      is_current: false,
      previous_version: 'v3.2.0',
      highlights: [
        'Interactive Live In-App Guided Tour actively navigating across Extractor, Community Hub, History Archive, and Settings in real-time.',
        'Dynamic Spotlight Box Highlighting with glowing theme borders and soft shadows illuminating the exact target cards on each step.',
        'Complete Rebranding to Link Extractor across window titles, PE resource headers, and in-app components.',
        'Display Framerate Selector toggling between 60 FPS (Balanced) and 120 FPS (Ultra Fluid) in real-time.',
        'Community Hub View Switcher with responsive Poster Grid View and Compact Feed List.',
        'Interactive Game Details Modal popup displaying all split repack archive parts with individual copy links.',
        'Enhanced Card Hover animations with theme-colored glowing borders, elevation pop, and smooth poster zoom.',
        'Expanded 8 dynamic Material 3 theme presets (Deep Violet, Emerald, Cyber Sapphire, Amber Gold, Neon Rose, Synthwave, Matrix, Crimson).',
        'Enhanced 1-Click Health Check with clear Part 1 verification badge and detailed tooltip.'
      ],
      bug_fixes: [
        'Fixed Icon missing positional argument in tour controller.',
        'Fixed typing import for Callable in state controller.',
        'Fixed shadow smudge glitch on lighter themes using native Material 3 elevation.',
        'Added automatic SQLite History archive deduplication and smart upsert updates.',
        'Enforced pure-white high-contrast text and icons on floating status notifications.'
      ]
    },
    {
      version: 'v3.2.0',
      title: 'Community Cloud Cache, Pixel Dino Loader & 3D Repack Hub',
      is_current: false,
      previous_version: 'v3.1.1',
      highlights: [
        'Decentralized Community Cloud Cache powered by Firebase Realtime Database lightweight REST API.',
        'Retro 8-bit Arcade Pixel Dino running loading animation with live cloud status updates.',
        'Interactive 3D-styled Game Cards with cover thumbnails, depth glow, and local timezone intelligence.',
        'Automatic instant pre-fetched link detection on Extractor screen with 1-click skip browser option.',
        '1-Click Health Check executing rapid 1-byte verification on Part 1 of any community repack.',
        'Automated background cloud publishing with privacy opt-out toggle in Settings & Tweaks.',
        'Freshness color badges (Fresh <12h, Aging 12-36h, Expired >36h) with local time display.'
      ],
      bug_fixes: [
        'Enforced strict overwrite logic to ensure newest extraction timestamps update cloud records.',
        'Added graceful offline fallback with built-in community cache when Firebase is unreachable.',
        'Added full entity unescaping and cover image extraction for FitGirl game pages.'
      ]
    },
    {
      version: 'v3.1.1',
      title: 'Startup Auto-Updater, Real-Time Async UI & In-App Installer',
      is_current: false,
      previous_version: 'v3.1.0',
      highlights: [
        'Automatic silent update check on application startup with user confirmation prompt.',
        'In-app background download progress dialog displaying live speed and percentage.',
        'Automated Windows binary replacement and seamless application restart launcher.',
        'Interactive What\'s New & Bug Fixes release notes popup dialog on updated version launch.',
        'Off-screen headed Playwright browser engine preventing OS window focus theft.'
      ],
      bug_fixes: [
        'Fixed real-time UI freezing by transitioning to native async event loop.',
        'Fixed DataTable child mutation rendering using state model rebuild pattern.',
        'Fixed SegmentedButton JSON serialization error with set-to-list conversion.',
        'Improved detached updater batch script cleanup and process PID tracking on Windows.'
      ]
    },
    {
      version: 'v3.1.0',
      title: 'Material 3 Engine, 1-Byte Size Validation & SQLite History Archive',
      is_current: false,
      previous_version: 'v3.0.0',
      highlights: [
        'Full Material 3 UI migration with Flutter hardware acceleration (60-120 FPS).',
        'Rapid concurrent 1-byte HTTP Range size validation and live total repack calculation.',
        'Integrated local SQLite download archive with instant search and 1-click re-export.',
        'JDownloader 2 FlashGot HTTP API push with #filename.rar zero-prompt anchors.',
        'Dynamic Material 3 theme seeds, branding logo switcher, and transition presets.',
        'Automatic startup update checker and automated in-app update installer.'
      ],
      bug_fixes: [
        'Fixed PyInstaller icons.json missing resource crash on standalone Windows binary.',
        'Fixed window and taskbar icon binding to eliminate Flutter runner default icon.',
        'Fixed cross-platform export directory path resolution on non-standard Windows drives.',
        'Fixed race conditions during mid-extraction cancellations.'
      ]
    },
    {
      version: 'v3.0.0',
      title: 'High-Speed Playwright Multi-Tab Engine & Turnstile Solver',
      is_current: false,
      previous_version: null,
      highlights: [
        'Parallel multi-tab browser pool resolving parts concurrently (3x-6x speedup).',
        'Automatic Cloudflare Turnstile captcha solver and response header interceptor.',
        'Automated retry engine with jitter delays for dropped links.',
        'Direct FitGirl game page and pastebin auto-detection.'
      ],
      bug_fixes: [
        'Resolved browser memory leak by sharing a single context across worker tabs.',
        'Fixed link parser edge cases on multi-mirror pastebins.'
      ]
    }
  ];

  $: hasUpdate = Boolean(
    releaseInfo && (
      releaseInfo.has_update || 
      releaseInfo.available || 
      (releaseInfo.latest_version && releaseInfo.latest_version !== currentVersion)
    )
  );

  $: activeEntry = changelogs[selectedVersionIndex] || changelogs[0] || null;

  function resetState() {
    step = 'overview';
    percent = 0;
    downloadedStr = '0 MB';
    totalStr = '68 MB';
    speedStr = 'Connecting...';
    errorMessage = '';
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }

  $: if (!isOpen) {
    resetState();
  }

  function handleStartTourClick() {
    playClickSound();
    if (onStartTour) {
      onStartTour();
    } else {
      onClose();
    }
  }

  function loadChangelogs() {
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.get_changelogs) {
      (window as any).pywebview.api.get_changelogs()
        .then((data: any[]) => {
          if (data && Array.isArray(data) && data.length > 0) {
            changelogs = data;
          } else {
            changelogs = FALLBACK_CHANGELOGS;
          }
          syncReleaseToChangelogs();
        })
        .catch(() => {
          changelogs = FALLBACK_CHANGELOGS;
          syncReleaseToChangelogs();
        });
    } else {
      changelogs = FALLBACK_CHANGELOGS;
      syncReleaseToChangelogs();
    }
  }

  function syncReleaseToChangelogs() {
    if (hasUpdate && releaseInfo?.latest_version) {
      const exists = changelogs.some(c => c.version === releaseInfo.latest_version);
      if (!exists) {
        const newReleaseEntry = {
          version: releaseInfo.latest_version,
          title: releaseInfo.name || `Link Extractor ${releaseInfo.latest_version}`,
          is_current: false,
          is_new: true,
          previous_version: currentVersion,
          highlights: parseBodyToHighlights(releaseInfo.body),
          bug_fixes: []
        };
        changelogs = [newReleaseEntry, ...changelogs];
      }
    }
  }

  function parseBodyToHighlights(bodyText: string): string[] {
    if (!bodyText) return ['New updates and improvements released on GitHub.'];
    const lines = bodyText.split('\n')
      .map(l => l.trim())
      .filter(l => l.startsWith('* ') || l.startsWith('- ') || l.startsWith('• '))
      .map(l => l.replace(/^[\*\-•]\s*/, '').replace(/\*\*(.*?)\*\*/g, '$1'));
    return lines.length > 0 ? lines : [bodyText.slice(0, 200)];
  }

  function handleTimelineWheel(e: WheelEvent) {
    if (e.deltaY !== 0) {
      e.preventDefault();
      const el = e.currentTarget as HTMLElement;
      el.scrollLeft += e.deltaY;
    }
  }

  onMount(() => {
    loadChangelogs();

    function onProgress(e: CustomEvent) {
      const d = e.detail;
      if (d) {
        step = 'downloading';
        percent = d.percent || 0;
        downloadedStr = d.downloaded_str || '0 MB';
        totalStr = d.total_str || 'Unknown';
        speedStr = d.speed_str || 'Downloading...';
      }
    }

    function onComplete(e: CustomEvent) {
      step = 'ready';
      playSuccessChime();
      onShowToast('Update downloaded successfully!');
      
      if (isFrozen) {
        autoRestartCountdown = 3;
        countdownTimer = setInterval(() => {
          autoRestartCountdown -= 1;
          if (autoRestartCountdown <= 0) {
            clearInterval(countdownTimer);
            countdownTimer = null;
            applyRestart();
          }
        }, 1000);
      }
    }

    function onCancelled() {
      resetState();
      onShowToast('Update download cancelled.');
    }

    function onError(e: CustomEvent) {
      step = 'error';
      errorMessage = e.detail?.error || 'Download failed. Please check your internet connection.';
    }

    window.addEventListener('updater:progress' as any, onProgress);
    window.addEventListener('updater:download_complete' as any, onComplete);
    window.addEventListener('updater:download_cancelled' as any, onCancelled);
    window.addEventListener('updater:error' as any, onError);

    return () => {
      window.removeEventListener('updater:progress' as any, onProgress);
      window.removeEventListener('updater:download_complete' as any, onComplete);
      window.removeEventListener('updater:download_cancelled' as any, onCancelled);
      window.removeEventListener('updater:error' as any, onError);
      if (countdownTimer) clearInterval(countdownTimer);
    };
  });

  $: if (isOpen) {
    loadChangelogs();
  }

  function handleCheckUpdatesManual() {
    playClickSound();
    isChecking = true;
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.check_for_updates) {
      (window as any).pywebview.api.check_for_updates()
        .then((res: any) => {
          isChecking = false;
          if (res && res.has_update && res.release_info) {
            releaseInfo = res.release_info;
            syncReleaseToChangelogs();
            onShowToast(`New update available: ${res.release_info.latest_version || res.release_info.tag_name}`);
          } else {
            onShowToast(res?.message || 'You are running the latest version.');
          }
        })
        .catch((err: any) => {
          isChecking = false;
          onShowToast(`Update check error: ${err?.message || err}`);
        });
    } else {
      setTimeout(() => {
        isChecking = false;
        onShowToast('Updater bridge ready.');
      }, 800);
    }
  }

  function startDownload() {
    playClickSound();
    step = 'downloading';
    percent = 1;
    speedStr = 'Connecting to GitHub CDN...';
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.start_update_download) {
      const url = releaseInfo?.download_url || '';
      (window as any).pywebview.api.start_update_download(url);
    }
  }

  function cancelDownload() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.cancel_update_download) {
      (window as any).pywebview.api.cancel_update_download();
    }
    resetState();
  }

  function applyRestart() {
    playClickSound();
    if (countdownTimer) clearInterval(countdownTimer);
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.apply_update_and_restart) {
      (window as any).pywebview.api.apply_update_and_restart();
    }
  }

  function launchDownloaded() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.launch_downloaded_binary) {
      (window as any).pywebview.api.launch_downloaded_binary();
    }
    onClose();
  }

  function openUpdatesFolder() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.open_updates_folder) {
      (window as any).pywebview.api.open_updates_folder();
    }
  }

  function openReleasePage() {
    playClickSound();
    const url = releaseInfo?.html_url || 'https://github.com/vik05h/Link-Extractor/releases';
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.open_external_url) {
      (window as any).pywebview.api.open_external_url(url);
    } else {
      window.open(url, '_blank');
    }
  }
</script>

{#if isOpen}
  <div 
    class="modal-backdrop" 
    role="dialog" 
    aria-modal="true"
    tabindex="-1"
    on:click|self={onClose}
    on:keydown={(e) => e.key === 'Escape' && step !== 'downloading' && onClose()}
  >
    <div class="modal-card glass-panel" role="document">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-left">
          <div class="header-icon-halo">
            <Icon name="sparkles" size={18} color="var(--accent-primary)" />
          </div>
          <div>
            <div class="modal-title">
              {isFirstRun ? "WELCOME TO LINK EXTRACTOR v3.8" : "WHAT'S NEW & UPDATES"}
            </div>
            <div class="modal-subtitle">
              {isFirstRun 
                ? "Explore new features, highlights & quick interactive tutorial" 
                : "Version comparison, release highlights & auto-updater"}
            </div>
          </div>
        </div>

        {#if step !== 'downloading'}
          <button type="button" class="btn-close" aria-label="Close dialog" on:click={onClose}>
            <Icon name="close" size={16} />
          </button>
        {/if}
      </div>

      <!-- Top Status & Actions Banner -->
      <div class="top-status-strip glass-card">
        <div class="status-left">
          <div class="status-indicator-pill" class:has-update={hasUpdate}>
            <span class="status-dot"></span>
            <span class="status-text">
              {#if hasUpdate}
                Update Ready: {releaseInfo?.latest_version || 'New Release'}
              {:else if isFirstRun}
                {currentVersion} Installed & Ready
              {:else}
                Up to Date ({currentVersion})
              {/if}
            </span>
          </div>
          <span class="author-tag">by Vikash (@vik05h)</span>
        </div>

        <div class="status-actions">
          {#if hasUpdate && step === 'overview'}
            <button type="button" class="btn-update-cta" on:click={startDownload}>
              <Icon name="download" size={14} color="#060d17" strokeWidth={2.5} />
              <span>Download Update</span>
            </button>
          {/if}

          <button 
            type="button" 
            class="btn-check-updates" 
            disabled={isChecking || step === 'downloading'} 
            on:click={handleCheckUpdatesManual}
            title="Check GitHub Releases"
          >
            <span class="icon-wrap" class:spinning={isChecking}>
              <Icon name="refresh" size={13} />
            </span>
            <span>{isChecking ? 'Checking...' : 'Check Updates'}</span>
          </button>
        </div>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        {#if step === 'overview'}
          <!-- Interactive Version Timeline Pills -->
          <div class="timeline-row-container">
            <div class="timeline-label font-mono">VERSIONS</div>
            <div class="timeline-pills-scroll" on:wheel={handleTimelineWheel}>
              {#each changelogs as item, idx}
                <button
                  type="button"
                  class="timeline-pill"
                  class:active={selectedVersionIndex === idx}
                  class:is-current={item.is_current}
                  class:is-new={item.is_new}
                  on:click={() => { playClickSound(); selectedVersionIndex = idx; }}
                >
                  <span class="pill-version">{item.version}</span>
                  {#if item.is_current}
                    <span class="pill-badge badge-curr">ACTIVE</span>
                  {:else if item.is_new}
                    <span class="pill-badge badge-new">NEW</span>
                  {/if}
                </button>
              {/each}
            </div>
          </div>

          <!-- Active Version Details & Diff Card -->
          {#if activeEntry}
            <div class="version-details-card glass-panel">
              <!-- Version Title & Diff Badge -->
              <div class="card-hero-header">
                <div class="hero-left">
                  <div class="hero-version-tag">{activeEntry.version}</div>
                  <div class="hero-title">{activeEntry.title}</div>
                </div>

                <div class="hero-diff-badge">
                  <Icon name="layers" size={12} color="var(--accent-primary)" />
                  <span>
                    {#if activeEntry.previous_version}
                      Changes vs {activeEntry.previous_version}
                    {:else}
                      Baseline Architecture
                    {/if}
                  </span>
                </div>
              </div>

              <!-- Highlights Section -->
              <div class="section-container">
                <div class="section-title-row">
                  <Icon name="sparkles" size={14} color="var(--accent-primary)" />
                  <span>NEW FEATURES & ARCHITECTURAL HIGHLIGHTS ({activeEntry.highlights?.length || 0})</span>
                </div>
                <div class="highlights-grid">
                  {#each activeEntry.highlights as feat}
                    <div class="feature-item glass-card">
                      <div class="feature-bullet">
                        <Icon name="check" size={12} color="var(--accent-primary)" strokeWidth={3} />
                      </div>
                      <div class="feature-text">{feat}</div>
                    </div>
                  {/each}
                </div>
              </div>

              <!-- Bug Fixes Section -->
              {#if activeEntry.bug_fixes && activeEntry.bug_fixes.length > 0}
                <div class="section-container fixes-section">
                  <div class="section-title-row">
                    <Icon name="shield-check" size={14} color="var(--accent-secondary, #38bdf8)" />
                    <span>RESOLVED ISSUES & HARDENING ({activeEntry.bug_fixes.length})</span>
                  </div>
                  <div class="fixes-grid">
                    {#each activeEntry.bug_fixes as fix}
                      <div class="feature-item fix-item glass-card">
                        <div class="feature-bullet fix-bullet">
                          <Icon name="check" size={12} color="var(--accent-secondary, #38bdf8)" strokeWidth={3} />
                        </div>
                        <div class="feature-text">{fix}</div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          {/if}

        {:else if step === 'downloading'}
          <!-- Active Download HUD -->
          <div class="download-hud glass-card">
            <div class="hud-top-row">
              <div class="hud-status-indicator">
                <span class="spin-radar"></span>
                <span>STREAMING UPDATE VIA GITHUB RELEASES...</span>
              </div>
              <div class="hud-percent font-mono">{percent.toFixed(0)}%</div>
            </div>

            <!-- Progress Bar -->
            <div class="progress-bar-track">
              <div class="progress-bar-fill" style="width: {percent}%;">
                <div class="progress-bar-head"></div>
              </div>
            </div>

            <!-- Download Stats Row -->
            <div class="hud-stats-row font-mono">
              <span>{downloadedStr} / {totalStr}</span>
              <span class="hud-speed">{speedStr}</span>
            </div>

            <div class="download-tip font-mono">
              Binary is securely verified and cached to %APPDATA%\FitGirlLinkExtractor\updates\
            </div>
          </div>

        {:else if step === 'ready'}
          <!-- Ready / Restart State -->
          <div class="ready-banner glass-card">
            <div class="ready-icon-halo">
              <Icon name="check-circle" size={32} color="var(--accent-primary)" />
            </div>

            <div class="ready-title">Update Ready to Apply!</div>

            {#if isFrozen}
              <div class="ready-desc">
                The updated executable will replace the existing binary and automatically restart the application.
              </div>
              <div class="countdown-badge font-mono">
                Restarting automatically in <strong>{autoRestartCountdown}s</strong>...
              </div>
            {:else}
              <div class="ready-desc">
                Running in Python development mode. Standalone executable downloaded to the updates folder.
              </div>
            {/if}
          </div>

        {:else if step === 'error'}
          <!-- Error State -->
          <div class="error-banner glass-card">
            <div class="error-icon-halo">
              <Icon name="alert-triangle" size={28} color="#ef4444" />
            </div>
            <div class="error-title">Update Failed</div>
            <div class="error-desc">{errorMessage}</div>
          </div>
        {/if}
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        {#if step === 'overview'}
          <div class="footer-meta font-mono">
            <span>Link Extractor {currentVersion} • PolyForm & CC BY-NC-SA 4.0</span>
          </div>

          <div class="footer-btn-group">
            <button type="button" class="btn-secondary" on:click={openReleasePage}>
              <Icon name="external-link" size={13} />
              <span>GitHub Releases</span>
            </button>
            {#if onStartTour}
              <button type="button" class="btn-primary" on:click={handleStartTourClick}>
                <Icon name="sparkles" size={14} color="#060d17" strokeWidth={2.5} />
                <span>Start Interactive Tour</span>
              </button>
            {/if}
            <button type="button" class="btn-secondary" on:click={onClose}>
              <span>{isFirstRun ? 'Continue to App' : 'Done'}</span>
            </button>
          </div>

        {:else if step === 'downloading'}
          <button type="button" class="btn-secondary btn-cancel" on:click={cancelDownload}>
            <Icon name="close" size={14} />
            <span>Cancel Download</span>
          </button>

        {:else if step === 'ready'}
          {#if isFrozen}
            <button type="button" class="btn-primary btn-cta" on:click={applyRestart}>
              <Icon name="bolt" size={15} />
              <span>Restart & Update Now</span>
            </button>
          {:else}
            <button type="button" class="btn-secondary" on:click={openUpdatesFolder}>
              <Icon name="package" size={14} />
              <span>Open Updates Folder</span>
            </button>
            <button type="button" class="btn-primary" on:click={launchDownloaded}>
              <Icon name="bolt" size={15} />
              <span>Launch New Binary</span>
            </button>
            <button type="button" class="btn-secondary" on:click={onClose}>
              <span>Close</span>
            </button>
          {/if}

        {:else if step === 'error'}
          <button type="button" class="btn-secondary" on:click={openReleasePage}>
            <Icon name="external-link" size={14} />
            <span>View Releases</span>
          </button>
          <button type="button" class="btn-primary" on:click={startDownload}>
            <Icon name="refresh" size={15} />
            <span>Retry Download</span>
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 10000;
    background: rgba(4, 6, 10, 0.75);
    backdrop-filter: blur(14px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: fadeIn 0.2s ease-out;
  }

  .modal-card {
    width: 680px;
    max-width: 95vw;
    max-height: 88vh;
    background: var(--bg-surface-elevated, #0c0f17);
    border: 1px solid var(--border-hover, rgba(255, 255, 255, 0.14));
    border-radius: var(--radius-lg, 16px);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px var(--accent-glow, rgba(16, 185, 129, 0.25));
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: scaleIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 22px;
    border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-icon-halo {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-title {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.8px;
    color: var(--text-primary, #f1f5f9);
  }

  .modal-subtitle {
    font-size: 11px;
    color: var(--text-muted, #94a3b8);
  }

  .btn-close {
    background: transparent;
    border: none;
    color: var(--text-muted, #94a3b8);
    cursor: pointer;
    padding: 6px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .btn-close:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.08);
  }

  /* Top Status Strip */
  .top-status-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 22px;
    margin: 12px 22px 0 22px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.07);
  }

  .status-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .status-indicator-pill {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 4px 10px;
    border-radius: 9999px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .status-indicator-pill.has-update {
    background: rgba(245, 158, 11, 0.15);
    border-color: rgba(245, 158, 11, 0.4);
  }

  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent-primary, #10b981);
    box-shadow: 0 0 8px var(--accent-primary, #10b981);
  }

  .status-indicator-pill.has-update .status-dot {
    background: #f59e0b;
    box-shadow: 0 0 8px #f59e0b;
    animation: pulseGlow 1.6s infinite;
  }

  .status-text {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-primary, #f1f5f9);
    letter-spacing: 0.2px;
  }

  .author-tag {
    font-size: 11px;
    color: var(--text-muted, #64748b);
  }

  .status-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .btn-update-cta {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 8px;
    border: none;
    background: var(--accent-primary, #10b981);
    color: #060d17;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 0 12px var(--accent-glow, rgba(16, 185, 129, 0.35));
    transition: all 0.15s ease;
  }

  .btn-update-cta:hover {
    filter: brightness(1.1);
    transform: translateY(-1px);
  }

  .btn-check-updates {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    background: rgba(255, 255, 255, 0.05);
    color: var(--text-muted, #94a3b8);
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-check-updates:hover:not(:disabled) {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
    background: rgba(255, 255, 255, 0.08);
  }

  .icon-wrap.spinning {
    animation: spin 1s linear infinite;
  }

  /* Modal Body */
  .modal-body {
    padding: 16px 22px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    max-height: calc(88vh - 160px);
  }

  /* Timeline Pills */
  .timeline-row-container {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .timeline-label {
    font-family: var(--font-display);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted, #64748b);
  }

  .timeline-pills-scroll {
    display: flex;
    align-items: center;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 2px;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .timeline-pills-scroll::-webkit-scrollbar {
    display: none;
  }

  .timeline-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 9999px;
    font-family: var(--font-display);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: var(--text-muted, #94a3b8);
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s ease;
  }

  .timeline-pill:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.08);
  }

  .timeline-pill.active {
    background: rgba(16, 185, 129, 0.15);
    border-color: var(--accent-primary, #10b981);
    color: var(--text-primary, #ffffff);
    box-shadow: 0 0 10px var(--accent-glow, rgba(16, 185, 129, 0.25));
  }

  .pill-version {
    font-family: var(--font-mono);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    font-weight: 700;
  }

  .pill-badge {
    font-size: 9px;
    font-weight: 800;
    padding: 1px 5px;
    border-radius: 4px;
    letter-spacing: 0.4px;
  }

  .badge-curr {
    background: rgba(16, 185, 129, 0.25);
    color: var(--accent-primary, #10b981);
  }

  .badge-new {
    background: rgba(245, 158, 11, 0.3);
    color: #f59e0b;
  }

  /* Version Details Card */
  .version-details-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .card-hero-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .hero-left {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .hero-version-tag {
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 800;
    color: var(--accent-primary, #10b981);
  }

  .hero-title {
    font-family: var(--font-display);
    font-size: 13.5px;
    font-weight: 700;
    line-height: 1.4;
    letter-spacing: 0.015em;
    color: var(--text-primary, #f1f5f9);
  }

  .hero-diff-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 6px;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.25);
    font-family: var(--font-display);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--accent-primary, #10b981);
    white-space: nowrap;
    letter-spacing: 0.05em;
  }

  .section-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .section-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--font-display);
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted, #94a3b8);
  }

  .highlights-grid, .fixes-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .feature-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(255, 255, 255, 0.05);
  }

  .feature-bullet {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .feature-item.fix-item {
    background: rgba(56, 189, 248, 0.02);
    border-color: rgba(56, 189, 248, 0.08);
  }

  .feature-bullet.fix-bullet {
    background: rgba(56, 189, 248, 0.15);
    border-color: rgba(56, 189, 248, 0.3);
  }

  .feature-text {
    font-size: 12px;
    line-height: 1.45;
    color: var(--text-primary, #e2e8f0);
  }

  /* Download HUD */
  .download-hud {
    padding: 24px 20px;
    border-radius: 12px;
    background: rgba(16, 185, 129, 0.03);
    border: 1px solid rgba(16, 185, 129, 0.2);
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .hud-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .hud-status-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.6px;
    color: var(--accent-primary, #10b981);
  }

  .spin-radar {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid var(--accent-primary, #10b981);
    border-top-color: transparent;
    animation: spin 0.8s linear infinite;
  }

  .hud-percent {
    font-size: 18px;
    font-weight: 900;
    color: var(--accent-primary, #10b981);
  }

  .progress-bar-track {
    width: 100%;
    height: 8px;
    border-radius: 9999px;
    background: rgba(255, 255, 255, 0.08);
    overflow: hidden;
    position: relative;
  }

  .progress-bar-fill {
    height: 100%;
    border-radius: 9999px;
    background: linear-gradient(90deg, var(--accent-primary, #10b981), #34d399);
    box-shadow: 0 0 12px var(--accent-glow, rgba(16, 185, 129, 0.5));
    transition: width 0.2s ease-out;
    position: relative;
  }

  .progress-bar-head {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: #ffffff;
    box-shadow: 0 0 6px #ffffff;
  }

  .hud-stats-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-muted, #94a3b8);
  }

  .hud-speed {
    color: var(--accent-primary, #10b981);
    font-weight: 700;
  }

  .download-tip {
    font-size: 10px;
    color: var(--text-muted, #64748b);
    line-height: 1.4;
  }

  /* Ready State */
  .ready-banner {
    padding: 30px 20px;
    border-radius: 12px;
    background: rgba(16, 185, 129, 0.05);
    border: 1px solid rgba(16, 185, 129, 0.25);
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 12px;
  }

  .ready-icon-halo {
    width: 54px;
    height: 54px;
    border-radius: 50%;
    background: rgba(16, 185, 129, 0.15);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ready-title {
    font-size: 16px;
    font-weight: 800;
    color: var(--text-primary, #f1f5f9);
  }

  .ready-desc {
    font-size: 12px;
    color: var(--text-muted, #94a3b8);
    max-width: 440px;
    line-height: 1.5;
  }

  .countdown-badge {
    padding: 6px 14px;
    border-radius: 9999px;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid var(--accent-primary, #10b981);
    color: var(--accent-primary, #10b981);
    font-size: 12px;
  }

  /* Error State */
  .error-banner {
    padding: 30px 20px;
    border-radius: 12px;
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.25);
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 12px;
  }

  .error-icon-halo {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: rgba(239, 68, 68, 0.15);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .error-title {
    font-size: 15px;
    font-weight: 800;
    color: #ef4444;
  }

  .error-desc {
    font-size: 12px;
    color: var(--text-muted, #94a3b8);
    max-width: 440px;
    line-height: 1.5;
  }

  /* Modal Footer */
  .modal-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 22px;
    border-top: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    background: rgba(0, 0, 0, 0.2);
  }

  .footer-meta {
    font-size: 10px;
    color: var(--text-muted, #64748b);
  }

  .footer-btn-group {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .btn-primary {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 7px 18px;
    border-radius: 8px;
    border: none;
    background: var(--accent-primary, #10b981);
    color: #060d17;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 0 12px var(--accent-glow, rgba(16, 185, 129, 0.3));
    transition: all 0.15s ease;
  }

  .btn-primary:hover {
    filter: brightness(1.1);
    transform: translateY(-1px);
  }

  .btn-secondary {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    background: rgba(255, 255, 255, 0.05);
    color: var(--text-muted, #94a3b8);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-secondary:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
    background: rgba(255, 255, 255, 0.08);
  }

  .btn-cancel {
    margin-left: auto;
    color: #ef4444;
    border-color: rgba(239, 68, 68, 0.3);
  }

  .btn-cancel:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #f87171;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes pulseGlow {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(1.15); }
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.96); }
    to { opacity: 1; transform: scale(1); }
  }
</style>
