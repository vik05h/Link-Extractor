"""The extraction pipeline, from a pasted link to verified direct links.

This module owns the rule for what happens to a finished run:

- cancelled: nothing is saved, published or reported as done.
- partial: some parts are missing. Saved locally and flagged, never published.
- complete: every part is there. Published only if every link was also verified,
  the user allows sharing, and the record has a real game title.

Everything outside the process (browser, network, database) arrives through
PipelinePorts, so the rule can be tested without any of it.
"""

import asyncio
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import game_records
import links
import scraper
import validator

log = logging.getLogger(__name__)

COMPLETE = "complete"
PARTIAL = "partial"
CANCELLED = "cancelled"
FAILED = "failed"

_PUBLISHABLE_TYPES = {"fitgirl_game_page", "fitgirl_pastebin"}


@dataclass
class PipelinePorts:
    make_engine: Callable[[int], Any]
    validate_links: Callable[..., validator.ValidationSummary]
    fetch_game_page: Callable[[str], Tuple[List[Dict[str, str]], str, str]]
    resolve_paste_metadata: Callable[[str, List[str]], Dict[str, str]]
    publish: Callable[..., Tuple[bool, str]]
    find_existing: Callable[[str], Dict[str, Any]]
    ask_duplicate: Callable[[Dict[str, Any]], Optional[str]]


@dataclass
class ExtractionResult:
    status: str
    title: str = ""
    image_url: str = ""
    source_url: str = ""
    urls: List[str] = field(default_factory=list)
    expected_parts: int = 0
    verified: bool = False
    message: str = ""


@dataclass
class _Job:
    url_type: str
    title: str
    image_url: str
    source_url: str
    parts: List[str]


class _Stop(Exception):
    """Ends the run as cancelled."""

    def __init__(self, message: str, reason: str = "user") -> None:
        super().__init__(message)
        self.message = message
        self.reason = reason


class _ExtractionError(Exception):
    """Ends the run with a message for the user."""


