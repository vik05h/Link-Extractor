# ⚡ FitGirl Direct Link Extractor v3.0 — High Speed Direct Link Grabber

A blazing-fast, lightweight Windows desktop app that extracts multi-part download links from FitGirl game pages & pastebins, automatically passes Cloudflare Turnstile verification using concurrent browser tabs, and outputs **TRUE direct download links** (`dl.fuckingfast.co`) for JDownloader 2 and IDM.

No more skipped links or "External solver required" captcha blocks in JDownloader!

---

## 🚀 What's New in v3.0

- ⚡ **3x Concurrent Tab Pool**: Resolves 3 links in parallel inside a single browser instance — cutting extraction time from **~4 minutes down to ~1 minute** for a 40-part game!
- 🎮 **Direct FitGirl Game Page Support**: Simply paste any FitGirl game URL (e.g. `https://fitgirl-repacks.site/black-myth-wukong/`). The tool automatically discovers and parses the FuckingFast mirror pastebin without manual hunting.
- 🔁 **Automated 2-Pass Retry Engine**: Never lose a single game part again. If Cloudflare temporarily throttles a link, the engine automatically re-queues and retries failed parts with smart jitter backoff.
- ⏱️ **Real-Time Speed & ETA Display**: Live progress reporting with per-part resolution speed (e.g. `1.8s/part`), active tab counter, and remaining time countdown.
- 🧩 **Clean Modular Architecture**: Deep separation between `scraper.py` (page & pastebin parsing), `engine.py` (high-performance Playwright worker pool), and `main.py` (CustomTkinter GUI).

---

## 📖 Quick Tutorial

### Step 1: Enter Your URL
Paste any of the following into the input box:
- **FitGirl Game Page URL**: `https://fitgirl-repacks.site/black-myth-wukong/`
- **FitGirl Pastebin URL**: `https://paste.fitgirl-repacks.site/?dc64365f494f3ba0#...`
- **Direct FuckingFast Links**: `https://fuckingfast.co/...`

The URL type is automatically detected in real-time!

---

### Step 2: Click "Extract & Resolve All"
Click **Extract & Resolve All** to initiate the high-speed pipeline.

---

### Step 3: Concurrent Cloudflare Resolution
The engine launches concurrent browser tabs (default 3) to automatically pass Cloudflare Turnstile challenges in parallel (~1.5-2.0s effective per part).

---

### Step 4: Direct URLs Auto-Copied & Saved
Watch direct `https://dl.fuckingfast.co/dl/...` URLs stream into the results list in real-time. Upon completion, all links are automatically copied to your clipboard and saved to `resolved_direct_urls.txt`.

---

### Step 5: Paste into JDownloader 2
Open **JDownloader 2**. LinkGrabber will catch the clipboard direct URLs automatically. Click **Start Downloads** for max-speed downloading with zero captcha interruptions!

---

## 🛠️ How to Build from Source

```bash
# 1. Install dependencies
pip install customtkinter playwright pyperclip pillow pyinstaller

# 2. (Optional) Re-generate app icons
python make_icon.py

# 3. Build Single-File Standalone EXE
pyinstaller LinkExtractor_Single.spec
```

The compiled standalone executable will be located in the `dist/` directory.

---

## 🗺️ Project Roadmap

See [PHASES.md](file:///c:/Code/link/PHASES.md) for full phase-by-phase development progress and future integrations (JDownloader Click'n'Load, HTTP HEAD validation, download history, and multi-hoster support).
