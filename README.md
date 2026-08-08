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

<img width="1643" height="991" alt="1" src="https://github.com/user-attachments/assets/30bbfaed-2458-46e0-914e-76de963a2093" />
<img width="1919" height="881" alt="2" src="https://github.com/user-attachments/assets/954a3f44-27ea-4feb-98b0-83b253c599c3" />



---

### Step 2: Click "Extract & Resolve All"
Click the **Extract & Resolve All** button to start the process.

<img width="1051" height="781" alt="3" src="https://github.com/user-attachments/assets/b6b275b0-3cb5-408e-855a-5977efe729a1" />


---

### Step 3: Automatic Cloudflare Verification
The app uses your system browser to automatically pass Cloudflare verification per link in ~5-8 seconds.

---

### Step 4: Direct URLs Generated
Watch as `https://dl.fuckingfast.co/dl/...` direct URLs are generated in real-time. They auto-copy to your clipboard!


<img width="871" height="448" alt="Screenshot 2026-08-08 140348" src="https://github.com/user-attachments/assets/4f96e27e-0d94-4242-9921-5f6b8a57f45c" />

---

### Step 5: Paste into JDownloader 2
Open **JDownloader 2**. LinkGrabber will grab the direct URLs automatically. Hit **Start Downloads** and enjoy max speed downloading with zero blocks!

<img width="1001" height="716" alt="Screenshot 2026-08-08 141817" src="https://github.com/user-attachments/assets/9d61bfb9-0490-41aa-b2f1-50916420ce0f" />

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
