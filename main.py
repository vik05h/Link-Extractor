"""
main.py — Main Application Entrypoint for Link Extractor Desktop.
Next-Gen Gaming Hub UI powered by Astro, Svelte, and pywebview (WebView2).
"""

import os
import sys
import threading
import webview

# Ensure Playwright browser cache location
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ms-playwright"
)

import utils
import updater
import community
import traceback
from bridge import AppBridge


def _handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        community.report_crash_log(
            error_type=exc_type.__name__,
            error_message=str(exc_value),
            traceback_str=tb_str,
            context="unhandled_main_thread"
        )
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = _handle_unhandled_exception

if hasattr(threading, "excepthook"):
    def _handle_thread_exception(args):
        tb_str = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        try:
            community.report_crash_log(
                error_type=args.exc_type.__name__,
                error_message=str(args.exc_value),
                traceback_str=tb_str,
                context=f"thread_{getattr(args.thread, 'name', 'worker')}"
            )
        except Exception:
            pass
    threading.excepthook = _handle_thread_exception


def main():
    utils.apply_windows_native_icon("app_icon.ico")
    
    bridge = AppBridge()

    # Determine URL: dev server or bundled dist_web/index.html
    if "--dev" in sys.argv:
        target_url = "http://localhost:4321"
    else:
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        target_url = os.path.join(base_dir, "dist_web", "index.html")
        if not os.path.exists(target_url):
            target_url = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist_web", "index.html")

    window = webview.create_window(
        title=f"Link Extractor {updater.CURRENT_VERSION}",
        url=target_url,
        js_api=bridge,
        width=1180,
        height=840,
        min_size=(960, 680),
        background_color="#07080b"
    )

    bridge.bind_window(window)

    def _check_updates_bg():
        try:
            avail, rel_info = updater.check_for_updates()
            if avail and rel_info:
                bridge.dispatch_event("app:update_available", {
                    "version": rel_info.get("tag_name"),
                    "notes": rel_info.get("body", "")
                })
        except Exception:
            pass

    threading.Thread(target=_check_updates_bg, daemon=True).start()

    webview.start(
        debug="--debug" in sys.argv,
        http_server=True,
        private_mode=False
    )


if __name__ == "__main__":
    main()
