from flask import Blueprint, request, jsonify
from repos.subscribers_repo import create_subscriber

subscribers_bp = Blueprint("subscribers", __name__)


@subscribers_bp.route("/api/tko/newsletter/subscribe", methods=["POST"])
def subscribe_newsletter():

    data = request.json

    first_name = data.get("first_name")
    email = data.get("email")
    message = data.get("message")

    if not email:
        return jsonify({"error": "Email required"}), 400

    try:
        subscriber = create_subscriber(first_name, email, message)

        return jsonify({
            "status": "success",
            "subscriber": subscriber
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
