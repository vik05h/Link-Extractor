# ⚡ FitGirl Direct Link Extractor for JDownloader 2

A fast, lightweight Windows app that extracts multi-part download links from FitGirl pastebin pages, automatically passes Cloudflare verification in the background, and gives you **TRUE direct download links** (`dl.fuckingfast.co`) for JDownloader 2.

No more skipped links or "External solver required" captcha blocks in JDownloader!

---

## 🚀 Features

- **Automated Cloudflare Bypass**: Auto-solves Turnstile challenges seamlessly using your installed browser (Edge/Chrome).
- **No Browser Download Spam**: Resolves direct URLs silently in memory without downloading 2GB `.rar` files onto your drive.
- **High Speed**: Resolves each link in ~5 seconds.
- **Auto Clipboard & Save**: Direct URLs are automatically copied to your clipboard and saved to `resolved_direct_urls.txt`.
- **JDownloader Ready**: Works instantly with JDownloader 2's LinkGrabber.

---

## 📖 Quick Tutorial

### Step 1: Copy your Pastebin URL
Paste your FitGirl pastebin link (e.g. `https://paste.fitgirl-repacks.site/?...`) into the input box.

<!-- SCREENSHOT PLACEHOLDER 1 -->
![Step 1 - Paste Link](./screenshots/step1.png)

---

### Step 2: Click "Extract & Resolve All"
Click the **Extract & Resolve All** button to start the process.

<!-- SCREENSHOT PLACEHOLDER 2 -->
![Step 2 - Start Extraction](./screenshots/step2.png)

---

### Step 3: Automatic Cloudflare Verification
The app uses your system browser to automatically pass Cloudflare verification per link in ~5 seconds.

<!-- SCREENSHOT PLACEHOLDER 3 -->
![Step 3 - Cloudflare Bypass](./screenshots/step3.png)

---

### Step 4: Direct URLs Generated
Watch as `https://dl.fuckingfast.co/dl/...` direct URLs are generated in real-time. They auto-copy to your clipboard!

<!-- SCREENSHOT PLACEHOLDER 4 -->
![Step 4 - Direct URLs Generated](./screenshots/step4.png)

---

### Step 5: Paste into JDownloader 2
Open **JDownloader 2**. LinkGrabber will grab the direct URLs automatically. Hit **Start Downloads** and enjoy max speed downloading with zero blocks!

<!-- SCREENSHOT PLACEHOLDER 5 -->
![Step 5 - JDownloader 2 Download](./screenshots/step5.png)

---

## 🛠️ How to Build from Source

```bash
# Install dependencies
pip install customtkinter playwright pyperclip pillow pyinstaller

# Generate app icon & assets
python make_icon.py

# Build single EXE
pyinstaller --noconfirm --onefile --windowed --icon="app_icon.ico" --add-data "app_icon.png;." --add-data "app_icon.ico;." --add-data "icon_extract.png;." --add-data "icon_copy.png;." --add-data "icon_cancel.png;." --name "LinkExtractor_Single" main.py
```
