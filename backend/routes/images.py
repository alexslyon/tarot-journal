"""
Image serving endpoints -- serves card images and thumbnails over HTTP.

Card images are stored as local file paths in the database.
This module reads those paths and streams the files to the browser.
"""

import os
from flask import Blueprint, current_app, send_file, abort

images_bp = Blueprint('images', __name__)

# Map common extensions to MIME types
_MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
}


def _mime_for(path):
    ext = os.path.splitext(path)[1].lower()
    return _MIME_TYPES.get(ext, 'image/jpeg')


@images_bp.route('/api/images/card/<int:card_id>')
def card_image(card_id):
    """Serve the full-size card image."""
    db = current_app.config['DB']
    card = db.get_card(card_id)
    if not card or not card['image_path']:
        abort(404)
    path = card['image_path']
    if not os.path.isfile(path):
        abort(404)
    resp = send_file(path, mimetype=_mime_for(path))
    resp.cache_control.max_age = 86400  # 24 hours
    return resp


@images_bp.route('/api/images/card/<int:card_id>/thumbnail')
def card_thumbnail(card_id):
    """Serve a cached thumbnail (300x450) for a card."""
    db = current_app.config['DB']
    cache = current_app.config['THUMB_CACHE']
    card = db.get_card(card_id)
    if not card or not card['image_path']:
        abort(404)
    thumb_path = cache.get_thumbnail_path(card['image_path'])
    if not thumb_path or not os.path.isfile(thumb_path):
        abort(404)
    resp = send_file(thumb_path, mimetype='image/png')
    resp.cache_control.max_age = 86400
    return resp


@images_bp.route('/api/images/card/<int:card_id>/preview')
def card_preview(card_id):
    """Serve a larger preview (500x750) for a card."""
    db = current_app.config['DB']
    cache = current_app.config['THUMB_CACHE']
    card = db.get_card(card_id)
    if not card or not card['image_path']:
        abort(404)
    thumb_path = cache.get_thumbnail_path(
        card['image_path'],
        size=cache.PREVIEW_SIZE,
    )
    if not thumb_path or not os.path.isfile(thumb_path):
        abort(404)
    resp = send_file(thumb_path, mimetype='image/png')
    resp.cache_control.max_age = 86400
    return resp


@images_bp.route('/api/images/deck/<int:deck_id>/back')
def deck_back_image(deck_id):
    """Serve the card-back image for a deck."""
    db = current_app.config['DB']
    deck = db.get_deck(deck_id)
    if not deck or not deck['card_back_image']:
        abort(404)
    path = deck['card_back_image']
    if not os.path.isfile(path):
        abort(404)
    resp = send_file(path, mimetype=_mime_for(path))
    resp.cache_control.max_age = 86400
    return resp
