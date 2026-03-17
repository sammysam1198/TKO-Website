import hmac
import os

from psycopg2.extras import RealDictCursor
from db import get_db_conn
from utils.serialization import rows_with_iso_dates
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



@dev_console_bp.get("/messages")
def get_dev_messages():
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, username, message, created_at
            FROM dev_messages
            ORDER BY created_at DESC
            LIMIT 100;
            """
        )
        rows = cur.fetchall()

        return jsonify({
            "ok": True,
            "messages": rows_with_iso_dates(rows)
        })

    finally:
        cur.close()
        conn.close()

@dev_console_bp.post("/messages")
def post_dev_message():
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()
    username = (data.get("username") or "dev").strip()

    if not message:
        return jsonify({"ok": False, "error": "Message required"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            INSERT INTO dev_messages (username, message)
            VALUES (%s, %s)
            RETURNING id, username, message, created_at;
            """,
            (username, message)
        )
        row = cur.fetchone()
        conn.commit()

        return jsonify({
            "ok": True,
            "message": rows_with_iso_dates([row])[0]
        })

    finally:
        cur.close()
        conn.close()


@dev_console_bp.get("/issues")
def get_issues():
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT * FROM dev_issues
            ORDER BY created_at DESC;
            """
        )
        rows = cur.fetchall()

        return jsonify({"ok": True, "issues": rows_with_iso_dates(rows)})

    finally:
        cur.close()
        conn.close()


@dev_console_bp.post("/issues")
def create_issue():
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    severity = (data.get("severity") or "normal").strip()
    created_by = (data.get("created_by") or "dev").strip()

    if not title:
        return jsonify({"ok": False, "error": "Title required"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            INSERT INTO dev_issues (title, description, severity, created_by)
            VALUES (%s, %s, %s, %s)
            RETURNING *;
            """,
            (title, description, severity, created_by)
        )
        row = cur.fetchone()
        conn.commit()

        return jsonify({"ok": True, "issue": rows_with_iso_dates([row])[0]})

    finally:
        cur.close()
        conn.close()


@dev_console_bp.get("/logs")
def get_logs():
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT * FROM dev_logs
            ORDER BY created_at DESC;
            """
        )
        rows = cur.fetchall()

        return jsonify({"ok": True, "logs": rows_with_iso_dates(rows)})

    finally:
        cur.close()
        conn.close()


@dev_console_bp.post("/logs")
def create_log():
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()
    level = (data.get("level") or "info").strip()

    if not message:
        return jsonify({"ok": False, "error": "Message required"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            INSERT INTO dev_logs (message, level)
            VALUES (%s, %s)
            RETURNING *;
            """,
            (message, level)
        )
        row = cur.fetchone()
        conn.commit()

        return jsonify({"ok": True, "log": rows_with_iso_dates([row])[0]})

    finally:
        cur.close()
        conn.close()




