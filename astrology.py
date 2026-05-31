"""
Astrological chart generation.

Wraps Kerykeion (Swiss Ephemeris) and timezonefinder so the rest of the
app can call a single `generate_chart(...)` and get back an SVG + a
structured JSON-serializable dict.

Charts are cached at the call-site via `chart_cache` (see database
layer); the `compute_input_hash` here is what determines when a cached
chart is stale.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from typing import Optional

from kerykeion import AstrologicalSubject, KerykeionChartSVG
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)


# Display-name -> Kerykeion single-letter code. The display strings here
# are what's shown in the Settings dropdown and stored in app_settings.
# Bump when the SVG post-processing or output schema changes; folded
# into compute_input_hash so existing cached charts regenerate next
# view rather than needing a manual Regenerate click.
CHART_RENDERER_VERSION = 3

HOUSE_SYSTEM_CODES = {
    'Placidus': 'P',
    'Whole Sign': 'W',
    'Equal': 'E',
    'Koch': 'K',
    'Regiomontanus': 'R',
    'Campanus': 'C',
    'Porphyry': 'O',
    'Morinus': 'M',
    'Alcabitius': 'B',
    'Topocentric': 'T',
}
DEFAULT_HOUSE_SYSTEM = 'Whole Sign'

# Single shared TimezoneFinder; constructing one loads ~50MB of polygons
# into memory, so we don't want to do that per-call.
_tz_finder: Optional[TimezoneFinder] = None


def _get_tz_finder() -> TimezoneFinder:
    global _tz_finder
    if _tz_finder is None:
        _tz_finder = TimezoneFinder()
    return _tz_finder


def resolve_timezone(lat: float, lon: float) -> str:
    """Return an IANA timezone name for the given coordinates.

    Falls back to UTC if the point is outside the timezone polygon set
    (e.g. open ocean). Callers should still treat the chart as best-effort
    in that edge case.
    """
    tz = _get_tz_finder().timezone_at(lat=lat, lng=lon)
    return tz or 'UTC'


def compute_input_hash(
    date_iso: str,
    time_iso: Optional[str],
    lat: float,
    lon: float,
    house_system: str,
    solar_chart: bool = False,
    place_label: str = '',
    chart_label: str = 'Birth Chart',
) -> str:
    """Deterministic hash of every input that affects chart output.

    Used by the cache layer: when the current hash doesn't match the
    stored one, the chart is regenerated. `solar_chart` is included so
    flipping the "allow solar chart" setting properly invalidates.
    `place_label` doesn't affect calculation but is baked into the SVG,
    so it's part of the hash too.
    """
    payload = json.dumps(
        {
            'date': date_iso,
            'time': time_iso or '',
            'lat': round(float(lat), 6),
            'lon': round(float(lon), 6),
            'house_system': house_system,
            'solar': bool(solar_chart),
            'place': place_label or '',
            'chart_label': chart_label or 'Birth Chart',
            'renderer': CHART_RENDERER_VERSION,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _parse_date(date_iso: str) -> tuple[int, int, int]:
    """Accepts 'YYYY-MM-DD' (the format SQLite stores DATE fields as)."""
    d = datetime.fromisoformat(date_iso[:10])
    return d.year, d.month, d.day


def _parse_time(time_iso: Optional[str]) -> tuple[int, int]:
    """Accepts 'HH:MM[:SS]' or 'HH:MM:SS.ffffff'. Returns 12:00 if None
    (caller decides whether that's a solar-chart fallback or refusal)."""
    if not time_iso:
        return 12, 0
    parts = time_iso.split(':')
    return int(parts[0]), int(parts[1])


def generate_chart(
    name: str,
    date_iso: str,
    time_iso: Optional[str],
    lat: float,
    lon: float,
    house_system: str,
    solar_chart_fallback: bool = False,
    place_label: str = '',
    chart_label: str = 'Birth Chart',
) -> dict:
    """
    Generate a natal/event chart.

    `place_label` is a free-text string passed to Kerykeion as the `city`
    field — purely a display label on the rendered SVG, since lat/lon
    drive the actual calculation. When empty, Kerykeion defaults to
    "Greenwich, GB" which is misleading; callers should pass the user's
    own place name (e.g. "Brooklyn, New York, US").

    Returns a dict:
        {
          'svg': '<svg>...',
          'data': {... kerykeion model_dump ...},
          'house_system': 'Placidus',
          'solar_chart': bool,
          'timezone': 'America/Los_Angeles',
        }

    Raises ValueError if time is missing and solar_chart_fallback is False.
    """
    if not time_iso and not solar_chart_fallback:
        raise ValueError(
            'birth_time missing and solar chart fallback disabled in settings'
        )

    year, month, day = _parse_date(date_iso)
    hour, minute = _parse_time(time_iso)
    tz_str = resolve_timezone(lat, lon)
    code = HOUSE_SYSTEM_CODES.get(house_system, HOUSE_SYSTEM_CODES[DEFAULT_HOUSE_SYSTEM])

    subject = AstrologicalSubject(
        name=name or 'Subject',
        year=year, month=month, day=day,
        hour=hour, minute=minute,
        lng=float(lon), lat=float(lat),
        tz_str=tz_str,
        city=place_label or '—',
        nation='',
        houses_system_identifier=code,
    )

    # Render SVG. KerykeionChartSVG writes to disk by default; we point it
    # at a temp dir and read the result back so the caller only deals
    # with the string. The "Natal" chart type is appropriate for both
    # natal and event charts in this initial implementation.
    with tempfile.TemporaryDirectory() as tmp:
        chart = KerykeionChartSVG(subject, chart_type='Natal', new_output_directory=tmp)
        chart.makeSVG()
        svg_path = _find_svg(tmp)
        with open(svg_path, 'r', encoding='utf-8') as fh:
            svg = fh.read()
    # Kerykeion always formats the top-left location label as
    # "{city}, {nation}" and silently forces nation='GB' when blank, so
    # SVGs end with junk like "Palo Alto, California, US, GB". Overwrite
    # that one labeled element with the exact place_label.
    if place_label:
        svg = re.sub(
            r"(<text[^>]*kr:node='Top_Left_Text_1'[^>]*>)[^<]*(</text>)",
            lambda m: m.group(1) + _escape_xml(place_label) + m.group(2),
            svg,
            count=1,
        )
    # Kerykeion hard-codes the chart heading as "{name} - Birth Chart" in
    # both the SVG <title> (accessibility) and the visible Chart_Title
    # element. Swap in our own label so event charts (journal entries)
    # read "Reading Chart" instead of "Birth Chart".
    if chart_label and chart_label != 'Birth Chart':
        new_heading = _escape_xml(f"{name or 'Subject'} - {chart_label}")
        svg = re.sub(
            r"<title>[^<]*</title>",
            f"<title>{new_heading}</title>",
            svg,
            count=1,
        )
        svg = re.sub(
            r"(<text[^>]*kr:node='Chart_Title'[^>]*>)[^<]*(</text>)",
            lambda m: m.group(1) + new_heading + m.group(2),
            svg,
            count=1,
        )

    return {
        'svg': svg,
        'data': subject.model_dump(),
        'house_system': house_system,
        'solar_chart': bool(not time_iso and solar_chart_fallback),
        'timezone': tz_str,
    }


def _escape_xml(s: str) -> str:
    return (
        s.replace('&', '&amp;')
         .replace('<', '&lt;')
         .replace('>', '&gt;')
         .replace("'", '&apos;')
         .replace('"', '&quot;')
    )


def _find_svg(directory: str) -> str:
    """Locate the SVG Kerykeion just wrote into `directory`.

    Kerykeion names files like '<name> - Natal Chart.svg', and any
    leading slashes / weird chars in the subject name get sanitized,
    but listing the dir is more robust than guessing the name.
    """
    candidates = [n for n in os.listdir(directory) if n.lower().endswith('.svg')]
    if not candidates:
        raise RuntimeError(f'Kerykeion produced no SVG in {directory}')
    # If somehow multiple exist, take the largest (the real chart vs any
    # intermediate render). Stable + cheap.
    candidates.sort(key=lambda n: os.path.getsize(os.path.join(directory, n)), reverse=True)
    return os.path.join(directory, candidates[0])
