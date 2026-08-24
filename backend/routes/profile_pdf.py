"""
Profile PDF export: header + optional natal chart, birth cards
(Greer and/or Amberstone variants), and name cards.

Follows the journal-entry PDF pipeline: build a Jinja2 context with
file:// image URIs, render profile_export.html, WeasyPrint to PDF,
stream back as an attachment. Chart resolution mirrors the
/api/profiles/<id>/chart route (same cache, same solar-chart rules)
but degrades to omitting the section instead of erroring — a missing
birth time shouldn't sink the rest of the export.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from io import BytesIO
from pathlib import Path

from flask import Blueprint, current_app, request, send_file, jsonify

import birth_cards as bc
import name_cards as nc
from backend.utils import row_to_dict
from backend.routes.pdf_export import (
    _file_uri, _planetary_positions, _render_chart_png_data_uri,
    _safe_filename)
from backend.routes.birth_cards import _hydrate as hydrate_birth_cards
from backend.routes.birth_cards import _prefs as birth_card_prefs
from backend.routes.name_cards import _major_hydrator

logger = logging.getLogger(__name__)

profile_pdf_bp = Blueprint('profile_pdf', __name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / 'pdf_templates'


def _jpeg_data_uri(image_path: str, cache) -> str | None:
    """A compact JPEG data URI for a card image. The thumbnail cache's
    preview renditions are PNGs (~300-600KB each); with dozens of card
    tiles across two birth-card variants plus the mandala, embedding
    those balloons the PDF into tens of MB. Re-encoding to a bounded
    JPEG keeps each image under ~80KB with no visible loss at print
    tile sizes. Falls back to the raw file URI if PIL chokes."""
    import base64

    path = None
    if cache is not None:
        try:
            path = cache.get_thumbnail_path(image_path, size=cache.PREVIEW_SIZE)
        except Exception:
            path = None
    if not path:
        path = image_path
    try:
        from PIL import Image
        with Image.open(path) as img:
            img = img.convert('RGB')
            img.thumbnail((500, 750))
            buf = BytesIO()
            img.save(buf, 'JPEG', quality=78, optimize=True)
        encoded = base64.b64encode(buf.getvalue()).decode('ascii')
        return f'data:image/jpeg;base64,{encoded}'
    except Exception as e:
        logger.debug('profile PDF: JPEG re-encode failed for %s: %s',
                     image_path, e)
        return _file_uri(image_path, cache)


def _card_image_uris(db, cache, card_ids: set) -> dict:
    """Map card id -> embeddable image URI (compressed data URI)."""
    out = {}
    ids = [cid for cid in card_ids if cid]
    if not ids:
        return out
    cursor = db.conn.cursor()
    placeholders = ','.join('?' * len(ids))
    cursor.execute(
        f'SELECT id, image_path FROM cards WHERE id IN ({placeholders})', ids)
    for row in cursor.fetchall():
        r = row if isinstance(row, dict) else dict(row)
        if not r.get('image_path'):
            continue
        uri = _jpeg_data_uri(r['image_path'], cache)
        if uri:
            out[r['id']] = uri
    return out


def _attach_image_uris(node, uri_map):
    """Walk a hydrated cards structure, attaching image_uri beside
    every card_id. Mutates in place; handles dicts and lists."""
    if isinstance(node, dict):
        if 'card_id' in node:
            node['image_uri'] = uri_map.get(node.get('card_id'))
        for value in node.values():
            _attach_image_uris(value, uri_map)
    elif isinstance(node, list):
        for item in node:
            _attach_image_uris(item, uri_map)


def _collect_card_ids(node, acc: set):
    if isinstance(node, dict):
        if node.get('card_id'):
            acc.add(node['card_id'])
        for value in node.values():
            _collect_card_ids(value, acc)
    elif isinstance(node, list):
        for item in node:
            _collect_card_ids(item, acc)


def _resolve_profile_chart(db, profile: dict) -> dict | None:
    """Natal chart block for the template, or None when birth data is
    incomplete / generation fails. Mirrors GET /api/profiles/:id/chart
    including the cache and the solar-chart fallback rule."""
    import astrology

    if (not profile.get('birth_date')
            or profile.get('birth_place_lat') is None
            or profile.get('birth_place_lon') is None):
        return None
    allow_solar = db.get_allow_solar_chart()
    if not profile.get('birth_time') and not allow_solar:
        return None

    house_system = db.get_house_system()
    place_label = profile.get('birth_place_name') or ''
    solar = not profile.get('birth_time') and allow_solar
    input_hash = astrology.compute_input_hash(
        profile['birth_date'], profile.get('birth_time'),
        profile['birth_place_lat'], profile['birth_place_lon'],
        house_system, solar_chart=solar, place_label=place_label)

    cached = db.get_cached_chart('profile', profile['id'])
    if cached and cached.get('input_hash') == input_hash:
        svg, chart_data = cached['chart_svg'], cached['chart_data']
    else:
        try:
            result = astrology.generate_chart(
                name=profile.get('name') or 'Subject',
                date_iso=profile['birth_date'],
                time_iso=profile.get('birth_time'),
                lat=profile['birth_place_lat'],
                lon=profile['birth_place_lon'],
                house_system=house_system,
                solar_chart_fallback=allow_solar,
                place_label=place_label)
        except Exception as e:
            logger.warning('profile PDF: chart generation failed: %s', e)
            return None
        svg, chart_data = result['svg'], dict(result['data'])
        chart_data['solar_chart'] = result['solar_chart']
        chart_data['timezone'] = result['timezone']
        try:
            db.save_cached_chart('profile', profile['id'], house_system,
                                 input_hash, svg, chart_data)
        except Exception as e:
            logger.debug('profile PDF: chart cache write failed: %s', e)

    return {
        'png_uri': _render_chart_png_data_uri(svg),
        'positions': _planetary_positions(chart_data),
        'house_system': house_system,
        'timezone': (chart_data or {}).get('timezone'),
        'solar_chart': bool((chart_data or {}).get('solar_chart')),
    }


def _birth_card_blocks(db, cache, profile: dict, methods: list) -> list:
    """One hydrated birth-card block per requested method."""
    birth_str = profile.get('birth_date')
    if not birth_str:
        return []
    try:
        birth = date.fromisoformat(birth_str)
    except ValueError:
        return []
    _, eight_eleven, court_system = birth_card_prefs(db)
    today = date.today()
    blocks = []
    for method in methods:
        if method not in bc.METHODS:
            continue
        calc = bc.calculate(birth, method=method,
                            reference_year=today.year,
                            reference_month=today.month)
        hydrated = hydrate_birth_cards(calc, eight_eleven, court_system, db)
        ids = set()
        _collect_card_ids(hydrated['cards'], ids)
        uris = _card_image_uris(db, cache, ids)
        _attach_image_uris(hydrated['cards'], uris)
        hydrated['reference_year'] = today.year
        hydrated['method_label'] = (
            'Greer (month + day + full year)' if method == bc.GREER
            else 'Amberstone (month + day + century + year)')
        blocks.append(hydrated)
    return blocks


def _name_card_block(db, cache, profile: dict) -> dict | None:
    """Name cards from full_name + the saved per-profile adjustments.
    None when there's no full name or the name fails validation."""
    full_name = (profile.get('full_name') or '').strip()
    if not full_name:
        return None
    config = {}
    raw = profile.get('name_cards_config')
    if raw:
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                config = loaded
        except ValueError:
            pass
    parts = config.get('parts') or full_name.split()
    try:
        result = nc.calculate_name_cards(
            parts,
            roles=config.get('roles'),
            y_mode=config.get('y_mode', 'heuristic'),
            y_overrides=config.get('y_overrides'),
            drop_suffixes=config.get('drop_suffixes', True))
    except ValueError as e:
        logger.warning('profile PDF: name cards skipped: %s', e)
        return None

    major, _ = _major_hydrator(db)
    result['cards'] = {
        'first_name': major(result['first_name_card']),
        'middle_name': major(result['middle_name_card']),
        'last_name': major(result['last_name_card']),
        'desires_inner_motivation': major(result['desires_inner_motivation']),
        'outer_persona': major(result['outer_persona']),
        'theme_note': major(result['theme_note']),
        'rhythm': major(result['rhythm']),
        'melody': major(result['melody']),
        'hidden_factor_name': [major(n) for n in result['hidden_factor_name']],
    }
    birth_str = profile.get('birth_date')
    if birth_str:
        try:
            birth = date.fromisoformat(birth_str)
            life = nc.life_potential(
                bc.method_base(birth, bc.GREER), result['all_letters'])
            result['life_potential'] = life
            result['cards']['life_potential'] = major(life)
        except ValueError:
            pass
    result['majors_by_number'] = {n: major(n) for n in range(1, 23)}

    ids = set()
    _collect_card_ids(result['cards'], ids)
    _collect_card_ids(result['majors_by_number'], ids)
    uris = _card_image_uris(db, cache, ids)
    _attach_image_uris(result['cards'], uris)
    _attach_image_uris(result['majors_by_number'], uris)
    # Constellation strip rows for the template (dict order is fine
    # but make it explicit and sorted).
    result['constellation_rows'] = [
        {'root': n, 'count': result['constellation_count'][n]}
        for n in range(1, 10)]
    return result


