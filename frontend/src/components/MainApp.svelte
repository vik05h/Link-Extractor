<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import LivingCanvas from './LivingCanvas.svelte';
  import GameStage from './GameStage.svelte';
  import DiscoveryHub from './DiscoveryHub.svelte';
  import SettingsModal from './SettingsModal.svelte';
  import HistoryModal from './HistoryModal.svelte';
  import CacheConflictModal from './CacheConflictModal.svelte';
  import UpdateModal from './UpdateModal.svelte';
  import OnboardingTour from './OnboardingTour.svelte';
  import ReportIssueModal from './ReportIssueModal.svelte';
  import ClipboardSentinel from './ClipboardSentinel.svelte';
  import SplashLoader from './SplashLoader.svelte';
  import BrandLogo from './BrandLogo.svelte';
  import Icon from './icons/Icon.svelte';
  import type { PartItem, GameRecord } from '../types';
  import { playClickSound, playSuccessChime, toggleAudioMute, isAudioMuted } from '../utils/audio';
  import { waitForBridge } from '../utils/bridgeReady';
  import { APP_VERSION, FIRST_RUN_KEY } from '../version';
  import { runBoot } from '../utils/boot';
  import { initLiquidGlass, liquidGlass, watchGlassPerformance } from '../utils/liquidGlass';
  import { glassBubble } from '../utils/glassBubble';
  import { say, sayNow } from '../utils/voice';
  import { chooseLaunchScreen } from '../utils/launch';
  import { advanceSample, createSampleGame, type SampleGame } from '../utils/sampleGame';

  // Startup: the splash shows while loading, then plays into the app, then the rest settles.
  const REVEAL_SETTLE_MS = 620;
  let bootPhase: 'loading' | 'exiting' | 'settling' | 'done' = 'loading';
  let bootProgress = 0.05;
  let bootStatus = 'Starting up';
  const afterBoot: (() => void)[] = [];

  // Held so the browser keeps these decoded until the Hub shows them.
  const preloadedCovers: HTMLImageElement[] = [];

  let resolveFirstSync: (feed: any) => void = () => {};
  const firstSyncEnded = new Promise<any>((resolve) => {
    resolveFirstSync = resolve;
  });

  // Navigation View: 'community' or 'stage'
  let currentView: 'community' | 'stage' = 'community';

  // Active Game State
  let gameTitle = 'FitGirl Game Repack';
  let coverUrl = '';
  let sourceUrl = '';
  let totalSizeStr = '0 B';
  let isRunning = false;
  let statusMessage = 'Paste any FitGirl URL or click a Community Repack to begin.';
  let parts: PartItem[] = [];
  let logs: string[] = [`[System] Link Extractor ${APP_VERSION} Turbo Engine initialized.`];

  // Community Feed State
  let communityGames: GameRecord[] = [];
  let isCommunityLoading = true;
  let isCommunityOffline = false;

  // Modals & Sound
  let settingsOpen = false;
  let historyOpen = false;
  let conflictModalOpen = false;
  let conflictRecord: any = null;
  let pendingTargetUrl = '';
  let conflictFromPipeline = false;
  let isCheckingCache = false;
  let audioMuted = false;
  let currentTheme = 'adaptive';
  let tourOpen = false;
  let reportModalOpen = false;

  // Auto-Updater State
  let updateModalOpen = false;
  let updateReleaseInfo: any = null;
  let isFrozenApp = false;
  let appCurrentVersion = APP_VERSION;
  let hasUpdateAvailable = false;
  /** What's New is showing because this version just arrived. */
  let isFirstRunOfVersion = false;

  function markVersionSeen() {
    isFirstRunOfVersion = false;
    try {
      localStorage.setItem(FIRST_RUN_KEY, 'true');
    } catch {}
  }

  // After an update, What's New is the whole welcome; the tour stays on its button.
  function handleCloseUpdateModal() {
    updateModalOpen = false;
    if (typeof window !== 'undefined' && updateReleaseInfo?.latest_version) {
      try {
        sessionStorage.setItem('le_dismissed_update_' + updateReleaseInfo.latest_version, 'true');
      } catch {}
    }
    if (isFirstRunOfVersion) markVersionSeen();
  }

  function handleStartTourFromUpdate() {
    updateModalOpen = false;
    markVersionSeen();
    setTimeout(startTour, 350);
  }

  // The tour: while it is open the Stage shows a made-up sample game, and the real game,
  // including a running extraction, carries on untouched underneath until it closes.
  const SAMPLE_TICK_MS = 650;
  const FILTER_CHOICE_KEY = 'le_selective_filter';
  let tourSample: SampleGame | null = null;
  let sampleTimer: ReturnType<typeof setInterval> | null = null;
  let viewBeforeTour: 'community' | 'stage' = 'community';
  let filterChoiceBeforeTour: string | null = null;

  function startTour() {
    if (tourOpen) return;
    viewBeforeTour = currentView;
    historyOpen = false;
    settingsOpen = false;
    updateModalOpen = false;
    reportModalOpen = false;
    try {
      filterChoiceBeforeTour = localStorage.getItem(FILTER_CHOICE_KEY);
    } catch {}
    tourSample = createSampleGame();
    sampleTimer = setInterval(() => {
      if (tourSample) tourSample = { ...tourSample, parts: advanceSample(tourSample.parts) };
    }, SAMPLE_TICK_MS);
    tourOpen = true;
  }

  function endTour() {
    tourOpen = false;
    if (sampleTimer) clearInterval(sampleTimer);
    sampleTimer = null;
    tourSample = null;
    currentView = viewBeforeTour;
    // Trying the filter chips on the sample game must not change the user's saved choice.
    try {
      if (filterChoiceBeforeTour === null) localStorage.removeItem(FILTER_CHOICE_KEY);
      else localStorage.setItem(FILTER_CHOICE_KEY, filterChoiceBeforeTour);
    } catch {}
  }

  function selectNav(index: number) {
    playClickSound();
    if (index === 2) {
      historyOpen = true;
      return;
    }
    historyOpen = false;
    currentView = index === 1 ? 'stage' : 'community';
  }

  // URL Input
  let inputUrl = '';
  let detectedType = '';
  let urlInputEl: HTMLInputElement;

  // Toast Notification
  let toastMessage = '';
  let toastTimeout: any = null;

  function showToast(msg: string) {
    toastMessage = msg;
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => { toastMessage = ''; }, 4000);
  }

  // Handle URL change
  function handleUrlInput() {
    const raw = inputUrl.trim();
    if (!raw) {
      detectedType = '';
      return;
    }
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.detect_url(raw).then((res: any) => {
        detectedType = res.url_type || '';
      });
    }
  }

  // Start Extraction with Duplicate Check. Python decides what counts as the same game.
  function startExtraction(urlToExtract?: string, forceFresh: boolean = false) {
    const target = (urlToExtract || inputUrl).trim();
    if (!target) {
      showToast('Please paste a valid FitGirl game or pastebin URL.');
      return;
    }
    if (isRunning || isCheckingCache) {
      showToast('An extraction is already running.');
      return;
    }

    if (forceFresh || !(window as any).pywebview?.api?.check_existing_game) {
      executeExtraction(target, forceFresh);
      return;
    }

    isCheckingCache = true;
    (window as any).pywebview.api.check_existing_game(target).then((res: any) => {
      isCheckingCache = false;
      if (res && res.exists && res.record) {
        if (res.is_expired) {
          const ageStr = res.record.age_str || 'more than a day ago';
          showToast(`Cached links for "${res.record.title}" are outdated (${ageStr}). Resolving fresh mirrors to update database...`);
          executeExtraction(target, true);
        } else {
          pendingTargetUrl = target;
          conflictFromPipeline = false;
          conflictRecord = res.record;
          conflictModalOpen = true;
        }
      } else {
        executeExtraction(target, false);
      }
    }).catch(() => {
      isCheckingCache = false;
      executeExtraction(target, false);
    });
  }

  function executeExtraction(target: string, forceFresh: boolean) {
    playClickSound();
    isRunning = true;
    currentView = 'stage';
    sourceUrl = target;
    activeGameSlug = '';
    statusMessage = 'Connecting to high-speed resolution pool...';
    parts = [];
    logs = [`[Pipeline] Starting multi-tab extraction for: ${target} ${forceFresh ? '(Overwrite Mode)' : ''}`];

    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.start_extraction(target, null, forceFresh).then((res: any) => {
        if (res && res.status === 'error') {
          isRunning = false;
          statusMessage = res.message;
          showToast(res.message);
        }
      });
    }
  }

  function handleSelectInstantConflict() {
    conflictModalOpen = false;
    if (conflictRecord) {
      if (conflictFromPipeline) {
        (window as any).pywebview?.api?.decide_duplicate('instant');
      }
      handleLoadCommunityRecord(conflictRecord);
    }
  }

  function handleSelectFreshConflict() {
    conflictModalOpen = false;
    if (conflictFromPipeline) {
      // The run that asked is still going and carries on from here.
      (window as any).pywebview?.api?.decide_duplicate('fresh');
      return;
    }
    const target = pendingTargetUrl || sourceUrl || inputUrl;
    if (target) {
      executeExtraction(target, true);
    }
  }

  function handleCloseConflictModal() {
    conflictModalOpen = false;
    conflictRecord = null;
    pendingTargetUrl = '';
    if (conflictFromPipeline) {
      (window as any).pywebview?.api?.decide_duplicate('cancel');
    }
  }

  function handleCancelExtraction() {
    playClickSound();
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.cancel_pipeline();
    }
  }

  // Load Community Record directly into Stage
  function handleLoadCommunityRecord(rec: any) {
    if (!rec) return;
    activeGameSlug = rec.source === 'history' ? '' : (rec.slug || '');

    gameTitle = rec.title;
    coverUrl = rec.image_url;
    sourceUrl = rec.source_url;
    totalSizeStr = rec.total_size_str;
    currentView = 'stage';
    statusMessage = 'Loaded instant pre-fetched direct links from Community Cache!';

    // If direct URLs are already included on the record (e.g. from history or check_existing_game)
    if (rec.urls && Array.isArray(rec.urls) && rec.urls.length > 0) {
      parts = rec.urls.map((u: string, i: number) => {
        const raw = u.includes('#') ? u.split('#').pop() : `Part ${i + 1}`;
        return {
          index: i + 1,
          url: u,
          direct_url: u,
          filename: decodeURIComponent(raw || `Part ${i + 1}`),
          status: 'resolved',
          size: rec.total_size_str || ''
        };
      });

      logs = [`[Database] Loaded ${rec.urls.length} cached direct links for ${gameTitle} with 0s wait!`];
      showToast(sayNow('toast.loadedParts', { count: rec.urls.length, title: gameTitle }));
      return;
    }

    // Immediately populate part slots so Defrag Matrix renders instantly
    const totalParts = rec.total_parts || 0;
    if (totalParts > 0) {
      parts = Array.from({ length: totalParts }, (_, i) => ({
        index: i + 1,
        url: '',
        direct_url: '',
        filename: `Part ${i + 1}`,
        status: 'pending',
        size: ''
      }));
    } else {
      parts = [];
    }

    if (typeof window !== 'undefined' && (window as any).pywebview && rec.slug) {
      (window as any).pywebview.api.get_game_urls(rec.slug).then((urls: string[]) => {
        if (urls && urls.length > 0) {
          parts = urls.map((u, i) => {
            const raw = u.includes('#') ? u.split('#').pop() : `Part ${i + 1}`;
            return {
              index: i + 1,
              url: u,
              direct_url: u,
              filename: decodeURIComponent(raw || `Part ${i + 1}`),
              status: 'resolved',
              size: rec.total_size_str
            };
          });

          // Infer real game title from filenames if generic
          if (gameTitle === 'FitGirl Pastebin Download' || gameTitle === 'FuckingFast Direct Parts' || gameTitle.includes('Pastebin')) {
            const firstWithHash = urls.find((u: string) => u.includes('#'));
            if (firstWithHash) {
              const rawName = decodeURIComponent(firstWithHash.split('#').pop() || '');
              const clean = rawName
                .replace(/\.part\d+\.rar/i, '')
                .replace(/\.rar/i, '')
                .replace(/--_fitgirl-repacks\.site_--.*/i, '')
                .replace(/[-_.]+/g, ' ')
                .trim();
              if (clean && clean.length > 2) {
                gameTitle = clean.split(' ').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
              }
            }
          }

          logs = [`[Community] Loaded ${urls.length} cached direct links for ${gameTitle}`];
          showToast(sayNow('toast.loadedParts', { count: urls.length, title: gameTitle }));
        } else {
          showToast(`No links cached for ${rec.title}. Try live extraction.`);
        }
      }).catch((err: any) => {
        console.error('Failed to get game URLs:', err);
        showToast('Error loading game URLs from cache');
      });
    }
  }

  function handleReextractGame(rec: any) {
    if (!rec) return;
    if (!rec.source_url) {
      showToast(`"${rec.title}" has no source page saved. Paste its FitGirl link to extract it again.`);
      return;
    }
    showToast(`Cached links for "${rec.title}" are outdated (${rec.age_str || 'more than a day ago'}). Resolving fresh mirrors...`);
    startExtraction(rec.source_url, true);
  }

  // Load History Item directly into Stage
  function handleLoadHistoryRecord(rec: any) {
    activeGameSlug = '';
    gameTitle = rec.game_title;
    coverUrl = '';
    sourceUrl = rec.source_url;
    totalSizeStr = rec.total_size || '0 B';
    currentView = 'stage';
    statusMessage = 'Loaded from local SQLite archive';

    parts = (rec.resolved_links || []).map((u: string, i: number) => ({
      index: i + 1,
      url: u,
      direct_url: u,
      filename: u.includes('#') ? u.split('#').pop() : `Part ${i + 1}`,
      status: 'resolved',
      size: rec.total_size || ''
    }));
    logs = [`[Archive] Loaded ${rec.resolved_links.length} links for ${rec.game_title}`];
    showToast(rec.is_partial
      ? `Loaded ${rec.game_title}. This record is incomplete: ${rec.resolved_count} of ${rec.parts_count} parts.`
      : sayNow('toast.loadedFromVault', { title: rec.game_title }));
  }

  let activeGameSlug = '';
  const countedGrabs = new Set<string>();

  // Counts one grab per game per session, however many ways its links get used.
  function countGrab(slug: string): boolean {
    if (!slug || countedGrabs.has(slug)) return false;
    countedGrabs.add(slug);
    if ((window as any).pywebview?.api?.track_game_usage) {
      (window as any).pywebview.api.track_game_usage(slug).catch(() => {});
    }
    return true;
  }

  function pushUrlsToJd2(urls: string[], title: string) {
    if (!urls || urls.length === 0) {
      showToast('No URLs available to push to JDownloader 2.');
      return;
    }
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.push_to_jd2(urls, title, sourceUrl).then((res: any) => {
        showToast(res?.message || sayNow('toast.pushed'));
      }).catch(() => {
        showToast('Error communicating with JDownloader 2');
      });
    }
  }

  // Push the game on the Stage to JDownloader 2
  function handlePushToJd2(urls: string[], title: string) {
    countGrab(activeGameSlug);
    pushUrlsToJd2(urls, title);
  }

  // Push community game directly to JDownloader 2
  function handlePushCommunityGameToJd2(slug: string, title: string) {
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.get_game_urls(slug).then((urls: string[]) => {
        if (urls && urls.length > 0) {
          pushUrlsToJd2(urls, title);
        } else {
          showToast(`No cached direct links found for ${title}.`);
        }
      }).catch(() => {
        showToast(`Failed to load links for ${title}`);
      });
    }
  }

  // Export URLs
  function handleExport(format: 'txt' | 'json' | 'crawljob', urls: string[], title: string) {
    countGrab(activeGameSlug);
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.export_urls(format, urls, title, totalSizeStr).then((res: any) => {
        showToast(res.message || sayNow('toast.exported'));
      });
    }
  }

  // Copy all direct URLs
  function handleCopyAll(urls: string[]) {
    countGrab(activeGameSlug);
    if (typeof window !== 'undefined' && (window as any).pywebview) {
      (window as any).pywebview.api.copy_to_clipboard(urls.join('\n')).then(() => {
        showToast(sayNow('toast.copiedAll', { count: urls.length }));
      });
    }
  }

  // Load the community list. A forced refresh, or a list that is too old, downloads a new one
  // in the background, and community:feed_updated calls this again when that ends.
  async function refreshCommunity(force: boolean = false): Promise<any> {
    const ready = await waitForBridge('get_community_feed', 7000);
    if (!ready) {
      isCommunityLoading = false;
      return null;
    }
    try {
      const feed = await (window as any).pywebview.api.get_community_feed(force);
      communityGames = feed?.games || [];
      isCommunityOffline = !!feed?.offline;
      // Keep the loader up only while there is nothing to show and a download is running.
      isCommunityLoading = communityGames.length === 0 && !!feed?.syncing;
      return feed;
    } catch (err) {
      console.error('[Community] API error:', err);
      isCommunityLoading = false;
      return null;
    }
  }

  function preloadCover(url: string): Promise<void> {
    const image = new Image();
    image.decoding = 'async';
    image.src = url;
    preloadedCovers.push(image);
    return image.decode();
  }

  async function bootApp() {
    await runBoot(
      {
        waitForBridge: () => waitForBridge('get_community_feed', 7000),
        loadFeed: () => refreshCommunity(),
        waitForSync: () => firstSyncEnded,
        preloadImage: preloadCover,
      },
      (progress, status) => {
        bootProgress = progress;
        bootStatus = status;
      }
    );
    // Let the bar visibly reach the end before the card starts moving.
    setTimeout(() => {
      bootPhase = 'exiting';
    }, 260);
  }

  function handleSplashFinished() {
    bootPhase = 'settling';
    setTimeout(() => {
      bootPhase = 'done';
      afterBoot.splice(0).forEach((run) => run());
      watchGlassPerformance();
    }, REVEAL_SETTLE_MS);
  }

  function whenBooted(run: () => void) {
    if (bootPhase === 'done') run();
    else afterBoot.push(run);
  }

  // Manual check for updates triggered from Settings
  async function handleManualCheckUpdates() {
    if (typeof window !== 'undefined' && (window as any).pywebview?.api?.check_for_updates) {
      try {
        const res = await (window as any).pywebview.api.check_for_updates();
        if (res && res.has_update && res.release_info) {
          hasUpdateAvailable = true;
          updateReleaseInfo = res.release_info;
          isFrozenApp = !!res.is_frozen;
          if (res.current_version) appCurrentVersion = res.current_version;
          updateModalOpen = true;
          return res;
        } else {
          hasUpdateAvailable = false;
          showToast(res?.message || 'You are running the latest version.');
          return res;
        }
      } catch (err: any) {
        showToast(`Failed to check updates: ${err?.message || err}`);
        return { has_update: false, message: String(err) };
      }
    } else {
      showToast('Updater bridge not connected yet.');
      return { has_update: false, message: 'Bridge not ready' };
    }
  }

  // Global Keyboard Shortcuts
  function handleGlobalKeydown(e: KeyboardEvent) {
    // The tour owns the keyboard while it is open, and moving views under it would lose its place.
    if (tourOpen) return;
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      if (e.key === 'Escape') {
        settingsOpen = false;
        historyOpen = false;
        conflictModalOpen = false;
        updateModalOpen = false;
      }
      return;
    }

    if (e.key === 'Escape') {
      settingsOpen = false;
      historyOpen = false;
      conflictModalOpen = false;
      updateModalOpen = false;
    } else if ((e.ctrlKey || e.metaKey) && e.key === '1') {
      e.preventDefault();
      currentView = 'community';
    } else if ((e.ctrlKey || e.metaKey) && e.key === '2') {
      e.preventDefault();
      currentView = 'stage';
    } else if ((e.ctrlKey || e.metaKey) && e.key === '3') {
      e.preventDefault();
      historyOpen = true;
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'j') {
      e.preventDefault();
      if (parts.length > 0) {
        const resolved = parts.filter(p => !p.excluded && p.status === 'resolved' && p.direct_url).map(p => p.direct_url as string);
        handlePushToJd2(resolved, gameTitle);
      }
    }
  }

  // Says only what is true about a finished run. "Verified" needs every part present and checked.
  function describeCompletion(d: any): { status: string; toast: string } {
    const size = d.total_size_str || '0 B';
    if (d.status === 'partial') {
      const missing = d.expected_parts - d.parts_count;
      return {
        status: `Only ${d.parts_count} of ${d.expected_parts} parts are ready. A multi-part archive will not extract with parts missing.`,
        toast: `${missing} of ${d.expected_parts} parts failed. These links are incomplete.`
      };
    }
    if (d.verified) {
      return {
        status: `Verified 100% of parts (${size})! Direct links ready.`,
        toast: sayNow('toast.verified', { count: d.parts_count, size })
      };
    }
    if (!d.validated) {
      return {
        status: `All ${d.parts_count} parts resolved. Link checking is off in Settings, so they are not verified.`,
        toast: `${d.parts_count} parts ready (not verified)`
      };
    }
    return {
      status: `All ${d.parts_count} parts resolved, but ${d.unverified_count} could not be checked right now, so they are not verified.`,
      toast: `${d.parts_count} parts ready. ${d.unverified_count} could not be checked.`
    };
  }

  // Python Event Listeners
  function setupEventListeners() {
    window.addEventListener('pipeline:status' as any, (e: CustomEvent) => {
      if (e.detail?.message) {
        statusMessage = e.detail.message;
        logs = [...logs, `[Status] ${e.detail.message}`];
      }
    });

    window.addEventListener('pipeline:game_meta' as any, (e: CustomEvent) => {
      if (e.detail?.title) gameTitle = e.detail.title;
      if (e.detail?.image_url) coverUrl = e.detail.image_url;
      logs = [...logs, `[Meta] Detected: ${e.detail.title} (${e.detail.parts_count} parts)`];
    });

    window.addEventListener('pipeline:init_parts' as any, (e: CustomEvent) => {
      if (e.detail) {
        parts = e.detail;
      }
    });

    window.addEventListener('pipeline:part_update' as any, (e: CustomEvent) => {
      const p = e.detail;
      if (!p) return;
      
      // Update matching part by part_name or index
      parts = parts.map(item => {
        if (p.part_name && item.filename === p.part_name) {
          return {
            ...item,
            status: p.status === 'resolved' ? 'resolved' : (p.status === 'failed' ? 'failed' : 'decrypting'),
            direct_url: p.direct_url || item.direct_url
          };
        }
        return item;
      });
      logs = [...logs, `[Worker] ${p.part_name || 'Part'}: ${p.status?.toUpperCase()} (${p.avg_speed || ''} | ETA: ${p.eta || ''})`];
    });

    window.addEventListener('pipeline:log' as any, (e: CustomEvent) => {
      if (e.detail?.message) {
        logs = [...logs, `[Engine] ${e.detail.message}`];
      }
    });

    window.addEventListener('pipeline:val_update' as any, (e: CustomEvent) => {
      const v = e.detail;
      if (!v) return;
      logs = [...logs, `[Validator] ${v.current}/${v.total} ${(v.verdict || '').toUpperCase()}: ${v.error || v.size}`];
      parts = parts.map(p => {
        if (p.direct_url !== v.url) return p;
        return v.verdict === 'dead' ? { ...p, size: v.size, status: 'failed' } : { ...p, size: v.size };
      });
    });

    window.addEventListener('pipeline:complete' as any, (e: CustomEvent) => {
      const d = e.detail;
      isRunning = false;
      if (d.total_size_str) totalSizeStr = d.total_size_str;

      const failed: { filename: string; reason: string }[] = d.failed_parts || [];
      const failedNames = new Set(failed.map(f => f.filename));
      parts = parts.map(p => (failedNames.has(p.filename || '') ? { ...p, status: 'failed' } : p));

      const summary = describeCompletion(d);
      statusMessage = summary.status;
      logs = [
        ...logs,
        ...failed.map(f => `[Failed] ${f.filename}: ${f.reason}`),
        ...(d.publish_error ? [`[Community] Not shared: ${d.publish_error}`] : []),
        `[Complete] ${summary.status}`
      ];
      if (d.status === 'complete') playSuccessChime();
      showToast(summary.toast);
    });

    window.addEventListener('pipeline:cancelled' as any, (e: CustomEvent) => {
      isRunning = false;
      if (e.detail?.reason === 'instant') return;
      statusMessage = 'Extraction cancelled.';
      logs = [...logs, `[Cancelled] Stopped by user.`];
      showToast('Extraction cancelled.');
    });

    window.addEventListener('pipeline:duplicate_detected' as any, (e: CustomEvent) => {
      const rec = e.detail;
      if (rec) {
        pendingTargetUrl = sourceUrl || inputUrl;
        conflictFromPipeline = true;
        conflictRecord = rec;
        conflictModalOpen = true;
      }
    });

    window.addEventListener('community:feed_updated' as any, () => {
      refreshCommunity(false).then(resolveFirstSync);
    });

    window.addEventListener('updater:available' as any, (e: CustomEvent) => {
      const d = e.detail;
      if (d && d.release_info) {
        hasUpdateAvailable = true;
        updateReleaseInfo = d.release_info;
        isFrozenApp = !!d.is_frozen;
        if (d.current_version) appCurrentVersion = d.current_version;

        // Auto-popup if not dismissed in this session
        const version = d.release_info.latest_version || '';
        const dismissed = typeof window !== 'undefined' && sessionStorage.getItem('le_dismissed_update_' + version);
        if (!dismissed) {
          whenBooted(() => {
            updateModalOpen = true;
            showToast(`A new update (${version || 'v' + d.release_info.version}) is available!`);
          });
        }
      }
    });

    window.addEventListener('pipeline:error' as any, (e: CustomEvent) => {
      isRunning = false;
      statusMessage = `Error: ${e.detail?.message || 'Failed'}`;
      logs = [...logs, `[Error] ${e.detail?.message}`];
      showToast(`Error: ${e.detail?.message}`);
    });
  }

  $: if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', currentTheme);
  }

  $: activeNavIndex = historyOpen ? 2 : (currentView === 'stage' ? 1 : 0);

  onMount(() => {
    if (typeof window !== 'undefined') {
      currentTheme = localStorage.getItem('app_theme') || 'adaptive';
      document.documentElement.setAttribute('data-theme', currentTheme);
      audioMuted = isAudioMuted();

      initLiquidGlass();
      setupEventListeners();
      window.addEventListener('keydown', handleGlobalKeydown);

      bootApp();
      // The loader must never hang, even if the sync's end event is somehow lost.
      setTimeout(() => { isCommunityLoading = false; }, 20000);

      waitForBridge('get_update_status', 6000).then((ready) => {
        if (ready && (window as any).pywebview?.api?.get_update_status) {
          (window as any).pywebview.api.get_update_status().then((stat: any) => {
            if (stat && stat.has_update) {
              hasUpdateAvailable = true;
              if (stat.release_info) updateReleaseInfo = stat.release_info;
            }
          }).catch(() => {});
        }
      });

      // A new install gets the tour. After an update, What's New opens once instead.
      const launch = chooseLaunchScreen({
        tourCompleted: !!localStorage.getItem('le_tour_completed'),
        seenThisVersion: !!localStorage.getItem(FIRST_RUN_KEY),
      });
      if (launch === 'tour') {
        whenBooted(startTour);
      } else if (launch === 'whats-new') {
        isFirstRunOfVersion = true;
        whenBooted(() => {
          updateModalOpen = true;
        });
      }

      // Global Client-Side Crash Diagnostic Listener
      window.onerror = (message, source, lineno, colno, error) => {
        try {
          const stack = error?.stack || `Error at ${source}:${lineno}:${colno}`;
          if ((window as any).pywebview?.api?.report_client_crash) {
            (window as any).pywebview.api.report_client_crash(String(message), stack);
          }
        } catch {}
      };

      window.onunhandledrejection = (event) => {
        try {
          const reason = event.reason;
          const msg = reason?.message || String(reason);
          const stack = reason?.stack || 'Unhandled Promise Rejection';
          if ((window as any).pywebview?.api?.report_client_crash) {
            (window as any).pywebview.api.report_client_crash(msg, stack);
          }
        } catch {}
      };
    }
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', handleGlobalKeydown);
    }
  });