class ExtractionPipeline:
    def __init__(self, ports: PipelinePorts, history: Any, settings: Dict[str, Any], emit: Callable[..., None]) -> None:
        self._ports = ports
        self._history = history
        self._settings = settings
        self._emit = emit

    def run(
        self,
        target_url: str,
        concurrency: int,
        force_fresh: bool = False,
        cancel_event: Optional[threading.Event] = None,
    ) -> ExtractionResult:
        """Run one extraction to its end and report the outcome through events."""
        cancel = cancel_event or threading.Event()
        try:
            return self._run(target_url, concurrency, force_fresh, cancel)
        except _Stop as stop:
            self._emit("pipeline:cancelled", {"message": stop.message, "reason": stop.reason})
            return ExtractionResult(CANCELLED, message=stop.message)
        except _ExtractionError as error:
            self._emit("pipeline:error", {"message": str(error)})
            return ExtractionResult(FAILED, message=str(error))
        except Exception as error:
            log.exception("Extraction failed")
            self._emit("pipeline:error", {"message": str(error)})
            return ExtractionResult(FAILED, message=str(error))

    def _status(self, status: str, message: str) -> None:
        self._emit("pipeline:status", {"status": status, "message": message})

    @staticmethod
    def _check_cancel(cancel: threading.Event) -> None:
        if cancel.is_set():
            raise _Stop("Extraction cancelled by user.")

    def _run(self, target_url: str, concurrency: int, force_fresh: bool, cancel: threading.Event) -> ExtractionResult:
        self._status("starting", "Inspecting URL...")
        url_type = scraper.detect_url_type(target_url)
        if url_type == "unknown":
            raise _ExtractionError(_unsupported_message(target_url))

        job, engine = self._prepare(url_type, target_url, concurrency, force_fresh, cancel)
        self._check_cancel(cancel)

        resolved, failed_parts = self._resolve(job, engine, concurrency, cancel)
        self._check_cancel(cancel)

        urls, size_str, size_bytes, unverified, validated = self._validate(resolved, failed_parts, cancel)
        self._check_cancel(cancel)

        expected = len(job.parts)
        status = COMPLETE if len(urls) == expected else PARTIAL
        verified = validated and unverified == 0

        self._save_to_history(job, expected, urls, size_bytes, size_str)
        published, publish_error = self._publish(job, status, verified, urls, size_str, size_bytes)

        self._emit("pipeline:complete", {
            "status": status,
            "verified": verified,
            "validated": validated,
            "unverified_count": unverified,
            "title": job.title,
            "image_url": job.image_url,
            "source_url": job.source_url,
            "urls": urls,
            "parts_count": len(urls),
            "expected_parts": expected,
            "failed_parts": failed_parts,
            "total_size_str": size_str,
            "total_size_bytes": size_bytes,
            "published": published,
            "publish_error": publish_error,
        })
        return ExtractionResult(status, job.title, job.image_url, job.source_url, urls, expected, verified)

    def _prepare(
        self, url_type: str, target_url: str, concurrency: int, force_fresh: bool, cancel: threading.Event
    ) -> Tuple[_Job, Any]:
        """Turn the user's input into a list of part pages, opening a pastebin if needed."""
        target = target_url.strip()
        if url_type == "raw_links":
            parts = scraper.extract_hoster_links(target)
            return self._direct_job(url_type, parts, "\n".join(parts)), self._ports.make_engine(concurrency)

        if "://" not in target:
            target = f"https://{target}"
        if url_type == "fuckingfast_direct":
            return self._direct_job(url_type, [target], target), self._ports.make_engine(concurrency)
        if url_type == "fitgirl_game_page":
            return self._prepare_game_page(target, concurrency, cancel)
        return self._prepare_pastebin(target, concurrency, force_fresh, cancel)

    def _direct_job(self, url_type: str, parts: List[str], source_url: str) -> _Job:
        name = scraper.extract_game_info_from_part_urls(parts)[0]
        title = "Direct Repack" if game_records.is_generic_title(name) else name
        self._emit("pipeline:game_meta", {"title": title, "image_url": "", "parts_count": len(parts)})
        return _Job(url_type, title, "", source_url, parts)

    def _prepare_game_page(self, target: str, concurrency: int, cancel: threading.Event) -> Tuple[_Job, Any]:
        self._status("scraping", "Parsing FitGirl Game Page...")
        pastebins, title, cover = self._ports.fetch_game_page(target)
        chosen = [paste for paste in pastebins if paste.get("hoster") == "FuckingFast"] or pastebins[:1]
        if not chosen:
            raise _ExtractionError("No FuckingFast or compatible pastebin mirrors found on game page.")
        self._check_cancel(cancel)

        self._status("scraping", "Decrypting Pastebin links...")
        engine = self._ports.make_engine(concurrency)
        parts = asyncio.run(engine.fetch_pastebin_links(chosen[0]["url"]))
        if not parts:
            raise _ExtractionError("No direct download parts found inside pastebin.")

        self._emit("pipeline:game_meta", {"title": title, "image_url": cover, "parts_count": len(parts)})
        return _Job("fitgirl_game_page", title, cover, target, parts), engine

    def _prepare_pastebin(self, target: str, concurrency: int, force_fresh: bool, cancel: threading.Event) -> Tuple[_Job, Any]:
        self._status("scraping", "Decrypting Pastebin page...")
        engine = self._ports.make_engine(concurrency)
        parts = asyncio.run(engine.fetch_pastebin_links(target))
        if not parts:
            raise _ExtractionError("No direct download parts found inside pastebin.")
        self._check_cancel(cancel)

        self._status("scraping", "Resolving Game Intelligence & Artwork...")
        meta = self._ports.resolve_paste_metadata(target, parts)
        title = meta.get("title") or "FitGirl Pastebin Repack"
        cover = meta.get("image_url") or ""
        source_url = meta.get("source_url") or target
        self._emit("pipeline:game_meta", {"title": title, "image_url": cover, "parts_count": len(parts)})

        if not force_fresh:
            self._handle_existing_copy(title, source_url, cancel)
        return _Job("fitgirl_pastebin", title, cover, source_url, parts), engine

    def _handle_existing_copy(self, title: str, source_url: str, cancel: threading.Event) -> None:
        """A pastebin only reveals its game partway through, so check for a cached copy here."""
        slug = game_records.generate_game_slug(source_url, title)
        found: Dict[str, Any] = {"exists": False}
        for query in (slug, title, source_url):
            found = self._ports.find_existing(query)
            if found.get("exists"):
                break
        if not found.get("exists"):
            return

        record = found.get("record") or {}
        if found.get("is_expired"):
            age = record.get("age_str", "outdated")
            self._status("resolving", f"Cached links are outdated ({age}). Resolving fresh mirrors to update database...")
            return

        choice = self._ports.ask_duplicate(record)
        self._check_cancel(cancel)
        if choice == "instant":
            raise _Stop("Switched to Instant Cached Links.", reason="instant")
        if choice == "cancel":
            raise _Stop("Extraction cancelled by user.")

    def _resolve(self, job: _Job, engine: Any, concurrency: int, cancel: threading.Event) -> Tuple[List[str], List[Dict[str, str]]]:
        total = len(job.parts)
        self._status("resolving", f"Bypassing Cloudflare Turnstile across {total} parts ({concurrency} tabs)...")
        self._emit("pipeline:init_parts", [
            {"index": index, "url": url, "filename": links.part_name(url), "status": "pending", "size": "Pending"}
            for index, url in enumerate(job.parts, 1)
        ])

        def on_progress(resolved_so_far, total_count, avg_speed, eta, active_workers, part_name, direct_url, status):
            self._emit("pipeline:part_update", {
                "resolved_so_far": resolved_so_far,
                "total": total_count,
                "avg_speed": f"{avg_speed:.1f}s/part",
                "eta": f"~{int(eta)}s",
                "part_name": part_name,
                "direct_url": direct_url or "",
                "status": status,
            })

        def on_log(message: str) -> None:
            self._emit("pipeline:log", {"message": message})

        results = engine.resolve_all(job.parts, on_progress=on_progress, on_log=on_log, cancel_event=cancel)
        self._check_cancel(cancel)

        resolved = [item.direct_url for item in results if item.status == "resolved" and item.direct_url]
        failed = [
            {"filename": item.part_name, "reason": "Could not be resolved after retries"}
            for item in results
            if not (item.status == "resolved" and item.direct_url)
        ]
        if not resolved:
            raise _ExtractionError("No direct download links could be resolved.")
        return resolved, failed

    def _validate(
        self, resolved: List[str], failed_parts: List[Dict[str, str]], cancel: threading.Event
    ) -> Tuple[List[str], str, int, int, bool]:
        """Returns (usable urls, size text, size bytes, links we could not check, whether checks ran)."""
        if not self._settings.get("auto_validate", True):
            return resolved, "0 B", 0, 0, False

        self._status("validating", f"Sending 1-byte Range HTTP requests to verify {len(resolved)} parts...")

        def on_progress(current: int, total: int, item: validator.ValidatedLink) -> None:
            self._emit("pipeline:val_update", {
                "current": current,
                "total": total,
                "url": item.url,
                "size": item.content_length_str,
                "valid": item.is_valid,
                "verdict": item.verdict,
                "error": item.error or "",
            })

        summary = self._ports.validate_links(resolved, max_workers=15, on_progress=on_progress, cancel_event=cancel)
        if summary.cancelled:
            raise _Stop("Extraction cancelled by user.")

        dead = {link.url: link for link in summary.links if link.verdict == validator.DEAD}
        for url, link in dead.items():
            failed_parts.append({"filename": links.part_name(url), "reason": link.error or "The link is dead"})

        usable = [url for url in resolved if url not in dead]
        if not usable:
            raise _ExtractionError("None of the resolved links passed the check. Please try again later.")
        return usable, summary.total_size_str, summary.total_bytes, summary.unknown_count, True

    def _save_to_history(self, job: _Job, expected: int, urls: List[str], size_bytes: int, size_str: str) -> None:
        try:
            self._history.add_record(
                title=job.title,
                source_url=job.source_url,
                total_parts=expected,
                resolved_count=len(urls),
                total_size_bytes=size_bytes,
                total_size_str=size_str,
                urls=urls,
            )
        except sqlite3.Error:
            log.exception("Could not save the extraction to history")

    def _publish(
        self, job: _Job, status: str, verified: bool, urls: List[str], size_str: str, size_bytes: int
    ) -> Tuple[bool, str]:
        """Share the links with the community if this run qualifies. Returns (published, error)."""
        allowed = (
            status == COMPLETE
            and verified
            and job.url_type in _PUBLISHABLE_TYPES
            and self._settings.get("community_auto_upload", True)
            and not game_records.is_generic_title(job.title)
        )
        if not allowed:
            return False, ""

        slug = game_records.generate_game_slug(job.source_url, job.title)
        try:
            ok, message = self._ports.publish(
                slug=slug,
                title=job.title,
                image_url=job.image_url,
                source_url=job.source_url,
                urls=urls,
                total_parts=len(urls),
                total_size_str=size_str,
                total_size_bytes=size_bytes,
            )
        except Exception as error:
            log.exception("Publishing failed")
            return False, str(error)

        if not ok:
            return False, message
        self._emit("community:feed_updated", {"slug": slug, "title": job.title})
        return True, ""


def _unsupported_message(target_url: str) -> str:
    urls = links.extract_urls(target_url) or [f"https://{target_url.strip()}"]
    if all(links.is_direct_link(url) for url in urls):
        return "These are already direct download links, so there is nothing to resolve."
    return "This link is not supported. Paste a FitGirl game page, a FitGirl pastebin, or a FuckingFast link."