@profile_pdf_bp.route('/api/profiles/<int:profile_id>/export-pdf',
                      methods=['POST'])
def export_profile_pdf(profile_id):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from weasyprint import HTML, CSS

    db = current_app.config['DB']
    cache = current_app.config.get('THUMB_CACHE')
    body = request.get_json(silent=True) or {}

    row = db.get_profile(profile_id)
    if not row:
        return jsonify({'error': 'Profile not found'}), 404
    profile = row_to_dict(row)

    chart_block = None
    if body.get('include_chart'):
        chart_block = _resolve_profile_chart(db, profile)

    birth_blocks = []
    if body.get('include_birth_cards'):
        methods = body.get('birth_card_methods') or [bc.GREER]
        birth_blocks = _birth_card_blocks(db, cache, profile, methods)

    name_block = None
    if body.get('include_name_cards'):
        name_block = _name_card_block(db, cache, profile)

    context = {
        'profile': profile,
        'chart_block': chart_block,
        'birth_blocks': birth_blocks,
        'name_block': name_block,
    }

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(['html']))
    html = env.get_template('profile_export.html').render(**context)
    css = CSS(filename=str(_TEMPLATE_DIR / 'profile_export.css'))
    pdf_bytes = HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf(
        stylesheets=[css])

    filename = f"profile_{_safe_filename(profile.get('name') or str(profile_id))}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename)
