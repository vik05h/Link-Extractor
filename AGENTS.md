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
| [`main.py`](file:///c:/Code/link/main.py) | Application entrypoint, Flet initialization, navigation rail, and screen switcher wiring. | Keep modular and minimal (< 150 lines); delegate screen layout and state to `ui/`. |
| [`utils.py`](file:///c:/Code/link/utils.py) | Path resolution (`get_app_data_dir`, `get_export_dir`), settings I/O, and Win32 icon binding. | Never hardcode local paths or `%TEMP%` when frozen. |
| [`ui/`](file:///c:/Code/link/ui/) | Modular UI package containing presets (`constants.py`), state models (`state.py`), and screen components (`screens/`). | Screens export clean builder functions; never mutate global state directly without `AppState` / `UIContext`. |
| [`engine.py`](file:///c:/Code/link/engine.py) | Playwright asynchronous multi-tab worker pool & Cloudflare Turnstile bypass. | Share a single browser context across concurrent tabs to minimize memory footprint. Use detected browser channel (Chrome/Edge). |
| [`scraper.py`](file:///c:/Code/link/scraper.py) | HTML parsing for FitGirl game pages, pastebins, and direct links. | Use `urllib.parse` and BeautifulSoup/lxml with defensive fallbacks for missing mirrors. |
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
python -c "import main, engine, scraper, validator, history, integrations, updater, utils; from ui import constants, state; from ui.screens import extractor, pipeline, history as hist_screen, settings; print('All modules OK')"
```

### Build Standalone Executable
```powershell
# Kill running instances first
Get-Process -Name LinkExtractor, flet, main -ErrorAction SilentlyContinue | Stop-Process -Force
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

* **Win32 Taskbar Icon Binding**: Flet's runner (`flet.exe`) displays a default Flutter icon. `apply_windows_native_icon()` uses `ctypes` (`SendMessageW(WM_SETICON)` + `SetClassLongPtrW(GCLP_HICON)`) on startup to bind `app_icon.ico` directly to the window class.
* **Flet AnimatedSwitcher Hot-Swap**: `AnimatedSwitcher` locks duration at `initState()`. To change animation style at runtime, wrap in `screen_holder = ft.Container(...)` and rebuild `screen_holder.content = create_screen_switcher(cfg, cur_screen)`.
* **PyInstaller Icon JSON Dependency**: Flet 0.86+ requires `collect_all('flet')` in `LinkExtractor_Single.spec` to bundle internal icon mappings.
* **Adaptive Scrolling**: All screen containers must include `scroll=ft.ScrollMode.ADAPTIVE` on the outer `ft.Column` to prevent UI truncation on smaller monitors.

---

## 5. Context Pointers

* For persistent architectural decisions, technical traps, and historical context: See [`MEMORY.md`](file:///c:/Code/link/MEMORY.md).
* For Phase 3 (Firebase Community Cloud Cache) specifications and roadmap: See [`PHASES.md`](file:///c:/Code/link/PHASES.md).
* For PR standards and local environment setup: See [`CONTRIBUTING.md`](file:///c:/Code/link/CONTRIBUTING.md).
