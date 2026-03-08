from flask import Blueprint, jsonify

core_bp = Blueprint("core", __name__)


@core_bp.get("/")
def root():
    return jsonify({
        "ok": True,
        "service": "TKO Game API",
        "developer": "Bela",
        "database": "PostgreSQL",
        "driver": "psycopg2",
        "message": "TKO backend is running."
    })


@core_bp.get("/health")
def health():
    return jsonify({"ok": True})
