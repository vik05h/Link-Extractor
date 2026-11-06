"""
main.py: Application entrypoint for Link Extractor Desktop.
Astro + Svelte frontend in a pywebview (WebView2) window. All logic lives behind bridge.py.
"""

import logging
import sys
import time

import webview

import telemetry
import updater
import utils
from bridge import AppBridge

log = logging.getLogger(__name__)


def _disable_webview_http_cache() -> None:
    """Stop WebView2 from serving stale web bundles after an update."""
    try:
        import webview.platforms.edgechromium as edge
    except Exception:
        # This is only a tweak, so it must never stop the app from starting.
        log.exception("WebView2 cache setting skipped")
        return

    original = edge.CoreWebView2CreationProperties  # pyright: ignore[reportPrivateImportUsage]

    class PatchedProperties(original):
        @property
        def AdditionalBrowserArguments(self):
            return super().AdditionalBrowserArguments

        @AdditionalBrowserArguments.setter
        def AdditionalBrowserArguments(self, value):
            if value and "--disable-http-cache" not in value:
                value = value + " --disable-http-cache"
            elif not value:
                value = "--disable-http-cache"
            super(PatchedProperties, self.__class__).AdditionalBrowserArguments.__set__(self, value)

    edge.CoreWebView2CreationProperties = PatchedProperties  # pyright: ignore[reportPrivateImportUsage]


def _frontend_url() -> str:
    if "--dev" in sys.argv:
        return "http://localhost:4321"
    return f"{utils.get_resource_path('dist_web/index.html')}?v={updater.CURRENT_VERSION}&t={int(time.time())}"


def main() -> None:
    utils.setup_logging()
    telemetry.install_exception_hooks()
    _disable_webview_http_cache()
    utils.apply_windows_native_icon("app_icon.ico")

    bridge = AppBridge()
    window = webview.create_window(
        title=f"Link Extractor {updater.CURRENT_VERSION}",
        url=_frontend_url(),
        js_api=bridge,
        width=1180,
        height=840,
        min_size=(960, 680),
        background_color="#07080b",
    )
    bridge.bind_window(window)

    webview.start(debug="--debug" in sys.argv, http_server=True, private_mode=False)


if __name__ == "__main__":
    main()
