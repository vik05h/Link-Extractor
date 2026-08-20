# 🚀 FitGirl Link Extractor — Development Phases & Roadmap

This document tracks current milestones, active implementation status, and upcoming phases for the FitGirl Link Extractor project.

---

## 📌 Status Dashboard

| Phase | Description | Status | Target Version |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Speed & Reliability Core** | 🟢 **Completed** | `v3.0.0` |
| **Phase 2** | **Material 3 UI/UX & Advanced Integrations** | 🟢 **Completed** | `v3.1.0` |
| **Phase 3** | **Multi-Hoster & Universal Automation** | ⚪ Planned | `v3.2.0` |

---

## 🟢 Phase 1: Speed & Reliability Core (v3.0.0) — COMPLETED

**Goal:** Deliver 3-4x faster extraction through concurrent browser workers, zero dropped links via automated retry loops, and direct game page link extraction.

- [x] **1.1 Modular Architecture Refactor**
  - [x] `scraper.py`: Dedicated parser for FitGirl Game Pages, Pastebin pages, and direct URLs with `urllib.parse` detection.
  - [x] `engine.py`: High-performance Playwright multi-tab worker pool, Cloudflare Turnstile solver, and lifecycle management.
  - [x] `main.py`: Sleek CustomTkinter UI shell with clean separation of concerns.
- [x] **1.2 High-Speed Concurrent Tab Pool (3-4x Speedup)**
  - [x] Multi-tab worker management inside a single browser context to avoid memory bloat.
  - [x] Concurrent Turnstile bypass and asynchronous response header interception (`HX-Redirect` / `Location`).
  - [x] Benchmark: 6 parts resolved in ~11 seconds (~1.8s/part average vs 5-8s previously).
- [x] **1.3 Automated Retry Engine**
  - [x] Automatic re-queueing of dropped/timed-out links (up to 2 retry passes).
  - [x] Smart jitter delay between retries to prevent anti-bot detection.
- [x] **1.4 Direct FitGirl Game Page Support**
  - [x] Detect `fitgirl-repacks.site/<game-slug>/` URLs.
  - [x] Auto-locate and parse FuckingFast pastebin mirror links without manual user navigation.
- [x] **1.5 Enhanced GUI & Real-Time Stats**
  - [x] Live ETA calculation and speed metrics (e.g. `⚡ 1.8s/part | ⏱️ ETA: ~12s | 🌐 3 tabs active`).
  - [x] Input URL type auto-detection badge (🎮 Game Page / 📋 Pastebin / ⚡ Direct).
  - [x] Dynamic tab badge counter and retry progress indicator.
  - [x] Updated PyInstaller spec files with `scraper` and `engine` bundled.

---

## 🟢 Phase 2: Material 3 UI/UX & Advanced Integrations (v3.1.0) — COMPLETED

**Goal:** Material 3 design overhaul with Navigation Rail, JDownloader 2 one-click push, async link validation, and SQLite history archive.

- [x] **2.1 Material 3 (M3) Design System & Navigation Rail**
  - [x] Expressive Violet & Indigo Dark theme tokens in `theme_m3.py` (`#141218` Surface, `#D0BCFF` Primary, `#4F378B` Container, `#4ADE80` Tertiary).
  - [x] Left M3 Navigation Rail with 3 screens: ⚡ **Extractor**, 📚 **History & Archive**, ⚙️ **Settings & Tweaks**.
  - [x] M3 Segmented button controls, pill badges, and elevated tonal cards.
- [x] **2.2 Live Link Validation & Total Size Calculation**
  - [x] Rapid concurrent `HTTP HEAD` verification in `validator.py` with 12 parallel workers.
  - [x] `Content-Length` aggregation and total repack size calculation (e.g. `94.20 GB across 195 parts`).
- [x] **2.3 SQLite History Archive & Saved Downloads**
  - [x] Local SQLite database (`history.db`) in `history.py` with instant search.
  - [x] 1-click re-copy, re-push to JDownloader 2, and single-record deletion.
- [x] **2.4 JDownloader 2 Direct One-Click Push**
  - [x] Local Click'n'Load (CNL2 / FlashGot on port 9666) integration in `integrations.py`.
  - [x] One-click push straight into JDownloader 2 LinkGrabber.
- [x] **2.5 Extended Exporters & Preferences**
  - [x] Export to `.crawljob` (JDownloader watch folder), `.json`, and `.txt`.
  - [x] Dynamic settings: worker concurrency slider (1–6 tabs), Headless browser mode toggle, and auto-validation toggle.

---

## ⚪ Phase 3: Multi-Hoster & Universal Automation (v3.2.0)

**Goal:** Universal repack link extraction across all mirror providers.

- [ ] **3.1 Multi-Hoster Support**
  - [ ] DataNodes mirror extraction.
  - [ ] FileKeeper mirror extraction.
- [ ] **3.2 Selective Download Filter**
  - [ ] Option to filter out optional languages or bonus soundtracks before resolving.
- [ ] **3.3 CLI Mode**
  - [ ] Headless command-line interface for scripting and server environments (`python main.py --cli --url ...`).

---
*Last Updated: 2026-08-20*
