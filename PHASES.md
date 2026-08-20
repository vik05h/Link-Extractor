# FitGirl Link Extractor — Development Phases & Roadmap

This document tracks current milestones, active implementation status, and upcoming phases for the FitGirl Link Extractor project.

---

## Status Dashboard

| Phase | Description | Status | Target Version |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Speed & Reliability Core** | **Completed** | `v3.0.0` |
| **Phase 2** | **Material 3 UI/UX & Advanced Integrations** | **Completed** | `v3.1.0` |
| **Phase 3** | **Community Cloud Cache & Shared Link Hub (Firebase)** | **Design Finalized / Ready** | `v3.2.0` |
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
- [x] **2.5 GitHub Releases Auto-Update Checker**
  - [x] `updater.py`: Live query to GitHub Releases API with semver comparison and changelog dialog.

---

## Phase 3: Community Cloud Cache & Shared Link Hub (v3.2.0) — DESIGN SPECIFICATION

**Goal:** Provide an instant community link cache powered by Firebase Realtime Database (free tier), allowing users to skip browser automation completely when fresh links (<24-36h) already exist for a game.

- [ ] **3.1 Firebase Realtime Database Architecture (Lightweight REST API)**
  - [ ] Zero-SDK lightweight integration via Python standard `urllib` / `httpx` (no heavy Google Cloud dependencies).
  - [ ] **Split Storage Schema**:
    - Metadata Node: `/games_meta/{slug}` (stores `title`, `source_url`, `timestamp`, `total_parts`, `total_size_str`, `active_status`) — minimal bandwidth.
    - Payload Node: `/games_urls/{slug}` (stores `urls: []`) — fetched on-demand only when imported or pushed.
- [ ] **3.2 Security, Moderation & Anti-Spam**
  - [ ] Strict client & server-side regex validation: all links must match `^https://dl\.fuckingfast\.co/dl/[a-zA-Z0-9_-]+`.
  - [ ] Repack validation requirement: part count must match pastebin parts count and pass 1-byte validation before upload.
  - [ ] Overwrite Protection: New upload can only overwrite an existing game record if the new extraction timestamp is strictly newer.
- [ ] **3.3 Expiration Tracking & 1-Click Health Check**
  - [ ] Visual link age indicators on game cards:
    - **Fresh** (< 12 hours old)
    - **Aging** (12–36 hours old)
    - **Likely Expired** (> 36 hours old)
  - [ ] Fast 1-Click Health Check: Rapid 1-byte Range GET on Part 1; if expired, offers 1-click local re-resolve and auto-refreshes the cloud cache.
- [ ] **3.4 UI Integration: Community Hub Tab**
  - [ ] New **Community Hub** destination in the left Navigation Rail.
  - [ ] Search bar with live title filtering, game cards with part counts, sizes, age badges, and 1-click `Push JD2` / `Copy` buttons.
- [ ] **3.5 Extractor Screen Integration & User Privacy**
  - [ ] When entering a URL on the Extractor screen, auto-check Firebase for active links.
  - [ ] If found: Display banner *"Found active links resolved X hours ago in Community Hub! [Use Instant Links] [Resolve Fresh]"*.
  - [ ] 100% anonymous sharing with global toggle in Settings & Tweaks: `[x] Auto-share resolved links to Community Hub` and checkbox on Extractor view.

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
*Last Updated: 2026-08-20*
