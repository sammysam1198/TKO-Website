import hashlib
import re

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_db_conn
from utils.auth_utils import decode_auth_token, check_rate_limit
from utils.serialization import row_with_iso_dates, rows_with_iso_dates

forum_bp = Blueprint("forum", __name__)

# Content limits
MAX_TITLE_LENGTH = 255
MAX_CONTENT_LENGTH = 10000
MAX_DISPLAY_NAME_LENGTH = 120


def get_client_identifier():
    """Get identifier for rate limiting."""
    return request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"


def sanitize_display_name(name: str) -> str:
    """remove control chars, limit length."""
    if not name:
        return name
    # Remove control characters
    name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', name)
    return name[:MAX_DISPLAY_NAME_LENGTH]


def get_current_user_optional():
    """Extract user from Bearer token if present. Returns None if not authenticated."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_auth_token(token)
        user_id = int(payload["sub"])

        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                "SELECT id, username, email FROM tko_users WHERE id = %s;",
                (user_id,),
            )
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()
    except Exception:
        return None


def get_voter_fingerprint():
    """Generate a fingerprint for anonymous vote tracking."""
    ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")
    return hashlib.sha256(f"{ip}:{ua}".encode()).hexdigest()


# ============ Categories ============


@forum_bp.get("/api/tko/forum/categories")
def get_categories():
    """List all forum categories."""
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, slug, name, description, display_order
            FROM tko_forum_categories
            ORDER BY display_order ASC;
            """
        )
        categories = cur.fetchall()
        return jsonify({"ok": True, "categories": categories})
    finally:
        cur.close()
        conn.close()


# ============ Posts ============


