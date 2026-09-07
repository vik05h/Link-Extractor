# AGENTS.md — Agent Operating Instructions & Codebase Guide

This document defines repository standards, architectural boundaries, runtime constraints, and verification workflows for AI agents working in this codebase.

---

## 1. Core Directives & Hard Constraints

1. **Author Attribution**: Vikash (`@vik05h`) is the author and maintainer. Maintain attribution in all legal, header, and UI components.
2. **License Compliance**: Licensed under **PolyForm Noncommercial 1.0.0** and **CC BY-NC-SA 4.0**. Code must remain non-commercial with no paywalls or monetization hooks.
3. **Persistent App Data**: 
   - Never write runtime databases or settings to local directory or `__file__` path in production mode.
   - Always use `get_app_data_dir()`, which targets `%APPDATA%\FitGirlLinkExtractor\` when frozen (`getattr(sys, 'frozen', False)`). PyInstaller single-file binaries wipe `%TEMP%/_MEIxxxxxx` on exit.
4. **Dynamic Exports**: 
   - Never hardcode `C:\Users\...` paths.
   - Use `get_export_dir()` (`os.path.expanduser("~")/Downloads` with `%USERPROFILE%` fallback) and `open_folder_cross_platform()`.
5. **No Emojis in Documentation**: Maintain clean, professional markdown typography across documentation (`README.md`, `PHASES.md`, `MEMORY.md`, `CONTRIBUTING.md`, `AGENTS.md`).
6. **Mandatory Skills Utilization**: Always check and invoke relevant skills from `.agents/skills/` (such as `diagnosing-bugs`, `codebase-design`, `tdd`, `code-review`, `writing-for-agents`).
7. **Grill for Every Key Decision (`grilling` / `/grill-me`)**: For architectural changes, design crossroads, or ambiguous requirements, relentlessly interview the user using structured rounds with recommended answers until a complete shared understanding is reached.
8. **Skill Discovery (`find-skills`)**: Use `find-skills` (`npx skills find`) to search and install new community skills when addressing novel capabilities or workflows.

---

## 2. Architecture & Module Boundaries

| Module | Responsibility | Critical Constraints |
| :--- | :--- | :--- |
| [`main.py`](file:///c:/Code/link/main.py) | Application entrypoint, pywebview WebView2 window initialization, and RPC bridge binding. | Keep modular and minimal (< 100 lines); delegate state and business logic to `bridge.py`. |
| [`community.py`](file:///c:/Code/link/community.py) | Community Cloud Cache REST client (Firebase RTDB), local timezone intelligence, and 1-byte health checks. | Zero-SDK integration with standard `urllib`/`json`; enforce split metadata/payload schema and overwrite rules. |
| [`utils.py`](file:///c:/Code/link/utils.py) | Path resolution (`get_app_data_dir`, `get_export_dir`), settings I/O, and Win32 icon binding. | Never hardcode local paths or `%TEMP%` when frozen. |
| [`bridge.py`](file:///c:/Code/link/bridge.py) | High-speed RPC Bridge connecting Python workers to the hardware-accelerated WebView2 frontend. | Use private attributes (`self._window`) to prevent COM recursion during JS reflection. |
| [`frontend/`](file:///c:/Code/link/frontend/) | Next-gen Astro + Svelte + Web Audio frontend (Living Canvas, Defrag Mosaic, Discovery Hub, Apple Liquid Glass). | Keep zero emojis, use `<Icon />` SVG components, and build to `dist_web/`. |
| [`engine.py`](file:///c:/Code/link/engine.py) | Playwright asynchronous multi-tab worker pool & Cloudflare Turnstile bypass. | Share a single browser context across concurrent tabs to minimize memory footprint. Use detected browser channel (Chrome/Edge). |
| [`scraper.py`](file:///c:/Code/link/scraper.py) | HTML parsing for FitGirl game pages, pastebins, cover art, and direct links. | Use `urllib.parse` and BeautifulSoup/lxml with defensive fallbacks for missing mirrors. |
| [`validator.py`](file:///c:/Code/link/validator.py) | Rapid 1-byte HTTP Range GET requests to verify links and aggregate total repack sizes. | Always sanitize filenames extracted from `Content-Disposition`. |
| [`history.py`](file:///c:/Code/link/history.py) | Embedded SQLite archive for saved extractions and link re-use. | Use 100% parameterized SQL queries (`?`). Never persist aborted extractions. |
| [`integrations.py`](file:///c:/Code/link/integrations.py) | JDownloader 2 FlashGot HTTP API (port 9666), `.crawljob`, `.txt`, `.json` exporters. | Append `#filename.rar` fragments to all URLs so JD2 avoids triggering "Deep Link Analysis". |
| [`updater.py`](file:///c:/Code/link/updater.py) | GitHub Releases API updater with semantic versioning comparisons. | Normalize version tuples to 3 parts (e.g. `v3.1` == `(3, 1, 0)`). |

---

## 3. Essential Commands & Workflows

### Run Application in Development
```powershell
python main.py
```

### Validate Syntax Across Modules
```powershell
python -c "import main, bridge, engine, scraper, validator, history, integrations, updater, utils, community; print('All Phase 4 modules OK')"
```

### Build Standalone Executable
```powershell
# Kill running instances first
Get-Process -Name LinkExtractor, main -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
pyinstaller LinkExtractor_Single.spec --noconfirm
```
*Output binary:* `dist/LinkExtractor.exe`

### Run Security Penetration Test Baseline
```powershell
python scratch/security_pen_test.py
```

---

## 4. Solved Technical Gotchas

* **WebView2 RPC Bridge Reflection Recursion**: pywebview iterates over public attributes of the exposed API object when generating JavaScript bindings. Assigning the window instance directly as `self.window` triggered recursive COM interface inspection and crashed with `RecursionError` or thread deadlocks. Always store window references in private attributes (`self._window`).
* **Off-Screen Headed Browser**: Launching visible browser instances (`headless=False`) causes Windows to steal foreground focus and throttle VSync frame delivery to the background application. Chromium/Edge must be launched with `--window-position=-3000,-3000` to maintain 100% Cloudflare Turnstile token resolution without stealing window focus.
* **PyInstaller Single-File Web Assets**: PyInstaller single-file binaries unpack to `%TEMP%/_MEIxxxxxx`. The WebView2 frontend must be bundled via `('dist_web', 'dist_web')` in `LinkExtractor_Single.spec` and resolved at runtime via `utils.get_resource_path('dist_web')`.
* **Legacy Flet UI Context (v3.5.0 and earlier)**: Prior to v3.8.0, Link Extractor used Python `flet` (Flutter runner). The legacy codebase suffered from thread buffer stalls, COM taskbar icon binding issues, and heavyweight memory usage. In v3.8.0, the entire `ui/` directory was deleted and replaced by Astro 5 + Svelte 5 + Windows WebView2, completely eliminating Flutter runner dependencies.

---

## 5. Context Pointers

* For persistent architectural decisions, technical traps, and historical context: See [`MEMORY.md`](file:///c:/Code/link/MEMORY.md).
* For Phase 3 (Firebase Community Cloud Cache) specifications and roadmap: See [`PHASES.md`](file:///c:/Code/link/PHASES.md).
* For PR standards and local environment setup: See [`CONTRIBUTING.md`](file:///c:/Code/link/CONTRIBUTING.md).
