from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_db_conn
from utils.serialization import row_with_iso_dates, rows_with_iso_dates

post_bp = Blueprint("posts", __name__)


@post_bp.post("/api/tko/posts")
def create_post():
    data = request.get_json(silent=True) or {}

    display_name = (data.get("display_name") or "").strip()
    mood_tag = (data.get("mood_tag") or "").strip() or None
    message = (data.get("message") or "").strip()

    if not display_name:
        return jsonify({"ok": False, "error": "Display name required"}), 400

    if not message:
        return jsonify({"ok": False, "error": "Message required"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            INSERT INTO tko_guestbook_posts (display_name, mood_tag, message)
            VALUES (%s, %s, %s)
            RETURNING id, display_name, mood_tag, message, upvotes, created_at, updated_at;
            """,
            (display_name, mood_tag, message)
        )
        post = cur.fetchone()

        conn.commit()

        return jsonify({
            "ok": True,
            "message": "Post created",
            "post": row_with_iso_dates(post)
        }), 201

    finally:
        cur.close()
        conn.close()


@post_bp.get("/api/tko/posts")
def get_posts():
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, display_name, mood_tag, message, upvotes, created_at, updated_at
            FROM tko_guestbook_posts
            ORDER BY created_at DESC;
            """
        )
        posts = cur.fetchall()

        return jsonify({
            "ok": True,
            "count": len(posts),
            "posts": rows_with_iso_dates(posts)
        })

    finally:
        cur.close()
        conn.close()


@post_bp.get("/api/tko/posts/<int:post_id>")
def get_post(post_id):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, display_name, mood_tag, message, upvotes, created_at, updated_at
            FROM tko_guestbook_posts
            WHERE id = %s;
            """,
            (post_id,)
        )
        post = cur.fetchone()

        if not post:
            return jsonify({"ok": False, "error": "Post not found"}), 404

        return jsonify({"ok": True, "post": row_with_iso_dates(post)})

    finally:
        cur.close()
        conn.close()


@post_bp.put("/api/tko/posts/<int:post_id>")
def update_post(post_id):
    data = request.get_json(silent=True) or {}

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, display_name, mood_tag, message, upvotes, created_at, updated_at
            FROM tko_guestbook_posts
            WHERE id = %s;
            """,
            (post_id,)
        )
        existing = cur.fetchone()

        if not existing:
            return jsonify({"ok": False, "error": "Post not found"}), 404

        display_name = existing["display_name"]
        mood_tag = existing["mood_tag"]
        message = existing["message"]

        if "display_name" in data:
            new_name = (data.get("display_name") or "").strip()
            if not new_name:
                return jsonify({"ok": False, "error": "Display name cannot be empty"}), 400
            display_name = new_name

        if "mood_tag" in data:
            mood_tag = (data.get("mood_tag") or "").strip() or None

        if "message" in data:
            new_message = (data.get("message") or "").strip()
            if not new_message:
                return jsonify({"ok": False, "error": "Message cannot be empty"}), 400
            message = new_message

        cur.execute(
            """
            UPDATE tko_guestbook_posts
            SET display_name = %s,
                mood_tag = %s,
                message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, display_name, mood_tag, message, upvotes, created_at, updated_at;
            """,
            (display_name, mood_tag, message, post_id)
        )
        updated_post = cur.fetchone()

        conn.commit()

        return jsonify({
            "ok": True,
            "message": "Post updated",
            "post": row_with_iso_dates(updated_post)
        })

    finally:
        cur.close()
        conn.close()


@post_bp.delete("/api/tko/posts/<int:post_id>")
def delete_post(post_id):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            DELETE FROM tko_guestbook_posts
            WHERE id = %s
            RETURNING id;
            """,
            (post_id,)
        )
        deleted = cur.fetchone()

        if not deleted:
            conn.rollback()
            return jsonify({"ok": False, "error": "Post not found"}), 404

        conn.commit()
        return jsonify({"ok": True, "message": "Post deleted"})

    finally:
        cur.close()
        conn.close()


@post_bp.post("/api/tko/posts/<int:post_id>/upvote")
def upvote_post(post_id):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            UPDATE tko_guestbook_posts
            SET upvotes = upvotes + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, display_name, mood_tag, message, upvotes, created_at, updated_at;
            """,
            (post_id,)
        )
        updated_post = cur.fetchone()

        if not updated_post:
            conn.rollback()
            return jsonify({"ok": False, "error": "Post not found"}), 404

        conn.commit()

        return jsonify({
            "ok": True,
            "message": "Post upvoted",
            "post": row_with_iso_dates(updated_post)
        })

    finally:
        cur.close()
        conn.close()