@forum_bp.get("/api/tko/forum/posts")
def get_posts():
    """List posts with pagination and filtering."""
    category = request.args.get("category")

    # Safely parse and bounds-check pagination params
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 50))
    except (ValueError, TypeError):
        limit = 20

    sort = request.args.get("sort", "newest")
    # Whitelist sort values
    if sort not in ("newest", "top", "hot"):
        sort = "newest"

    offset = (page - 1) * limit

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        where_clauses = ["p.parent_id IS NULL"]
        params = []

        if category:
            where_clauses.append("c.slug = %s")
            params.append(category)

        order_clause = {
            "newest": "p.created_at DESC",
            "top": "p.score DESC, p.created_at DESC",
            "hot": "p.score DESC, p.reply_count DESC, p.created_at DESC",
        }.get(sort, "p.created_at DESC")

        query = f"""
            SELECT p.id, p.category_id, p.user_id, p.display_name, p.title,
                   p.content, p.reply_count, p.score, p.is_pinned,
                   p.created_at, p.updated_at,
                   c.slug as category_slug, c.name as category_name,
                   u.username as author_username
            FROM tko_forum_posts p
            JOIN tko_forum_categories c ON p.category_id = c.id
            LEFT JOIN tko_users u ON p.user_id = u.id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY p.is_pinned DESC, {order_clause}
            LIMIT %s OFFSET %s;
        """
        params.extend([limit, offset])

        cur.execute(query, params)
        posts = cur.fetchall()

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM tko_forum_posts p
            JOIN tko_forum_categories c ON p.category_id = c.id
            WHERE {' AND '.join(where_clauses)};
        """
        cur.execute(count_query, params[:-2] if category else [])
        total = cur.fetchone()["total"]

        return jsonify({
            "ok": True,
            "posts": rows_with_iso_dates(posts),
            "page": page,
            "limit": limit,
            "total": total,
        })
    finally:
        cur.close()
        conn.close()


@forum_bp.get("/api/tko/forum/posts/<int:post_id>")
def get_post(post_id):
    """Get a single post with all nested replies."""
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Get main post
        cur.execute(
            """
            SELECT p.*, c.slug as category_slug, c.name as category_name,
                   u.username as author_username
            FROM tko_forum_posts p
            JOIN tko_forum_categories c ON p.category_id = c.id
            LEFT JOIN tko_users u ON p.user_id = u.id
            WHERE p.id = %s;
            """,
            (post_id,),
        )
        post = cur.fetchone()

        if not post:
            return jsonify({"ok": False, "error": "Post not found"}), 404

        # Get all replies using recursive CTE
        cur.execute(
            """
            WITH RECURSIVE reply_tree AS (
                SELECT p.*, u.username as author_username, 0 as tree_depth
                FROM tko_forum_posts p
                LEFT JOIN tko_users u ON p.user_id = u.id
                WHERE p.parent_id = %s

                UNION ALL

                SELECT p.*, u.username as author_username, rt.tree_depth + 1
                FROM tko_forum_posts p
                LEFT JOIN tko_users u ON p.user_id = u.id
                JOIN reply_tree rt ON p.parent_id = rt.id
                WHERE rt.tree_depth < 10
            )
            SELECT * FROM reply_tree
            ORDER BY created_at ASC;
            """,
            (post_id,),
        )
        replies = cur.fetchall()

        return jsonify({
            "ok": True,
            "post": row_with_iso_dates(post),
            "replies": rows_with_iso_dates(replies),
        })
    finally:
        cur.close()
        conn.close()


@forum_bp.post("/api/tko/forum/posts")
def create_post():
    """Create a new post or reply."""
    # Rate limiting
    client_id = get_client_identifier()
    if not check_rate_limit(f"forum_post:{client_id}", max_requests=5, window=60):
        return jsonify({"ok": False, "error": "Too many posts. Please wait before posting again."}), 429

    data = request.get_json(silent=True) or {}
    user = get_current_user_optional()

    category_id = data.get("category_id")
    display_name = sanitize_display_name((data.get("display_name") or "").strip())
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    parent_id = data.get("parent_id")

    # Input length validation
    if title and len(title) > MAX_TITLE_LENGTH:
        return jsonify({"ok": False, "error": f"Title cannot exceed {MAX_TITLE_LENGTH} characters"}), 400

    if content and len(content) > MAX_CONTENT_LENGTH:
        return jsonify({"ok": False, "error": f"Content cannot exceed {MAX_CONTENT_LENGTH} characters"}), 400

    # Use username as display name if logged in and not provided
    if not display_name:
        if user:
            display_name = user["username"]
        else:
            return jsonify({"ok": False, "error": "Display name required"}), 400

    if not content:
        return jsonify({"ok": False, "error": "Content required"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        depth = 0
        actual_category_id = category_id

        if parent_id:
            # Get parent info for replies
            cur.execute(
                "SELECT depth, category_id FROM tko_forum_posts WHERE id = %s",
                (parent_id,),
            )
            parent = cur.fetchone()
            if not parent:
                return jsonify({"ok": False, "error": "Parent post not found"}), 404
            depth = parent["depth"] + 1
            actual_category_id = parent["category_id"]
        else:
            # Top-level posts require title and category
            if not title:
                return jsonify({"ok": False, "error": "Title required for new posts"}), 400
            if not category_id:
                return jsonify({"ok": False, "error": "Category required"}), 400

        cur.execute(
            """
            INSERT INTO tko_forum_posts
            (category_id, user_id, parent_id, display_name, title, content, depth)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
            """,
            (
                actual_category_id,
                user["id"] if user else None,
                parent_id,
                display_name,
                title if not parent_id else None,
                content,
                depth,
            ),
        )
        post = cur.fetchone()

        # Update parent reply count if this is a reply
        if parent_id:
            cur.execute(
                """
                UPDATE tko_forum_posts
                SET reply_count = reply_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
                """,
                (parent_id,),
            )

        conn.commit()
        return jsonify({"ok": True, "post": row_with_iso_dates(post)}), 201
    finally:
        cur.close()
        conn.close()


# ============ Voting ============


@forum_bp.post("/api/tko/forum/posts/<int:post_id>/vote")
def vote_post(post_id):
    """Upvote or downvote a post."""
    # Rate limiting for votes
    client_id = get_client_identifier()
    if not check_rate_limit(f"vote:{client_id}", max_requests=30, window=60):
        return jsonify({"ok": False, "error": "Too many votes. Please slow down."}), 429

    data = request.get_json(silent=True) or {}
    vote_type = data.get("vote_type")

    if vote_type not in [1, -1]:
        return jsonify({"ok": False, "error": "Invalid vote type (use 1 or -1)"}), 400

    user = get_current_user_optional()
    fingerprint = None if user else get_voter_fingerprint()

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Check if post exists
        cur.execute("SELECT id FROM tko_forum_posts WHERE id = %s", (post_id,))
        if not cur.fetchone():
            return jsonify({"ok": False, "error": "Post not found"}), 404

        # Check for existing vote
        if user:
            cur.execute(
                """
                SELECT id, vote_type FROM tko_forum_votes
                WHERE post_id = %s AND user_id = %s;
                """,
                (post_id, user["id"]),
            )
        else:
            cur.execute(
                """
                SELECT id, vote_type FROM tko_forum_votes
                WHERE post_id = %s AND voter_fingerprint = %s;
                """,
                (post_id, fingerprint),
            )

        existing = cur.fetchone()
        score_delta = 0

        if existing:
            if existing["vote_type"] == vote_type:
                # Toggle off - remove vote
                cur.execute("DELETE FROM tko_forum_votes WHERE id = %s", (existing["id"],))
                score_delta = -vote_type
            else:
                # Change vote direction
                cur.execute(
                    "UPDATE tko_forum_votes SET vote_type = %s WHERE id = %s",
                    (vote_type, existing["id"]),
                )
                score_delta = vote_type * 2
        else:
            # New vote
            cur.execute(
                """
                INSERT INTO tko_forum_votes (post_id, user_id, voter_fingerprint, vote_type)
                VALUES (%s, %s, %s, %s);
                """,
                (post_id, user["id"] if user else None, fingerprint, vote_type),
            )
            score_delta = vote_type

        # Update denormalized score
        cur.execute(
            """
            UPDATE tko_forum_posts
            SET score = score + %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING score;
            """,
            (score_delta, post_id),
        )
        result = cur.fetchone()

        conn.commit()
        return jsonify({"ok": True, "new_score": result["score"]})
    finally:
        cur.close()
        conn.close()
