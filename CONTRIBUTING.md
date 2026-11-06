# Contributing to FitGirl Direct Link Extractor

Thank you for your interest in contributing to **FitGirl Direct Link Extractor**. Whether you are optimizing concurrency, enhancing the web UI, or improving integration exporters, your contributions are welcome.

---

## 1. Code of Conduct & Ground Rules

1. **Non-Commercial License Compliance**: This project is licensed under **PolyForm Noncommercial 1.0.0** and **Creative Commons BY-NC-SA 4.0**. All contributions must remain strictly non-commercial. No monetization hooks, paywalls, adware, or third-party trackers are permitted. The app's only telemetry is its own opt-out crash report and an anonymous presence heartbeat; do not add more.
2. **Author Attribution**: Maintain author credit (**Vikash / @vik05h**) across all legal notices, code headers, and UI dialogs.
3. **No Malicious Payloads**: All scrapers, resolvers, and automation logic must strictly perform legitimate HTTP requests and browser automation.
4. **Persistent App Data Safety**: Never write persistent databases, configuration files, or logs to `__file__` or local directories in production. Always utilize `get_app_data_dir()` (`%APPDATA%\FitGirlLinkExtractor\` on Windows) to prevent data loss during PyInstaller `%TEMP%` cleanup on application exit.
5. **Dynamic Export Paths**: Never hardcode user file paths (such as `C:\Users\...`). Always use `get_export_dir()` and `open_folder_cross_platform()`.
6. **Cancellation Integrity**: Aborted extractions must cleanly release browser context resources and must never create corrupted or partial records in the SQLite database (`history.db`).
7. **Clean Typography**: Maintain clean, professional markdown typography without emojis across all project documentation.

---

## 2. Local Development Setup

### Prerequisites
- **Python 3.12+** (releases are built with Python 3.14)
- **Node.js 18+** (22.18+ to run `npm test`, which uses Node's built-in TypeScript support)
- **Git**
- **Chromium / Google Chrome / Microsoft Edge**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/vik05h/Link-Extractor.git
cd Link-Extractor

# 2. Create and activate a virtual environment
# Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1

# Windows (cmd):
python -m venv .venv
.venv\Scripts\activate.bat

# Linux/macOS:
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies, including the test and build tools
pip install -r requirements-dev.txt

# 4. Install Playwright browser engine
playwright install chromium

# 5. Build the web frontend
cd frontend
npm install
npm run build
cd ..
```

### Running the Application

```bash
# Launch the desktop application
python main.py
```

---

## 3. Architecture & Codebase Layout

The project follows a modular architecture separating the hardware-accelerated Astro/Svelte web UI, high-speed Python RPC bridge, asynchronous Playwright engine, HTTP validators, local persistence, and external tool integrations:

```
Link-Extractor/
|-- main.py                    # Entrypoint: WebView2 window and bridge binding (< 100 lines)
|-- bridge.py                  # RPC adapter between the web frontend and the modules below
|-- pipeline.py                # Extraction pipeline and the rule for what a finished run may do
|-- engine.py                  # Playwright multi-tab pool, Cloudflare Turnstile bypass, retry engine
|-- scraper.py                 # FitGirl game page and pastebin parsing, artwork cascade
|-- validator.py               # Concurrent 1-byte HTTP Range link checks and size totals
|-- history.py                 # SQLite local storage (history.db) with parameterized queries
|-- community.py               # Community Cloud Cache: feed, links, publishing, presence
|-- issues.py                  # Community Issue Center: reports, votes, comments, moderation
|-- telemetry.py               # Opt-out crash reports with personal data removed
|-- firebase_client.py         # Zero-SDK Firebase REST client
|-- links.py                   # Which links are trusted, by exact hostname
|-- game_records.py            # Game identity, freshness, cleaning of shared records
|-- integrations.py            # JDownloader 2 FlashGot HTTP API (port 9666) and file exporters
|-- updater.py                 # GitHub Releases update check and verified installer
|-- palette.py                 # Ambient colors from cover art
|-- utils.py                   # Paths, settings I/O, logging, Win32 icon binding
|-- version.py                 # The app version (change it with scripts/set_version.py)
|-- firebase/                  # Database rules and setup guide
|-- tests/                     # pytest suite, offline, with a local Firebase stand-in
|-- dist_web/                  # Compiled production web bundle loaded by pywebview
|-- frontend/                  # Astro 5 + Svelte 5 + Web Audio frontend
|   |-- src/components/        # LivingCanvas, DefragMosaic, DiscoveryHub, GameStage, UpdateModal
|   |-- src/styles/global.css  # Dark cyberpunk & adaptive theming system
|   |-- src/styles/glass.css   # The Liquid Glass material
|   |-- src/utils/             # Startup, the glass action, bridge helpers
|   |-- tests/                 # Logic tests (npm test)
|-- LinkExtractor_Single.spec  # PyInstaller single-file build specification
|-- file_version_info.txt      # Windows executable metadata and version definition
|-- assets/                    # Application icons, logos, and branding graphics
```

### Module Responsibilities

| Module | Responsibility | Key Constraints |
| :--- | :--- | :--- |
| `main.py` | Window bootstrapping, pywebview initialization, and bridge binding. | Keep modular and minimal (< 100 lines); delegate state to `bridge.py`. |
| `bridge.py` | RPC API endpoints and event dispatching. | An adapter only: decisions live in the modules. Use private attributes (`self._window`) to prevent COM recursion during JS reflection. |
| `pipeline.py` | Runs one extraction and decides what happens to the result. | The one place that decides what is saved and published. Reaches the browser and network only through `PipelinePorts`. |
| `frontend/` | Svelte components and modern CSS design system. | Zero emojis, responsive layout, and build to `dist_web/`. |
| `utils.py` | Path resolution, settings I/O, logging, Win32 icon binding. | Always handle frozen vs non-frozen environments safely. |
| `engine.py` | Playwright multi-tab worker pool and Cloudflare Turnstile solver. | Share a single browser context across tabs; respect cancellation events immediately. |
| `scraper.py` | URL classification, game title extraction, and pastebin parsing. | Judge links by exact hostname through `links.py`. |
| `links.py` | Which links are trusted. | Every link from the database, the clipboard, or a web page passes through here. |
| `game_records.py` | One definition of the same game and of expired, and cleaning of shared records. | Pure functions only. |
| `validator.py` | 1-byte HTTP Range checks and total size. | Keep the three verdicts apart: alive, dead, unknown. Sanitize filenames from `Content-Disposition`. |
| `history.py` | Persistent SQLite archive (`history.db`). | Use 100% parameterized SQL queries (`?`); never record cancelled runs. |
| `community.py` | Community Cloud Cache client. | Clients add and update game records and leave deleting to the admin. |
| `issues.py` | Community Issue Center. | The server decides admin rights through `firebase/database.rules.json`. |
| `firebase_client.py` | Firebase REST calls. | Zero-SDK, standard `urllib`/`json`. Failures raise `FirebaseError`. |
| `telemetry.py` | Crash reports. | All crash reports go through `report_crash_log`, which applies the opt-out and cleaning. |
| `integrations.py` | JDownloader 2 FlashGot API and `.txt`, `.json`, `.crawljob` exports. | Always append `#filename.rar` fragments to prevent JD2 Deep Link Analysis. |
| `updater.py` | GitHub Releases update checker and installer. | Install only files that pass the source, size, SHA-256, and file type checks. |

---

## 4. Coding Standards & Technical Guidelines

### Frontend and WebView2 Bridge
- **Asynchronous IPC**: All UI interactions trigger asynchronous methods on `window.pywebview.api`. Never block the UI thread.
- **Dynamic Asset Rebuilding**: Always execute `npm run build` inside `frontend/` after modifying Svelte components to synchronize `dist_web/`.
- **Zero Emojis**: Maintain professional typography across all UI labels and notifications. Use SVG `<Icon />` components.
- **Liquid Glass**: Surfaces use `.glass-panel` from `styles/glass.css`. Add `use:liquidGlass` to floating surfaces that have content moving behind them. An ancestor with `backdrop-filter`, `filter`, `mask`, or opacity below 1 stops a surface seeing the page, so dim a dialog's scrim with a background color and leave its opacity alone.

### Integration with JDownloader 2
- When generating direct URLs for JDownloader 2 (via FlashGot API or `.crawljob`), always append `#filename.rar` anchors (e.g., `https://dl.fuckingfast.co/...#setup.rar`). This prevents JDownloader 2 from prompting the user with "Deep Link Analysis".

### Security & Sanitization
- **SQL Queries**: Every SQLite query in `history.py` must use parameterized placeholders (`?`). Never interpolate variables into SQL strings.
- **Path Traversal**: Filenames extracted from web headers or game titles must be sanitized with `re.sub(r'[^a-zA-Z0-9_.-]', '_', name)`.
- **SSRF Prevention**: Fetch only links that pass `links.py`.
- **Database Rules**: Anything the app sends to Firebase must also pass `firebase/database.rules.json`, which protects every installed copy. See [firebase/README.md](firebase/README.md).

---

## 5. Testing & Verification

Before submitting changes, execute the following validation steps:

### 1. Automated Checks
These run offline and never touch the live database. CI runs them on every push.

```bash
python -m pytest
ruff check .
pyright
cd frontend && npm run check && npm test
```

### 2. Manual Workflow Checklist
- **URL Auto-Detection**: Test with FitGirl game pages, pastebin links, and raw hoster links. Verify that badge indicators update accurately.
- **Parallel Resolution**: Verify that multi-tab workers resolve parts concurrently and stream progress without deadlocking.
- **Cancellation**: Click **Cancel** during an active multi-tab extraction. Confirm that browser tabs close immediately, nothing is written to history, and nothing is published.
- **1-Byte Range Validation**: Verify that total repack sizes and individual file sizes calculate correctly.
- **JDownloader 2 Push**: Verify that pushing links to `localhost:9666` sends the package to JDownloader 2 LinkGrabber without captcha prompts.
- **File Exports**: Export `.txt`, `.json`, and `.crawljob` files. Confirm they write to the user's Downloads folder.
- **SQLite History**: Confirm that completed extractions appear in the **History** tab, are searchable, and persist across application restarts.

### 3. Executable Packaging Verification
Test that the standalone executable builds and runs properly:

```powershell
# Kill any running instances
Get-Process -Name LinkExtractor, main -ErrorAction SilentlyContinue | Stop-Process -Force

# Build standalone single-file binary
pyinstaller LinkExtractor_Single.spec --noconfirm
```

Verify that `dist/LinkExtractor.exe` launches cleanly and retains custom window icons and theme settings.

---

## 6. Pull Request Process

1. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Follow Conventional Commits**:
   - `feat: add failed-part count to extraction summary`
   - `fix: resolve race condition in worker pool cancellation`
   - `perf: optimize 1-byte range HTTP header parsing`
   - `refactor: extract reusable card components in frontend/src/components`
   - `docs: update setup instructions in CONTRIBUTING.md`
3. **Keep PRs Focused**: Submit discrete pull requests for specific features or bug fixes rather than large monolithic changes.
4. **Include Verification Details**: Document your testing steps and include before/after screenshots for any UI modifications.

---

## 7. Releasing

1. Run `python scripts/set_version.py X.Y.Z`.
2. Add a matching entry to `VERSION_CHANGELOGS` in `updater.py`.
3. Run the automated checks, then build the executable.
4. Create the GitHub release and attach `LinkExtractor.exe`. The in-app updater verifies it against the SHA-256 that GitHub publishes for the file.

---

## 8. Reporting Issues & Seeking Help

If you encounter bugs, have questions, or want to propose a new feature, please open an issue on GitHub:
- Issue Tracker: [https://github.com/vik05h/Link-Extractor/issues](https://github.com/vik05h/Link-Extractor/issues)
- Author Profile: [@vik05h](https://github.com/vik05h)
