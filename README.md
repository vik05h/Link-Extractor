# ⚡ FitGirl Direct Link Extractor v3.1 — High Speed Direct Link Grabber

[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm_Noncommercial_1.0.0-blue.svg)](LICENSE)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC_BY--NC--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Framework: Flet](https://img.shields.io/badge/UI-Flet_Material_3-purple.svg)](https://flet.dev)

A blazing-fast, lightweight Windows desktop app that extracts multi-part download links from FitGirl game pages & pastebins, automatically passes Cloudflare Turnstile verification using concurrent browser tabs, and outputs **TRUE direct download links** (`dl.fuckingfast.co`) with direct 1-click push to JDownloader 2 and IDM.

No more skipped links or "External solver required" captcha blocks in JDownloader!

---

## 🚀 Key Features

- ⚡ **3x-6x Concurrent Tab Pool**: Resolves links in parallel inside a single browser instance — cutting extraction time from **~4 minutes down to ~1 minute** for a 40-part game!
- 🎨 **Material 3 UI (Flutter Engine)**: 60–120 FPS hardware acceleration, Navigation Rail, live interactive DataTable with 1-click copy, and 5 dynamic color themes.
- 🎮 **Direct FitGirl Game Page Support**: Simply paste any FitGirl game URL (e.g. `https://fitgirl-repacks.site/black-myth-wukong/`). The tool automatically discovers and parses the FuckingFast mirror pastebin without manual hunting.
- 🔁 **Automated 2-Pass Retry Engine**: Never lose a single game part again. If Cloudflare temporarily throttles a link, the engine automatically re-queues and retries failed parts with smart jitter backoff.
- 🔍 **Live 1-Byte Range Link Validation**: Computes exact total repack download size and live filenames using ultra-fast 1-byte Range requests without downloading files.
- 🚀 **1-Click JDownloader 2 Push**: Direct push to JDownloader 2 LinkGrabber via local Click'n'Load HTTP API + `.crawljob` auto-import with `#filename.rar` fragments (zero "Deep link analysis" popups).
- 📚 **SQLite History & Archive**: Embedded local search database of all your past extractions for instant 1-click re-copying or re-pushing.
- 🔄 **GitHub Releases Auto-Updater**: Built-in update checker that notifies you when new releases or binaries are published.

---

## 📖 Quick Tutorial

### Step 1: Enter Your URL
Paste any of the following into the input box:
- **FitGirl Game Page URL**: `https://fitgirl-repacks.site/black-myth-wukong/`
- **FitGirl Pastebin URL**: `https://paste.fitgirl-repacks.site/?dc64365f494f3ba0#...`
- **Direct FuckingFast Links**: `https://fuckingfast.co/...`

The URL type is automatically detected in real-time!

---

### Step 2: Click "Extract & Resolve"
Click **Extract & Resolve** to initiate the high-speed pipeline.

---

### Step 3: Concurrent Cloudflare Resolution
The engine launches concurrent browser tabs (default 3) to automatically pass Cloudflare Turnstile challenges in parallel (~1.5-2.0s effective per part).

---

### Step 4: Direct URLs Auto-Streamed & Validated
Watch direct `https://dl.fuckingfast.co/dl/...` URLs stream into the live DataTable in real-time with verified part sizes and filenames.

---

### Step 5: Push to JDownloader 2 or Copy All
Click **Push to JD2** to send all parts directly into JDownloader 2 LinkGrabber, or click **Copy All** to paste into your favorite download manager.

---

## 🛠️ How to Build from Source

```bash
# 1. Install dependencies
pip install flet playwright pyperclip

# 2. Install browser binaries (one-time)
playwright install chromium

# 3. Run application
python main.py

# 4. Build Standalone EXE
pyinstaller --noconsole --onefile --name "LinkExtractor" main.py
```

The compiled standalone executable will be located in the `dist/` directory.

---

## 🗺️ Project Roadmap

See [PHASES.md](file:///c:/Code/link/PHASES.md) for full phase-by-phase development progress and future integrations (Firebase Community Cloud Cache, multi-hoster support, and CLI automation).

---

## 📜 License & Attribution

This project is licensed under the **PolyForm Noncommercial License 1.0.0** (and **CC BY-NC-SA 4.0**).

### Terms:
* **Non-Commercial Only**: You may use, study, modify, and distribute this software for **free personal, educational, and archival purposes only**. You may **NOT** sell this software, bundle it in paid products, or monetize it in any way.
* **Mandatory Attribution**: Any fork, modification, or binary distribution **MUST** give visible credit to the original author:
  > **Original Author:** Vikash ([@vik05h](https://github.com/vik05h))  
  > **Repository:** [https://github.com/vik05h/Link-Extractor](https://github.com/vik05h/Link-Extractor)
* **Share-Alike**: Any derivative works must be distributed under the same non-commercial license.

---

### ⚠️ Disclaimer
*This tool is created for educational automation and file archival assistance. It does not host or distribute copyrighted files.*
