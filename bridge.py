"""
bridge.py — Asynchronous Bi-Directional RPC Bridge for Link Extractor Desktop.

Exposes core extraction, community caching, JDownloader 2 push, history, and
settings APIs to the web frontend via pywebview's window.pywebview.api.
Dispatches real-time events to the frontend via JavaScript CustomEvents.
"""

import os
import re
import json
import time
import asyncio
import threading
from typing import Dict, Any, List, Optional
import pyperclip

import utils
import scraper
import engine
import validator
import community
import integrations
import updater
from history import HistoryManager


class AppBridge:
    def __init__(self):
        self._window = None
        self._settings = utils.load_settings()
        self._history_mgr = HistoryManager()
        self._cancel_event = threading.Event()
        self._is_running = False
        self._current_engine: Optional[engine.ResolutionEngine] = None
        self._clipboard_thread = None
        self._clipboard_running = False
        self._last_clipboard_val = ""

    def bind_window(self, window):
        """Binds the active pywebview window reference."""
        self._window = window
        self._start_clipboard_sentinel()

    def dispatch_event(self, event_name: str, payload: Any = None):
        """Dispatches a custom event to the web frontend."""
        if not self._window:
            return
        try:
            data_json = json.dumps(payload if payload is not None else {})
            js_code = f"window.dispatchEvent(new CustomEvent('{event_name}', {{ detail: {data_json} }}));"
            self._window.evaluate_js(js_code)
        except Exception as err:
            print(f"[Bridge Event Error] {event_name}: {err}")

    # ==========================================
    # Window Controls
    # ==========================================

    def minimize_window(self):
        """Minimizes the native desktop window."""
        if self._window:
            try:
                self._window.minimize()
            except Exception:
                pass

    def maximize_window(self):
        """Toggles maximize or restore on the native desktop window."""
        if self._window:
            try:
                self._window.toggle_fullscreen()
            except Exception:
                pass

    def close_window(self):
        """Closes the desktop application."""
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass

    # ==========================================
    # Clipboard Sentinel
    # ==========================================

    def _start_clipboard_sentinel(self):
        if self._clipboard_running:
            return
        self._clipboard_running = True

        def _sentinel_loop():
            while self._clipboard_running:
                try:
                    if self._settings.get("clipboard_sentinel_enabled", True):
                        clip_val = (pyperclip.paste() or "").strip()
                        if clip_val and clip_val != self._last_clipboard_val:
                            self._last_clipboard_val = clip_val
                            url_type = scraper.detect_url_type(clip_val)
                            if url_type in ("fitgirl_game_page", "fitgirl_pastebin", "fuckingfast_direct", "raw_links"):
                                slug = scraper.extract_game_slug(clip_val)
                                self.dispatch_event("clipboard:detected", {
                                    "url": clip_val,
                                    "url_type": url_type,
                                    "slug": slug
                                })
                except Exception:
                    pass
                time.sleep(1.5)

        self._clipboard_thread = threading.Thread(target=_sentinel_loop, daemon=True)
        self._clipboard_thread.start()

    # ==========================================
    # URL & Metadata Discovery
    # ==========================================

    def detect_url(self, url: str) -> Dict[str, Any]:
        """Detects the input URL type and extracts game slug."""
        clean_url = (url or "").strip()
        url_type = scraper.detect_url_type(clean_url)
        slug = scraper.extract_game_slug(clean_url) if url_type == "fitgirl_game_page" else ""
        return {
            "url": clean_url,
            "url_type": url_type,
            "slug": slug
        }

    # ==========================================
    # Community Cloud Cache APIs
    # ==========================================

    def get_community_feed(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetches trending pre-resolved games from Community Firebase Cache."""
        try:
            fb_url = self._settings.get("community_firebase_url")
            games = community.get_community_games(fb_url, force_refresh=force_refresh)
            return games or []
        except Exception as err:
            print(f"[Bridge Error] get_community_feed: {err}")
            return []

    def get_game_by_slug(self, slug: str) -> Dict[str, Any]:
        """Queries single game metadata by slug."""
        fb_url = self._settings.get("community_firebase_url")
        data = community.get_game_by_slug(slug, fb_url)
        return data or {}

    def get_game_urls(self, slug: str) -> List[str]:
        """Fetches direct URLs for a specific community game slug."""
        fb_url = self._settings.get("community_firebase_url")
        return community.get_game_urls(slug, fb_url)

    def check_health(self, url: str) -> Dict[str, Any]:
        """Performs 1-byte Range check to verify if direct link is alive."""
        try:
            val_link = validator.validate_single_url(1, url, timeout=6.0)
            return {
                "is_alive": val_link.is_valid,
                "status_code": val_link.status_code,
                "message": val_link.content_length_str if val_link.is_valid else (val_link.error or "Link unreachable")
            }
        except Exception as err:
            return {"is_alive": False, "status_code": 0, "message": str(err)}

    def ping_presence(self, session_id: str = "") -> Dict[str, Any]:
        """Pings user presence heartbeat and returns online gamers count."""
        fb_url = self._settings.get("community_firebase_url")
        active = community.ping_presence(session_id, updater.CURRENT_VERSION, fb_url)
        return {"live_gamers": active}

    def track_game_usage(self, slug: str) -> Dict[str, Any]:
        """Increments usage/download counter for a community game."""
        fb_url = self._settings.get("community_firebase_url")
        new_count = community.increment_game_usage(slug, fb_url)
        return {"slug": slug, "used_count": new_count}

    def get_community_stats(self) -> Dict[str, Any]:
        """Fetches live user count and global grabs."""
        fb_url = self._settings.get("community_firebase_url")
        return community.get_community_stats(fb_url)

    def extract_game_palette(self, image_url: str) -> Dict[str, Any]:
        """
        Downloads game cover art via Python (bypassing browser CORS restrictions),
        analyzes pixels using PIL and HSV space, and returns the signature vibrant
        primary and harmonic secondary colors for YouTube-style ambient mode.
        """
        if not image_url or not isinstance(image_url, str):
            return {
                "primary": [16, 185, 129],
                "secondary": [6, 182, 212],
                "glow": "rgba(16, 185, 129, 0.35)"
            }

        if not hasattr(self, "_palette_cache"):
            self._palette_cache = {}

        if image_url in self._palette_cache:
            return self._palette_cache[image_url]

        try:
            import urllib.request
            import io
            import colorsys
            from PIL import Image

            req = urllib.request.Request(
                image_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            data = urllib.request.urlopen(req, timeout=5.0).read()
            img = Image.open(io.BytesIO(data)).convert("RGB").resize((48, 48))

            pixels = [img.getpixel((x, y)) for y in range(48) for x in range(48)]

            scored = []
            for r, g, b in pixels:
                h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                # Filter out pure whites, deep blacks, and muddy greys
                if 0.16 < v < 0.95 and s > 0.22:
                    score = (s * 2.0) + (1.0 - abs(v - 0.55))
                    scored.append((score, (r, g, b), h))

            if scored:
                scored.sort(key=lambda item: item[0], reverse=True)
                raw_primary = scored[0][1]
                primary_h = scored[0][2]

                # Boost brightness slightly for vibrant dark-theme readability
                p_r = min(245, max(35, int(raw_primary[0] * 1.3)))
                p_g = min(245, max(35, int(raw_primary[1] * 1.3)))
                p_b = min(245, max(35, int(raw_primary[2] * 1.3)))
                primary_rgb = (p_r, p_g, p_b)

                secondary_rgb = None
                for _, rgb, h in scored[1:]:
                    hue_diff = abs(h - primary_h)
                    if hue_diff > 0.5:
                        hue_diff = 1.0 - hue_diff
                    if hue_diff > 0.10 or abs(rgb[0] - raw_primary[0]) > 50:
                        s_r = min(245, max(35, int(rgb[0] * 1.25)))
                        s_g = min(245, max(35, int(rgb[1] * 1.25)))
                        s_b = min(245, max(35, int(rgb[2] * 1.25)))
                        secondary_rgb = (s_r, s_g, s_b)
                        break

                if not secondary_rgb:
                    s_r = min(245, max(35, int(primary_rgb[0] * 0.7 + 45)))
                    s_g = min(245, max(35, int(primary_rgb[1] * 0.85 + 50)))
                    s_b = min(245, max(35, int(primary_rgb[2] * 1.25 + 60)))
                    secondary_rgb = (s_r, s_g, s_b)

                result = {
                    "primary": list(primary_rgb),
                    "secondary": list(secondary_rgb),
                    "glow": f"rgba({primary_rgb[0]}, {primary_rgb[1]}, {primary_rgb[2]}, 0.4)"
                }
                self._palette_cache[image_url] = result
                return result
        except Exception:
            pass

        # Deterministic fallback from url hash if network fails
        import colorsys
        h_val = sum(ord(c) for c in image_url) % 360
        r_f, g_f, b_f = [int(x * 255) for x in colorsys.hsv_to_rgb(h_val / 360.0, 0.85, 0.65)]
        fallback = {
            "primary": [r_f, g_f, b_f],
            "secondary": [min(255, r_f + 40), max(10, g_f - 30), max(10, b_f - 20)],
            "glow": f"rgba({r_f}, {g_f}, {b_f}, 0.35)"
        }
        self._palette_cache[image_url] = fallback
        return fallback

    # ==========================================
    # Extraction Pipeline
    # ==========================================

    def start_extraction(self, url: str, concurrency: int = None) -> Dict[str, Any]:
        """Starts the asynchronous link extraction pipeline."""
        if self._is_running:
            return {"status": "error", "message": "An extraction is already in progress."}

        target_url = (url or "").strip()
        if not target_url:
            return {"status": "error", "message": "Empty URL provided."}

        self._cancel_event.clear()
        self._is_running = True
        concurrency = concurrency or self._settings.get("concurrency", 3)

        threading.Thread(
            target=self._run_extraction_pipeline,
            args=(target_url, concurrency),
            daemon=True
        ).start()

        return {"status": "started", "target_url": target_url}

    def _run_extraction_pipeline(self, target_url: str, concurrency: int):
        game_title = "Game Repack"
        cover_image = ""
        resolved_urls = []
        val_summary = None

        try:
            self.dispatch_event("pipeline:status", {"status": "starting", "message": "Inspecting URL..."})

            url_type = scraper.detect_url_type(target_url)
            intermediate_urls = []

            if url_type == "fitgirl_game_page":
                self.dispatch_event("pipeline:status", {"status": "scraping", "message": "Parsing FitGirl Game Page..."})
                pastebins, game_title, cover_image = scraper.extract_game_page_pastebins(target_url)

                ff_pastebins = [p for p in pastebins if p.get("hoster") == "FuckingFast"] or (pastebins[:1] if pastebins else [])
                if not ff_pastebins:
                    raise ValueError("No FuckingFast or compatible pastebin mirrors found on game page.")

                target_pastebin = ff_pastebins[0]["url"]
                self.dispatch_event("pipeline:status", {"status": "scraping", "message": "Decrypting Pastebin links..."})
                self._current_engine = engine.ResolutionEngine(concurrency=concurrency, headless=False)
                intermediate_urls = asyncio.run(self._current_engine.fetch_pastebin_links(target_pastebin))

                if not intermediate_urls:
                    raise ValueError("No direct download parts found inside pastebin.")

                self.dispatch_event("pipeline:game_meta", {
                    "title": game_title,
                    "image_url": cover_image,
                    "parts_count": len(intermediate_urls)
                })

            elif url_type == "fitgirl_pastebin":
                self.dispatch_event("pipeline:status", {"status": "scraping", "message": "Decrypting Pastebin page..."})
                self._current_engine = engine.ResolutionEngine(concurrency=concurrency, headless=False)
                intermediate_urls = asyncio.run(self._current_engine.fetch_pastebin_links(target_url))

                # Auto-resolve game title, artwork, and canonical slug from part filenames
                self.dispatch_event("pipeline:status", {"status": "scraping", "message": "Resolving Game Intelligence & Artwork..."})
                pastebin_meta = scraper.resolve_pastebin_metadata(target_url, intermediate_urls)
                game_title = pastebin_meta.get("title") or "FitGirl Pastebin Repack"
                cover_image = pastebin_meta.get("image_url") or ""
                target_url = pastebin_meta.get("source_url") or target_url

                self.dispatch_event("pipeline:game_meta", {
                    "title": game_title,
                    "image_url": cover_image,
                    "parts_count": len(intermediate_urls)
                })
            else:
                intermediate_urls = [target_url]
                game_title = "Direct Repack"

            total_parts = len(intermediate_urls)
            self.dispatch_event("pipeline:status", {
                "status": "resolving",
                "message": f"Bypassing Cloudflare Turnstile across {total_parts} parts ({concurrency} tabs)..."
            })

            # Initialize parts state on frontend
            parts_payload = []
            for idx, p_url in enumerate(intermediate_urls, 1):
                clean_name = p_url.split("#")[-1] if "#" in p_url else f"Part {idx}"
                parts_payload.append({
                    "index": idx,
                    "url": p_url,
                    "filename": clean_name,
                    "status": "pending",
                    "size": "Pending"
                })
            self.dispatch_event("pipeline:init_parts", parts_payload)

            # Callback for Playwright progress
            def on_engine_progress(resolved_so_far, total_count, avg_speed, eta, active_workers, part_name, direct_url, status):
                self.dispatch_event("pipeline:part_update", {
                    "resolved_so_far": resolved_so_far,
                    "total": total_count,
                    "avg_speed": f"{avg_speed:.1f}s/part",
                    "eta": f"~{int(eta)}s",
                    "part_name": part_name,
                    "direct_url": direct_url or "",
                    "status": status
                })

            if not self._current_engine:
                self._current_engine = engine.ResolutionEngine(concurrency=concurrency, headless=False)

            raw_results = self._current_engine.resolve_all(
                intermediate_urls,
                on_progress=on_engine_progress,
                cancel_event=self._cancel_event
            )

            if self._cancel_event.is_set():
                self.dispatch_event("pipeline:cancelled", {"message": "Extraction cancelled by user."})
                return

            resolved_urls = [r.direct_url for r in raw_results if r.status == "resolved" and r.direct_url]
            if not resolved_urls:
                raise RuntimeError("No direct download links could be resolved.")

            # Validation stage
            auto_val = self._settings.get("auto_validate", True)
            total_size_str = "0 B"
            total_size_bytes = 0

            if auto_val:
                self.dispatch_event("pipeline:status", {
                    "status": "validating",
                    "message": f"Sending 1-byte Range HTTP requests to verify {len(resolved_urls)} parts..."
                })

                def on_val_prog(curr, tot, p_url, p_size, is_ok):
                    self.dispatch_event("pipeline:val_update", {
                        "current": curr,
                        "total": tot,
                        "url": p_url,
                        "size": p_size,
                        "valid": is_ok
                    })

                val_summary = validator.validate_links(
                    resolved_urls,
                    max_workers=15,
                    on_progress=on_val_prog,
                    cancel_event=self._cancel_event
                )

                if val_summary:
                    total_size_str = val_summary.total_size_str
                    total_size_bytes = getattr(val_summary, 'total_bytes', 0)

            # Auto-save to SQLite History
            self._history_mgr.add_record(
                title=game_title,
                source_url=target_url,
                total_parts=len(resolved_urls),
                resolved_count=len(resolved_urls),
                total_size_bytes=total_size_bytes,
                total_size_str=total_size_str,
                urls=resolved_urls
            )

            # Auto-upload to Community Cloud if enabled
            if self._settings.get("community_auto_upload", True) and game_title not in ("Direct Repack", "FitGirl Repack"):
                try:
                    game_slug = scraper.extract_game_slug(target_url, game_title)
                    community.upload_game_record(
                        slug=game_slug,
                        title=game_title,
                        image_url=cover_image,
                        source_url=target_url,
                        urls=resolved_urls,
                        total_parts=len(resolved_urls),
                        total_size_str=total_size_str,
                        total_size_bytes=total_size_bytes,
                        firebase_url=self._settings.get("community_firebase_url")
                    )
                except Exception as up_err:
                    print(f"[Community Auto-Upload Warning] {up_err}")

            # Notify frontend completion
            self.dispatch_event("pipeline:complete", {
                "title": game_title,
                "image_url": cover_image,
                "source_url": target_url,
                "urls": resolved_urls,
                "parts_count": len(resolved_urls),
                "total_size_str": total_size_str,
                "total_size_bytes": total_size_bytes
            })

        except Exception as exc:
            self.dispatch_event("pipeline:error", {"message": str(exc)})
        finally:
            self._is_running = False
            self._current_engine = None

    def cancel_pipeline(self) -> Dict[str, Any]:
        """Signals cancellation of active extraction."""
        if not self._is_running:
            return {"status": "idle"}
        self._cancel_event.set()
        if self._current_engine:
            self._current_engine.cancel()
        self.dispatch_event("pipeline:status", {"status": "cancelling", "message": "Cancelling workers..."})
        return {"status": "cancelling"}

    # ==========================================
    # Integrations: JDownloader 2 & Export
    # ==========================================

    def push_to_jd2(self, urls: List[str], title: str, source_url: str = "") -> Dict[str, Any]:
        """Pushes direct URLs to JDownloader 2 via FlashGot API (port 9666) with folderwatch fallback."""
        if not urls:
            return {"success": False, "message": "No URLs to push."}
        port = self._settings.get("jd_port", 9666)
        success, msg = integrations.push_to_jdownloader(
            urls,
            package_name=title or "FitGirl Repack",
            source_url=source_url,
            port=port
        )
        return {"success": success, "message": msg}

    def export_urls(self, format_type: str, urls: List[str], title: str, total_size_str: str = "") -> Dict[str, Any]:
        """Exports URLs as .txt, .json, or .crawljob to Downloads folder."""
        if not urls:
            return {"success": False, "message": "No URLs to export."}

        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title or "repack").strip('_') or "repack"
        out_dir = utils.get_export_dir()
        os.makedirs(out_dir, exist_ok=True)

        if format_type == "txt":
            fp = os.path.join(out_dir, f"{safe_title}_direct_urls.txt")
            integrations.export_text(fp, urls, title)
        elif format_type == "json":
            fp = os.path.join(out_dir, f"{safe_title}.json")
            integrations.export_json(fp, title, "", urls, total_size_str)
        elif format_type == "crawljob":
            fp = os.path.join(out_dir, f"{safe_title}.crawljob")
            integrations.export_crawljob(fp, urls, title)
        else:
            return {"success": False, "message": f"Unsupported format: {format_type}"}

        utils.open_folder_cross_platform(out_dir)
        return {
            "success": True,
            "file_path": fp,
            "message": f"Saved {os.path.basename(fp)} to Downloads!"
        }

    def copy_to_clipboard(self, text: str) -> Dict[str, Any]:
        """Copies given text to the system clipboard safely."""
        try:
            pyperclip.copy(text or "")
            return {"success": True}
        except Exception as err:
            return {"success": False, "error": str(err)}

    # ==========================================
    # History SQLite Archive
    # ==========================================

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieves past extractions from SQLite."""
        try:
            records = self._history_mgr.get_records()
            return [
                {
                    "id": r["id"],
                    "game_title": r["title"],
                    "source_url": r.get("source_url", ""),
                    "parts_count": r.get("total_parts", 0),
                    "total_size": r.get("total_size_str", "0 B"),
                    "created_at": r.get("timestamp", "Recently"),
                    "resolved_links": r.get("urls", [])
                }
                for r in records
            ]
        except Exception as err:
            print(f"[History Error] {err}")
            return []

    def search_history(self, query: str) -> List[Dict[str, Any]]:
        """Searches SQLite history records by game title."""
        try:
            records = self._history_mgr.get_records(search_query=query)
            return [
                {
                    "id": r["id"],
                    "game_title": r["title"],
                    "source_url": r.get("source_url", ""),
                    "parts_count": r.get("total_parts", 0),
                    "total_size": r.get("total_size_str", "0 B"),
                    "created_at": r.get("timestamp", "Recently"),
                    "resolved_links": r.get("urls", [])
                }
                for r in records
            ]
        except Exception as err:
            return []

    def delete_history_item(self, record_id: int) -> Dict[str, Any]:
        """Deletes a record from SQLite history."""
        try:
            self._history_mgr.delete_record(int(record_id))
            return {"success": True}
        except Exception as err:
            return {"success": False, "error": str(err)}

    def clear_history(self) -> Dict[str, Any]:
        """Clears all records from SQLite history."""
        try:
            self._history_mgr.clear_history()
            return {"success": True}
        except Exception as err:
            return {"success": False, "error": str(err)}

    # ==========================================
    # Settings & Updater
    # ==========================================

    def get_settings(self) -> Dict[str, Any]:
        """Returns loaded user settings."""
        self._settings = utils.load_settings()
        return self._settings

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Saves user settings to settings.json."""
        self._settings.update(new_settings)
        utils.save_settings(self._settings)
        return {"success": True}

    def check_updates(self) -> Dict[str, Any]:
        """Checks GitHub Releases for new updates."""
        try:
            is_avail, rel_info, msg = updater.check_for_updates()
            return {
                "available": is_avail,
                "current_version": updater.CURRENT_VERSION,
                "release_info": rel_info or {},
                "message": msg
            }
        except Exception as err:
            return {"available": False, "error": str(err)}
