# 🤝 Contributing to FitGirl Direct Link Extractor

Thank you for your interest in contributing! Whether you're fixing a bug, improving performance, adding new hoster decrypters, or refining the UI, your help is welcome.

---

## 📜 Code of Conduct & Ground Rules

1. **Non-Commercial Respect**: This project is licensed under **PolyForm Noncommercial 1.0.0**. Contributions must remain open, free, and non-commercial.
2. **Attribution**: Author credits (`Vikash / @vik05h`) must be preserved in all documentation and UI components.
3. **No Malicious Payloads**: All submitted scrapers, resolvers, and parsers must strictly adhere to legitimate HTTP/browser automation and respect user safety.

---

## 🛠️ Local Development Setup

### 1. Prerequisites
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **Git**
- Google Chrome, Microsoft Edge, or Chromium

### 2. Clone and Install
```bash
# Clone the repository
git clone https://github.com/vik05h/Link-Extractor.git
cd Link-Extractor

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat
# Linux/macOS:
source .venv/bin/activate

# Install core dependencies
pip install flet playwright pyperclip

# Install Playwright browser engines
playwright install chromium
```

### 3. Run Development Server
```bash
# Launch the Material 3 Desktop App
python main.py
```

---

## 📐 Architecture & Codebase Layout

```
Link-Extractor/
├── main.py              # Modern Flet Material 3 desktop UI & state management
├── main_tkinter.py      # Legacy CustomTkinter UI fallback
├── engine.py            # Playwright multi-tab pool & Cloudflare Turnstile solver
├── scraper.py           # FitGirl game page & pastebin parser
├── validator.py         # Concurrent 1-byte Range GET link & size validator
├── history.py           # SQLite local storage for past downloads
├── integrations.py      # JDownloader 2 FlashGot HTTP API (9666) & .crawljob exporter
├── updater.py           # GitHub Releases API auto-update checker
├── theme_m3.py          # Material 3 design tokens & color schemes
└── assets/              # App icons, logos, and UI graphics
```

---

## 🧪 Testing Your Changes

Before submitting a Pull Request, please test your changes across the following workflows:

1. **Syntax & Import Validation**:
   ```bash
   python -c "import main, engine, scraper, validator, history, integrations, updater; print('All modules OK')"
   ```
2. **Single-Link & Multi-Tab Resolution**:
   Test with a real FitGirl game page URL and confirm all parts resolve to `dl.fuckingfast.co` links with `#part_name.rar` anchors.
3. **Cancellation & History State**:
   Verify that clicking **Cancel** mid-extraction gracefully aborts without deadlocking the UI or creating orphan history records.
4. **JDownloader 2 Integration**:
   Confirm that clicking **Push to JD2** sends links to JDownloader without triggering the "Deep Link Analysis" prompt.

---

## 🔀 Git Workflow & Pull Request Process

1. **Fork the Repo** and create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Commit with Clear Messages**:
   - `feat: add DataNodes mirror resolver`
   - `fix: prevent race condition in cancellation event`
   - `perf: optimize 1-byte range header parsing`
3. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
4. **Open a Pull Request**:
   - Describe what the PR accomplishes and why.
   - Include before/after screenshots if making UI changes.

---

## 💬 Questions & Support

Have an idea or need help? Open an issue on GitHub:
👉 [https://github.com/vik05h/Link-Extractor/issues](https://github.com/vik05h/Link-Extractor/issues)
