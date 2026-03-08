import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS

# -------------------------------------------------------------------
# TKO / Bela Game API
# psycopg2 version, styled more like ASTRA backend code
# -------------------------------------------------------------------

app = Flask(__name__)
CORS(app)


# -------------------------------------------------------------------
# DATABASE CONNECTION HELPERS
# -------------------------------------------------------------------

def get_db_conn():
    """Create a fresh PostgreSQL connection using Render's DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(database_url)


def init_db():
    """Create required tables if they do not already exist."""
    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tko_subscribers (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(120),
            email VARCHAR(255) NOT NULL UNIQUE,
            interest TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tko_guestbook_posts (
            id SERIAL PRIMARY KEY,
            display_name VARCHAR(120) NOT NULL,
            mood_tag VARCHAR(120),
            message TEXT NOT NULL,
            upvotes INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conn.commit()
    cur.close()
    conn.close()


# -------------------------------------------------------------------
# SERIALIZATION HELPERS
# -------------------------------------------------------------------

def row_with_iso_dates(row):
    """Convert datetime fields to ISO strings for JSON responses."""
    if not row:
        return row

    converted = dict(row)

    for key, value in converted.items():
        if isinstance(value, datetime):
            converted[key] = value.isoformat()

    return converted


def rows_with_iso_dates(rows):
    return [row_with_iso_dates(row) for row in rows]


# -------------------------------------------------------------------
# BASIC SERVICE ROUTES
# -------------------------------------------------------------------

@app.get("/")
def root():
    return jsonify({
        "ok": True,
        "service": "TKO Game API",
        "developer": "Bela",
        "database": "PostgreSQL",
        "driver": "psycopg2",
        "message": "TKO backend is running."
    })


@app.get("/health")
def health():
    return jsonify({"ok": True})


# -------------------------------------------------------------------
# MAILING LIST ENDPOINTS
# -------------------------------------------------------------------

@app.post("/api/tko/subscribers")
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


@app.get("/api/tko/subscribers")
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


@app.delete("/api/tko/subscribers/<int:subscriber_id>")
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


# -------------------------------------------------------------------
# GUESTBOOK / FORUM ENDPOINTS
# -------------------------------------------------------------------

@app.post("/api/tko/posts")
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


@app.get("/api/tko/posts")
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


@app.get("/api/tko/posts/<int:post_id>")
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


@app.put("/api/tko/posts/<int:post_id>")
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


@app.delete("/api/tko/posts/<int:post_id>")
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


@app.post("/api/tko/posts/<int:post_id>/upvote")
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


# -------------------------------------------------------------------
# START SERVER
# -------------------------------------------------------------------

if __name__ == "__main__":
    init_db()

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

