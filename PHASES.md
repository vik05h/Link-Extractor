# FitGirl Link Extractor — Development Phases & Roadmap

This document tracks current milestones, active implementation status, and upcoming phases for the FitGirl Link Extractor project.

---

## Status Dashboard

| Phase | Description | Status | Target Version |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Speed & Reliability Core** | **Completed** | `v3.0.0` |
| **Phase 2** | **Material 3 UI/UX & Advanced Integrations** | **Completed** | `v3.1.0` |
| **Phase 3** | **Community Cloud Cache & Shared Link Hub (Firebase)** | **Completed** | `v3.2.0` |
| **Phase 4** | **Multi-Hoster & Universal Automation** | Planned | `v3.3.0` |

---

## Phase 1: Speed & Reliability Core (v3.0.0) — COMPLETED

**Goal:** Deliver 3-4x faster extraction through concurrent browser workers, zero dropped links via automated retry loops, and direct game page link extraction.

- [x] **1.1 Modular Architecture Refactor**
  - [x] `scraper.py`: Dedicated parser for FitGirl Game Pages, Pastebin pages, and direct URLs with `urllib.parse` detection.
  - [x] `engine.py`: High-performance Playwright multi-tab worker pool, Cloudflare Turnstile solver, and lifecycle management.
  - [x] `main.py`: Sleek UI shell with clean separation of concerns.
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
  - [x] Live ETA calculation and speed metrics (e.g. `1.8s/part | ETA: ~12s | 3 tabs active`).
  - [x] Input URL type auto-detection badge (Game Page / Pastebin / Direct).
  - [x] Dynamic tab badge counter and retry progress indicator.
  - [x] Updated PyInstaller spec files with `scraper` and `engine` bundled.

---

## Phase 2: Material 3 UI/UX & Advanced Integrations (v3.1.0) — COMPLETED

**Goal:** Material 3 design overhaul with Navigation Rail, JDownloader 2 one-click push, async link validation, and SQLite history archive.

- [x] **2.1 Material 3 (M3) Design System & Navigation Rail**
  - [x] Full migration to Flet (Flutter engine for Python) with 60-120 FPS hardware acceleration.
  - [x] Left M3 Navigation Rail with 3 screens: **Extractor**, **History & Archive**, **Settings & Tweaks**.
  - [x] Live interactive DataTable with real-time row streaming and 1-click copy.
  - [x] Dynamic Theme color switcher with 5 Material 3 presets.
- [x] **2.2 Live Link Validation & Total Size Calculation**
  - [x] Rapid concurrent 1-byte Range GET verification in `validator.py`.
  - [x] Exact file size aggregation and Content-Disposition filename extraction.
- [x] **2.3 SQLite History Archive & Saved Downloads**
  - [x] Local SQLite database (`history.db`) in `history.py` with instant search.
  - [x] 1-click re-copy, re-push to JDownloader 2, and single-record deletion.
- [x] **2.4 JDownloader 2 Direct One-Click Push**
  - [x] Local Click'n'Load (CNL2 / FlashGot on port 9666) integration in `integrations.py`.
  - [x] Auto-formatting with `#filename.partXX.rar` anchors to prevent "Deep Link Analysis" prompts.
- [x] **2.5 GitHub Releases Auto-Updater & In-App Installer**
  - [x] `updater.py`: Live query to GitHub Releases API with semver comparison.
  - [x] Automated startup update checker with user approval prompt.
  - [x] In-app background download progress bar and detached Windows launcher (`apply_update.bat`) executable replacement.
  - [x] Post-update What's New & Bug Fixes popup dialog on updated version launch.

---

## Phase 3: Community Cloud Cache & Shared Link Hub (v3.2.0) — COMPLETED

**Goal:** Decentralized, high-speed Community Cloud Cache powered by Firebase Realtime Database (lightweight REST API), allowing users to skip browser automation completely when fresh links already exist for a game.

- [x] **3.1 Firebase Realtime Database Architecture (Lightweight REST API)**
  - [x] Zero-SDK lightweight integration via standard `urllib` / `json` in `community.py` (no heavy Google Cloud dependencies).
  - [x] **Split Storage Schema**:
    - Metadata Node: `/games_meta/{slug}` (stores `title`, `image_url`, `source_url`, `timestamp_utc`, `total_parts`, `total_size_str`, `total_size_bytes`, `uploader`, `app_version`).
    - Payload Node: `/games_urls/{slug}` (stores direct `urls: []` and `updated_at`).
- [x] **3.2 Security, Moderation & Anti-Spam**
  - [x] Strict regex and domain validation for all direct URLs matching `dl.fuckingfast.co/dl/...`.
  - [x] Strict overwrite protection: New uploads must have equal or newer extraction timestamps than existing records.
  - [x] Slug sanitization protecting against path traversal and database node pollution.
- [x] **3.3 Expiration Tracking & 1-Click Health Check**
  - [x] Local timezone intelligence: UTC timestamps converted to client timezone (e.g. `21 Aug 2026, 05:25 PM IST`).
  - [x] Visual link age badges on game cards:
    - **Fresh** (< 12 hours old)
    - **Aging** (12–36 hours old)
    - **Likely Expired** (> 36 hours old)
  - [x] Rapid 1-Click Health Check: 1-byte Range GET on Part 1 to determine live/expired status in under 1 second.
- [x] **3.4 UI Integration: Community Hub Tab & Pixel Dino Animation**
  - [x] Dedicated **Community** tab in the left Navigation Rail.
  - [x] Retro 8-bit arcade Pixel Dino running loading animation when loading/refreshing cloud feed.
  - [x] 3D-styled Game Cards with game cover art, depth lighting, part counts, sizes, local time badges, and 4 quick actions: `Use Instant`, `Push JD2`, `Copy URLs`, `Health Check`.
  - [x] Real-time title search and filter chips (`All`, `Fresh`, `Aging`, `Expired`).
- [x] **3.5 Extractor Screen Integration & User Privacy**
  - [x] Automatic Community cache lookup upon clicking `Extract & Resolve`.
  - [x] Interactive dialog presenting game cover, local time, and options to `Use Instant Links (Skip Browser)` or `Resolve Fresh & Update Cloud`.
  - [x] Background automated publishing to Community Cloud with global opt-out switch in Settings & Tweaks.

---

## Phase 4: Multi-Hoster & Universal Automation (v3.3.0)

**Goal:** Universal repack link extraction across all mirror providers.

- [ ] **4.1 Multi-Hoster Support**
  - [ ] DataNodes mirror extraction.
  - [ ] FileKeeper mirror extraction.
- [ ] **4.2 Selective Download Filter**
  - [ ] Option to filter out optional languages or bonus soundtracks before resolving.
- [ ] **4.3 CLI Mode**
  - [ ] Headless command-line interface for scripting and server environments (`python main.py --cli --url ...`).

---
*Last Updated: 2026-08-21*