</script>

<div
  class="app-layout-root"
  class:is-booting={bootPhase === 'loading'}
  class:is-revealing={bootPhase === 'exiting' || bootPhase === 'settling'}
>
  <!-- Living Canvas Ambient Color Bleed Background -->
  <LivingCanvas {coverUrl} theme={currentTheme} activeView={currentView} />

  <!-- Sidebar: Liquid Glass, with a glass bubble over the selected item -->
  <aside class="left-sidebar glass-panel" use:liquidGlass>
    <!-- Brand Logo -->
    <button
      type="button"
      class="sidebar-logo-btn"
      title="Link Extractor {APP_VERSION}"
      aria-label="Link Extractor {APP_VERSION}"
      on:click={() => { currentView = 'community'; historyOpen = false; playClickSound(); }}
    >
      <div class="logo-mark">
        <BrandLogo />
      </div>
    </button>

    <!-- Click, drag or use the arrow keys; utils/glassBubble.ts moves the bubble -->
    <nav
      class="sidebar-nav"
      aria-label="Main"
      use:glassBubble={{ axis: 'y', selected: activeNavIndex, onSelect: selectNav, host: '.app-layout-root', variant: 'glass-bubble--nav', size: 58 }}
    >
      <button
        type="button"
        class="sidebar-item"
        class:active={activeNavIndex === 0}
        aria-current={activeNavIndex === 0 ? 'page' : undefined}
        data-bubble-item
        title="Community Hub (Ctrl+1)"
      >
        <span class="tab-content-zoom">
          <Icon name="globe" size={20} />
          <span class="nav-label">Hub</span>
        </span>
      </button>

      <button
        type="button"
        class="sidebar-item"
        class:active={activeNavIndex === 1}
        aria-current={activeNavIndex === 1 ? 'page' : undefined}
        data-bubble-item
        title="Active Game Stage (Ctrl+2)"
      >
        <span class="tab-content-zoom">
          <Icon name="gamepad" size={20} />
          <span class="nav-label">Stage</span>
        </span>
      </button>

      <button
        type="button"
        class="sidebar-item"
        class:active={activeNavIndex === 2}
        aria-current={activeNavIndex === 2 ? 'page' : undefined}
        id="tour-nav-vault"
        data-bubble-item
        title="Extraction Vault / History (Ctrl+3)"
      >
        <span class="tab-content-zoom">
          <Icon name="history" size={20} />
          <span class="nav-label">Vault</span>
        </span>
      </button>
    </nav>

    <!-- Bottom Utility Controls -->
    <div class="sidebar-footer" id="tour-sidebar-footer">
      <button 
        type="button" 
        class="sidebar-icon-btn tour-trigger-btn" 
        title="Interactive Guided Tour"
        aria-label="Interactive Guided Tour"
        on:click={() => { playClickSound(); startTour(); }}
      >
        <Icon name="help-circle" size={18} />
      </button>

      <button 
        type="button" 
        class="sidebar-icon-btn issue-trigger-btn" 
        title="Community Issue Center (Bugs & Feedback)"
        on:click={() => { playClickSound(); reportModalOpen = true; }}
      >
        <Icon name="bug" size={18} color="#f43f5e" />
      </button>

      <button 
        type="button" 
        class="sidebar-icon-btn update-btn" 
        class:has-update={hasUpdateAvailable}
        title={hasUpdateAvailable ? "Update Available! View What's New & Download" : "What's New & Updates (" + appCurrentVersion + ")"}
        on:click={() => { playClickSound(); updateModalOpen = true; }}
      >
        <Icon name="sparkles" size={18} />
        {#if hasUpdateAvailable}
          <span class="update-pulse-dot" aria-hidden="true"></span>
        {/if}
      </button>

      <button 
        type="button" 
        class="sidebar-icon-btn" 
        title={audioMuted ? 'Unmute Audio Haptics' : 'Mute Audio Haptics'}
        on:click={() => { audioMuted = toggleAudioMute(); }}
      >
        <Icon name={audioMuted ? 'volume-x' : 'volume'} size={18} />
      </button>

      <button 
        type="button" 
        class="sidebar-icon-btn" 
        title="Settings & Themes"
        on:click={() => { settingsOpen = true; playClickSound(); }}
      >
        <Icon name="settings" size={18} />
      </button>
    </div>
  </aside>

  <!-- Main Viewport Area -->
  <div class="main-viewport">
    <!-- Top Command Deck (URL Input Bar) -->
    <header class="top-command-deck glass-panel" id="tour-url-bar" use:liquidGlass>
      <div class="input-field-container">
        <span class="input-leading-icon">
          <Icon name="link" size={16} color="var(--text-muted)" />
        </span>

        <input 
          bind:this={urlInputEl}
          type="text" 
          class="url-input-box" 
          placeholder="Paste FitGirl game page URL, pastebin mirror, or direct FuckingFast link..." 
          bind:value={inputUrl}
          on:input={handleUrlInput}
          on:keydown={(e) => { if (e.key === 'Enter') startExtraction(); }}
        />

        {#if detectedType}
          <div class="inline-detected-chip">
            <span class="chip-pulse"></span>
            <span>{detectedType.replace('fitgirl_', '').replace('_', ' ').toUpperCase()}</span>
          </div>
        {/if}
      </div>

      <button 
        type="button" 
        class="btn-primary btn-resolve"
        disabled={isRunning}
        on:click={() => startExtraction()}
      >
        <Icon name="bolt" size={16} color="#ffffff" strokeWidth={2.5} />
        <span>{isRunning ? 'Resolving Parts...' : 'Extract & Resolve'}</span>
      </button>
    </header>

    <!-- Active Screen Body -->
    <main class="active-screen-body">
      {#if currentView === 'stage'}
        <!-- Rebuilt when the tour starts or ends, so the sample never mixes with the real game. -->
        {#key !!tourSample}
          {#if tourSample}
            <GameStage
              demo
              gameTitle={tourSample.title}
              coverUrl={tourSample.coverUrl}
              totalSizeStr={tourSample.totalSizeStr}
              statusMessage={$say('tour.sampleStatus')}
              parts={tourSample.parts}
              logs={tourSample.logs}
            />
          {:else}
            <GameStage
              {gameTitle}
              {coverUrl}
              {sourceUrl}
              {totalSizeStr}
              {isRunning}
              {statusMessage}
              {parts}
              {logs}
              onPushJd2={handlePushToJd2}
              onExport={handleExport}
              onCopyAll={handleCopyAll}
              onCancel={handleCancelExtraction}
            />
          {/if}
        {/key}
      {:else}
        <DiscoveryHub 
          games={communityGames}
          isLoading={isCommunityLoading}
          onLoadRecord={handleLoadCommunityRecord}
          onReextract={handleReextractGame}
          isOffline={isCommunityOffline}
          onPushJd2={handlePushCommunityGameToJd2}
          onGrab={(rec) => countGrab(rec.slug)}
          onRefresh={() => refreshCommunity(true)}
        />
      {/if}
    </main>
  </div>

  <!-- Global Toast Notification -->
  {#if toastMessage}
    <div class="app-toast glass-panel" use:liquidGlass={{ style: 'clear', bezel: 12, strength: 14 }}>
      <Icon name="sparkles" size={16} color="var(--accent-primary)" />
      <span>{toastMessage}</span>
    </div>
  {/if}

  <!-- Background Clipboard Sentinel -->
  <ClipboardSentinel onResolveUrl={(url) => { inputUrl = url; startExtraction(url); }} />

  <!-- Modals -->
  <CacheConflictModal
    isOpen={conflictModalOpen}
    record={conflictRecord}
    onSelectInstant={handleSelectInstantConflict}
    onSelectFresh={handleSelectFreshConflict}
    onClose={handleCloseConflictModal}
  />

  <HistoryModal 
    isOpen={historyOpen}
    onClose={() => historyOpen = false}
    onLoadHistoryItem={handleLoadHistoryRecord}
    onPushJd2={pushUrlsToJd2}
  />

  <SettingsModal 
    isOpen={settingsOpen}
    onClose={() => settingsOpen = false}
    onThemeChange={(t) => currentTheme = t}
    onCheckUpdates={handleManualCheckUpdates}
    onOpenTour={startTour}
    onOpenIssueCenter={() => { reportModalOpen = true; }}
    currentVersion={appCurrentVersion}
  />

  <UpdateModal
    isOpen={updateModalOpen}
    releaseInfo={updateReleaseInfo}
    isFrozen={isFrozenApp}
    currentVersion={appCurrentVersion}
    isFirstRun={isFirstRunOfVersion}
    onClose={handleCloseUpdateModal}
    onStartTour={handleStartTourFromUpdate}
    onShowToast={showToast}
  />

  <OnboardingTour
    isOpen={tourOpen}
    onClose={endTour}
    onView={(view) => { currentView = view; }}
  />

  <ReportIssueModal
    isOpen={reportModalOpen}
    onClose={() => reportModalOpen = false}
    onShowToast={showToast}
    engineLogs={logs}
  />

  {#if bootPhase === 'loading' || bootPhase === 'exiting'}
    <SplashLoader
      progress={bootProgress}
      status={bootStatus}
      exiting={bootPhase === 'exiting'}
      onFinished={handleSplashFinished}
    />
  {/if}
</div>

<style>
  .app-layout-root {
    position: relative;
    width: 100vw;
    height: 100vh;
    display: flex;
    overflow: hidden;
    background: var(--bg-base);
  }

  /* Sidebar: the shared Liquid Glass material from glass.css. The bubble over the selected
     item comes from utils/glassBubble.ts and lives outside the sidebar so it can see through it. */
  .left-sidebar {
    position: relative;
    z-index: 100;
    width: 72px;
    height: calc(100vh - 24px);
    margin: 12px 0 12px 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    padding: 18px 0;
    border-radius: 24px;
    flex-shrink: 0;
    box-shadow: var(--glass-shadow), 0 0 30px -8px var(--accent-glow);
  }

  /* Above the glass's rim and pointer highlight. */
  .sidebar-logo-btn,
  .sidebar-nav,
  .sidebar-footer {
    position: relative;
    z-index: 4;
  }

  .sidebar-logo-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 0;
  }

  .logo-mark {
    width: 40px;
    height: 40px;
    filter: drop-shadow(0 0 10px var(--accent-glow));
    transition: transform 0.35s var(--glass-spring), filter 0.2s ease;
  }

  .sidebar-logo-btn:hover .logo-mark {
    transform: scale(1.08);
    filter: drop-shadow(0 0 14px var(--accent-glow)) brightness(1.12);
  }

  .sidebar-nav {
    display: flex;
    flex-direction: column;
    gap: 16px;
    align-items: center;
    touch-action: none;
  }

  .sidebar-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    transition: color 0.25s ease;
  }

  .sidebar-item:hover:not(.active) {
    color: var(--text-primary);
  }

  .tab-content-zoom {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
  }

  .sidebar-item.active {
    color: #ffffff;
  }

  /* Keeps the label crisp over the bubble's tint. */
  .sidebar-item.active .tab-content-zoom {
    filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.45));
  }

  .nav-label {
    font-family: var(--font-display);
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .sidebar-footer {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }

  .sidebar-icon-btn {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: color 0.2s ease, background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  }

  /* A small piece of glass catches the light under the pointer. */
  .sidebar-icon-btn:hover {
    color: var(--text-primary);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.04));
    border-color: rgba(255, 255, 255, 0.1);
    box-shadow: var(--glass-chip-highlight);
  }

  .sidebar-icon-btn.update-btn {
    position: relative;
  }

  .sidebar-icon-btn.update-btn.has-update {
    color: var(--accent-primary);
  }

  .sidebar-icon-btn.update-btn:hover {
    color: var(--accent-primary);
  }

  .sidebar-icon-btn.tour-trigger-btn:hover {
    color: var(--accent-secondary);
    background: rgba(6, 182, 212, 0.12);
    border-color: rgba(6, 182, 212, 0.3);
  }

  .sidebar-icon-btn.issue-trigger-btn:hover {
    color: #f43f5e;
    background: rgba(244, 63, 94, 0.12);
    border-color: rgba(244, 63, 94, 0.3);
  }

  .update-pulse-dot {
    position: absolute;
    top: 5px;
    right: 5px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #f59e0b;
    box-shadow: 0 0 10px #f59e0b, 0 0 16px rgba(245, 158, 11, 0.6);
    animation: pulseDot 1.8s infinite;
  }

  @keyframes pulseDot {
    0%, 100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.35);
      opacity: 0.6;
    }
  }

  /* Main Viewport: content runs the full height and scrolls beneath the floating bars. */
  .main-viewport {
    --deck-offset: 86px;
    position: relative;
    z-index: 10;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    height: 100vh;
    overflow: hidden;
  }

  /* Top Command Deck */
  .top-command-deck {
    position: absolute;
    top: 12px;
    left: 14px;
    right: 16px;
    z-index: 30;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-radius: 18px;
  }

  .input-field-container {
    position: relative;
    flex: 1;
    display: flex;
    align-items: center;
    background: rgba(3, 5, 9, 0.34);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 11px;
    padding: 0 12px;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.4), inset 0 -1px 0 rgba(255, 255, 255, 0.05);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .input-field-container:focus-within {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 2px var(--accent-glow);
  }

  .input-leading-icon {
    display: flex;
    align-items: center;
    margin-right: 10px;
  }

  .url-input-box {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: 13px;
    padding: 10px 0;
  }

  .url-input-box::placeholder {
    color: var(--text-muted);
    font-family: var(--font-body);
    font-size: 12px;
  }

  /* Clean Inline Chip (No Text Overlap) */
  .inline-detected-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px;
    border-radius: 6px;
    background: rgba(6, 182, 212, 0.15);
    border: 1px solid rgba(6, 182, 212, 0.35);
    color: var(--accent-secondary);
    font-family: var(--font-display);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
    margin-left: 8px;
    flex-shrink: 0;
  }

  .chip-pulse {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-secondary);
    box-shadow: 0 0 6px var(--accent-secondary);
  }

  .btn-resolve {
    position: relative;
    overflow: hidden;
    flex-shrink: 0;
    padding: 10px 20px;
    font-family: var(--font-display);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.15s ease;
  }

  .btn-resolve::after {
    content: '';
    position: absolute;
    top: -50%;
    left: -60%;
    width: 40%;
    height: 200%;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(255, 255, 255, 0.4),
      transparent
    );
    transform: rotate(25deg);
    animation: btnSheen 4.5s infinite ease-in-out;
    pointer-events: none;
  }

  @keyframes btnSheen {
    0%, 75% {
      left: -60%;
    }
    100% {
      left: 140%;
    }
  }

  .btn-resolve:active,
  .sidebar-item:active,
  .sidebar-icon-btn:active {
    transform: scale(0.96);
  }

  /* Active Screen Body */
  .active-screen-body {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    display: flex;
    padding: 0 10px 0 14px;
  }

  /* Toast */
  .app-toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 99999;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    box-shadow: var(--glass-shadow-lg);
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
