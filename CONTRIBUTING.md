# Contributing to FitGirl Direct Link Extractor

Thank you for your interest in contributing to **FitGirl Direct Link Extractor**. Whether you are optimizing concurrency, adding support for new mirror hosts, enhancing the Material 3 UI, or improving integration exporters, your contributions are welcome.

---

## 1. Code of Conduct & Ground Rules

1. **Non-Commercial License Compliance**: This project is licensed under **PolyForm Noncommercial 1.0.0** and **Creative Commons BY-NC-SA 4.0**. All contributions must remain strictly non-commercial. No monetization hooks, paywalls, adware, or telemetry trackers are permitted.
2. **Author Attribution**: Maintain author credit (**Vikash / @vik05h**) across all legal notices, code headers, and UI dialogs.
3. **No Malicious Payloads**: All scrapers, resolvers, and automation logic must strictly perform legitimate HTTP requests and browser automation.
4. **Persistent App Data Safety**: Never write persistent databases, configuration files, or logs to `__file__` or local directories in production. Always utilize `get_app_data_dir()` (`%APPDATA%\FitGirlLinkExtractor\` on Windows) to prevent data loss during PyInstaller `%TEMP%` cleanup on application exit.
5. **Dynamic Export Paths**: Never hardcode user file paths (such as `C:\Users\...`). Always use `get_export_dir()` and `open_folder_cross_platform()`.
6. **Cancellation Integrity**: Aborted extractions must cleanly release browser context resources and must never create corrupted or partial records in the SQLite database (`history.db`).
7. **Clean Typography**: Maintain clean, professional markdown typography without emojis across all project documentation.

---

## 2. Local Development Setup

### Prerequisites
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
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

# 3. Install core dependencies
pip install flet playwright pyperclip requests beautifulsoup4 lxml pyinstaller pillow

# 4. Install Playwright browser engine
playwright install chromium
```

### Running the Application

```bash
# Launch the desktop application
python main.py
```

---

## 3. Architecture & Codebase Layout

The project follows a modular architecture separating the Material 3 UI, the asynchronous Playwright engine, HTTP validators, local persistence, and external tool integrations:

```
Link-Extractor/
|-- main.py                    # Entrypoint: window initialization, navigation rail, animated switcher (< 150 lines)
|-- utils.py                   # Persistent path resolution, settings I/O, Win32 native icon binding
|-- engine.py                  # Playwright multi-tab pool, Cloudflare Turnstile bypass, retry engine
|-- scraper.py                 # FitGirl game page & pastebin parsing, URL categorization
|-- validator.py               # Concurrent 1-byte HTTP Range GET link verification & size aggregation
|-- history.py                 # SQLite local storage (history.db) with parameterized queries
|-- integrations.py            # JDownloader 2 FlashGot HTTP API (port 9666) & multi-format file exporters
|-- updater.py                 # GitHub Releases API auto-update checker with semantic versioning
|-- make_icon.py               # Multi-resolution icon and asset generator
|-- LinkExtractor_Single.spec  # PyInstaller single-file build specification
|-- file_version_info.txt      # Windows executable metadata and version definition
|-- assets/                    # Application icons, logos, and branding graphics
|-- ui/                        # Modular Material 3 UI package
    |-- constants.py           # Theme palettes, logo presets, and animation configurations
    |-- state.py               # AppState and UIContext runtime state containers
    |-- screens/
        |-- extractor.py       # Input field, URL detection badge, live progress, and stats cards
        |-- pipeline.py        # Real-time streaming logs and multi-tab status terminal
        |-- history.py         # Searchable SQLite history archive with batch operations
        |-- settings.py        # Concurrency slider, port configuration, and theme selectors
```

### Module Responsibilities

| Module | Responsibility | Key Constraints |
| :--- | :--- | :--- |
| `main.py` | Window bootstrapping, NavigationRail layout, and screen switcher wiring. | Keep modular and minimal (< 150 lines); delegate screen layout to `ui/`. |
| `utils.py` | Path resolution (`get_app_data_dir`, `get_export_dir`), settings I/O, Win32 icon binding. | Always handle frozen vs non-frozen environments safely. |
| `ui/` | Modular UI package containing presets, state models, and screens. | Never mutate state directly without `AppState` and `UIContext`. |
| `engine.py` | Playwright multi-tab worker pool and Cloudflare Turnstile solver. | Share a single browser context across tabs; respect cancellation events immediately. |
| `scraper.py` | URL pattern classification, game title extraction, and pastebin parsing. | Defensive HTML parsing with fallback mechanisms for missing mirrors. |
| `validator.py` | 1-byte HTTP Range validation and total repack size computation. | Sanitize filenames extracted from `Content-Disposition` headers. |
| `history.py` | Persistent SQLite archive (`history.db`). | Use 100% parameterized SQL queries (`?`); never record aborted jobs. |
| `integrations.py` | JDownloader 2 FlashGot API and `.txt`, `.json`, `.crawljob` exports. | Always append `#filename.rar` fragments to prevent JD2 Deep Link Analysis. |
| `updater.py` | GitHub Releases API update checker. | Use normalized 3-part version tuples for accurate semver comparisons. |

---

## 4. Coding Standards & Technical Guidelines

### UI and Flet Controls
- **Adaptive Scrolling**: Always set `scroll=ft.ScrollMode.ADAPTIVE` on outer scrollable columns to ensure proper layout scaling on smaller screens.
- **Control Update Lifecycle**: Never invoke `.update()` directly on unmounted or detached child controls from background threads. Call `page.update()` or verify mounting state.
- **AnimatedSwitcher Hot-Swapping**: Flutter locks `AnimatedSwitcher` duration at `initState()`. To dynamically update transitions, wrap in a container and rebuild the switcher control.

### Integration with JDownloader 2
- When generating direct URLs for JDownloader 2 (via FlashGot API or `.crawljob`), always append `#filename.rar` anchors (e.g., `https://dl.fuckingfast.co/...#setup.rar`). This prevents JDownloader 2 from prompting the user with "Deep Link Analysis".

### Security & Sanitization
- **SQL Queries**: Every SQLite query in `history.py` must use parameterized placeholders (`?`). Never interpolate variables into SQL strings.
- **Path Traversal**: Filenames extracted from web headers or game titles must be sanitized with `re.sub(r'[^a-zA-Z0-9_.-]', '_', name)`.
- **SSRF Prevention**: Restrict HTTP validation requests to known host domains and standard HTTP/HTTPS schemes.

---

## 5. Testing & Verification

Before submitting changes, execute the following validation steps:

### 1. Syntax & Import Verification
Validate that all modules and UI screens import cleanly without syntax or dependency errors:

```bash
python -c "import main, engine, scraper, validator, history, integrations, updater, utils; from ui import constants, state; from ui.screens import extractor, pipeline, history as hist_screen, settings; print('All modules OK')"
```

### 2. Manual Workflow Checklist
- **URL Auto-Detection**: Test with FitGirl game pages, pastebin links, and raw hoster links. Verify that badge indicators update accurately.
- **Parallel Resolution**: Verify that multi-tab workers resolve parts concurrently and stream progress without deadlocking.
- **Cancellation**: Click **Cancel** during an active multi-tab extraction. Confirm that browser tabs close immediately and no partial records are written to history.
- **1-Byte Range Validation**: Verify that total repack sizes and individual file sizes calculate correctly.
- **JDownloader 2 Push**: Verify that pushing links to `localhost:9666` sends the package to JDownloader 2 LinkGrabber without captcha prompts.
- **File Exports**: Export `.txt`, `.json`, and `.crawljob` files. Confirm they write to the user's Downloads folder.
- **SQLite History**: Confirm that completed extractions appear in the **History** tab, are searchable, and persist across application restarts.

### 3. Executable Packaging Verification
Test that the standalone executable builds and runs properly:

```powershell
# Kill any running instances
Get-Process -Name LinkExtractor, flet, main -ErrorAction SilentlyContinue | Stop-Process -Force

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
   - `feat: add support for DataNodes direct resolver`
   - `fix: resolve race condition in worker pool cancellation`
   - `perf: optimize 1-byte range HTTP header parsing`
   - `refactor: extract reusable card components in ui/screens`
   - `docs: update setup instructions in CONTRIBUTING.md`
3. **Keep PRs Focused**: Submit discrete pull requests for specific features or bug fixes rather than large monolithic changes.
4. **Include Verification Details**: Document your testing steps and include before/after screenshots for any UI modifications.

---

## 7. Reporting Issues & Seeking Help

If you encounter bugs, have questions, or want to propose a new feature, please open an issue on GitHub:
- Issue Tracker: [https://github.com/vik05h/Link-Extractor/issues](https://github.com/vik05h/Link-Extractor/issues)
- Author Profile: [@vik05h](https://github.com/vik05h)
