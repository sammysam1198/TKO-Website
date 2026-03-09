from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_db_conn
from utils.serialization import row_with_iso_dates, rows_with_iso_dates

subscriber_bp = Blueprint("subscribers", __name__)


@subscriber_bp.post("/api/tko/subscribers")
def create_subscriber():
    data = request.get_json(silent=True) or {}

    first_name = (data.get("first_name") or "").strip() or None
    email = (data.get("email") or "").strip().lower()
    interest = (data.get("interest") or "").strip() or None

    if not email:
        return jsonify({"ok": False, "error": "Email is required"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, first_name, email, interest, created_at
            FROM tko_subscribers
            WHERE LOWER(email) = %s
            LIMIT 1;
            """,
            (email,)
        )
        existing = cur.fetchone()

        if existing:
            return jsonify({
                "ok": True,
                "message": "Email already subscribed",
                "subscriber": row_with_iso_dates(existing)
            }), 200

        cur.execute(
            """
            INSERT INTO tko_subscribers (first_name, email, interest)
            VALUES (%s, %s, %s)
            RETURNING id, first_name, email, interest, created_at;
            """,
            (first_name, email, interest)
        )
        subscriber = cur.fetchone()

        conn.commit()

        return jsonify({
            "ok": True,
            "message": "Subscriber added",
            "subscriber": row_with_iso_dates(subscriber)
        }), 201

    finally:
        cur.close()
        conn.close()


@subscriber_bp.get("/api/tko/subscribers")
def get_subscribers():
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, first_name, email, interest, created_at
            FROM tko_subscribers
            ORDER BY created_at DESC;
            """
        )
        subscribers = cur.fetchall()

        return jsonify({
            "ok": True,
            "count": len(subscribers),
            "subscribers": rows_with_iso_dates(subscribers)
        })

    finally:
        cur.close()
        conn.close()


@subscriber_bp.delete("/api/tko/subscribers/<int:subscriber_id>")
def delete_subscriber(subscriber_id):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            DELETE FROM tko_subscribers
            WHERE id = %s
            RETURNING id;
            """,
            (subscriber_id,)
        )
        deleted = cur.fetchone()

        if not deleted:
            conn.rollback()
            return jsonify({"ok": False, "error": "Subscriber not found"}), 404

        conn.commit()
        return jsonify({"ok": True, "message": "Subscriber removed"})

    finally:
        cur.close()
        conn.close()
