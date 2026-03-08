from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_db_conn
from utils.auth_utils import (
    is_valid_email,
    is_valid_username,
    validate_password,
    hash_password,
    verify_password,
    create_auth_token,
)
from utils.serialization import row_with_iso_dates

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/api/tko/auth/signup")
def signup():
    data = request.get_json(silent=True) or {}

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    agreed_to_terms = bool(data.get("agreed_to_terms"))

    if not first_name:
        return jsonify({"ok": False, "error": "First name is required"}), 400
    if not last_name:
        return jsonify({"ok": False, "error": "Last name is required"}), 400
    if not email:
        return jsonify({"ok": False, "error": "Email is required"}), 400
    if not is_valid_email(email):
        return jsonify({"ok": False, "error": "Email format is invalid"}), 400
    if not username:
        return jsonify({"ok": False, "error": "Username is required"}), 400
    if not is_valid_username(username):
        return jsonify({"ok": False, "error": "Username format is invalid"}), 400
    if username.lower() == password.lower() or password.lower() in username.lower():
        return jsonify({"ok": False, "error": "Username cannot match or contain the password"}), 400

    password_ok, password_error = validate_password(password)
    if not password_ok:
        return jsonify({"ok": False, "error": password_error}), 400

    if not agreed_to_terms:
        return jsonify({"ok": False, "error": "You must agree to the Terms of Use and Privacy Policy"}), 400

    password_hash = hash_password(password)

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id FROM tko_users
            WHERE LOWER(email) = %s OR LOWER(username) = %s
            LIMIT 1;
            """,
            (email, username.lower())
        )
        existing = cur.fetchone()

        if existing:
            return jsonify({"ok": False, "error": "Email or username already exists"}), 409

        cur.execute(
            """
            INSERT INTO tko_users (
                first_name, last_name, email, username, password_hash, agreed_to_terms
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, first_name, last_name, email, username, agreed_to_terms, profile_image_url, created_at, updated_at;
            """,
            (first_name, last_name, email, username, password_hash, agreed_to_terms)
        )
        user = cur.fetchone()
        conn.commit()

        token = create_auth_token(user)

        return jsonify({
            "ok": True,
            "message": "Account created",
            "token": token,
            "user": row_with_iso_dates(user)
        }), 201

    finally:
        cur.close()
        conn.close()


@auth_bp.post("/api/tko/auth/signin")
def signin():
    data = request.get_json(silent=True) or {}

    username_or_email = (data.get("username_or_email") or "").strip().lower()
    password = data.get("password") or ""

    if not username_or_email:
        return jsonify({"ok": False, "error": "Username or email is required"}), 400
    if not password:
        return jsonify({"ok": False, "error": "Password is required"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, first_name, last_name, email, username, password_hash,
                   agreed_to_terms, profile_image_url, created_at, updated_at
            FROM tko_users
            WHERE LOWER(email) = %s OR LOWER(username) = %s
            LIMIT 1;
            """,
            (username_or_email, username_or_email)
        )
        user = cur.fetchone()

        if not user:
            return jsonify({"ok": False, "error": "Invalid credentials"}), 401

        if not verify_password(password, user["password_hash"]):
            return jsonify({"ok": False, "error": "Invalid credentials"}), 401

        token = create_auth_token(user)

        safe_user = dict(user)
        safe_user.pop("password_hash", None)

        return jsonify({
            "ok": True,
            "message": "Signed in successfully",
            "token": token,
            "user": row_with_iso_dates(safe_user)
        })

    finally:
        cur.close()
        conn.close()


@auth_bp.get("/api/tko/auth/me")
def me():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"ok": False, "error": "Missing token"}), 401

    token = auth_header.split(" ", 1)[1]

    from utils.auth_utils import decode_auth_token

    try:
        payload = decode_auth_token(token)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid or expired token"}), 401

    user_id = int(payload["sub"])

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, first_name, last_name, email, username,
                   agreed_to_terms, profile_image_url, created_at, updated_at
            FROM tko_users
            WHERE id = %s
            LIMIT 1;
            """,
            (user_id,)
        )
        user = cur.fetchone()

        if not user:
            return jsonify({"ok": False, "error": "User not found"}), 404

        return jsonify({"ok": True, "user": row_with_iso_dates(user)})

    finally:
        cur.close()
        conn.close()
