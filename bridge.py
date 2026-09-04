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
from datetime import datetime, timezone
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
        self._duplicate_wait_event = threading.Event()
        self._duplicate_action = None
        self._instance_id = f"proc_{os.getpid()}_{int(time.time()) % 10000}"
        self._update_available = False
        self._latest_release_info = None

    def bind_window(self, window):
        """Binds the active pywebview window reference."""
        self._window = window
        self._start_clipboard_sentinel()
        self._start_startup_updater_check()

    def _start_startup_updater_check(self):
        def _check():
            time.sleep(3.5)
            try:
                has_up, rel_info, msg = updater.check_for_updates()
                if has_up and rel_info:
                    self._update_available = True
                    self._latest_release_info = rel_info
                    self.dispatch_event("updater:available", {
                        "release_info": rel_info,
                        "is_frozen": updater.is_running_frozen(),
                        "current_version": updater.CURRENT_VERSION
                    })
            except Exception as e:
                print(f"[Startup Updater Check] {e}")

        threading.Thread(target=_check, daemon=True).start()

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

    def check_existing_game(self, url_or_slug: str) -> Dict[str, Any]:
        """
        Checks if a game already exists in Firebase Community Cloud or SQLite History.
        Returns match status and record details.
        """
        clean_input = (url_or_slug or "").strip()
        if not clean_input:
            return {"exists": False}

        # 1. Derive slug candidates
        slug = ""
        if "http://" in clean_input or "https://" in clean_input:
            slug = scraper.extract_game_slug(clean_input)
        else:
            slug = community.sanitize_slug(clean_input)
        fallback_slug = community.generate_game_slug(clean_input)

        # 2. Check Firebase Community Cache
        fb_url = self._settings.get("community_firebase_url")
        comm_rec = None

        cached_list = community.get_community_games(fb_url, force_refresh=False)
        clean_lower = clean_input.lower()
        for item in cached_list:
            item_slug = item.get("slug", "")
            item_title = item.get("title", "").lower()
            item_src = item.get("source_url", "").lower()

            if slug and (slug == item_slug or slug in item_src):
                comm_rec = item
                break
            if clean_input and (clean_input == item.get("source_url") or (len(clean_lower) >= 4 and clean_lower in item_title)):
                comm_rec = item
                break
            if fallback_slug and (fallback_slug == item_slug or fallback_slug in item_src):
                comm_rec = item
                break

        if not comm_rec and slug:
            single = community.get_game_by_slug(slug, fb_url)
            if single and single.get("title"):
                comm_rec = single

        if comm_rec:
            target_slug = comm_rec.get("slug") or slug
            urls = community.get_game_urls(target_slug, fb_url)

            # Check if record is expired (> 24h old or marked 'expired')
            iso_ts = comm_rec.get("timestamp_utc", "")
            freshness = comm_rec.get("freshness", "fresh")
            is_expired = freshness == "expired"
            if iso_ts and not is_expired:
                try:
                    dt_utc = community.parse_iso_timestamp(iso_ts)
                    age_hours = (datetime.now(timezone.utc) - dt_utc).total_seconds() / 3600.0
                    if age_hours >= 24.0:
                        is_expired = True
                        freshness = "expired"
                except Exception:
                    pass

            return {
                "exists": True,
                "source": "community",
                "is_expired": is_expired,
                "record": {
                    "slug": target_slug,
                    "title": comm_rec.get("title", "FitGirl Repack"),
                    "image_url": comm_rec.get("image_url", ""),
                    "source_url": comm_rec.get("source_url", clean_input),
                    "total_parts": comm_rec.get("total_parts", len(urls)),
                    "total_size_str": comm_rec.get("total_size_str", "0 B"),
                    "age_str": comm_rec.get("age_str", "Recently"),
                    "timestamp_utc": comm_rec.get("timestamp_utc", ""),
                    "freshness": freshness,
                    "is_expired": is_expired,
                    "used_count": comm_rec.get("used_count", 0),
                    "urls": urls
                }
            }

        # 3. Check SQLite Local History
        try:
            hist_records = self._history_mgr.get_records(limit=200)
            matched_hist = None
            for r in hist_records:
                src = (r.get("source_url") or "").strip()
                title = (r.get("title") or "").strip()
                if clean_input and (clean_input == src or (src and src in clean_input)):
                    matched_hist = r
                    break
                if slug and (slug in community.generate_game_slug(src, title)):
                    matched_hist = r
                    break
                if clean_input.lower() in title.lower() and len(clean_input) > 4:
                    matched_hist = r
                    break

            if matched_hist:
                derived_slug = community.generate_game_slug(matched_hist.get("source_url", ""), matched_hist.get("title", ""))
                hist_ts = matched_hist.get("timestamp", "")
                is_expired = False
                try:
                    dt_hist = datetime.strptime(hist_ts, "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - dt_hist).total_seconds() >= 86400:
                        is_expired = True
                except Exception:
                    pass

                return {
                    "exists": True,
                    "source": "history",
                    "is_expired": is_expired,
                    "record": {
                        "slug": derived_slug,
                        "title": matched_hist.get("title", "FitGirl Repack"),
                        "image_url": "",
                        "source_url": matched_hist.get("source_url", clean_input),
                        "total_parts": matched_hist.get("total_parts", len(matched_hist.get("urls", []))),
                        "total_size_str": matched_hist.get("total_size_str", "0 B"),
                        "age_str": hist_ts or "Local History",
                        "timestamp_utc": hist_ts,
                        "freshness": "expired" if is_expired else "fresh",
                        "is_expired": is_expired,
                        "used_count": 0,
                        "urls": matched_hist.get("urls", [])
                    }
                }
        except Exception as e:
            print(f"[Bridge Check Error] SQLite check failed: {e}")

        return {"exists": False}

    def decide_duplicate(self, action: str) -> Dict[str, Any]:
        """Handles user response to duplicate detected modal: 'instant' or 'fresh'."""
        self._duplicate_action = action
        if hasattr(self, "_duplicate_wait_event") and self._duplicate_wait_event:
            self._duplicate_wait_event.set()
        return {"status": "ok", "action": action}

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
        sid = (session_id or "").strip() or self._instance_id
        active = community.ping_presence(sid, updater.CURRENT_VERSION, fb_url)
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

            def to_vibrant(h, l, s, min_l=0.66, max_l=0.76, min_s=0.82):
                target_l = max(min_l, min(max_l, max(l, 0.68)))
                target_s = max(min_s, min(1.0, max(s * 1.3, 0.85)))
                rf, gf, bf = colorsys.hls_to_rgb(h, target_l, target_s)
                return (int(round(rf * 255)), int(round(gf * 255)), int(round(bf * 255)))

            scored = []
            for r, g, b in pixels:
                h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
                # Filter out pure whites, deep blacks, and muddy greys
                if 0.10 < l < 0.94 and s > 0.16:
                    score = (s * 2.5) + (1.0 - abs(l - 0.50))
                    scored.append((score, (r, g, b), h, l, s))

            if scored:
                scored.sort(key=lambda item: item[0], reverse=True)
                best = scored[0]
                primary_h, primary_l, primary_s = best[2], best[3], best[4]
                primary_rgb = to_vibrant(primary_h, primary_l, primary_s)

                secondary_rgb = None
                for _, rgb, h, l, s in scored[1:]:
                    hue_diff = abs(h - primary_h)
                    if hue_diff > 0.5:
                        hue_diff = 1.0 - hue_diff
                    if hue_diff > 0.10:
                        secondary_rgb = to_vibrant(h, l, s)
                        break

                if not secondary_rgb:
                    sec_h = (primary_h + 0.12) % 1.0
                    secondary_rgb = to_vibrant(sec_h, 0.70, 0.88)

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
        r_f, g_f, b_f = [int(round(x * 255)) for x in colorsys.hls_to_rgb(h_val / 360.0, 0.70, 0.88)]
        s_f, s_g, s_b = [int(round(x * 255)) for x in colorsys.hls_to_rgb(((h_val + 45) % 360) / 360.0, 0.68, 0.85)]
        fallback = {
            "primary": [r_f, g_f, b_f],
            "secondary": [s_f, s_g, s_b],
            "glow": f"rgba({r_f}, {g_f}, {b_f}, 0.35)"
        }
        self._palette_cache[image_url] = fallback
        return fallback

    # ==========================================
    # Extraction Pipeline
    # ==========================================

    def start_extraction(self, url: str, concurrency: int = None, force_fresh: bool = False) -> Dict[str, Any]:
        """Starts the asynchronous link extraction pipeline."""
        if self._is_running:
            return {"status": "error", "message": "An extraction is already in progress."}

        target_url = (url or "").strip()
        if not target_url:
            return {"status": "error", "message": "Empty URL provided."}

        self._cancel_event.clear()
        self._duplicate_wait_event.clear()
        self._duplicate_action = None
        self._is_running = True
        concurrency = concurrency or self._settings.get("concurrency", 3)

        threading.Thread(
            target=self._run_extraction_pipeline,
            args=(target_url, concurrency, force_fresh),
            daemon=True
        ).start()

        return {"status": "started", "target_url": target_url}

    def _run_extraction_pipeline(self, target_url: str, concurrency: int, force_fresh: bool = False):
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

                # Mid-scrape duplicate check for pastebin
                if not force_fresh:
                    discovered_slug = scraper.extract_game_slug(target_url, game_title)
                    dup_check = self.check_existing_game(discovered_slug)
                    if not dup_check.get("exists"):
                        dup_check = self.check_existing_game(game_title)
                    if not dup_check.get("exists"):
                        dup_check = self.check_existing_game(target_url)

                    if dup_check.get("exists"):
                        if dup_check.get("is_expired"):
                            rec_age = dup_check.get("record", {}).get("age_str", "outdated")
                            self.dispatch_event("pipeline:status", {
                                "status": "resolving",
                                "message": f"Cached links are outdated ({rec_age}). Resolving fresh mirrors to update database..."
                            })
                        else:
                            self.dispatch_event("pipeline:duplicate_detected", dup_check.get("record"))
                            self._duplicate_wait_event.wait(timeout=60.0)
                            if self._duplicate_action == "instant":
                                self.dispatch_event("pipeline:cancelled", {"message": "Switched to Instant Cached Links."})
                                return
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

                def on_val_prog(*args):
                    if len(args) == 3:
                        curr, tot, item = args
                        p_url = getattr(item, 'url', '') if item else ""
                        p_size = getattr(item, 'content_length_str', 'Unknown') if item else "Unknown"
                        is_ok = getattr(item, 'is_valid', False) if item else False
                        idx = getattr(item, 'index', None) if item else None
                    elif len(args) >= 5:
                        curr, tot, p_url, p_size, is_ok = args[:5]
                        idx = None
                    else:
                        return
                    self.dispatch_event("pipeline:val_update", {
                        "current": curr,
                        "total": tot,
                        "url": p_url,
                        "size": p_size,
                        "valid": is_ok,
                        "index": idx
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
                    game_slug = community.generate_game_slug(target_url, game_title)
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
                    self.dispatch_event("community:feed_updated", {"slug": game_slug, "title": game_title})
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
        if hasattr(self, "_duplicate_wait_event") and self._duplicate_wait_event:
            self._duplicate_wait_event.set()
        if self._current_engine and hasattr(self._current_engine, "cancel"):
            try:
                self._current_engine.cancel()
            except Exception:
                pass
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

    # ==========================================
    # Auto-Updater Endpoints
    # ==========================================

    def get_changelogs(self) -> List[Dict[str, Any]]:
        """Returns structured changelogs for all releases."""
        return updater.get_all_version_changelogs()

    def get_update_status(self) -> Dict[str, Any]:
        """Returns currently known update availability and release information."""
        return {
            "has_update": getattr(self, "_update_available", False),
            "release_info": getattr(self, "_latest_release_info", None),
            "current_version": updater.CURRENT_VERSION,
            "is_frozen": updater.is_running_frozen()
        }

    def check_for_updates(self, force_available: bool = False) -> Dict[str, Any]:
        """Check GitHub Releases for newer version of the application."""
        try:
            has_update, release_info, message = updater.check_for_updates(force_available=force_available)
            self._update_available = has_update
            self._latest_release_info = release_info if has_update else None
            return {
                "has_update": has_update,
                "available": has_update,
                "release_info": release_info or {},
                "message": message,
                "is_frozen": updater.is_running_frozen(),
                "current_version": updater.CURRENT_VERSION
            }
        except Exception as err:
            return {
                "has_update": False,
                "available": False,
                "release_info": None,
                "message": f"Check failed: {err}",
                "is_frozen": updater.is_running_frozen(),
                "current_version": updater.CURRENT_VERSION
            }

    def check_updates(self) -> Dict[str, Any]:
        """Backward-compatible alias for check_for_updates."""
        return self.check_for_updates()

    def start_update_download(self, download_url: str = "") -> Dict[str, Any]:
        """Starts background download of update binary with live progress events."""
        if hasattr(self, "_update_downloading") and self._update_downloading:
            return {"status": "downloading", "message": "Download already in progress."}

        target_url = download_url
        if not target_url:
            _, rel, _ = updater.check_for_updates()
            if rel and rel.get("download_url"):
                target_url = rel["download_url"]
            else:
                return {"status": "error", "message": "No download URL found in release."}

        self._update_cancel_event = threading.Event()
        self._update_downloading = True

        def _download_thread():
            def _prog(dl, tot, pct, speed):
                spd_str = f"{speed / 1048576:.1f} MB/s" if speed > 0 else "Calculating..."
                dl_str = f"{dl / 1048576:.1f} MB"
                tot_str = f"{tot / 1048576:.1f} MB" if tot > 0 else "Unknown"
                self.dispatch_event("updater:progress", {
                    "downloaded": dl,
                    "total": tot,
                    "percent": round(pct, 1),
                    "speed_str": spd_str,
                    "downloaded_str": dl_str,
                    "total_str": tot_str
                })

            try:
                target_file = updater.download_update(
                    target_url,
                    progress_callback=_prog,
                    cancel_event=self._update_cancel_event
                )
                self._downloaded_update_path = target_file
                self._update_downloading = False
                file_size = os.path.getsize(target_file) if os.path.exists(target_file) else 0
                self.dispatch_event("updater:download_complete", {
                    "file_path": target_file,
                    "is_frozen": updater.is_running_frozen(),
                    "file_size": file_size,
                    "file_size_str": f"{file_size / 1048576:.1f} MB"
                })
            except Exception as ex:
                self._update_downloading = False
                if "cancelled" in str(ex).lower():
                    self.dispatch_event("updater:download_cancelled", {})
                else:
                    self.dispatch_event("updater:error", {"error": str(ex)})

        threading.Thread(target=_download_thread, daemon=True).start()
        return {"status": "started"}

    def cancel_update_download(self) -> Dict[str, Any]:
        """Cancels an in-progress update download."""
        if hasattr(self, "_update_cancel_event") and self._update_cancel_event:
            self._update_cancel_event.set()
        self._update_downloading = False
        return {"status": "cancelled"}

    def apply_update_and_restart(self) -> Dict[str, Any]:
        """Applies downloaded binary and restarts application in frozen mode."""
        target_path = getattr(self, "_downloaded_update_path", None)
        if not target_path or not os.path.exists(target_path):
            updates_dir = os.path.join(utils.get_app_data_dir(), "updates")
            target_path = os.path.join(updates_dir, "LinkExtractor_update.exe")

        if not os.path.exists(target_path):
            return {"status": "error", "message": "No downloaded update file found."}

        applied = updater.apply_update_and_restart(target_path)
        if applied:
            threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0)), daemon=True).start()
            return {"status": "restarting"}
        else:
            return {"status": "not_frozen", "message": "Application is running in Python dev mode."}

    def launch_downloaded_binary(self) -> Dict[str, Any]:
        """Launches the downloaded standalone executable in development mode."""
        target_path = getattr(self, "_downloaded_update_path", None)
        if not target_path or not os.path.exists(target_path):
            updates_dir = os.path.join(utils.get_app_data_dir(), "updates")
            target_path = os.path.join(updates_dir, "LinkExtractor_update.exe")

        if os.path.exists(target_path):
            ok = updater.launch_downloaded_executable(target_path)
            return {"status": "launched" if ok else "error"}
        return {"status": "not_found", "message": "Downloaded binary not found."}

    def open_updates_folder(self) -> Dict[str, Any]:
        """Reveals the updates folder in Windows Explorer."""
        folder = updater.open_updates_folder()
        return {"status": "opened", "path": folder}
