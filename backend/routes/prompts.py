"""
Prompt preset routes — viewing, editing, and switching the AI
assistants' system prompts. The built-in defaults live in the
frontend; the backend stores only user-authored variants and which
one is active (null = built-in default).
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from backend.utils import row_to_dict, require_json

prompts_bp = Blueprint('prompts', __name__)

FEATURES = ('mirror', 'analyst', 'scribe')


def _check_feature(feature: str):
    if feature not in FEATURES:
        return jsonify({'error': f'Unknown assistant: {feature}'}), 404
    return None


@prompts_bp.route('/api/prompts/<feature>')
def get_prompts(feature):
    err = _check_feature(feature)
    if err:
        return err
    db = current_app.config['DB']
    return jsonify({
        'presets': [row_to_dict(r) for r in db.get_prompt_presets(feature)],
        'active_id': db.get_active_prompt_preset_id(feature),
    })


@prompts_bp.route('/api/prompts/<feature>/presets', methods=['POST'])
@require_json
def add_preset(feature, data):
    err = _check_feature(feature)
    if err:
        return err
    db = current_app.config['DB']
    name = (data.get('name') or '').strip()
    content = data.get('content') or ''
    if not name or not content.strip():
        return jsonify({'error': 'name and content are required'}), 400
    preset_id = db.add_prompt_preset(feature, name, content)
    return jsonify({'id': preset_id}), 201


@prompts_bp.route('/api/prompts/presets/<int:preset_id>', methods=['PUT'])
@require_json
def update_preset(preset_id, data):
    db = current_app.config['DB']
    if not db.get_prompt_preset(preset_id):
        return jsonify({'error': 'Preset not found'}), 404
    name = data.get('name')
    if name is not None and not name.strip():
        return jsonify({'error': 'name cannot be empty'}), 400
    content = data.get('content')
    if content is not None and not content.strip():
        return jsonify({'error': 'content cannot be empty'}), 400
    db.update_prompt_preset(preset_id, name=name, content=content)
    return jsonify({'ok': True})


@prompts_bp.route('/api/prompts/presets/<int:preset_id>', methods=['DELETE'])
def delete_preset(preset_id):
    db = current_app.config['DB']
    row = db.get_prompt_preset(preset_id)
    if not row:
        return jsonify({'error': 'Preset not found'}), 404
    # Deleting the active preset falls back to the built-in default.
    feature = row['feature']
    if db.get_active_prompt_preset_id(feature) == preset_id:
        db.set_active_prompt_preset_id(feature, None)
    db.delete_prompt_preset(preset_id)
    return jsonify({'ok': True})


@prompts_bp.route('/api/prompts/<feature>/active', methods=['PUT'])
@require_json
def set_active(feature, data):
    err = _check_feature(feature)
    if err:
        return err
    db = current_app.config['DB']
    preset_id = data.get('preset_id')
    if preset_id is not None:
        row = db.get_prompt_preset(int(preset_id))
        if not row or row['feature'] != feature:
            return jsonify({'error': 'Preset not found for this assistant'}), 404
    db.set_active_prompt_preset_id(feature, preset_id)
    return jsonify({'ok': True})
