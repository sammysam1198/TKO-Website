from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta
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
             role, agreed_to_terms, profile_image_url,
            theme_preference, colorblind_mode,
            two_factor_enabled, two_factor_method,
            created_at, updated_at
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


@auth_bp.post("/api/tko/auth/change-password")
def change_password():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"ok": False, "error": "Missing token"}), 401

    token = auth_header.split(" ", 1)[1]

    try:
        payload = decode_auth_token(token)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid or expired token"}), 401

    user_id = int(payload["sub"])
    data = request.get_json(silent=True) or {}

    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not current_password:
        return jsonify({"ok": False, "error": "Current password is required"}), 400
    if not new_password:
        return jsonify({"ok": False, "error": "New password is required"}), 400
    if new_password != confirm_password:
        return jsonify({"ok": False, "error": "New passwords do not match"}), 400

    password_ok, password_error = validate_password(new_password)
    if not password_ok:
        return jsonify({"ok": False, "error": password_error}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, username, password_hash
            FROM tko_users
            WHERE id = %s
            LIMIT 1;
            """,
            (user_id,)
        )
        user = cur.fetchone()

        if not user:
            return jsonify({"ok": False, "error": "User not found"}), 404

        if not verify_password(current_password, user["password_hash"]):
            return jsonify({"ok": False, "error": "Current password is incorrect"}), 401

        if verify_password(new_password, user["password_hash"]):
            return jsonify({"ok": False, "error": "New password must be different from the current password"}), 400

        new_password_hash = hash_password(new_password)

        cur.execute(
            """
            UPDATE tko_users
            SET password_hash = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (new_password_hash, user_id)
        )

        conn.commit()

        return jsonify({
            "ok": True,
            "message": "Password changed successfully"
        })
    finally:
        cur.close()
        conn.close()



@auth_bp.patch("/api/tko/users/preferences")
def update_preferences():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"ok": False, "error": "Missing token"}), 401

    token = auth_header.split(" ", 1)[1]

    try:
        payload = decode_auth_token(token)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid or expired token"}), 401

    user_id = int(payload["sub"])
    data = request.get_json(silent=True) or {}

    theme_preference = data.get("theme_preference")
    colorblind_mode = data.get("colorblind_mode")

    allowed_themes = {"dark", "light"}

    if theme_preference is not None and theme_preference not in allowed_themes:
        return jsonify({"ok": False, "error": "theme_preference must be 'dark' or 'light'"}), 400

    if colorblind_mode is not None and not isinstance(colorblind_mode, bool):
        return jsonify({"ok": False, "error": "colorblind_mode must be true or false"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            UPDATE tko_users
            SET
                theme_preference = COALESCE(%s, theme_preference),
                colorblind_mode = COALESCE(%s, colorblind_mode),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, first_name, last_name, email, username,
                      role, agreed_to_terms, profile_image_url,
                      theme_preference, colorblind_mode,
                      two_factor_enabled, two_factor_method,
                      created_at, updated_at;
            """,
            (theme_preference, colorblind_mode, user_id)
        )
        user = cur.fetchone()

        if not user:
            return jsonify({"ok": False, "error": "User not found"}), 404

        conn.commit()

        return jsonify({
            "ok": True,
            "message": "Preferences updated",
            "user": row_with_iso_dates(user)
        })
    finally:
        cur.close()
        conn.close()


@auth_bp.post("/api/tko/auth/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"ok": False, "error": "Email is required"}), 400

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT id, email, username
            FROM tko_users
            WHERE LOWER(email) = %s
            LIMIT 1;
            """,
            (email,)
        )
        user = cur.fetchone()

        # Do not reveal whether the email exists
        if not user:
            return jsonify({
                "ok": True,
                "message": "If that email exists, a reset link has been prepared."
            })

        raw_token = generate_secure_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        cur.execute(
            """
            INSERT INTO tko_password_reset_tokens (
                user_id, token_hash, expires_at
            )
            VALUES (%s, %s, %s);
            """,
            (user["id"], token_hash, expires_at)
        )

        conn.commit()

        reset_url = f"https://tkofficial.onrender.com/reset-password.html?token={raw_token}"

        return jsonify({
            "ok": True,
            "message": "If that email exists, a reset link has been prepared.",
            "dev_reset_url": reset_url
        })
    finally:
        cur.close()
        conn.close()


@auth_bp.post("/api/tko/auth/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}

    raw_token = (data.get("token") or "").strip()
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not raw_token:
        return jsonify({"ok": False, "error": "Reset token is required"}), 400
    if not new_password:
        return jsonify({"ok": False, "error": "New password is required"}), 400
    if new_password != confirm_password:
        return jsonify({"ok": False, "error": "Passwords do not match"}), 400

    password_ok, password_error = validate_password(new_password)
    if not password_ok:
        return jsonify({"ok": False, "error": password_error}), 400

    token_hash = hash_token(raw_token)

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT prt.id, prt.user_id, prt.expires_at, prt.used_at, u.password_hash
            FROM tko_password_reset_tokens prt
            JOIN tko_users u ON u.id = prt.user_id
            WHERE prt.token_hash = %s
            LIMIT 1;
            """,
            (token_hash,)
        )
        reset_record = cur.fetchone()

        if not reset_record:
            return jsonify({"ok": False, "error": "Invalid reset token"}), 400

        if reset_record["used_at"] is not None:
            return jsonify({"ok": False, "error": "Reset token has already been used"}), 400

        expires_at = reset_record["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            return jsonify({"ok": False, "error": "Reset token has expired"}), 400

        if verify_password(new_password, reset_record["password_hash"]):
            return jsonify({"ok": False, "error": "New password must be different from the current password"}), 400

        new_password_hash = hash_password(new_password)

        cur.execute(
            """
            UPDATE tko_users
            SET password_hash = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (new_password_hash, reset_record["user_id"])
        )

        cur.execute(
            """
            UPDATE tko_password_reset_tokens
            SET used_at = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (reset_record["id"],)
        )

        conn.commit()

        return jsonify({
            "ok": True,
            "message": "Password reset successfully"
        })
    finally:
        cur.close()
        conn.close()


