"""Ambient colors for the Living Canvas, taken from a game's cover art.

Cover links come from the shared database, so they are checked before and during the
download: this code never fetches anything on this machine or a private network.
"""

import colorsys
import http.client
import io
import logging
import threading
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

import links

log = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
DEFAULT_PALETTE = {"primary": [16, 185, 129], "secondary": [6, 182, 212], "glow": "rgba(16, 185, 129, 0.35)"}

_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()


class _PublicRedirectsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not links.is_public_http_url(newurl):
            raise OSError("Refused a redirect to a private address")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_PublicRedirectsOnly)


def extract_game_palette(image_url: str) -> Dict[str, Any]:
    """The cover's vibrant primary and secondary colors, or a stable fallback if it cannot be read."""
    if not isinstance(image_url, str) or not image_url:
        return dict(DEFAULT_PALETTE)
    with _cache_lock:
        if image_url in _cache:
            return _cache[image_url]

    result = _palette_from_cover(image_url) or _fallback_palette(image_url)
    with _cache_lock:
        _cache[image_url] = result
    return result


def _palette_from_cover(image_url: str) -> Optional[Dict[str, Any]]:
    if not links.is_public_http_url(image_url):
        return None
    request = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with _opener.open(request, timeout=5.0) as response:
            data = response.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            return None
        image = Image.open(io.BytesIO(data)).convert("RGB").resize((48, 48))
    except (OSError, ValueError, http.client.HTTPException, Image.DecompressionBombError) as error:
        log.debug("Could not read cover art: %s", error)
        return None
    pixels: List[Tuple[int, int, int]] = [image.getpixel((x, y)) for y in range(48) for x in range(48)]  # type: ignore[misc]
    return _palette_from_pixels(pixels)


def _vibrant(hue: float, lightness: float, saturation: float) -> Tuple[int, int, int]:
    target_l = max(0.66, min(0.76, max(lightness, 0.68)))
    target_s = max(0.82, min(1.0, max(saturation * 1.3, 0.85)))
    red, green, blue = colorsys.hls_to_rgb(hue, target_l, target_s)
    return int(round(red * 255)), int(round(green * 255)), int(round(blue * 255))


def _palette_from_pixels(pixels: List[Tuple[int, int, int]]) -> Optional[Dict[str, Any]]:
    scored = []
    for red, green, blue in pixels:
        hue, lightness, saturation = colorsys.rgb_to_hls(red / 255.0, green / 255.0, blue / 255.0)
        # Skip pure whites, deep blacks and muddy greys.
        if 0.10 < lightness < 0.94 and saturation > 0.16:
            scored.append(((saturation * 2.5) + (1.0 - abs(lightness - 0.50)), hue, lightness, saturation))
    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    _, primary_h, primary_l, primary_s = scored[0]
    primary = _vibrant(primary_h, primary_l, primary_s)

    secondary = None
    for _, hue, lightness, saturation in scored[1:]:
        difference = abs(hue - primary_h)
        if difference > 0.5:
            difference = 1.0 - difference
        if difference > 0.10:
            secondary = _vibrant(hue, lightness, saturation)
            break
    if secondary is None:
        secondary = _vibrant((primary_h + 0.12) % 1.0, 0.70, 0.88)

    return {
        "primary": list(primary),
        "secondary": list(secondary),
        "glow": f"rgba({primary[0]}, {primary[1]}, {primary[2]}, 0.4)",
    }


def _fallback_palette(image_url: str) -> Dict[str, Any]:
    """A color derived from the link, so one game keeps the same look when its cover is unavailable."""
    hue = sum(ord(char) for char in image_url) % 360
    primary = [int(round(value * 255)) for value in colorsys.hls_to_rgb(hue / 360.0, 0.70, 0.88)]
    secondary = [int(round(value * 255)) for value in colorsys.hls_to_rgb(((hue + 45) % 360) / 360.0, 0.68, 0.85)]
    return {
        "primary": primary,
        "secondary": secondary,
        "glow": f"rgba({primary[0]}, {primary[1]}, {primary[2]}, 0.35)",
    }
