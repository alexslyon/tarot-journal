"""
Register all route blueprints with the Flask app.
"""


def register_blueprints(app):
    from backend.routes.health import health_bp
    from backend.routes.types import types_bp
    from backend.routes.decks import decks_bp
    from backend.routes.cards import cards_bp
    from backend.routes.images import images_bp
    from backend.routes.tags import tags_bp
    from backend.routes.archetypes import archetypes_bp
    from backend.routes.import_export import import_export_bp
    from backend.routes.entries import entries_bp
    from backend.routes.spreads import spreads_bp
    from backend.routes.stats import stats_bp
    from backend.routes.settings import settings_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(types_bp)
    app.register_blueprint(decks_bp)
    app.register_blueprint(cards_bp)
    app.register_blueprint(images_bp)
    app.register_blueprint(tags_bp)
    app.register_blueprint(archetypes_bp)
    app.register_blueprint(import_export_bp)
    app.register_blueprint(entries_bp)
    app.register_blueprint(spreads_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(settings_bp)
