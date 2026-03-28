from flask import Blueprint, jsonify, request
from repos.CG_contact_repo import (
    create_contact_message,
    get_contact_messages,
    mark_contact_message_read,
)

CG_contact_bp = Blueprint("CG_contact_bp", __name__, url_prefix="/api/chromaglow/contact")


def _clean(value):
    return (value or "").strip()


@CG_contact_bp.post("")
def submit_contact_message():
    data = request.get_json(silent=True) or {}

    name = _clean(data.get("name"))
    email = _clean(data.get("email"))
    subject = _clean(data.get("subject"))
    message = _clean(data.get("message"))

    errors = {}

    if not name:
        errors["name"] = "Name is required."
    if not email:
        errors["email"] = "Email is required."
    elif "@" not in email:
        errors["email"] = "Enter a valid email."
    if not subject:
        errors["subject"] = "Subject is required."
    if not message:
        errors["message"] = "Message is required."
    elif len(message) < 10:
        errors["message"] = "Message must be at least 10 characters."

    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    created = create_contact_message(
        name=name,
        email=email,
        subject=subject,
        message=message,
    )

    return jsonify({
        "ok": True,
        "message": "Message received successfully.",
        "data": created,
    }), 201


@CG_contact_bp.get("")
def list_contact_messages():
    messages = get_contact_messages()
    return jsonify({"ok": True, "data": messages}), 200


@CG_contact_bp.patch("/<int:message_id>/read")
def set_contact_message_read(message_id: int):
    data = request.get_json(silent=True) or {}
    is_read = bool(data.get("is_read", True))

    updated = mark_contact_message_read(message_id, is_read=is_read)

    if not updated:
        return jsonify({"ok": False, "error": "Message not found."}), 404

    return jsonify({"ok": True, "data": updated}), 200
