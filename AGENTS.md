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
| [`main.py`](file:///c:/Code/link/main.py) | Entrypoint: pywebview WebView2 window and bridge binding. | Keep under 100 lines. |
| [`bridge.py`](file:///c:/Code/link/bridge.py) | RPC adapter between the frontend and the modules below. | An adapter only: decisions live in the modules. Private attributes (`self._window`) prevent COM recursion during JS reflection. |
| [`pipeline.py`](file:///c:/Code/link/pipeline.py) | Runs one extraction and decides what happens to the result. | The single source of truth for what gets saved and published. Reaches the browser and network only through `PipelinePorts`. |
| [`links.py`](file:///c:/Code/link/links.py) | Which links are trusted. | Every link from the database, clipboard, or a web page passes through here. Hostnames compare exactly. |
| [`game_records.py`](file:///c:/Code/link/game_records.py) | One definition of "the same game" and "expired"; cleans shared records. | Pure functions only. |
| [`firebase_client.py`](file:///c:/Code/link/firebase_client.py) | Firebase REST calls. | Zero-SDK `urllib`/`json`. Failures raise `FirebaseError`. |
| [`community.py`](file:///c:/Code/link/community.py) | Community Cloud Cache: feed, links, publishing, presence, usage. | Clients add and update game records; deleting belongs to the admin. |
| [`issues.py`](file:///c:/Code/link/issues.py) | Community Issue Center: reports, votes, comments, moderation. | The server judges the admin key. Local reports are only an outbox. |
| [`telemetry.py`](file:///c:/Code/link/telemetry.py) | Crash reports. | Everything goes through `report_crash_log`, which applies the opt-out and removes personal data. |
| [`utils.py`](file:///c:/Code/link/utils.py) | Path resolution, settings I/O, logging, Win32 icon binding. | Never hardcode local paths or `%TEMP%` when frozen. |
| [`frontend/`](file:///c:/Code/link/frontend/) | Astro + Svelte + Web Audio frontend. | Use `<Icon />` SVG components for icons, and build to `dist_web/`. |
| [`engine.py`](file:///c:/Code/link/engine.py) | Playwright multi-tab worker pool & Cloudflare Turnstile bypass. | Share a single browser context across concurrent tabs. Use detected browser channel (Chrome/Edge). |
| [`scraper.py`](file:///c:/Code/link/scraper.py) | Parsing of FitGirl game pages and pastebins, cover art. | Regular expressions with defensive fallbacks for missing mirrors. |
| [`validator.py`](file:///c:/Code/link/validator.py) | 1-byte HTTP Range link checks and repack size totals. | Keep the three verdicts apart: alive, dead, unknown. Sanitize filenames from `Content-Disposition`. |
| [`history.py`](file:///c:/Code/link/history.py) | SQLite archive of extractions. | 100% parameterized SQL (`?`). Cancelled runs are never persisted. |
| [`integrations.py`](file:///c:/Code/link/integrations.py) | JDownloader 2 FlashGot HTTP API (port 9666), `.crawljob`, `.txt`, `.json` exporters. | Append `#filename.rar` fragments to all URLs so JD2 avoids "Deep Link Analysis". |
| [`updater.py`](file:///c:/Code/link/updater.py) | GitHub Releases update check and installer. | Install only files that pass the source, size, SHA-256, and file type checks. Normalize version tuples to 3 parts. |

---

## 3. Essential Commands & Workflows

### Run Application in Development
```powershell
python main.py
```

### Run the Checks
```powershell
python -m pytest
ruff check .
pyright
cd frontend; npm run check
```
Tests run offline against a local Firebase stand-in. After changing `firebase/database.rules.json`, also run the emulator tests in [`firebase/README.md`](file:///c:/Code/link/firebase/README.md), because those rules protect every installed copy.

### Validate Imports
```powershell
python -c "import main, bridge, pipeline, engine, scraper, validator, history, integrations, updater, utils, community, issues, telemetry, palette, links, firebase_client, game_records, version; print('All modules OK')"
```

### Change the Version
```powershell
python scripts/set_version.py 4.0.0
```
Then add a matching entry to `VERSION_CHANGELOGS` in `updater.py`.

### Build Standalone Executable
```powershell
# Kill running instances first
Get-Process -Name LinkExtractor, main -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
pyinstaller LinkExtractor_Single.spec --noconfirm
```
*Output binary:* `dist/LinkExtractor.exe`. Add new modules to `hiddenimports` in the spec files.

---

## 4. Solved Technical Gotchas

* **WebView2 RPC Bridge Reflection Recursion**: pywebview iterates over public attributes of the exposed API object when generating JavaScript bindings. Assigning the window instance directly as `self.window` triggered recursive COM interface inspection and crashed with `RecursionError` or thread deadlocks. Always store window references in private attributes (`self._window`).
* **Off-Screen Headed Browser**: Launching visible browser instances (`headless=False`) causes Windows to steal foreground focus and throttle VSync frame delivery to the background application. Chromium/Edge must be launched with `--window-position=-3000,-3000` to maintain 100% Cloudflare Turnstile token resolution without stealing window focus.
* **PyInstaller Single-File Web Assets**: PyInstaller single-file binaries unpack to `%TEMP%/_MEIxxxxxx`. The WebView2 frontend must be bundled via `('dist_web', 'dist_web')` in `LinkExtractor_Single.spec` and resolved at runtime via `utils.get_resource_path('dist_web')`.
* **The database has no login**: Anyone can call Firebase directly, so server protection lives only in `firebase/database.rules.json`. Client checks in `links.py` protect the client itself.

---

## 5. Context Pointers

* For persistent architectural decisions, technical traps, and historical context: See [`MEMORY.md`](file:///c:/Code/link/MEMORY.md).
* For the roadmap: See [`PHASES.md`](file:///c:/Code/link/PHASES.md).
* For database rules and Admin Mode setup: See [`firebase/README.md`](file:///c:/Code/link/firebase/README.md).
* For PR standards and local environment setup: See [`CONTRIBUTING.md`](file:///c:/Code/link/CONTRIBUTING.md).
