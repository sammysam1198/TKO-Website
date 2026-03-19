import os

from flask import Flask, Response
from flask_cors import CORS

from db import init_db
from routes.core_routes import core_bp
from routes.subscriber_routes import subscribers_bp
from routes.post_routes import post_bp
from routes.auth_routes import auth_bp
from routes.dev_console_routes import dev_console_bp
from routes.forum_routes import forum_bp


app = Flask( __name__)
CORS(app)

# Security headers middleware
@app.after_request
def add_security_headers(response: Response) -> Response:
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers.pop("Server", None)
    return response


app.register_blueprint(core_bp)
app.register_blueprint(subscribers_bp)
app.register_blueprint(post_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dev_console_bp)
app.register_blueprint(forum_bp)

# Run table creation when the app starts on Render too
init_db()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    is_dev = os.getenv("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=is_dev)
