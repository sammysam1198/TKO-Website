import hmac
import os

from flask import Blueprint, jsonify, request

dev_console_bp = Blueprint("dev_console", __name__, url_prefix="/api/tko/dev-console")


@dev_console_bp.route("/unlock", methods=["POST"])
def unlock_dev_console():
    data = request.get_json(silent=True) or {}
    submitted_password = str(data.get("password", ""))

    expected_password = os.getenv("DEV_CONSOLE_PASSWORD", "")

    if not expected_password:
        return jsonify({"error": "Developer console password is not configured on the server."}), 500

    if not hmac.compare_digest(submitted_password, expected_password):
        return jsonify({"error": "Invalid developer password."}), 401

    return jsonify({"ok": True, "message": "Developer access granted."}), 200
