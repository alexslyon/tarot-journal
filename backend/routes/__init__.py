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
    from backend.routes.correspondences import correspondences_bp
    from backend.routes.reference_sources import reference_sources_bp
    from backend.routes.combinations import combinations_bp
    from backend.routes.archetype_languages import archetype_languages_bp
    # (archetype_notes routes removed — source entries now live on the
    # reference_sources blueprint.)
    from backend.routes.anki_export import anki_export_bp
    from backend.routes.llm_export import llm_export_bp
    from backend.routes.llm import llm_bp
    from backend.routes.scribe import scribe_bp
    from backend.routes.insights import insights_bp
    from backend.routes.pdf_export import pdf_export_bp
    from backend.routes.geocode import geocode_bp

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
    app.register_blueprint(correspondences_bp)
    app.register_blueprint(reference_sources_bp)
    app.register_blueprint(combinations_bp)
    app.register_blueprint(archetype_languages_bp)
    app.register_blueprint(anki_export_bp)
    app.register_blueprint(llm_export_bp)
    app.register_blueprint(llm_bp)
    app.register_blueprint(scribe_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(pdf_export_bp)
    app.register_blueprint(geocode_bp)
