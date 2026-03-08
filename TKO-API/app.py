from flask import Flask
from flask_cors import CORS

from db import init_db
from routes.core_routes import core_bp
from routes.subscriber_routes import subscriber_bp
from routes.post_routes import post_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(core_bp)
app.register_blueprint(subscriber_bp)
app.register_blueprint(post_bp)

# Run table creation when the app starts on Render too
init_db()

if __name__ == "__main__":
    import os

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
